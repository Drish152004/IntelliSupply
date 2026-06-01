"""
LLM tool-calling loop for the logistics agent.

The model chooses graphrag_query, predict_eta, predict_next_stop, or
predict_route_sequence. ML tools collect parameters one conversational field at a time.
"""

from __future__ import annotations

import json
from typing import Any

from integrations import llm_client, logistics_tools, parameter_collector

MAX_LLM_ROUNDS = 10

SYSTEM_PROMPT = """You are IntelliSupply's logistics assistant.

You can call these tools:
- graphrag_query: hubs, cities, couriers, orders, routes in the knowledge graph
- predict_eta: estimated delivery time in minutes for one shipment
- predict_next_stop: which stop a courier should visit next
- predict_route_sequence: best visit order across multiple stops

Choose the tool that best answers the user. You may call multiple tools if needed.
When calling ML tools, only include argument values the user explicitly provided.
Never invent IDs, coordinates, or timestamps.

After you receive tool results, reply in clear, friendly plain language."""


def _message_to_dict(msg: Any) -> dict[str, Any]:
    if isinstance(msg, dict):
        return msg
    data: dict[str, Any] = {"role": msg.role, "content": msg.content or ""}
    if msg.tool_calls:
        data["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return data


def _start_collection(
    session: dict[str, Any],
    messages: list[dict[str, Any]],
    tool_name: str,
    field_path: str,
    prompt: str,
    partial: dict[str, Any],
    tool_call_id: str,
) -> dict[str, Any]:
    session["messages"] = messages
    session["collecting"] = {
        "tool": tool_name,
        "partial": partial,
        "field_path": field_path,
        "tool_call_id": tool_call_id,
    }
    return {
        "agent": "logistics",
        "status": "awaiting_input",
        "question": prompt,
        "session": session,
    }


def run_logistics_turn(
    user_message: str,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run one user turn. May return status 'awaiting_input' with a single question,
    or status 'complete' with the assistant answer.
    """
    session = session or {"messages": []}
    messages: list[dict[str, Any]] = list(session.get("messages", []))

    collecting = session.get("collecting")
    if collecting:
        tool_name = collecting["tool"]
        partial = collecting["partial"]
        field_path = collecting["field_path"]
        parameter_collector.parse_field_answer(
            tool_name, partial, field_path, user_message
        )
        step = parameter_collector.next_collection_step(tool_name, partial)
        if step:
            next_path, prompt = step
            return _start_collection(
                session,
                messages,
                tool_name,
                next_path,
                prompt,
                partial,
                collecting["tool_call_id"],
            )

        tool_result = logistics_tools.execute_tool(
            tool_name, parameter_collector.finalize_partial(tool_name, partial)
        )
        session.pop("collecting", None)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": collecting["tool_call_id"],
                "name": tool_name,
                "content": tool_result,
            }
        )
    else:
        if not messages:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})
        messages.append({"role": "user", "content": user_message})

    client = llm_client.get_client()
    model = llm_client.get_model()

    for _ in range(MAX_LLM_ROUNDS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=logistics_tools.OPENAI_TOOLS,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=1200,
        )
        assistant = response.choices[0].message
        messages.append(_message_to_dict(assistant))

        if not assistant.tool_calls:
            answer = (assistant.content or "").strip()
            return {
                "agent": "logistics",
                "status": "complete",
                "answer": answer,
                "session": None,
            }

        for tool_call in assistant.tool_calls:
            name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            if name == "graphrag_query":
                tool_result = logistics_tools.execute_tool(name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": tool_result,
                    }
                )
                continue

            prep = logistics_tools.prepare_tool_call(name, args, None)
            if prep is not None:
                field_path, prompt, partial = prep
                return _start_collection(
                    session,
                    messages,
                    name,
                    field_path,
                    prompt,
                    partial,
                    tool_call.id,
                )

            merged = logistics_tools.merge_tool_args(name, {}, args)
            tool_result = logistics_tools.execute_tool(
                name, parameter_collector.finalize_partial(name, merged)
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": tool_result,
                }
            )

    return {
        "agent": "logistics",
        "status": "complete",
        "answer": "I could not finish within the step limit. Please try a simpler question.",
        "session": None,
    }
