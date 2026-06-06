"""Orchestration script to run the full ETA prediction pipeline."""

import argparse
from pathlib import Path

from full_pipeline.preprocess import preprocess_data
from full_pipeline.feature_engineering import compute_and_save_stats
from full_pipeline.training import train_model

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT_DIR / "data" / "Delivery.csv"
DEFAULT_MODELS_DIR = ROOT_DIR / "models"


def main():
    parser = argparse.ArgumentParser(description="Run full ETA prediction training pipeline.")
    parser.add_argument(
        "--data-path",
        type=str,
        default=str(DEFAULT_DATA_PATH),
        help="Path to the raw Delivery.csv dataset."
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help="Directory to save the trained model and pickled artifacts."
    )
    args = parser.parse_args()

    data_path = Path(args.data_path)
    models_dir = Path(args.models_dir)

    if not data_path.exists():
        raise FileNotFoundError(f"Raw data file not found at: {data_path}")

    print("=== Starting ETA Prediction Pipeline ===")
    print(f"Data source: {data_path}")
    print(f"Artifacts output directory: {models_dir}")
    print("========================================")

    # Step 1: Preprocess data
    print("\n[Step 1/3] Preprocessing raw data...")
    df = preprocess_data(data_path)

    # Step 2: Feature Engineering & Statistics Computation
    print("\n[Step 2/3] Computing historical statistics...")
    stats = compute_and_save_stats(df, models_dir=models_dir)

    # Step 3: Model Training
    print("\n[Step 3/3] Training model...")
    train_model(df, stats=stats, models_dir=models_dir)

    print("\n=== Pipeline Executed Successfully ===")


if __name__ == "__main__":
    main()
