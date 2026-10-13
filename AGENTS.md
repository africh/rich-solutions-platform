# AGENTS.md

Operating rules for the autonomous agent team that builds the Rich Solutions Platform. Alex Rich is the principal operator. Agents keep no memory between runs: all shared state lives in Notion (Agent Team HQ) and in this repository.

## This repository is PUBLIC

Never commit client names, engagement details, pilot candidates, credentials, tokens, org IDs, or any other secret. Describe engagements generically (for example "a public-sector pilot"). If in doubt, leave it out and raise it in the Operator Inbox.

## Every run

1. Start by reading the Vision Brief and Agent Team HQ in Notion, this file, and the 3 newest Agent Handoff Log entries.
2. Touch only what your role owns (table below). Comment on other agents' items; never edit them.
3. Blocked, conflicting requirements, or a decision needed: create an Operator Inbox item (Status Open, From Agent = your role) and stop on that item.
4. Never merge, force-push, delete branches or pages, or sign up for paid services or external accounts. Only Alex sets an ADR to Approved.
5. End every run with exactly one Agent Handoff Log entry (Run = `<Role> - YYYY-MM-DD`, Outcome Progress / No change / Blocked / Failed). If Notion or GitHub is unreachable, still try to log Outcome = Failed with the exact error. If you cannot push, say so in the log and raise a Blocker in the Operator Inbox.

## Git workflow

- Branch: `agent/<role>/<story-id>`, e.g. `agent/technical-architect/SB-2`. Role slugs: `project-manager`, `business-analyst`, `enterprise-architect`, `technical-architect`, `developer`, `qa-reviewer`, `resource-manager`.
- Open a PR to `main` using the PR template; link the Sprint Board story in the description and put the PR URL in the story's PR Link.
- Only Alex merges to `main`. No force-push. No branch deletion.
- Keep `python build.py` working; the `build-smoke-test` workflow checks it.

## Folder ownership

| Path | Owner | Notes |
|---|---|---|
| `AGENTS.md`, `.github/pull_request_template.md`, `.github/CODEOWNERS`, `docs/README.md`, every `docs/*/README.md`, other repo scaffolding | Technical Architect | Folder owners may propose README changes via the Operator Inbox |
| `docs/design/`, `docs/specs/` | Technical Architect | Specs are named `<story-id>.md` |
| `docs/adr/` | Technical Architect (technical ADRs), Enterprise Architect (enterprise ADRs) | Matching Decisions Log row required |
| `docs/togaf/` | Enterprise Architect | |
| `docs/requirements/` | Business Analyst | |
| `docs/vision/` | Project Manager | Notion Vision Brief is source of truth |
| Package source, tests (added in later phases) | Developer | Only from Ready for Dev stories with an Approved-ADR spec |
| PR reviews; Defects database | QA Reviewer | Review comments only; no pushes to others' branches |
| `README.md`, `GOAL.md`, `LICENSE`, `build.py`, `template.html`, `whitespace-atlas.html`, `research/`, `accelerators/`, `.github/workflows/` | Alex | Agents do not move or rewrite these without an Operator Inbox decision |

## Story flow

Backlog → Ready for Design (Business Analyst) → Ready for Dev (Technical Architect, once requirements and related ADRs are Approved and a spec exists) → In PR (Developer) → In QA (QA Reviewer) → Awaiting Merge → Done (Alex merges).

## Architecture guardrails

- First package: Salesforce unlocked 2GP package exposing knowledge-backed service calls via REST, Apex and Agentforce actions, driven by an Obsidian knowledge graph synced through GitHub.
- Keep the knowledge-graph sync format and service contracts runtime-neutral so future non-Salesforce runtimes reuse them instead of forking.
- IP line: package and templates are Rich Solutions IP; per-client logic is billable and lives outside this repo.
