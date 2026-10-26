# D2 Individual Contributions

### Sukhmandeep Gill

**Role:** Database development, backend deployment, and testing.

**Contributions:**
- Implemented the PostgreSQL database and data persistence layer.
- Configured and deployed the backend on Railway using Docker.
- Developed backend integration tests for database operations and the research pipeline.
- Tested and debugged backend integration issues.

<<<<<<< HEAD
### Jaynik Sheth
=======
### Jaynik Shah
>>>>>>> 389f6fb4cf581228d005cc7110bfdc015fa77c44

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