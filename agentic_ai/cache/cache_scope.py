"""Cache scope helpers: entity signatures and identity scopes for safe cache matching."""

from __future__ import annotations

from orchestrator.state import AgentState


def _resolve_courier_id(state: AgentState) -> str | None:
    courier_id = state.get("authenticated_courier_id")
    if courier_id:
        return str(courier_id).strip()

    session = state.get("logistics_session") or {}
    session_courier = session.get("courier_id")
    if session_courier:
        return str(session_courier).strip()

    auth = state.get("authenticated_user") or {}
    auth_courier = auth.get("courier_id")
    if auth_courier:
        return str(auth_courier).strip()

    return None


def build_entity_signature(state: AgentState) -> str:
    """
    Build a deterministic entity signature for cache partitioning.

    Reads state["entities"] only; does not infer or mutate self_scoped.

    Examples:
        order ORD123 -> order:ORD123
        shipment SHIP123 -> shipment:SHIP123
        courier C001 -> courier:C001
        my route (courier bound) -> courier:<courier_id>
        inventory query -> inventory_global
        no entity -> global
    """
    domain = state.get("domain", "")
    task = state.get("task", "")

    if domain == "inventory" or task == "inventory_nlsql":
        return "inventory_global"

    entities = state.get("entities") or {}

    if entities.get("order_id"):
        return f"order:{entities['order_id']}"
    if entities.get("shipment_id"):
        return f"shipment:{entities['shipment_id']}"
    if entities.get("courier_id"):
        return f"courier:{entities['courier_id']}"
    if entities.get("self_scoped") == "true":
        courier_id = _resolve_courier_id(state)
        if courier_id:
            return f"courier:{courier_id}"

    if entities.get("hub_id"):
        return f"hub:{entities['hub_id']}"
    city = entities.get("city_name") or entities.get("city")
    if city:
        return f"city:{city}"
    if entities.get("from_hub") and entities.get("to_hub"):
        return f"route:{entities['from_hub']}->{entities['to_hub']}"

    return "global"


def build_identity_scope(state: AgentState) -> str:
    """
    Build an identity scope to prevent cross-user cache leakage.

    Examples:
        Courier with courier_id -> courier:C001
        Authenticated user -> user:123
        Unauthenticated -> unauthenticated:<role|unknown>
    """
    role = state.get("user_role")
    courier_id = _resolve_courier_id(state)
    if role == "COURIER" and courier_id:
        return f"courier:{courier_id}"

    user_id = state.get("authenticated_user_id")
    if not user_id:
        auth = state.get("authenticated_user") or {}
        user_id = auth.get("user_id")
    if user_id:
        return f"user:{user_id}"

    return f"unauthenticated:{role or 'unknown'}"
