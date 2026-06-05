"""
Tool Call Validator for IntelliSupply.

Validates AI-generated tool calls before execution:
1. Rejects unsupported tools.
2. Checks that required parameters exist.
3. Checks that parameter types are correct.
4. Identifies and blocks dangerous parameters (e.g. command injection, SQL injection).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Union, Tuple

# Supported tools and their parameter types
# Type definitions can be a type or a tuple of types.
SUPPORTED_TOOLS: Dict[str, Dict[str, Any]] = {
    "graphrag_query": {
        "required": {"question"},
        "types": {"question": str}
    },
    "predict_eta": {
        "required": set(),
        "types": {
            "delivery_user_id": (int, float),
            "from_dipan_id": (int, float),
            "aoi_id": (int, float),
            "receipt_time": str,
            "receipt_lat": (int, float),
            "receipt_lng": (int, float),
            "poi_lat": (int, float),
            "poi_lng": (int, float),
        }
    },
    "predict_next_stop": {
        "required": set(),
        "types": {
            "current_lat": (int, float),
            "current_lng": (int, float),
            "stops_completed": int,
            "route_start_time": str,
        }
    },
    "predict_route_sequence": {
        "required": set(),
        "types": {}  # Flexibly defined stops
    },
    "nl_to_sql": {
        "required": {"question"},
        "types": {"question": str}
    },
    "predict_demand": {
        "required": set(),
        "types": {
            "city": str,
            "region_id": str,
            "day_of_week": int,
            "month": int,
            "day_of_month": int,
            "day_of_year": int,
            "is_weekend": int,
            "lag_1": (int, float),
            "lag_2": (int, float),
            "lag_7": (int, float),
            "lag_14": (int, float),
            "rolling_mean_7": (int, float),
            "rolling_std_7": (int, float),
            "rolling_mean_28": (int, float),
            "ds": str
        }
    }
}

# Dangerous pattern signatures (e.g., shell command execution, SQL injection, path traversal)
DANGEROUS_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Command execution indicators
    (re.compile(r"(?i)\b(rm\s+-rf|chmod|chown|wget|curl|nc|netcat|sh|bash|cmd|powershell)\b"), "OS command injection pattern"),
    (re.compile(r"\$\(.*\)|\`.*\`"), "Subshell/eval command execution pattern"),
    # Path traversal
    (re.compile(r"\.\./|\.\.\\"), "Path traversal pattern"),
    # Dangerous SQL statements within parameters
    (re.compile(r"(?i)\b(union\s+select|drop\s+table|delete\s+from|alter\s+table|truncate\s+table)\b"), "Destructive SQL command pattern"),
]


def check_for_dangerous_input(value: Any) -> Tuple[bool, str | None]:
    """
    Recursively check string parameters for command/SQL injection or path traversal.
    """
    if isinstance(value, str):
        for pattern, description in DANGEROUS_PATTERNS:
            if pattern.search(value):
                return False, f"{description}: '{value[:50]}...'"
    elif isinstance(value, dict):
        for k, v in value.items():
            safe, reason = check_for_dangerous_input(k)
            if not safe:
                return False, reason
            safe, reason = check_for_dangerous_input(v)
            if not safe:
                return False, reason
    elif isinstance(value, list):
        for item in value:
            safe, reason = check_for_dangerous_input(item)
            if not safe:
                return False, reason
    return True, None


def validate_tool_call(tool_name: str, args: Dict[str, Any]) -> None:
    """
    Validate a tool call before execution.
    
    Raises:
        ValueError: If validation fails.
    """
    from security.audit.logger import log_security_violation
    
    # 1. Reject unsupported tools
    if tool_name not in SUPPORTED_TOOLS:
        err_msg = f"Unsupported tool execution blocked: {tool_name}"
        log_security_violation("UNSUPPORTED_TOOL", err_msg)
        raise ValueError(err_msg)

    schema = SUPPORTED_TOOLS[tool_name]
    required = schema["required"]
    types = schema["types"]

    # 2. Check required parameters exist
    missing = required - set(args.keys())
    if missing:
        err_msg = f"Tool '{tool_name}' missing required parameters: {', '.join(missing)}"
        log_security_violation("MISSING_PARAMETERS", err_msg)
        raise ValueError(err_msg)

    # 3. Check parameter types and scan for dangerous inputs
    for key, val in args.items():
        # Clean type checking for expected properties
        if key in types:
            expected_type = types[key]
            # Handle list/tuple of types or single type
            if not isinstance(val, expected_type):
                err_msg = f"Tool '{tool_name}' argument '{key}' has invalid type. Expected {expected_type}, got {type(val)}."
                log_security_violation("TYPE_MISMATCH", err_msg)
                raise ValueError(err_msg)

        # 4. Scan for dangerous patterns in values
        is_safe, danger_reason = check_for_dangerous_input(val)
        if not is_safe:
            err_msg = f"Dangerous operation blocked in tool '{tool_name}' parameter '{key}': {danger_reason}"
            log_security_violation("DANGEROUS_OPERATION", err_msg)
            raise ValueError(err_msg)
