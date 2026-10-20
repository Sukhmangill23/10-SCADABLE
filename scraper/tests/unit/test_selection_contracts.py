from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scraper.config import ScraperConfig, SelectionConfig, resolve_config
from scraper.decision_models import CandidateObservation, DecisionCandidate, PageAssessment
from scraper.models import FetchedPage


def test_selection_defaults_are_llm_with_a_three_cent_allowance():
    selection = ScraperConfig().selection
    assert selection.mode == "llm"
    assert selection.model == "gpt-6-luna"
    assert selection.budget_usd == 0.03
    assert selection.exploration_fraction == 0.2
    assert selection.trace_enabled is False
    assert selection.timeout_seconds == 15
    assert selection.max_retries == 2
    assert selection.max_concurrency == 2
    assert "company" in selection.objective


def test_partial_nested_selection_overrides_survive_round_trip():
    global_settings = ScraperConfig(selection={"budget_usd": 0.01, "timeout_seconds": 8})
    competitor = ScraperConfig(selection={"trace_enabled": True})
    cli = ScraperConfig(selection={"mode": "structural"})
    restored = ScraperConfig.model_validate_json(competitor.model_dump_json(exclude_unset=True))
    settings = resolve_config(global_settings, restored, cli)
    assert settings.selection.mode == "structural"
    assert settings.selection.budget_usd == 0.01
    assert settings.selection.timeout_seconds == 8
    assert settings.selection.trace_enabled is True
    assert global_settings.selection.trace_enabled is False


@pytest.mark.parametrize(
    "patch",
    [
        {"mode": "keywords"},
        {"model": "unsupported"},
        {"budget_usd": -0.01},
        {"budget_usd": float("inf")},
        {"budget_usd": True},
        {"exploration_fraction": -0.1},
        {"exploration_fraction": 1.1},
        {"trace_enabled": "true"},
        {"timeout_seconds": 0},
        {"max_retries": -1},
        {"max_concurrency": 0},
        {"max_concurrency": True},
        {"objective": " "},
        {"objective": "a" * 4001},
        {"api_key": "do-not-serialize-secrets"},
    ],
)
def test_invalid_selection_settings_are_rejected(patch):
    with pytest.raises(ValidationError):
        SelectionConfig.model_validate(patch)


def test_zero_budget_and_exploration_endpoints_are_valid():
    assert SelectionConfig(budget_usd=0.0, exploration_fraction=0.0).budget_usd == 0
    assert SelectionConfig(exploration_fraction=1.0).exploration_fraction == 1


def test_observations_are_bounded_and_candidates_use_registered_ids():
    observation = CandidateObservation(
        anchor_text="Meet Atlas",
        heading="Contract review",
        surrounding_text="Review contracts.",
        location="main_content",
        parent_url="https://example.com/",
    )
    candidate = DecisionCandidate(
        candidate_id="link_017", url="https://example.com/atlas", observations=[observation]
    )
    assert candidate.observations[0].heading == "Contract review"
    with pytest.raises(ValidationError):
        CandidateObservation(anchor_text="x" * 161)
    with pytest.raises(ValidationError):
        DecisionCandidate(
            candidate_id="link_017", url=candidate.url, observations=[observation] * 3
        )
    with pytest.raises(ValidationError):
        DecisionCandidate(candidate_id="ignore instructions", url=candidate.url)


def test_page_content_can_carry_a_typed_assessment_without_losing_markdown():
    assessment = PageAssessment(usefulness=0.9, novelty=0.7, category="products")
    page = FetchedPage(
        source_url="https://example.com/atlas",
        crawl_timestamp=datetime.now(UTC),
        crawl_status="success",
        raw_markdown="# Atlas\nFull source content.",
        content_assessment=assessment,
    )
    restored = FetchedPage.model_validate_json(page.model_dump_json())
    assert restored.content_assessment.category == "products"
    assert restored.raw_markdown == page.raw_markdown
    with pytest.raises(ValidationError):
        PageAssessment(usefulness=float("nan"))
