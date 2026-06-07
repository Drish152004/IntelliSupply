"""Resource-level graph authorization for courier-scoped lookups."""

from __future__ import annotations

import logging
import re

from orchestrator.rbac.courier_identity import COURIER_IDENTITY_NOT_BOUND

logger = logging.getLogger(__name__)

COURIER_SCOPED_TASKS: frozenset[str] = frozenset({
    "route_lookup",
    "route_prediction",
    "next_stop_prediction",
})

_SELF_PATTERN = re.compile(r"\b(?:my|mine)\b", re.I)


class GraphAuthorizer:
    """Authorize graph queries against session-bound courier resources."""

    COURIER_SCOPED_TASKS = COURIER_SCOPED_TASKS

    @staticmethod
    def _session_courier_id(session: dict | None) -> str | None:
        if not session:
            return None
        courier_id = session.get("courier_id")
        if isinstance(courier_id, str) and courier_id.strip():
            return courier_id.strip()
        return None

    @staticmethod
    def _is_self_scoped(user_query: str, entities: dict[str, str]) -> bool:
        return entities.get("self_scoped") == "true" or bool(_SELF_PATTERN.search(user_query))

    @staticmethod
    def check(
        *,
        role: str,
        task: str,
        entities: dict[str, str],
        user_query: str,
        session: dict | None = None,
    ) -> tuple[bool, str | None]:
        """
        Return (allowed, denial_reason).

        ADMIN and LOGISTICS are always allowed. COURIER access to courier-scoped
        tasks requires a session-bound courier_id and cannot target other couriers.
        """
        normalized_role = role.strip().upper()

        if normalized_role in {"ADMIN", "LOGISTICS"}:
            logger.info(
                "GRAPH AUTH ALLOW\nrole=%s\ntask=%s",
                normalized_role,
                task,
            )
            return True, None

        if task not in COURIER_SCOPED_TASKS:
            logger.info(
                "GRAPH AUTH ALLOW\nrole=%s\ntask=%s",
                normalized_role,
                task,
            )
            return True, None

        if normalized_role != "COURIER":
            logger.info(
                "GRAPH AUTH ALLOW\nrole=%s\ntask=%s",
                normalized_role,
                task,
            )
            return True, None

        session_courier_id = GraphAuthorizer._session_courier_id(session)
        if not session_courier_id:
            reason = COURIER_IDENTITY_NOT_BOUND
            logger.info(
                "GRAPH AUTH DENY\nrole=%s\ntask=%s\nreason=%s",
                normalized_role,
                task,
                reason,
            )
            return False, reason

        requested_courier_id = entities.get("courier_id")
        self_scoped = GraphAuthorizer._is_self_scoped(user_query, entities)

        if self_scoped or not requested_courier_id:
            requested_courier_id = session_courier_id

        if requested_courier_id.upper() != session_courier_id.upper():
            reason = (
                f"Courier {session_courier_id} cannot access route information "
                f"for courier {requested_courier_id}."
            )
            logger.info(
                "GRAPH AUTH DENY\nrole=%s\ntask=%s\nreason=%s",
                normalized_role,
                task,
                reason,
            )
            return False, reason

        logger.info(
            "GRAPH AUTH ALLOW\nrole=%s\ntask=%s\ncourier_id=%s",
            normalized_role,
            task,
            session_courier_id,
        )
        return True, None

    @staticmethod
    def resolve_courier_id(
        *,
        entities: dict[str, str],
        user_query: str,
        session: dict | None = None,
    ) -> dict[str, str]:
        """Inject session courier_id for self-scoped courier route queries."""
        resolved = dict(entities)
        if resolved.get("courier_id"):
            return resolved

        if not GraphAuthorizer._is_self_scoped(user_query, entities):
            return resolved

        session_courier_id = GraphAuthorizer._session_courier_id(session)
        if session_courier_id:
            resolved["courier_id"] = session_courier_id
        return resolved
