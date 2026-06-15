import os
import sys
from pathlib import Path
import pandas as pd

# Define paths
FILE_PATH = Path(__file__).resolve()
BASE_DIR = FILE_PATH.parent.parent
REPO_ROOT = BASE_DIR.parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rag.supabase.supabase_connection import get_supabase_engine

def main():
    print("Connecting to database...")
    engine = get_supabase_engine()
    
    query = """
    SELECT 
        d.delivery_id AS order_id,
        d.courier_id AS delivery_user_id,
        d.poi_lat,
        d.poi_lng,
        d.receipt_lat,
        d.receipt_lng,
        d.receipt_time,
        d.sign_time,
        d.typecode,
        d.aoi_id,
        d.ds,
        c.city_name
    FROM delivery_orders d
    JOIN cities c ON d.city_id = c.city_id
    WHERE d.receipt_time IS NOT NULL 
      AND d.sign_time IS NOT NULL 
      AND d.poi_lat IS NOT NULL 
      AND d.poi_lng IS NOT NULL 
      AND d.receipt_lat IS NOT NULL 
      AND d.receipt_lng IS NOT NULL
    """
    
    print("Querying delivery orders from database...")
    df = pd.read_sql(query, engine)
    print(f"Retrieved {len(df):,} records.")
    
    output_dir = BASE_DIR / "data"
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "Delivery.csv"
    print(f"Saving to {output_path}...")
    df.to_csv(output_path, index=False)
    print("Done!")

if __name__ == "__main__":
    main()
