"""SWOT overview endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import serializers
from app.api.schemas import Finding, SwotOverview
from app.db import repository as repo
from app.db.database import get_db

router = APIRouter(prefix="/swot", tags=["swot"])

_BUCKETS = {
    "strength": "strengths",
    "weakness": "weaknesses",
    "opportunity": "opportunities",
    "threat": "threats",
}


@router.get("/overview", response_model=SwotOverview)
def get_swot_overview(db: Session = Depends(get_db)) -> SwotOverview:
    """SCADABLE's overall SWOT.

    Uses the "overall" SWOT when one has been generated; until then, combines
    each competitor's latest completed SWOT.
    """
    overall = repo.get_overall_swot(db)
    if overall:
        findings = [serializers.finding_from_entry(e, None) for e in overall]
    else:
        findings = [
            serializers.finding_from_entry(entry, competitor)
            for competitor in repo.list_competitors(db, limit=500)
            for entry in repo.get_latest_swot(db, competitor.id)
        ]

    buckets: dict[str, list[Finding]] = {name: [] for name in _BUCKETS.values()}
    for finding in findings:
        buckets[_BUCKETS[finding.category]].append(finding)

    return SwotOverview(
        updated_at=max((f.detected_at for f in findings), default=None),
        **buckets,
    )
