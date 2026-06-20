"""Entity resolution node: map user-facing courier and hub refs to graph IDs."""

from __future__ import annotations

import contextvars
import logging
import re
import sys
from typing import Any, Callable, Literal

from config.paths import REPO_ROOT
from observability.trace_events import trace_entity_resolution, trace_identity_binding
from orchestrator.state import AgentState
from orchestrator.tracing import log_entity_resolution, log_identity_binding

logger = logging.getLogger(__name__)

_COURIER_ROLE = "COURIER"

_AURA_ROOT = REPO_ROOT / "rag" / "aura_graphdb"
_imports_ready = False

# Canonical graph courier_id formats observed in Aura:
# - 32-char hex (primary): uuid.uuid4().hex at courier creation (aura_courier.py)
# - UUID with dashes: standard UUID string when supplied externally
# - 24-char hex ObjectId: legacy / imported records
_GRAPH_HEX32 = re.compile(r"^[0-9a-f]{32}$", re.I)
_GRAPH_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_OBJECT_ID = re.compile(r"^[0-9a-f]{24}$", re.I)
_COURIER_CODE = re.compile(r"^C(\d+)$", re.I)
_HUB_UNDERSCORE = re.compile(r"^Hub_(\d+)$", re.I)

_COURIER_REFERENCE_KEY = "courier_reference"
_COURIER_NAME_KEY = "courier_name"
_COURIER_ENTITY_KEY = "courier_id"
_HUB_ENTITY_KEYS = ("hub_id", "hub_name", "from_hub", "to_hub")
_HUB_ID_OUTPUT_KEYS = {
    "from_hub": "from_hub_id",
    "to_hub": "to_hub_id",
    "hub_id": "hub_id",
    # Domain-aware extraction emits the user-facing ``hub_name`` ("Hub 1");
    # resolve it to the canonical numeric hub_id so parameter preparation does
    # not treat it as an unresolved entity.
    "hub_name": "hub_id",
}

ResolutionStatus = Literal["success", "failure", "unchanged"]

_resolution_records_var: contextvars.ContextVar[list[dict[str, Any]]] = contextvars.ContextVar(
    "entity_resolution_records",
    default=[],
)


def get_entity_resolution_records() -> list[dict[str, Any]]:
    """Return resolution records captured during the current node execution."""
    return list(_resolution_records_var.get() or [])


def _clear_resolution_records() -> None:
    _resolution_records_var.set([])


def _record_resolution(
    *,
    entity_type: Literal["courier", "hub"],
    entity_key: str,
    before: str,
    after: str | None,
    status: ResolutionStatus,
) -> None:
    records = list(_resolution_records_var.get() or [])
    records.append(
        {
            "entity_type": entity_type,
            "entity_key": entity_key,
            "before": before,
            "after": after,
            "status": status,
        }
    )
    _resolution_records_var.set(records)


def _emit_resolution_trace(
    trace_id: str | None,
    *,
    entity_type: Literal["courier", "hub"],
    entity_key: str,
    before: str,
    after: str | None,
    status: ResolutionStatus,
) -> None:
    """Emit structured and human-readable traces for a single entity resolution."""
    if not trace_id:
        return

    _record_resolution(
        entity_type=entity_type,
        entity_key=entity_key,
        before=before,
        after=after,
        status=status,
    )

    trace_entity_resolution(
        {
            "entity_type": entity_type,
            "entity_key": entity_key,
            "before": before,
            "after": after,
            "status": status,
        },
        trace_id=trace_id,
    )
    log_entity_resolution(
        trace_id,
        entity_type=entity_type,
        entity_key=entity_key,
        before=before,
        after=after,
        status=status,
    )

    if status == "success":
        logger.info(
            "%s resolution success: %s=%s -> %s",
            entity_type,
            entity_key,
            before,
            after,
        )
    elif status == "failure":
        logger.warning(
            "%s resolution failure: %s=%s",
            entity_type,
            entity_key,
            before,
        )
    else:
        logger.info(
            "%s already canonical: %s=%s",
            entity_type,
            entity_key,
            before,
        )


def _ensure_aura_imports() -> None:
    global _imports_ready
    if _imports_ready:
        return
    root = str(REPO_ROOT)
    aura_path = str(_AURA_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    if aura_path not in sys.path:
        sys.path.insert(0, aura_path)
    _imports_ready = True


def _load_resolvers() -> tuple[Callable[..., dict[str, Any] | None], Callable[..., dict[str, Any] | None]]:
    _ensure_aura_imports()
    from aura_courier import resolve_courier  # noqa: WPS433
    from aura_hubs import resolve_hub  # noqa: WPS433

    return resolve_courier, resolve_hub


def _is_canonical_courier_id(value: str) -> bool:
    """
    Return True when value is already a graph-native courier_id.

    Examples:
        Input: 66907539947b192650558694485996b6
        Expected: canonical=True

        Input: 353273c1262ac569e651c1cc44638b8c
        Expected: canonical=True

        Input: C11
        Expected: canonical=False

        Input: Courier 11
        Expected: canonical=False
    """
    cleaned = value.strip()
    return bool(
        _GRAPH_HEX32.match(cleaned)
        or _GRAPH_UUID.match(cleaned)
        or _OBJECT_ID.match(cleaned)
    )


def _courier_lookup_kwargs(
    *,
    courier_reference: str | None = None,
    courier_name: str | None = None,
    courier_id: str | None = None,
) -> dict[str, str]:
    """Build resolve_courier keyword arguments from extracted courier entities."""
    clean_id = (courier_id or "").strip()
    if clean_id and _is_canonical_courier_id(clean_id):
        return {"courier_id": clean_id}

    clean_name = (courier_name or "").strip()
    if clean_name:
        return {"courier_name": clean_name}

    clean_ref = (courier_reference or "").strip()
    if not clean_ref:
        return {}

    code_match = _COURIER_CODE.match(clean_ref)
    if code_match:
        return {"courier_name": f"Courier {code_match.group(1)}"}

    if clean_ref.isdigit():
        return {"courier_name": f"Courier {clean_ref}"}

    return {"courier_name": clean_ref}


def _hub_lookup_kwargs(value: str) -> dict[str, Any]:
    """Build resolve_hub keyword arguments from an extracted hub reference."""
    cleaned = value.strip()
    if not cleaned:
        return {}

    if cleaned.isdigit():
        return {"hub_id": int(cleaned)}

    underscore_match = _HUB_UNDERSCORE.match(cleaned)
    if underscore_match:
        return {"hub_id": int(underscore_match.group(1))}

    trailing_digits = re.search(r"(\d+)$", cleaned)
    if trailing_digits and cleaned.lower().startswith("hub"):
        return {"hub_id": int(trailing_digits.group(1))}

    return {"hub_name": cleaned}


def _canonical_hub_id(resolved: dict[str, Any]) -> str | None:
    hub_id = resolved.get("hub_id")
    if hub_id is None:
        return None
    return str(hub_id).strip()


def resolve_courier_entity(
    *,
    courier_reference: str | None = None,
    courier_name: str | None = None,
    courier_id: str | None = None,
    resolve_courier: Callable[..., dict[str, Any] | None] | None = None,
) -> str | None:
    """Resolve extracted courier entities to the graph courier_id, or None when unresolved."""
    lookup_kwargs = _courier_lookup_kwargs(
        courier_reference=courier_reference,
        courier_name=courier_name,
        courier_id=courier_id,
    )
    if not lookup_kwargs:
        return None

    resolver = resolve_courier
    if resolver is None:
        resolver, _ = _load_resolvers()

    resolved = resolver(**lookup_kwargs)
    if not resolved:
        return None

    resolved_courier_id = resolved.get("courier_id")
    if resolved_courier_id is None or not str(resolved_courier_id).strip():
        return None
    return str(resolved_courier_id).strip()


def resolve_hub_entity(
    value: str,
    *,
    resolve_hub: Callable[..., dict[str, Any] | None] | None = None,
) -> str | None:
    """Resolve a hub reference to the canonical hub_id string, or None when unresolved."""
    lookup_kwargs = _hub_lookup_kwargs(value)
    if not lookup_kwargs:
        return None

    resolver = resolve_hub
    if resolver is None:
        _, resolver = _load_resolvers()

    resolved = resolver(**lookup_kwargs)
    if not resolved:
        return None
    return _canonical_hub_id(resolved)


def resolve_entities(
    entities: dict[str, str],
    *,
    resolve_courier: Callable[..., dict[str, Any] | None] | None = None,
    resolve_hub: Callable[..., dict[str, Any] | None] | None = None,
    trace_id: str | None = None,
) -> dict[str, str]:
    """
    Resolve courier and hub entity values to canonical graph IDs.

    ``courier_reference`` / ``courier_name`` are removed after successful resolution.
    Hub keys ``from_hub`` / ``to_hub`` are mapped to ``from_hub_id`` / ``to_hub_id``.
    """
    resolved = dict(entities or {})

    courier_reference = resolved.get(_COURIER_REFERENCE_KEY)
    courier_name = resolved.get(_COURIER_NAME_KEY)
    existing_courier_id = resolved.get(_COURIER_ENTITY_KEY)

    if courier_reference or courier_name or existing_courier_id:
        before_parts = [
            f"{_COURIER_REFERENCE_KEY}={courier_reference}" if courier_reference else "",
            f"{_COURIER_NAME_KEY}={courier_name}" if courier_name else "",
            f"{_COURIER_ENTITY_KEY}={existing_courier_id}" if existing_courier_id else "",
        ]
        before = ", ".join(part for part in before_parts if part)

        clean_existing_id = str(existing_courier_id or "").strip()
        # JWT/self-scoped identity binding injects a graph-native courier_id with no
        # name or reference. That id is already the canonical Courier.courier_id, so
        # the resolver round-trip would only return it unchanged -- skip it. Explicit
        # name/reference lookups (courier 11, courier aarushi) still resolve below.
        if (
            clean_existing_id
            and not courier_reference
            and not courier_name
            and _is_canonical_courier_id(clean_existing_id)
        ):
            _emit_resolution_trace(
                trace_id,
                entity_type="courier",
                entity_key=_COURIER_ENTITY_KEY,
                before=before,
                after=clean_existing_id,
                status="unchanged",
            )
        else:
            canonical_courier_id = resolve_courier_entity(
                courier_reference=str(courier_reference).strip() if courier_reference else None,
                courier_name=str(courier_name).strip() if courier_name else None,
                courier_id=clean_existing_id or None,
                resolve_courier=resolve_courier,
            )
            if canonical_courier_id:
                if canonical_courier_id == clean_existing_id:
                    _emit_resolution_trace(
                        trace_id,
                        entity_type="courier",
                        entity_key=_COURIER_ENTITY_KEY,
                        before=before,
                        after=canonical_courier_id,
                        status="unchanged",
                    )
                else:
                    resolved[_COURIER_ENTITY_KEY] = canonical_courier_id
                    _emit_resolution_trace(
                        trace_id,
                        entity_type="courier",
                        entity_key=_COURIER_ENTITY_KEY,
                        before=before,
                        after=canonical_courier_id,
                        status="success",
                    )
                resolved.pop(_COURIER_REFERENCE_KEY, None)
                resolved.pop(_COURIER_NAME_KEY, None)
            else:
                _emit_resolution_trace(
                    trace_id,
                    entity_type="courier",
                    entity_key=_COURIER_ENTITY_KEY,
                    before=before,
                    after=None,
                    status="failure",
                )

    for key in _HUB_ENTITY_KEYS:
        hub_ref = resolved.get(key)
        if not hub_ref:
            continue
        before = str(hub_ref).strip()
        canonical_hub_id = resolve_hub_entity(
            hub_ref,
            resolve_hub=resolve_hub,
        )
        if canonical_hub_id:
            output_key = _HUB_ID_OUTPUT_KEYS.get(key, key)
            if canonical_hub_id == before:
                _emit_resolution_trace(
                    trace_id,
                    entity_type="hub",
                    entity_key=key,
                    before=before,
                    after=canonical_hub_id,
                    status="unchanged",
                )
            else:
                resolved[output_key] = canonical_hub_id
                if output_key != key:
                    resolved.pop(key, None)
                _emit_resolution_trace(
                    trace_id,
                    entity_type="hub",
                    entity_key=key,
                    before=before,
                    after=canonical_hub_id,
                    status="success",
                )
        else:
            _emit_resolution_trace(
                trace_id,
                entity_type="hub",
                entity_key=key,
                before=before,
                after=None,
                status="failure",
            )

    return resolved


def apply_courier_identity_binding(state: AgentState) -> AgentState:
    """
    Bind the authenticated courier identity from the JWT, the single source of truth.

    COURIER role only. ADMIN/LOGISTICS/INVENTORY identities are never auto-bound.

    The JWT ``courier_id`` claim (``authenticated_courier_id``) is the graph-native
    courier id: it is the same ``Courier.courier_id`` returned by name resolution and
    compared in resource authorization. It is therefore used directly as
    ``bound_courier_id`` -- no graph lookup, fuzzy matching, or name normalization.

    Self-scoped courier queries ("my route", "my orders", ...) are bound to the
    courier's own ``courier_id`` here so they resolve without clarification. This
    is identity binding only -- resource ownership authorization is a later phase.
    """
    if state.get("user_role") != _COURIER_ROLE:
        return state

    trace_id = state.get("trace_id")
    bound_courier_id = (str(state.get("authenticated_courier_id") or "")).strip() or None
    source = "authenticated_jwt" if bound_courier_id else "unresolved"

    updated: AgentState = {**state, "bound_courier_id": bound_courier_id}

    if trace_id:
        bound_name = state.get("bound_courier_name")
        trace_identity_binding(
            {
                "role": _COURIER_ROLE,
                "bound_courier_name": bound_name,
                "bound_courier_id": bound_courier_id,
                "resolved_courier_id": bound_courier_id,
                "source": source,
            },
            trace_id=trace_id,
        )
        log_identity_binding(
            trace_id,
            bound_courier_name=bound_name,
            bound_courier_id=bound_courier_id,
            source=source,
        )

    # Self-scoped identity binding: a courier's "my ..." query targets their own
    # data, so populate courier_id from the bound identity when no explicit
    # courier was requested.
    entities = dict(updated.get("entities") or {})
    if (
        bound_courier_id
        and entities.get("self_scoped") == "true"
        and not (entities.get(_COURIER_ENTITY_KEY) or "").strip()
    ):
        entities[_COURIER_ENTITY_KEY] = bound_courier_id
        updated["entities"] = entities

    return updated


def resolve_entities_node(state: AgentState) -> AgentState:
    """
    Bind courier identity and resolve user-facing courier/hub references.

    Does not classify intent, authorize, run HITL, or validate parameters.
    """
    if state.get("clarification_failed"):
        return state

    _clear_resolution_records()
    bound_state = apply_courier_identity_binding(state)

    entities = dict(bound_state.get("entities") or {})
    if not entities:
        return bound_state

    return {
        **bound_state,
        "entities": resolve_entities(entities, trace_id=bound_state.get("trace_id")),
    }
