import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config.env import load_env

load_env()


def get_supabase_engine():
    host = os.getenv("SUPABASE_DB_HOST")
    port = os.getenv("SUPABASE_DB_PORT", "6543")
    dbname = os.getenv("SUPABASE_DB_NAME", "postgres")
    user = os.getenv("SUPABASE_DB_USER")
    password = os.getenv("SUPABASE_DB_PASSWORD")

    if not all([host, port, dbname, user, password]):
        raise ValueError("Missing Supabase database environment variables.")

    password = quote_plus(password)

    db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"

    return create_engine(db_url)
