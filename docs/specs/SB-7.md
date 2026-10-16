# SB-7: Runtime-neutral knowledge bundle schema and service contracts

- **Story:** SB-7 (Notion Sprint Board, shown as RSP-7) "Define runtime-neutral knowledge bundle schema and service contracts"
- **Requirements:** REQ-8 Runtime-neutral sync format and service contracts (Should, Approved)
- **ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) (Approved 2026-10-15), decision points 2 and 3
- **Principles:** AP-1 Runtime-neutral contracts, AP-2 One service core, SP-1 Public-repo hygiene ([principles.md](../togaf/principles.md))
- **Spec author:** Technical Architect, 2026-10-15 (committed 2026-10-16)
- **Builder:** Developer

## 1. Goal

Publish version 1 of the two contracts that every runtime (Salesforce now, others later) builds against:

1. **kg-bundle v1**: the JSON format that the vault compiler produces and every runtime imports.
2. **knowledge services v1**: the service calls (OpenAPI 3.1 for HTTP, plus an MCP-style tool manifest) that every runtime exposes.

Both live under `contracts/`, contain no Salesforce-specific types, and are the source of truth. Apex DTOs, REST resources and Agentforce actions (SB-9 to SB-11) and the compiler (SB-8) conform to them; they do not redefine them.

Out of scope: the compiler itself (SB-8), any Apex (SB-9 to SB-11), semantic/vector search (ADR-001 consequences), access-control fields (REQ-15 is still Needs Alex; see section 8).

## 2. Components and files

```
contracts/
  README.md                         what each contract is, versioning rules (section 7), how to validate
  kg-bundle/
    v1/
      kg-bundle.schema.json         JSON Schema 2020-12, the full bundle document
      kg-bundle-page.schema.json    JSON Schema 2020-12, one import page (section 3.4)
      examples/
        sample-vault-bundle.json    valid full bundle built from a 4-note synthetic vault
        sample-page-1-of-1.json     valid import page for the same vault
        invalid/                    one file per rule the schema must reject (section 6)
  services/
    v1/
      knowledge-services.openapi.yaml   OpenAPI 3.1; component schemas $ref the kg-bundle schema
      tool-manifest.json                MCP-style tools: name, description, inputSchema, outputSchema
      examples/                         one request + response JSON per operation
tools/
  contracts-check/                  validator script + tests (section 6); no runtime code
.github/workflows/contracts-check.yml   runs tools/contracts-check on PRs touching contracts/ or tools/contracts-check/
```

All sample content is synthetic (for example notes about a fictional "Example Corp"). No client names, data, org IDs or URLs to private repos (SP-1).

Note: `.github/workflows/` is listed under Alex in AGENTS.md. The Developer adds the workflow file in the SB-7 PR and calls it out in the PR description so Alex approves that path explicitly when merging; if Alex declines, the check runs locally only and the PR test evidence carries its output.

## 3. Data: kg-bundle v1

### 3.1 Identifiers and conventions

- Node `id`: lower-case slug of the vault-relative path without extension, `/` kept as separator, other characters outside `[a-z0-9-_/]` replaced by `-`, repeated `-` collapsed. Example: `Customers/Onboarding Guide.md` becomes `customers/onboarding-guide`. Pattern: `^[a-z0-9][a-z0-9_/-]{0,254}$`. Stable across compiles as long as the file is not moved or renamed.
- Hashes: `sha256:` followed by 64 lower-case hex characters, computed over UTF-8 bytes.
- Timestamps: RFC 3339 UTC strings (`format: date-time`).
- No property uses a Salesforce type, suffix (`__c`), ID format or field-length rule. Size limits that matter to one runtime (Long Text Area 131,072 chars) are handled by chunking in the compiler (3.3), expressed as a neutral `maxChunkChars` value the compiler is told, not as a schema constant.
- `additionalProperties: false` on every object except `frontmatter` and `extensions`, so typos fail validation.

### 3.2 Bundle document (`kg-bundle.schema.json`)

| Property | Type | Required | Notes |
|---|---|---|---|
| `schemaVersion` | string, const `"1.0"` | yes | Minor versions stay backward compatible (section 7) |
| `bundle.id` | string | yes | `<source.repo-slug>@<source.commit>`; unique per compile |
| `bundle.generatedAt` | date-time | yes | |
| `bundle.generator` | object `{name, version}` | yes | e.g. `kg-compiler`, `0.1.0` |
| `bundle.contentHash` | hash | yes | Hash over node and edge hashes in id order; equal hash means no change |
| `source.repo` | string | yes | Opaque label for the vault repo (e.g. `example-org/example-vault`); never a token or private URL with credentials |
| `source.ref` | string | yes | Branch or tag compiled |
| `source.commit` | string, `^[0-9a-f]{40}$` | yes | Git commit SHA |
| `stats` | object `{nodeCount, edgeCount, unresolvedLinkCount}` | yes | Integers, must match array sizes (checked by contracts-check, not expressible in JSON Schema) |
| `nodes[]` | array of Node | yes | May be empty |
| `edges[]` | array of Edge | yes | May be empty |
| `extensions` | object | no | Namespaced keys (`^[a-z][a-z0-9]*:[a-zA-Z0-9_.-]+$`) for runtime- or client-specific additions; consumers ignore keys they do not know. Base contracts never require a key here. |

**Node**

| Property | Type | Required | Notes |
|---|---|---|---|
| `id` | string (3.1 pattern) | yes | |
| `path` | string | yes | Vault-relative path including extension |
| `title` | string, 1 to 512 chars | yes | Frontmatter `title`, else first `# ` heading, else file name |
| `kind` | enum `note`, `attachment` | yes | Attachments carry metadata only, no binary content in v1 |
| `body` | string | yes for `note` | Markdown with wikilinks left as written; empty string allowed |
| `chunks[]` | array of `{index, text, hash}` | no | Present only when body exceeds `maxChunkChars`; then `body` holds chunk 0 and chunks are 0-based, contiguous, concatenation equals full body |
| `frontmatter` | object | yes | Parsed YAML as JSON; `{}` when none. Values limited to JSON types; dates become strings |
| `tags` | array of string, unique | yes | Without leading `#`, lower-cased, nested tags keep `/` |
| `aliases` | array of string | yes | From frontmatter `aliases`; `[]` when none |
| `contentHash` | hash | yes | Over full body plus canonical frontmatter JSON |
| `updatedAt` | date-time | no | Last commit touching the file, if the compiler can tell |

**Edge**

| Property | Type | Required | Notes |
|---|---|---|---|
| `source` | node id | yes | Must exist in `nodes` |
| `target` | node id or null | yes | Null when the link is unresolved |
| `targetText` | string | yes | Link text as written (`Onboarding Guide#Setup`) |
| `type` | enum `wikilink`, `embed`, `tag`, `relation` | yes | `relation` comes from a frontmatter key listed in compiler config |
| `relation` | string | when `type` = `relation` | Frontmatter key, e.g. `depends-on` |
| `anchor` | string | no | Heading or block reference after `#` |
| `resolved` | boolean | yes | `false` iff `target` is null |

Duplicate edges (same source, target, type, relation, anchor) are emitted once.

### 3.3 Chunking rule

The compiler receives `maxChunkChars` (default 100,000, leaving headroom under the Salesforce Long Text Area limit). Bodies longer than that are split at the last blank line before the limit, else the last newline, else hard at the limit. The schema does not hard-code the number.

### 3.4 Import page (`kg-bundle-page.schema.json`)

ADR-001 option A imports in pages to stay under runtime memory limits. A page is:

| Property | Type | Required | Notes |
|---|---|---|---|
| `schemaVersion` | const `"1.0"` | yes | |
| `bundle` | same object as 3.2 `bundle` | yes | Identifies which compile this page belongs to |
| `source` | same as 3.2 | yes | |
| `page.index` | integer >= 1 | yes | |
| `page.count` | integer >= 1, >= index | yes | |
| `nodes[]` | Node | yes | Default page size 200 nodes, configurable |
| `edges[]` | Edge | yes | Edges are sent on the page that carries their `source` node |
| `deletions[]` | array of node id | yes on last page, else omitted | Optional for the producer to compute; runtimes also treat any node not seen in any page of the bundle as deleted when the last page commits |

The page schema `$ref`s Node and Edge from the bundle schema (`$defs`), so there is one definition of each.

## 4. Interfaces: knowledge services v1

### 4.1 Operations

All paths are relative to a runtime base URL. On Salesforce that is `/services/apexrest/<ns>/knowledge/v1`; the contract only defines the part after the base (`servers` uses a templated `{baseUrl}`).

| Operation id / tool name | HTTP | Input | Output | Used by |
|---|---|---|---|---|
| `importBundlePage` | `POST /bundles/{bundleId}/pages` | Import page (3.4) | `ImportStatus` | SB-8 CI sync |
| `getImportStatus` | `GET /bundles/{bundleId}` | path param | `ImportStatus` | SB-8, ops |
| `getNode` | `GET /nodes/{nodeId}` | `nodeId` path, `includeBody` (bool, default true) | `NodeResult` | SB-9 to SB-11 |
| `searchNodes` | `POST /search` | `{query (1..500 chars), tags[], limit (1..50, default 10), cursor}` | `SearchResult` | SB-9 to SB-11 |
| `getNeighbors` | `GET /nodes/{nodeId}/neighbors` | `direction` (`out`,`in`,`both`; default `both`), `types[]`, `depth` (1..2, default 1), `limit` (1..100, default 25) | `NeighborResult` | SB-9 to SB-11 |
| `getContext` | `POST /context` | `{question (1..2000 chars), maxNodes (1..10, default 5), maxChars (1000..60000, default 20000)}` | `ContextResult` | SB-11 Agentforce grounding |

ADR-001 named the import endpoint `POST /knowledge/v1/bundles`. This spec refines it to `POST /bundles/{bundleId}/pages` so pages of one compile are grouped and idempotent; the base path, method and purpose are unchanged, so no new ADR is needed. The `tool-manifest.json` lists only the read operations (`getNode`, `searchNodes`, `getNeighbors`, `getContext`); import is an HTTP-only admin call and is not offered to agents.

### 4.2 Result shapes

- `NodeResult`: `{node: NodeSummary + body (full body, chunks reassembled) + frontmatter, bundle: {id, commit}}`.
- `NodeSummary`: `{id, title, path, tags, kind, snippet?}`; `snippet` is up to 300 chars of plain text around the match.
- `SearchResult`: `{items: NodeSummary[] with score (0..1, optional), nextCursor: string|null, bundle: {id, commit}}`. Cursor is opaque.
- `NeighborResult`: `{node: NodeSummary, edges: [{edge (3.2 Edge), node: NodeSummary|null}], truncated: boolean}`.
- `ContextResult`: `{question, passages: [{nodeId, title, path, text, citation}], truncated: boolean, bundle: {id, commit}}`. `citation` is `<path>@<commit>` so every answer can cite its source note (helps REQ-13 if Alex approves it).
- `ImportStatus`: `{bundleId, state (enum `receiving`, `committed`, `failed`, `superseded`), pagesReceived, pageCount, nodesUpserted, nodesUnchanged, nodesDeleted, errors: Error[], updatedAt}`.

### 4.3 Errors

One error envelope for every operation and every runtime (RFC 9457 problem details style):

```json
{ "error": { "code": "NODE_NOT_FOUND", "message": "No node with id customers/onboarding-guide", "details": [], "retryable": false } }
```

| Code | HTTP | When |
|---|---|---|
| `INVALID_REQUEST` | 400 | Input fails the operation's schema; `details[]` holds `{path, rule}` items |
| `INVALID_BUNDLE` | 422 | Import page fails `kg-bundle-page.schema.json` or references an unknown source node |
| `BUNDLE_CONFLICT` | 409 | Page for a bundle older than the committed one, or `page.count` differs from earlier pages of the same bundle |
| `NODE_NOT_FOUND` | 404 | |
| `UNAUTHORIZED` | 401 | No or bad credentials (runtime decides how) |
| `FORBIDDEN` | 403 | Caller lacks permission (runtime decides how; see section 8) |
| `PAYLOAD_TOO_LARGE` | 413 | Page exceeds the runtime's documented size limit |
| `RATE_LIMITED` | 429 | `retryable: true` |
| `INTERNAL` | 500 | `retryable: true`; never leaks stack traces |

Agent tools return the same envelope as the tool result so a non-HTTP runtime (MCP server, Apex) maps errors the same way.

### 4.4 Import semantics (contract-level, every runtime must honour)

1. Pages may arrive in any order and may be retried; the same page twice is a no-op.
2. A bundle is `committed` only when all `page.count` pages arrived. Until then, reads keep serving the previously committed bundle.
3. On commit: upsert nodes by `id`, skip unchanged `contentHash`, mark nodes absent from the bundle as deleted (not returned by reads), replace edges for every upserted source node.
4. A page whose `bundle.id` equals the committed bundle returns the committed `ImportStatus` (idempotent re-run).
5. A newer bundle arriving while an older one is `receiving` marks the older one `superseded`.

## 5. Runtime-neutrality rules (checked in review and by contracts-check)

- No `__c`, `__r`, `Id` 15/18-char patterns, `sObject`, `Apex`, `Salesforce`, `Agentforce` or `SOSL` in schema property names, enums or descriptions, except in `contracts/README.md` where runtimes are listed as examples. contracts-check greps for these tokens.
- No runtime limits as schema constants (chunk size, page size are parameters).
- Auth is declared as an OpenAPI `securitySchemes` placeholder (`bearerAuth`, HTTP bearer); each runtime documents how it satisfies it.

## 6. Test approach

`tools/contracts-check/` (Python 3.12, stdlib plus `jsonschema` and `pyyaml`, pinned in a `requirements.txt`; or Node with `ajv` if the Developer prefers, one choice only). The check must:

1. Validate both JSON Schemas against the 2020-12 meta-schema.
2. Validate every file in `kg-bundle/v1/examples/` against the right schema; every file in `examples/invalid/` must fail, each for its named reason. Minimum invalid cases: bad node id pattern, missing `contentHash`, `resolved: true` with `target: null`, unknown top-level property, edge source not in nodes (semantic check), `stats` count mismatch (semantic check), `page.index` > `page.count`, wrong `schemaVersion`.
3. Validate the OpenAPI document (`openapi-spec-validator` or equivalent) and check every `services/v1/examples/` request and response against the referenced component schemas.
4. Check `tool-manifest.json`: each tool's `inputSchema`/`outputSchema` equals the matching OpenAPI request/response schema (same `$ref` targets), and every tool name is an `operationId` in the OpenAPI document.
5. Run the runtime-neutrality token scan (section 5).
6. **Neutral consumer test** (REQ-8 AC 2): a small reader in `tools/contracts-check/` that uses only the published schema and the Python standard library plus `jsonschema` to load `sample-vault-bundle.json`, rebuild the graph (nodes by id, adjacency from edges) and assert expected counts and one known path. It imports nothing from any runtime folder.

Exit code non-zero on any failure. The PR's test evidence is the command and its output.

## 7. Versioning

- Folder per major version (`v1/`). `schemaVersion` is `"<major>.<minor>"`.
- Minor (`1.1`): only additive optional properties or new enum values that consumers can ignore; schema `$id` stays under `v1/`.
- Major (`2.0`): anything else; needs a new ADR and a new folder, and runtimes support both majors for one release.
- Each schema has `$id` `https://github.com/africh/rich-solutions-platform/contracts/kg-bundle/v1/<file>` (an identifier, not fetched at runtime).

## 8. Open points (do not block build)

- **REQ-15 governed access** is Needs Alex. v1 carries no per-node access fields; `FORBIDDEN` and `securitySchemes` exist so access control can be added in a minor version (for example an optional `access` object on Node) without breaking consumers.
- **REQ-13 citations** is Needs Alex. `citation` in `ContextResult` is included anyway because it is cheap and additive.

## 9. Acceptance-criteria mapping

| # | Acceptance criterion (story SB-7 / REQ-8) | Met by | Verified by |
|---|---|---|---|
| 1 | Bundle format published as JSON Schema in a runtime-neutral location | `contracts/kg-bundle/v1/*.schema.json` (section 3) | contracts-check step 1 |
| 2 | Service calls published as OpenAPI (or equivalent) in a runtime-neutral location | `contracts/services/v1/knowledge-services.openapi.yaml` + `tool-manifest.json` (section 4) | contracts-check steps 3 and 4 |
| 3 | No Salesforce-specific types in either | Section 3.1 conventions, section 5 rules | contracts-check step 5; QA review |
| 4 | A sample bundle validates against the schema | `examples/sample-vault-bundle.json`, `sample-page-1-of-1.json` | contracts-check step 2 |
| 5 | REQ-8: a non-Salesforce consumer can parse a bundle using only the published schema | Neutral consumer test | contracts-check step 6 |
| 6 | Spec in `docs/specs/<story-id>.md` references ADR-001 | This file | Header links ADR-001 |

## 10. Definition of done for the Developer PR

- Files in section 2 exist; contracts-check passes locally and (if the workflow is accepted) in CI.
- No changes outside `contracts/`, `tools/contracts-check/` and the one workflow file.
- `python build.py` is unaffected (no changes to `research/`, `template.html`, `build.py`).
- PR description links SB-7 and this spec; story moves to In PR.
