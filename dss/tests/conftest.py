"""Shared fixtures.

The pipeline stages are named with a leading digit so they sort into run
order, which means they cannot be imported by name. They are loaded from
their file paths instead.
"""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def load_stage(filename: str):
    """Import a numbered pipeline stage from its path."""
    path = SRC / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def cfg():
    import config
    return config


@pytest.fixture(scope="session")
def clean():
    return load_stage("03_clean.py")


@pytest.fixture(scope="session")
def ahp():
    import ahp as module
    return module


@pytest.fixture(scope="session")
def dea():
    return load_stage("04_dea.py")


@pytest.fixture(scope="session")
def squad_efficiency(processed):
    return pd.read_parquet(processed / "squad_efficiency.parquet")


@pytest.fixture(scope="session")
def goal_programme():
    return load_stage("07_goal_programme.py")


@pytest.fixture(scope="session")
def processed(cfg):
    """The processed data directory, skipping the suite if it is not built."""
    path = ROOT / cfg.PROCESSED
    if not (path / "squad_value.parquet").exists():
        pytest.skip("processed data not built; run stages 03 to 07 first")
    return path


@pytest.fixture(scope="session")
def squad_value(processed):
    return pd.read_parquet(processed / "squad_value.parquet")


@pytest.fixture(scope="session")
def weighted(processed):
    return pd.read_csv(processed / "squad_weighted.csv")


@pytest.fixture(scope="session")
def preemptive(processed):
    return pd.read_csv(processed / "squad_preemptive.csv")


@pytest.fixture(scope="session")
def players_season(processed):
    return pd.read_parquet(processed / "players_season.parquet")


@pytest.fixture(scope="session")
def league_raw(cfg):
    path = ROOT / cfg.RAW / "league_players_raw.parquet"
    if not path.exists():
        pytest.skip("raw league data not present; run stage 02 first")
    return pd.read_parquet(path)
