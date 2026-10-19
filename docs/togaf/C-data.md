# Phase C: Data Architecture

- **Status:** Draft
- **Date:** 2026-10-19
- **Owner:** Enterprise Architect
- **Story:** SB-15 "TOGAF Phases B to F: Business, Data, Application, Technology, Opportunities & Migration" (Notion Sprint Board)
- **Sources:** Notion Vision Brief (approved 2026-10-13, gate G0), [`GOAL.md`](../../GOAL.md), Notion Requirements database
- **Related requirements:** REQ-1, REQ-5, REQ-6, REQ-7, REQ-8 (Approved); REQ-12 to REQ-15 (Needs Alex); see [`docs/requirements/traceability.md`](../requirements/traceability.md)
- **Related ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) 2GP package structure and knowledge-graph sync (Approved 2026-10-15). No new ADR is proposed here.
- **Related specs and designs (open PRs, not yet on `main`):** `docs/specs/SB-7.md` kg-bundle v1 and knowledge services v1 (PR #7); `docs/design/ip-boundary.md` (PR #8, SB-13)
- **Previous:** [Phase A Architecture Vision](A-vision.md), Phase B Business Architecture (`B-business.md`, PR #6) · **Principles:** [principles.md](principles.md)

This phase describes the data the platform handles, who owns it, how it moves, and where it may live. It is the enterprise view: it names entities, flows and rules, and leaves field-level design to the Technical Architect's specs. Where the SB-7 spec already defines a structure, this document points to it instead of restating it, so the contract stays defined once (AP-1).

Engagements are described generically (SP-1). Client and pilot specifics live only in Notion.

## 1. Data principles applied

| Principle | What it means for data |
|---|---|
| DP-1 Knowledge is a governed, versioned asset | The vault is the only place knowledge is edited. Every runtime holds a snapshot that names its source commit and content hash. |
| DP-2 Data residency and least data | Client knowledge stays in the client's GitHub and the client's Salesforce org. Rich Solutions stores none of it. |
| AP-1 Runtime-neutral contracts | The bundle format and service result shapes carry no Salesforce types. Runtime storage is a mapping of the logical model, not its definition. |
| SP-1 Public-repo IP hygiene | This repo holds only contracts, schemas and synthetic samples. Never vault content, bundles from real vaults, org IDs or credentials. |
| SP-2 Least privilege and governed access | Reads go through the service layer with the caller's permissions. Credentials are scoped to one purpose. |
| BP-2 Clear IP line | Client data and client-specific data extensions belong to the client side of the line (see section 6). |

## 2. Data domains

| Domain | What it holds | System of record | Owner (accountable) | Steward (day to day) |
|---|---|---|---|---|
| **D1 Knowledge content** | Notes, attachments, links, tags, frontmatter | Client vault repository (GitHub) | Client (business sponsor) | Knowledge authors |
| **D2 Knowledge snapshots** | Compiled bundles and import pages | Derived from D1. The CI build output is transient; the loaded copy lives in each runtime | Client | Client Salesforce admin, CI pipeline |
| **D3 Runtime knowledge store** | Nodes, edges, chunks and import records loaded into a runtime | Client Salesforce org (MVP); other runtimes later | Client | Client Salesforce admin |
| **D4 Service interactions** | Queries, results, context passages, citations, errors | Transient. Not persisted by the base package in the MVP | Client | – |
| **D5 Contracts and reference data** | JSON Schemas, OpenAPI, tool manifest, synthetic sample vault and bundles | This repository (`contracts/`, per ADR-001) | Rich Solutions | Technical Architect |
| **D6 Factory governance data** | Requirements, stories, ADR rows, defects, handoffs, reports, Inbox | Notion Agent Team HQ (private); ADR text and specs in this repo | Rich Solutions (Alex) | Agent team |
| **D7 Credentials and secrets** | CI connected-app key, any tokens | GitHub Actions encrypted secrets in the vault repo; the client org | Client (for its org); Alex (for Rich Solutions accounts) | Whoever administers that store |
| **D8 Package metadata** | Package versions, namespace, install state | Salesforce Dev Hub and subscriber orgs | Rich Solutions (versions); client (installs) | Developer, client admin |

## 3. Logical data model

### 3.1 Entities

The logical model is runtime-neutral. Section 3.3 maps it to the kg-bundle v1 contract and to Salesforce storage.

| Entity | Domain | Description | Key | Notes |
|---|---|---|---|---|
| Vault | D1 | One Git repository of Markdown notes | Repo label + ref | Opaque label only, never a URL with credentials |
| Note | D1 → D3 | One Markdown file with optional YAML frontmatter | Node id (slug of vault path) | Stable while the file is not moved or renamed |
| Attachment | D1 → D3 | A non-Markdown file referenced by notes | Node id | Metadata only in v1. Binary content is not synced |
| Link | D1 → D3 | A directed relation between two notes: wikilink, embed, tag or frontmatter relation | Source id + target id + type + relation + anchor | Unresolved links are kept and flagged, not dropped |
| Tag | D1 → D3 | A label on a note | Tag text (lower-case, nested with `/`) | Stored on the note; also expressible as a `tag` link |
| Chunk | D3 | One slice of a note body that exceeds a runtime's field limit | Node id + index | Created by the compiler from a neutral size parameter |
| Bundle | D2 → D3 | One compiled, validated snapshot of a vault at one commit | `<repo-slug>@<commit>` | Carries content hash, generator version and stats |
| Bundle page | D2 | One import unit of a bundle | Bundle id + page index | Grouping and retry unit for import |
| Import record | D3 | The state of one bundle's import into one runtime | Bundle id | States: receiving, committed, failed, superseded |
| Query | D4 | A service call: get, search, neighbours or context | – | Transient |
| Result / passage | D4 | What a service returns, including passages for agent grounding | – | Each passage carries a citation of `<path>@<commit>` |
| Extension data | D1/D3 (client side) | Client-specific keys in the bundle's namespaced `extensions` object | Namespaced key, e.g. `acme:priority` | Defined by the client, never by the base schemas |

### 3.2 Relationships

```
Vault 1 ──< Note 1 ──< Chunk
          │      └──< Link >── 0..1 Note        (target null = unresolved)
          └──< Attachment

Vault commit 1 ── 1 Bundle 1 ──< Bundle page ──< Note / Link   (as carried in the page)
Bundle 1 ── 1 Import record (per runtime)
Runtime store: exactly one committed Bundle is live at a time; Notes absent from it are deleted (not served)
Result ──< Passage ── 1 Note @ Bundle commit                   (citation)
```

### 3.3 Mapping across layers

| Logical entity | kg-bundle v1 (SB-7 spec, section 3) | Salesforce storage (ADR-001 Storage layer) | Future runtime |
|---|---|---|---|
| Bundle | `bundle`, `source`, `stats` | `Knowledge_Bundle__c` (one record per import, with commit SHA and status) | Any store that keeps the same fields |
| Bundle page | `kg-bundle-page` document | Not stored; processed per import call | Same |
| Import record | `ImportStatus` result shape | Status fields on `Knowledge_Bundle__c` | Same states and rules (SB-7 section 4.4) |
| Note / Attachment | `nodes[]` with `kind` | `Knowledge_Node__c`, upserted by node id | Same id and hash rules |
| Chunk | `nodes[].chunks[]` | Chunk records or fields, sized under the Long Text Area limit (131,072 chars) | Chunking optional when the store has no field limit |
| Link | `edges[]` | `Knowledge_Edge__c` | Same |
| Tag | `nodes[].tags` (and `tag` edges) | Field on the node; SOSL-searchable | Same |
| Extension data | `extensions` (namespaced) | Client extension package metadata, never base objects | Ignored unless the runtime knows the key |

Field names, types, indexes and sharing settings for the Salesforce objects belong to the Technical Architect's SB-8 and SB-9 specs. This table only fixes which logical entity each object realises, so the specs cannot drift from the contract.

## 4. Data flows

### 4.1 Flow summary

| # | Flow | From → To | Data | Trigger | Transport and protection | Requirements |
|---|---|---|---|---|---|---|
| DF-1 | Author | Knowledge author → vault repo | Note changes | Commit and push | Git over HTTPS, client's GitHub access control and review | REQ-1 |
| DF-2 | Compile | Vault repo → CI runner (`kg-compiler`) | Full vault at one commit → bundle | Push to the vault's tracked branch | Runs inside the vault repo's CI; no third-party service | REQ-1, REQ-8 |
| DF-3 | Validate | CI runner (contracts) | Bundle checked against `kg-bundle.schema.json` and semantic checks | After compile | Invalid bundle stops the flow; nothing is sent | REQ-8 |
| DF-4 | Import | CI runner → client org import endpoint | Bundle pages (default 200 nodes each) | After validation | HTTPS with a CI-only connected-app credential from GitHub Actions secrets (ADR-001) | REQ-1 |
| DF-5 | Commit | Import service → runtime store | Upserts, skips, deletions; import record | Last page received | Within the org; prior bundle stays live until commit; idempotent on retry | REQ-1 |
| DF-6 | Read | Runtime store → caller (REST, Apex, Agentforce action) | Node, search, neighbour and context results | Service call | Caller's Salesforce authentication and permissions (SP-2; granularity pending REQ-15) | REQ-2, REQ-3, REQ-4 |
| DF-7 | Ground | Agentforce action → the org's configured LLM | Context passages plus the user's question | Agent invokes a context action | Salesforce's own Agentforce model path inside the client's org; the base package adds no external model call | REQ-4, REQ-13 |
| DF-8 | Govern | Agents ↔ Notion and this repo | Requirements, stories, ADRs, logs, contracts, specs | Each agent run | Notion private workspace; public repo holds only public-class data (section 5) | REQ-7 |

### 4.2 Main flow

```
[Client GitHub]                          [Client CI runner]                      [Client Salesforce org]
 vault repo ──DF-1 commit──► push ──DF-2──► kg-compiler ──► bundle
                                              │ DF-3 validate
                                              ├─ invalid ─► fail the run, report to author, send nothing
                                              └─ valid ───DF-4 pages (HTTPS, CI credential)──► import service
                                                                                                │ DF-5 commit
                                                                                                ▼
                                                                                         knowledge store
                                                                                                │ DF-6 read
                                                        REST / Apex caller ◄────────────────────┤
                                                        Agentforce action ◄─────────────────────┘
                                                                │ DF-7 ground (passages + citation)
                                                                ▼
                                                        org's configured LLM ──► answer with sources, or no-answer
```

Every box in this flow is client-owned in the MVP. Rich Solutions supplies the code (package, compiler, contracts) and never handles client data. That is what keeps DP-2 true without a hosting decision.

### 4.3 Flow rules

1. **Single writer.** Only DF-5 writes knowledge into a runtime store. No user, admin or agent edits runtime knowledge records by hand (DP-1); the next import would overwrite them anyway.
2. **All or prior.** A bundle is live only when all its pages are committed. On any failure, reads keep serving the previous committed bundle (SB-7 section 4.4).
3. **Traceable answers.** Every result names the bundle id and commit it came from, and passages carry `<path>@<commit>` citations, so any answer can be traced back to a vault commit.
4. **No content in logs.** Import errors, service errors and CI logs carry ids, codes and counts, never note bodies or frontmatter values. CI logs on GitHub-hosted runners are visible to anyone with read access to the vault repo.
5. **No bundles in this repo.** Bundles compiled from real vaults are never committed to this repository, attached to its releases, or uploaded as its CI artifacts. Only synthetic samples live in `contracts/` (SP-1).

## 5. Data classification

| Class | Examples | May live in | Must never be in |
|---|---|---|---|
| **Public** | Contracts and schemas, synthetic sample vault and bundles, TOGAF docs, ADRs, specs | This repo, published package source | – |
| **Internal** | Notion factory data: Inbox items, handoffs, reports, pilot planning, defects | Notion private workspace | This repo (summaries without client detail are fine) |
| **Client confidential** | Vault content, compiled bundles, runtime knowledge records, service results, agent prompts and answers | Client vault repo, client CI, client Salesforce org | This repo, Notion, Rich Solutions accounts, agent transcripts |
| **Secret** | Connected-app private key, tokens, org IDs tied to a client | GitHub Actions encrypted secrets of the vault repo; the client org | Any file, log, issue, PR, Notion page or commit |

A sensitive client vault (for example one holding personal, student or payment data) stays in the "client confidential" class. The platform does not add a separate class for it; instead, section 7 lists the extra controls a regulated pilot needs.

## 6. Data and the IP line

Following BP-2 and the SB-13 IP-boundary design (PR #8):

| Base package side (Rich Solutions IP, this repo) | Client side (billable, outside this repo) |
|---|---|
| Logical model and kg-bundle schemas | Vault content and every bundle compiled from it |
| Generic storage objects and import logic | Client-specific fields, record types and data mappings |
| Generic compiler defaults | Client compiler configuration (relation keys, folder filters) |
| Synthetic sample vault | Real or realistic client data, including in tests |
| The namespaced `extensions` mechanism | The keys a client puts in `extensions` and the code that reads them |

The base package never reads an extension key by name. Client packages that need extra data use the `extensions` object or their own objects, not new fields on base objects.

## 7. Residency and compliance notes

GOAL.md assumes data residency and FedRAMP, StateRAMP, FERPA and PCI-aware controls for target sectors (A-vision CN-8). This section records where data goes and which questions a regulated pilot must answer. It does not claim any certification.

### 7.1 Where client data is processed in the MVP

| Location | Data | Who operates it | Residency note |
|---|---|---|---|
| Client vault repository (GitHub) | D1 | Client | Under the client's GitHub plan and settings |
| CI runner for the vault repo | D1 → D2, transient | Client's GitHub Actions | GitHub-hosted runners are shared cloud infrastructure. A self-hosted runner inside the client's boundary is an option for sensitive vaults (gap GD-4) |
| CI artifacts and logs | D2 if uploaded; error metadata | Client's GitHub Actions | Bundles uploaded as artifacts stay until their retention period ends (GitHub defaults to 90 days unless configured). Keep them short-lived or don't upload them (gap GD-5) |
| Client Salesforce org | D3, D4 | Client | Under the client's Salesforce instance region and contract |
| Agentforce model path | D4 context passages and questions | Salesforce, within the client's Agentforce configuration | Model hosting, retention and region follow the client's Salesforce terms. Confirm per pilot sector (gap GD-6) |

No Rich Solutions-operated system receives client data in the MVP. Anything that would change that (for example external hosting, option C in ADR-001) needs an ADR first (DP-2) and is blocked on the open hosting question in the Operator Inbox.

### 7.2 Controls by concern

| Concern | MVP control | Owner |
|---|---|---|
| Who can read knowledge | Package permission sets; services enforce caller access (SP-2). Per-note access is not in kg-bundle v1; it can be added as a minor version once REQ-15 is answered | Client admin; TA for design |
| Who can write knowledge | Only the CI credential can call import; it is scoped to that one purpose | Client admin |
| Integrity | Schema validation, content hashes, commit SHA on every bundle, all-or-prior commit | Contracts (SB-7), import (SB-8) |
| Auditability | Import records per bundle; Git history of the vault; citations on answers | SB-8, SB-9 to SB-11 |
| Deletion | Deleting a note in the vault removes it from service results on the next import | SB-8 |
| Data minimisation | Attachments sync metadata only; no analytics or telemetry of queries in the base package | SB-7, SB-9 |

### 7.3 Sector checklist for a regulated pilot

Before a pilot in a regulated sector, the engagement team answers these (in Notion, not in this repo):

1. Does the vault hold regulated data (personal, student, payment, criminal-justice, controlled unclassified)? If yes, can that content be kept out of the vault?
2. Must CI run on a self-hosted runner inside the client boundary?
3. Is the client's Salesforce org on an accredited offering where one is required, and does its Agentforce configuration meet the sector's rules for model processing?
4. Must deleted knowledge also be purged from runtime storage within a set time (section 8)?
5. Who in the client organisation owns the vault (data owner) and who approves changes (steward)?

## 8. Data lifecycle and retention

| Stage | D1 Vault | D2 Bundle | D3 Runtime store | D4 Interactions |
|---|---|---|---|---|
| Create | Author commits | Compiled per push | Import commit | Per call |
| Update | New commit | New bundle per commit | Upsert when the hash changes | – |
| Delete | Remove the file | – | Marked deleted, not served | – |
| Retain | Git history (client policy) | Transient; artifact retention as configured | Live bundle plus import records | Not stored by the base package |
| Purge | Git history rewrite (client decision) | Artifact expiry | **Open:** whether soft-deleted node records are hard-deleted, and when (gap GD-3) | – |

## 9. Data quality rules

These are enforced by the contracts and the import service. They are listed here so the Data Architecture can be checked against them:

| Rule | Enforced by |
|---|---|
| Node ids are stable slugs of the vault path and unique within a bundle | Schema pattern, compiler |
| Every bundle names its source repo label, ref and commit SHA | Schema (required fields) |
| Edge sources exist in the bundle; unresolved targets are flagged, not dropped | contracts-check semantic checks, compiler |
| `stats` counts match the arrays | contracts-check semantic checks |
| Chunks are contiguous and reassemble the full body | Schema and compiler |
| An unchanged content hash means no write | Import service |
| Unknown properties fail validation, except in `frontmatter` and `extensions` | Schema (`additionalProperties: false`) |

## 10. Requirement traceability

| Requirement | Status | Data entities | Flows | Covered |
|---|---|---|---|---|
| REQ-1 Knowledge-graph sync | Approved, Must | Vault, Note, Link, Tag, Bundle, Import record | DF-1 to DF-5 | Yes |
| REQ-2 REST service calls | Approved, Must | Query, Result | DF-6 | Yes |
| REQ-3 Apex service calls | Approved, Must | Query, Result | DF-6 | Yes |
| REQ-4 Agentforce actions | Approved, Must | Query, Result, Passage | DF-6, DF-7 | Yes |
| REQ-5 Unlocked 2GP install | Approved, Must | Package metadata (D8); storage objects ship in the package | – | Yes |
| REQ-6 IP line | Approved, Must | Extension data; classification (section 5) | – | Yes (section 6) |
| REQ-7 Work logged in Notion | Approved, Must | Factory governance data (D6) | DF-8 | Yes |
| REQ-8 Runtime-neutral contracts | Approved, Should | Logical model, kg-bundle mapping (section 3.3) | DF-2, DF-3 | Yes |
| REQ-9 to REQ-11 | Approved, Won't | – | – | Out of scope; the future-runtime column in section 3.3 keeps REQ-9 open without building it |
| REQ-12 Zero-manual-step install | Needs Alex | Storage objects and permission sets ship in the package | – | Pending Alex |
| REQ-13 End-to-end Agentforce answer | Needs Alex | Passage with citation | DF-7 | Pending Alex (citations already supported) |
| REQ-14 One client pilot | Needs Alex | Sector checklist (section 7.3) | – | Pending Alex |
| REQ-15 Governed access | Needs Alex | Access controls (section 7.2); no per-note access fields in v1 | DF-6 | Pending Alex |

Every Approved Must or Should requirement maps to at least one data entity or flow.

## 11. Gaps and open items

| # | Gap | Effect | Handling |
|---|---|---|---|
| GD-1 | Hosting outside Salesforce is undecided | Only affects future delivery adapters (ADR-001 options B2 and C). The MVP data flow needs no hosting | Existing Enterprise Architect Operator Inbox question; Phase D records both options |
| GD-2 | REQ-15 access granularity (package-level vs per-note) | Decides whether kg-bundle gains an optional `access` object in a minor version | Existing Business Analyst Inbox item |
| GD-3 | Hard-purge policy for deleted knowledge in runtime stores | Matters for regulated pilots and right-to-delete requests | TA to propose in the SB-8 spec (soft delete plus a purge job, or immediate hard delete); Alex confirms per pilot |
| GD-4 | CI runner location for sensitive vaults | GitHub-hosted runners process vault content | Sector checklist item 2; Phase D records the self-hosted runner option |
| GD-5 | Bundle artifact retention in the vault repo's CI | Bundles may linger as artifacts | SB-8 spec: don't upload full bundles as artifacts, or set a short retention period |
| GD-6 | Model processing terms for Agentforce in regulated sectors | Context passages go to the org's configured model | Sector checklist item 3; confirmed per pilot, in Notion |
| GD-7 | SB-7 spec (PR #7) and Phase B (PR #6) are not merged | This document cites them by PR | Update links to `main` paths once merged |

None of these gaps blocks SB-7 to SB-13 or needs a new ADR now. GD-3 and GD-5 are inputs to the SB-8 spec.

## 12. Next ADM steps

1. Phase C Application Architecture (`C-application.md`): application components and interfaces for the flows above, aligned with ADR-001 layers and the SB-7 operations.
2. Phase D Technology Architecture (`D-technology.md`): platforms and environments. It records the hosting question and the CI runner option as gaps, not choices.
3. Phases E to F (`E-F-roadmap.md`), then propose gate G1 once Phases A to D are Baseline and the core ADRs are Approved.
