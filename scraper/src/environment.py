"""Explicit startup loading of local credentials; importing the package reads no files."""

from pathlib import Path

from dotenv import load_dotenv


def default_env_file() -> Path:
    """Find the shared checkout .env; standalone installations use the working directory."""
    working_directory = Path.cwd()
    for start in (working_directory, Path(__file__).resolve().parent):
        for directory in (start, *start.parents):
            if (
                (directory / "pyproject.toml").is_file()
                and (directory / "scraper" / "pyproject.toml").is_file()
                and (directory / "llm").is_dir()
            ):
                return directory / ".env"
    return working_directory / ".env"


def load_environment(env_file: str | Path | None = None, *, required: bool = False) -> bool:
    """Load one UTF-8 .env without replacing existing process environment values.

    In this checkout the default is the repository-root .env, shared with LLM analysis.
    Standalone installations outside a checkout use the working directory's .env.
    Library consumers can call this explicitly with their application's own path.
    """
    path = Path(env_file) if env_file is not None else default_env_file()
    if required and not path.is_file():
        raise FileNotFoundError(f"Environment file not found: {path}")
    return load_dotenv(dotenv_path=path, override=False, encoding="utf-8-sig")
