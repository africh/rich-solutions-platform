# Phase B: Business Architecture

- **Status:** Draft
- **Date:** 2026-10-16
- **Owner:** Enterprise Architect
- **Story:** none yet on the Sprint Board (TOGAF ADM baseline, Enterprise Architect routine); follows SB-4
- **Sources:** Notion Vision Brief (approved 2026-10-13, gate G0), [`GOAL.md`](../../GOAL.md), Notion Requirements database
- **Related requirements:** REQ-1 to REQ-15; see [`docs/requirements/traceability.md`](../requirements/traceability.md)
- **Related ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) 2GP package structure and knowledge-graph sync (Approved 2026-10-15)
- **Previous:** [Phase A Architecture Vision](A-vision.md) · **Principles:** [principles.md](principles.md)

This phase describes what the business does, who does it and how value flows, independent of technology. It covers two businesses that share one architecture:

1. **The accelerator business:** Rich Solutions Consulting turning whitespace opportunities into reusable packages and deploying them to clients (build once, deploy many, BP-1).
2. **Accelerator #1 in use:** a client organisation that authors knowledge in an Obsidian vault and consumes it through governed, knowledge-backed service calls in Salesforce.

Engagements are described generically (SP-1). Client and pilot specifics live only in Notion.

## 1. Business actors and roles

| Actor | Type | Role in the business | Main touchpoints | Requirements |
|---|---|---|---|---|
| Principal operator (Alex) | Internal person | Architecture board: approves gates, ADRs, scope changes; merges; owns client relationships | Operator Inbox, PR review, Decisions Log | REQ-7 |
| Agent team (PM, BA, EA, TA, Developer, QA, Resource Manager) | Internal automated actors | Run the software factory under AGENTS.md; propose, never approve | Notion HQ, this repo | REQ-7 |
| Engagement team | Internal people | Deploy accelerators, build billable client extensions outside this repo | Package versions, extension convention | REQ-6, REQ-14 |
| Client business sponsor | External person | Funds the pilot; defines which questions the agent must answer | Pilot scope (via Alex) | REQ-13, REQ-14 |
| Knowledge author | External person (client) or internal | Writes and links notes in the Obsidian vault; reviews changes via Git | Vault repository | REQ-1 |
| Client Salesforce admin | External person | Installs and upgrades the package, assigns permission sets, configures Agentforce | Package install, permission sets | REQ-5, REQ-12, REQ-15 |
| Client developer / integrator | External person or system | Calls knowledge services from Apex or REST; builds extension packages | Apex API, REST API | REQ-2, REQ-3, REQ-6 |
| Client end user | External person | Asks questions and gets sourced answers through an agent | Agentforce agent | REQ-4, REQ-13 |
| Agentforce agent | External automated actor | Invokes knowledge actions on behalf of the end user, with that user's permissions | Agentforce actions | REQ-4, REQ-15 |
| Future runtime operator | External (future) | Runs the same services outside Salesforce | Runtime-neutral contracts | REQ-8, REQ-9 |

## 2. Business capability map

Capabilities are named to match the **TOGAF Capability** field on each Notion requirement, so the trace stays one-to-one. Level 1 is the capability domain; level 2 is the capability the MVP needs. "MVP" marks what accelerator #1 must deliver; "Enabling" marks what the factory needs to deliver it; "Future" is recorded only so it is not built by accident.

| L1 domain | L2 capability | Description | Scope | Requirements | Stories |
|---|---|---|---|---|---|
| **Knowledge Management** | Knowledge authoring | Write, link and tag notes in a Git-versioned vault | MVP (client-side, existing tooling) | REQ-1 | – |
| | Knowledge publication (sync) | Turn a vault commit into a validated, versioned snapshot and load it into a runtime | MVP | REQ-1, REQ-8 | SB-7, SB-8 |
| | Knowledge retrieval | Find, read and traverse knowledge to answer a question, with the source cited | MVP | REQ-1, REQ-13 | SB-9 |
| **Integration & API Management** | Service contract management | Define and version service calls once, runtime-neutral | MVP | REQ-2, REQ-3, REQ-8 | SB-7 |
| | Service exposure | Offer the same knowledge services over REST and Apex | MVP | REQ-2, REQ-3 | SB-9, SB-10 |
| **AI & Agent Services** | Agent action provisioning | Make knowledge services available as Agentforce actions | MVP | REQ-4 | SB-11 |
| | Grounded answering | Answer end users from synced knowledge, or say there is no answer | MVP (acceptance demo) | REQ-13 (Needs Alex) | SB-11 |
| **Security & Access Management** | Governed access | Only permitted users, integrations and agents can call services or see results | MVP | REQ-15 (Needs Alex) | SB-9 |
| **Release & Deployment Management** | Package release | Build and version the unlocked 2GP package | MVP | REQ-5 | SB-12 |
| | Clean installation | Install into a fresh scratch org or sandbox with no hand edits | MVP | REQ-5, REQ-12 (Needs Alex) | SB-12 |
| **Product & IP Portfolio Management** | IP boundary management | Keep base package and templates as Rich Solutions IP; client logic separate and billable | MVP | REQ-6 | SB-13 |
| | Accelerator selection | Choose the next accelerator from whitespace scores and the pattern library | Enabling (post-MVP use) | GOAL.md | – |
| | Pilot delivery | Deploy accelerator #1 at one client | MVP target | REQ-14 (Needs Alex) | – |
| **Architecture Governance** | Decision and work traceability | Record every decision, requirement, story, spec and PR | Enabling | REQ-7 | SB-3 |
| | Gate management (HITL) | Human approval between solution-path stages | Enabling | BP-3 | G0, G1 |
| | Runtime neutrality assurance | Check designs keep contracts free of runtime-specific types | Enabling | REQ-8 | SB-7 |
| **Platform Runtime Services** | Alternative runtime hosting | Run knowledge services outside Salesforce | Future | REQ-9 (Won't) | – |
| **Marketplace Management** | Multi-vendor listing | Third-party packages in the marketplace | Future | REQ-10 (Won't) | – |
| **Commercial Management** | Storefront, billing, licensing | Sell and license packages | Future | REQ-11 (Won't) | – |

### Capability heat (MVP readiness)

| Capability | Current state | Gap to MVP |
|---|---|---|
| Knowledge authoring | Exists (Obsidian + Git) | None for the platform; vault location for the pilot is an Alex account action (ADR-001) |
| Knowledge publication | Designed (ADR-001 option A) | Contracts (SB-7, spec waiting to be pushed), compiler and import (SB-8) |
| Knowledge retrieval, service exposure, agent actions | Not started | SB-9 to SB-11, after G1 |
| Governed access | Principle only (SP-2) | REQ-15 granularity answer from Alex |
| Package release, clean install | Designed (ADR-001) | Dev Hub, namespace, CI credentials (Alex account actions); SB-12 |
| IP boundary management | Principle (BP-2) and package split (ADR-001) | Convention and checklist (SB-13) |
| Decision traceability, gates | Operating (Notion HQ, this repo) | G1 criteria evidence (Phases A to D Baseline) |
| Accelerator selection | Whitespace Atlas exists; research data is placeholder on `main` | Alex-owned research data (open Inbox FYI) |

## 3. Value streams

Value streams use the TOGAF form: stages, each with an entry condition, value item and exit gate. Gates are human (BP-3).

### VS-1 Whitespace to accelerator (the accelerator business)

Realises GOAL.md's six-stage solution path. Stakeholder: Rich Solutions. Value: a reusable, installable package.

| # | Stage | Value item | Capabilities | Exit gate (human) |
|---|---|---|---|---|
| 1 | Identify whitespace | Ranked opportunities (Whitespace Score ≥ 16) | Accelerator selection | Alex picks the opportunity |
| 2 | Select pattern | Pattern choice (P01 to P14); for accelerator #1, P05 Knowledge Retrieval & Policy Q&A | Accelerator selection | Alex confirms scope (Vision Brief, G0) |
| 3 | Blueprint the solution | Architecture vision, B/C/D architectures, ADRs | Gate management, runtime neutrality assurance | **G1 Design approved** |
| 4 | Specify backlog | Requirements, stories, specs | Decision and work traceability | Story reaches Ready for Dev (Approved requirement + Approved ADR + spec) |
| 5 | Build in the factory | Package source, tests, PRs | Package release, IP boundary management | QA review, then Alex merges |
| 6 | Deploy and operate | Installed package, billable client extension | Clean installation, pilot delivery | Pilot acceptance (gate defined in E–F roadmap) |

Feedback loop: lessons from each deployment flow back into the base package (stage 5), and client-only needs become extension work outside this repo (BP-2).

### VS-2 Vault commit to governed answer (accelerator #1 in use)

Stakeholder: client end user. Value: a correct, sourced answer, or an explicit "no answer", inside Salesforce.

| # | Stage | Actor | Value item | Capabilities | Requirements |
|---|---|---|---|---|---|
| 1 | Author | Knowledge author | Reviewed note change committed to the vault | Knowledge authoring | REQ-1 |
| 2 | Publish | CI (on the author's push) | Validated, versioned knowledge bundle traceable to a commit; invalid bundle rejected, prior knowledge stays live | Knowledge publication | REQ-1, REQ-8 |
| 3 | Load | Package import service | Knowledge queryable in the client org | Knowledge publication | REQ-1 |
| 4 | Grant | Client admin | Users, integrations and agents hold the right permission sets | Governed access | REQ-15 |
| 5 | Ask | End user via agent, or developer via REST/Apex | A service call within the caller's permissions | Service exposure, agent action provisioning | REQ-2 to REQ-4 |
| 6 | Answer | Knowledge service | Structured answer with source notes, or explicit no-answer | Knowledge retrieval, grounded answering | REQ-13 |

### VS-3 Package release to client install

Stakeholder: client admin and engagement team. Value: a working install with nothing done by hand.

| # | Stage | Actor | Value item | Requirements |
|---|---|---|---|---|
| 1 | Release | Factory (Developer, QA) after Alex merges | Versioned unlocked 2GP package | REQ-5 |
| 2 | Install | Client admin or engagement team | Package installed in a scratch org or sandbox | REQ-5, REQ-12 |
| 3 | Extend | Engagement team | Client extension package that depends on the base, built outside this repo | REQ-6 |
| 4 | Upgrade | Client admin | New base version installed; extensions keep working through published interfaces | REQ-5, REQ-6 |

## 4. Business services

Business services are what each actor receives, independent of channel. Phase C maps them to application services; the runtime-neutral contracts (SB-7) define them once (AP-1).

| Business service | Consumer | Provided by capability | Channels (MVP) |
|---|---|---|---|
| Publish knowledge | Knowledge author | Knowledge publication | Git push → CI |
| Look up knowledge (get a note, search, follow links) | Developer, agent | Knowledge retrieval | REST, Apex, Agentforce |
| Answer a question from knowledge | End user (through an agent) | Grounded answering | Agentforce |
| Install and upgrade the accelerator | Client admin | Package release, clean installation | Salesforce package install |
| Extend the accelerator for one client | Engagement team | IP boundary management | Extension package (outside this repo) |
| Decide and approve | Principal operator | Gate management | Operator Inbox, PR review |

## 5. Key business processes

### BP-PR-1 Knowledge change (happy path and failure)

```
Author edits note -> commits to vault -> CI compiles + validates bundle
   valid   -> bundle loaded into org -> next service call sees new content
   invalid -> load rejected, prior bundle stays live -> author notified with the failure reason
```

Business rules: the vault is the only place knowledge is edited (DP-1); every loaded bundle names its source commit; deletes in the vault remove content on the next sync (SB-8 acceptance criteria).

### BP-PR-2 Governed question answering

```
User asks agent -> agent invokes knowledge action as the user -> permission check
   denied  -> error, no content returned
   allowed -> retrieve matching notes -> answer with sources, or explicit no-answer
```

Business rules: agents act with the invoking user's permissions (SP-2); no answer is better than an unsourced one (HITL, BP-3); whether answers must cite the source note is part of REQ-13 (Needs Alex).

### BP-PR-3 Engagement extension

```
Client need raised -> is it reusable for other clients?
   yes -> base package backlog (Notion Requirements, this repo)
   no  -> billable extension package, outside this repo, through published interfaces
```

Business rule: the base package never depends on an extension (BP-2); SB-13 publishes the convention and review checklist item.

## 6. Organisation and governance mapping

| Decision type | Proposes | Approves | Record |
|---|---|---|---|
| Scope / Vision change | Project Manager, any agent via Inbox | Alex | Vision Brief, Operator Inbox |
| Requirement | Business Analyst | Alex (Needs Alex items) | Notion Requirements, traceability.md |
| Enterprise architecture (TOGAF phases, enterprise ADRs) | Enterprise Architect | Alex | `docs/togaf/`, `docs/adr/`, Decisions Log |
| Technical architecture (technical ADRs, specs) | Technical Architect | Alex | `docs/adr/`, `docs/specs/`, Decisions Log |
| Code change | Developer | QA review, then Alex merges | PRs, Sprint Board |
| Gate (G0, G1, later gates) | Any agent with evidence | Alex | Decisions Log, Operator Inbox |

## 7. Gap analysis (baseline to target)

Baseline: consulting engagements that leave billable hours, not reusable assets; no packaged knowledge-backed AI for Salesforce clients. Target: accelerator #1 released, installed at one pilot, with contracts reusable by future runtimes.

| # | Gap | Resolved by | Status |
|---|---|---|---|
| GB-1 | No runtime-neutral definition of knowledge bundle or services | SB-7 | Spec written, push blocked (open Inbox Blocker) |
| GB-2 | No way to move vault content into an org | SB-8 under ADR-001 option A | Ready for Design |
| GB-3 | No knowledge services in any channel | SB-9, SB-10, SB-11 | Ready for Design |
| GB-4 | No releasable package | SB-12; Alex account actions (Dev Hub, namespace, CI credentials) | Ready for Design |
| GB-5 | IP line exists only as a principle | SB-13 | Ready for Design |
| GB-6 | Access model granularity undecided | REQ-15 answer from Alex | Open Inbox question |
| GB-7 | Acceptance demo and install bar not confirmed | REQ-12, REQ-13 answers from Alex | Open Inbox question |
| GB-8 | No pilot chosen | REQ-14; Alex (Notion only) | Open |

No new business capability gap needs a story beyond SB-7 to SB-13, provided REQ-12 to REQ-15 are answered; the Business Analyst creates stories for them once Approved.

## 8. Requirement coverage check

| Requirement | Capability | Value stream stage | Covered |
|---|---|---|---|
| REQ-1 | Knowledge publication, retrieval | VS-2 stages 1–3 | Yes |
| REQ-2 | Service exposure | VS-2 stage 5 | Yes |
| REQ-3 | Service exposure | VS-2 stage 5 | Yes |
| REQ-4 | Agent action provisioning | VS-2 stage 5 | Yes |
| REQ-5 | Package release, clean installation | VS-3 stages 1–2 | Yes |
| REQ-6 | IP boundary management | VS-1 stage 5, VS-3 stage 3 | Yes |
| REQ-7 | Decision and work traceability | VS-1 all stages | Yes |
| REQ-8 | Service contract management, runtime neutrality assurance | VS-2 stage 2 | Yes |
| REQ-9 to REQ-11 | Future capabilities | – | Recorded as out of scope |
| REQ-12 | Clean installation | VS-3 stage 2 | Yes, pending Alex |
| REQ-13 | Grounded answering | VS-2 stage 6 | Yes, pending Alex |
| REQ-14 | Pilot delivery | VS-1 stage 6 | Yes, pending Alex |
| REQ-15 | Governed access | VS-2 stage 4 | Yes, pending Alex |

Every Approved requirement maps to at least one capability and value stream stage. No requirement is orphaned and no capability in MVP scope lacks a requirement.

## 9. Open items

| # | Item | Handling |
|---|---|---|
| OB-1 | REQ-12 to REQ-15 confirmation | Existing Business Analyst Inbox item; this document is updated when answered |
| OB-2 | Hosting outside Salesforce | Existing Enterprise Architect Inbox question; does not change Phase B (affects Phase D) |
| OB-3 | Pilot candidate and sector | Alex, Notion only (SP-1) |
| OB-4 | This phase has no Sprint Board story | Project Manager may add one for the remaining TOGAF phases (B to E–F) |

## 10. Next ADM steps

1. Phase C Data Architecture (`C-data.md`): knowledge-graph entities, bundle data flows, residency and compliance notes, aligned with ADR-001 and the SB-7 contracts.
2. Phase C Application Architecture (`C-application.md`): components and interfaces for the business services above.
3. Phase D Technology Architecture (`D-technology.md`), referencing the open hosting question rather than choosing.
4. Phases E to F roadmap, then propose gate G1 once Phases A to D are Baseline and core ADRs are Approved.
