
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

test_url = os.getenv("TEST_DATABASE_URL")

if not test_url:
    pytest.skip("PostgreSQL test database not configured", allow_module_level=True)

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
from app.db.models import ResearchStatus, SWOTCategory, SWOTScope
from app.db.repository import (
    DuplicateCompetitorError,
    InvalidStatusTransitionError,
    NotFoundError,
    create_competitor,
    create_research_run,
    delete_competitor,
    get_competitor,
    get_competitor_by_url,
    get_latest_research_run,
    get_latest_swot,
    get_overall_swot,
    get_research_run,
    list_competitors,
    replace_overall_swot,
    save_analysis_result,
    save_scraped_data,
    save_swot_entries,
    update_research_run_status,
)


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
    return create_competitor(
        db,
        name="Vanta",
        website_url="https://vanta.com",
    )


def test_create_competitor(db):
    competitor = create_competitor(
        db,
        name="Drata",
        website_url="https://drata.com",
    )

    assert competitor.id is not None
    assert competitor.name == "Drata"
    assert competitor.normalized_url == "drata.com"

    saved = get_competitor(db, competitor.id)

    assert saved is not None
    assert saved.website_url == "https://drata.com"


def test_duplicate_competitor(db, competitor):
    with pytest.raises(DuplicateCompetitorError):
        create_competitor(
            db,
            name="Vanta Duplicate",
            website_url="https://www.vanta.com/pricing",
        )

    assert get_competitor(db, competitor.id) is not None


def test_get_competitor_by_url(db, competitor):
    found = get_competitor_by_url(
        db,
        "http://www.vanta.com/features",
    )

    assert found is not None
    assert found.id == competitor.id


def test_list_competitors(db):
    create_competitor(db, "Vanta", "https://vanta.com")
    create_competitor(db, "Drata", "https://drata.com")

    competitors = list_competitors(db)

    assert len(competitors) == 2


def test_delete_competitor(db, competitor):
    assert delete_competitor(db, competitor.id) is True
    assert get_competitor(db, competitor.id) is None
    assert delete_competitor(db, competitor.id) is False


def test_create_research_run(db, competitor):
    run = create_research_run(db, competitor.id)

    assert run.id is not None
    assert run.competitor_id == competitor.id
    assert run.status == ResearchStatus.PENDING

    assert get_research_run(db, run.id).id == run.id
    assert get_latest_research_run(db, competitor.id).id == run.id


def test_research_run_invalid_competitor(db):
    with pytest.raises(NotFoundError):
        create_research_run(db, competitor_id=999999)


def test_research_run_status(db, competitor):
    run = create_research_run(db, competitor.id)

    run = update_research_run_status(
        db, run.id, ResearchStatus.RUNNING
    )

    assert run.status == ResearchStatus.RUNNING
    assert run.started_at is not None

    run = update_research_run_status(
        db, run.id, ResearchStatus.COMPLETED
    )

    assert run.status == ResearchStatus.COMPLETED
    assert run.completed_at is not None


def test_invalid_status_transition(db, competitor):
    run = create_research_run(db, competitor.id)

    with pytest.raises(InvalidStatusTransitionError):
        update_research_run_status(
            db, run.id, ResearchStatus.COMPLETED
        )


def test_save_scraped_data(db, competitor):
    run = create_research_run(db, competitor.id)

    scraped = {
        "provider": "crawl4ai",
        "pages": [
            {
                "url": "https://vanta.com",
                "title": "Vanta",
                "text": "Automated compliance platform",
            }
        ],
    }

    save_scraped_data(db, run.id, scraped)

    saved_run = get_research_run(db, run.id)

    assert saved_run.scraped_data == scraped


def test_save_analysis_result(db, competitor):
    run = create_research_run(db, competitor.id)

    analysis = {
        "company_name": "Vanta",
        "strengths": ["Automated compliance"],
        "weaknesses": ["Limited customization"],
    }

    save_analysis_result(db, run.id, analysis)

    saved_run = get_research_run(db, run.id)

    assert saved_run.analysis_result == analysis


def test_save_competitor_swot(db, competitor):
    run = create_research_run(db, competitor.id)

    entries = [
        {
            "category": "strength",
            "content": "Strong automation capabilities",
            "source_url": "https://vanta.com",
        },
        {
            "category": "weakness",
            "content": "Limited customization",
        },
    ]

    saved = save_swot_entries(db, run.id, entries)

    assert len(saved) == 2
    assert saved[0].scope == SWOTScope.COMPETITOR

    update_research_run_status(
        db, run.id, ResearchStatus.RUNNING
    )
    update_research_run_status(
        db, run.id, ResearchStatus.COMPLETED
    )

    latest = get_latest_swot(db, competitor.id)

    assert len(latest) == 2
    assert latest[0].category == SWOTCategory.STRENGTH


def test_swot_replacement(db, competitor):
    run = create_research_run(db, competitor.id)

    save_swot_entries(
        db,
        run.id,
        [{"category": "strength", "content": "Old finding"}],
    )

    replaced = save_swot_entries(
        db,
        run.id,
        [{"category": "opportunity", "content": "New finding"}],
    )

    assert len(replaced) == 1
    assert replaced[0].content == "New finding"


def test_overall_swot(db):
    entries = [
        {
            "category": "strength",
            "content": "SCADABLE offers AI-driven compliance",
        },
        {
            "category": "opportunity",
            "content": "Growing compliance automation market",
        },
    ]

    replace_overall_swot(db, entries)

    saved = get_overall_swot(db)

    assert len(saved) == 2
    assert all(entry.scope == SWOTScope.OVERALL for entry in saved)
    assert all(entry.competitor_id is None for entry in saved)


def test_retry_clears_previous_results(db, competitor):
    run = create_research_run(db, competitor.id)

    update_research_run_status(
        db, run.id, ResearchStatus.RUNNING
    )

    save_scraped_data(db, run.id, {"pages": ["old data"]})

    save_swot_entries(
        db,
        run.id,
        [{"category": "strength", "content": "Old result"}],
    )

    update_research_run_status(
        db, run.id, ResearchStatus.FAILED
    )

    retried = update_research_run_status(
        db, run.id, ResearchStatus.PENDING
    )

    assert retried.started_at is None
    assert retried.completed_at is None
    assert retried.error_message is None
    assert retried.scraped_data is None
    assert retried.swot_entries == []
