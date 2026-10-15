# ADR-001: 2GP package structure and knowledge-graph sync approach

- **Status:** Proposed
- **Date:** 2026-10-13
- **Proposed by:** Technical Architect
- **Story:** SB-5 "ADR-001: 2GP package structure and knowledge-graph sync approach" (Notion Sprint Board)
- **Decisions Log:** matching row "ADR-001: 2GP package structure and knowledge-graph sync approach" (Notion)

## Context

The first Rich Solutions package (Vision Brief, MVP scope) is a Salesforce **unlocked 2GP package** that exposes knowledge-backed, MCP-like service calls three ways: REST endpoints, an Apex API, and Agentforce actions. The knowledge comes from an **Obsidian vault stored in a GitHub repository** (Markdown notes with YAML frontmatter, `[[wikilinks]]` between notes, tags, and attachments).

Two decisions are needed before any requirement can be specified for build:

1. How the package is structured (projects, layers, objects, extension points).
2. How the vault gets from GitHub into a form the package can query.

Constraints that shape both:

| # | Constraint | Source |
|---|---|---|
| C1 | Installs cleanly into a fresh scratch org / sandbox with zero manual steps | Vision Brief, MVP must-do 3 and success metric |
| C2 | Sync format and service contracts stay **runtime-neutral**, so later non-Salesforce runtimes reuse them instead of forking | Vision Brief, future enhancements; AGENTS.md guardrails |
| C3 | Clear IP line: package and templates are Rich Solutions IP; per-client logic is billable and lives outside this repo | Vision Brief, MVP must-do 4 |
| C4 | Hosting for anything outside Salesforce is **undecided** (AWS vs on-platform only) | Operator Inbox, open question |
| C5 | No paid services or new external accounts without Alex | AGENTS.md |
| C6 | Salesforce governor limits: 6 MB synchronous / 12 MB async heap, 100 callouts and 120 s callout time per transaction, 131,072 chars per Long Text Area field | Platform |

## Part 1: Package structure

### Options considered

**1a. One monolithic unlocked package.** Contracts, storage, sync receiver, REST, Apex and Agentforce actions all in one package. Simple to build and install, but client extensions have nowhere clean to live except as unpackaged metadata, which blurs the IP line (C3).

**1b. Base package plus extension packages (recommended).** One Rich Solutions base package holds everything generic. Client-specific logic ships as a separate unlocked package, built and versioned outside this repo, that declares a dependency on the base package and plugs in through published Apex interfaces. Slightly more packaging work, but the IP line is enforced by package boundaries rather than by convention.

**1c. Several base packages split by layer** (storage, services, Agentforce). Finer-grained, but multiplies version-dependency management and install steps for no MVP benefit. Revisit if the package grows past one team.

### Proposed structure (option 1b)

Repository layout (folders are created by the Developer when build stories reach Ready for Dev; listed here so specs can refer to them):

```
contracts/                      runtime-neutral, no Salesforce code
  kg-bundle/                    JSON Schema for the knowledge bundle (sync format), versioned (v1, v2 ...)
  services/                     OpenAPI 3.1 + tool manifest for knowledge service calls
tools/
  kg-compiler/                  vault -> kg-bundle compiler (CLI, runs in CI and locally)
packages/
  salesforce/                   SFDX project (sfdx-project.json) for the unlocked 2GP base package
    force-app/main/default/...
```

Inside the Salesforce base package, four layers, each depending only on the one below:

| Layer | Contents | Notes |
|---|---|---|
| Contract | Apex interfaces and DTOs generated from / mirrored on `contracts/services` (`KnowledgeService`, `KnowledgeQuery`, `KnowledgeResult`) | `global` interfaces are the extension points for client packages |
| Storage | Custom objects `Knowledge_Bundle__c`, `Knowledge_Node__c`, `Knowledge_Edge__c` (fields in Part 2) and a permission set | No Salesforce Knowledge or Data Cloud dependency, so a plain scratch org works (C1) |
| Service | Apex implementation of `KnowledgeService`: get node, search (SOSL), neighbours (edge traversal), context assembly for an agent prompt | All business logic lives here once |
| Exposure | `@RestResource` endpoints under `/knowledge/v1/`, `@InvocableMethod` actions for Agentforce, and the public Apex API | Thin adapters over the service layer; no logic of their own |

Namespace: a namespaced unlocked package is recommended so the Rich Solutions IP is identifiable in subscriber orgs and API names cannot collide with client metadata. Registering a namespace and a Dev Hub are free but are account actions, so they are listed under Consequences for Alex.

## Part 2: Knowledge-graph sync

All options share one runtime-neutral step: a compiler turns the vault into a **knowledge bundle**, a versioned JSON document (or set of paged JSON files) defined by a JSON Schema in `contracts/kg-bundle/`:

- `bundle`: schema version, source repo, commit SHA, generated-at, content hash
- `nodes[]`: stable id (vault-relative path slug), title, body (Markdown), frontmatter (JSON object), tags, content hash, chunk index when a body exceeds the target store's field limit
- `edges[]`: source id, target id, type (`wikilink`, `embed`, `tag`, or a frontmatter-declared relation), plus unresolved links flagged rather than dropped

Parsing Obsidian Markdown happens once, in the compiler. Every runtime (Salesforce now, others later) consumes the same bundle (C2). The options differ in **how the bundle (or the raw vault) reaches Salesforce**.

### Option A: Compile in CI, push into the org (recommended for MVP)

A GitHub Actions workflow runs on pushes to the vault repo: run `kg-compiler`, validate the bundle against the schema, publish it as a build artifact / release asset, then call the package's own import endpoint `POST /services/apexrest/<ns>/knowledge/v1/bundles` in pages (for example 200 nodes per call, to stay under the 6 MB heap limit, C6). Authentication uses the Salesforce CLI JWT flow with a connected app; the key lives in GitHub Actions encrypted secrets, never in the repo.

- **Pros:** no hosting needed beyond GitHub Actions (C4, C5); parsing is out of Apex and out of governor limits; the bundle is diffable, testable and reusable by any runtime (C2); the import endpoint is itself part of the service contract, so a future runtime implements the same `POST /bundles`; idempotent upsert by node external id and content hash makes re-runs safe.
- **Cons:** each target org needs a connected app and a secret in the vault repo's CI; freshness equals commit-to-workflow time (minutes); an org we do not operate cannot pull updates on its own.

### Option B: Salesforce pulls from GitHub

Scheduled or queueable Apex calls the GitHub REST API through a Named Credential and ingests content into the same storage objects.

- **B1, pull raw Markdown and parse in Apex.** Rejected: the Obsidian parser would be written in Apex, so every future runtime re-implements it (fails C2); vaults of any size hit heap, CPU and callout limits (C6); a GitHub token is stored in each org.
- **B2, pull the compiled bundle** (release asset from Option A's compile step). Keeps parsing out of Apex and keeps C2. Useful later for subscriber orgs that should self-update, but needs a Named Credential, a GitHub token per org, and scheduled-job setup at install time, which works against C1 for the MVP.

### Option C: External sync service

A hosted service (for example AWS Lambda) watches the vault, compiles, optionally adds embeddings, and pushes into orgs.

- **Pros:** scales to many orgs and large vaults; natural home for vector search later.
- **Cons:** depends on the open hosting decision (C4) and likely a paid service (C5); more to operate and secure; not needed to meet MVP success metrics.

### Option D: Target Salesforce Knowledge or Data Cloud instead of custom objects

Load notes as Knowledge articles or Data Cloud records. Rejected for MVP: both need features or licences that a plain scratch org does not have, breaking zero-manual-step install (C1), and they tie the storage shape to Salesforce-specific products.

### Comparison

| Criterion | A: CI push | B1: Apex pulls raw | B2: Apex pulls bundle | C: External service |
|---|---|---|---|---|
| Runtime-neutral (C2) | Yes | No | Yes | Yes |
| Clean scratch-org install (C1) | Yes | Needs NC + token | Needs NC + token | Yes |
| Needs hosting decision (C4) | No | No | No | **Yes** |
| Governor-limit risk (C6) | Low (paged import) | High | Medium | Low |
| Secrets location | GitHub Actions | Each org | Each org | Service |
| Effort for MVP | Low | High | Medium | High |

## Decision (proposed)

1. **Package structure:** option 1b, one namespaced unlocked 2GP base package with Contract / Storage / Service / Exposure layers; client logic ships as separate dependent packages outside this repo.
2. **Sync:** option A for the MVP. The vault is compiled in CI into a schema-validated, runtime-neutral `kg-bundle`, which is pushed into the org through the package's own `POST /knowledge/v1/bundles` import endpoint.
3. **Contracts first:** `contracts/kg-bundle` (JSON Schema) and `contracts/services` (OpenAPI 3.1 plus an MCP-style tool manifest describing each service call's input and output schema) are the source of truth; Apex DTOs, REST resources and invocable actions are adapters that must conform to them.
4. **Later, without re-deciding:** B2 (orgs pull the published bundle) and C (external service) stay open as additional delivery adapters for the same bundle. Choosing either later does not change the bundle format or the service contracts.

This decision does not depend on the open hosting question: option A needs only GitHub Actions and Salesforce. If Alex decides on AWS hosting, option C can be added as a delivery adapter later.

## Consequences

- **Alex actions (account / settings, agents cannot do these):** enable a Dev Hub and register a package namespace; create the connected app and JWT certificate for CI and store them as GitHub Actions secrets in the vault repo; confirm which repository holds the Obsidian vault (it may hold client content, so it should not be this public repo).
- New runtime-neutral folders `contracts/` and `tools/` and the SFDX project under `packages/salesforce/` need owners in AGENTS.md once this ADR is approved (proposed: Developer builds, Technical Architect owns the contract schemas).
- Storage objects sized to Long Text Area 131,072 chars per field; the compiler chunks longer notes, and the service layer reassembles chunks.
- Search starts with SOSL keyword search; semantic / vector search is out of MVP scope and would arrive with option C or a later ADR.
- Imports are idempotent: upsert by node id, skip when content hash is unchanged, mark nodes absent from the new bundle as deleted, and record each import on `Knowledge_Bundle__c` with commit SHA and status.
- Follow-up specs, once this ADR and the related requirements are Approved: `kg-bundle` schema v1, `kg-compiler`, import endpoint, service layer, REST / Apex / Agentforce adapters.

## Links

- Vision Brief (Notion, Agent Team HQ)
- Sprint Board story SB-5 (Notion)
- Decisions Log row for ADR-001 (Notion)
- Operator Inbox: hosting target question (open), "Approve ADR-001" item
