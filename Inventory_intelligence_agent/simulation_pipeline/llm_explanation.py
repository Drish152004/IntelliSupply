from __future__ import annotations

import json
import os
from typing import Any, Optional

from groq import Groq

from recommendation_models import LLMExplanation

DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_MAX_TOKENS = 1200

_client: Optional[Groq] = None

SYSTEM_PROMPT = """
You are a senior supply chain analyst at IntelliSupply writing a client-facing planning report.

Your role is EXPLANATION ONLY. You receive a structured brief with simulation-backed metrics,
rankings, scenario cases, and intervention comparisons. Write a thorough analyst report in
flowing prose (5-7 paragraphs, roughly 400-650 words) as if you are briefing a customer.

Cover these themes in order, woven into natural paragraphs (no section headers or bullet lists):
1. Current situation — hub, product, category, inventory position vs safety stock, demand outlook, and overall risk context.
2. Baseline assessment — what simulations show if no action is taken: stockout probability, expected shortage, days below safety stock, and key risk signals. Explain what this means operationally for the customer.
3. Recommended intervention — the selected action, why it ranks first, and the business rationale.
4. Expected impact — quantify how the recommendation changes stockout risk, shortage, ending inventory, and days below safety stock versus doing nothing. Translate metrics into practical supply-chain impact (service levels, exposure, recovery).
5. Alternatives considered — briefly compare other evaluated options, why they scored lower, and what trade-offs they represent.
6. Scenario outlook — best, most likely, and worst case after the recommended action; explain the range of outcomes and residual risk.
7. Closing recommendation — clear, actionable next step for the customer.

Rules:
- Do NOT invent recommendations, interventions, or actions not present in the brief.
- Do NOT change rankings, scores, or any numeric simulation results.
- Do NOT override or contradict the recommendation in the brief.
- All numbers and comparisons must come directly from the brief.
- Round displayed numbers sensibly for executive readability (whole units, one decimal where appropriate).
- If no intervention was recommended, focus on baseline risk, why options were insufficient, and what to monitor.
- Write in plain, confident business language. Address the reader directly.
"""

_LLM_EXPLANATION_SCHEMA = {"analyst_report": "string"}


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


def _round_num(value: Any, digits: int = 1) -> float | int:
    if value is None:
        return 0
    number = float(value)
    if digits == 0:
        return int(round(number))
    return round(number, digits)


def _format_case(case: dict) -> str:
    stockout_day = case.get("stockout_day")
    stockout_text = (
        f"a stockout on day {stockout_day}" if stockout_day is not None else "no stockout"
    )
    return (
        f"ending inventory of {_round_num(case.get('ending_inventory'), 0)} units, "
        f"shortage of {_round_num(case.get('shortage_quantity'), 0)} units, and {stockout_text}"
    )


def _format_improvements(improvements: dict[str, Any]) -> str:
    stockout_pts = _round_num(-float(improvements.get("stockout_probability_change", 0)) * 100, 0)
    shortage = _round_num(improvements.get("shortage_reduction", 0), 0)
    ending_inv = _round_num(improvements.get("ending_inventory_change", 0), 0)
    days_ss = _round_num(-float(improvements.get("days_below_safety_stock_change", 0)), 1)
    parts = []
    if stockout_pts:
        parts.append(f"stockout probability down {abs(stockout_pts):.0f} percentage points")
    if shortage:
        parts.append(f"average shortage reduced by {abs(shortage)} units")
    if ending_inv:
        sign = "higher" if ending_inv > 0 else "lower"
        parts.append(f"ending inventory {abs(ending_inv)} units {sign}")
    if days_ss:
        parts.append(f"{abs(days_ss)} fewer days below safety stock on average")
    return ", ".join(parts) if parts else "modest operational improvement"


def _format_alternative(item: dict[str, Any]) -> str:
    improvements = item.get("expected_improvements") or {}
    stockout_pts = _round_num(
        -float(improvements.get("stockout_probability_change", 0)) * 100,
        0,
    )
    return (
        f"{item.get('title')} (impact {_round_num(item.get('impact_score', 0), 0)}/100"
        + (f", stockout risk down {abs(stockout_pts)} pts" if stockout_pts else "")
        + ")"
    )


def _build_template_explanation(brief: dict[str, Any]) -> LLMExplanation:
    situation = brief["situation"]
    baseline = brief["baseline_risk"]
    rec = brief["recommendation"]
    stockout_pct = _round_num(baseline.get("stockout_probability", 0.0) * 100.0, 0)
    baseline_outlook = baseline.get("outlook_if_no_action") or {}

    opening = (
        f"Based on our review of Hub {situation.get('hub_id')} for product "
        f"{situation.get('product_id')} in the {situation.get('category')} category, "
        f"current on-hand inventory is {_round_num(situation.get('current_stock'), 0)} units "
        f"against a safety stock target of {_round_num(situation.get('safety_stock'), 0)} units, "
        f"with forecast demand of roughly {_round_num(situation.get('predicted_demand'), 0)} units "
        f"over the {_round_num(situation.get('planning_window_days', 7), 0)}-day planning window. "
        f"Coverage is approximately {_round_num(situation.get('coverage_days', 0), 1)} days, "
        f"and the composite risk score is {_round_num(situation.get('composite_risk_score', 0), 0)}/100 "
        f"({situation.get('risk_level', 'unknown')} risk)."
    )

    signals = baseline.get("signals") or []
    baseline_assessment = (
        f"If no corrective action is taken, Monte Carlo simulation across multiple demand "
        f"and replenishment scenarios indicates a {stockout_pct:.0f}% probability of stockout, "
        f"with an average shortage of {_round_num(baseline.get('avg_shortage_quantity', 0), 0)} units "
        f"and {_round_num(baseline.get('avg_days_below_safety_stock', 0), 1)} days below safety stock. "
    )
    if signals:
        baseline_assessment += f"The main risk drivers flagged in the model are {', '.join(signals)}. "
    baseline_assessment += (
        "In the most likely no-action path, we would expect "
        f"{_format_case(baseline_outlook.get('most_likely', {}))}, which implies meaningful "
        "service-level exposure if demand materializes near forecast."
    )

    if rec.get("selected_intervention"):
        impact = _round_num(rec.get("impact_score", 0), 1)
        improvements = rec.get("expected_improvements") or {}
        recommendation = (
            f"Our recommended course of action is to {rec.get('selected_intervention').lower()} "
            f"if operationally feasible. This option ranked first among evaluated interventions "
            f"with an impact score of {impact}/100. {rec.get('explanation', '').strip()} "
            "From a planning perspective, this intervention directly addresses the inventory gap "
            "that is driving elevated stockout risk."
        )
        impact_paragraph = (
            "Relative to doing nothing, the recommended intervention is expected to deliver "
            f"{_format_improvements(improvements)}. In practical terms, that should improve "
            "product availability at this hub, reduce the likelihood of emergency transfers "
            "or expedites, and narrow the gap between current stock and policy safety levels."
        )
        alternatives = brief.get("alternatives_considered") or []
        other_alts = [
            item
            for item in alternatives
            if item.get("title") != rec.get("selected_intervention")
        ]
        if other_alts:
            alt_text = "; ".join(_format_alternative(item) for item in other_alts[:3])
            alternatives_paragraph = (
                f"We also evaluated {len(other_alts)} alternative intervention(s), including "
                f"{alt_text}. These options were not selected because they offered lower simulated "
                "risk reduction or weaker trade-offs against operational complexity."
            )
        else:
            alternatives_paragraph = (
                "No other interventions produced a stronger simulated risk reduction in this scenario."
            )
    else:
        recommendation = rec.get(
            "explanation",
            "We are not recommending a corrective intervention at this time.",
        )
        impact_paragraph = (
            "Given the current simulation results, the expected benefit of available interventions "
            "does not clearly outweigh the baseline risk profile or operational cost of action."
        )
        alternatives_paragraph = (
            "Alternative options were reviewed but none demonstrated sufficient improvement to warrant recommendation."
        )

    outlook = brief.get("outlook") or {}
    if rec.get("selected_intervention"):
        outlook_paragraph = (
            "After implementing the recommended approach, simulated outcomes span a range of futures. "
            f"The most likely case shows {_format_case(outlook.get('most_likely', {}))}. "
            f"In a favorable scenario we could see {_format_case(outlook.get('best_case', {}))}, "
            f"while a stressed scenario could still produce {_format_case(outlook.get('worst_case', {}))}. "
            "This range highlights both the upside of acting now and the residual uncertainty that "
            "should be monitored through the planning window."
        )
        closing = (
            "We recommend proceeding with the top-ranked intervention and tracking stock position, "
            "forecast accuracy, and replenishment timing daily through the planning horizon. "
            "If conditions shift materially, the simulation should be rerun to validate whether "
            "a different intervention becomes preferable."
        )
    else:
        outlook_paragraph = (
            "Scenario simulations under the current trajectory show a spread of possible outcomes. "
            f"The most likely path is {_format_case(outlook.get('most_likely', {}))}, "
            f"while upside and downside cases range from {_format_case(outlook.get('best_case', {}))} "
            f"to {_format_case(outlook.get('worst_case', {}))}."
        )
        closing = (
            "We recommend close monitoring of inventory against safety stock and forecast error, "
            "with a follow-up simulation if stockout risk escalates or replenishment timing slips."
        )

    paragraphs = [
        opening,
        baseline_assessment,
        recommendation,
        impact_paragraph,
        alternatives_paragraph,
        outlook_paragraph,
        closing,
    ]
    report = "\n\n".join(paragraphs)
    return LLMExplanation(analyst_report=report)


def generate_llm_explanation(
    brief: dict[str, Any],
    *,
    skip_llm: bool = False,
) -> LLMExplanation:
    if skip_llm or not os.environ.get("GROQ_API_KEY"):
        return _build_template_explanation(brief)

    schema_prompt = (
        "Respond with a single JSON object with exactly this string field:\n"
        f"{json.dumps(_LLM_EXPLANATION_SCHEMA, indent=2)}"
    )
    user_content = json.dumps(brief, separators=(",", ":"))

    response = _get_client().chat.completions.create(
        model=_get_groq_model(),
        messages=[
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{schema_prompt}"},
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=int(os.environ.get("GROQ_EXPLANATION_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
    )

    content = response.choices[0].message.content
    if not content:
        return _build_template_explanation(brief)

    data = json.loads(content)
    report = str(data.get("analyst_report", "")).strip()
    if len(report.split()) < 120:
        template = _build_template_explanation(brief)
        if len(template.analyst_report.split()) > len(report.split()):
            return template

    if not report:
        return _build_template_explanation(brief)

    return LLMExplanation(analyst_report=report)
