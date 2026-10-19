"""Output validation: citation checks, evidence status, and run-to-run changes."""

import re
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit

VALID_CATEGORIES = ("strength", "weakness", "opportunity", "threat")
# Finding had "confirmed" status but none of its citations were crawled URLs.
UNVERIFIED = "unverified"


def normalize_url(url: str) -> str:
    """Normalize a URL for citation matching (case, fragment, trailing slash)."""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower() or "https", host, path, parts.query, ""))


def build_url_index(urls: Iterable[str]) -> dict[str, str]:
    """Map normalized URL -> original crawled URL."""
    return {normalize_url(u): u for u in urls if u and u.strip()}


def filter_citations(
    cited: Iterable[str],
    url_index: Mapping[str, str],
) -> tuple[list[str], list[str]]:
    """Split citations into (valid crawled URLs, dropped hallucinated URLs)."""
    valid: list[str] = []
    dropped: list[str] = []
    for url in cited:
        if not isinstance(url, str) or not url.strip():
            continue
        match = url_index.get(normalize_url(url))
        if match is None:
            dropped.append(url)
        elif match not in valid:
            valid.append(match)
    return valid, dropped


def validate_findings(
    findings: Iterable[Mapping[str, Any]],
    url_index: Mapping[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate SWOT findings against the crawled URLs.

    - Drops citations that were not crawled and records a warning.
    - Downgrades a "confirmed" finding with no surviving citation to "unverified".
    - Discards findings with an unknown category or empty content.
    """
    validated: list[dict[str, Any]] = []
    warnings: list[str] = []
    for finding in findings:
        category = str(finding.get("category", "")).lower()
        content = str(finding.get("content", "")).strip()
        if category not in VALID_CATEGORIES or not content:
            warnings.append(f"Discarded malformed finding: {category!r}")
            continue

        valid, dropped = filter_citations(finding.get("source_urls") or [], url_index)
        if dropped:
            warnings.append(f"Dropped uncrawled citation(s) {dropped} from {category} finding.")

        status = finding.get("status", "confirmed")
        if status == "confirmed" and not valid:
            status = UNVERIFIED
            warnings.append(f"{category} finding has no valid citation; marked unverified.")

        validated.append(
            {"category": category, "content": content, "status": status, "source_urls": valid}
        )
    return validated, warnings


def to_swot_entries(findings: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Convert findings to the orchestrator's ``swot_entries`` shape.

    Keeps the original ``{category, content, source_url}`` keys; ``status`` and
    ``source_urls`` are additive and ignored by the current repository layer.
    """
    return [
        {
            "category": f["category"],
            "content": f["content"],
            "source_url": f["source_urls"][0] if f.get("source_urls") else None,
            "source_urls": list(f.get("source_urls") or []),
            "status": f.get("status", "confirmed"),
        }
        for f in findings
    ]


def _finding_key(entry: Mapping[str, Any]) -> tuple[str, str]:
    text = re.sub(r"[^a-z0-9 ]+", "", str(entry.get("content", "")).lower())
    return str(entry.get("category", "")).lower(), re.sub(r"\s+", " ", text).strip()


def compute_swot_changes(
    previous_entries: Iterable[Mapping[str, Any]] | None,
    current_entries: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare SWOT entries with the previous run.

    Matching is by category plus normalized content text. Returns lists of
    ``added``, ``removed`` and ``unchanged`` entries plus counts.
    """
    current = list(current_entries)
    if previous_entries is None:
        return {
            "has_previous": False,
            "added": current,
            "removed": [],
            "unchanged": [],
            "counts": {"added": len(current), "removed": 0, "unchanged": 0},
        }

    previous = list(previous_entries)
    prev_keys = {_finding_key(e) for e in previous}
    curr_keys = {_finding_key(e) for e in current}
    added = [e for e in current if _finding_key(e) not in prev_keys]
    unchanged = [e for e in current if _finding_key(e) in prev_keys]
    removed = [e for e in previous if _finding_key(e) not in curr_keys]
    return {
        "has_previous": True,
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "counts": {"added": len(added), "removed": len(removed), "unchanged": len(unchanged)},
    }
