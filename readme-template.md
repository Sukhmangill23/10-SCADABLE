# Live SWOT
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
​
## Instructions
The current version is an interactive frontend prototype and does not yet include a backend or persistent data storage. The prototype can be accessed here: [Final Prototype](deliverables/D1/mockups/final-prototype.html).

Users can browse tracked competitors, search or filter the competitor list, open individual competitor profiles, view the SWOT overview, add a new competitor, and view sample AI research run information.
 
 ## Development requirements
The application is planned to use Next.js for the frontend, Python for the backend research workflows, and PostgreSQL for data storage. Additional tools for AI analysis, web retrieval, hosting, and deployment are still being evaluated by the team.
 
 ## Deployment and Github Workflow
​
Our team coordinates day-to-day development through Discord and GitHub. Before starting work, we discuss who is responsible for each task so that team members avoid working on the same files or features at the same time.

Each developer creates a separate branch for their work rather than committing directly to `main`. Once the work is ready, they open a pull request into `main` and another team member reviews it before it is merged. This gives us a chance to catch mistakes, discuss implementation choices, and keep `main` stable.

For larger features, we plan to divide work by area, such as frontend, backend/research workflow, database, and integration work, while still reviewing each other's pull requests. We also use Discord to notify the team when a pull request is ready or when a change may affect someone else's work.

Our deployment process and hosting tools have not been finalized yet. We will update this section once the team has agreed on the deployment setup.

We chose this workflow because our project has several connected components and seven team members, so clear ownership, separate branches, and peer review should reduce merge conflicts and make it easier to understand who changed what and why.

## Coding Standards and Guidelines

We will keep naming and file structure consistent with the part of the project being worked on, and avoid making unrelated changes in the same pull request. Each pull request should be small enough for another team member to review and understand before it is merged into `main`.

## Licenses

Our partner stated that he is comfortable with the team freely using and sharing the work created for this project, and did not request any additional confidentiality restrictions.

## Deployed URL / Access Instructions

The application has not been deployed yet. The current interactive prototype can be accessed here: [Final Prototype](deliverables/D1/mockups/final-prototype.html).
