import sys
import os
from pathlib import Path
import pandas as pd

# Add paths to sys.path
sys.path.insert(0, './FastAPI')
sys.path.insert(0, './Inventory_intelligence_agent/simulation_pipeline')

import bootstrap
from base_state import build_base_state, DATA_DIR

def check():
    df = pd.read_csv(DATA_DIR / "demand_forecast_daily.csv")
    combinations = df[["category", "product_id", "hub_id", "forecast_date"]].drop_duplicates()
    print(f"Total unique combinations to check: {len(combinations)}")
    
    success_count = 0
    fail_count = 0
    errors = {}
    
    for idx, row in combinations.iterrows():
        cat = row["category"]
        prod = row["product_id"]
        hub = str(row["hub_id"])
        dt = row["forecast_date"]
        
        try:
            build_base_state(hub_id=hub, product_id=prod, category=cat, simulation_date=dt)
            success_count += 1
        except Exception as e:
            fail_count += 1
            err_msg = str(e)
            errors[err_msg] = errors.get(err_msg, 0) + 1
            if fail_count <= 5:
                print(f"Failed combination: cat={cat}, prod={prod}, hub={hub}, date={dt}. Error: {err_msg}")
                
    print(f"\nResult: {success_count} succeeded, {fail_count} failed.")
    print("Error breakdown:")
    for err, count in errors.items():
        print(f" - {err}: {count} occurrences")

if __name__ == "__main__":
    check()
