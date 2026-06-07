from chatbot import env_setup  # noqa: F401
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found")

engine = create_engine(DATABASE_URL)

query = """
SELECT p.product_name,
       w.city,
       i.quantity
FROM inventory i
JOIN products p
ON i.product_id = p.product_id
JOIN warehouses w
ON i.warehouse_id = w.warehouse_id
LIMIT 10;
"""

with engine.connect() as conn:

    result = conn.execute(text(query))

    for row in result:
        print(row)