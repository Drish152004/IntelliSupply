"""Start the unified ML API (avoids naming conflict with the fastapi package)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "").lower() in ("1", "true", "yes")
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=port,
        reload=reload,
        app_dir=str(ROOT),
    )