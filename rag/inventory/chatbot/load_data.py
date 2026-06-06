import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

# Load env variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found")

# Create engine
engine = create_engine(DATABASE_URL)

# CSV PATHS
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DATA_DIR = os.path.join(
    BASE_DIR,
    "inventory_database"
)

# LOAD CSV FILES
products_df = pd.read_csv(
    os.path.join(DATA_DIR, "products.csv")
)

warehouses_df = pd.read_csv(
    os.path.join(DATA_DIR, "Hubs.csv")
)

inventory_df = pd.read_csv(
    os.path.join(DATA_DIR, "inventory.csv")
)

# INSERT INTO POSTGRES
products_df.to_sql(
    "products",
    engine,
    if_exists="append",
    index=False
)

warehouses_df.to_sql(
    "warehouses",
    engine,
    if_exists="append",
    index=False
)

inventory_df.to_sql(
    "inventory",
    engine,
    if_exists="append",
    index=False
)

print("Data loaded successfully!")