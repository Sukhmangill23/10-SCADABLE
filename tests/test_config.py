"""Analysis settings honor an explicit dotenv file and process overrides."""

import os
import subprocess
import sys

import pytest

from llm.config import Settings


def test_settings_load_dotenv_and_environment_override(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=offline-file-key\nOPENAI_MODEL=file-model\nOPENAI_TIMEOUT_SECONDS=12.5\n",
        encoding="utf-8",
    )
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_TIMEOUT_SECONDS",
        "PYTHON_DOTENV_DISABLED",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=env_file)
    assert settings.openai_api_key.get_secret_value() == "offline-file-key"
    assert settings.openai_model == "file-model"
    assert settings.openai_timeout_seconds == 12.5

    monkeypatch.setenv("OPENAI_MODEL", "environment-model")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "7.5")
    overridden = Settings(_env_file=env_file)
    assert overridden.openai_model == "environment-model"
    assert overridden.openai_timeout_seconds == 7.5


@pytest.mark.parametrize("process_override", [False, True])
def test_both_layers_load_shared_root_dotenv_from_nested_directory(
    tmp_path, process_override
):
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "llm").mkdir()
    scraper = tmp_path / "scraper"
    scraper.mkdir()
    (scraper / "pyproject.toml").touch()
    nested = scraper / "nested"
    nested.mkdir()
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=root-fixture-key\nOPENAI_MODEL=root-model\n",
        encoding="utf-8-sig",
    )
    (scraper / ".env").write_text("OPENAI_API_KEY=obsolete-key\n", encoding="utf-8")
    (nested / ".env").write_text("OPENAI_API_KEY=wrong-key\n", encoding="utf-8")
    environment = dict(os.environ)
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "PYTHON_DOTENV_DISABLED"):
        environment.pop(name, None)
    expected = "process-key" if process_override else "root-fixture-key"
    if process_override:
        environment["OPENAI_API_KEY"] = expected
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            (
                "import os; from llm.config import Settings; "
                "from scraper.environment import load_environment; "
                "settings = Settings(); "
                f"assert settings.openai_api_key.get_secret_value() == {expected!r}; "
                "assert settings.openai_model == 'root-model'; "
                "load_environment(); "
                f"assert os.environ['OPENAI_API_KEY'] == {expected!r}"
            ),
        ],
        check=False,
        cwd=nested,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
