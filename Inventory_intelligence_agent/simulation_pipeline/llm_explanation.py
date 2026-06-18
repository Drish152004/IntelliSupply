from __future__ import annotations

import json
import os
from typing import Optional

from groq import Groq

from recommendation_models import ExplainabilityPayload, LLMExplanation

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

_client: Optional[Groq] = None

SYSTEM_PROMPT = """
You are an inventory planning explainability assistant for IntelliSupply.

Your role is EXPLANATION ONLY. You receive a structured payload with simulation-backed
metrics, rankings, and representative scenario cases. Convert it into clear,
executive-friendly narrative text.

Rules:
- Do NOT invent recommendations, interventions, or actions not present in the payload.
- Do NOT change rankings, scores, or any numeric simulation results.
- Do NOT override or contradict the recommendation_summary in the payload.
- All numbers and comparisons must come directly from the payload.
- If no intervention was recommended, explain baseline risk and that no options were evaluated.
- Write in plain business language suitable for supply-chain executives.
"""

_LLM_EXPLANATION_SCHEMA = {
    "executive_summary": "string",
    "recommended_action": "string",
    "baseline_analysis": "string",
    "decision_comparison": "string",
    "best_case_analysis": "string",
    "most_likely_analysis": "string",
    "worst_case_analysis": "string",
}


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set.")
        _client = Groq(api_key=api_key)
    return _client


def _get_groq_model() -> str:
    return os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)


def _format_case(case: dict) -> str:
    stockout_day = case.get("stockout_day")
    stockout_text = (
        f"stockout on day {stockout_day}" if stockout_day is not None else "no stockout"
    )
    return (
        f"ending inventory {case.get('ending_inventory')}, "
        f"shortage {case.get('shortage_quantity')}, {stockout_text}"
    )


def _build_template_explanation(payload: ExplainabilityPayload) -> LLMExplanation:
    scenario = payload.scenario_summary
    baseline = payload.baseline_summary
    rec = payload.recommendation_summary
    stockout_pct = baseline.get("stockout_probability", 0.0) * 100.0

    executive_summary = (
        f"Hub {scenario.get('hub_id')} product {scenario.get('product_id')} "
        f"({scenario.get('category')}) faces a {stockout_pct:.0f}% stockout probability "
        f"with current stock {scenario.get('current_stock')} against safety stock "
        f"{scenario.get('safety_stock')}."
    )

    if rec.get("selected_intervention"):
        utility = rec.get("utility_score", 0)
        recommended_action = (
            f"Recommended action: {rec.get('selected_intervention')} "
            f"(effectiveness {utility:.0f}/100). {rec.get('explanation', '')}"
        )
    else:
        recommended_action = rec.get("explanation", "No intervention recommended.")

    baseline_analysis = (
        f"Baseline simulation shows stockout probability {stockout_pct:.0f}%, "
        f"average shortage {baseline.get('avg_shortage_quantity'):.1f} units, "
        f"average ending inventory {baseline.get('avg_ending_inventory'):.1f}, "
        f"and {baseline.get('avg_days_below_safety_stock'):.1f} days below safety stock. "
        f"Risk signals: {', '.join(baseline.get('signals', [])) or 'none'}."
    )

    if payload.ranked_decisions_summary:
        lines = [
            f"#{item['rank']} {item['title']} "
            f"(effectiveness {item.get('utility_score', 0):.0f}/100)"
            for item in payload.ranked_decisions_summary
        ]
        decision_comparison = "Evaluated interventions (ranked): " + "; ".join(lines) + "."
    else:
        decision_comparison = "No decision interventions were simulated."

    best_case_analysis = (
        "Best case after recommended intervention: "
        + _format_case(payload.best_case_summary)
    )
    most_likely_analysis = (
        "Most likely case after recommended intervention: "
        + _format_case(payload.most_likely_summary)
    )
    worst_case_analysis = (
        "Worst case after recommended intervention: "
        + _format_case(payload.worst_case_summary)
    )

    return LLMExplanation(
        executive_summary=executive_summary,
        recommended_action=recommended_action,
        baseline_analysis=baseline_analysis,
        decision_comparison=decision_comparison,
        best_case_analysis=best_case_analysis,
        most_likely_analysis=most_likely_analysis,
        worst_case_analysis=worst_case_analysis,
    )


def _payload_to_dict(payload: ExplainabilityPayload) -> dict:
    return {
        "scenario_summary": payload.scenario_summary,
        "baseline_summary": payload.baseline_summary,
        "recommendation_summary": payload.recommendation_summary,
        "ranked_decisions_summary": payload.ranked_decisions_summary,
        "best_case_summary": payload.best_case_summary,
        "most_likely_summary": payload.most_likely_summary,
        "worst_case_summary": payload.worst_case_summary,
    }


def generate_llm_explanation(
    payload: ExplainabilityPayload,
    *,
    skip_llm: bool = False,
) -> LLMExplanation:
    if skip_llm or not os.environ.get("GROQ_API_KEY"):
        return _build_template_explanation(payload)

    schema_prompt = (
        "Respond with a single JSON object with exactly these string fields:\n"
        f"{json.dumps(_LLM_EXPLANATION_SCHEMA, indent=2)}"
    )
    user_content = json.dumps(_payload_to_dict(payload), separators=(",", ":"))

    response = _get_client().chat.completions.create(
        model=_get_groq_model(),
        messages=[
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{schema_prompt}"},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = response.choices[0].message.content
    if not content:
        return _build_template_explanation(payload)

    data = json.loads(content)
    return LLMExplanation(
        executive_summary=str(data.get("executive_summary", "")),
        recommended_action=str(data.get("recommended_action", "")),
        baseline_analysis=str(data.get("baseline_analysis", "")),
        decision_comparison=str(data.get("decision_comparison", "")),
        best_case_analysis=str(data.get("best_case_analysis", "")),
        most_likely_analysis=str(data.get("most_likely_analysis", "")),
        worst_case_analysis=str(data.get("worst_case_analysis", "")),
    )
