# D2 Individual Contributions

### Sukhmandeep Gill

**Role:** Database development, backend deployment, and testing.

**Contributions:**
- Implemented the PostgreSQL database and data persistence layer.
- Configured and deployed the backend on Railway using Docker.
- Developed backend integration tests for database operations and the research pipeline.
- Tested and debugged backend integration issues.

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
