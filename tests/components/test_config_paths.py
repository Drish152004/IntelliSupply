"""Tests for config.paths canonical locations."""

from __future__ import annotations

from config.paths import (
    CLUSTER_ASSIGNMENTS_PATH,
    NOTEBOOK_OUTPUTS_DIR,
    REPO_ROOT,
    ROUTE_MODEL_PATH,
    ROUTE_NOTEBOOKS_DIR,
)


def test_repo_root_exists():
    assert REPO_ROOT.is_dir()


def test_notebook_dirs():
    assert ROUTE_NOTEBOOKS_DIR.name == "route_prediction"
    assert NOTEBOOK_OUTPUTS_DIR == ROUTE_NOTEBOOKS_DIR / "outputs"


def test_route_model_path_location():
    assert ROUTE_MODEL_PATH == ROUTE_NOTEBOOKS_DIR / "route_ranker.pkl"
    assert ROUTE_MODEL_PATH.is_file(), "route_ranker.pkl should exist after notebook migration"


def test_cluster_assignments_path_under_outputs():
    assert CLUSTER_ASSIGNMENTS_PATH.parent == NOTEBOOK_OUTPUTS_DIR
