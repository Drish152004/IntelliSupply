"""
Structured Audit Logger for IntelliSupply.

Writes security-related events (user queries, blocked prompts, executed tools,
GraphRAG queries, and safety violations) as JSON lines to logs/security_audit.log.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Resolve the root log file path: repo_root/logs/security_audit.log
REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = REPO_ROOT / "logs"
LOG_FILE_PATH = LOG_DIR / "security_audit.log"


def _write_log(event_type: str, details: Dict[str, Any], severity: str = "INFO") -> None:
    """
    Format the log event as JSON and append it as a line to the audit log file.
    Ensures thread/process safety by creating directories if needed and using standard appends.
    """
    try:
        # Create logs directory if it doesn't exist
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        # Build structured log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": details
        }

        # Write to the log file
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")
    except Exception as exc:
        # Fallback to standard error or print if write fails to prevent breaking business execution
        print(f"[SECURITY AUDIT LOG ERROR] Failed to write audit log: {exc}")


def log_query(user_query: str, masked_query: str) -> None:
    """Audit the initial user query and its sanitized/masked version."""
    _write_log(
        event_type="USER_QUERY",
        severity="INFO",
        details={
            "original_query": user_query,
            "masked_query": masked_query
        }
    )


def log_blocked_prompt(user_query: str, reason: str) -> None:
    """Audit a prompt query blocked by prompt injection/jailbreak guardrails."""
    _write_log(
        event_type="PROMPT_BLOCKED",
        severity="WARNING",
        details={
            "user_query": user_query,
            "reason": reason
        }
    )


def log_executed_tool(tool_name: str, args: Dict[str, Any], success: bool, error: str | None = None) -> None:
    """Audit LLM tool call execution and outcome."""
    # Mask PII in arguments before writing to log
    from security.pii.masker import default_masker
    masked_args = default_masker.mask_data(args)

    _write_log(
        event_type="TOOL_EXECUTION",
        severity="INFO" if success else "ERROR",
        details={
            "tool_name": tool_name,
            "arguments": masked_args,
            "success": success,
            "error": error
        }
    )


def log_graphrag_query(user_question: str, cypher: str, success: bool, error: str | None = None) -> None:
    """Audit a Neo4j GraphRAG query execution."""
    from security.pii.masker import default_masker
    masked_question = default_masker.mask_text(user_question)

    _write_log(
        event_type="GRAPHRAG_QUERY",
        severity="INFO" if success else "ERROR",
        details={
            "user_question": masked_question,
            "cypher": cypher,
            "success": success,
            "error": error
        }
    )


def log_security_violation(violation_type: str, details: str) -> None:
    """Audit general security violations (e.g. prompt injection, tool validation, cypher validation)."""
    _write_log(
        event_type="SECURITY_VIOLATION",
        severity="CRITICAL",
        details={
            "violation_type": violation_type,
            "message": details
        }
    )
