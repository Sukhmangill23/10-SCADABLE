"""Version fingerprints and the analysis cache key.

Person 3 stores ``versions["cache_key"]`` with each analysis and calls
``is_cache_valid`` before re-running the LLM.
"""

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from app.llm.prompts import PROMPT_VERSION
from app.services.diff import compute_content_hash


def compute_baseline_version(baseline: Mapping[str, Any]) -> str:
    """Deterministic short hash of SCADABLE's baseline profile."""
    serialized = json.dumps(baseline, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def build_cache_key(
    input_fingerprint: str,
    prompt_version: str,
    baseline_version: str,
    model: str,
) -> str:
    """Build a deterministic cache key from everything that affects the output."""
    payload = json.dumps(
        {
            "input": input_fingerprint,
            "prompt": prompt_version,
            "baseline": baseline_version,
            "model": model,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_versions(
    scraped_data: Mapping[str, Any],
    baseline: Mapping[str, Any],
    model: str,
) -> dict[str, str]:
    """Return the ``versions`` block, including the cache key."""
    fingerprint = compute_content_hash(dict(scraped_data))
    baseline_version = compute_baseline_version(baseline)
    return {
        "prompt_version": PROMPT_VERSION,
        "baseline_version": baseline_version,
        "model": model,
        "input_fingerprint": fingerprint,
        "cache_key": build_cache_key(fingerprint, PROMPT_VERSION, baseline_version, model),
    }


def is_cache_valid(
    cached_result: Mapping[str, Any] | None,
    scraped_data: Mapping[str, Any],
    baseline: Mapping[str, Any],
    model: str,
) -> bool:
    """Return True when a stored analysis can be reused for this input.

    Mock results are never considered valid cache entries.
    """
    if not cached_result or cached_result.get("analysis_mode") != "real":
        return False
    cached_versions = cached_result.get("versions") or {}
    current = build_versions(scraped_data, baseline, model)
    return bool(cached_versions.get("cache_key")) and (
        cached_versions.get("cache_key") == current["cache_key"]
    )
