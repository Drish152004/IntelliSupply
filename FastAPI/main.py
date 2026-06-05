"""
Unified FastAPI gateway for IntelliSupply ML services.

Run from repo root:
  pip install -r fastapi/requirements.txt
  python fastapi/run.py

Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import sys
import time
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

FASTAPI_ROOT = Path(__file__).resolve().parent
if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))
REPO_ROOT = FASTAPI_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from routers import demand_forecasting, eta_prediction, route_prediction  # noqa: E402
from services.registry import init_all_services  # noqa: E402

from security.pii.masker import default_masker  # noqa: E402
from security.guardrails.prompt_guard import check_prompt_injection  # noqa: E402
from security.audit.logger import log_security_violation, _write_log  # noqa: E402


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Read request body safely for auditing/safety check
        body_bytes = b""
        if request.method in ("POST", "PUT", "PATCH"):
            body_bytes = await request.body()
            # Restore request receive channel
            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            request._receive = receive

        body_str = body_bytes.decode("utf-8", errors="ignore") if body_bytes else ""
        
        # Parse body as JSON to apply PII masking for log
        masked_body = body_str
        try:
            if body_str:
                body_json = json.loads(body_str)
                masked_body = json.dumps(default_masker.mask_data(body_json))
        except Exception:
            pass

        # Scan for prompt injection in request payload (if any string is sent)
        if body_str:
            is_safe, error_msg = check_prompt_injection(body_str)
            if not is_safe:
                log_security_violation(
                    "API_PROMPT_INJECTION",
                    f"Blocked API request to '{request.url.path}' due to safety guardrails."
                )
                return Response(
                    content=json.dumps({"detail": error_msg or "Security Alert: Input query rejected due to safety policy violation."}),
                    status_code=400,
                    media_type="application/json"
                )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log structured API request
            _write_log(
                event_type="API_REQUEST",
                severity="INFO",
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": dict(request.query_params),
                    "request_body": masked_body,
                    "status_code": response.status_code,
                    "duration_sec": round(process_time, 4)
                }
            )
            return response
        except Exception as exc:
            process_time = time.time() - start_time
            log_security_violation(
                "API_ERROR",
                f"Exception during request {request.method} {request.url.path}: {exc}"
            )
            raise exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.service_status = init_all_services()
    yield


app = FastAPI(
    title="IntelliSupply ML API",
    description="Centralized inference for route prediction, demand forecasting, and ETA.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityAuditMiddleware)

app.include_router(route_prediction.router)
app.include_router(demand_forecasting.router)
app.include_router(eta_prediction.router)


@app.get("/health")
def health():
    return {"status": "ok", "services": app.state.service_status}


@app.get("/")
def root():
    return {
        "message": "IntelliSupply unified ML API",
        "docs": "/docs",
        "services": {
            "route": "/route",
            "demand": "/demand",
            "eta": "/eta",
        },
    }
