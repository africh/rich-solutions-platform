# Phase C: Application Architecture

- **Status:** Draft
- **Date:** 2026-10-21
- **Owner:** Enterprise Architect
- **Story:** SB-15 "TOGAF Phases B to F: Business, Data, Application, Technology, Opportunities & Migration" (Notion Sprint Board)
- **Sources:** Notion Vision Brief (approved 2026-10-13, gate G0), [`GOAL.md`](../../GOAL.md), Notion Requirements database
- **Related requirements:** REQ-1 to REQ-8 (Approved); REQ-12 to REQ-15 (Needs Alex); see [`docs/requirements/traceability.md`](../requirements/traceability.md)
- **Related ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) 2GP package structure and knowledge-graph sync (Approved 2026-10-15); [ADR-002](../adr/ADR-002-hybrid-agent-runtime.md) hybrid cloud/local agent runtime (Approved). No new ADR is proposed here.
- **Related specs and designs (open PRs, not yet on `main`):** `docs/specs/SB-7.md` contracts (PR #7); `docs/specs/SB-8.md` sync (PR #11); `docs/specs/SB-12.md` package project (PR #12); `docs/design/ip-boundary.md` (PR #8, SB-13)
- **Previous:** Phase B Business Architecture (`B-business.md`, PR #6), Phase C Data Architecture (`C-data.md`, PR #10) · **Principles:** [principles.md](principles.md)

This phase names the application components that deliver the Phase B business services and carry the Phase C data flows, and the interfaces between them. It is the enterprise view. Component internals, field lists and class designs belong to the Technical Architect's specs; where a spec or ADR already defines something, this document points to it instead of restating it (AP-1, one definition).

Nothing here changes an Approved ADR. If a later spec needs to differ from this document, the spec wins for detail and this document is updated; if it would differ from ADR-001 or ADR-002, a new ADR is needed first.

## 1. Application principles applied

| Principle | What it means for applications |
|---|---|
| AP-1 Runtime-neutral contracts | Every product component conforms to `contracts/kg-bundle` and `contracts/services`. Runtime components are adapters to them |
| AP-2 One service core, many thin exposures | REST, Apex and Agentforce components hold no business logic; they call one service core |
| AP-3 Model and vendor swappability | The base package makes no model call of its own; grounding goes through the org's configured Agentforce model path |
| BP-2 Clear IP line | Client logic plugs in only through `global` Contract-layer interfaces from a separate extension package (ip-boundary design) |
| TP-1 No new hosting by default | MVP components run only in GitHub Actions, a developer workstation, or the client's Salesforce org. No hosted service is introduced |
| TP-2 Clean, repeatable install | Every in-org component ships in the one base package and works with no post-install hand edits |
| SP-2 Least privilege | Each caller type has its own permission set; the import path and read path use different permissions |

## 2. Application landscape

Components fall into three groups. Only the first two are product (Rich Solutions IP shipped to clients); the third is the factory that builds them.

| Group | Runs in | Components |
|---|---|---|
| **G1 Runtime-neutral toolchain** | This repo (definitions), the vault repo's CI, a developer workstation | Contracts, contracts-check, kg-compiler, kg-push, vault-sync workflow template |
| **G2 Salesforce base package** (accelerator #1) | The client's Salesforce org | Contract, Storage, Service and Exposure layers (ADR-001), plus admin and permission components |
| **G3 Factory** (not shipped) | Notion, GitHub, scheduled cloud agent runs, an optional local agent (ADR-002) | Agent team, Notion Agent Team HQ, GitHub repo and PR flow, CI checks, local agent runtime |

Client-side applications that the platform depends on but does not build: the client's Obsidian vault repository and its GitHub Actions, the client's Salesforce org (with Agentforce where used), and the client's own extension package, if any.

## 3. Application components

### 3.1 Runtime-neutral toolchain (G1)

| ID | Component | Responsibility | Defined by | Story | Requirements |
|---|---|---|---|---|---|
| AC-1 | **Contracts**: `contracts/kg-bundle/v1`, `contracts/services/v1` | Source of truth for the bundle format, import pages, service operations, results and errors; MCP-style tool manifest for the read operations | ADR-001 decision 3; SB-7 spec sections 3 and 4 | SB-7 | REQ-8, REQ-2, REQ-3, REQ-4 |
| AC-2 | **contracts-check** (`tools/contracts-check`) | Validates schemas, examples and the OpenAPI document; runtime-neutrality token scan; neutral consumer test; shared validation library for AC-3 | SB-7 spec section 6; SB-8 spec section 4.2 | SB-7, SB-8 | REQ-8 |
| AC-3 | **kg-compiler** (`tools/kg-compiler`) | Turns a vault at one commit into a deterministic, validated bundle and import pages. The only Obsidian parser in the platform | SB-8 spec section 4 | SB-8 | REQ-1, REQ-8 |
| AC-4 | **kg-push** (`tools/kg-push`) | Sends import pages to a runtime's import operations and polls status. Runtime-neutral apart from one auth adapter per runtime | SB-8 spec section 5.1 | SB-8 | REQ-1 |
| AC-5 | **Vault-sync workflow template** (`templates/vault-sync`) | GitHub Actions workflow a client copies into the vault repo: compile, validate, push, report. Holds no secrets; secrets live in the vault repo | SB-8 spec section 5.2 | SB-8 | REQ-1 |

### 3.2 Salesforce base package (G2)

Layers follow ADR-001 decision 1. Each layer depends only on the one below it; Exposure depends on Contract and Service, never on Storage directly.

| ID | Layer | Component | Responsibility | Defined by | Story | Requirements |
|---|---|---|---|---|---|---|
| AC-10 | Contract | **Contract interfaces and DTOs** (`KnowledgeService`, `KnowledgeQuery`, `KnowledgeResult` and related types) | Apex mirror of `contracts/services`; the only `global` surface extensions may reference | ADR-001 Part 1; ip-boundary section 3.1 | SB-9, SB-10 | REQ-3, REQ-6, REQ-8 |
| AC-11 | Storage | **Knowledge store objects** (bundle, page, node, chunk, tag, edge set, edge; sync settings) | Versioned runtime store for committed bundles and import records | SB-8 spec section 6 | SB-8 | REQ-1 |
| AC-12 | Storage | **KnowledgeStore** | The only reader of "current" rows; shared by import and read paths | SB-8 spec section 3 | SB-8, SB-9 | REQ-1 |
| AC-13 | Service | **Import service** (intake, validation, commit step runner, resume and purge jobs) | Implements SB-7 import semantics (section 4.4): idempotent pages, all-or-nothing commit, prior bundle stays live, supersede, purge | SB-8 spec sections 7 and 8 | SB-8 | REQ-1 |
| AC-14 | Service | **Knowledge service core** (implements `KnowledgeService`) | `getNode`, `searchNodes`, `getNeighbors`, `getContext`; chunk reassembly; citations; error mapping to the SB-7 envelope. All read logic lives here once | ADR-001 Part 1; SB-7 section 4 | SB-9 | REQ-2, REQ-3, REQ-4 |
| AC-15 | Service | **Extension resolver** | Picks the `KnowledgeService` implementation (base default, or a configured extension class) without naming extension types | ip-boundary section 3.1 rule 2 | SB-9 | REQ-6 |
| AC-16 | Exposure | **Import REST resource** (`/knowledge/v1/bundles/*`) | HTTP adapter for `importBundlePage` and `getImportStatus`; admin path only, not offered to agents | SB-7 section 4.1; SB-8 spec section 3 | SB-8 | REQ-1 |
| AC-17 | Exposure | **Read REST resources** (`/knowledge/v1/nodes`, `/search`, `/context`) | HTTP adapters for the read operations | SB-7 section 4.1 | SB-9 | REQ-2 |
| AC-18 | Exposure | **Global Apex API** | Subscriber-org Apex entry points for each read operation; same results as REST for the same input; documented catchable exception | ADR-001 Part 1 | SB-10 | REQ-3 |
| AC-19 | Exposure | **Agentforce actions** (`@InvocableMethod`) | Agent-facing adapters for the tool-manifest operations; explicit no-answer result when nothing matches | ADR-001 Part 1; SB-7 tool manifest | SB-11 | REQ-4, REQ-13 |
| AC-20 | Admin | **Package info and permission sets** (`Knowledge_Admin`, `Knowledge_Sync`, and a read permission set for callers) | Version info for install checks; least-privilege access per caller type | SB-12 spec section 3; SB-8 spec section 5.2 | SB-12, SB-8, SB-9 | REQ-5, REQ-15 |
| AC-21 | Admin | **package-check** (`tools/package-check`) and install scripts | Static dependency check (no extension dependency) and post-install component verification | SB-12 spec sections 6 and 7; ip-boundary section 4 | SB-12 | REQ-5, REQ-6 |

AC-21 lives in `tools/` but checks the Salesforce package only, so it is grouped here.

Agent metadata that cannot be packaged (agent definitions, topic assignment) lives in `packages/salesforce/unpackaged/agentforce/` as a generic sample (SB-12 spec section 3). It is a template, not a product component; client agents and prompts are extension work.

### 3.3 Factory (G3)

| ID | Component | Responsibility | Defined by |
|---|---|---|---|
| AC-30 | **Cloud agent team** (seven scheduled roles) | Requirements, architecture, specs, build, review, reporting | `AGENTS.md`; Notion Agent Team HQ |
| AC-31 | **Notion Agent Team HQ** | System of record for status: Sprint Board, Requirements, Decisions Log, Defects, Operator Inbox, Handoff Log, Reports, Roadmap | Notion |
| AC-32 | **GitHub repository and PR flow** | System of record for architecture content and code; branch protection; Alex-only merge | `AGENTS.md` |
| AC-33 | **CI checks** (`build-smoke-test`, and proposed `contracts-check` and `package-ci` workflows) | Automated checks on PRs | `.github/workflows/` (Alex-owned; new workflows pending the Inbox decision on agent-added workflow files) |
| AC-34 | **Local agent runtime** (sandboxed, local-only profile) | Bounded L0/L1 tasks under cloud review, entering only as `runtime:local` PRs | ADR-002; `docs/design/hybrid-agent-runtime.md` |

The factory is in scope for architecture governance (REQ-7) but is never shipped to a client and never reads client data.

## 4. Application services

Each Phase B business service maps to one or more application services. The operation names are the SB-7 `operationId`s, so every channel offers the same service.

| Business service (Phase B) | Application service | Operations | Provided by | Channels |
|---|---|---|---|---|
| Publish knowledge | Knowledge publication | compile, validate, `importBundlePage`, `getImportStatus` | AC-3, AC-2, AC-4, AC-5 → AC-16 → AC-13 | CI only (admin HTTP) |
| Look up knowledge | Knowledge retrieval | `getNode`, `searchNodes`, `getNeighbors` | AC-14 via AC-17, AC-18, AC-19 | REST, Apex, Agentforce |
| Answer a question from knowledge | Grounding context | `getContext` | AC-14 via AC-19 (also AC-17, AC-18) | Agentforce (REST and Apex for testing and custom agents) |
| Install and upgrade the accelerator | Package install and verification | version create, install, verify | AC-20, AC-21 | Salesforce package install |
| Extend the accelerator for one client | Extension hook | `global` `KnowledgeService` interface, extension resolver | AC-10, AC-15 | Client extension package (outside this repo) |
| Decide and approve | Governance | Inbox items, ADR status, PR review and merge | AC-31, AC-32 | Notion, GitHub |

## 5. Interfaces

### 5.1 Interface catalogue

| ID | From → To | Interface | Contract | Protocol and auth | Data flow (Phase C) |
|---|---|---|---|---|---|
| IF-1 | Knowledge author → vault repo | Git push | Obsidian Markdown conventions | Git over HTTPS; client's GitHub access control | DF-1 |
| IF-2 | Vault repo → AC-5 workflow | GitHub Actions trigger | Workflow template | Push to default branch, or manual dispatch | DF-2 |
| IF-3 | AC-3 → AC-2 | Library call | `kg-bundle.schema.json`, `kg-bundle-page.schema.json` | In-process | DF-3 |
| IF-4 | AC-4 → AC-16 | `importBundlePage`, `getImportStatus` | `knowledge-services.openapi.yaml` (SB-7 4.1) | HTTPS; bearer token from the CI-only connected app (JWT), key in vault-repo secrets; `Knowledge_Sync` permission set | DF-4 |
| IF-5 | AC-16 → AC-13 → AC-11 | Internal Apex | Service layer | In-org; asynchronous commit jobs | DF-5 |
| IF-6 | External caller → AC-17 | Read REST operations | OpenAPI read operations | HTTPS; caller's Salesforce authentication and read permission set | DF-6 |
| IF-7 | Subscriber-org Apex → AC-18 | Global Apex API | Contract-layer DTOs mirroring OpenAPI schemas | In-org; running user's permissions | DF-6 |
| IF-8 | Agentforce agent → AC-19 | Invocable actions | `tool-manifest.json` input and output schemas | In-org; agent user's permissions | DF-6 |
| IF-9 | AC-19 result → org's model | Grounding passages with citations | `ContextResult` | Salesforce's own Agentforce model path; the package adds no model call | DF-7 |
| IF-10 | Client extension → AC-10 / AC-15 | `global` interface implementation, chosen by configuration | Contract-layer `global` members (versioned as SB-7 section 7) | In-org; one-way dependency, extension depends on base | – |
| IF-11 | Agents ↔ AC-31, AC-32 | Notion connector, Git, GitHub | `AGENTS.md`, HQ rules | Agent credentials held by the platform, never in the repo | DF-8 |

### 5.2 Interface rules

1. **One contract per interface.** IF-4, IF-6, IF-7 and IF-8 all derive from `contracts/services/v1`. An adapter that needs a field the contract lacks raises a contract change (SB-7 section 7), never a local addition.
2. **Same answer on every channel.** For the same input and the same committed bundle, IF-6, IF-7 and IF-8 return equivalent results and the same error codes (SB-10 acceptance criterion; SB-7 section 4.3).
3. **Import is not an agent tool.** IF-4 is admin-only. The tool manifest lists read operations only, so no agent can write knowledge (C-data flow rule 1, single writer).
4. **Reads never see a half-import.** Reads serve the last committed bundle until the next commit finishes (SB-7 section 4.4 rule 2).
5. **No outbound calls from the base package in the MVP.** No Named Credential, no callout and no external model call. Pull-based delivery (ADR-001 option B2) or an external service (option C) would add one, and each needs its own story first.
6. **Extensions are one-way.** Base code never names an extension type (ip-boundary section 3.1). IF-10 is the only extension interface; extension contract data travels in the bundle's namespaced `extensions` object.

## 6. Key interactions

### 6.1 Knowledge change to queryable knowledge (VS-2, first half)

```
author ─IF-1─► vault repo ─IF-2─► AC-5 workflow
                                    │ AC-3 compile  ─IF-3─► AC-2 validate ──invalid──► workflow fails, nothing sent
                                    │ valid
                                    ▼
                                  AC-4 kg-push ─IF-4 pages─► AC-16 import resource ─► AC-13 intake
                                                                                       │ all pages in
                                                                                       ▼
                                                                         AC-13 commit runner ─► AC-11 store
                                  AC-4 ◄─IF-4 getImportStatus (committed / failed)─────┘
```

A failed import leaves the previous bundle live and reports the failure through the workflow run (REQ-1 acceptance criteria; SB-8 spec).

### 6.2 Governed question to grounded answer (VS-2, second half)

```
end user ─► Agentforce agent ─IF-8─► AC-19 action ─► AC-15 resolver ─► AC-14 service core ─► AC-12 store
                     ▲                                                     │
                     └──IF-9 passages + citations (or explicit no-answer)◄─┘
```

The same core answers IF-6 (REST) and IF-7 (Apex) calls, which is what makes the REST/Apex parity test in SB-10 meaningful.

### 6.3 Client extension (VS-3 and BP-PR-3)

A client extension package, built outside this repo, implements the `global` `KnowledgeService` interface (or a narrower hook the SB-9 spec defines) and is selected by a configuration record. Removing the extension falls back to the base default with no code change.

## 7. Application and the IP line

| In this repo (Rich Solutions IP) | Outside this repo (client, billable) |
|---|---|
| AC-1 to AC-5, AC-10 to AC-21, generic templates and samples | The vault repository, its content, its secrets and any client-specific compiler config |
| `global` extension interfaces and their defaults | Extension packages implementing those interfaces |
| Generic unpackaged Agentforce sample | Client agents, topics, prompts and instructions |
| Factory components AC-30 to AC-34 (definitions, not client data) | Client org configuration, credentials and connected apps |

The ip-boundary design (SB-13) is the detailed rule; this table only places each component on the right side.

## 8. Runtime neutrality: what a second runtime reuses

Vision Brief "Future enhancements" asks that a non-Salesforce runtime reuse, not fork. In application terms:

| Reused unchanged | Rebuilt per runtime (thin) |
|---|---|
| AC-1 contracts, AC-2 contracts-check, AC-3 kg-compiler, AC-5 workflow template | Store (AC-11/AC-12 equivalent) |
| AC-4 kg-push, except its auth adapter | Import semantics implementation (AC-13 equivalent), held to SB-7 section 4.4 |
| The neutral consumer test (SB-7 section 6 step 6) as the conformance starting point | Service core (AC-14 equivalent) and the runtime's exposures, for example an MCP server or HTTP service |

A second runtime is out of MVP scope (REQ-9, Won't). Where it would be hosted is the open hosting question (Phase D).

## 9. ADR and spec alignment check

| Source | Statement | This document |
|---|---|---|
| ADR-001 decision 1 | One namespaced base package, four layers, extensions as separate dependent packages | Section 3.2 layers; IF-10; section 7 |
| ADR-001 decision 2 | Sync option A: compile in CI, push through the package's own import endpoint | AC-3 to AC-5, IF-4, section 6.1 |
| ADR-001 decision 3 | Contracts are the source of truth; Salesforce code is adapters | Section 5.2 rule 1; AC-1 |
| ADR-001 decision 4 | B2 and C stay open as later delivery adapters | Section 5.2 rule 5: not in MVP, need their own story |
| SB-7 section 4.1 | Import path refined to `POST /bundles/{bundleId}/pages`; import not in tool manifest | IF-4; section 5.2 rule 3 |
| ADR-002 | Cloud-governed hybrid runtime; local output only as reviewed PRs | AC-34 is a factory component only; it never touches G1 or G2 runtime data |

No conflict found.

## 10. Requirement traceability

| Requirement | Status | Application components | Interfaces | Covered |
|---|---|---|---|---|
| REQ-1 Knowledge-graph sync | Approved, Must | AC-3, AC-4, AC-5, AC-11, AC-12, AC-13, AC-16 | IF-1 to IF-5 | Yes |
| REQ-2 REST service calls | Approved, Must | AC-14, AC-17 | IF-6 | Yes |
| REQ-3 Apex service calls | Approved, Must | AC-10, AC-14, AC-18 | IF-7 | Yes |
| REQ-4 Agentforce actions | Approved, Must | AC-14, AC-19 | IF-8, IF-9 | Yes |
| REQ-5 Clean 2GP install | Approved, Must | AC-20, AC-21 (all G2 components ship in the one package) | – | Yes |
| REQ-6 Clear IP line | Approved, Must | AC-10, AC-15, AC-21; section 7 | IF-10 | Yes |
| REQ-7 Work logged in Notion | Approved, Must | AC-30, AC-31, AC-32 | IF-11 | Yes |
| REQ-8 Runtime-neutral contracts | Approved, Should | AC-1, AC-2, AC-3, AC-4; section 8 | IF-3, IF-4 | Yes |
| REQ-9 to REQ-11 | Won't (MVP) | None built; section 8 records reuse for REQ-9 | – | Out of scope |
| REQ-12 Zero-manual-step install | Needs Alex | AC-21 | – | Pending Alex |
| REQ-13 End-to-end Agentforce answer | Needs Alex | AC-19, AC-14 (citations already in `ContextResult`) | IF-8, IF-9 | Pending Alex |
| REQ-14 One client pilot by late January 2027 | Needs Alex | No component; deployment of G2 at one client | – | Pending Alex |
| REQ-15 Governed access | Needs Alex | AC-20 permission sets; `FORBIDDEN` error and `securitySchemes` reserved in AC-1 | IF-6 to IF-8 | Pending Alex |

## 11. Gaps and open items

| ID | Gap | Impact | Handling |
|---|---|---|---|
| GA-1 | No spec yet for SB-9, SB-10, SB-11 (service core, Apex API, Agentforce actions) | AC-14, AC-15, AC-17 to AC-19 are named here but not designed | Technical Architect specs; they should keep the section 5.2 rules. Extension hook shape (AC-15) to be fixed in the SB-9 spec |
| GA-2 | REQ-15 access granularity | Decides whether one read permission set is enough or per-note access is needed | Existing Business Analyst Inbox item (REQ-12 to REQ-15) |
| GA-3 | Owners for `contracts/`, `tools/`, `templates/`, `packages/` in AGENTS.md | Components AC-1 to AC-5 and AC-10 to AC-21 have no folder owner yet | Existing Technical Architect Inbox Blocker of 2026-10-15 |
| GA-4 | Agent-added CI workflows (AC-33) | `contracts-check` and `package-ci` may run locally only | Existing Technical Architect Inbox item on `.github/workflows/` |
| GA-5 | Hosting outside Salesforce | Only matters for ADR-001 options B2 or C and for a second runtime; MVP components need none | Existing Enterprise Architect Inbox question; Phase D records both options |
| GA-6 | Account actions (Dev Hub, namespace, connected app, sandbox) | AC-16 and AC-20 cannot be proven end to end until they exist | Existing Technical Architect Inbox item on account actions |
| GA-7 | Phase B, Phase C Data and the SB-7, SB-8, SB-12, SB-13 documents are in open PRs | This document cites them by PR | Update links to `main` paths once merged |

None of these gaps needs a new ADR or blocks the SB-7 to SB-13 specs.

## 12. Next ADM steps

1. Phase D Technology Architecture (`D-technology.md`): platforms, environments (scratch org, sandbox, Dev Hub, GitHub Actions runners) and hosting. It records the hosting question and the self-hosted runner option as gaps, not choices.
2. Phases E to F (`E-F-roadmap.md`): work packages mapped to SB-7 to SB-13, transition architectures and gates.
3. Promote Phases A to D to Baseline after their PRs merge, then propose gate G1 once the core ADRs are Approved (ADR-001 and ADR-002 already are).
