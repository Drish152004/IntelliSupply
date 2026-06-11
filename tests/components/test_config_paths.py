"""Tests for config.paths canonical locations."""

from __future__ import annotations

from config.paths import (
    ETA_MODEL_PATH,
    MODELS_ROOT,
    REPO_ROOT,
    ROUTE_MODEL_PATH,
)


def test_repo_root_exists():
    assert REPO_ROOT.is_dir()


def test_models_root_location():
    assert MODELS_ROOT == REPO_ROOT / "models"


def test_route_model_path_location():
    assert ROUTE_MODEL_PATH == MODELS_ROOT / "route_ranker.pkl"
    assert ROUTE_MODEL_PATH.is_file(), "route_ranker.pkl should exist under models/"


def test_eta_model_path_location():
    assert ETA_MODEL_PATH == MODELS_ROOT / "eta_lightgbm_model.pkl"
    assert ETA_MODEL_PATH.is_file(), "eta_lightgbm_model.pkl should exist under models/"
