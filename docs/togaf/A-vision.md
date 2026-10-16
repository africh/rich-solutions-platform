# Phase A: Architecture Vision

- **Status:** Draft
- **Date:** 2026-10-14
- **Owner:** Enterprise Architect
- **Story:** SB-4 "TOGAF Preliminary + Phase A Architecture Vision" (Notion Sprint Board)
- **Sources:** Notion Vision Brief (approved 2026-10-13, gate G0), [`GOAL.md`](../../GOAL.md), [`README.md`](../../README.md)
- **Related requirements:** REQ-1 to REQ-15; see [`docs/requirements/traceability.md`](../requirements/traceability.md)
- **Related ADRs:** ADR-001 2GP package structure and knowledge-graph sync (Approved 2026-10-15)
- **Principles:** [principles.md](principles.md) · **Next:** [Phase B Business Architecture](B-business.md)

The Notion Vision Brief is the source of truth for scope. This document restates it in TOGAF terms and connects it to the whitespace model in GOAL.md. If the two ever disagree, the Vision Brief wins and the difference is raised in the Operator Inbox.

## 1. Problem and opportunity

Vertical and mid-size firms want sovereign, reusable AI capabilities inside the systems they already run, starting with Salesforce. Consulting engagements usually leave behind billable hours rather than reusable assets.

The Whitespace Atlas (GOAL.md) finds where AI readiness is high but market coverage is low:

```
Whitespace Score = AI Readiness x (6 - Market Coverage)    High >= 16, Medium 9-15, Low <= 8
```

Each high-whitespace capability is a candidate **accelerator**: a reusable package that applies one or more of the 14 agentic patterns to that capability. The Rich Solutions Platform is the marketplace that houses these accelerators.

## 2. Stakeholders

| Stakeholder | Interest | Concerns | Engagement |
|---|---|---|---|
| Alex Rich (principal operator) | Reusable IP, fast path to a pilot | Quality, IP protection, agent cost | Approves ADRs and gates, merges PRs, answers Operator Inbox |
| Client business sponsors (vertical and mid-size firms on Salesforce) | Governed AI actions without a custom build | Data residency, compliance, vendor lock-in | Pilot feedback (via Alex) |
| Client Salesforce admins and developers | Clean install, extension points | Install steps, permissions, upgrade path | Install docs, extension convention (SB-13) |
| Client end users and Agentforce agents | Correct, sourced answers | Trust, citations, no-answer behaviour | Acceptance demo (REQ-13, pending) |
| Knowledge authors (vault maintainers) | Easy authoring in Obsidian | Sync freshness, broken links | Sync design (SB-8, ADR-001) |
| Rich Solutions engagement teams (public-sector and enterprise) | Package they can deploy and extend | Billable extension work stays separate | IP boundary (REQ-6) |
| Agent team (7 agents) | Clear ownership and inputs | No memory between runs | AGENTS.md, Notion HQ |
| Regulators / compliance functions in target sectors | Controls evidence | FedRAMP/StateRAMP/FERPA/PCI-aware posture | Principles DP-2, SP-2 |

## 3. Business drivers

1. **Turn services into product:** every engagement should create or improve a reusable package (Vision).
2. **Whitespace demand:** many capabilities in wave-1 industries (Public Sector, Education, Nonprofit, Hospitality) score high on AI readiness but low on market coverage (GOAL.md).
3. **Meet clients where they are:** target firms already run Salesforce and want AI inside it, not beside it.
4. **Sovereignty and governance:** buyers need AI actions that respect their permissions, data residency and audit needs.
5. **Pilot timing:** one client pilot by late January 2027 (proposed success metric, REQ-14 pending).

## 4. Goals and success measures

| Goal | Measure | Requirement |
|---|---|---|
| G-1 Ship accelerator #1 | Unlocked 2GP package installs into a fresh scratch org with zero manual steps | REQ-5, REQ-12 (pending) |
| G-2 Prove knowledge-backed AI | One Agentforce action answers from the knowledge graph end to end | REQ-4, REQ-13 (pending) |
| G-3 Reach a client | One client pilot by late January 2027 | REQ-14 (pending) |
| G-4 Protect and reuse IP | Base package has no client logic; contracts reusable by a second runtime | REQ-6, REQ-8 |
| G-5 Run the factory transparently | All work and decisions logged in Notion and the repo | REQ-7 |

## 5. Scope

### In scope (MVP, accelerator #1)

- Sync an Obsidian knowledge graph, stored in GitHub, into a form the package can query (REQ-1).
- Knowledge-backed, MCP-like service calls exposed via REST endpoints, an Apex API and Agentforce actions (REQ-2 to REQ-4).
- Clean install as an unlocked 2GP package into a scratch org or sandbox (REQ-5).
- IP line between base package and per-client extension packages (REQ-6).
- Factory work and decisions logged in Notion (REQ-7).
- Runtime-neutral sync format and service contracts (REQ-8).

### Out of scope (MVP)

- Multi-vendor marketplace (REQ-10).
- Public storefront, billing, licensing management (REQ-11).
- Non-Salesforce runtimes (REQ-9): a future enhancement, but the MVP must not block it (principle AP-1).
- Accelerators #2 onward; the whitespace model selects them after the MVP.

### Architecture scope (TOGAF dimensions)

| Dimension | Scope |
|---|---|
| Breadth | Accelerator #1 and the shared platform elements it introduces (contracts, sync, factory conventions) |
| Depth | Enough for Technical Architect specs; component-level detail lives in ADRs and specs |
| Time | Now to the first client pilot (target late January 2027), across phases P0 to P3 |
| Domains | Business (B), Data (C), Application (C), Technology (D) |

## 6. Constraints

| # | Constraint | Source |
|---|---|---|
| CN-1 | First runtime is Salesforce; package type is unlocked 2GP | Vision Brief |
| CN-2 | Knowledge source is an Obsidian vault synced through GitHub | Vision Brief |
| CN-3 | Repository is public: no client names, engagement details, credentials or secrets | AGENTS.md |
| CN-4 | No paid services or new external accounts without Alex | AGENTS.md |
| CN-5 | Hosting for anything outside Salesforce is undecided (AWS vs on-platform only) | Operator Inbox (open) |
| CN-6 | Human approval at every gate; only Alex approves ADRs and merges | GOAL.md, AGENTS.md |
| CN-7 | Salesforce governor limits (heap, callouts, field sizes) | Platform; see ADR-001 |
| CN-8 | Compliance-aware posture for regulated sectors (FedRAMP/StateRAMP/FERPA/PCI) | GOAL.md (assumed default) |
| CN-9 | Agent team usage budget not yet set | Operator Inbox (open) |

## 7. Value chain

The platform sits on GOAL.md's six-stage, human-gated solution path. Each arrow is a HITL gate.

| Stage | Activity | Platform output | Who / what |
|---|---|---|---|
| 1. Whitespace Identification | Score L1 to L3 capabilities by industry | Whitespace Atlas, ranked opportunities | Research agents + Alex |
| 2. Pattern Selection | Map opportunity to agentic patterns (P01 to P14) | Pattern choice per accelerator | Alex + Enterprise Architect |
| 3. Solution Blueprint & Reference Architecture | Architecture vision, B/C/D architectures, ADRs | `docs/togaf/`, `docs/adr/` | Enterprise + Technical Architect |
| 4. Backlog & Agent Specification | Requirements, stories, specs | Notion Requirements and Sprint Board, `docs/specs/` | Business Analyst, Technical Architect |
| 5. Factory Build | Scaffold, code, test | Package source, tests, PRs | Developer, QA Reviewer |
| 6. Deploy & Operate | Install, extend, pilot | Package versions, client extension packages (outside this repo) | Alex, engagement teams |

Value flows back: each deployment improves the base package (build once, deploy many), and per-client extension work is billable.

Accelerator #1 primarily realises pattern **P05 Knowledge Retrieval & Policy Q&A**, and is a building block for P04 Conversational Service Concierge and P03 Case Triage & Routing in later accelerators.

## 8. High-level solution concept

```
 Knowledge authors                     Rich Solutions platform (this repo, public)                Client Salesforce org
 ------------------                    -------------------------------------------                ---------------------
 Obsidian vault  --git push-->  GitHub  -->  Compile + validate  -->  Knowledge bundle  --sync-->   Base 2GP package
 (client or RS repo)                         (runtime-neutral)        (versioned, JSON)              - Storage
                                                                                                    - Service core
                         Runtime-neutral contracts:                                                 - Exposure: REST | Apex | Agentforce
                         - knowledge bundle schema                                                         |
                         - service-call contract                       Future runtimes reuse  <------      v
                                                                       the same contracts           Client extension package
                                                                                                    (billable, outside this repo)
```

Building blocks (detailed in Phases B to D and ADR-001):

| Building block | Purpose | Principle |
|---|---|---|
| Knowledge graph (Obsidian vault in GitHub) | Single source of knowledge content | DP-1 |
| Knowledge bundle + schema | Runtime-neutral, versioned snapshot of the graph | AP-1, DP-1 |
| Service-call contract | Runtime-neutral definition of knowledge service calls | AP-1 |
| Sync mechanism | Moves a validated bundle into a runtime (ADR-001 proposes CI compile and push) | TP-1 |
| Salesforce base package | Storage, service core, REST/Apex/Agentforce exposure | AP-2, TP-2 |
| Client extension packages | Per-client logic through published interfaces | BP-2 |
| Software factory (agent team + Notion + repo) | Builds and governs the platform with HITL gates | BP-3, BP-4 |

Accelerator #1 is the first package in the marketplace. Later accelerators reuse the contracts, sync and factory conventions it establishes.

## 9. Risks and open questions

| # | Item | Impact | Handling |
|---|---|---|---|
| R-1 | Hosting outside Salesforce undecided | Shapes Phase D and later sync adapters | Existing Operator Inbox question; ADR-001 proposes a sync that needs no extra hosting |
| R-2 | Success metrics and governed access not confirmed (REQ-12 to REQ-15) | Acceptance criteria may shift | Existing Business Analyst Operator Inbox item |
| R-3 | Pilot candidate not chosen | Pilot timing (REQ-14) | Alex; answer in Notion only (public repo) |
| R-4 | Agent team usage budget not set | Pace of delivery | Existing Resource Manager Operator Inbox item |
| R-5 | Governor limits for large vaults | Sync paging and storage design | ADR-001, SB-8 spec |
| R-6 | `python build.py` fails on `main` (placeholder research data) | CI signal on Alex-owned files | Existing Operator Inbox FYI |

## 10. Next ADM steps

1. Phase B Business Architecture (`B-business.md`): capabilities, value streams and actors mapped to requirements.
2. Phase C Data and Application Architectures (`C-data.md`, `C-application.md`), aligned with ADR-001 once Approved.
3. Phase D Technology Architecture (`D-technology.md`), referencing the hosting question rather than choosing.
4. Phases E to F roadmap (`E-F-roadmap.md`).
5. When Phases A to D are Baseline and core ADRs are Approved, propose gate G1 "Design approved".
