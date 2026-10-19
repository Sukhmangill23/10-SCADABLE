"""SCADABLE company profile endpoint (static baseline for D2)."""

from fastapi import APIRouter

from app.api.schemas import CompanyProfile, GithubStatus
from app.core.baseline import get_scadable_baseline

router = APIRouter(prefix="/company", tags=["company"])


@router.get("", response_model=CompanyProfile)
def get_company_profile() -> CompanyProfile:
    baseline = get_scadable_baseline()
    frameworks = baseline.get("supported_frameworks", [])
    offerings = list(baseline.get("core_capabilities", []))
    if frameworks:
        offerings.insert(0, "Frameworks: " + ", ".join(frameworks))
    return CompanyProfile(
        offerings=offerings,
        positioning_notes=list(baseline.get("differentiators", [])),
        github=GithubStatus(
            connected=False,
            repository=None,
            tracked_file=None,
            status_label="Static profile (GitHub sync not connected yet)",
            last_synced_at=None,
            recent_change=None,
        ),
    )
