"""SWOT endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import serializers
from app.api.schemas import ErrorResponse, Finding, SwotOverview
from app.db import repository as repo
from app.db.database import get_db

router = APIRouter(prefix="/swot", tags=["swot"])

_BUCKETS = {
    "strength": "strengths",
    "weakness": "weaknesses",
    "opportunity": "opportunities",
    "threat": "threats",
}


def _group(findings: list[Finding]) -> SwotOverview:
    buckets: dict[str, list[Finding]] = {name: [] for name in _BUCKETS.values()}
    for finding in findings:
        buckets[_BUCKETS[finding.category]].append(finding)
    return SwotOverview(
        updated_at=max((f.detected_at for f in findings), default=None),
        **buckets,
    )


def _overview_findings(db: Session) -> list[Finding]:
    """Overall SWOT when generated; otherwise each competitor's latest SWOT."""
    overall = repo.get_overall_swot(db)
    if overall:
        return [serializers.finding_from_entry(e, None) for e in overall]
    return [
        serializers.finding_from_entry(entry, competitor)
        for competitor in repo.list_competitors(db, limit=500)
        for entry in repo.get_latest_swot(db, competitor.id)
    ]


@router.get("", response_model=SwotOverview, responses={404: {"model": ErrorResponse}})
def get_swot(
    competitor_id: int | None = Query(None, alias="competitorId", ge=1),
    db: Session = Depends(get_db),
) -> SwotOverview:
    """SWOT grouped by category.

    With ``competitorId``: that competitor's latest SWOT. Without: the overview.
    """
    if competitor_id is None:
        return _group(_overview_findings(db))

    competitor = repo.get_competitor(db, competitor_id)
    if competitor is None:
        raise repo.NotFoundError(f"Competitor {competitor_id} not found.")
    return _group(
        [
            serializers.finding_from_entry(entry, competitor)
            for entry in repo.get_latest_swot(db, competitor.id)
        ]
    )


@router.get("/overview", response_model=SwotOverview)
def get_swot_overview(db: Session = Depends(get_db)) -> SwotOverview:
    """SCADABLE's overall SWOT (used by the frontend overview page)."""
    return _group(_overview_findings(db))
