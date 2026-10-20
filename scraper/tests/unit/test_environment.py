import os

import pytest


@pytest.fixture(autouse=True)
def isolated_dotenv(tmp_path, monkeypatch):
    import scraper.environment as environment

    # Simulate a standalone installation, outside the developer's real checkout.
    monkeypatch.setattr(environment, "__file__", str(tmp_path / "installed/scraper/environment.py"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Track dotenv's os.environ mutation so pytest restores the process afterwards.
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY")


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig"])
def test_loads_working_directory_dotenv_with_quotes_comments_and_windows_bom(tmp_path, encoding):
    from scraper.environment import load_environment

    (tmp_path / ".env").write_text('OPENAI_API_KEY="fixture-key" # comment\n', encoding=encoding)
    assert load_environment()
    assert os.environ["OPENAI_API_KEY"] == "fixture-key"


def test_existing_environment_has_precedence(tmp_path, monkeypatch):
    from scraper.environment import load_environment

    (tmp_path / ".env").write_text("OPENAI_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "existing-key")
    load_environment()
    assert os.environ["OPENAI_API_KEY"] == "existing-key"


def test_explicit_path_loads_from_another_directory(tmp_path, monkeypatch):
    from scraper.environment import load_environment

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    path = tmp_path / "custom.env"
    path.write_text("OPENAI_API_KEY=explicit-key\n", encoding="utf-8")
    load_environment(path, required=True)
    assert os.environ["OPENAI_API_KEY"] == "explicit-key"


def test_missing_default_file_is_optional_and_does_not_search_parents(tmp_path, monkeypatch):
    from scraper.environment import load_environment

    (tmp_path / ".env").write_text("OPENAI_API_KEY=parent-key\n", encoding="utf-8")
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.chdir(child)
    assert load_environment() is False
    assert "OPENAI_API_KEY" not in os.environ


def test_missing_explicit_file_has_actionable_error(tmp_path):
    from scraper.environment import load_environment

    with pytest.raises(FileNotFoundError, match="Environment file not found"):
        load_environment(tmp_path / "missing.env", required=True)


def test_checkout_uses_root_dotenv_instead_of_scraper_local_file(tmp_path, monkeypatch):
    from scraper.environment import load_environment

    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "llm").mkdir()
    scraper = tmp_path / "scraper"
    scraper.mkdir()
    (scraper / "pyproject.toml").touch()
    (scraper / ".env").write_text("OPENAI_API_KEY=obsolete-key\n", encoding="utf-8")
    monkeypatch.chdir(scraper)
    # A missing root file must not silently fall back to the old local file.
    assert load_environment() is False
    assert "OPENAI_API_KEY" not in os.environ
    (tmp_path / ".env").write_text("OPENAI_API_KEY=shared-key\n", encoding="utf-8")
    assert load_environment()
    assert os.environ["OPENAI_API_KEY"] == "shared-key"


def test_module_location_finds_checkout_when_launched_elsewhere(tmp_path, monkeypatch):
    import scraper.environment as environment

    root = tmp_path / "checkout"
    root.mkdir()
    (root / "pyproject.toml").touch()
    (root / "llm").mkdir()
    (root / "scraper").mkdir()
    (root / "scraper/pyproject.toml").touch()
    (root / ".env").write_text("OPENAI_API_KEY=module-root-key\n", encoding="utf-8")
    monkeypatch.setattr(environment, "__file__", str(root / "scraper/src/environment.py"))
    assert environment.load_environment()
    assert os.environ["OPENAI_API_KEY"] == "module-root-key"
