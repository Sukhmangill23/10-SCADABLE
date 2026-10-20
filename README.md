# Live SWOT


> _Note:_ This document is intended to be relatively short. Be concise and precise. Assume the reader has no prior knowledge of your application and is non-technical. 
​
## Partner Intro
Our partner is SCADABLE. Ali Rahbar is a co-founder and our primary contact (a.rahbar@scadable.com), and he led our kickoff call. Hossein Molavi is also a co-founder (h.molavi@scadable.com) and was cc'd on scheduling. We haven't confirmed a secondary point of contact yet.

SCADABLE is an AI compliance company. They help startups and small and medium-sized businesses 
handle SOC 2 and HIPAA compliance automatically using AI agents, so they can pass audits 
and sell to bigger customers without spending hundreds of hours doing the work manually.

## Description about the project
SCADABLE tracks competitors manually today, which is slow and easy to fall behind on. 
Live SWOT automates this by researching competitors and organizing the findings into a 
live SWOT analysis, so the founders and sales team can quickly see how they compare and 
answer competitor questions without doing the research themselves.
​
## Key Features
Live SWOT will allow users to add and track competitors, view individual competitor profiles, compare relevant competitive signals, and view an overall SWOT analysis. Competitor research will refresh on a regular schedule and highlight new or changed information.

The system will also include internal monitoring for automated research runs, including run status, cost, workflow steps, and cache usage to help reduce unnecessary repeated AI processing.

SCADABLE's own product features will be stored in a connected GitHub repository. When the feature file changes, a webhook will notify the backend so the updated product information can be used in future competitor comparisons and SWOT evaluations.
​
## Instructions
The current version is an interactive frontend prototype and does not yet include a backend or persistent data storage. The prototype can be accessed here: [Final Prototype](https://csc301-2026-f.github.io/10-SCADABLE/deliverables/D1/mockups/final-prototype.html)

Users can browse tracked competitors, search or filter the competitor list, open individual competitor profiles, view the SWOT overview, add a new competitor, view sample AI research run information, and view the connected GitHub product feature source and its latest sync status.
 
## Development requirements
The application is planned to use Next.js for the frontend, Python for the backend research workflows, and PostgreSQL for data storage. The system will also integrate with GitHub through a GitHub App and webhook to track changes to SCADABLE's product feature file. Additional tools for AI analysis, web retrieval, hosting, and deployment are still being evaluated by the team.
 
## Deployment and Github Workflow
​
Our team coordinates day-to-day development through Discord and GitHub. Before starting work, we discuss who is responsible for each task so that team members avoid working on the same files or features at the same time.

Each developer creates a separate branch for their work rather than committing directly to `main`. Once the work is ready, they open a pull request into `main` and another team member reviews it before it is merged. This gives us a chance to catch mistakes, discuss implementation choices, and keep `main` stable.

For larger features, we plan to divide work by area, such as frontend, backend/research workflow, database, and integration work, while still reviewing each other's pull requests. We also use Discord to notify the team when a pull request is ready or when a change may affect someone else's work.

Our deployment process and hosting tools have not been finalized yet. We will update this section once the team has agreed on the deployment setup.

We chose this workflow because our project has several connected components and seven team members, so clear ownership, separate branches, and peer review should reduce merge conflicts and make it easier to understand who changed what and why.

## Coding Standards and Guidelines

We will keep naming and file structure consistent with the part of the project being worked on, and avoid making unrelated changes in the same pull request. Each pull request should be small enough for another team member to review and understand before it is merged into `main`.

## Python research scaffold

This is the initial scraping and LLM foundation. Crawling, cleaning, extraction,
analysis, and comparison methods deliberately raise `NotImplementedError`.
The OpenAI wrapper is usable independently, but the pipeline is not yet a working
research application. There is no API server, database, scheduler, or frontend integration.

### Setup

Use Python 3.12 from the repository root. Install both local packages into the same
environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ./scraper -e ".[dev]"
Copy-Item .env.example .env
python -m pytest
python -m pytest -c scraper/pyproject.toml scraper/tests
```

On macOS/Linux, activate with `source .venv/bin/activate` and copy the environment
file with `cp .env.example .env`.

Core dependencies are the local scraper package, Pydantic for typed contracts,
pydantic-settings for environment configuration, and OpenAI SDK 3.x, shared with the
scraper's Decisions adapter. Development dependencies are pytest, pytest-asyncio for
the scraper's async tests, and httpx2 for offline SDK transport tests. The scraper
continues to use httpx for its own HTTP requests.

The combined environment installs the scraper as a regular local package; reinstall
`./scraper` after changing its source. Its standalone editable development workflow is
documented in [scraper/README.md](scraper/README.md). No browser installation is needed
for offline tests; real crawling requires Chromium as described in that guide.

### Structure and contracts

| Location | Responsibility |
| --- | --- |
| `src/config.py` | `Settings`: environment variables and optional local `.env` |
| `src/models/crawl_result.py` | `CompetitorURL`, `ScrapedContent`, and `CrawlResult` |
| `src/crawling/base.py` | Async `BaseCrawler.crawl()` contract |
| `src/crawling/firecrawl.py`, `crawl4ai.py` | Independent provider placeholders |
| `src/crawling/manager.py` | `create_crawler(settings)` provider selection |
| `src/processing/cleaner.py` | `clean_content(page)` placeholder |
| `src/llm/client.py` | Reusable async OpenAI client and structured-output helper |
| `src/llm/schemas.py` | Extraction, company analysis, comparison, and SWOT contracts |
| `src/llm/prompts/` | Placeholder instructions by task |
| `src/llm/analyzer.py` | Extraction, competitor, SCADABLE, and comparison placeholders |
| `src/pipeline.py` | `run_pipeline()` component wiring |
| `tests/` | Offline configuration, model, provider, SDK, and pipeline checks |

The editable install makes modules importable as `crawling`, `llm`, `models`,
`processing`, `config`, and `pipeline`; `src` is the source directory, not an import prefix.

Set `CRAWLER_PROVIDER` to `firecrawl` (default) or `crawl4ai`. Provider selection
does not start a crawl. `FIRECRAWL_API_KEY` is reserved for its future adapter.
`OPENAI_API_KEY` and `OPENAI_MODEL` must be nonempty when constructing
`OpenAIClient`; select a model supporting Responses API structured outputs.
`OPENAI_TIMEOUT_SECONDS` defaults to 30. Environment variables override `.env`.
Importing modules or running tests requires no real credentials.

The wrapper follows the official
[Responses API structured-output interface](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
Calling `generate_structured()` explicitly makes an API request; analyzer
placeholders do not call it yet. Close the client with `await client.close()`
after use, including when a component raises an error.
Crawler URLs are validated as HTTP URLs. LLM output source URLs use plain strings
to avoid unsupported URI format constraints in structured-output schemas.

### Pipeline and next steps

The skeleton passes data through:

```text
CompetitorURL → crawler.crawl() → CrawlResult.pages → clean_content()
             → AnalysisInput → extract_information() → ExtractedInformation
             → analyze_competitor() → CompanyAnalysis
```

Construct components with `Settings()`, `create_crawler(settings)`, and
`Analyzer(OpenAIClient(settings))`, then call
`await run_pipeline(competitor, crawler=crawler, analyzer=analyzer)`.
This currently stops at the crawler's `NotImplementedError`. The pipeline accepts
components explicitly so each module can be implemented and verified independently.
Tests substitute offline components to check the handoffs without implementing
production scraping or analysis.

Next, team members can implement either adapter and add its SDK dependency,
implement content cleaning, refine schemas and prompts, and connect analyzer
methods to the wrapper. Agree on traversal limits, extraction criteria,
missing-content handling, and comparison requirements before implementing those TODOs.

## Licenses

Our partner stated that he is comfortable with the team freely using and sharing the work created for this project, and did not request any additional confidentiality restrictions.

## Deployed URL / Access Instructions

The application has not been deployed yet. The current interactive prototype can be accessed here: [Final Prototype](https://csc301-2026-f.github.io/10-SCADABLE/deliverables/D1/mockups/final-prototype.html).
