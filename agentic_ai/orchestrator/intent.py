"""
LLM intent detection (few-shot) for inventory vs logistics routing.

Uses the shared NVIDIA client (integrations.llm_client). Keyword matching is
only a fallback when the model returns an unparseable label.
"""

from __future__ import annotations

import re

from integrations.llm_client import get_client, get_model
from orchestrator.state import AgentState

VALID_INTENTS = frozenset({"inventory", "logistics"})

INVENTORY_KEYWORDS = ("stock", "inventory", "warehouse", "demand", "forecast")
LOGISTICS_KEYWORDS = ("shipment", "route", "delivery", "eta", "transport")

SYSTEM_PROMPT = """You classify user messages for IntelliSupply's two-agent orchestrator.

Agents:
- inventory: Postgres NL-to-SQL (products, warehouses, stock, hubs in cities) and
  hosted demand forecasting (lags, rolling means, region demand).
- logistics: Neo4j GraphRAG (couriers, pickup orders, hub routes, grid routes) and
  ML for ETA, next-stop, and route sequence.

Reply with exactly one word: inventory or logistics.
No punctuation, no explanation."""

FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    ("How many iPhones are in Shanghai?", "inventory"),
    ("Show products below threshold in Hangzhou warehouses", "inventory"),
    ("Forecast demand for Hangzhou region 56 next week", "inventory"),
    ("What is the total stock quantity for MacBook in Beijing?", "inventory"),
    ("List low inventory AirPods by hub city", "inventory"),
    ("What is the shipment ETA for order 88421?", "logistics"),
    ("Optimize the delivery route for courier 1204", "logistics"),
    ("Which hub should this courier visit next?", "logistics"),
    ("How many pickup orders are assigned in Chongqing?", "logistics"),
    ("Predict travel time between these two hub coordinates", "logistics"),
]


def _session_collecting(session: dict | None) -> bool:
    return bool(session and session.get("collecting"))


def _build_messages(user_query: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for question, label in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": label})
    messages.append({"role": "user", "content": user_query})
    return messages


def _parse_intent_label(text: str) -> str | None:
    cleaned = text.strip().lower()
    if cleaned in VALID_INTENTS:
        return cleaned
    match = re.search(r"\b(inventory|logistics)\b", cleaned)
    if match:
        return match.group(1)
    return None


def _keyword_fallback(query: str) -> str:
    inventory_score = sum(1 for keyword in INVENTORY_KEYWORDS if keyword in query)
    logistics_score = sum(1 for keyword in LOGISTICS_KEYWORDS if keyword in query)
    if inventory_score > logistics_score:
        return "inventory"
    if logistics_score > inventory_score:
        return "logistics"
    return "logistics"


def classify_intent(user_query: str) -> str:
    """Classify a message as inventory or logistics using few-shot LLM prompting."""
    try:
        response = get_client().chat.completions.create(
            model=get_model(),
            messages=_build_messages(user_query),
            temperature=0.0,
            max_tokens=16,
        )
        raw = response.choices[0].message.content or ""
        label = _parse_intent_label(raw)
        if label:
            return label
    except Exception:
        pass
    return _keyword_fallback(user_query.lower())


def detect_intent(state: AgentState) -> AgentState:
    """Detect intent from the user query and update state."""
    if _session_collecting(state.get("inventory_session")):
        return {**state, "intent": "inventory"}
    if _session_collecting(state.get("logistics_session")):
        return {**state, "intent": "logistics"}

    intent = classify_intent(state["user_query"])
    return {**state, "intent": intent}
