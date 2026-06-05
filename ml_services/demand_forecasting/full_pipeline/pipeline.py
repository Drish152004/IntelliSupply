"""End-to-end demand pipeline: LaDe ingest → panel → forecast → outputs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from sklearn.pipeline import Pipeline

from ..lade_demand import (
    build_daily_demand,
    build_multistep_forecast,
    load_artifact,
    load_city_data,
    make_daily_panel,
)
from ..lade_weekly import prepare_weekly_pipeline
from ..weekly_strategies import produce_weekly_forecast

Granularity = Literal["daily", "weekly"]


@dataclass
class ForecastSummary:
    total_predicted: float
    period_start: str
    period_end: str
    n_regions: int
    cities: list[str]


@dataclass
class PipelineResult:
    granularity: str
    horizon: int
    dataset_kind: str
    strategy: str
    panel_rows: int
    summary: ForecastSummary
    forecast: pd.DataFrame
    by_period: list[dict[str, Any]]
    by_city: list[dict[str, Any]]
    top_regions: list[dict[str, Any]]
    meta: dict[str, Any] = field(default_factory=dict)
    output_dir: str = ""


class DemandForecastPipeline:
    """
    Real-world LaDe CSV → daily demand panel → multistep forecast.

    Mirrors ml_services/route_prediction/full_pipeline/pipeline.py:
    one class, one run() entry point, optional artifact export.
    """

    def __init__(
        self,
        *,
        model_path: Path | None = None,
        lade_dir: Path | None = None,
        output_dir: Path | None = None,
        strategy_path: Path | None = None,
    ):
        self.model_path = model_path
        self.lade_dir = lade_dir
        self.output_dir = output_dir
        self.strategy_path = strategy_path
        self._model: Pipeline | None = None
        self._meta: dict[str, Any] | None = None

    def _load_model(self) -> tuple[Pipeline, dict[str, Any]]:
        if self._model is not None and self._meta is not None:
            return self._model, self._meta
        if self.model_path and self.model_path.exists():
            import joblib

            self._model = joblib.load(self.model_path)
            meta_path = self.model_path.with_suffix(".meta.json")
            if meta_path.exists():
                self._meta = json.loads(meta_path.read_text(encoding="utf-8"))
            else:
                self._meta = {}
            return self._model, self._meta

        self._model, self._meta = load_artifact("daily")
        return self._model, self._meta

    def _load_weekly_strategy(self, override: str | None = None) -> str:
        if override:
            return override
        path = self.strategy_path
        if path and path.exists():
            return json.loads(path.read_text(encoding="utf-8")).get("recommended", "daily_sum")
        from .config import WEEKLY_STRATEGY_PATH

        if WEEKLY_STRATEGY_PATH.exists():
            return json.loads(WEEKLY_STRATEGY_PATH.read_text(encoding="utf-8")).get(
                "recommended", "daily_sum"
            )
        return "daily_sum"

    def _build_panel(self, dataset_kind: str) -> pd.DataFrame:
        raw = load_city_data(dataset_kind, lade_dir=self.lade_dir)
        daily = build_daily_demand(raw)
        return make_daily_panel(daily)

    def _summarize_forecast(self, forecast: pd.DataFrame) -> ForecastSummary:
        return ForecastSummary(
            total_predicted=float(forecast["predicted_demand"].sum()),
            period_start=str(forecast["ds"].min().date()),
            period_end=str(forecast["ds"].max().date()),
            n_regions=int(forecast[["city", "region_id"]].drop_duplicates().shape[0]),
            cities=sorted(forecast["city"].unique().tolist()),
        )

    def _aggregate_outputs(self, forecast: pd.DataFrame) -> tuple[list[dict], list[dict], list[dict]]:
        by_period = (
            forecast.groupby("ds", as_index=False)["predicted_demand"]
            .sum()
            .sort_values("ds")
        )
        by_city = (
            forecast.groupby("city", as_index=False)["predicted_demand"]
            .sum()
            .sort_values("predicted_demand", ascending=False)
        )
        top_regions = (
            forecast.groupby(["city", "region_id"], as_index=False)["predicted_demand"]
            .sum()
            .nlargest(15, "predicted_demand")
        )

        period_rows = [
            {"date": str(r.ds.date()), "predicted_demand": round(r.predicted_demand)}
            for r in by_period.itertuples()
        ]
        city_rows = [
            {"city": r.city, "predicted_demand": round(r.predicted_demand)}
            for r in by_city.itertuples()
        ]
        region_rows = [
            {
                "city": r.city,
                "region_id": str(r.region_id),
                "predicted_demand": round(r.predicted_demand),
            }
            for r in top_regions.itertuples()
        ]
        return period_rows, city_rows, region_rows

    def run(
        self,
        *,
        granularity: Granularity = "daily",
        horizon: int | None = None,
        city: str | None = None,
        dataset_kind: str = "delivery",
        weekly_strategy: str | None = None,
        save_outputs: bool = True,
    ) -> PipelineResult:
        default_h = 7 if granularity == "daily" else 4
        horizon = horizon or default_h

        if granularity == "daily" and horizon > 28:
            raise ValueError("Daily horizon max is 28 days")
        if granularity == "weekly" and horizon > 12:
            raise ValueError("Weekly horizon max is 12 weeks")

        model, meta = self._load_model()
        panel = self._build_panel(dataset_kind)

        if granularity == "daily":
            forecast = build_multistep_forecast(panel, model, n_days=horizon)
            strategy = "daily"
            result_meta = {**meta, "granularity": "daily"}
        else:
            strategy = self._load_weekly_strategy(weekly_strategy)
            weekly_panel, _ = prepare_weekly_pipeline(dataset_kind)
            forecast = produce_weekly_forecast(
                strategy,  # type: ignore[arg-type]
                dataset_kind=dataset_kind,
                n_weeks=horizon,
                daily_panel=panel,
                weekly_panel=weekly_panel,
                daily_model=model,
            )
            extra: dict[str, Any] = {}
            strat_path = self.strategy_path
            from .config import WEEKLY_STRATEGY_PATH

            path = strat_path if strat_path and strat_path.exists() else WEEKLY_STRATEGY_PATH
            if path.exists():
                extra = json.loads(path.read_text(encoding="utf-8"))
            result_meta = {
                **meta,
                "granularity": "weekly",
                "weekly_strategy": strategy,
                "strategy_comparison": extra.get("metrics", {}),
            }

        if city:
            forecast = forecast[forecast["city"] == city].copy()

        period_rows, city_rows, region_rows = self._aggregate_outputs(forecast)
        summary = self._summarize_forecast(forecast)

        result = PipelineResult(
            granularity=granularity,
            horizon=horizon,
            dataset_kind=dataset_kind,
            strategy=strategy,
            panel_rows=len(panel),
            summary=summary,
            forecast=forecast.sort_values(["ds", "city", "region_id"]).reset_index(drop=True),
            by_period=period_rows,
            by_city=city_rows,
            top_regions=region_rows,
            meta=result_meta,
            output_dir=str(self.output_dir) if self.output_dir else "",
        )

        if save_outputs and self.output_dir:
            self._save_outputs(result)

        return result

    def _save_outputs(self, result: PipelineResult) -> None:
        assert self.output_dir is not None
        self.output_dir.mkdir(parents=True, exist_ok=True)

        detail_path = self.output_dir / "forecast_detail.csv"
        result.forecast.to_csv(detail_path, index=False)

        pd.DataFrame(result.by_period).to_csv(
            self.output_dir / "forecast_by_period.csv", index=False
        )
        pd.DataFrame(result.by_city).to_csv(
            self.output_dir / "forecast_by_city.csv", index=False
        )
        pd.DataFrame(result.top_regions).to_csv(
            self.output_dir / "forecast_top_regions.csv", index=False
        )

        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "granularity": result.granularity,
            "horizon": result.horizon,
            "dataset_kind": result.dataset_kind,
            "strategy": result.strategy,
            "panel_rows": result.panel_rows,
            "summary": asdict(result.summary),
            "by_period": result.by_period,
            "by_city": result.by_city,
            "top_regions": result.top_regions,
            "holdout_metrics": result.meta.get("holdout_metrics", {}),
        }
        with open(self.output_dir / "pipeline_summary.json", "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
