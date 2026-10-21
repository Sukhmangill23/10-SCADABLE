"""Real FastAPI -> background research -> PostgreSQL test; no network or OpenAI calls."""
import os
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL test database", allow_module_level=True)

url = make_url(TEST_DATABASE_URL)
if url.get_backend_name() != "postgresql" or not url.database.endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must be PostgreSQL and end with _test")
if os.environ.get("DATABASE_URL") != TEST_DATABASE_URL:
    raise RuntimeError("DATABASE_URL must match TEST_DATABASE_URL to prevent production writes")

from fastapi.testclient import TestClient  # noqa: E402
from app.db.database import Base, engine, SessionLocal  # noqa: E402
from app.db import models, repository  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services import orchestrator  # noqa: E402
from app.services.crawler import MockCrawl4AICrawler  # noqa: E402
from app.services.llm import MockOpenAIAnalyzer  # noqa: E402


def test_api_research_results_persist_to_postgres(monkeypatch):
    Base.metadata.create_all(engine)
    mock_crawler = MockCrawl4AICrawler()
    mock_llm = MockOpenAIAnalyzer()
    original_trigger = orchestrator.trigger_research_task

    def trigger_with_mock_research(competitor_id, background_tasks, db):
        return original_trigger(
            competitor_id, background_tasks, db,
            session_factory=SessionLocal,
            crawler=mock_crawler,
            analyzer=mock_llm,
        )

    monkeypatch.setattr(orchestrator, "trigger_research_task", trigger_with_mock_research)
    name = "Integration Test Company"
    website = f"https://integration-{uuid4().hex}.example"

    with TestClient(create_app()) as client:
        created = client.post("/competitors", json={"name": name, "dataSources": [website]})
        assert created.status_code == 201, created.text
        competitor_id = int(created.json()["competitor"]["id"])
        run_id = int(created.json()["queuedRunId"])
        try:
            run = client.get(f"/runs/{run_id}")
            assert run.status_code == 200, run.text
            assert run.json()["status"] == "success", run.json()

            profile = client.get(f"/competitors/{competitor_id}")
            assert profile.status_code == 200, profile.text
            assert profile.json()["researchStatus"] == "success"
            categories = {f["category"] for f in profile.json()["findings"]}
            assert categories == {"strength", "weakness", "opportunity", "threat"}

            with SessionLocal() as db:
                saved = repository.get_research_run(db, run_id)
                assert saved.status == models.ResearchStatus.COMPLETED
                assert len(saved.scraped_data["pages"]) >= 1
                assert len(saved.analysis_result["swot_entries"]) >= 4
                assert len(repository.get_latest_swot(db, competitor_id)) >= 4

            # Subsequent research preserves history; identical content should skip LLM.
            rerun = client.post(f"/competitors/{competitor_id}/rerun")
            assert rerun.status_code == 202, rerun.text
            runs = client.get(f"/runs?competitorId={competitor_id}").json()
            assert len(runs) == 2
            assert all(r["status"] == "success" for r in runs)
            with SessionLocal() as db:
                latest = repository.get_latest_research_run(db, competitor_id)
                assert latest.id != run_id
                assert latest.analysis_result["skipped_llm"] is True
                assert repository.get_research_run(db, run_id).status == models.ResearchStatus.COMPLETED
        finally:
            assert client.delete(f"/competitors/{competitor_id}").status_code == 204
