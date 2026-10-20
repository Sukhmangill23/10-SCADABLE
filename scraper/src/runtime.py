"""Explicit browser startup configuration shared by scripts and library consumers."""

import os
from pathlib import Path

from .environment import default_env_file


def configure_runtime(project_directory: Path | None = None) -> None:
    """Reuse checkout caches without overriding host-provided deployment settings.

    Run before importing Crawl4AI or starting Playwright. Outside this checkout,
    installed packages retain the SDK's normal cache locations.
    """
    if project_directory is None:
        project_directory = default_env_file().parent / "scraper"
        if not (project_directory / "pyproject.toml").is_file():
            return
    cache = project_directory / ".uv-cache"
    os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", str(cache))
    browsers = cache / "playwright"
    if browsers.is_dir():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers))
