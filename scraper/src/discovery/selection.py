"""Coordinate bounded decision cycles and feedback without owning fetch resources."""

from ..config import ScraperConfig
from ..decision_models import SelectionDiagnostics
from ..interfaces import DecisionProvider
from ..models import DiscoveredUrl, FetchedPage
from .evidence import EvidenceLedger
from .traversal import UrlFrontier


class AdaptiveSelection:
    def __init__(self, frontier: UrlFrontier, settings: ScraperConfig, provider: DecisionProvider):
        self.frontier, self.settings, self.provider = frontier, settings, provider
        self.ledger = EvidenceLedger()
        self._last_evaluation_attempt = -5

    def _mode(self):
        mode = self.provider.summary.effective_mode
        self.frontier.set_mode(mode)
        return mode

    async def rank_if_needed() -> None:
        if self._mode() != "llm" or self.settings.strategy == "bfs":
            return
        if self.frontier.attempted_pages >= self.settings.max_pages:
            return
        if self.frontier.attempted_pages - self._last_evaluation_attempt < 5 and (
            self.frontier.has_scored_candidates
        ):
            return
        candidates = self.frontier.evaluation_candidates()
        if candidates:
            scores = await self.provider.score_candidates(candidates)
            self.frontier.apply_scores(candidates, scores)
            self._mode()
        self._last_evaluation_attempt = self.frontier.attempted_pages

    @property
    def evaluation_due(self) -> bool:
        """Finish a fetch batch at a scoring boundary, never reorder work in flight."""
        return (
            self._mode() == "llm"
            and self.settings.strategy == "best_first"
            and (
                self.frontier.attempted_pages - self._last_evaluation_attempt >= 5
                or not self.frontier.has_scored_candidates
            )
        )

    @staticmethod
    def attach(page: FetchedPage, record: DiscoveredUrl) -> FetchedPage:
        assessment = page.content_assessment
        available = assessment is not None and any(
            value is not None
            for value in (
                assessment.usefulness,
                assessment.novelty,
                assessment.category_confidence,
            )
        )
        return page.model_copy(
            update={
                "selection": SelectionDiagnostics(
                    method=record.selection_method,
                    relevance_score=record.relevance_score,
                    assessment_available=available,
                )
            }
        )

    async def assess(self, page: FetchedPage, record: DiscoveredUrl) -> FetchedPage:
        if page.crawl_status == "success" and self._mode() == "llm":
            assessment = await self.provider.assess_content(page, self.ledger.excerpts)
            page = page.model_copy(update={"content_assessment": assessment})
            self.frontier.note_assessment(str(record.normalized_url), assessment)
            self.ledger.add(page)
            self._mode()
        return self.attach(page, record)
