"""Analysis settings honor an explicit dotenv file and process overrides."""

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
