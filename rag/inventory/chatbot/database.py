from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found")

# Create engine
engine = create_engine(DATABASE_URL)

# Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Test connection
def test_connection():
    try:
        with engine.connect() as connection:
            print("Connected to Neon PostgreSQL successfully!")

    except Exception as e:
        print("Connection failed:")
        print(e)

if __name__ == "__main__":
    test_connection()