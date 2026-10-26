# Phases E and F: Opportunities and Solutions, Migration Planning

- **Status:** Draft
- **Date:** 2026-10-26
- **Owner:** Enterprise Architect
- **Story:** SB-15 "TOGAF Phases B to F: Business, Data, Application, Technology, Opportunities & Migration" (Notion Sprint Board). The file name follows the SB-15 acceptance criteria (`E-F-migration.md`); the Phase A next-steps list calls it `E-F-roadmap.md`, which means this file
- **Sources:** Notion Vision Brief (approved 2026-10-13, gate G0), [`GOAL.md`](../../GOAL.md), Notion Sprint Board and Requirements, Operator Inbox
- **Related requirements:** REQ-1 to REQ-8 (Approved); REQ-12 to REQ-15 (Needs Alex); see [`docs/requirements/traceability.md`](../requirements/traceability.md)
- **Related ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) 2GP package structure and knowledge-graph sync (Approved 2026-10-15); [ADR-002](../adr/ADR-002-hybrid-agent-runtime.md) hybrid cloud/local agent runtime (Approved). No new ADR is proposed here.
- **Related specs and designs (open PRs, not yet on `main`):** `docs/specs/SB-7.md` (PR #7), `docs/specs/SB-8.md` (PR #11), `docs/specs/SB-9.md` (PR #14), `docs/specs/SB-10.md` (PR #15), `docs/specs/SB-11.md` (PR #16), `docs/specs/SB-12.md` (PR #12), `docs/design/ip-boundary.md` (PR #8, SB-13)
- **Previous:** Phase B (`B-business.md`, PR #6), Phase C Data (`C-data.md`, PR #10), Phase C Application (`C-application.md`, PR #13), Phase D (`D-technology.md`, PR #17) · **Principles:** [principles.md](principles.md)

Phase E groups the gaps found in Phases B to D into work packages and transition architectures. Phase F puts them in order, with the human gates between them. Both stay inside the approved Vision Brief: every work package maps to an existing Sprint Board story (SB-7 to SB-13), and nothing here adds scope (SB-15 acceptance criterion 4).

Build order and slice contents come from the Technical Architect's specs. This document points to them and does not restate their detail (AP-1, one definition). If a spec's build order changes in review, the spec wins and this document is updated.

## 1. Baseline and target

| | Baseline (today, 2026-10-26) | Target (end of P3, pilot-ready) |
|---|---|---|
| Architecture | Principles and Phase A on `main`; Phases B to D in open PRs; ADR-001 and ADR-002 Approved | Phases A to F Baseline; gate G1 passed |
| Specs | SB-7 to SB-13 specs and designs written, QA PASS, waiting on merge | Merged; each story built and Done |
| Package | No Salesforce source in the repo | One namespaced unlocked 2GP base package, promoted by Alex, installs into a plain scratch org and a sandbox |
| Knowledge flow | None | Vault commit → CI compile and validate → push → queryable in the org (VS-2) |
| Channels | None | REST, global Apex and Agentforce actions with the same results for the same input |
| IP line | Principle BP-2 and design SB-13 | Enforced by `package-check` in CI; client logic only in extension packages outside this repo |
| Pilot | Not chosen | One client sandbox install, then production (REQ-14, Needs Alex) |

## 2. Work packages

One work package per Sprint Board story, numbered to match (WP-7 is SB-7). Slices are the specs' own slices, each one Developer PR. "Transition" is the transition architecture in section 4 that the slice completes.

| WP | Story | Slices (spec section) | Delivers (Phase C/D components) | Depends on | Transition | Requirements |
|---|---|---|---|---|---|---|
| **WP-7** Contracts | SB-7 | One build PR (SB-7 spec 2 and 10) | AC-1 contracts, AC-2 contracts-check | G1 | T1 | REQ-8 (and the contract for REQ-1 to REQ-4) |
| **WP-8** Knowledge sync | SB-8 | 8a compiler, push, workflow template; 8b storage, import, commit and purge; 8c end-to-end run (SB-8 spec 2) | AC-3, AC-4, AC-5; AC-11 to AC-13, AC-16 | 8a: WP-7. 8b: 12a. 8c: 8a, 8b, Dev Hub | 8a: T1. 8b: T2. 8c: T3 | REQ-1, REQ-8 |
| **WP-9** Service core and REST | SB-9 | 9a core reads and `/nodes`; 9b search and context; 9c end-to-end and OpenAPI check (SB-9 spec 2) | AC-10, AC-12, AC-14, AC-15, AC-17; `Knowledge_Reader` (AC-20) | 9a: WP-7, 8b, 12a. 9b: 9a. 9c: 9b, 8c | 9a, 9b: T2. 9c: T3 | REQ-2 (REQ-15 pending) |
| **WP-10** Global Apex API | SB-10 | 10a (SB-10 spec 2) | AC-18 | 9b | T2 | REQ-3 |
| **WP-11** Agentforce actions | SB-11 | 11a invocable actions; 11b unpackaged agent sample and agent test (SB-11 spec 2) | AC-19 | 11a: 9b, 12a. 11b: 11a, Agentforce-capable scratch org | T3 | REQ-4 (REQ-13 pending) |
| **WP-12** Package project | SB-12 | 12a skeleton, `package-check`, scripts, CI workflow; 12b install verification and sandbox run (SB-12 spec 2) | AC-20, AC-21; TC-8 to TC-10; ENV-3 to ENV-6 | 12a: G1 (version create needs Dev Hub). 12b: 8b, WP-9, WP-10, 11a, sandbox | 12a: T1. 12b: T3 | REQ-5, REQ-6 (REQ-12 pending) |
| **WP-13** IP boundary | SB-13 | No code slice: the design and PR-template item (PR #8). Enforcement is built inside 12a (`package-check` S1 and S3) | Convention; IF-10 rules | PR #8 merge | T1 (with 12a) | REQ-6 |

REQ-7 (work logged in Notion) is met by how the factory already runs (AC-30 to AC-32) and needs no work package.

### 2.1 What is deliberately not a work package

| Item | Why not | Where it lives |
|---|---|---|
| REQ-12 to REQ-15 stories | Needs Alex; the Business Analyst creates stories only once Approved | BA Inbox item (2026-10-14). If approved, they fold into WP-9 (REQ-15), WP-11 (REQ-13), WP-12 (REQ-12) and the P3 pilot (REQ-14) |
| Hosting outside Salesforce (H1) | Not needed for the MVP (Phase D section 6) | EA Inbox question (2026-10-13). If chosen, a new enterprise ADR, then a new story |
| REQ-9 to REQ-11 (other runtimes, marketplace, storefront) | Won't for the MVP | Vision Brief out of scope / future enhancements |
| ADR-002 local agent rollout | Factory capability, not part of accelerator #1 | `docs/design/hybrid-agent-runtime.md`; Technical Architect and Resource Manager |
| Factory evaluation and observability | Proposed scope change, not decided | TA Scope change Inbox item (2026-10-16) |
| Client extension packages | Billable, per client, outside this repo (BP-2) | Engagement work |

## 3. Prerequisites outside the agent team

These are Alex decisions or account actions. None is a work package; each is already in the Operator Inbox, so this document adds no new item.

| ID | Prerequisite | Needed by | Inbox item |
|---|---|---|---|
| PRE-1 | Merge the P1 spec and architecture PRs | G1, then every WP | QA Merge PR items for #5 to #8 and #10 to #17 |
| PRE-2 | Folder owners for `contracts/`, `tools/`, `templates/`, `packages/` in AGENTS.md | WP-7 onward (Developer folder rights) | TA Blocker 2026-10-15 (decision b) |
| PRE-3 | Agent-added workflow files (`contracts-check`, `package-ci`) | WP-7, 12a CI evidence; otherwise checks run locally with output in the PR | TA question 2026-10-20 |
| PRE-4 | Dev Hub, namespace, package name; optional CI connected app and secrets | 12a version create, 8c, 9c, 12b | TA question 2026-10-19 |
| PRE-5 | A sandbox the package may be installed into | 12b (REQ-5 AC 4) | Same item as PRE-4 |
| PRE-6 | An Agentforce-capable scratch-org shape | 11b | Same item as PRE-4 (SB-11 spec 11) |
| PRE-7 | REQ-12 to REQ-15 answered | Final acceptance bar for G2 | BA question 2026-10-14 |
| PRE-8 | Pilot candidate chosen (kept in Notion only, SP-1) | P3 | Vision Brief open question; REQ-14 |
| PRE-9 | Agent team usage budget | Pace of P2 (Developer and QA run cadence) | RM question 2026-10-13; RM Scope change items 2026-10-23 |

## 4. Transition architectures

Each transition is a working, reviewable state of `main`. The application and technology components named are from Phases C and D.

### T0 Factory and architecture (current)

- **In place:** AC-30 to AC-33 (agent team, Notion HQ, repo and PR flow, `build-smoke-test`); ADR-001 and ADR-002 Approved; specs SB-7 to SB-13 in PRs.
- **Exit:** gate **G1 Design approved**.

### T1 Contracts and package skeleton

- **Adds:** WP-7 contracts and contracts-check; 12a package skeleton with layer folders, `package-check` and scripts; 8a compiler, push and vault-sync template; WP-13 enforced through `package-check`.
- **Demonstrable:** a synthetic vault compiles into a bundle that validates against `kg-bundle` v1 (REQ-8); `package-check static` passes and rejects a dependency fixture (REQ-6); a beta package version installs into a plain scratch org once PRE-4 exists (REQ-5 AC 2, AC 3).
- **Runtime neutrality check:** everything in T1 except 12a is Salesforce-free; contracts-check's token scan passes.
- **Exit:** QA PASS and Alex merge per PR (no named gate; Ready for Dev flow).

### T2 Sync and reads

- **Adds:** 8b storage, import and commit; 9a and 9b service core and REST; 10a global Apex API.
- **Demonstrable:** a pushed bundle is committed all-or-nothing, prior knowledge stays live on failure, and REST and Apex return the same results for the same input (REQ-1, REQ-2, REQ-3). Apex tests in a scratch org.
- **Exit:** QA PASS and Alex merge per PR.

### T3 Agentforce and pilot-ready

- **Adds:** 11a invocable actions and 11b agent sample; end-to-end evidence 8c and 9c; 12b install verification and sandbox install.
- **Demonstrable:** one Agentforce action answers from the synced knowledge graph, or returns the explicit no-answer result (REQ-4; REQ-13 pending); `verify-install` finds every REST, Apex and Agentforce component in a fresh scratch org and a sandbox (REQ-5; REQ-12 pending).
- **Exit:** gate **G2 MVP accepted** (proposed, section 5).

After T3, P3 hardens and pilots the same architecture. It adds no new component: Alex promotes a tested beta version, tags it, and installs it in the pilot client's sandbox, then production. Per-client work goes into an extension package outside this repo.

## 5. Gates

Gates follow principle BP-3: an agent proposes with evidence, Alex decides. Each gate is a Decisions Log row whose name starts with the gate id, set to Approved by Alex (the SB-12 spec uses the same "G1" row convention).

| Gate | Phase transition | Criteria | Status |
|---|---|---|---|
| **G0 Vision approved** | P0 → P1 | Vision Brief approved | Passed 2026-10-13 |
| **G1 Design approved** | P1 → P2 (T0 → T1) | Phases A to D Baseline on `main`; ADR-001 and ADR-002 Approved; SB-7 to SB-13 specs merged; this document merged | Defined in [principles.md](principles.md). The Enterprise Architect raises one Inbox item when the criteria hold |
| **G2 MVP accepted** (proposed) | P2 → P3 (T3 → pilot) | SB-7 to SB-13 Done; all REQ-1 to REQ-8 acceptance criteria shown with evidence in the PRs; a beta version passes `install-and-test` on a plain scratch org and on the sandbox; REQ-12 to REQ-15 either Approved and met, or explicitly deferred by Alex; no open Defect of high severity | Proposed here; Alex confirms or changes it when deciding G1 |
| **G3 Pilot accepted** (proposed) | P3 → next accelerator | Promoted version installed in one client org; the client's residency and model-terms questions (C-data section 7, Phase D section 8) answered in Notion; pilot sponsor acceptance recorded by Alex in Notion only (SP-1) | Proposed here; Alex confirms or changes it when deciding G1 |

Between gates, every PR still passes the story flow in AGENTS.md (Ready for Dev only from an Approved requirement, an Approved ADR and a spec; QA review; Alex merge). Package promotion and tags are Alex actions (SB-12 spec 8), so they act as release gates inside P3.

## 6. Migration plan (Phase F)

### 6.1 Sequence

```
P1 Architecture (now)
  merge #7 SB-7, #8 SB-13 ─┬─ #6 B, #10 C-data, #13 C-app, #17 D, this PR (E-F)
  then #11 SB-8, #12 SB-12, #14 SB-9, #15 SB-10, #16 SB-11, #5 traceability
  promote A to F to Baseline ──► G1 Design approved
                                     │
P2 MVP build                         ▼
  T1:  WP-7 contracts ──► 8a compiler/push          12a package skeleton (parallel with WP-7)
                                                         │
  T2:                            8b storage/import ◄─────┘
                                     │
                                 9a core + /nodes ──► 9b search + context ──► 10a Apex API
                                                            │
  T3:                                   11a actions ◄───────┘ ──► 11b agent sample (PRE-6)
                     8c e2e (PRE-4) ──► 9c e2e ──► 12b install verification + sandbox (PRE-5)
                                     ──► G2 MVP accepted (proposed)
P3 Harden + pilot
  Alex promotes and tags the tested version ──► pilot client sandbox ──► production ──► G3 (proposed)
```

The merge order in P1 follows the QA Merge PR items: SB-7 first because every spec cites it; SB-9 before SB-10 and SB-11; SB-8 before SB-12 because SB-12 cites error codes SB-8 defines.

### 6.2 Critical path and parallel work

- **Critical path:** G1 → 12a → 8b → 9a → 9b → 11a → 12b. It runs through the package skeleton, not the contracts, because 8b and 9a need `packages/salesforce/` from 12a.
- **Parallel with the critical path:** WP-7 and 8a (Python toolchain, no org needed); 10a once 9b merges, alongside 11a.
- **Externally gated:** 8c, 9c and 12b need PRE-4 and PRE-5; 11b needs PRE-6. They can trail the code slices without blocking them, but G2 waits on them.
- **One slice per Developer PR**, so the merge queue never holds two slices of the same story at once.

### 6.3 Timing

The only dated target is the proposed success metric "one client pilot by late January 2027" (REQ-14, Needs Alex). P2 has 9 code slices and 3 evidence slices. With 12 PRs waiting and no merge since PR #9, the pilot date is at risk unless P1 merges soon and PRE-2 to PRE-5 are answered with G1. This is a risk statement, not a schedule commitment; the Project Manager owns dates on the Sprint Board.

### 6.4 Rollback and coexistence

- There is no legacy system to migrate from, so there is no cut-over. Each transition adds to `main`; a bad slice is reverted by a normal PR.
- Package versions are additive. A failed beta is never promoted. A client keeps the previous promoted version until Alex promotes a fixed one.
- Knowledge loads are all-or-nothing with the prior bundle staying live (SB-7 4.4, SB-8 7.3), so a bad vault commit never empties a client org.

## 7. Migration risks

| # | Risk | Effect | Mitigation |
|---|---|---|---|
| RM-1 | P1 PRs stay unmerged | G1 cannot pass; P2 cannot start; rebase churn grows (12 open PRs) | One merge round in the order of section 6.1; RM scope-change items already propose slowing idle agents |
| RM-2 | Account actions (PRE-4 to PRE-6) arrive late | T3 evidence and G2 slip, even with all code merged | Code slices proceed without them; evidence slices trail |
| RM-3 | Experiments in 9a, 10a, 11a, 12a (for example SOSL in triggers, Agentforce packaging) contradict a spec assumption | Rework in later slices | Experiments run in the first slice of each story, results go in the PR description, and the TA revises the spec before the next slice |
| RM-4 | REQ-12 to REQ-15 answered late or with stricter terms (for example per-note access) | G2 acceptance bar moves; kg-bundle may need an optional `access` object (C-data GD-2) | A minor contract version, per SB-7 7; no change to the transition order |
| RM-5 | Spec drift between Phase C and the later SB-9 spec (extension hook shape) | Documents disagree | Noted by QA on PR #13; whichever merges second aligns, and the Baseline pass fixes Phase C |
| RM-6 | Regulated pilot needs a self-hosted runner or a government Salesforce offering | Pilot set-up time | Phase D GT-2 and section 8; per-pilot checklist in Notion, no platform change |

## 8. Gap closure

Every gap recorded in Phases B to D is closed by a work package, a prerequisite, or an existing Inbox item.

| Gap | Closed by |
|---|---|
| GB-1 runtime-neutral definition | WP-7 |
| GB-2 vault into org | WP-8 |
| GB-3 knowledge services in any channel | WP-9, WP-10, WP-11 |
| GB-4 releasable package | WP-12; PRE-4 |
| GB-5 IP line only a principle | WP-13; 12a `package-check` |
| GB-6, GA-2, GD-2 access granularity | PRE-7 (REQ-15) |
| GB-7 acceptance demo and install bar | PRE-7 (REQ-12, REQ-13) |
| GB-8 no pilot | PRE-8 (REQ-14) |
| GA-1 no spec for SB-9 to SB-11 | Closed: specs written (PRs #14 to #16) |
| GA-3 folder owners | PRE-2 |
| GA-4, GT-4 agent-added workflows | PRE-3 |
| GA-5, GD-1, GT-1 hosting | Not needed for the MVP; existing EA Inbox question |
| GA-6, GT-3 account actions | PRE-4 to PRE-6 |
| GA-7, GD-7, GT-7 links to open PRs | PRE-1, then the Baseline pass |
| GD-3 hard-purge policy | WP-8 slice 8b (SB-8 spec 8; Alex confirms per pilot) |
| GD-4, GT-2 runner location | Per-pilot client choice (P3); the AC-5 template supports both |
| GD-5 bundle artifact retention | WP-8 slice 8a (SB-8 spec 5.3) |
| GD-6 model terms | Per-pilot checklist (P3, G3) |
| GT-5 `python build.py` fails on `main` | Existing TA FYI item; Alex-owned files |
| GT-6 usage budget | PRE-9 |

## 9. Requirement traceability

| Requirement | Status | Work packages | Transition | Gate evidence |
|---|---|---|---|---|
| REQ-1 Knowledge-graph sync | Approved, Must | WP-8 | T1 (8a), T2 (8b), T3 (8c) | G2 |
| REQ-2 REST service calls | Approved, Must | WP-9 | T2, T3 (9c) | G2 |
| REQ-3 Apex service calls | Approved, Must | WP-10 | T2 | G2 |
| REQ-4 Agentforce actions | Approved, Must | WP-11 | T3 | G2 |
| REQ-5 Clean 2GP install | Approved, Must | WP-12 | T1 (12a), T3 (12b) | G2 |
| REQ-6 Clear IP line | Approved, Must | WP-13, WP-12 (`package-check`) | T1 | G2 |
| REQ-7 Work logged in Notion | Approved, Must | None needed (factory practice) | T0 | Every gate |
| REQ-8 Runtime-neutral contracts | Approved, Should | WP-7, WP-8 (8a) | T1 | G1 (design), G2 (build) |
| REQ-9 to REQ-11 | Won't (MVP) | None | – | – |
| REQ-12 Zero-manual-step install | Needs Alex | WP-12 if Approved | T3 | Pending Alex |
| REQ-13 End-to-end Agentforce answer | Needs Alex | WP-11 if Approved | T3 | Pending Alex |
| REQ-14 One client pilot by late January 2027 | Needs Alex | P3 pilot (no WP) | After T3 | G3, pending Alex |
| REQ-15 Governed access | Needs Alex | WP-9 if Approved | T2 | Pending Alex |

Every work package maps to one of SB-7 to SB-13, and every Approved requirement maps to at least one work package or to existing factory practice.

## 10. ADR and spec alignment check

| Source | Statement | This document |
|---|---|---|
| ADR-001 decision 1 | One namespaced base package; extensions separate and dependent | WP-12, WP-13; extension packages are not work packages here |
| ADR-001 decision 2 | Sync option A: compile in CI, push to the import endpoint | WP-8 slices 8a and 8b |
| ADR-001 decision 4 | Options B2 and C are later adapters | Section 2.1, hosting not a work package |
| ADR-002 | Hybrid runtime is a factory capability with its own phased rollout | Section 2.1, outside this roadmap |
| SB-8, SB-9, SB-10, SB-11, SB-12 specs, section 2 | Slice contents and dependencies | Section 2 and 6.1 repeat them by reference |
| SB-12 spec 2 and 8 | 12a is the first Salesforce PR after G1; Alex promotes and tags | Sections 5 and 6 |

No conflict found.

## 11. Next ADM steps

1. After PRs #6, #10, #13, #17 and this one merge: promote principles, A, B, C-data, C-application, D and E-F to Baseline in one PR, replacing PR links with `main` paths.
2. Then raise the single G1 Inbox item with evidence, including the proposed G2 and G3 definitions in section 5 for Alex to confirm.
3. Phase G (implementation governance) and Phase H (change management) are carried out by the existing story flow, QA review and gates; no separate document is planned unless Alex asks for one.
