# Team 10 – Niche

## Iteration 02 – Review & Retrospect

 * When: Thursday, October 22, 2026, 4:00–4:30 PM
 * Where: Online via Google Meet

## Process - Reflection


#### Q1. What worked well

List **process-related** (i.e. team organization and how you work) decisions and actions that worked well.


 * 2 - 4 important decisions, processes, actions, or anything else that worked well for you, ordered from most to least important.
 * Give a supporting argument about what makes you think that way.
 * Feel free to refer/link to process artifact(s).
### Q2. What did not work well

- **Late integration between components:** Although our team made progress developing the frontend, backend, scraper, and LLM independently, we integrated these components too close to the deadline. This left us with limited time to identify and resolve issues between different parts of the application. For example, we encountered problems with frontend-backend communication that required additional debugging. In future iterations, we plan to integrate components earlier and more frequently to identify compatibility issues before the final stages of development.

- **Deployment planning and unexpected delays:** Our backend deployment was significantly disrupted by an unexpected Railway outage, which prevented us from deploying and testing the application as planned. Since we were relying on Railway for our deployed backend and had scheduled integration testing close to the deadline, the outage delayed our progress and affected our ability to demonstrate a fully working application to our partner. Moving forward, we plan to deploy earlier in the iteration to allow more time for troubleshooting unexpected infrastructure issues.

- **Insufficient end-to-end testing:** While individual components were being developed and tested, we did not test the complete scraper-to-LLM-to-database-to-frontend workflow early enough. As a result, we discovered issues such as invalid LLM citation URLs and frontend API configuration problems during the later stages of integration. These required additional debugging and slowed down our progress toward a reliable application. In future iterations, we plan to test complete user workflows more regularly rather than relying primarily on individual component tests.


#### Q3(a). Planned changes

List any **process-related** (i.e. team organization and/or how you work) changes you are planning to make (if there are any)

 * Ordered from most to least important, with supporting argument explaining a change.

#### Q3(b). Integration & Next steps
Briefly explain how you integrated the previously developed individuals components as one product (i.e. How did you split the work across your team) and how was the work integrated together.

 * Keep this very short (1-3 lines).


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
