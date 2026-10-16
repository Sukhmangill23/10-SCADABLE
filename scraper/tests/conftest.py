"""Confine SDK import caches to pytest's temporary directory; no live browser tests."""

import pytest


@pytest.fixture(autouse=True)
def sdk_cache_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("CRAWL4_AI_BASE_DIRECTORY", str(tmp_path))
