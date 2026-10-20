"""Check the per-feature competition score and its place in the company prompt."""

import pytest
from pydantic import ValidationError

from llm.prompts.competitor import COMPANY_SYSTEM_PROMPT
from llm.schemas import CompanyAnalysis, FeatureScore


@pytest.mark.parametrize("bad", [-1, 11])
def test_score_outside_zero_to_ten_is_rejected(bad):
    with pytest.raises(ValidationError):
        FeatureScore(feature="Evidence collection", score=bad)


@pytest.mark.parametrize("ok", [0, 5, 10])
def test_scores_from_zero_to_ten_are_accepted(ok):
    assert FeatureScore(feature="Evidence collection", score=ok).score == ok


def test_score_schema_has_no_numeric_limits_for_openai_strict_mode():
    flat = str(FeatureScore.model_json_schema()["properties"]["score"])
    assert "minimum" not in flat and "maximum" not in flat


def test_company_analysis_carries_feature_scores():
    analysis = CompanyAnalysis(
        company_name="Acme",
        summary="s",
        claims_cited=[],
        scores=[FeatureScore(feature="Auto remediation", score=8)],
    )
    assert analysis.scores[0].feature == "Auto remediation"


def test_company_prompt_explains_the_scoring():
    assert "SCORING_CRITERIA" in COMPANY_SYSTEM_PROMPT
    assert "FEATURE_SCORE" in COMPANY_SYSTEM_PROMPT
    assert "<<" not in COMPANY_SYSTEM_PROMPT
