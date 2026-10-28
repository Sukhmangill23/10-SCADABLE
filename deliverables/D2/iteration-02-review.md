# Team 10 – Niche

## Iteration 02 – Review & Retrospect

 * When: Thursday, October 22, 2026, 4:00–4:30 PM
 * Where: Online via Google Meet

## Process - Reflection


#### Q1. What worked well

1. **Discord server and rooms for backend, scraper/llm, and frontend**: This is our mode of communication. Questions reached the right people without cluttering the other subteams' channels. For example, if there was an issue that was only relevant to the backend, it was in the backend channel so other teammates could focus on their tasks. This also avoids the issue of everyone talking over one another in a single chat room.

 2. **Agreeing on interfaces first and building using mocks, so subteams didn't block each other**: For example, the frontend used mock data, and the backend used mock crawler and analyzer fallbacks. This allowed us to build in parallel so that we weren't constantly waiting on each. Everything was connected with real data at the end. This meant we always had something to do and no time was wasted. It also gave us a stable demo when the live deployment was risky or down. For example, even though Railway (our cloud provider) was down for a few days, we could still show much of our work.

 3. **Feature branches with PRs, including multiple commits with messages**: This allows main branch's history to be clean and readable, so bugs are caught before they reach main. For example, Sukhman found a bug in an import in PR [#23](https://github.com/csc301-2026-f/10-SCADABLE/pull/23), and this was fixed before being pushed to main. This allows our main branch to always be functional.

 4. **GitHub project table that links to issues and pull requests**: It let us see who owned each task and what was still open. Splitting it by deliverable kept us focused on what was due. Linked PRs show who built each component, which also helps TAs see who did what. [Table](https://github.com/orgs/csc301-2026-f/projects/20)


### Q2. What did not work well

- **Late integration between components:** Although our team made progress developing the frontend, backend, scraper, and LLM independently, we integrated these components too close to the deadline. This left us with limited time to identify and resolve issues between different parts of the application. For example, we encountered problems with frontend-backend communication that required additional debugging. In future iterations, we plan to integrate components earlier and more frequently to identify compatibility issues before the final stages of development.

- **Deployment planning and unexpected delays:** Our backend deployment was significantly disrupted by an unexpected Railway outage, which prevented us from deploying and testing the application as planned. Since we were relying on Railway for our deployed backend and had scheduled integration testing close to the deadline, the outage delayed our progress and affected our ability to demonstrate a fully working application to our partner. Moving forward, we plan to deploy earlier in the iteration to allow more time for troubleshooting unexpected infrastructure issues.

- **Insufficient end-to-end testing:** While individual components were being developed and tested, we did not test the complete scraper-to-LLM-to-database-to-frontend workflow early enough. As a result, we discovered issues such as invalid LLM citation URLs and frontend API configuration problems during the later stages of integration. These required additional debugging and slowed down our progress toward a reliable application. In future iterations, we plan to test complete user workflows more regularly rather than relying primarily on individual component tests.


#### Q3(a). Planned changes

List any **process-related** (i.e. team organization and/or how you work) changes you are planning to make (if there are any)

 * Prioritizing integration testing: helps every assignee understand what can be improved on sooner, exposes any hidden vulnerabilities.
 * Increasing weekly team meetings: have 1-2 meetings a week (one must be within 1 day before the tutorial) to share updates, answer questions, provide design decision changes, and anything else related to the project work. This should allow clarity on the state of the project and allows teams to understand how to change their design or integrate other modules.
 * Using Jira kanban board: gives visibility to all team members of tasks based on their assignee, details, status. Holds people accountable for their work and can increase productivity.

#### Q3(b). Integration & Next steps
Briefly explain how you integrated the previously developed individuals components as one product (i.e. How did you split the work across your team) and how was the work integrated together.

 * Keep this very short (1-3 lines).

We split into three subteams — frontend, backend, and LLM/scraping — and each built its part largely in parallel. Integration meant connecting the frontend to the backend APIs, and the backend to the scraper/LLM pipeline for research runs, SWOT, and findings, then debugging the full flow once those pieces were ready.


## Product - Review

#### Q4. How was your product demo?

**Preparation:** We planned to demo the deployed app, but Railway was down on the day, so we ran the frontend locally as a fallback.

**What we demoed:** The frontend dashboard: the competitor list, adding a competitor, competitor profiles, the SWOT analysis view, and the agent runs page.

**Partner feedback:** Our partner liked the product and accepted the features. He requested the following changes and additions:
- Show the SWOT in a traditional 2×2 grid and remove the extra subheadings under each category.
- Show more relevant information directly on the page, using dropdowns for details, instead of relying on external links.
- Show more detail about each agent run.
- Let users define custom tracking criteria (e.g. funding, projects, company developments) and how to score them, configurable through GitHub config files or a frontend settings tab.
- Scrape competitor job postings to infer what projects they are working on.
- Schedule weekly automated agent runs to keep the analysis up to date.

**Learnings:**
- Process: Deploy and test the full system well before the demo, and always have a local fallback ready. Railway going down meant we could only show the frontend.
- Product: The partner values configurability (choosing what gets tracked and how it is scored) and having information visible at a glance over raw links. This will shape our next iteration.
