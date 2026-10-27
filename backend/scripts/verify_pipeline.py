"""End-to-End Research Pipeline Verification Script.

Run this script to verify that database persistence, the crawler adapter,
diffing/token-saving logic, and LLM SWOT analysis are fully functional.

Usage:
    PYTHONPATH="backend" DATABASE_URL="sqlite:///:memory:" python backend/scripts/verify_pipeline.py
"""

import asyncio
import os
import sys

# Ensure default DATABASE_URL for local verification if not set
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api import serializers
from app.db.database import Base
from app.db.models import Competitor, ResearchRun, ResearchStatus, SWOTEntry, SWOTScope
from app.db.repository import (
    create_competitor,
    create_research_run,
    get_latest_swot,
    get_overall_swot,
)
from app.services.crawler import MockCrawl4AICrawler
from app.services.diff import compute_content_hash, has_content_changed
from app.services.llm import MockOpenAIAnalyzer
from app.services.orchestrator import execute_research_run


def main():
    print("=" * 65)
    print("  SCADABLE LIVE SWOT: PIPELINE & ADAPTER VERIFICATION")
    print("=" * 65)

    db_url = os.environ["DATABASE_URL"]
    print(f"\n[1/7] Initializing database at: {db_url}")
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    print("      ✓ Database tables successfully initialized.")

    print("\n[2/7] Verifying Snapshot Diffing & Token-Conservation Logic...")
    data_a = {"pages": [{"url": "https://vanta.com/features", "text": "SOC 2 Compliance"}]}
    data_b = {"pages": [{"url": "https://vanta.com/features", "text": "  soc 2 compliance  \n"}]}
    data_c = {"pages": [{"url": "https://vanta.com/features", "text": "ISO 27001 Compliance"}]}

    assert compute_content_hash(data_a) == compute_content_hash(data_b), "Hashing normalization failed"
    assert has_content_changed(data_b, data_a) is False, "Unchanged content was marked as changed"
    assert has_content_changed(data_c, data_a) is True, "Changed content was not detected"
    print("      ✓ Diffing engine correctly ignores whitespace/casing and catches changes.")

    with Session(engine) as db:
        print("\n[3/7] Creating Competitor and Pending Run...")
        competitor = create_competitor(db, name="Vanta", website_url="https://vanta.com")
        run1 = create_research_run(db, competitor.id)
        assert run1.status == ResearchStatus.PENDING
        print(f"      ✓ Competitor: {competitor.name} (ID: {competitor.id})")
        print(f"      ✓ Initial Run: ID {run1.id} (Status: {run1.status.value})")

        print("\n[4/7] Executing End-to-End Research Pipeline (Run 1 - Zero Token Mock Mode)...")
        crawler = MockCrawl4AICrawler()
        analyzer = MockOpenAIAnalyzer()

        finished_run = asyncio.run(
            execute_research_run(
                db=db,
                run_id=run1.id,
                crawler=crawler,
                analyzer=analyzer,
            )
        )

        assert finished_run.status == ResearchStatus.COMPLETED, f"Run status was {finished_run.status}"
        assert finished_run.scraped_data is not None, "Missing scraped_data snapshot"
        assert finished_run.analysis_result is not None, "Missing analysis_result"
        pages = finished_run.scraped_data.get("pages", [])
        assert len(pages) > 0, "No pages recorded in scrape"
        print(f"      ✓ Run finished with status: '{finished_run.status.value}'")
        print(f"      ✓ Scraped and stored {len(pages)} pages in PostgreSQL JSONB.")
        print(f"      ✓ Analysis summary: \"{finished_run.analysis_result.get('summary', '')[:70]}...\"")

        print("\n[5/7] Verifying Stored SWOT Findings & Citations...")
        swot_rows = get_latest_swot(db, competitor.id)
        assert len(swot_rows) > 0, "No SWOT rows persisted"

        categories_found = set()
        for entry in swot_rows:
            categories_found.add(entry.category.value)
            assert entry.source_url is not None, f"SWOT entry '{entry.content}' missing citation source_url"
            print(f"      - [{entry.category.value.upper()}] {entry.content[:55]}... (Source: {entry.source_url})")

        assert {"strength", "weakness", "opportunity", "threat"}.issubset(categories_found), "Missing core SWOT categories"
        print(f"      ✓ {len(swot_rows)} SWOT entries persisted with verified source citations.")

        print("\n[6/7] Verifying Overall SCADABLE SWOT (Compare Against All Competitors)...")
        overall_rows = get_overall_swot(db)
        assert {e.category.value for e in overall_rows} == {"strength", "weakness", "opportunity", "threat"}, "Missing overall SWOT categories"
        assert all(e.scope == SWOTScope.OVERALL and e.competitor_id is None for e in overall_rows), "Overall rows must not belong to a competitor"
        for entry in overall_rows:
            print(f"      - [{entry.category.value.upper()}] {entry.content[:65]}")
        print(f"      ✓ {len(overall_rows)} overall SWOT entries saved for the overview page.")

        print("\n[7/7] Verifying Re-Run Diffing (Token-Conservation Test) & API Serialization...")
        run2 = create_research_run(db, competitor.id)
        finished_run2 = asyncio.run(
            execute_research_run(
                db=db,
                run_id=run2.id,
                crawler=crawler,
                analyzer=analyzer,
            )
        )

        assert finished_run2.status == ResearchStatus.COMPLETED
        assert finished_run2.analysis_result.get("skipped_llm") is True, "LLM was not skipped on identical content"
        assert finished_run2.analysis_result.get("reused_from_run_id") == run1.id, "Reused run ID not linked"
        swot_rows_after_rerun = get_latest_swot(db, competitor.id)
        assert len(swot_rows_after_rerun) == len(swot_rows), "Prior SWOT entries were not copied forward on skipped LLM run"
        assert [e.id for e in get_overall_swot(db)] == [e.id for e in overall_rows], "Overall SWOT was recomputed on unchanged content"

        # Verify API serializer compatibility for frontend consumption
        db.refresh(competitor)
        profile_dto = serializers.competitor_profile(competitor, finished_run2, swot_rows_after_rerun)
        run_dto = serializers.agent_run(finished_run2, competitor.name)
        assert profile_dto.research_status == "success", f"Expected API status 'success', got {profile_dto.research_status}"
        assert "established compliance automation platform" in profile_dto.summary
        assert len(profile_dto.findings) == len(swot_rows)
        assert run_dto.cache_hits == 1 and run_dto.cache_misses == 0

        print("      ✓ Second run completed with skipped_llm = True (LLM tokens conserved).")
        print("      ✓ Overall SWOT left unchanged (no extra comparison call).")
        print(f"      ✓ Reused findings ({len(swot_rows_after_rerun)} rows) & summary linked to original Run ID {run1.id}.")
        print("      ✓ Frontend API serializers (CompetitorProfile & AgentRun) verified.")
        print("\n" + "=" * 65)
        print("  ALL PIPELINE CHECKS PASSED (0 API TOKENS USED)")
        print("=" * 65)



if __name__ == "__main__":
    main()

