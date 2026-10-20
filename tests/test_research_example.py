"""The example exposes both invocation modes without credentials at startup."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/research_pipeline.py"


@pytest.mark.parametrize(
    "args,code,expected",
    [
        (["--help"], 0, "--export"),
        ([], 2, "Provide homepage URLs or --export"),
        (["https://example.com/", "--export", "unused.json"], 2, "exclusively"),
    ],
)
def test_example_invocation_modes_without_api_requests(args, code, expected):
    environment = dict(os.environ, PYTHON_DOTENV_DISABLED="1")
    environment.pop("OPENAI_API_KEY", None)
    result = subprocess.run(
        [sys.executable, "-B", str(EXAMPLE), *args],
        check=False,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == code, result.stderr
    assert expected in result.stdout + result.stderr
