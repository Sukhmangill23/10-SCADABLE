# D2 Individual Contributions

### Sukhmandeep Gill

**Role:** Database development, backend deployment, integration testing, and documentation.

**Contributions:**
- Implemented PostgreSQL database integration and persistent data storage.
- Configured Docker for Railway deployment (**PR #27**) and independently managed backend deployment.
- Developed FastAPI/PostgreSQL integration tests (**PR #28**) and an end-to-end backend research integration test (**PR #29**).
- Assisted with frontend deployment on Vercel and integration with the Railway backend.
- Tested the deployed application, identified issues with feature scoring, SWOT citations, and competitor management, and coordinated fixes with teammates.
- Comprehensively updated the D2 README, documenting application features, setup instructions, deployment, limitations, and screenshots.
- Contributed to the D2 iteration retrospective and team documentation.

### Jaynik Sheth

**Role:** Scraper development and research pipeline integration.

**Contributions:**

- Designed and implemented the entire Crawl4AI scraper end to end(`scraper` and `scraper-decisions-api` branch; [PR #11](https://github.com/csc301-2026-f/10-SCADABLE/pull/11)).
- Connected the scraper and LLM layers(`d2_scraping-llm` branch; [PR #18](https://github.com/csc301-2026-f/10-SCADABLE/pull/18)).
- Created architecture and setup plus manual research-run examples to support connecting the pipeline to the FastAPI backend (`d2_backend-scraper-llm` branch; [PR #20](https://github.com/csc301-2026-f/10-SCADABLE/pull/20)).
- Coordinated and led the partner meeting to demo, gather feedback, discuss future improvements and took meeting notes

### Essam Elmancy

**Role:** Backend API development, request validation, and containerization.

**Contributions:**
- Designed and implemented the FastAPI endpoints the frontend uses to add, view, delete, and re-run research on competitors, and to view research runs, SWOT findings, and SCADABLE's company profile (`essam_d2_backend` branch, merged through `d2_backend`; [PR #17](https://github.com/csc301-2026-f/10-SCADABLE/pull/17)).
- Built Pydantic request/response schemas matching the frontend's API types, with input validation, consistent error formatting and HTTP status codes (404, 409, 422, 500), and CORS configuration.
- Wrote the backend Dockerfile and 38 API tests, and tested the full API end to end against PostgreSQL in Docker.
- Reviewed the Railway deployment Dockerfile and fixed a bug where the crawler silently fell back to mock data inside the container (`fix/railway-deployment` branch).
- Documented the API endpoints and local setup in the backend README.

### Ibraheem Hussain

**Role:** Frontend development (Next.js app shell, auth, competitors, and agent runs).

**Contributions:**
- Scaffolded the Next.js frontend (`frontend/base`) with App Router, design tokens, AppShell navigation, typed `lib/api` client, and mock fixtures so frontend work could proceed before the backend was ready ([PR #25](https://github.com/csc301-2026-f/10-SCADABLE/pull/25)).
- Implemented Clerk authentication: invite-only sign-in, protected routes, and a local “Go to dashboard” bypass when Clerk keys are missing.
- Built the competitors list and profiles: search/filters, add-competitor modal, delete with confirmation, research-status banner, Recharts visuals, and links to the latest successful agent run ([PR #10](https://github.com/csc301-2026-f/10-SCADABLE/pull/10)).
- Built the Agent Runs page (weekly summary cards, latest-run table, expandable steps/failure detail) and added polling while research is pending or running ([PR #26](https://github.com/csc301-2026-f/10-SCADABLE/pull/26), [PR #32](https://github.com/csc301-2026-f/10-SCADABLE/pull/32)).


### Houssam Yaacoub

**Role:** Research pipeline orchestration, scraper/LLM backend integration, and verification.

**Contributions:**
- Built the background research orchestrator that runs each competitor's research, tracks run status (pending, running, completed, failed), and handles timeouts and errors while keeping earlier results (`orchestrator.py`) [PR #17](https://github.com/csc301-2026-f/10-SCADABLE/pull/17).
- Implemented change detection that hashes scraped pages and skips the OpenAI call when a competitor's website hasn't changed, reusing the previous SWOT findings and summary to save tokens (`diff.py`) [PR #17](https://github.com/csc301-2026-f/10-SCADABLE/pull/17).
- Connected the Crawl4AI scraper and OpenAI analyzer to the backend through adapters with mock fallbacks, and added SCADABLE's static baseline profile used in the analysis (`crawler.py`, `llm.py`, `baseline.py`; `backend/wire-orchestrator-adapters` branch) [PR #23](https://github.com/csc301-2026-f/10-SCADABLE/pull/23).
- Fixed adapter bugs that made the backend silently fall back to mock data, including a wrong `CrawlSummary` import and invalid page validation (`backend/wire-orchestrator-adapters` branch). Fixed in [PR #23](https://github.com/csc301-2026-f/10-SCADABLE/pull/23) and merged to main in [PR #24](https://github.com/csc301-2026-f/10-SCADABLE/pull/24).
- Added an overall SWOT step that compares SCADABLE against all researched competitors with one LLM call and saves it for the overview page (`backend/d2_swot_pipline` branch) [PR #38](https://github.com/csc301-2026-f/10-SCADABLE/pull/38).
- Wrote the orchestrator unit tests and a zero-token end-to-end verification script for the pipeline (`test_orchestrator.py`, `verify_pipeline.py`) [PR #17](https://github.com/csc301-2026-f/10-SCADABLE/pull/17), [PR #23](https://github.com/csc301-2026-f/10-SCADABLE/pull/23).
- Set up the GitHub Projects board, which tracks tasks, issues, and pull requests for each deliverable [Link](https://github.com/orgs/csc301-2026-f/projects/20).

## Saad Qureshi

**Role:** Frontend development (SWOT overview and Our Company pages), Vercel deployment, demo planning, and team coordination.

**Contributions:**

- Built the SWOT Overview page, which displays SCADABLE's overall SWOT against its researched competitors (`feat/swot-overview` branch; [PR #21](https://github.com/csc301-2026-f/10-SCADABLE/pull/21)).
- Built the Our Company page, which shows SCADABLE's company profile and baseline used in the analysis (`feat/company` branch; [PR #22](https://github.com/csc301-2026-f/10-SCADABLE/pull/22)).
- Deployed the Next.js frontend to Vercel, giving the team and partner a live, shareable URL for the demo and feedback.
- Designed the demo flow and coordinated the preparation of the presentation slides.
- Coordinated the team across frontend and backend work, keeping task ownership, integration timing, and deliverable requirements on track.

## Yash Khanchandani
**Role**: AI Agent for data extraction, company analysis, and SWOT analysis, and testing

**Contributions:**
- Built the LLM agent to extract the key data from the company websites of SCADABLE and its competitors (see `llm/analyzer.py`), analyze each company's data to spot all their strengths, weaknesses, improvements or declines in the workforce, and finally compile each company's analysis into a fully-supported SWOT analysis.
- Optimized user and system prompt as well as output schemas (`llm/schemas.py`) for the LLM to:
    - Prevent repetition of data between prompt and responses.
    - Use numerical indexing for each citation rather than copying the URL text for citation, reducing chances of made-up citations.
- Introduced prompt caching to each API call to increase the cache hits and reduce API call costs, reaching up to 26% cache hit across the data extraction and company analysis (SWOT analysis not included).
- Added job analytics into SWOT after discussing with Ali (SCADABLE founder) which I don't think was mentioned earlier.
- Discussed future optimizations with the team to reduce API costs (one of them being website diff tracking to provide only the changed section of an already-scraped website so less tokens are consumed on inputs).
- Updated `research-pipeline.md` to reflect the new flow of logic for how the data extraction, company analysis, and SWOT analysis, is conducted.
- Adjusted the base testcases to reflect the updated AI Agent prompting logic.

