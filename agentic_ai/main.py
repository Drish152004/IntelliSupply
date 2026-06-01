"""
CLI entrypoint for the agentic_ai orchestration system.

Interactive session: the logistics agent uses GraphRAG and ML tools via an LLM.
When a tool needs inputs, it asks for one field at a time.
"""

import json

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
    if payload and payload.get("status") == "complete":
        print(f"\nAssistant: {payload.get('answer', raw)}")
        return
    if payload and payload.get("status") == "awaiting_input":
        return
    print(f"\n{raw}")


def _run_query_turn(initial_query: str) -> None:
    """One user question, including tool parameter follow-ups."""
    session = None
    user_message = initial_query

    while True:
        result = run_orchestrator(user_message, logistics_session=session)

        print(f"\nDetected intent: {result['intent']}")
        print(f"Selected agent: {result['selected_agent']}")

        payload = _parse_response(result["final_response"])

        if payload and payload.get("status") == "awaiting_input":
            print(f"\nAssistant: {payload.get('question', 'I need a bit more information.')}")
            user_message = input("\nYou: ").strip()
            if _is_quit(user_message):
                print("Cancelled this request.")
                return
            if not user_message:
                print("Cancelled this request.")
                return
            session = payload.get("session")
            continue

        _print_result(payload, result["final_response"])
        return


def main() -> None:
    print("IntelliSupply logistics agent. Ask about shipments, routes, or the network.")
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
