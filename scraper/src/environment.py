"""Explicit startup loading of local credentials; importing the package reads no files."""

from pathlib import Path

from dotenv import load_dotenv


def load_environment(env_file: str | Path | None = None, *, required: bool = False) -> bool:
    """Load one UTF-8 .env without replacing existing process environment values.

    The default is the working directory's .env, without searching parent directories.
    Library consumers can call this explicitly with their application's own path.
    """
    path = Path(env_file) if env_file is not None else Path.cwd() / ".env"
    if required and not path.is_file():
        raise FileNotFoundError(f"Environment file not found: {path}")
    return load_dotenv(dotenv_path=path, override=False, encoding="utf-8-sig")
