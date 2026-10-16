"""One auditable URL registry and deterministic BestFirst/BFS frontier per competitor."""

from collections.abc import Callable
from dataclasses import dataclass

from ..config import ScraperConfig
from ..models import DiscoveredUrl, DiscoveryEvidence
from ..types import DiscoverySource, UrlDisposition
from .relevance import UrlPolicy
from .urls import normalize_url

MAX_EVIDENCE_PER_URL = 8


@dataclass
class _Entry:
    record: DiscoveredUrl
    sequence: int
    title: str
    attempted: bool = False
    in_flight: bool = False


class UrlFrontier:
    def __init__(self, homepage: str, settings: ScraperConfig):
        self.settings = settings
        self.homepage = homepage
        self.policy = UrlPolicy(homepage, settings)
        self._entries: dict[str, _Entry] = {}
        self._children: dict[str, set[str]] = {}
        self.attempted_pages = 0
        self.invalid_links = 0
        self.truncated = False
        self.discover(homepage, depth=0, source="homepage", depth_basis="homepage")

    @property
    def records(self) -> list[DiscoveredUrl]:
        return [entry.record.model_copy(deep=True) for entry in self._entries.values()]

    def _replace(self, entry: _Entry, **changes) -> None:
        entry.record = DiscoveredUrl.model_validate({**entry.record.model_dump(), **changes})

    def _refresh_policy(self, entry: _Entry) -> None:
        if entry.attempted:
            return
        record = entry.record
        decision = self.policy.evaluate(
            str(record.normalized_url),
            title=entry.title,
            homepage=record.discovery_source == DiscoverySource.HOMEPAGE,
        )
        disposition, reason = decision.disposition, decision.reason
        if disposition == UrlDisposition.PENDING and record.depth > self.settings.max_depth:
            disposition, reason = UrlDisposition.DEFERRED, "depth_limit"
        self._replace(
            entry,
            disposition=disposition,
            reason=reason,
            relevance_score=max(record.relevance_score, decision.score),
        )

    def discover(
        self,
        raw_url: str,
        *,
        parent_url: str | None = None,
        depth: int = 1,
        source: str | DiscoverySource = DiscoverySource.INTERNAL_LINK,
        depth_basis: str = "link",
        title: str = "",
    ) -> DiscoveredUrl | None:
        normalized = normalize_url(raw_url, base_url=parent_url or self.homepage)
        if normalized is None:
            self.invalid_links += 1
            return None
        key = normalized.normalized
        entry = self._entries.get(key)
        if entry is None and len(self._entries) >= self.settings.max_discovered_urls:
            self.truncated = True
            return None
        parent = normalize_url(parent_url) if parent_url else None
        evidence = DiscoveryEvidence(
            observed_url=raw_url,
            discovery_source=source,
            parent_url=parent.absolute if parent else None,
            depth=depth,
            title=title,
        )
        if entry is None:
            record = DiscoveredUrl(
                url=normalized.absolute,
                normalized_url=key,
                discovery_source=source,
                parent_url=evidence.parent_url,
                depth=depth,
                depth_basis=depth_basis,
                evidence=[evidence],
            )
            entry = _Entry(record, len(self._entries), title)
            self._entries[key] = entry
        else:
            items = entry.record.evidence
            changes = {"discovery_count": entry.record.discovery_count + 1}
            if len(items) < MAX_EVIDENCE_PER_URL and evidence not in items:
                changes["evidence"] = [*items, evidence]
            if depth < entry.record.depth:
                changes.update(depth=depth, depth_basis=depth_basis, parent_url=evidence.parent_url)
            if title and self.policy.score(key, title) > self.policy.score(key, entry.title):
                entry.title = title
            self._replace(entry, **changes)
        if parent and parent.normalized in self._entries:
            self._children.setdefault(parent.normalized, set()).add(key)
        self._refresh_policy(entry)
        self._relax_descendants(key)
        return entry.record.model_copy(deep=True)

    def _relax_descendants(self, key: str) -> None:
        """Propagate shorter discovered paths without refetching already fetched pages."""
        pending = [key]
        while pending:
            parent_key = pending.pop()
            parent = self._entries[parent_key].record
            for child_key in sorted(self._children.get(parent_key, ())):
                child = self._entries[child_key]
                depth = parent.depth + 1
                if child.record.depth <= depth:
                    continue
                self._replace(
                    child, depth=depth, depth_basis="link", parent_url=parent.normalized_url
                )
                self._refresh_policy(child)
                pending.append(child_key)

    def pop_next(
        self, *, eligible: Callable[[DiscoveredUrl], bool] | None = None
    ) -> DiscoveredUrl | None:
        if self.attempted_pages >= self.settings.max_pages:
            return None

        def priority(entry):
            depth = entry.record.depth or 0
            value = (
                float(depth) if self.settings.strategy == "bfs" else -entry.record.relevance_score
            )
            if entry.record.discovery_source == DiscoverySource.HOMEPAGE:
                value = -2.0
            return value, depth, entry.sequence

        # With at most 5,000 records and 50 attempts, scanning the registry is small and
        # avoids an unbounded heap of stale entries when URLs are rediscovered repeatedly.
        candidates = (
            entry
            for entry in self._entries.values()
            if not entry.attempted
            and entry.record.disposition == UrlDisposition.PENDING
            and (eligible is None or eligible(entry.record))
        )
        entry = min(candidates, key=priority, default=None)
        if entry is None:
            return None
        entry.attempted = entry.in_flight = True
        self.attempted_pages += 1
        return entry.record.model_copy(deep=True)

    def get(self, url: str) -> DiscoveredUrl:
        normalized = normalize_url(url)
        if normalized is None or normalized.normalized not in self._entries:
            raise KeyError(url)
        return self._entries[normalized.normalized].record.model_copy(deep=True)

    def note_title(self, url: str, title: str) -> None:
        normalized = normalize_url(url)
        entry = self._entries[normalized.normalized]
        score = self.policy.score(normalized.normalized, title)
        if score > entry.record.relevance_score:
            entry.title = title
            self._replace(entry, relevance_score=score)

    def reject_reserved(self, url: str, *, reason: str, deferred: bool = False) -> None:
        """A preflight refusal is not a page fetch and releases its reserved page slot."""
        normalized = normalize_url(url)
        entry = self._entries[normalized.normalized]
        if not entry.in_flight:
            raise ValueError("Only a reserved URL can be rejected")
        entry.in_flight = False
        self.attempted_pages -= 1
        self._replace(
            entry,
            disposition=UrlDisposition.DEFERRED if deferred else UrlDisposition.SKIPPED,
            reason=reason,
        )

    def complete(self, url: str, *, success: bool, error: str | None = None) -> None:
        normalized = normalize_url(url)
        entry = self._entries.get(normalized.normalized if normalized else "")
        if entry is None or not entry.in_flight:
            raise ValueError("Only a reserved URL can be completed")
        entry.in_flight = False
        self._replace(
            entry,
            disposition=UrlDisposition.CRAWLED if success else UrlDisposition.FAILED,
            reason=None if success else (error or "fetch_failed"),
        )

    def finalize(self, *, reason: str | None = None) -> None:
        reason = reason or (
            "page_limit" if self.attempted_pages >= self.settings.max_pages else "not_crawled"
        )
        for entry in self._entries.values():
            if entry.record.disposition == UrlDisposition.PENDING and not entry.in_flight:
                self._replace(entry, disposition=UrlDisposition.DEFERRED, reason=reason)
