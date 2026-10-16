# Architecture Principles (TOGAF Preliminary Phase)

- **Status:** Draft
- **Date:** 2026-10-14
- **Owner:** Enterprise Architect
- **Story:** SB-4 "TOGAF Preliminary + Phase A Architecture Vision" (Notion Sprint Board)
- **Related requirements:** REQ-1 to REQ-8 (MVP), REQ-9 to REQ-11 (out of scope), REQ-12 to REQ-15 (waiting on Alex); see [`docs/requirements/traceability.md`](../requirements/traceability.md)
- **Related ADRs:** ADR-001 2GP package structure and knowledge-graph sync (Approved 2026-10-15, Technical Architect)
- **Next:** [Phase A Architecture Vision](A-vision.md)

These principles bind every architecture artifact, ADR, spec and pull request for the Rich Solutions Platform. When two principles pull in different directions, the conflict goes to the Operator Inbox; agents do not resolve it silently. Changes to this file need Alex's approval through the Operator Inbox.

Each principle follows the TOGAF template: **Statement**, **Rationale**, **Implications**.

## Architecture organisation and scope (Preliminary)

| Item | Baseline |
|---|---|
| Enterprise in scope | Rich Solutions Consulting's accelerator platform: the reusable packages, their contracts, and the agent team ("software factory") that builds them |
| Architecture board | Alex Rich (principal operator) is the sole approver of ADRs, gates and merges |
| Architecture team | Autonomous agents: Project Manager, Business Analyst, Enterprise Architect, Technical Architect, Developer, QA Reviewer, Resource Manager (roles and ownership in [`AGENTS.md`](../../AGENTS.md)) |
| Repository | This public GitHub repository (architecture content) plus Notion Agent Team HQ (status, decisions, requests) |
| Framework tailoring | TOGAF ADM, lightweight: one Markdown file per phase in `docs/togaf/`, decisions as ADRs in `docs/adr/`, compliance via PR review and gates |
| Governance gates | G0 Vision approved (passed 2026-10-13); G1 Design approved (Phases A to D Baseline and core ADRs Approved); later build and pilot gates defined in the Phase E–F roadmap |

## Business principles

### BP-1 Platform-led, build once, deploy many

- **Statement:** Every engagement creates or improves a reusable package; we do not build one-off solutions inside this platform.
- **Rationale:** The Vision Brief positions the platform as a marketplace of Rich Solutions accelerator IP. Reuse is what turns consulting hours into a compounding asset.
- **Implications:**
  - A requirement that only one client needs is billable extension work and lives outside this repo (see BP-2).
  - Designs are judged on how many future deployments they serve, not only on the first.
  - Each accelerator traces back to a whitespace opportunity and agentic pattern (GOAL.md), so the library grows deliberately.

### BP-2 Clear IP line between platform and client logic

- **Statement:** Packages, templates and contracts in this repo are Rich Solutions IP. Per-client logic, data and configuration are billable and live outside this repo, in separate extension packages that depend on the base package.
- **Rationale:** Vision Brief Must-do #4 (REQ-6). A clean line protects the IP, keeps the base package installable everywhere, and keeps client data out of a public repo.
- **Implications:**
  - The base package never depends on an extension package; extensions plug in through published interfaces.
  - Reviews flag any client-specific logic, names or data in a PR (SB-13 defines the convention and checklist).
  - ADR-001 (Proposed) realises this with a base package plus dependent client extension packages.

### BP-3 Human-in-the-loop at every gate

- **Statement:** Agents propose; a human approves. No stage of the solution path, and no architecture decision, advances without an explicit human gate.
- **Rationale:** GOAL.md makes HITL mandatory between all six stages of the solution path (Whitespace Identification, Pattern Selection, Solution Blueprint & Reference Architecture, Backlog & Agent Specification, Factory Build, Deploy & Operate). The agent team runs unattended, so gates are the control that keeps it safe and accountable.
- **Implications:**
  - Only Alex sets an ADR to Approved, passes a gate, or merges to `main`.
  - Agents stop and raise an Operator Inbox item when blocked or when a decision is needed, instead of choosing.
  - Packaged agentic actions (for example Agentforce actions) are designed so a human can review, override or decline their output in the subscriber org; actions that write or act on behalf of a user need an explicit confirmation step.

### BP-4 Decisions are recorded and traceable

- **Statement:** Every architecture-significant choice is an ADR with a matching Decisions Log row; every requirement traces to a story, spec and PR.
- **Rationale:** Agents keep no memory between runs (REQ-7). The repo and Notion are the only shared memory, so undocumented decisions are lost decisions.
- **Implications:**
  - No spec may build on a Proposed ADR.
  - Architecture docs carry a status line (Draft / Baseline), a date, and links to related requirements and ADRs.
  - Each agent run ends with exactly one Handoff Log entry.

## Data principles

### DP-1 Knowledge is a governed, versioned asset

- **Statement:** The knowledge graph (an Obsidian vault in GitHub) is the single source of knowledge content; every runtime consumes a versioned, schema-validated snapshot of it, traceable to a commit.
- **Rationale:** REQ-1. Git gives history, review and rollback for free; a versioned snapshot lets any runtime prove which knowledge produced an answer.
- **Implications:**
  - Knowledge is edited in the vault, never directly in a runtime store.
  - Bundles carry source repo, commit SHA and content hash; invalid bundles are rejected and the prior version stays live (SB-8 acceptance criteria).
  - Answers should be able to cite the source note (confirmation pending on REQ-13).

### DP-2 Data residency and least data

- **Statement:** Client knowledge and data stay in the client's own systems (their GitHub vault and their Salesforce org) unless Alex approves otherwise; the platform stores the minimum it needs.
- **Rationale:** GOAL.md assumes residency and FedRAMP/StateRAMP/FERPA/PCI-aware controls for target sectors. Keeping data in the client's systems avoids new compliance scope for Rich Solutions.
- **Implications:**
  - Any component that would hold client data outside the client's org (for example external hosting) is an architecture-significant decision needing an ADR; hosting is currently an open Operator Inbox question.
  - Access to knowledge-backed calls respects the subscriber org's permissions (granularity pending on REQ-15).
  - Sample and test vaults in this repo are synthetic.

## Application principles

### AP-1 Runtime-neutral contracts

- **Statement:** The knowledge-bundle sync format and the service-call contracts are defined once, in runtime-neutral form (for example JSON Schema and OpenAPI), with no Salesforce-specific types. Each runtime is an adapter over those contracts.
- **Rationale:** Vision Brief future enhancement and REQ-8: later non-Salesforce runtimes must reuse the sync format and contracts instead of forking them. AGENTS.md lists this as an architecture guardrail.
- **Implications:**
  - Contracts live in a runtime-neutral location in the repo (proposed `contracts/` in ADR-001) and are versioned; breaking changes need a new version and an ADR.
  - Parsing the vault happens once, outside any runtime (ADR-001 proposes a CI compiler).
  - Salesforce code mirrors the contracts; it does not redefine them. SB-7 publishes the first contract versions.
  - A design that only works on one runtime must say so in its ADR and explain why.

### AP-2 One service core, many thin exposures

- **Statement:** Business logic for knowledge-backed service calls lives in one service layer; REST, Apex and Agentforce (and future channels such as MCP) are thin adapters over it.
- **Rationale:** REQ-2 to REQ-4 require the same calls through three channels; SB-10 requires Apex and REST to return the same result for the same input.
- **Implications:**
  - Exposure layers hold no logic of their own.
  - Adding a channel or runtime means adding an adapter, not a new implementation.

### AP-3 Model and vendor swappability

- **Statement:** Claude is the default model for the factory and for any packaged generation step, but every model and vendor dependency sits behind an interface and can be swapped.
- **Rationale:** GOAL.md: "Claude as default model, swappable"; target clients often have mandated AI vendors or sovereign-AI requirements.
- **Implications:**
  - Inside Salesforce, generation uses the platform's own AI layer (Agentforce) rather than a hard-wired external model call.
  - No contract or bundle format assumes a specific model or embedding.

## Technology principles

### TP-1 Cloud-agnostic, no new hosting by default

- **Statement:** Prefer capabilities the client already runs (Salesforce) and the tools we already have (GitHub, GitHub Actions). New hosting or paid services need an ADR approved by Alex.
- **Rationale:** GOAL.md cloud-agnostic constraint; AGENTS.md forbids signing up for paid services or accounts; hosting outside Salesforce is an open question (AWS vs on-platform only).
- **Implications:**
  - The MVP must not depend on an external runtime unless the hosting question is answered.
  - When external hosting is proposed, the design stays portable across clouds.

### TP-2 Clean, repeatable install

- **Statement:** A package installs into a fresh scratch org or sandbox from a versioned artifact with no hand edits.
- **Rationale:** REQ-5 and the proposed zero-manual-step success metric (REQ-12).
- **Implications:**
  - No dependency on optional org features (for example Salesforce Knowledge or Data Cloud) unless declared and approved.
  - Any post-install setup is scripted and documented.

## Security and repository principles

### SP-1 Public-repo IP hygiene

- **Statement:** This repository is public. It never contains client names, engagement details, pilot candidates, credentials, tokens, org IDs or other secrets.
- **Rationale:** AGENTS.md and the Vision Brief. Anything pushed to a public repo should be treated as published permanently.
- **Implications:**
  - Engagements are described generically (for example "a public-sector pilot"); specifics live only in Notion.
  - Secrets live in the CI secret store or the client's own systems, never in files, and the PR template checklist confirms this on every PR.
  - When in doubt, leave it out and raise it in the Operator Inbox.
  - Platform IP being public is accepted for templates and contracts; client IP never is.

### SP-2 Least privilege and governed access

- **Statement:** Every caller, human or agent, gets only the access it needs; agent actions run with the invoking user's permissions.
- **Rationale:** Target customers want governed AI actions (Vision Brief); REQ-15 (pending) covers governed access.
- **Implications:**
  - Package permissions are granted through permission sets, not profiles.
  - Unauthenticated or unauthorised calls get an error and no content (SB-9).
  - CI integrations use dedicated credentials scoped to one purpose.

## Principle-to-requirement map

| Principle | Requirements | Stories / ADRs |
|---|---|---|
| BP-1 Platform-led | Vision | All accelerators |
| BP-2 IP line | REQ-6 | SB-13, ADR-001 |
| BP-3 HITL gates | GOAL.md | Gates G0, G1 |
| BP-4 Traceability | REQ-7 | SB-3 |
| DP-1 Governed knowledge | REQ-1, REQ-13 | SB-8, ADR-001 |
| DP-2 Residency | REQ-15 | Hosting question (Operator Inbox) |
| AP-1 Runtime-neutral contracts | REQ-8, REQ-9 | SB-7, ADR-001 |
| AP-2 One core, thin exposures | REQ-2, REQ-3, REQ-4 | SB-9, SB-10, SB-11 |
| AP-3 Swappable model | GOAL.md | – |
| TP-1 Cloud-agnostic | – | Hosting question (Operator Inbox) |
| TP-2 Clean install | REQ-5, REQ-12 | SB-12 |
| SP-1 Public-repo hygiene | REQ-6 | AGENTS.md, PR template |
| SP-2 Least privilege | REQ-15 | SB-9 |
