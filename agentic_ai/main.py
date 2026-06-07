"""
CLI entrypoint for the agentic_ai orchestration system.

Interactive session: inventory (NL-to-SQL, demand ML) and logistics (GraphRAG, ML) via an LLM.
When a tool needs inputs, it asks for one field at a time.
"""

import json
import os

from orchestrator.graph import run_orchestrator

_QUIT_WORDS = frozenset({"quit", "exit", "q"})


def _parse_response(final_response: str) -> dict | None:
    try:
        return json.loads(final_response)
    except (json.JSONDecodeError, TypeError):
        return None


def _is_quit(text: str) -> bool:
    return text.lower() in _QUIT_WORDS


def _print_result(payload: dict | None, raw: str) -> None:
    if not payload:
        print(f"\n{raw}")
        return

    status = payload.get("status")
    if status == "success":
        source = payload.get("source", "")
        data = payload.get("data", {})
        if source == "cache":
            print(f"\nAssistant (cached): {data}")
        elif source == "graph":
            print(f"\nAssistant (graph): {data}")
        elif source == "ml":
            print(f"\nAssistant (ml): {data}")
        else:
            print(f"\nAssistant: {data.get('answer', payload.get('message', raw))}")
        return
    if status == "clarification_required":
        return
    if status == "access_denied":
        print(f"\nAccess denied: {payload.get('message', raw)}")
        return
    if status == "error":
        print(f"\nError ({payload.get('stage', 'unknown')}): {payload.get('message', raw)}")
        return
    print(f"\n{raw}")


def _authenticated_user_from_env() -> dict | None:
    role = os.environ.get("INTELLISUPPLY_USER_ROLE")
    if not role or not role.strip():
        return None
    user: dict = {"role": role.strip()}
    courier_id = os.environ.get("INTELLISUPPLY_COURIER_ID")
    if courier_id and courier_id.strip():
        user["courier_id"] = courier_id.strip()
    return user


def _run_query_turn(initial_query: str) -> None:
    """One user question, including tool parameter follow-ups."""
    logistics_session = None
    inventory_session = None
    user_message = initial_query
    authenticated_user = _authenticated_user_from_env()

    while True:
        result = run_orchestrator(
            user_message,
            logistics_session=logistics_session,
            inventory_session=inventory_session,
            authenticated_user=authenticated_user,
        )

        print(f"\nDetected domain: {result['domain']}")
        print(f"Detected task: {result['task']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Selected agent: {result['selected_agent']}")

        payload = _parse_response(result["final_response"])

        if payload and payload.get("status") == "clarification_required":
            print(f"\nAssistant: {payload.get('question', 'I need a bit more information.')}")
            user_message = input("\nYou: ").strip()
            if _is_quit(user_message):
                print("Cancelled this request.")
                return
            if not user_message:
                print("Cancelled this request.")
                return
            session = (payload.get("data") or {}).get("session")
            if result.get("domain") == "inventory":
                inventory_session = session
                logistics_session = None
            else:
                logistics_session = session
                inventory_session = None
            continue

        _print_result(payload, result["final_response"])
        return


def main() -> None:
    print(
        "IntelliSupply agent. Ask about inventory, demand forecasts, "
        "shipments, routes, or the network."
    )
    print("Type 'quit' to exit.\n")
    while True:
        user_query = input("You: ").strip()
        if not user_query:
            continue
        if _is_quit(user_query):
            print("Goodbye.")
            break
        _run_query_turn(user_query)


if __name__ == "__main__":
    main()
