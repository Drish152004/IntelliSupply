"""FastAPI service for route ranker inference."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException

from api.schemas import (
    CandidateScore,
    ChosenStop,
    HealthResponse,
    NextStopRequest,
    NextStopResponse,
    RouteSequenceRequest,
    RouteSequenceResponse,
)
from route_predictor import RoutePredictor, orders_to_dataframe

DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "notebooks" / "route_ranker.pkl"


def _model_path() -> Path:
    return Path(os.environ.get("ROUTE_RANKER_MODEL", DEFAULT_MODEL))


@asynccontextmanager
async def lifespan(app: FastAPI):
    path = _model_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Model not found: {path}. Train the notebook and export route_ranker.pkl, "
            "or set ROUTE_RANKER_MODEL."
        )
    app.state.predictor = RoutePredictor.load(path)
    app.state.model_path = str(path.resolve())
    yield


app = FastAPI(
    title="IntelliSupply Route Prediction",
    description="Next-stop and full-route sequencing via LightGBM LambdaRank (v3).",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health():
    pred: RoutePredictor = app.state.predictor
    return HealthResponse(
        status="ok",
        model_version=pred.version,
        model_path=app.state.model_path,
        feature_count=len(pred.feature_cols),
    )


@app.post("/predict/next-stop", response_model=NextStopResponse)
def predict_next_stop(body: NextStopRequest):
    pred: RoutePredictor = app.state.predictor
    try:
        remaining = orders_to_dataframe([o.model_dump() for o in body.remaining_orders])
        order_id, score_map, row = pred.predict_next_stop(
            body.current_lat,
            body.current_lng,
            remaining,
            body.stops_completed,
            body.route_start_time,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return NextStopResponse(
        order_id=str(order_id),
        candidate_scores=[
            CandidateScore(order_id=oid, score=score)
            for oid, score in score_map.items()
        ],
        chosen=ChosenStop(
            order_id=str(order_id),
            poi_lat=float(row["poi_lat"]),
            poi_lng=float(row["poi_lng"]),
            dist_to_candidate=float(row.get("dist_to_candidate", 0)),
            stops_remaining=int(row.get("stops_remaining", 0)),
        ),
    )


@app.post("/predict/route", response_model=RouteSequenceResponse)
def predict_route(body: RouteSequenceRequest):
    pred: RoutePredictor = app.state.predictor
    try:
        route_df = orders_to_dataframe([o.model_dump() for o in body.orders])
        sequence = pred.predict_full_sequence(route_df)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return RouteSequenceResponse(sequence=sequence)
