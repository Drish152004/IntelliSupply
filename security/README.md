# Enterprise AI Security Layer for IntelliSupply

This directory contains the security module for the IntelliSupply logistics platform. It provides modular, lightweight, and production-ready guardrails designed to secure user inputs, LLM interactions, tool calls, and GraphRAG operations.

## Architecture

The security layer is organized into decoupled, single-responsibility modules:

```
security/
├── pii/
│   └── masker.py            # Sanitizes names, phone numbers, emails, and addresses
├── guardrails/
│   └── prompt_guard.py      # Protects against prompt injection and jailbreak attempts
├── validators/
│   ├── tool_validator.py    # Ensures tool schema type safety and blocks dangerous inputs
│   └── cypher_validator.py  # Enforces read-only operations for Neo4j GraphRAG
├── audit/
│   └── logger.py            # Structured JSON audit logging to logs/security_audit.log
└── README.md                # Security architecture documentation (this file)
```

---

## Implemented Protections

### 1. PII Masking & Redaction (`security/pii/masker.py`)
Protects user privacy by intercepting and redacting sensitive data.
- **Rules**:
  - **Phone Numbers**: Identifies 10-digit formats and replaces the middle digits with `X` (e.g., `9876543210` $\rightarrow$ `98XXXXXX10`).
  - **Emails**: Redacted as `[EMAIL_REDACTED]`.
  - **Names**: Redacted as `[REDACTED]`.
  - **Addresses & Zip Codes**: Redacted as `[ADDRESS_REDACTED]` or `[ZIP_REDACTED]`.
- **Modes**:
  - `mask_text(text: str)`: Applies compiled regex patterns to free-form text.
  - `mask_data(payload: dict | list)`: Recursively scans structured JSON/dictionary inputs and redacts values matching keys like `customer_name`, `phone`, `email`, `address`.

### 2. Prompt Injection Protection (`security/guardrails/prompt_guard.py`)
Scans user query inputs before execution to intercept and block jailbreaks and instruction overrides.
- **Checks**:
  - Direct instruction override phrases (e.g. `"ignore previous instructions"`).
  - Secret prompt/API key extraction requests (e.g. `"reveal secrets"`, `"reveal system prompt"`).
  - Malicious database actions (e.g. `"dump database"`, SQL queries in prompt).
  - Jailbreak tactics (e.g. `"developer mode"`, `"override safety"`).
- **Behavior**: If triggered, blocks graph execution immediately, logs a critical violation, and returns:
  `"Security Alert: Input query rejected due to safety policy violation."`

### 3. Tool Call Validation (`security/validators/tool_validator.py`)
Validates model-generated tool arguments before execution.
- **Checks**:
  - Rejects execution of unsupported tools.
  - Asserts existence of all required parameters.
  - Ensures argument data types strictly match the tool schemas.
  - Scans parameter values to block command execution (`rm -rf`, `curl`, backticks) and path traversal (`../`).

### 4. Read-Only GraphRAG Cypher Validation (`security/validators/cypher_validator.py`)
Enforces a read-only environment for Neo4j database interactions.
- **Checks**:
  - Pre-processes the query to strip comments (avoiding comment-bypass attacks).
  - Blocks query execution if it contains write keywords: `CREATE`, `MERGE`, `DELETE`, `DETACH`, `SET`, `REMOVE`, `DROP`, `LOAD CSV`.
  - Blocks admin/metadata procedures (`CALL dbms`, `CALL apoc`).
  - Ensures the query strictly starts with read-only keywords: `MATCH`, `OPTIONAL MATCH`, `WITH`, `RETURN`, `UNWIND`, `SHOW`.

### 5. Centralized Audit Logging (`security/audit/logger.py`)
Writes events as JSON lines to the `logs/security_audit.log` file at the repository root.
- **Events Logged**:
  - `USER_QUERY`: Incoming prompts and their PII-masked versions.
  - `PROMPT_BLOCKED`: Security block events on injection detection.
  - `TOOL_EXECUTION`: Tool execution requests, arguments (PII-masked), and result status.
  - `GRAPHRAG_QUERY`: Generated Cypher statements and execution outcomes.
  - `SECURITY_VIOLATION`: Critical security blocks and exceptions.
  - `API_REQUEST`: Inbound FastAPI gateway requests, payload details (PII-masked), response status, and processing times.

---

## Future Extensibility

### 1. Extending PII Masking Rules
To add new PII entities (e.g., credit card numbers or passport IDs):
1. Define a regular expression in `security/pii/masker.py`.
2. Add a redaction call to `mask_text`.
3. Add key-level matching to `mask_data`.

### 2. Modifying Guardrail Patterns
To intercept new prompt injection vectors:
1. Append a compiled regex pattern and a descriptive reason to `INJECTION_PATTERNS` in `security/guardrails/prompt_guard.py`.

### 3. Registering New Tools
When adding tools to the agents:
1. Add the tool parameters and expected types to the `SUPPORTED_TOOLS` mapping in `security/validators/tool_validator.py`.
