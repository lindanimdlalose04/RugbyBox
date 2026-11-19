"""Tests for the shared store reader.

Most tests run offline against stubbed responses. The few that read the
real store are marked `network` and skipped unless --network is passed, so a
normal run needs no connection.
"""

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "network: needs the rugbydata store, skipped by default"
    )


def pytest_addoption(parser):
    parser.addoption(
        "--network", action="store_true", default=False,
        help="run the tests that read from the rugbydata store",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--network"):
        return
    skip = pytest.mark.skip(reason="needs the store; pass --network to run")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)
