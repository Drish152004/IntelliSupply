import os
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


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