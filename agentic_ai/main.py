"""
CLI entrypoint for the agentic_ai orchestration system.

Accepts a user query from the terminal, runs the LangGraph workflow,
and prints the detected intent, selected agent, and final response.
"""

from orchestrator.graph import run_orchestrator


def main() -> None:
    user_query = input("Enter your query: ").strip()
    if not user_query:
        print("No query provided. Exiting.")
        return

    result = run_orchestrator(user_query)

    print(f"\nDetected intent: {result['intent']}")
    print(f"Selected agent: {result['selected_agent']}")
    print(f"Final response: {result['final_response']}")


if __name__ == "__main__":
    main()
