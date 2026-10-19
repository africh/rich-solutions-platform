# SB-8: Knowledge-graph sync (compile the Obsidian vault from GitHub and load it into the org)

- **Story:** SB-8 (Notion Sprint Board, shown as RSP-8) "Knowledge-graph sync: compile Obsidian vault from GitHub and load it into the org"
- **Requirements:** REQ-1 Knowledge-graph sync from GitHub-hosted Obsidian vault (Must, Approved)
- **ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) (Approved 2026-10-15), decision points 2 and 3 (sync option A: compile in CI, push through the package's own import endpoint)
- **Contracts:** [SB-7 spec](SB-7.md) (kg-bundle v1, knowledge services v1). Until PR #7 merges, read it on the branch `agent/technical-architect/SB-7`.
- **Inputs taken into account:** QA notes 1 and 2 on PR #7 (bundle ordering, re-compile idempotency); Phase C data gaps GD-3 (hard purge) and GD-5 (bundle artifact retention) in `docs/togaf/C-data.md` (PR #10); IP boundary in `docs/design/ip-boundary.md` (PR #8)
- **Principles:** AP-1 Runtime-neutral contracts, AP-2 One service core, SP-1 Public-repo hygiene ([principles.md](../togaf/principles.md))
- **Spec author:** Technical Architect, 2026-10-19
- **Builder:** Developer

## 1. Goal

Make the notes, links and metadata of an Obsidian vault in a GitHub repository queryable inside a Salesforce org, keep the org in step with adds, edits and deletes, and never leave the org with half-loaded or invalid knowledge.

The work has a runtime-neutral half (compile and push, reusable by any future runtime) and a Salesforce half (storage objects and the import endpoint). Reads (`getNode`, `searchNodes`, `getNeighbors`, `getContext`) are SB-9; this story only has to make the data queryable (SOQL is enough to prove it).

Out of scope: semantic or vector search, orgs pulling bundles themselves (ADR-001 option B2), any hosted sync service (option C), per-node access control (REQ-15 is Needs Alex).

## 2. Build order and slices

| Slice | Contents | Depends on | Can start |
|---|---|---|---|
| 8a | `tools/kg-compiler`, `tools/kg-push`, vault-repo workflow template (sections 3, 4, 5) | SB-7 build (schemas and `contracts-check` library) | After the SB-7 Developer PR merges |
| 8b | Storage objects, import endpoint, commit job, purge job (sections 6, 7, 8) | SB-12 slice 1 (SFDX project skeleton, `packages/salesforce/`) | After SB-12 slice 1 merges |
| 8c | End-to-end run against a scratch org (section 10.3) | 8a, 8b, and the Alex account actions in section 12 | When a Dev Hub exists |

Each slice is its own Developer PR that links SB-8 and this spec. The story moves to In PR with the first slice and stays there until 8c's evidence is attached.

## 3. Components and files

```
tools/
  kg-compiler/                      Python 3.12 package and CLI, runtime-neutral
    kg_compiler/
      cli.py                        `kg-compiler compile ...` entry point
      config.py                     loads kg-compiler.yml (section 4.1)
      vault.py                      walks the vault, applies include/exclude
      markdown.py                   frontmatter, title, tags, links, embeds
      resolve.py                    Obsidian link resolution (section 4.4)
      bundle.py                     ids, hashes, chunking, sort order, canonical JSON
      paginate.py                   splits a bundle into import pages (section 4.6)
    tests/
      fixtures/                     synthetic vaults (section 10.1)
      test_*.py
    pyproject.toml                  pins pyyaml and jsonschema; reuses tools/contracts-check for validation
  kg-push/                          Python 3.12 CLI, runtime-neutral apart from an auth adapter
    kg_push/
      cli.py                        `kg-push push ...`
      client.py                     importBundlePage / getImportStatus over HTTP (SB-7 4.1)
      auth_salesforce.py            gets base URL and bearer token from the Salesforce CLI (section 5.2)
    tests/
templates/
  vault-sync/
    README.md                       how to install the sync into a vault repository
    kg-sync.yml                     GitHub Actions workflow to copy into the vault repo's .github/workflows/
    kg-compiler.example.yml         sample compiler config
packages/salesforce/force-app/main/storage/    (8b, inside the SB-12 project)
  objects/Knowledge_Bundle__c/ ...
  objects/Knowledge_Bundle_Page__c/ ...
  objects/Knowledge_Node__c/ ...
  objects/Knowledge_Node_Chunk__c/ ...
  objects/Knowledge_Edge__c/ ...
  customMetadata / objects/Knowledge_Sync_Setting__mdt/ ...
  permissionsets/Knowledge_Sync.permissionset-meta.xml
  customPermissions/Knowledge_Import.customPermission-meta.xml
packages/salesforce/force-app/main/service/classes/
  KnowledgeImportService.cls        page intake, validation, state machine
  KnowledgeImportCommitJob.cls      Queueable chain that applies a bundle
  KnowledgeImportPurgeJob.cls       Schedulable + Queueable purge (section 8)
  KnowledgeStore.cls                the only class that reads "current" rows (shared with SB-9)
packages/salesforce/force-app/main/exposure/classes/
  KnowledgeBundlesResource.cls      @RestResource for /knowledge/v1/bundles/*
```

The workflow template lives in `templates/`, not in this repository's `.github/workflows/`, because it runs in each vault repository, not here. It is generic Rich Solutions IP (ip-boundary section 2: "templates"); a client's vault repository and any client-specific compiler config stay outside this repo.

`tools/`, `templates/` and `packages/` have no owner row in AGENTS.md yet. That is the open Technical Architect Operator Inbox Blocker of 2026-10-15, decision (b). The Developer PRs call this out; they do not edit AGENTS.md.

## 4. kg-compiler (slice 8a)

### 4.1 Command and config

```
kg-compiler compile --vault <dir> --out <dir> --repo <label> --ref <ref> --commit <sha>
                    [--config <file>] [--max-chunk-chars 100000]
                    [--page-max-nodes 200] [--page-max-bytes 2000000]
```

`--repo` is an opaque label (SB-7 `source.repo`), never a URL with credentials. Config defaults to `<vault>/kg-compiler.yml` if present:

| Key | Default | Meaning |
|---|---|---|
| `include` | `["**/*.md"]` plus `attachments.extensions` | Globs relative to the vault root |
| `exclude` | `[".obsidian/**", ".trash/**", ".git/**", ".github/**"]` | Applied after `include` |
| `attachments.extensions` | `["png","jpg","jpeg","gif","svg","pdf"]` | Become `kind: attachment` nodes, metadata only |
| `relations` | `[]` | Frontmatter keys whose values become `relation` edges |
| `maxChunkChars` | 100000 | Same as the CLI flag; CLI wins |

Exit codes: `0` success, `1` compile or validation error (message per problem, `path:line` where known), `2` usage error.

### 4.2 Outputs

- `<out>/bundle.json`: the full kg-bundle v1 document.
- `<out>/pages/page-0001.json` ... : import pages (SB-7 3.4).
- `<out>/summary.json`: `{bundleId, contentHash, commit, stats, pageCount, warnings[]}`. No note content. This is the only file the workflow may upload as an artifact (section 5.3).

Before writing, the compiler validates `bundle.json` and every page with the SB-7 schemas and semantic checks by importing the `tools/contracts-check` library. A bundle that fails its own contract is never written.

### 4.3 Parsing rules

| Item | Rule |
|---|---|
| Encoding | UTF-8 only; strip a leading BOM; normalise CRLF and CR to LF. Non-UTF-8 file: error |
| Frontmatter | YAML between a first-line `---` and the next `---`; `yaml.safe_load`; must be a mapping, else error. Dates become ISO strings |
| Title | SB-7 3.2: frontmatter `title`, else first `# ` heading, else file name without extension |
| Tags | Frontmatter `tags` (list or comma/space separated string) plus inline `#tag` in body text. Lower-case, no `#`, unique, sorted. Ignore `#` inside fenced code, inline code, URLs and headings |
| Aliases | Frontmatter `aliases` (list or single string) |
| Links | `[[target]]`, `[[target\|label]]`, `[[target#heading]]`, `[[target#^block]]` give `type: wikilink`; the same with a leading `!` give `type: embed`; Markdown links `[text](relative/path.md)` to vault files give `type: wikilink`. External URLs are ignored. Nothing inside fenced or inline code counts |
| Relations | For each key in `relations`: each value (string or list) that is `[[X]]` or a plain note name becomes an edge `type: relation, relation: <key>` |
| Tag edges | Not emitted in v1. Tags live on `node.tags`; the `tag` edge type stays reserved |
| `updatedAt` | From `git log -1 --format=%cI -- <path>` when the vault is a git checkout with history; else omitted |

### 4.4 Link resolution (matches Obsidian)

1. Strip `#...` into `anchor` and `|...` (label); trim.
2. If the target contains `/`: resolve against vault-relative paths (with or without `.md`), case-insensitive.
3. Otherwise match on file base name, case-insensitive. One match: resolved. Several matches: pick the shortest path, then lexical order, and add a warning `AMBIGUOUS_LINK` to `summary.json`.
4. No match: `target: null`, `resolved: false`, counted in `stats.unresolvedLinkCount`.
5. Self-links are kept. Duplicates are removed as SB-7 3.2 says.

### 4.5 Ids, hashes, chunking and determinism

- Node ids per SB-7 3.1. Two files that slug to the same id: error `ID_COLLISION` naming both paths. Nothing is guessed.
- Canonical JSON for every hash: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` encoded as UTF-8.
- Node `contentHash`: SB-7 3.2 (full body plus canonical frontmatter JSON).
- **Bundle `contentHash` (clarifies SB-7 3.2, which says "over node and edge hashes" but edges have no hash):** sha256 over the canonical JSON of `{"nodes": [[id, contentHash], ...], "edges": [edge, ...]}`, nodes sorted by id and edges sorted as below, each edge as its full canonical object.
- Sort order: nodes by `id`; edges by `(source, type, relation or "", target or "", anchor or "", targetText)`.
- Chunking per SB-7 3.3 with `maxChunkChars`.
- Determinism: compiling the same commit twice gives byte-identical `nodes`, `edges`, `stats` and `contentHash`. Only `bundle.generatedAt` (and `bundle.generator.version` across compiler upgrades) may differ. A test enforces this (10.1).

### 4.6 Pagination

- Fill pages in node-id order up to `--page-max-nodes` nodes **and** `--page-max-bytes` bytes of canonical page JSON, whichever comes first. The byte limit keeps each request well under the Salesforce 6 MB synchronous request and heap limits (ADR-001 C6), leaving room for parsing.
- Edges go on the page that carries their `source` node (SB-7 3.4).
- A single node whose page would exceed `--page-max-bytes` on its own: error `NODE_TOO_LARGE` naming the path and size. With the defaults this is a note of roughly 1.9 MB of text, far beyond normal notes.
- The last page carries `deletions: []`. The compiler cannot know what the target holds; runtimes derive deletions as "absent from every page" (SB-7 3.4).

## 5. kg-push and the vault workflow (slice 8a)

### 5.1 kg-push

```
kg-push push --pages <dir> --base-url <url> --token-env <VAR>
             [--timeout 600] [--poll-interval 5] [--max-retries 5]
kg-push salesforce-auth --target-org <alias>     prints base URL; exports token to the given env var file
```

1. Send pages in index order with `POST {baseUrl}/bundles/{bundleId}/pages`, one at a time.
2. Retry on `429`, `5xx` and network errors with exponential backoff (1, 2, 4, 8, 16 s); never on `4xx` other than `429`. A retried page is harmless because page intake is idempotent (7.2).
3. After the last page, poll `GET {baseUrl}/bundles/{bundleId}` until `state` is `committed`, `failed` or `superseded`, or `--timeout` passes.
4. Exit `0` only on `committed`. On `failed` print every `errors[]` item and exit `1`. On `superseded` print a notice and exit `0` (a newer commit is being loaded). On timeout exit `1`.
5. Never print the token. Log lines carry bundle id, page index, HTTP status and error code only, never note content.

`kg-push` speaks only the SB-7 HTTP contract. The one Salesforce-specific piece is `auth_salesforce.py`, which runs `sf org display --target-org <alias> --json` and reads `instanceUrl` and `accessToken`; the base URL becomes `<instanceUrl>/services/apexrest/<ns>/knowledge/v1`. A future runtime adds its own auth adapter and reuses everything else.

### 5.2 Workflow template `templates/vault-sync/kg-sync.yml`

- **Triggers:** `push` to the vault's default branch, and `workflow_dispatch`.
- **Concurrency:** `group: kg-sync-${{ github.ref }}`, `cancel-in-progress: false`, so two syncs for one branch never interleave.
- **Steps:**
  1. Check out with `fetch-depth: 0` (needed for `updatedAt`).
  2. Set up Python 3.12; install `kg-compiler` and `kg-push` from a pinned tag of this repository (`pip install "git+https://github.com/africh/rich-solutions-platform@<tag>#subdirectory=tools/kg-compiler"`, the same for kg-push). Pinned tag, never `main`.
  3. `kg-compiler compile ...` with `--repo "${{ github.repository }}" --ref "${{ github.ref_name }}" --commit "${{ github.sha }}"`.
  4. **Stale-commit guard** (QA note 1 on PR #7): `git ls-remote origin "refs/heads/${{ github.ref_name }}"`. If the branch head is no longer `${{ github.sha }}`, stop with a notice "newer commit exists; skipping push". Re-running an old workflow therefore cannot load an older vault over a newer one.
  5. Install the Salesforce CLI; `sf org login jwt --client-id "$SF_CLIENT_ID" --jwt-key-file <tmp file from SF_JWT_KEY> --username "$SF_USERNAME" --instance-url "$SF_INSTANCE_URL" --alias target`; delete the key file right after login.
  6. `kg-push push ...`.
  7. Write `summary.json` fields and the final import status to `$GITHUB_STEP_SUMMARY`.
- **Secrets (in the vault repository, never in this one):** `SF_CLIENT_ID`, `SF_JWT_KEY`, `SF_USERNAME`, `SF_INSTANCE_URL`. One integration user per org, assigned the `Knowledge_Sync` permission set only.
- **Failure reporting:** any failed step fails the workflow run, so GitHub's normal failure notification reaches the vault owner, and the step summary shows the error codes.

### 5.3 Artifact retention (closes gap GD-5)

- The template uploads **only** `summary.json`, with `retention-days: 7`. It never uploads `bundle.json` or `pages/`, because they contain the full note text.
- `templates/vault-sync/README.md` says so, and adds that the repository's default artifact and log retention should be lowered for sensitive vaults. It also points to the self-hosted runner option (gap GD-4, owned by the Enterprise Architect).

## 6. Storage objects (slice 8b)

All objects are in the base package, Storage layer. Field names below are without the namespace prefix. Sharing: Private or ControlledByParent as noted; access is via permission sets only.

### 6.1 Versioned rows

Readers must keep seeing the previous committed bundle until a new one commits (SB-7 4.4 rule 2), and a commit may span several transactions. So node and edge rows are **versioned by bundle sequence**:

- Every committed bundle gets an integer `Sequence__c` (1, 2, 3 ...).
- A node or edge row is visible at sequence *S* when `Valid_From__c <= S` and (`Valid_To__c` is null or `Valid_To__c > S`).
- The current sequence is the `Sequence__c` of the one `Knowledge_Bundle__c` with `Is_Current__c = true`.
- A commit at sequence *N* only inserts rows with `Valid_From__c = N` and sets `Valid_To__c = N` on rows it replaces. Readers at *N-1* see none of that. The last step of the commit flips `Is_Current__c` in one DML statement, so the switch is atomic.

`KnowledgeStore.cls` is the only class that builds this visibility filter. SB-9 reads through it.

### 6.2 Objects and fields

**`Knowledge_Bundle__c`** (one per received bundle; Sharing: Private)

| Field | Type | Notes |
|---|---|---|
| `Name` | Auto number `KB-{000000}` | |
| `Bundle_Key__c` | Text(255), External Id, unique | `<bundle.id>#<first 16 hex of bundle.contentHash>` (section 7.1) |
| `Bundle_Id__c` | Text(255) | SB-7 `bundle.id` |
| `Content_Hash__c` | Text(71) | `sha256:` plus 64 hex |
| `Source_Repo__c`, `Source_Ref__c` | Text(255) | |
| `Source_Commit__c` | Text(40) | |
| `Generated_At__c` | Date/Time | Ordering key (7.1) |
| `Generator__c` | Text(255) | `name@version` |
| `State__c` | Picklist `receiving`, `committing`, `committed`, `failed`, `superseded` | `committing` is reported as `receiving` over the API (7.4) |
| `Page_Count__c`, `Pages_Received__c` | Number(6,0) | |
| `Sequence__c` | Number(10,0), unique | Set when the commit starts |
| `Is_Current__c` | Checkbox | Exactly one true after the first commit |
| `Nodes_Upserted__c`, `Nodes_Unchanged__c`, `Nodes_Deleted__c` | Number(9,0) | |
| `Errors__c` | Long Text Area(131072) | JSON array of SB-7 Error objects, at most 50 items |
| `Stats__c` | Long Text Area(32768) | SB-7 `stats` as JSON |

**`Knowledge_Bundle_Page__c`** (Master-Detail to `Knowledge_Bundle__c`)

| Field | Type | Notes |
|---|---|---|
| `Page_Key__c` | Text(255), External Id, unique | `<Bundle_Key__c>#<page.index>`; makes a duplicate page a no-op |
| `Page_Index__c` | Number(6,0) | |
| `Content_Version_Id__c` | Text(18) | The staged page JSON, stored as a ContentVersion linked to the bundle record |
| `Node_Count__c`, `Edge_Count__c` | Number(6,0) | |

**`Knowledge_Node__c`** (one row per node version; Sharing: Private)

| Field | Type | Notes |
|---|---|---|
| `Name` | Text(80) | Title truncated to 80 chars |
| `Version_Key__c` | Text(100), External Id, unique | `<sha256 hex of node id>@<Valid_From__c>` (node ids may be 255 chars, longer than an external id allows with a suffix) |
| `Node_Id__c` | Text(255), indexed (External Id, not unique) | SB-7 node `id` |
| `Path__c` | Text(255) | Longer paths are rejected at intake with `INVALID_BUNDLE` |
| `Title__c` | Text(255) | Truncated to 255 for filtering and sorting |
| `Title_Full__c` | Long Text Area(1024) | Full title (SB-7 allows up to 512 chars); results return this one |
| `Kind__c` | Picklist `note`, `attachment` | |
| `Body__c` | Long Text Area(131072) | Chunk 0 (SB-7 3.3) |
| `Chunk_Count__c` | Number(4,0) | 0 when not chunked |
| `Frontmatter__c` | Long Text Area(131072) | Canonical JSON |
| `Tags__c` | Long Text Area(32768) | Tags joined with ` ` and wrapped in spaces (` a b/c `), for `LIKE '% tag %'` filters and SOSL |
| `Aliases__c` | Long Text Area(32768) | JSON array |
| `Content_Hash__c` | Text(71) | |
| `Edges_Hash__c` | Text(71) | sha256 over the canonical JSON of the node's outgoing edges (7.3) |
| `Updated_At__c` | Date/Time | |
| `Valid_From__c`, `Valid_To__c` | Number(10,0) | Section 6.1 |
| `Closed_At__c` | Date/Time | Set when a commit sets `Valid_To__c`; drives purge (section 8) |
| `Deleted_At__c` | Date/Time | Set when a commit closes the row because the node left the vault |

**`Knowledge_Node_Chunk__c`** (Master-Detail to `Knowledge_Node__c`): `Chunk_Index__c` Number(4,0) (1-based for chunks after 0), `Text__c` Long Text Area(131072), `Hash__c` Text(71).

**`Knowledge_Edge__c`** (one row per edge version; Sharing: Private)

| Field | Type | Notes |
|---|---|---|
| `Source_Node_Id__c` | Text(255), indexed | |
| `Target_Node_Id__c` | Text(255), indexed | Null when unresolved. Text, not a lookup, so a target's new version does not touch its incoming edges |
| `Target_Text__c` | Text(255) | |
| `Type__c` | Picklist `wikilink`, `embed`, `tag`, `relation` | |
| `Relation__c`, `Anchor__c` | Text(255) | |
| `Resolved__c` | Checkbox | |
| `Valid_From__c`, `Valid_To__c` | Number(10,0) | |
| `Closed_At__c` | Date/Time | Set when a commit sets `Valid_To__c` |

**`Knowledge_Sync_Setting__mdt`** (one record `Default`, packaged, subscriber-editable): `Purge_After_Days__c` Number (default 30; 0 means purge at the end of each commit), `Keep_Bundles__c` Number (default 10), `Max_Errors__c` Number (default 50).

**Permission set `Knowledge_Sync`**: custom permission `Knowledge_Import`; Apex class access to `KnowledgeBundlesResource`; create/read on `Knowledge_Bundle__c` and `Knowledge_Bundle_Page__c`; no read on node or edge objects (the integration user only writes through Apex running in system mode). Read access for end users comes with SB-9's reader permission set.

## 7. Import endpoint and commit (slice 8b)

### 7.1 Bundle identity and ordering (contract clarifications)

These settle QA notes 1 and 2 on PR #7. They change no schema; they define runtime behaviour the SB-7 contract left open, and every runtime must follow them. The Developer copies the three rules into the `importBundlePage` and `getImportStatus` descriptions in `knowledge-services.openapi.yaml` in the 8b PR (an additive description change, allowed as v1.0 per SB-7 section 7).

1. **Import key = (`bundle.id`, `bundle.contentHash`).** Re-compiling the same commit with a newer compiler that changes the output is a new import. Re-sending identical content is a no-op. This refines SB-7 4.4 rule 4.
2. **Ordering key = `bundle.generatedAt`**, ties broken by `bundle.id` in lexical order. "Older" and "newer" in SB-7 4.3 (`BUNDLE_CONFLICT`) and 4.4 rule 5 (supersede) mean this order. Runtimes cannot see commit ancestry, so the producer must not push stale commits; the workflow's stale-commit guard (5.2 step 4) ensures that.
3. `GET /bundles/{bundleId}` returns the status of the newest import with that `bundle.id` (by ordering key).

### 7.2 Page intake: `POST /knowledge/v1/bundles/{bundleId}/pages`

Synchronous Apex, in this order:

1. Caller lacks custom permission `Knowledge_Import`: `403 FORBIDDEN`.
2. Body over 3,000,000 bytes: `413 PAYLOAD_TOO_LARGE`.
3. JSON parse failure, or structural validation failure: `422 INVALID_BUNDLE` with `details[]` of `{path, rule}`. Apex cannot run JSON Schema, so `KnowledgeImportService` checks the rules that matter for safety: `schemaVersion = "1.0"`; required properties present; node id pattern; hash pattern; commit pattern; `page.index <= page.count`; `kind` and edge `type` enums; `resolved` is false exactly when `target` is null; every edge `source` is a node on the same page; `Path__c` and other Text(255) values fit. The full JSON Schema check already ran in CI (4.2), so this is defence in depth, not the only gate.
4. Path `bundleId` differs from `bundle.id` in the body: `400 INVALID_REQUEST`.
5. Lock with `SELECT ... FOR UPDATE` the `Knowledge_Bundle__c` for this import key, creating it in `receiving` if absent. Then:
   - The import key already exists as `committed`, `committing` or `superseded`: return its status, `200`. No change.
   - The current committed bundle is newer by the ordering key: `409 BUNDLE_CONFLICT`.
   - `page.count` differs from the stored `Page_Count__c`: `409 BUNDLE_CONFLICT`.
   - A page with the same `Page_Key__c` exists: return status, `200`. No change.
6. Store the raw page as a ContentVersion linked to the bundle record; insert `Knowledge_Bundle_Page__c`; increment `Pages_Received__c`.
7. Any other import in `receiving` that is older by the ordering key becomes `superseded`; its staged pages are deleted.
8. If `Pages_Received__c = Page_Count__c`: set `committing` and enqueue `KnowledgeImportCommitJob`. Only one import may be `committing` at a time; if another is, the job re-enqueues itself with a delay (`System.enqueueJob(job, delayMinutes)`) and tries again.
9. Return `202` with `ImportStatus` (`200` for the no-op cases above).

`GET /knowledge/v1/bundles/{bundleId}` returns `ImportStatus` per 7.1 rule 3. For an unknown bundle it returns `404` with a new error code **`BUNDLE_NOT_FOUND`**: SB-7 4.3 only defines `NODE_NOT_FOUND`, which would mislead. A new enum value is additive and allowed in v1.0 (SB-7 section 7); the Developer adds it to the OpenAPI error enum in the 8b PR. Same permission check as intake (`403` without `Knowledge_Import`).

### 7.3 Commit job

`KnowledgeImportCommitJob` is a Queueable chain, one staged page per execution, then a finalise step. With the 2 MB page budget the parsed page fits the 12 MB async heap.

1. **Start:** assign `Sequence__c = current sequence + 1` (*N*); load the set of node ids and their `Content_Hash__c` and `Edges_Hash__c` for rows visible at *N-1* into a map stored on the job, paged with a query cursor if large (a 10,000-node vault is about 1 MB of keys).
2. **Per page:** for each node:
   - Absent from the map, or `contentHash` differs: insert a new `Knowledge_Node__c` row (`Valid_From__c = N`) with its chunks; close the old row (`Valid_To__c = N`); insert its edges with `Valid_From__c = N`; close the old row's edges.
   - Same `contentHash` but the edges hash differs (for example a link became resolved because its target note was added): leave the node row; insert the new edges, close the old ones.
   - Both equal: count as unchanged.
   - Record the node id as "seen".
3. **Finalise:**
   - Cross-page checks: total nodes equals `stats.nodeCount`; total edges equals `stats.edgeCount`; no node id appears on two pages. Any failure goes to rollback.
   - Nodes visible at *N-1* and not seen: close their row and edges with `Valid_To__c = N`, set `Deleted_At__c`.
   - In one DML: set the old current bundle `Is_Current__c = false`, the new one `Is_Current__c = true` and `State__c = committed`, and write counts.
   - Delete the staged ContentVersions and page rows. Enqueue the purge job.
4. **Rollback** (any exception or failed check, including a failure in a later chained job): delete rows with `Valid_From__c = N`; clear `Valid_To__c = N` back to null, with the `Closed_At__c` and `Deleted_At__c` values this commit set; set `State__c = failed` with `Errors__c`; delete staged pages. The current bundle never changed, so the previous knowledge stays queryable (REQ-1 AC 3). A failure inside rollback leaves `State__c = failed` with an `INTERNAL` error, and the next commit's start step first repeats the rollback for any sequence greater than the current one.

The job uses `Database.Savepoint` within each execution and the sequence-based rollback across executions. It runs `without sharing` and writes only package objects.

### 7.4 State mapping to the contract

| Stored `State__c` | API `state` (SB-7 `ImportStatus`) |
|---|---|
| `receiving`, `committing` | `receiving` (callers see `pagesReceived = pageCount` while committing) |
| `committed`, `failed`, `superseded` | same |

## 8. Purge and retention (closes gap GD-3, proposal for Alex to confirm per pilot)

Proposed policy: **soft delete at commit, hard delete after a retention window.**

- A commit only closes rows (6.1). Closed rows are invisible to every read immediately.
- `KnowledgeImportPurgeJob` hard-deletes node rows (and their chunks) and edge rows whose `Valid_To__c <= current sequence` and whose `Closed_At__c` is more than `Purge_After_Days__c` days ago (default 30). This covers both deleted notes and old versions of edited notes.
- `Purge_After_Days__c = 0` gives immediate hard delete at the end of every commit, for pilots with strict right-to-delete needs.
- Bundles: keep the newest `Keep_Bundles__c` (default 10) `Knowledge_Bundle__c` records; delete older ones that are not current.
- It runs after every commit and on a daily schedule. The schedule is registered by a post-install script (SB-12), not by the package itself, so install stays free of side effects.
- Purged rows go to the Recycle Bin by default; the job calls `Database.emptyRecycleBin` on them so purge is final.
- The retention window exists so an admin can inspect what a bad commit removed. It is not a restore feature; restoring means re-syncing an older vault commit.

The Enterprise Architect records the confirmed policy per pilot in Notion (gap GD-3). The default in the package is the proposal above.

## 9. Error handling summary

| Situation | Where caught | Result | Reported to |
|---|---|---|---|
| Vault file not UTF-8, bad frontmatter, id collision, node too large | kg-compiler | Exit 1 before anything is pushed | Workflow run fails; step log lists `path:line` |
| Bundle fails its own schema | kg-compiler (contracts-check library) | Exit 1, nothing pushed | Workflow run fails |
| Stale commit | Workflow guard | Push skipped, run succeeds with a notice | Step summary |
| Auth failure | `sf org login jwt` or `401` | Exit 1 | Workflow run fails |
| Network or `5xx` or `429` | kg-push | Retried up to 5 times, then exit 1 | Workflow run fails |
| Invalid page | Import endpoint | `422 INVALID_BUNDLE`, nothing staged | kg-push prints details; run fails |
| Older bundle | Import endpoint | `409 BUNDLE_CONFLICT` | kg-push exits 1 with the conflict |
| Cross-page check fails, or Apex error during commit | Commit job | Rollback; `failed`; previous bundle stays current | `GET /bundles/{id}` errors; kg-push exits 1; `Knowledge_Bundle__c` record in the org |
| Commit not finished in time | kg-push timeout | Exit 1; the commit may still finish | Run fails; next run sees the committed state |

No error message or log line contains note text, tokens or org identifiers. Errors cite node id or vault path and the rule broken.

## 10. Test approach

### 10.1 kg-compiler and kg-push (pytest, slice 8a)

Synthetic fixture vaults, all content invented ("Example Corp"):

| Fixture | Proves |
|---|---|
| `basic/` (4 notes, 1 attachment, frontmatter, tags, aliases, wikilinks, an embed, a relation) | Every node and edge field; stats; schema-valid bundle and pages |
| `links/` | Path links, base-name links, case differences, ambiguous names (warning), unresolved links, anchors, block refs, labels, Markdown links, links inside code ignored |
| `chunking/` (one note over `maxChunkChars`, small value set in the test) | Chunk split rule, concatenation equals body, hashes |
| `collision/` (`A B.md` and `A-B.md`) | `ID_COLLISION` exit 1 |
| `bad-encoding/`, `bad-frontmatter/` | Exit 1 with path |
| `paging/` (generated 450 small notes) | Page limits by count and by bytes; edges on the source's page; `NODE_TOO_LARGE` |
| Determinism | Compile `basic/` twice: identical except `generatedAt`; identical `contentHash` |
| Change detection | `basic/` v1 then v2 (one note added, one edited, one deleted): node hashes and bundle hash change exactly where expected |
| kg-push against a local stub server (Python `http.server`) | Page order, retry on `503` and `429`, no retry on `422`, polling to `committed`, exit codes for `failed`, `superseded`, timeout; token never in output |

### 10.2 Apex (slice 8b)

Run with `sf apex run test --test-level RunLocalTests`; coverage at least 85 % on the import, commit and purge classes. Tests build pages with a test factory (no static resource with real content):

1. First import: rows at sequence 1, `Is_Current__c`, counts.
2. Same import key again: no-op, `200`, no new rows.
3. Same `bundle.id`, different `contentHash`: new import, new sequence.
4. Add, edit, delete one node each: visible set at the new sequence is right; old versions closed; deleted node has `Deleted_At__c`.
5. Edge-only change (target added): node row unchanged, edges replaced.
6. Pages out of order and a duplicated page.
7. Each structural rule in 7.2 step 3 returns `422` with the right `details[].rule`.
8. Older bundle after a newer commit: `409`.
9. Newer bundle while an older one is `receiving`: older becomes `superseded`.
10. Stats mismatch at finalise: `failed`, rollback, previous bundle still current and readable through `KnowledgeStore`.
11. Exception injected in the second chained job: same rollback result.
12. Purge with `Purge_After_Days__c = 0` and with the default (`Closed_At__c` moved back in test data).
13. Missing `Knowledge_Import` permission: `403` (`System.runAs` a user without the permission set).
14. Chunked node: chunks stored and reassembled by `KnowledgeStore`.

### 10.3 End to end (slice 8c)

Script `packages/salesforce/scripts/e2e-sync.sh`, run by the Developer against a fresh scratch org (needs the Dev Hub from section 12):

1. Create a scratch org; install the package version or push source; assign `Knowledge_Sync` to the running user.
2. Compile `tools/kg-compiler/tests/fixtures/basic` and push with kg-push. Expect `committed`.
3. Query with `sf data query` (SB-9 may not exist yet): current nodes, their tags and frontmatter, and edges. Compare with the fixture's expected JSON.
4. Compile the v2 fixture (add, edit, delete) and push. Query again; expect exactly the changes.
5. Push a deliberately broken page set (stats mismatch). Expect kg-push exit 1, state `failed`, and step 3's query still returning the v2 data.
6. The output of all steps is the PR's test evidence.

## 11. Acceptance-criteria mapping

| # | Acceptance criterion (SB-8 story / REQ-1) | Met by | Verified by |
|---|---|---|---|
| 1 | Given a sample vault with notes and wikilinks, a sync run makes notes, links and metadata queryable in a scratch org | Compiler (4), push (5), storage and import (6, 7) | 10.1 `basic/`; 10.2 test 1; 10.3 steps 2 and 3 |
| 2 | Adds, edits and deletes in the vault are reflected on the next run | Content and edge hashes, versioned rows, deletion of unseen nodes (7.3) | 10.1 change detection; 10.2 tests 4 and 5; 10.3 step 4 |
| 3 | An invalid bundle is rejected, prior knowledge stays queryable and the failure is reported | Compiler self-validation (4.2), intake validation (7.2), atomic switch and rollback (6.1, 7.3), error reporting (9) | 10.1 bad fixtures; 10.2 tests 7, 10 and 11; 10.3 step 5 |
| 4 | Uses the sync approach approved in ADR-001 | Option A: compile in CI, push through the package's own import endpoint; bundle is SB-7 kg-bundle v1 | This spec's header and sections 4, 5 and 7; QA review |
| 5 | REQ-1: notes, links and metadata available in a queryable form | Node, chunk and edge objects (6.2) read through `KnowledgeStore` | 10.3 step 3 |

## 12. Dependencies and open points

**Alex account actions** (already listed in ADR-001 Consequences; none blocks slices 8a or 8b):

- Enable a Dev Hub and register the package namespace (also needed by SB-12).
- For 8c and for real vaults: a connected app with a JWT certificate and an integration user per target org, with the secrets stored in the vault repository's GitHub Actions secrets.
- Confirm which repository holds the vault. It must not be this public repository if it holds client content.

**Open points (do not block build):**

- AGENTS.md ownership rows for `tools/`, `templates/` and `packages/` (TA Inbox Blocker of 2026-10-15, decision b).
- Gap GD-3: Alex confirms the purge default (30 days) or a per-pilot value.
- Contract clarifications in 7.1 and the `BUNDLE_NOT_FOUND` code are written into the OpenAPI document by the 8b PR. If Alex prefers them in the SB-7 spec text as well, the TA adds an errata section to `SB-7.md` after PR #7 merges.

## 13. Definition of done for the Developer PRs

- Files in section 3 for the slice exist; tests in section 10 for the slice pass, with commands and output in the PR.
- 8a: no Salesforce code outside `kg_push/auth_salesforce.py`; contracts-check passes on generated output.
- 8b: no change to `contracts/` other than the description and enum additions in 7.1 and 7.2.
- No client content, credentials, org IDs or instance URLs anywhere, including fixtures and logs.
- `python build.py` is unaffected (no changes to `research/`, `template.html` or `build.py`).
- Each PR links SB-8 and this spec. The story's PR Link points at the latest slice PR.
