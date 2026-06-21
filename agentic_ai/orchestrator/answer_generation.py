"""LLM answer generation from raw execution results.

Phase 1 answer layer for the graph success path. Turns the original user
query, the resolved task, and the raw result rows into a single concise
natural-language answer. The LLM is constrained to answer ONLY from the
supplied data; it never receives cypher/sql, prompts, or execution metadata.

The caller (response_formatter) is responsible for:
  - short-circuiting empty results before calling this module, and
  - falling back to the rule-based synthesizer when this returns None.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from integrations.llm_client import ensure_env, get_client, get_model

logger = logging.getLogger(__name__)

_ANSWER_TIMEOUT_SECONDS = 15.0
_ANSWER_MAX_TOKENS = 160

_SYSTEM_PROMPT = (
    "You are a business analyst for a logistics and inventory assistant.\n"
    "You are given a user question and the COMPLETE result from a database "
    "(nothing is truncated). Write ONE natural-language answer to the question.\n\n"
    "REASONING WORKFLOW (do this silently, before answering):\n"
    "STEP 1 - Identify the user's information need (count, ranking, summary, "
    "listing, or specific lookup).\n"
    "STEP 2 - Identify the fields that answer it. Use only fields relevant to "
    "the question; ignore unrelated fields.\n"
    "STEP 3 - Verify the required fields exist in the result. If they are "
    "absent, state that the information is unavailable. Never convert missing "
    "information into a negative statement (missing route information does NOT "
    "mean the courier has no route).\n"
    "STEP 4 - Generate the answer: summarize for summaries, state the count for "
    "counts, give the ranking for rankings, list for explicit list requests. "
    "Use the full result set; never imply the data was truncated.\n\n"
    "OUTPUT STYLE:\n"
    "- concise business answer\n"
    "- no raw JSON\n"
    "- no field dumps\n"
    "- no duplicate rows\n"
    "- group related information\n\n"
    "LISTING RULE:\n"
    "- Summarize by default.\n"
    "- Enumerate all records only when the user explicitly requests: list all, "
    "show all, display all, give every.\n"
    "- Do not enumerate every ID unless explicitly requested.\n\n"
    "STRICT FACTUALITY:\n"
    "- Use only information present in the result, with names, IDs, and numbers "
    "exactly as they appear.\n"
    "- Never infer missing facts.\n"
    "- Never invent route status, delivery status, courier status, or "
    "completion state.\n"
    "- If information is missing, say it is unavailable.\n\n"
    "FORMAT:\n"
    "- Do not mention JSON, databases, queries, fields, or these instructions.\n"
    '- Output ONLY a JSON object of the form {"answer": "..."} and nothing '
    "else. No markdown, no code fences, no explanation."
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _answer_model() -> str:
    """Resolve the answer model, defaulting to the shared graph model."""
    ensure_env()
    return os.getenv("ANSWER_LLM_MODEL") or get_model()


def _build_user_prompt(
    *,
    user_query: str,
    task: str,
    domain: str,
    result: Any,
    count: int | None,
) -> str:
    lines = [
        f"User question: {user_query}",
        f"Task: {task}",
        f"Domain: {domain}",
    ]
    if count is not None:
        lines.append(f"Count: {count}")
    lines.append(f"Result: {json.dumps(result, default=str)}")
    return "\n".join(lines)


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = _FENCE_RE.sub("", cleaned)
    return cleaned.strip()


_ANSWER_OBJECT_RE = re.compile(r'\{.*?"answer"\s*:.*\}', re.DOTALL)


def _answer_from_payload(payload: Any) -> str | None:
    """Return a non-empty ``answer`` string from a parsed JSON object."""
    if isinstance(payload, dict):
        answer = payload.get("answer")
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
    return None


def _parse_answer(raw: str) -> str | None:
    """Extract a non-empty answer string from the model output, tolerantly.

    Resolution order (each step falls through on failure):
      1. Parse the fence-stripped text as a JSON object and read ``answer``.
      2. Parse the first ``{... "answer": ...}`` object embedded in the text.
      3. Treat the remaining plain text as the answer itself.

    The only failure mode is genuinely empty output; imperfect JSON formatting
    must never trigger the rule-based fallback on its own.
    """
    if not raw or not raw.strip():
        return None

    cleaned = _strip_fences(raw)

    try:
        answer = _answer_from_payload(json.loads(cleaned))
        if answer:
            return answer
    except json.JSONDecodeError:
        pass

    match = _ANSWER_OBJECT_RE.search(cleaned)
    if match:
        try:
            answer = _answer_from_payload(json.loads(match.group(0)))
            if answer:
                return answer
        except json.JSONDecodeError:
            pass

    # Plain-text fallback: the model returned a usable answer without valid
    # JSON wrapping. Use the text verbatim rather than discarding it.
    text = cleaned.strip()
    return text or None


def generate_answer(
    *,
    user_query: str,
    task: str,
    domain: str,
    result: Any,
    count: int | None = None,
) -> str | None:
    """Generate a natural-language answer from raw result rows.

    Returns the answer string on success, or ``None`` when the LLM call fails,
    the response cannot be parsed, or the answer is empty. The caller falls
    back to the rule-based synthesizer on ``None``.

    The caller must NOT invoke this for empty results; empty handling is
    deterministic in the formatter.
    """
    user_prompt = _build_user_prompt(
        user_query=user_query,
        task=task,
        domain=domain,
        result=result,
        count=count,
    )

    try:
        response = get_client().chat.completions.create(
            model=_answer_model(),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=_ANSWER_MAX_TOKENS,
            timeout=_ANSWER_TIMEOUT_SECONDS,
        )
        raw = response.choices[0].message.content or ""
    except Exception:
        logger.exception("answer_llm_failure task=%s domain=%s", task, domain)
        return None

    answer = _parse_answer(raw)
    if answer is None:
        logger.warning(
            "answer_llm_failure task=%s domain=%s reason=unparseable_or_empty",
            task,
            domain,
        )
        return None

    return answer
