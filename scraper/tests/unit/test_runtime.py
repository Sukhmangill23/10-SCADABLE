import os

import pytest


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "llm").mkdir()
    scraper = tmp_path / "scraper"
    scraper.mkdir()
    (scraper / "pyproject.toml").touch()
    monkeypatch.chdir(scraper)
    monkeypatch.delenv("CRAWL4_AI_BASE_DIRECTORY", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    return scraper


def test_checkout_runtime_reuses_manual_runner_browser_cache(checkout):
    from scraper.runtime import configure_runtime

    browsers = checkout / ".uv-cache/playwright"
    browsers.mkdir(parents=True)
    configure_runtime()
    assert os.environ["CRAWL4_AI_BASE_DIRECTORY"] == str(checkout / ".uv-cache")
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(browsers)


def test_runtime_keeps_explicit_host_cache_configuration(checkout, monkeypatch):
    from scraper.runtime import configure_runtime

    (checkout / ".uv-cache/playwright").mkdir(parents=True)
    monkeypatch.setenv("CRAWL4_AI_BASE_DIRECTORY", "custom-sdk")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "custom-browsers")
    configure_runtime()
    assert os.environ["CRAWL4_AI_BASE_DIRECTORY"] == "custom-sdk"
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == "custom-browsers"


def test_runtime_does_not_select_an_uninstalled_local_browser_cache(checkout):
    from scraper.runtime import configure_runtime

    configure_runtime()
    assert "PLAYWRIGHT_BROWSERS_PATH" not in os.environ


def test_standalone_runtime_keeps_sdk_defaults(tmp_path, monkeypatch):
    from scraper import runtime

    monkeypatch.setattr(runtime, "default_env_file", lambda: tmp_path / ".env")
    monkeypatch.delenv("CRAWL4_AI_BASE_DIRECTORY", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    runtime.configure_runtime()
    assert "CRAWL4_AI_BASE_DIRECTORY" not in os.environ
    assert "PLAYWRIGHT_BROWSERS_PATH" not in os.environ
