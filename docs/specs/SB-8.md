# SB-8: Knowledge-graph sync (compile the Obsidian vault from GitHub and load it into the org)

- **Story:** SB-8 (Notion Sprint Board, shown as RSP-8) "Knowledge-graph sync: compile Obsidian vault from GitHub and load it into the org"
- **Requirements:** REQ-1 Knowledge-graph sync from GitHub-hosted Obsidian vault (Must, Approved)
- **ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) (Approved 2026-10-15), decision points 2 and 3 (sync option A: compile in CI, push through the package's own import endpoint)
- **Contracts:** [SB-7 spec](SB-7.md) (kg-bundle v1, knowledge services v1). Until PR #7 merges, read it on the branch `agent/technical-architect/SB-7`.
- **Inputs taken into account:** QA notes 1 and 2 on PR #7 (bundle ordering, re-compile idempotency); Phase C data gaps GD-3 (hard purge) and GD-5 (bundle artifact retention) in `docs/togaf/C-data.md` (PR #10, branch `agent/enterprise-architect/SB-15`); IP boundary in `docs/design/ip-boundary.md` (PR #8, branch `agent/technical-architect/SB-13`); QA reviews of this spec on PR #11 (M1 to M7, m1 to m8, nits on 2026-10-19; N1, n1, n2 on 2026-10-20)
- **Principles:** AP-1 Runtime-neutral contracts, AP-2 One service core, SP-1 Public-repo hygiene ([principles.md](../togaf/principles.md))
- **Spec author:** Technical Architect, 2026-10-19; revised 2026-10-20 and 2026-10-21 for the QA reviews on PR #11 (see sections 14 and 15)
- **Builder:** Developer

## 1. Goal

Make the notes, links and metadata of an Obsidian vault in a GitHub repository queryable inside a Salesforce org, keep the org in step with adds, edits and deletes, and never leave the org with half-loaded or invalid knowledge.

The work has a runtime-neutral half (compile and push, reusable by any future runtime) and a Salesforce half (storage objects and the import endpoint). Reads (`getNode`, `searchNodes`, `getNeighbors`, `getContext`) are SB-9; this story only has to make the data queryable (SOQL is enough to prove it).

Out of scope: semantic or vector search, orgs pulling bundles themselves (ADR-001 option B2), any hosted sync service (option C), per-node access control (REQ-15 is Needs Alex).

## 2. Build order and slices

| Slice | Contents | Depends on | Can start |
|---|---|---|---|
| 8a | `tools/kg-compiler`, `tools/kg-push`, vault-repo workflow template, `contracts-check` made pip-installable (sections 3, 4, 5) | SB-7 build (schemas and `contracts-check` library) | After the SB-7 Developer PR merges |
| 8b | Storage objects, import endpoint, commit step runner and jobs, purge job (sections 6, 7, 8) | SB-12 slice 12a (SFDX project skeleton, `packages/salesforce/`) | After SB-12 slice 12a merges |
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
    pyproject.toml                  pins pyyaml and jsonschema; depends on the contracts-check package (section 4.2)
  contracts-check/                  from SB-7; 8a adds a pyproject.toml so it installs as package `contracts_check` (section 4.2)
  kg-push/                          Python 3.12 CLI, runtime-neutral apart from an auth adapter
    kg_push/
      cli.py                        `kg-push push ...`
      client.py                     importBundlePage / getImportStatus over HTTP (SB-7 4.1)
      auth_salesforce.py            gets base URL and bearer token from the Salesforce CLI (section 5.1)
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
  objects/Knowledge_Node_Tag__c/ ...
  objects/Knowledge_Edge_Set__c/ ...
  objects/Knowledge_Edge__c/ ...
  customMetadata / objects/Knowledge_Sync_Setting__mdt/ ...
  permissionsets/Knowledge_Sync.permissionset-meta.xml
  customPermissions/Knowledge_Import.customPermission-meta.xml
packages/salesforce/force-app/main/service/classes/
  KnowledgeImportService.cls        page intake, validation, state machine
  KnowledgeCommitStepRunner.cls     one bounded unit of commit or rollback work per call; state on the bundle record (7.3)
  KnowledgeImportCommitJob.cls      Queueable that calls the step runner and re-enqueues itself (7.3)
  KnowledgeImportResumeJob.cls      Schedulable that starts a fresh Queueable chain at the depth limit or after a failed-step back-off (7.3)
  KnowledgeSyncWatchdogJob.cls      hourly Schedulable that restarts stalled commits, rollbacks and cleanups (7.3)
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
                    [--config <file>] [--contracts-dir <dir>] [--max-chunk-chars 100000]
                    [--page-max-nodes 200] [--page-max-bytes 1000000] [--page-max-edges 5000]
                    [--node-max-edges 1000] [--node-max-tags 100]
```

`--repo` is an opaque label (SB-7 `source.repo`), never a URL with credentials. `--contracts-dir` points at the SB-7 `contracts/` folder; the vault workflow passes the copy it checks out at the pinned tag (5.2), and local runs in this repository default to `<repo root>/contracts`. Config defaults to `<vault>/kg-compiler.yml` if present:

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

Before writing, the compiler validates `bundle.json` and every page with the SB-7 schemas and semantic checks by calling the `contracts_check` package against `--contracts-dir`. A bundle that fails its own contract is never written.

Packaging (closes QA M6): slice 8a adds `tools/contracts-check/pyproject.toml` so the SB-7 checker installs as the package `contracts_check` with a callable API (`validate_bundle(doc, contracts_dir)`, `validate_page(doc, contracts_dir)`); its existing CLI keeps working. The schemas are **not** copied into kg-compiler or into the package: they are read from `--contracts-dir`, so there is one copy of the contract. Missing or unreadable `--contracts-dir` is exit `2` with a clear message, never a silent skip.

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
- **Bundle id** (defines SB-7's `<source.repo-slug>@<source.commit>`, closes QA m3): the repo slug is `--repo` lower-cased, with `/` replaced by `--` and every other character outside `[a-z0-9._-]` replaced by `-`. Example: `Example-Org/KB-Vault` gives `example-org--kb-vault`, and the bundle id is `example-org--kb-vault@<40-hex commit>`. Pattern: `^[a-z0-9][a-z0-9._-]{0,179}@[0-9a-f]{40}$`, so a bundle id is at most 221 characters, `Bundle_Key__c` at most 238 and `Page_Key__c` at most 245, all inside Text(255) (QA n1). A GitHub `owner--repo` slug is at most 141 characters; a longer slug (only possible with a hand-set `--repo`) makes the compiler exit 1 with `REPO_SLUG_TOO_LONG`. The id has no `/`, so it is one URL path segment; kg-push still percent-encodes it (RFC 3986) and runtimes decode it. Intake rejects any other shape with `400 INVALID_REQUEST`.
- Canonical JSON for every hash: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` encoded as UTF-8.
- Node `contentHash`: SB-7 3.2 (full body plus canonical frontmatter JSON).
- **Bundle `contentHash` (clarifies SB-7 3.2, which says "over node and edge hashes" but edges have no hash):** sha256 over the canonical JSON of `{"nodes": [[id, contentHash, path, title, kind], ...], "edges": [edge, ...]}`, nodes sorted by id and edges sorted as below, each edge as its full canonical object. Path, title and kind are included so that a case-only rename (`Foo.md` to `foo.md`, same id and same node hash) still changes the bundle hash and is applied (QA m4). Slice 8a writes this rule into the `bundle.contentHash` description in `contracts/kg-bundle/v1/kg-bundle.schema.json` and adds a contracts-check semantic check that recomputes it, so a second compiler that hashes differently fails validation (QA m2). This is a description change plus a check of an existing property, so the bundle schema stays `1.0`.
- Sort order: nodes by `id`; edges by `(source, type, relation or "", target or "", anchor or "", targetText)`.
- Chunking per SB-7 3.3 with `maxChunkChars`.
- Determinism: compiling the same commit twice gives byte-identical `nodes`, `edges`, `stats` and `contentHash`. Only `bundle.generatedAt` (and `bundle.generator.version` across compiler upgrades) may differ. A test enforces this (10.1).

### 4.6 Pagination

- Fill pages in node-id order up to `--page-max-nodes` nodes, `--page-max-edges` edges **and** `--page-max-bytes` bytes of canonical page JSON, whichever comes first. The 1 MB byte default keeps the intake transaction well inside the 6 MB synchronous heap: the request body, one parsed tree and the stored file copy together stay under about 4 MB (QA m6). These limits bound heap and query sizes; DML rows are budgeted separately by the commit step runner (7.3).
- Per-node limits, so that one node's writes always fit one commit execution (7.3): more than `--node-max-edges` outgoing edges is error `NODE_TOO_MANY_EDGES`, more than `--node-max-tags` tags is error `NODE_TOO_MANY_TAGS`, a tag longer than 255 characters is error `TAG_TOO_LONG`. Each names the path. These are runtime parameters of the compiler, not schema constants (SB-7 3.1).
- Edges go on the page that carries their `source` node (SB-7 3.4).
- A single node whose page would exceed `--page-max-bytes` on its own: error `NODE_TOO_LARGE` naming the path and size. With the defaults this is a note of roughly 0.9 MB of text, far beyond normal notes.
- The last page carries `deletions: []`. The compiler cannot know what the target holds; runtimes derive deletions as "absent from every page" (SB-7 3.4).

## 5. kg-push and the vault workflow (slice 8a)

### 5.1 kg-push

```
kg-push push --pages <dir> --base-url <url> --token-env <VAR>
             [--timeout 600] [--poll-interval 5] [--max-retries 5]
kg-push salesforce-auth --target-org <alias> --token-env <VAR>   prints base URL; writes VAR=<token> to $GITHUB_ENV
```

1. Send pages in index order with `POST {baseUrl}/bundles/{bundleId}/pages` (bundle id percent-encoded, 4.5), one at a time.
2. Retry on `429`, `5xx` and network errors with exponential backoff (1, 2, 4, 8, 16 s); never on `4xx` other than `429`. A retried page is harmless because page intake is idempotent (7.2).
3. After the last page, poll `GET {baseUrl}/bundles/{bundleId}` until `state` is `committed`, `failed` or `superseded`, or `--timeout` passes.
4. Exit `0` only on `committed`. On `failed` print every `errors[]` item and exit `1`. On `superseded` print a notice and exit `0` (a newer commit is being loaded). On timeout exit `1`.
5. Never print the token. Log lines carry bundle id, page index, HTTP status and error code only, never note content.
6. `salesforce-auth`: the token from `sf org display` is not a GitHub secret, so Actions does not mask it. When `GITHUB_ACTIONS=true`, the command first prints `::add-mask::<token>` and only then appends the token to `$GITHUB_ENV`; it never writes the token anywhere else (QA m8). Outside Actions it refuses to write `$GITHUB_ENV` and prints only the base URL.

`kg-push` speaks only the SB-7 HTTP contract. The one Salesforce-specific piece is `auth_salesforce.py`, which runs `sf org display --target-org <alias> --json` and reads `instanceUrl` and `accessToken`; the base URL becomes `<instanceUrl>/services/apexrest/<ns>/knowledge/v1`. A future runtime adds its own auth adapter and reuses everything else.

### 5.2 Workflow template `templates/vault-sync/kg-sync.yml`

- **Triggers:** `push` to the vault's default branch, and `workflow_dispatch`. The job has `if: github.ref_name == github.event.repository.default_branch`, so a manual run from another branch does nothing (QA m5).
- **Concurrency:** one group per target org, `group: kg-sync-${{ vars.KG_SYNC_TARGET || 'default' }}`, `cancel-in-progress: false`, so two syncs to one org never interleave whatever triggered them. The runtime also re-checks ordering when a commit starts (7.3), so ordering does not rely on the workflow alone.
- **Steps:**
  1. Check out with `fetch-depth: 0` (needed for `updatedAt`).
  2. Check out this repository at a pinned tag into `.rsp/` (`actions/checkout` with `repository: africh/rich-solutions-platform`, `ref: <tag>`, `path: .rsp`, `sparse-checkout: contracts` and `tools`). Pinned tag, never `main`. The repository is public, so no token is needed.
  3. Set up Python 3.12; `pip install ./.rsp/tools/contracts-check ./.rsp/tools/kg-compiler ./.rsp/tools/kg-push` (closes QA M6: the checker, its schemas and both CLIs come from the same tag).
  3a. `kg-compiler compile ... --contracts-dir .rsp/contracts` with `--repo "${{ github.repository }}" --ref "${{ github.ref_name }}" --commit "${{ github.sha }}"`.
  4. **Stale-commit guard** (QA note 1 on PR #7): `git ls-remote origin "refs/heads/${{ github.ref_name }}"`. If the branch head is no longer `${{ github.sha }}`, stop with a notice "newer commit exists; skipping push". Re-running an old workflow therefore cannot load an older vault over a newer one.
  5. Install the Salesforce CLI; `sf org login jwt --client-id "$SF_CLIENT_ID" --jwt-key-file <tmp file from SF_JWT_KEY> --username "$SF_USERNAME" --instance-url "$SF_INSTANCE_URL" --alias target`; delete the key file right after login.
  6. `kg-push salesforce-auth --target-org target --token-env KG_TOKEN` (masks the token, 5.1 rule 6), then `kg-push push ... --token-env KG_TOKEN`.
  7. Write `summary.json` fields and the final import status to `$GITHUB_STEP_SUMMARY`.
- **Secrets (in the vault repository, never in this one):** `SF_CLIENT_ID`, `SF_JWT_KEY`, `SF_USERNAME`, `SF_INSTANCE_URL`. One integration user per org, assigned the `Knowledge_Sync` permission set only.
- **Failure reporting:** any failed step fails the workflow run, so GitHub's normal failure notification reaches the vault owner, and the step summary shows the error codes.

### 5.3 Artifact retention (closes gap GD-5)

- The template uploads **only** `summary.json`, with `retention-days: 7`. It never uploads `bundle.json` or `pages/`, because they contain the full note text.
- `templates/vault-sync/README.md` says so, and adds that the repository's default artifact and log retention should be lowered for sensitive vaults. It also points to the self-hosted runner option (gap GD-4, owned by the Enterprise Architect).
- This departs on purpose from ADR-001 option A's "bundle as build artifact / release asset": with push delivery (A) the org never needs a stored bundle, and storing it would keep full note text in GitHub. If a later runtime pulls bundles (option B2), that runtime's adapter adds an opt-in, access-controlled bundle upload; the compiler output is already the right shape.

## 6. Storage objects (slice 8b)

All objects are in the base package, Storage layer. Field names below are without the namespace prefix. Sharing: Private or ControlledByParent as noted; access is via permission sets only.

### 6.1 Versioned rows

Readers must keep seeing the previous committed bundle until a new one commits (SB-7 4.4 rule 2), and a commit may span several transactions. So the two **versioned row** objects, `Knowledge_Node__c` (one row per node version) and `Knowledge_Edge_Set__c` (one row per version of a node's outgoing edges), are **versioned by bundle sequence**:

- Every committing bundle gets an integer `Sequence__c` (1, 2, 3 ...), allocated as in 7.3.
- A versioned row is visible at sequence *S* when `Valid_From__c <= S` and (`Valid_To__c` is null or `Valid_To__c > S`).
- Chunks and tags are Master-Detail children of a node version; edges are Master-Detail children of an edge set version. Children carry no validity fields: they are visible exactly when their parent is. Replacing a node's edges is therefore one edge-set insert and one edge-set close, however many edges it has, and rollback never touches child rows one by one except through cascade delete.
- The node row and the edge set version independently. An edge-only change (for example a link that became resolved because its target note was added) writes a new edge set and leaves the node row alone; because the edge hash lives on the versioned edge set row, rollback restores it like any other row (closes QA M2).
- The current sequence is the `Sequence__c` of the one `Knowledge_Bundle__c` with `Is_Current__c = true`.
- A commit at sequence *N* only inserts versioned rows with `Valid_From__c = N` and sets `Valid_To__c = N` on versioned rows it replaces. It never updates any other field of a row visible at *N-1*. Readers at *N-1* see none of that. The last step of the commit flips `Is_Current__c` in one DML statement, so the switch is atomic.

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
| `Sequence__c` | Number(10,0), unique (nulls allowed) | Allocated when the commit starts; cleared when a rollback completes (7.3), so a failed commit never holds a sequence number (closes QA M1) |
| `Attempt__c` | Number(4,0) | 1 on first receipt; incremented when a `failed` import is retried (7.2 step 5) |
| `Commit_Phase__c` | Picklist `check`, `apply`, `close_unseen`, `switch`, `rollback`, `done` | Step-runner position (7.3). Cleared when `done` finishes, so a `committed` bundle with `Commit_Phase__c = done` has cleanup pending |
| `Commit_Page__c` | Number(6,0) | Page being applied |
| `Commit_Cursor__c` | Text(255) | Last node id processed in the current phase (keyset cursor) |
| `Last_Step_At__c` | Date/Time | Set by every step; the watchdog in 7.3 uses it |
| `Step_Failures__c` | Number(2,0) | Consecutive failed attempts of a `rollback` or `done` step; reset to 0 by any successful step (7.3) |
| `Cleanup_Error__c` | Text(255) | Last `done` failure (error code and step, no note text). Internal only: not returned in `ImportStatus`, because the commit itself succeeded |
| `Is_Current__c` | Checkbox | Exactly one true after the first commit |
| `Nodes_Upserted__c`, `Nodes_Unchanged__c`, `Nodes_Deleted__c` | Number(9,0) | |
| `Errors__c` | Long Text Area(131072) | JSON array of SB-7 Error objects, at most 50 items |
| `Stats__c` | Long Text Area(32768) | SB-7 `stats` as JSON |

**`Knowledge_Bundle_Page__c`** (Master-Detail to `Knowledge_Bundle__c`)

| Field | Type | Notes |
|---|---|---|
| `Page_Key__c` | Text(255), External Id, unique | `<Bundle_Key__c>#<page.index>`; makes a duplicate page a no-op |
| `Page_Index__c` | Number(6,0) | |
| `Content_Document_Id__c` | Text(18) | The staged page JSON, stored as a file (ContentVersion) linked to the bundle record; the ContentDocument id is kept because files are deleted through their ContentDocument (QA m7) |
| `Node_Count__c`, `Edge_Count__c` | Number(6,0) | |
| `Node_Ids__c` | Long Text Area(131072) | Newline-separated node ids on this page (at most 200 x 256 chars), used by the check and close-unseen phases without re-reading the file |

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
| `Tags__c` | Long Text Area(32768) | JSON array, for returning results only. Long Text Area cannot be used in a SOQL `WHERE`, so tag filters use `Knowledge_Node_Tag__c` (closes QA M4) |
| `Tag_Count__c` | Number(4,0) | |
| `Aliases__c` | Long Text Area(32768) | JSON array |
| `Content_Hash__c` | Text(71) | |
| `Updated_At__c` | Date/Time | |
| `Valid_From__c`, `Valid_To__c` | Number(10,0) | Section 6.1 |
| `Closed_At__c` | Date/Time | Set when a commit sets `Valid_To__c`; drives purge (section 8) |
| `Deleted_At__c` | Date/Time | Set when a commit closes the row because the node left the vault |

**`Knowledge_Node_Chunk__c`** (Master-Detail to `Knowledge_Node__c`): `Chunk_Index__c` Number(4,0) (1-based for chunks after 0), `Text__c` Long Text Area(131072), `Hash__c` Text(71).

**`Knowledge_Node_Tag__c`** (Master-Detail field `Node__c` to `Knowledge_Node__c`): `Tag__c` Text(255), indexed (External Id, not unique), lower-case as compiled. SB-9's tag filter is a semi-join on the node version, for example `Id IN (SELECT Node__c FROM Knowledge_Node_Tag__c WHERE Tag__c IN :tags)` combined with the visibility filter, built only inside `KnowledgeStore`.

**`Knowledge_Edge_Set__c`** (versioned; one row per version of one node's outgoing edges; Sharing: Private)

| Field | Type | Notes |
|---|---|---|
| `Version_Key__c` | Text(100), External Id, unique | `<sha256 hex of source node id>@<Valid_From__c>` |
| `Source_Node_Id__c` | Text(255), indexed | |
| `Edges_Hash__c` | Text(71) | sha256 over the canonical JSON of the node's outgoing edges, sorted as in 4.5 |
| `Edge_Count__c` | Number(6,0) | |
| `Valid_From__c`, `Valid_To__c` | Number(10,0) | Section 6.1 |
| `Closed_At__c` | Date/Time | Set when a commit sets `Valid_To__c`; drives purge |

A node with no outgoing edges still gets an edge set row with `Edge_Count__c = 0`, so "edges unchanged" is always a hash comparison.

**`Knowledge_Edge__c`** (Master-Detail to `Knowledge_Edge_Set__c`; visible when its edge set is)

| Field | Type | Notes |
|---|---|---|
| `Source_Node_Id__c` | Text(255), indexed | Copied from the edge set, so incoming-edge queries need no join on source |
| `Target_Node_Id__c` | Text(255), indexed | Null when unresolved. Text, not a lookup, so a target's new version does not touch its incoming edges |
| `Target_Text__c` | Text(255) | |
| `Type__c` | Picklist `wikilink`, `embed`, `tag`, `relation` | |
| `Relation__c`, `Anchor__c` | Text(255) | |
| `Resolved__c` | Checkbox | |

**`Knowledge_Sync_Setting__mdt`** (one record `Default`, packaged, subscriber-editable): `Purge_After_Days__c` Number (default 30; 0 means purge at the end of each commit), `Keep_Bundles__c` Number (default 10), `Max_Errors__c` Number (default 50), `Dml_Row_Budget__c` Number (default 8000, the DML rows one commit step may use; the platform limit is 10,000), `Max_Chain_Depth__c` Number (default 4, see 7.3).

**Permission set `Knowledge_Sync`**: custom permission `Knowledge_Import`; Apex class access to `KnowledgeBundlesResource`; create/read on `Knowledge_Bundle__c` and `Knowledge_Bundle_Page__c`; no read on node, tag, chunk, edge set or edge objects (the integration user only writes through Apex running in system mode). Read access for end users comes with SB-9's reader permission set.

## 7. Import endpoint and commit (slice 8b)

### 7.1 Bundle identity and ordering (contract clarifications)

These settle QA notes 1 and 2 on PR #7. They change no schema; they define runtime behaviour the SB-7 contract left open, and every runtime must follow them. The Developer copies the three rules into the `importBundlePage` and `getImportStatus` descriptions in `knowledge-services.openapi.yaml` in the 8b PR (an additive description change, allowed as v1.0 per SB-7 section 7).

1. **Import key = (`bundle.id`, `bundle.contentHash`).** Re-compiling the same commit with a newer compiler that changes the output is a new import. Re-sending identical content is a no-op. This refines SB-7 4.4 rule 4.
2. **Ordering key = `bundle.generatedAt`**, ties broken by `bundle.id` in lexical order. "Older" and "newer" in SB-7 4.3 (`BUNDLE_CONFLICT`) and 4.4 rule 5 (supersede) mean this order. Runtimes cannot see commit ancestry, so the producer must not push stale commits; the workflow's stale-commit guard (5.2 step 4) ensures that.
3. `GET /bundles/{bundleId}` returns the status of the newest import with that `bundle.id` (by ordering key).

### 7.2 Page intake: `POST /knowledge/v1/bundles/{bundleId}/pages`

Synchronous Apex, in this order:

1. Caller lacks custom permission `Knowledge_Import`: `403 FORBIDDEN`.
2. Body over 1,500,000 bytes: `413 PAYLOAD_TOO_LARGE` (1.5 times the compiler's 1 MB page default, 4.6). The body is parsed once with `JSON.deserializeUntyped` from `RestRequest.requestBody.toString()`, and the file in step 6 is written from the original `Blob`, so at most one string copy and one parsed tree are on the heap.
3. JSON parse failure, or structural validation failure: `422 INVALID_BUNDLE` with `details[]` of `{path, rule}`. Apex cannot run JSON Schema, so `KnowledgeImportService` checks the rules that matter for safety: `schemaVersion = "1.0"`; required properties present; node id pattern; hash pattern; commit pattern; `page.index <= page.count`; `kind` and edge `type` enums; `resolved` is false exactly when `target` is null; every edge `source` is a node on the same page; `Path__c` and other Text(255) values fit. The full JSON Schema check already ran in CI (4.2), so this is defence in depth, not the only gate.
4. Path `bundleId` (after percent-decoding) differs from `bundle.id` in the body, or does not match the bundle id pattern in 4.5: `400 INVALID_REQUEST`.
5. Lock with `SELECT ... FOR UPDATE` the `Knowledge_Bundle__c` for this import key, creating it in `receiving` if absent. Then:
   - The import key already exists as `committed`, `committing` or `superseded`: return its status, `200`. No change.
   - The import key exists as `failed` (closes QA M7): a re-send means the producer is retrying, for example a re-run of the workflow after a transient error. If the current committed bundle is newer by the ordering key, `409 BUNDLE_CONFLICT`. Otherwise reset the record in the same transaction: `State__c = receiving`, `Pages_Received__c = 0`, the `Nodes_*` counters to 0, `Errors__c` and the `Commit_*` fields cleared, `Attempt__c` + 1. Its staged pages were deleted when it failed and its `Sequence__c` was cleared by the rollback (7.3), so nothing else needs undoing. Then continue with this page as a new receipt. Each retry needs a producer re-send, so a bundle that fails deterministically (for example a stats mismatch) fails again and costs one commit attempt per workflow run, never a loop.
   - The current committed bundle is newer by the ordering key: `409 BUNDLE_CONFLICT`.
   - `page.count` differs from the stored `Page_Count__c`: `409 BUNDLE_CONFLICT`.
   - A page with the same `Page_Key__c` exists: return status, `200`. No change.
6. Store the raw page as a ContentVersion linked to the bundle record (from the request `Blob`); insert `Knowledge_Bundle_Page__c` with its `Content_Document_Id__c`, counts and `Node_Ids__c`; increment `Pages_Received__c`.
7. Any other import in `receiving` that is older by the ordering key becomes `superseded`; its staged pages are deleted (through their ContentDocuments).
8. If `Pages_Received__c = Page_Count__c` and no other import is `committing`: set `committing`, `Commit_Phase__c = check`, and enqueue `KnowledgeImportCommitJob`. If another import is `committing`, leave this one in `receiving` with all pages received; when the running commit ends (committed or failed), its last step starts the newest complete `receiving` import (7.3 step 6). Only one import is ever `committing`, and no job polls with delays.
9. Return `202` with `ImportStatus` (`200` for the no-op cases above).

`GET /knowledge/v1/bundles/{bundleId}` returns `ImportStatus` per 7.1 rule 3. For an unknown bundle it returns `404` with a new error code **`BUNDLE_NOT_FOUND`**: SB-7 4.3 only defines `NODE_NOT_FOUND`, which would mislead. A new enum value that consumers can ignore is a **minor** version under SB-7 section 7, so the 8b PR adds it to the OpenAPI error enum and bumps `knowledge-services.openapi.yaml` `info.version` from `1.0.0` to `1.1.0` (QA m1). The kg-bundle schemas stay `1.0`. A malformed `bundleId` gives `400 INVALID_REQUEST`. Same permission check as intake (`403` without `Knowledge_Import`).

### 7.3 Commit: step runner and jobs

The commit runs as a sequence of bounded **steps**. Each step is one call to `KnowledgeCommitStepRunner.runStep(bundleRecordId)`, which does one unit of work, saves its position on the `Knowledge_Bundle__c` record (`Commit_Phase__c`, `Commit_Page__c`, `Commit_Cursor__c`, `Last_Step_At__c`) and returns whether more work remains. No commit state lives in Queueable member variables, so any execution can resume any commit.

**Budgets per step.** A step stops before the next unit of work would take it over `Dml_Row_Budget__c` DML rows (default 8,000 of the 10,000 limit; cascade-deleted children are counted), 70 % of the async heap, or 80 SOQL queries. A unit is one node in the apply and close-unseen phases and one versioned row (with its children) in rollback. The cost of a unit is known before it is written: a changed node costs 2 node rows (insert, close) + its chunks + its tags + 2 edge-set rows + its edges, all counted from the staged page; the old version's children are never touched. With the compiler's per-node limits (4.6) one node costs at most about 1,115 rows, so every unit fits in one step (closes QA M3).

**Phases.**

1. **Allocate** (at the start of `check`): first finish any interrupted rollback: a non-current bundle whose `Sequence__c` is set and greater than the current sequence, with `State__c` `failed` or `committing` and `Commit_Phase__c = rollback`, is rolled back to the end before anything else. Then re-check ordering (QA m5): if the current committed bundle, or a `receiving` import with all pages received, is newer by the ordering key, this import becomes `superseded` and the newer one is started. Otherwise set `Sequence__c = (max Sequence__c over all bundles, nulls ignored) + 1` (*N*). Because a finished rollback clears its sequence and an unfinished one is completed first, *N* is never already taken (closes QA M1).
2. **check:** cross-page checks before any row is written: the sum of page `Node_Count__c` equals `stats.nodeCount`; the sum of `Edge_Count__c` equals `stats.edgeCount`; no node id appears on two pages (from `Node_Ids__c`). Any failure goes to rollback, which then has nothing to delete.
3. **apply:** for each page in index order and each node in id order after `Commit_Cursor__c`: load the node's row and edge set visible at *N-1* (one query per page for that page's ids, at most 200):
   - No visible row, or `contentHash`, `path`, `title` or `kind` differs (the last three catch case-only renames, QA m4): insert a new `Knowledge_Node__c` (`Valid_From__c = N`) with its chunks and tags, and close the old row (`Valid_To__c = N`, `Closed_At__c = now`).
   - Compute the node's edges hash. No visible edge set, or its `Edges_Hash__c` differs: insert a new `Knowledge_Edge_Set__c` (`Valid_From__c = N`) with its edges, and close the old one.
   - Otherwise nothing is written; the node counts as unchanged.
4. **close_unseen:** build the set of node ids in this bundle from all pages' `Node_Ids__c`. Walk the node rows visible at *N-1* in `Node_Id__c` order (keyset on `Commit_Cursor__c`). Each one whose id is not in the set gets `Valid_To__c = N`, `Closed_At__c` and `Deleted_At__c`, and its visible edge set is closed too.
5. **switch:** in one DML statement set the old current bundle `Is_Current__c = false` and this one `Is_Current__c = true`, `State__c = committed`, `Commit_Phase__c = done`, with the counts. This is the only moment readers move from *N-1* to *N*, and it is the **point of no return**: once this step's transaction commits, the bundle is never rolled back (closes QA N1). If the switch step itself throws, its savepoint undoes it, nothing has switched, and normal rollback applies.
6. **done (cleanup):** delete the staged pages (rows, and files through their ContentDocuments). Start the purge job and, if one is waiting, the newest complete `receiving` import (7.2 step 8), each through the chaining rule below. Then clear `Commit_Phase__c`. Every action is idempotent: deleting pages that are already gone is a no-op, the purge job is only enqueued if none is queued or scheduled, and the waiting import is only started if it is still `receiving` with all pages and no import is `committing`. So a `done` step can be repeated any number of times.

**After the switch, failures are retried, never rolled back.** The runner reads the persisted `State__c` before deciding what a failure means. If the bundle is `committed` (phase `done`), the step's savepoint undoes only that step's partial cleanup DML; the runner then sets `Cleanup_Error__c`, increments `Step_Failures__c` and retries the step as described under "Retries" below. The bundle stays current with all its rows, and `State__c`, `Is_Current__c` and every versioned row are left alone. Readers are never affected by a cleanup failure; at worst staged files stay a little longer or the waiting import starts later.

**Rollback** (any exception or failed check in `check`, `apply`, `close_unseen` or `switch`, that is, only while the bundle is still `committing` and has never been current; the runner catches it, records `Errors__c`, sets `Commit_Phase__c = rollback`). The bundle stays `committing` while rollback runs, so no other commit can start. Rollback steps use the same budgets: delete versioned rows with `Valid_From__c = N` (their children go by cascade and count against the budget), then set `Valid_To__c`, `Closed_At__c` and `Deleted_At__c` back to null on rows with `Valid_To__c = N`. When none of either is left: delete the staged pages, set `State__c = failed`, **clear `Sequence__c`**, and start any waiting import as in step 6. The current bundle never changed, so the previous knowledge stays queryable (REQ-1 AC 3). If a rollback step itself fails, its savepoint undoes that step, the record keeps `Commit_Phase__c = rollback` with an `INTERNAL` error, `Step_Failures__c` goes up by one, and the step is retried as below. Because the bundle is still `committing`, no other commit starts in the meantime (7.2 step 8), so recovery comes from these retries and the watchdog, not from the next commit (QA n2). The allocate step's "finish any interrupted rollback" check stays as defence in depth only, for example after an admin edits a record by hand.

Within one step, `System.Savepoint` and `Database.rollback` undo that step's partial DML before the runner records the error, so each step is all or nothing and the cross-step rollback only has to deal with whole steps.

**Jobs and chain depth (closes QA M5).**

- `KnowledgeImportCommitJob` (Queueable) calls `runStep` once and, if more work remains, enqueues itself. Before enqueuing it reads `System.AsyncInfo.getCurrentQueueableStackDepth()`: below `Max_Chain_Depth__c` it chains (passing `AsyncOptions` with `MaximumQueueableStackDepth` set to the same value); at the limit it schedules `KnowledgeImportResumeJob` once, one minute ahead, which starts a fresh chain. Developer Edition, trial and scratch orgs cap chains at depth 5, so the default of 4 works in every org; production orgs may raise the setting.
- In Apex tests a Queueable cannot enqueue another one, so tests do not rely on chaining. `KnowledgeCommitStepRunner.runToCompletion(bundleRecordId, maxSteps)` calls `runStep` in a loop in the same transaction and is used by the tests, with small `@TestVisible` budgets so that multi-step paths run on small fixtures. The job skips its own re-enqueue when `Test.isRunningTest()`, and one test enqueues it inside `Test.startTest()`/`Test.stopTest()` to cover a single execution. A `@TestVisible` hook throws in a chosen step, so "failure in a later step" (test 11) is reproducible.
- **Retries (rollback and done steps):** when a `rollback` or `done` step fails, the job does not chain straight back into the same failure. It schedules `KnowledgeImportResumeJob` with a back-off of 1, 5 and then 15 minutes for `Step_Failures__c` = 1, 2 and 3. After the third consecutive failure it stops scheduling and leaves the bundle to the watchdog, which keeps retrying once an hour. A transient failure (row lock, enqueue limit) therefore clears within minutes; a persistent one is visible on the record (`Errors__c` or `Cleanup_Error__c`, `Step_Failures__c`, `Last_Step_At__c`) and never loops.
- **Watchdog:** `KnowledgeSyncWatchdogJob` (Schedulable) runs **hourly** (registered by the SB-12 post-install script alongside the daily purge schedule, section 8). It restarts (a) any bundle in `committing` whose `Last_Step_At__c` is more than 15 minutes old and that has no queued or scheduled job, whatever its phase, including a stalled rollback; and (b) any `committed` bundle with `Commit_Phase__c = done` under the same age and no-job conditions. So a lost job or a stuck rollback blocks sync for at most about 75 minutes, not a day (QA n2). Each restart is one fresh chain and resets the back-off.

The runner is `without sharing` and writes only package objects.

### 7.4 State mapping to the contract

| Stored `State__c` | API `state` (SB-7 `ImportStatus`) |
|---|---|
| `receiving`, `committing` | `receiving` (callers see `pagesReceived = pageCount` while committing) |
| `committed`, `failed`, `superseded` | same |

## 8. Purge and retention (closes gap GD-3, proposal for Alex to confirm per pilot)

Proposed policy: **soft delete at commit, hard delete after a retention window.**

- A commit only closes rows (6.1). Closed rows are invisible to every read immediately.
- `KnowledgeImportPurgeJob` hard-deletes versioned rows (`Knowledge_Node__c` with its chunks and tags, `Knowledge_Edge_Set__c` with its edges) whose `Valid_To__c <= current sequence` and whose `Closed_At__c` is more than `Purge_After_Days__c` days ago (default 30). This covers both deleted notes and old versions of edited notes. It uses the same DML row budget as the commit steps (cascade children counted) and re-enqueues itself under the same chain-depth rule (7.3). It never runs while an import is `committing`.
- `Purge_After_Days__c = 0` gives immediate hard delete at the end of every commit, for pilots with strict right-to-delete needs.
- Bundles: keep the newest `Keep_Bundles__c` (default 10) `Knowledge_Bundle__c` records; delete older ones that are not current and not `committing`. Any staged files left on them are deleted through their ContentDocuments.
- It runs after every commit and on a daily schedule. The schedules (daily purge, hourly watchdog) are registered by a post-install script (SB-12), not by the package itself, so install stays free of side effects.
- Purged rows go to the Recycle Bin by default; the job calls `Database.emptyRecycleBin` on them so purge is final.
- The commit watchdog has its own hourly schedule (7.3), so a stalled commit does not wait for the daily purge.
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
| Cross-page check fails, or Apex error during commit | Commit step runner | Rollback; `failed`; sequence cleared; previous bundle stays current | `GET /bundles/{id}` errors; kg-push exits 1; `Knowledge_Bundle__c` record in the org |
| Re-send of a `failed` import | Import endpoint | Reset to `receiving` and retried (7.2 step 5) | `Attempt__c` on the bundle record; kg-push sees the new outcome |
| Commit job lost or chain depth reached | Resume job, hourly watchdog | Fresh chain resumes from the saved phase | `Last_Step_At__c` on the bundle record |
| Rollback step fails | Step runner | Step undone; retried with back-off, then by the hourly watchdog; no other commit starts meanwhile | `Errors__c`, `Step_Failures__c` on the bundle record |
| Cleanup (`done`) fails after the switch | Step runner | Bundle stays `committed` and current with all rows; cleanup retried with back-off, then by the watchdog; never rolled back | `Cleanup_Error__c`, `Step_Failures__c` on the bundle record |
| Node over the per-node edge or tag limit | kg-compiler | Exit 1 before anything is pushed | Workflow run fails with the path |
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
| `paging/` (generated 450 small notes) | Page limits by node count, edge count and bytes; edges on the source's page; `NODE_TOO_LARGE`; `NODE_TOO_MANY_EDGES`, `NODE_TOO_MANY_TAGS`, `TAG_TOO_LONG` |
| Bundle id | `--repo Example-Org/KB-Vault` gives `example-org--kb-vault@<sha>`; the id matches the 4.5 pattern; a 180-character slug passes and a 181-character one exits 1 with `REPO_SLUG_TOO_LONG` |
| Contracts dir | Missing `--contracts-dir` exits 2; a bundle whose `contentHash` is recomputed wrongly fails contracts-check (4.5) |
| Case-only rename | `Foo.md` renamed `foo.md`: same node id and node hash, different bundle hash |
| Determinism | Compile `basic/` twice: identical except `generatedAt`; identical `contentHash` |
| Change detection | `basic/` v1 then v2 (one note added, one edited, one deleted): node hashes and bundle hash change exactly where expected |
| kg-push against a local stub server (Python `http.server`) | Page order, retry on `503` and `429`, no retry on `422`, polling to `committed`, exit codes for `failed`, `superseded`, timeout; token never in output; bundle id percent-encoded in the path |
| `salesforce-auth` with a fake `sf` on `PATH` | With `GITHUB_ACTIONS=true` the first output line is `::add-mask::<token>` and the token appears nowhere else but `$GITHUB_ENV`; without it, `$GITHUB_ENV` is not written |

### 10.2 Apex (slice 8b)

Run with `sf apex run test --test-level RunLocalTests` in a development scratch org (source deployed, so local tests include these); coverage at least 85 % on the import, step runner, job and purge classes. Tests build pages with a test factory (no static resource with real content) and drive commits with `KnowledgeCommitStepRunner.runToCompletion` (7.3), not with chained Queueables:

1. First import: rows at sequence 1, `Is_Current__c`, counts.
2. Same import key again: no-op, `200`, no new rows.
3. Same `bundle.id`, different `contentHash`: new import, new sequence.
4. Add, edit, delete one node each: visible set at the new sequence is right; old versions closed; deleted node has `Deleted_At__c`.
5. Edge-only change (target added): node row unchanged, new edge set at the new sequence, old one closed. Then roll that commit back (injected failure): the old edge set is visible again with its old `Edges_Hash__c`, and the next commit replaces it once (QA M2).
6. Pages out of order and a duplicated page.
7. Each structural rule in 7.2 step 3 returns `422` with the right `details[].rule`.
8. Older bundle after a newer commit: `409`.
9. Newer bundle while an older one is `receiving`: older becomes `superseded`.
10. Stats mismatch at finalise: `failed`, rollback, previous bundle still current and readable through `KnowledgeStore`.
11. Exception injected in a later step (after at least one apply step has written rows): same rollback result; no row with `Valid_From__c = N` remains; `Sequence__c` is null.
    - 11a: **Commit after a failure** (QA M1): after test 10 or 11, a new import commits and takes the next free sequence. Variant (QA n2): the hook throws once in a rollback step; the bundle stays `committing` with `Commit_Phase__c = rollback` and `Step_Failures__c = 1`; the job path schedules `KnowledgeImportResumeJob` (checked through `CronTrigger`); running the next step finishes the rollback, clears `Sequence__c` and resets `Step_Failures__c`; then a new import commits.
    - 11b: **Retry of a failed import** (QA M7): the same pages sent again after a failure reset the import to `receiving`, `Attempt__c = 2`, and it commits; `Pages_Received__c` never exceeds `Page_Count__c`.
    - 11c: **Budgets** (QA M3): with a test row budget of 50, a bundle needing several hundred rows commits correctly over many steps; no step goes over its budget (`Limits.getDmlRows()` checked in the hook). Rollback of that bundle also spans several steps.
    - 11d: **Job path** (QA M5): one `KnowledgeImportCommitJob` execution inside `Test.startTest()`/`Test.stopTest()` runs one step and does not enqueue in tests; at the depth limit (depth stubbed through a `@TestVisible` seam) it schedules `KnowledgeImportResumeJob` instead of chaining.
    - 11e: **Ordering re-check** (QA m5): a commit about to start when a newer complete import exists becomes `superseded`, and the newer one commits.
    - 11f: **Case-only rename** (QA m4): path and title are updated at the new sequence.
    - 11g: **Watchdog**: `KnowledgeSyncWatchdogJob.execute` restarts a `committing` bundle with an old `Last_Step_At__c` and no job, both in `apply` and in `rollback`, and a `committed` bundle with `Commit_Phase__c = done`; it ignores bundles with a recent `Last_Step_At__c`. After three failed rollback steps no resume job is scheduled and only the watchdog restarts it.
    - 11h: **Failure after the switch** (QA N1): the hook throws in the `done` step. The bundle stays `committed` and `Is_Current__c = true`; every row with `Valid_From__c = N` is still there and readable through `KnowledgeStore`; rows closed at *N* stay closed; `Sequence__c` is unchanged; `Cleanup_Error__c` is set and `Errors__c` is not. Running the `done` step again deletes the staged pages, starts a waiting import and clears `Commit_Phase__c`. Running it a third time changes nothing (idempotent).
    - 11i: **Failure in the switch step**: the hook throws inside `switch`; the savepoint leaves the old bundle current, and normal rollback follows (same result as test 11).
12. Purge with `Purge_After_Days__c = 0` and with the default (`Closed_At__c` moved back in test data).
13. Missing `Knowledge_Import` permission: `403` (`System.runAs` a user without the permission set).
14. Chunked node: chunks stored and reassembled by `KnowledgeStore`.
15. Tags: `KnowledgeStore` finds nodes by tag through `Knowledge_Node_Tag__c`, only at the visible sequence (QA M4).
16. Largest page: a 1 MB page (and a 1.5 MB body that is still accepted) is taken in with `Limits.getHeapSize()` under 6 MB; a larger body gives `413` (QA m6).
17. Malformed path `bundleId`: `400 INVALID_REQUEST`; unknown valid one on `GET`: `404 BUNDLE_NOT_FOUND`.
18. Staged files are deleted through `ContentDocument` on commit, supersede and failure (QA m7).

### 10.3 End to end (slice 8c)

Script `packages/salesforce/scripts/e2e-sync.sh`, run by the Developer against a fresh scratch org (needs the Dev Hub from section 12):

1. Create a scratch org; install the package version or push source; assign `Knowledge_Sync` to the running user.
2. Compile `tools/kg-compiler/tests/fixtures/basic` and push with kg-push. Expect `committed`.
3. Query with `sf data query` (SB-9 may not exist yet): current nodes, their tags and frontmatter, and edges. Compare with the fixture's expected JSON.
4. Compile the v2 fixture (add, edit, delete) and push. Query again; expect exactly the changes.
5. Push a deliberately broken page set (stats mismatch). Expect kg-push exit 1, state `failed`, and step 3's query still returning the v2 data.
5a. Compile and push a v3 fixture (one more edit). Expect `committed`: a failure does not block later syncs (QA M1).
5b. Push `paging/` (several pages, more steps than the default chain depth) and expect `committed`, which shows the resume path works in a scratch org (QA M5).
6. The output of all steps is the PR's test evidence.

## 11. Acceptance-criteria mapping

| # | Acceptance criterion (SB-8 story / REQ-1) | Met by | Verified by |
|---|---|---|---|
| 1 | Given a sample vault with notes and wikilinks, a sync run makes notes, links and metadata queryable in a scratch org | Compiler (4), push (5), storage and import (6, 7) | 10.1 `basic/`; 10.2 test 1; 10.3 steps 2 and 3 |
| 2 | Adds, edits and deletes in the vault are reflected on the next run | Content hash, path, title and kind; versioned node rows and edge sets; close of unseen nodes (7.3) | 10.1 change detection and case-only rename; 10.2 tests 4, 5 and 11f; 10.3 steps 4 and 5a |
| 3 | An invalid bundle is rejected, prior knowledge stays queryable and the failure is reported | Compiler self-validation (4.2), intake validation (7.2), atomic switch, point of no return and rollback (6.1, 7.3), retry (7.2 step 5), error reporting (9) | 10.1 bad fixtures; 10.2 tests 7, 10, 11, 11a, 11b, 11h and 11i; 10.3 steps 5 and 5a |
| 4 | Uses the sync approach approved in ADR-001 | Option A: compile in CI, push through the package's own import endpoint; bundle is SB-7 kg-bundle v1 | This spec's header and sections 4, 5 and 7; QA review |
| 5 | REQ-1: notes, links and metadata available in a queryable form | Node, chunk, tag, edge set and edge objects (6.2) read through `KnowledgeStore` | 10.2 test 15; 10.3 step 3 |

## 12. Dependencies and open points

**Alex account actions** (already listed in ADR-001 Consequences; none blocks slices 8a or 8b):

- Enable a Dev Hub and register the package namespace (also needed by SB-12).
- For 8c and for real vaults: a connected app with a JWT certificate and an integration user per target org, with the secrets stored in the vault repository's GitHub Actions secrets.
- Confirm which repository holds the vault. It must not be this public repository if it holds client content.

**Open points (do not block build):**

- AGENTS.md ownership rows for `tools/`, `templates/` and `packages/` (TA Inbox Blocker of 2026-10-15, decision b).
- Gap GD-3: Alex confirms the purge default (30 days) or a per-pilot value.
- Contract clarifications in 7.1 and the `BUNDLE_NOT_FOUND` code (services contract 1.1) are written into the OpenAPI document by the 8b PR, and the bundle id and `contentHash` rules (4.5) into the kg-bundle schema descriptions by the 8a PR. If Alex prefers them in the SB-7 spec text as well, the TA adds an errata section to `SB-7.md` after PR #7 merges.

## 13. Definition of done for the Developer PRs

- Files in section 3 for the slice exist; tests in section 10 for the slice pass, with commands and output in the PR.
- 8a: no Salesforce code outside `kg_push/auth_salesforce.py`; contracts-check passes on generated output; `tools/contracts-check` gains `pyproject.toml` and the `contentHash` check (4.2, 4.5); `contracts/` changes are limited to the `bundle.id` and `bundle.contentHash` descriptions.
- 8b: no change to `contracts/` other than the description additions in 7.1, the `BUNDLE_NOT_FOUND` enum value and the `info.version` bump to `1.1.0` (7.2). The 8b PR also adds its entries (the import resource probe and its test classes) to SB-12's `expected-components.json`. It also extends SB-12's `scripts/post-install.sh` (SB-12 5.2 lists only the purge job) so that it schedules `KnowledgeSyncWatchdogJob` hourly as well, idempotently.
- No client content, credentials, org IDs or instance URLs anywhere, including fixtures and logs.
- `python build.py` is unaffected (no changes to `research/`, `template.html` or `build.py`).
- Each PR links SB-8 and this spec. The story's PR Link points at the latest slice PR.

## 14. Changes after QA review on PR #11 (2026-10-20)

| QA item | Change | Where |
|---|---|---|
| M1 failed commit wedges `Sequence__c` | Sequence allocated as max + 1 after finishing any interrupted rollback; cleared when rollback completes | 6.2, 7.3 allocate and rollback; tests 11, 11a; e2e 5a |
| M2 stale edge hash | Edge hash moved to the versioned `Knowledge_Edge_Set__c`; edges are its children | 6.1, 6.2, 7.3 apply; test 5 |
| M3 10,000 DML rows | Step runner with a DML row budget per step; per-node edge and tag limits in the compiler; close-unseen and rollback are budgeted phases | 4.6, 7.3; test 11c |
| M4 `Tags__c` LIKE | Child `Knowledge_Node_Tag__c` with an indexed Text(255) tag; `Tags__c` kept for output only | 6.2; test 15 |
| M5 Queueable chain in tests and depth 5 | State on the record; synchronous `runToCompletion` for tests; chain-depth limit with a Schedulable resume and a watchdog | 7.3; tests 11d, 11g; e2e 5b |
| M6 contracts-check and schemas missing in vault repos | contracts-check made pip-installable; workflow checks out this repo at the pinned tag and passes `--contracts-dir` | 4.1, 4.2, 5.2 |
| M7 retry of a failed import | Defined reset to `receiving` with `Attempt__c` | 7.2 step 5; test 11b |
| m1 `BUNDLE_NOT_FOUND` version | Services contract bumped to 1.1 | 7.2 |
| m2 `contentHash` not in contracts | Rule written into the schema description and checked by contracts-check | 4.5, 13 |
| m3 bundle id slug | Defined, with pattern and encoding | 4.5, 7.2 step 4 |
| m4 case-only rename | Path, title and kind in change detection and in the bundle hash | 4.5, 7.3 apply; test 11f |
| m5 concurrency | One concurrency group per target; dispatch only on the default branch; ordering re-checked at commit start | 5.2, 7.3 allocate; test 11e |
| m6 intake heap | Page default 1 MB, body limit 1.5 MB, single parse, file from the Blob | 4.1, 4.6, 7.2 step 2; test 16 |
| m7 ContentVersion delete | Delete through ContentDocument | 6.2, 7.3, 8; test 18 |
| m8 token masking | `::add-mask::` before writing `$GITHUB_ENV` | 5.1 rule 6; 10.1 |
| Nits | Section reference 5.1; `System.Savepoint`; branch names for C-data and ip-boundary; GD-5 departure from ADR-001 option A explained | header, 3, 5.3, 7.3 |

## 15. Changes after QA re-review on PR #11 (2026-10-21)

| QA item | Change | Where |
|---|---|---|
| N1 rollback can run after `switch` | `switch` is the point of no return and also sets `Commit_Phase__c = done`. Rollback only runs while the bundle is `committing`. A `done` failure is undone by its savepoint, recorded in the new `Cleanup_Error__c`, and retried; every cleanup action is idempotent. The bundle stays current with its rows | 6.2, 7.3 phases 5 and 6, rollback, retries; 9; tests 11h and 11i |
| n1 `Bundle_Key__c` / `Page_Key__c` over Text(255) | Slug capped at 180 characters (`{0,179}`), so the keys are at most 238 and 245 characters; the compiler rejects a longer slug with `REPO_SLUG_TOO_LONG` | 4.5; 10.1 bundle id test |
| n2 interrupted-rollback path unreachable | Removed the claim that the next commit finishes a stalled rollback (allocate's check stays as defence in depth only). Failed `rollback` and `done` steps are retried with a 1, 5 and 15 minute back-off through `KnowledgeImportResumeJob`, tracked in the new `Step_Failures__c`. A new hourly `KnowledgeSyncWatchdogJob` replaces the daily watchdog, so the worst-case block is about 75 minutes | 6.2, 7.3 rollback, retries and watchdog; 8; 9; tests 11a and 11g |
