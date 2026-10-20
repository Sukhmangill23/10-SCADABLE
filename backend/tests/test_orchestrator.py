"""Tests for research workflow orchestration, change detection, and task execution."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from starlette.datastructures import State

from app.db.models import ResearchStatus, SWOTCategory, SWOTScope
from app.db.repository import (
    create_competitor,
    create_research_run,
    get_latest_swot,
    get_research_run,
)
from app.services.crawler import MockCrawl4AICrawler
from app.services.diff import compute_content_hash, has_content_changed
from app.services.llm import MockOpenAIAnalyzer
from app.services.orchestrator import execute_research_run, trigger_research_task


# ---------------------------------------------------------------------------
# Unit Tests for Diffing and Mock Services (Run anywhere without a database)
# ---------------------------------------------------------------------------

def test_compute_content_hash():
    data1 = {
        "pages": [
            {"url": "https://vanta.com/features", "text": "Continuous Automated Evidence"},
            {"url": "https://vanta.com/pricing", "text": "Starting at $7500/year"},
        ]
    }
    # Same content with different casing and whitespace should yield identical hash
    data2 = {
        "pages": [
            {"url": "https://vanta.com/features", "text": "  continuous   automated evidence  \n"},
            {"url": "https://vanta.com/pricing", "text": "starting at $7500/year  "},
        ]
    }
    data3 = {
        "pages": [
            {"url": "https://vanta.com/features", "text": "Continuous Automated Evidence"},
            {"url": "https://vanta.com/pricing", "text": "Starting at $10,000/year"},
        ]
    }

    assert compute_content_hash(data1) == compute_content_hash(data2)
    assert compute_content_hash(data1) != compute_content_hash(data3)
    assert compute_content_hash(None) == ""


def test_has_content_changed():
    initial_scrape = {
        "pages": [
            {"url": "https://drata.com/features", "text": "Real-time compliance monitoring"},
        ]
    }
    same_scrape = {
        "pages": [
            {"url": "https://drata.com/features", "text": "  Real-time compliance monitoring  "},
        ]
    }
    updated_scrape = {
        "pages": [
            {"url": "https://drata.com/features", "text": "Real-time compliance monitoring with AI"},
        ]
    }

    # Initial crawl has no prior snapshot: should register as changed
    assert has_content_changed(initial_scrape, None) is True
    # Unchanged content: should register as unchanged (skip LLM)
    assert has_content_changed(same_scrape, initial_scrape) is False
    # Modified content: should register as changed
    assert has_content_changed(updated_scrape, initial_scrape) is True


import asyncio

def test_mock_crawler():
    crawler = MockCrawl4AICrawler()
    result = asyncio.run(crawler.crawl("Vanta", "https://vanta.com"))

    assert result["competitor_name"] == "Vanta"
    assert len(result["pages"]) == 3
    urls = [p["url"] for p in result["pages"]]
    assert "https://vanta.com/features" in urls
    assert "https://vanta.com/pricing" in urls
    assert "https://vanta.com/docs" in urls


def test_mock_analyzer():
    analyzer = MockOpenAIAnalyzer()
    scraped = {
        "competitor_name": "Drata",
        "base_url": "https://drata.com",
    }
    result = asyncio.run(analyzer.analyze(scraped, {"baseline": "SCADABLE"}))

    assert result["competitor_name"] == "Drata"
    entries = result["swot_entries"]
    assert len(entries) >= 4
    categories = {e["category"] for e in entries}
    assert {"strength", "weakness", "opportunity", "threat"}.issubset(categories)
    for entry in entries:
        assert entry["source_url"].startswith("https://drata.com")


# ---------------------------------------------------------------------------
# Integration Tests requiring PostgreSQL test database
# ---------------------------------------------------------------------------

test_url = os.getenv("TEST_DATABASE_URL")

if test_url:
    if test_url.startswith("postgres://"):
        test_url = test_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif test_url.startswith("postgresql://"):
        test_url = test_url.replace("postgresql://", "postgresql+psycopg://", 1)

    parsed_url = make_url(test_url)
    if (
        parsed_url.get_backend_name() != "postgresql"
        or not parsed_url.database
        or not parsed_url.database.endswith("_test")
    ):
        raise RuntimeError("Tests require a PostgreSQL database ending in _test.")

    os.environ["DATABASE_URL"] = test_url
    from app.db.database import Base

    @pytest.fixture(scope="session")
    def engine():
        test_engine = create_engine(test_url, pool_pre_ping=True)
        Base.metadata.create_all(test_engine)
        yield test_engine
        test_engine.dispose()

    @pytest.fixture
    def db(engine):
        connection = engine.connect()
        transaction = connection.begin()
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.close()

    @pytest.fixture
    def competitor(db):
        return create_competitor(db, name="Vanta", website_url="https://vanta.com")

    def test_execute_research_run_success(db, competitor):
        run = create_research_run(db, competitor.id)
        assert run.status == ResearchStatus.PENDING

        crawler = MockCrawl4AICrawler()
        analyzer = MockOpenAIAnalyzer()

        finished_run = asyncio.run(execute_research_run(
            db=db,
            run_id=run.id,
            crawler=crawler,
            analyzer=analyzer,
        ))

        assert finished_run.status == ResearchStatus.COMPLETED
        assert finished_run.started_at is not None
        assert finished_run.completed_at is not None
        assert finished_run.error_message is None
        assert finished_run.scraped_data is not None
        assert finished_run.analysis_result is not None

        # Verify SWOT entries were persisted to DB with source URLs
        swot_rows = get_latest_swot(db, competitor.id)
        assert len(swot_rows) > 0
        for entry in swot_rows:
            assert entry.source_url is not None
            assert entry.source_url.startswith("https://vanta.com")

    def test_execute_research_run_diff_skips_llm(db, competitor):
        crawler = MockCrawl4AICrawler()
        analyzer = MockOpenAIAnalyzer()

        # Run 1: initial run, should call LLM
        run1 = create_research_run(db, competitor.id)
        res1 = asyncio.run(execute_research_run(db, run1.id, crawler, analyzer))
        assert res1.status == ResearchStatus.COMPLETED

        # Run 2: content has not changed, should skip LLM
        run2 = create_research_run(db, competitor.id)
        res2 = asyncio.run(execute_research_run(db, run2.id, crawler, analyzer))

        assert res2.status == ResearchStatus.COMPLETED
        assert res2.analysis_result.get("skipped_llm") is True
        assert res2.analysis_result.get("reused_from_run_id") == run1.id

    def test_execute_research_run_crawler_failure(db, competitor):
        run = create_research_run(db, competitor.id)
        failing_crawler = MockCrawl4AICrawler(should_fail=True)

        failed_run = asyncio.run(execute_research_run(
            db=db,
            run_id=run.id,
            crawler=failing_crawler,
        ))

        assert failed_run.status == ResearchStatus.FAILED
        assert "simulated failure" in failed_run.error_message

    def test_execute_research_run_analyzer_failure(db, competitor):
        run = create_research_run(db, competitor.id)
        crawler = MockCrawl4AICrawler()
        failing_analyzer = MockOpenAIAnalyzer(should_fail=True)

        failed_run = asyncio.run(execute_research_run(
            db=db,
            run_id=run.id,
            crawler=crawler,
            analyzer=failing_analyzer,
        ))

        assert failed_run.status == ResearchStatus.FAILED
        assert "simulated failure" in failed_run.error_message
        # Scraped data must remain preserved even if LLM fails
        assert failed_run.scraped_data is not None

    def test_trigger_research_task(db, competitor):
        from fastapi import BackgroundTasks

        bg_tasks = BackgroundTasks()
        run = trigger_research_task(
            competitor_id=competitor.id,
            background_tasks=bg_tasks,
            db=db,
        )

        assert run.id is not None
        assert run.status == ResearchStatus.PENDING
        assert len(bg_tasks.tasks) == 1

