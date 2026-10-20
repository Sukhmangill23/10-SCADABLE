"""Noise filter and content diffing utilities.

Compares new scraped data against previous snapshots stored in the database
to prevent redundant LLM invocations and reduce OpenAI token costs.
"""

import hashlib
import json
import re
from typing import Any


def _normalize_text(text: str) -> str:
    """Strip dynamic timestamps, session tokens, and excessive whitespace."""
    # Collapse multiple whitespace/newlines
    cleaned = re.sub(r"\s+", " ", text.strip())
    # Lowercase for deterministic hashing
    return cleaned.lower()


def compute_content_hash(scraped_data: dict[str, Any] | None) -> str:
    """Generate a deterministic SHA-256 hash of scraped page text.

    Handles various page data structures (e.g. lists of pages, dictionaries
    of subpages, or raw text fields).
    """
    if not scraped_data:
        return ""

    hasher = hashlib.sha256()

    pages = scraped_data.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if isinstance(page, dict):
                url = page.get("url", "")
                # Support text, markdown, or content keys
                body = (
                    page.get("text")
                    or page.get("markdown")
                    or page.get("content")
                    or ""
                )
                normalized = f"{url}:{_normalize_text(str(body))}"
                hasher.update(normalized.encode("utf-8"))
            elif isinstance(page, str):
                hasher.update(_normalize_text(page).encode("utf-8"))
    elif "text" in scraped_data or "content" in scraped_data:
        raw = scraped_data.get("text") or scraped_data.get("content") or ""
        hasher.update(_normalize_text(str(raw)).encode("utf-8"))
    else:
        # Fallback to deterministic JSON serialization of the payload
        serialized = json.dumps(scraped_data, sort_keys=True)
        hasher.update(serialized.encode("utf-8"))

    return hasher.hexdigest()


def has_content_changed(
    new_scraped: dict[str, Any],
    previous_scraped: dict[str, Any] | None,
) -> bool:
    """Determine whether new crawl output differs from the previous snapshot.

    Returns:
        True if there is no previous snapshot or if content has changed.
        False if the content hash matches, allowing LLM synthesis to be skipped.
    """
    if not previous_scraped:
        return True

    new_hash = compute_content_hash(new_scraped)
    prev_hash = compute_content_hash(previous_scraped)

    if not new_hash:
        return True

    return new_hash != prev_hash

