# Requirements traceability

Owner: Business Analyst. Requirements are authored in the Notion Requirements database; this file is a public-safe copy of the trace from requirement to story to spec to PR. Story IDs are Sprint Board IDs (shown in Notion as `RSP-n`, referred to as `SB-n` in branch names).

Last updated: 2026-10-16 (seeded from the approved Vision Brief in SB-3; refreshed after PRs #2 to #4 merged).

## Status key

- **Approved**: traced directly to approved Vision Brief text.
- **Needs Alex**: inferred or marked "proposed" in the Vision Brief; waiting on an Operator Inbox answer. No stories are created until Approved.
- **Won't** (priority): out of MVP scope or a future enhancement, recorded so it is not built by accident.

## MVP requirements

| Req | Requirement | Type | Priority | Status | Source | Story | Spec | PR |
|---|---|---|---|---|---|---|---|---|
| REQ-1 | Knowledge-graph sync from GitHub-hosted Obsidian vault | Functional | Must | Approved | Vision Brief, Must do #1 | SB-8 | – | – |
| REQ-2 | Knowledge-backed service calls via REST endpoints | Functional | Must | Approved | Vision Brief, Must do #2 | SB-9 | – | – |
| REQ-3 | Knowledge-backed service calls via Apex API | Functional | Must | Approved | Vision Brief, Must do #2 | SB-10 | – | – |
| REQ-4 | Knowledge-backed service calls via Agentforce actions | Functional | Must | Approved | Vision Brief, Must do #2 | SB-11 | – | – |
| REQ-5 | Installs cleanly as an unlocked 2GP package | Constraint | Must | Approved | Vision Brief, Must do #3 | SB-12 | – | – |
| REQ-6 | Clear IP line between package and per-client logic | Constraint | Must | Approved | Vision Brief, Must do #4 | SB-13 | – | – |
| REQ-7 | Factory work and decisions logged in Notion | Non-functional | Must | Approved | Vision Brief, Must do #5 | SB-3 | – | #3 |
| REQ-8 | Runtime-neutral sync format and service contracts | Non-functional | Should | Approved | Vision Brief, Future enhancements | SB-7 | – | – |

Related design work: SB-5 (ADR-001, package structure and sync approach, Approved, PR #2) informs REQ-1, REQ-5, REQ-6 and REQ-8. Specs for SB-7 to SB-13 are pending with the Technical Architect.

## Waiting on Alex

| Req | Requirement | Type | Priority (proposed) | Status | Source |
|---|---|---|---|---|---|
| REQ-12 | Zero-manual-step install into a fresh scratch org | Non-functional | Should | Needs Alex | Vision Brief, Success metrics (proposed) |
| REQ-13 | End-to-end Agentforce answer from the knowledge graph | Functional | Must | Needs Alex | Vision Brief, Success metrics (proposed) |
| REQ-14 | One client pilot by late January 2027 | Constraint | Should | Needs Alex | Vision Brief, Success metrics (proposed) |
| REQ-15 | Governed access to knowledge-backed service calls | Non-functional | Must | Needs Alex | Inferred from Vision Brief, Target customers |

## Not in MVP

| Req | Requirement | Priority | Status | Source |
|---|---|---|---|---|
| REQ-9 | Non-Salesforce runtimes (future) | Won't | Approved | Vision Brief, Future enhancements |
| REQ-10 | Multi-vendor marketplace | Won't | Approved | Vision Brief, Out of scope |
| REQ-11 | Public storefront, billing and licensing | Won't | Approved | Vision Brief, Out of scope |

## Stories

| Story | Title | Phase | Status | Requirements |
|---|---|---|---|---|
| SB-3 | Seed initial requirements from Vision Brief | P0 Foundations | Done | REQ-7 |
| SB-7 | Define runtime-neutral knowledge bundle schema and service contracts | P1 Architecture | Ready for Design | REQ-8 |
| SB-8 | Knowledge-graph sync: compile Obsidian vault from GitHub and load it into the org | P2 MVP build | Ready for Design | REQ-1 |
| SB-9 | Knowledge service core and REST endpoints | P2 MVP build | Ready for Design | REQ-2 |
| SB-10 | Global Apex API for knowledge service calls | P2 MVP build | Ready for Design | REQ-3 |
| SB-11 | Agentforce actions for knowledge service calls | P2 MVP build | Ready for Design | REQ-4 |
| SB-12 | Unlocked 2GP package project with clean scratch-org and sandbox install | P2 MVP build | Ready for Design | REQ-5 |
| SB-13 | IP boundary: base package vs client extension package convention | P1 Architecture | Ready for Design | REQ-6 |

Acceptance criteria (Given/When/Then) for each requirement live in Notion.
