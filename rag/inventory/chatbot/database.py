import os

from chatbot import env_setup  # noqa: F401 — loads root .env
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def test_connection():
    try:
        with engine.connect() as connection:
            print("Connected to Neon PostgreSQL successfully!")
    except Exception as e:
        print("Connection failed:")
        print(e)


if __name__ == "__main__":
    test_connection()
