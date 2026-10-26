# Your Team Number and Name

 > _Note:_ This document is meant to be written during (or shortly after) your review meeting, which should happen fairly close to the due date.      
 >      
 > _Suggestion:_ Have your review meeting a day or two before the due date. This way you will have some time to go over (and edit) this document, and all team members should have a chance to make their contribution.


## Iteration XX - Review & Retrospect

 * When: FILL IN THE DATE WHEN YOU ACTUALLY HAD YOUR REVIEW MEETING
 * Where: PHYSICAL LOCATION AND/OR ONLINE

## Process - Reflection


#### Q1. What worked well

List **process-related** (i.e. team organization and how you work) decisions and actions that worked well.


 * 2 - 4 important decisions, processes, actions, or anything else that worked well for you, ordered from most to least important.
 * Give a supporting argument about what makes you think that way.
 * Feel free to refer/link to process artifact(s).

#### Q2. What did not work well

List **process-related** (i.e. team organization and how you work) decisions and actions that did not work well.

 * 2 - 4 important decisions, processes, actions, or anything else that did not work well for you, ordered from most to least important.
 * Give a supporting argument about what makes you think that way.
 * Feel free to refer/link to process artifact(s).


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
