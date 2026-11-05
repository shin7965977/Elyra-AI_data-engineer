"""Smoke tests for UI components and app imports."""

import os
from src.db.connection import get_engine, init_db, get_session
from src.evaluation.benchmark import load_golden_dataset


def test_ui_dependencies_and_golden_dataset():
    engine, db_type = get_engine()
    init_db(engine)
    assert db_type in ("PostgreSQL", "SQLite")

    cases = load_golden_dataset("data/golden_dataset")
    assert len(cases) == 8


def test_app_imports_cleanly():
    import src.ui.app
    assert src.ui.app.GOLDEN_CASES is not None
    assert len(src.ui.app.SAMPLE_PROMPTS) >= 5
