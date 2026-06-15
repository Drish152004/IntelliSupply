import os
import sys
import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ============================================================
# Load root .env safely
# Do NOT use: from chatbot import env_setup
# because chatbot.py conflicts with the chatbot package name.
# ============================================================

CURRENT_FILE = Path(__file__).resolve()
CHATBOT_DIR = CURRENT_FILE.parent
REPO_ROOT = CURRENT_FILE.parents[3]

for path in [str(REPO_ROOT), str(CHATBOT_DIR.parent)]:
    if path not in sys.path:
        sys.path.insert(0, path)


def _load_env_setup():
    env_setup_path = CHATBOT_DIR / "env_setup.py"

    spec = importlib.util.spec_from_file_location(
        "inventory_chatbot_env_setup",
        env_setup_path,
    )

    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load env_setup.py from {env_setup_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_env_setup()


# ============================================================
# Database connection
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found. Add DATABASE_URL to your root .env file."
    )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def test_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("Connected to PostgreSQL/Supabase successfully!")
    except Exception as exc:
        print("Connection failed:")
        print(exc)


if __name__ == "__main__":
    test_connection()
