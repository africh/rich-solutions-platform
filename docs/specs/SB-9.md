# SB-9: Knowledge service core and REST endpoints

- **Story:** SB-9 (Notion Sprint Board, shown as RSP-9) "Knowledge service core and REST endpoints"
- **Requirements:** REQ-2 Knowledge-backed service calls via REST endpoints (Must, Approved). Also respects REQ-8, runtime-neutral contracts (Should, Approved), and REQ-6, the IP line (Must, Approved).
- **ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) (Approved 2026-10-15), Part 1: one service core, exposed three ways; layers Contract, Storage, Service, Exposure. ADR-002 (Approved) does not affect the package.
- **Builds on (unmerged at the time of writing; read them on their branches):**
  - [SB-7 spec](SB-7.md): kg-bundle v1, knowledge services v1, operations, result shapes and the error envelope. PR #7, branch `agent/technical-architect/SB-7`.
  - [SB-8 spec](SB-8.md): storage objects, the bundle-sequence visibility rule and `KnowledgeStore`. PR #11, branch `agent/technical-architect/SB-8`.
  - [SB-12 spec](SB-12.md): the SFDX project, layer folders, `expected-components.json` and the verify probes. PR #12, branch `agent/technical-architect/SB-12`.
  - [ip-boundary](../design/ip-boundary.md): base and extension package rules. PR #8, branch `agent/technical-architect/SB-13`.
  - Phase C application architecture, `docs/togaf/C-application.md` (PR #13, branch `agent/enterprise-architect/SB-15-application`): components AC-10, AC-12, AC-14, AC-15, AC-17 and AC-20; interface rules in its section 5.2; gap GA-1 (this spec fixes the extension hook shape).
- **Principles:** AP-1 Runtime-neutral contracts, AP-2 One service core, SP-1 Public-repo hygiene ([principles.md](../togaf/principles.md))
- **Spec author:** Technical Architect, 2026-10-21
- **Builder:** Developer

## 1. Goal

Build the **knowledge service core**: the one place where the four read operations of the SB-7 services contract (`getNode`, `searchNodes`, `getNeighbors`, `getContext`) are implemented. Then expose them as **REST endpoints** that match `contracts/services/v1/knowledge-services.openapi.yaml`.

SB-10 (global Apex API) and SB-11 (Agentforce actions) are thin adapters over the same core and the same Contract-layer types, so all three channels give the same answer (C-application 5.2 rule 2). This story also fixes the **extension hook** that client extension packages use (C-application GA-1, AC-15).

Out of scope:

- The import endpoints (SB-8).
- The global Apex entry point (SB-10) and the invocable actions (SB-11).
- Semantic or vector search (ADR-001 consequences).
- Per-note access control (REQ-15 is still Needs Alex; see section 8).
- Any outbound call (C-application 5.2 rule 5).

## 2. Build order and slices

| Slice | Content | Depends on | Can start |
|---|---|---|---|
| 9a | Contract-layer types (section 4), `KnowledgeException`, `KnowledgeResultHook` and resolver (section 5), service core `getNode` and `getNeighbors`, `KnowledgeStore` read methods, REST resource `/nodes/*`, `Knowledge_Reader` permission set, experiment E1 (section 7.1) | SB-7 build PR (contracts), SB-8 slice 8b (storage and `KnowledgeStore`), SB-12 slice 12a | After 8b merges |
| 9b | `searchNodes` and `getContext` in the core; REST resources `/search` and `/context` | 9a | After 9a merges |
| 9c | End-to-end script against a scratch org, response validation against the OpenAPI document, `expected-components.json` entries | 9b, SB-8 slice 8c | After 9b merges |

Each slice is one Developer PR linked to SB-9.

## 3. Components and files

All paths are under `packages/salesforce/force-app/main/` (SB-12 3.2 layer folders) unless they start with `tools/`.

```
contract/classes/
  KnowledgeRequests.cls          global DTOs: GetNodeRequest, SearchRequest, NeighborsRequest, ContextRequest (4.1)
  KnowledgeResults.cls           global DTOs: BundleRef, NodeSummary, NodeDetail, NodeResult, SearchItem,
                                 SearchResult, Edge, NeighborEdge, NeighborResult, Passage, ContextResult (4.2)
  KnowledgeException.cls         global exception carrying the SB-7 error envelope fields (4.3)
  KnowledgeResultHook.cls        global virtual class: the extension hook (section 5)
storage/classes/
  KnowledgeStore.cls             from SB-8; 9a adds the read methods in 6.1
service/classes/
  KnowledgeService.cls           public interface: the four read operations over the Contract-layer DTOs
  KnowledgeServiceCore.cls       public implementation of KnowledgeService (section 6)
  KnowledgeServiceResolver.cls   public; returns the core with the configured hook attached (5.2)
  KnowledgeRequestValidator.cls  input rules from the OpenAPI document (6.6)
  KnowledgeText.cls              tokenizing, stop words, snippet and passage selection (6.4, 6.5)
  KnowledgeCursor.cls            opaque search cursor (6.3)
exposure/classes/
  KnowledgeNodesResource.cls     @RestResource(urlMapping='/knowledge/v1/nodes/*'): getNode, getNeighbors
  KnowledgeSearchResource.cls    @RestResource(urlMapping='/knowledge/v1/search'): searchNodes
  KnowledgeContextResource.cls   @RestResource(urlMapping='/knowledge/v1/context'): getContext
  KnowledgeRestSupport.cls       request parsing, JSON writing with the contract's property names, error envelope (7.3)
storage/objects/Knowledge_Service_Setting__mdt/ ...   hook configuration (5.2)
storage/customPermissions/Knowledge_Read.customPermission-meta.xml
storage/permissionsets/Knowledge_Reader.permissionset-meta.xml
tests (each next to its class):  *Test.cls, plus KnowledgeTestData.cls (test factory that writes committed
                                 bundles through the SB-8 step runner, synthetic "Example Corp" content)
packages/salesforce/scripts/e2e-read.sh                9c (section 9.3)
tools/contracts-check/contracts_check/responses.py     9c: validates saved responses against the OpenAPI schemas
tools/package-check/expected-components.json           9c adds the SB-9 entries (9.4)
```

Layer rule (SB-12 3.2): Contract references nothing else in the package. Storage references Contract only. Service references Contract and Storage. Exposure references Contract and Service, never Storage directly (C-application 3.2). `package-check static` already enforces this.

## 4. Contract-layer types (Apex mirror of the SB-7 services contract)

The Contract layer is the only `global` surface (ip-boundary 3.1 rule 4). The rules for these types:

- They mirror the OpenAPI component schemas one to one. They add no field that the contract lacks (C-application 5.2 rule 1).
- They are plain data classes: `global` fields, a `global` no-argument constructor, and no logic apart from defaults.
- A `global` member cannot be removed or retyped once a version is released. Adding a field when the contract gets a minor version (SB-7 section 7) is allowed.

Apex reserved words cannot be field names. Where the contract property is a reserved word or would be confusing in Apex, the Apex field gets a different name and the JSON writer in 7.3 maps it back. The table lists every such case. Any other field has exactly the contract's name.

| Contract property | Apex field | Why |
|---|---|---|
| `limit` | `maxItems` | `limit` is reserved in Apex |
| `type` (Edge) | `edgeType` | Avoids confusion with `System.Type` |
| `types` (getNeighbors) | `edgeTypes` | Same |
| `commit` (BundleRef) | `commitSha` | `commit` is reserved in Apex |

### 4.1 Requests (`KnowledgeRequests`)

| Class | Fields (defaults as in SB-7 4.1) |
|---|---|
| `GetNodeRequest` | `String nodeId`; `Boolean includeBody = true` |
| `SearchRequest` | `String query`; `List<String> tags = new List<String>()`; `Integer maxItems = 10`; `String cursor` |
| `NeighborsRequest` | `String nodeId`; `String direction = 'both'`; `List<String> edgeTypes = new List<String>()`; `Integer depth = 1`; `Integer maxItems = 25` |
| `ContextRequest` | `String question`; `Integer maxNodes = 5`; `Integer maxChars = 20000` |

### 4.2 Results (`KnowledgeResults`)

| Class | Fields |
|---|---|
| `BundleRef` | `String id`; `String commitSha` (JSON `commit`) |
| `NodeSummary` | `String id`, `title`, `path`, `kind`; `List<String> tags`; `String snippet` (null when not set) |
| `NodeDetail` | extends `NodeSummary`: `String body` (null when `includeBody = false`); `Map<String, Object> frontmatter`; `List<String> aliases`; `Datetime updatedAt` |
| `NodeResult` | `NodeDetail node`; `BundleRef bundle` |
| `SearchItem` | extends `NodeSummary`: `Decimal score` (always null in the MVP, see 6.3) |
| `SearchResult` | `List<SearchItem> items`; `String nextCursor`; `BundleRef bundle` |
| `Edge` | `String source`, `target`, `targetText`, `edgeType`, `relation`, `anchor`; `Boolean resolved` |
| `NeighborEdge` | `Edge edge`; `NodeSummary node` (null when the edge is unresolved) |
| `NeighborResult` | `NodeSummary node`; `List<NeighborEdge> edges`; `Boolean truncated` |
| `Passage` | `String nodeId`, `title`, `path`, `text`, `citation` |
| `ContextResult` | `String question`; `List<Passage> passages`; `Boolean truncated`; `BundleRef bundle` |

`NodeSummary` is a `global virtual class` so that `NodeDetail` and `SearchItem` can extend it.

**When no bundle has ever been committed**, `bundle` is null in `SearchResult` and `ContextResult` (empty results), and `getNode` and `getNeighbors` return `NODE_NOT_FOUND`. SB-7 4.2 does not say whether `bundle` may be null. Because the SB-7 contract has not been built yet, the SB-7 build PR declares `bundle` nullable in `SearchResult` and `ContextResult` (section 11, open point 1). If that PR has already merged without it, the 9b PR adds it as a 1.x clarification.

### 4.3 `KnowledgeException`

`global class KnowledgeException extends Exception` with `global` read accessors:

- `String getCode()`: one of the SB-7 4.3 codes.
- `Integer getHttpStatus()`: derived from the code by the fixed SB-7 table, never set separately.
- `Boolean isRetryable()`.
- `List<Map<String, String>> getDetails()`: items of `{path, rule}`.
- `String getMessage()`: the standard message.

The code is set by `global` static factories (`invalidRequest(details)`, `notFound(nodeId)`, `forbidden()`, `internal()`), so no other code can be made up. SB-10 throws this same exception to subscriber Apex. That is REQ-3's "documented, catchable exception", and defining it here means REST and Apex share one error model.

## 5. Extension hook (fixes C-application GA-1 and AC-15)

### 5.1 Shape

C-application 6.3 allows either a full `KnowledgeService` override or "a narrower hook the SB-9 spec defines". This spec picks the **narrower hook**: an extension can post-process results but cannot replace the core.

A full override would let an extension skip the permission check (6.7), the bundle-consistent read (6.2) and the error model. The REST, Apex and Agentforce channels would then no longer be guaranteed to agree, and that guarantee is what REQ-3's parity criterion and C-application 5.2 rule 2 depend on. The narrower hook keeps all of that in base code while still letting a client re-rank, filter, annotate or redact results, which covers the extension cases we know about.

```apex
global virtual class KnowledgeResultHook {
    global virtual void afterGetNode(KnowledgeRequests.GetNodeRequest request, KnowledgeResults.NodeResult result) {}
    global virtual void afterSearch(KnowledgeRequests.SearchRequest request, KnowledgeResults.SearchResult result) {}
    global virtual void afterNeighbors(KnowledgeRequests.NeighborsRequest request, KnowledgeResults.NeighborResult result) {}
    global virtual void afterContext(KnowledgeRequests.ContextRequest request, KnowledgeResults.ContextResult result) {}
}
```

- It is a `global virtual class`, not an interface, so a later minor version can add a method with a no-op default without breaking extensions that already compiled against it.
- An extension subclasses it in its own namespace and changes the result in place. It may remove items or passages, reorder them, change `snippet` and `text`, or set `score`.
- It must not throw for "no result". To hide a node from `getNode` it throws `KnowledgeException.notFound(nodeId)`, which is the only exception the core passes through unchanged. Any other exception from a hook becomes `INTERNAL` (6.8).
- The core calls the hook after building the result and before returning it to any channel. All three channels therefore see the hooked result.
- Base code never names an extension type (ip-boundary 3.1 rule 2).
- `KnowledgeService` (Service layer) stays `public`. It is an internal seam for tests and for SB-10 and SB-11, not part of the extension surface. This narrows C-application AC-10, which lists `KnowledgeService` among the `global` types. The Technical Architect will comment on PR #13 so the Enterprise Architect can align AC-10 and AC-15.

### 5.2 Configuration and resolution

`Knowledge_Service_Setting__mdt` has one packaged record, `Default`, which the subscriber can edit:

| Field | Type | Default | Notes |
|---|---|---|---|
| `Result_Hook_Class__c` | Text(255) | blank | `<namespace>.<ClassName>`, or `<ClassName>` with no namespace. Blank means no hook |
| `Search_Candidate_Limit__c` | Number(3,0) | 200 | Section 6.3 |
| `Context_Candidate_Limit__c` | Number(3,0) | 50 | Section 6.5 |

`KnowledgeServiceResolver.get()` reads the record once per transaction. If the hook field is blank, it returns the core with no hook. Otherwise it calls `Type.forName(namespace, name)` and `newInstance()`, and checks with `instanceof` that the object is a `KnowledgeResultHook`.

If the class does not exist, cannot be constructed or is not a subclass, every read fails with `INTERNAL` (`details: [{path: "Knowledge_Service_Setting__mdt.Result_Hook_Class__c", rule: "hook.invalid"}]`). The resolver **fails closed** because the hook may be a client's redaction filter, and skipping it silently could expose content the client meant to hide. To remove an extension, the admin clears the field: no code change is needed (C-application 6.3).

## 6. Service core (`KnowledgeServiceCore`)

`public with sharing class KnowledgeServiceCore implements KnowledgeService`. Every operation follows the same steps:

1. Run the permission check (6.7).
2. Validate the request (6.6).
3. Read the current bundle **once**: `KnowledgeStore.currentBundle()` returns `{sequence, bundleId, commit}` or null.
4. Make every query at that sequence *S*.
5. Build the result.
6. Call the hook (section 5).
7. Return the result.

Because step 3 runs once, a commit that switches during a request never produces a result that mixes two bundles (SB-8 6.1, C-application 5.2 rule 4).

### 6.1 `KnowledgeStore` read methods (added in 9a)

SB-8 makes `KnowledgeStore` the only class that builds the visibility filter (`Valid_From__c <= S AND (Valid_To__c = null OR Valid_To__c > S)`). 9a adds the following methods. All of them are `inherited sharing`, query `WITH SYSTEM_MODE` (see 6.7 for why) and take *S* explicitly:

| Method | Returns | Queries |
|---|---|---|
| `currentBundle()` | sequence, `Bundle_Id__c`, `Source_Commit__c` of the `Is_Current__c` bundle, or null | 1 |
| `nodesById(S, Set<String> nodeIds, Boolean withBody)` | `Map<String, Knowledge_Node__c>`, visible versions only | 1 |
| `chunks(Set<Id> nodeRecordIds)` | chunks in `Chunk_Index__c` order, grouped by node record | 1 |
| `chunk(Id nodeRecordId, Integer index)` | one chunk | 1 |
| `nodeIdsWithAllTags(S, Set<String> nodeIds, List<String> tags)` | the subset of `nodeIds` whose visible version has every tag (semi-join on `Knowledge_Node_Tag__c`, one semi-join per tag, at most 10 tags) | 1 |
| `outEdges(S, Set<String> sourceIds, Set<String> types)` | edges of the visible edge sets of those nodes | 1 |
| `inEdges(S, Set<String> targetIds, Set<String> types)` | edges whose `Target_Node_Id__c` is in the set and whose parent edge set is visible (filter on `Edge_Set__r.Valid_From__c` and `Edge_Set__r.Valid_To__c`) | 1 |
| `searchCandidates(S, String soslTerm, Integer maxIds)` | ordered list of `{nodeId, chunkIndex or null}` for visible nodes (6.3) | 1 SOSL plus 1 SOQL |

Every method selects only the fields it needs. `Body__c` and chunk text are loaded only where a result returns them.

### 6.2 `getNode`

1. Validate: `nodeId` matches `^[a-z0-9][a-z0-9_/-]{0,254}$` (SB-7 3.1), otherwise `400 INVALID_REQUEST` with rule `pattern`.
2. If there is no current bundle, or no visible row: `404 NODE_NOT_FOUND`. A deleted node (closed at or before *S*) is not visible, so it is also 404 (SB-7 4.4 rule 3).
3. Build `NodeDetail`:
   - `title` comes from `Title_Full__c`.
   - `tags`, `aliases` and `frontmatter` are parsed from their JSON fields.
   - `updatedAt` comes from `Updated_At__c`.
   - `body` is `Body__c` plus every chunk in index order when `Chunk_Count__c > 0` (SB-7 3.3). It is omitted when `includeBody = false`.
   - `snippet` is null.
4. The heap is bounded because the compiler rejects any node over about 0.9 MB (`NODE_TOO_LARGE`, SB-8 4.6). The largest body plus its JSON copy therefore stays under about 4 MB of the 6 MB synchronous heap. Test 9 covers it.

### 6.3 `searchNodes`

**Input rules:**

- `query`: 1 to 500 characters after trimming.
- `tags`: 0 to 10 items, each 1 to 255 characters. They are lower-cased before matching, as the compiler lower-cases them.
- `limit`: 1 to 50.
- `cursor`: optional.

**Building the search term** (`KnowledgeText.toSoslTerm`):

1. Split the query on whitespace.
2. In each token, escape the SOSL reserved characters `? & | ! { } [ ] ( ) ^ ~ * : \ " ' + -` with a backslash.
3. Drop tokens that are empty after escaping, or shorter than 2 characters.
4. Join the remaining tokens with ` AND `, and quote any token that contains a space.

If no token is left, the result is empty `items` with `nextCursor = null`, not an error (a query of only punctuation is valid input that matches nothing).

**Candidates:**

- `KnowledgeStore.searchCandidates` runs one SOSL query: `FIND :term IN ALL FIELDS RETURNING Knowledge_Node__c(Id, Node_Id__c WHERE <visibility at S>), Knowledge_Node_Chunk__c(Id, Node__c, Chunk_Index__c)`. Each object returns at most `Search_Candidate_Limit__c` rows (default 200).
- Chunk hits are mapped to their parent node record. A second SOQL query keeps only parents that are visible at *S*, because experiment E2 (7.1) decides whether SOSL `WHERE` can filter through the relationship. The SOQL step is used either way, so correctness does not depend on E2.
- Hits are merged in SOSL order: node rows first, then chunk rows. Duplicates are dropped by `Node_Id__c`, keeping the first position and remembering which chunk matched.
- If the AND search returns no candidates and there was more than one token, the core runs the search once more with ` OR `. That makes at most 2 SOSL queries per call; the platform limit is 20.
- If `tags` is not empty, `nodeIdsWithAllTags` filters the candidates (AND across tags).

**Order and score:**

- Results keep SOSL relevance order. The platform does not expose SOSL scores, so `score` is always null in the MVP. The contract marks it optional.
- Ties cannot happen, because SOSL order is total within one call.

**Page and cursor:**

- `items` is the candidate list from `offset` to `offset + limit`.
- `KnowledgeCursor` is base64url of the canonical JSON `{"v":1,"s":S,"o":nextOffset,"h":<first 16 hex of sha256(query + "\n" + sorted tags)>}`.
- `nextCursor` is null when no candidates remain, or when the candidate limit has been reached. In that case the search does not go past 200 results, and the next page simply does not exist.
- A cursor that does not decode, or whose `h` does not match the request, gives `400 INVALID_REQUEST`, rule `cursor.invalid`.
- A cursor whose `s` is not the current sequence gives `400 INVALID_REQUEST`, rule `cursor.stale`. The client restarts the search. Paging never mixes two bundles.

**Snippet:** `KnowledgeText.snippet(text, tokens)` returns up to 300 characters of plain text around the first case-insensitive match of any token. The text is the matched chunk when the hit came from a chunk, otherwise `Body__c`.

- Plain text means the result after removing `[[`, `]]`, `![[`, leading `#` characters, `*`, `_` and backticks, and collapsing whitespace.
- The window starts at the nearest word boundary at or before 100 characters before the match.
- If no token occurs in the text (the hit was on the title or tags), the snippet is the first 300 characters.

Only the bodies of the returned page (at most 50 rows, chunk 0 or one chunk each, about 5 MB in the worst case) are loaded. The core reads them in groups of 10 and frees each group's text after building its snippets, so the heap stays under 6 MB. Test 15 uses 50 nodes of 100,000 characters each.

**SOSL index lag:** new rows become searchable a short time after a commit (the platform indexes asynchronously). For a short time, a fresh commit can return fewer search results than `getNode` can find. This is documented in the REST README. It does not break the contract: the result is still consistent with bundle *S*, it is just incomplete. Apex tests use `Test.setFixedSearchResults`.

### 6.4 `getNeighbors`

**Input rules:**

- `nodeId`: the 6.2 pattern.
- `direction`: `out`, `in` or `both`.
- `types`: items from `wikilink`, `embed`, `tag`, `relation`. Empty means all.
- `depth`: 1 or 2.
- `limit`: 1 to 100 (this caps the number of edges).

**Steps:**

1. Load the start node. If it is not visible: `404 NODE_NOT_FOUND`.
2. For depth 1, `out` reads `outEdges({id})`, `in` reads `inEdges({id})`, and `both` reads both.
3. For depth 2, the frontier is the set of resolved neighbour node ids from depth 1, excluding the start node. The same calls run again over the whole frontier at once, so each extra level costs a constant number of queries, not one per node. Edges already returned are not repeated. In SOQL terms an edge is identified by its edge record id.
4. Collect the node ids at the other end of each edge (`target` for out-edges, `source` for in-edges). Load their summaries with one `nodesById(S, ids, false)` call.
   - An unresolved edge has `node = null`.
   - A resolved edge whose target is not visible at *S* also gets `node = null`. This should not happen, because the compiler only resolves links to nodes in the same bundle, but it is handled.
5. Order the edges by depth, then by the SB-8 4.5 edge order `(source, type, relation or "", target or "", anchor or "", targetText)`.
6. Cut the list to `limit`. `truncated` is true when more edges existed at any depth.

The cost is at most 7 SOQL queries for depth 2 and `both`. Each edge query is capped at `limit + 1` rows per call. The `+1` is how the core knows to set `truncated`.

### 6.5 `getContext`

This builds grounding passages for an agent. It is deterministic and lexical, and it makes no model call: the package makes no outbound calls (C-application 5.2 rule 5), and generating the answer is the org's own Agentforce model's job (IF-9).

**Input rules:**

- `question`: 1 to 2,000 characters after trimming.
- `maxNodes`: 1 to 10.
- `maxChars`: 1,000 to 60,000.

**Steps:**

1. **Keywords:** `KnowledgeText.keywords(question)`:
   - Lower-case the question and split it on anything that is not a letter or a digit.
   - Drop tokens shorter than 3 characters, and tokens in the built-in English stop-word list (a constant in `KnowledgeText`, about 150 words, stored in code with no data file).
   - Remove duplicates, keeping the first 10 tokens in question order.
   - If no keyword is left: empty `passages`, `truncated = false`.
2. **Candidates:** `searchCandidates` with the keywords joined by ` OR `, capped at `Context_Candidate_Limit__c` (default 50).
3. **Re-rank:** load the candidates' summaries without bodies. Score each candidate as 3 × (keywords in the title) + 2 × (keywords in tags or aliases) + 1 if it was a SOSL hit. Order by score, then by SOSL position. Take the top `maxNodes`.
4. **Passages:** for each chosen node, load the matched chunk if the SOSL hit was a chunk, otherwise `Body__c` (chunk 0). This is at most one text of up to 100,000 characters per node, so at most about 1 M characters for 10 nodes. Then:
   - Split the text into paragraphs on blank lines.
   - Score each paragraph by keyword occurrences.
   - Keep the best paragraphs in their original order until the node's budget is used. The budget is `floor(maxChars / number of chosen nodes)`. Any budget left by short nodes goes to the following nodes.
   - A paragraph longer than the remaining budget is cut at a word boundary.
   - `text` is the kept paragraphs joined by a blank line. They are plain Markdown, and wikilinks are kept as written so an agent can quote them.
5. **Citation:** each passage gets `citation = <path>@<commit>` (SB-7 4.2), where the commit is the current bundle's `Source_Commit__c`.
6. **Truncation:** `truncated` is true when any paragraph was cut, any scored paragraph was left out for lack of budget, or there were more candidates with a score above 0 than `maxNodes`.
7. **No match:** if no candidate has a score above 0, and no candidate came from SOSL, `passages` is empty. SB-11 turns an empty `passages` into its explicit no-answer result (REQ-4 AC 2). The core never makes up text.

The total length of `passages[].text` is never more than `maxChars`. Test 18 checks this.

### 6.6 Validation (`KnowledgeRequestValidator`)

One validator for all channels, so REST and Apex reject the same inputs with the same `details` (C-application 5.2 rule 2).

- Each rule failure adds `{path, rule}`. `path` is a JSON pointer into the request, for example `/limit`. `rule` is the JSON Schema keyword that failed: `required`, `minLength`, `maxLength`, `minimum`, `maximum`, `enum`, `pattern` or `maxItems`, or one of the named rules `cursor.invalid`, `cursor.stale` or `additionalProperties`.
- All failures are collected, then thrown together as `400 INVALID_REQUEST`.
- Numbers outside their range are rejected, never clamped, because the contract's `minimum` and `maximum` are hard limits.

### 6.7 Access (REQ-2 AC 2)

- **Authentication** is done by the platform. A request with no valid session or OAuth token never reaches Apex. It gets the platform's `401` with the platform's JSON body, not the SB-7 envelope. SB-7 4.3 says `UNAUTHORIZED` is "runtime decides how", so this is compliant, and it returns no knowledge content. The REST README documents it.
- **Authorization (MVP, package level):** the core's first step is `FeatureManagement.checkPermission('Knowledge_Read')`. If it fails, or the running user's `UserType` is `Guest`, the core throws `403 FORBIDDEN` with no content. The guest check catches a site profile that was given class access by mistake.
- **Permission set `Knowledge_Reader`:** the custom permission `Knowledge_Read`, plus Apex class access to the three REST resource classes. SB-10 and SB-11 add their classes to it.
  - It deliberately grants **no object permissions** on the knowledge objects. `KnowledgeStore` reads `WITH SYSTEM_MODE` after the permission check. A reader therefore cannot use the standard REST or SOQL API to see closed or deleted versions that are waiting for purge (SB-8 section 8). Only the service, which applies the visibility rule, can read the objects.
  - `Knowledge_Admin` gets Read on the knowledge objects for support work.
- **Per-note access** (REQ-15, Needs Alex) is not in the MVP. If Alex approves it, a later story adds an optional `access` object to Node (SB-7 section 8) and a filter step in the core. The extension hook (section 5) can redact in the meantime.

### 6.8 Errors

| Situation | Code | HTTP |
|---|---|---|
| Request fails the 6.6 rules; bad or stale cursor | `INVALID_REQUEST` | 400 |
| Node id not visible at *S*, or there is no current bundle (`getNode`, `getNeighbors`) | `NODE_NOT_FOUND` | 404 |
| No `Knowledge_Read`, or a guest user | `FORBIDDEN` | 403 |
| REST body larger than 16 KB (read requests are small) | `PAYLOAD_TOO_LARGE` | 413 |
| Invalid hook configuration; a hook throws anything other than `notFound`; any other unexpected exception | `INTERNAL` (`retryable: true`, except `hook.invalid`, which is `false`) | 500 |

- `INTERNAL` messages are generic and carry the platform request id (`Request.getCurrent().getRequestId()`) so an admin can find the log. They never include a stack trace, note text or the query (SB-8 section 9 rule).
- The core logs the exception type and the request id at `ERROR` level with `System.debug`, and nothing else.
- `RATE_LIMITED` is never sent by the base package. The platform's own API limits apply.

## 7. REST endpoints (Exposure layer)

### 7.1 Experiments in 9a (the results go in the 9a PR description)

- **E1: percent-encoded `/` in the path.** Node ids contain `/` (`customers/onboarding-guide`). OpenAPI path parameters cannot contain a raw `/`, so clients must send `%2F` (OpenAPI style `simple`). Before writing the resource, the Developer checks in a scratch org whether `RestContext.request.requestURI` keeps `%2F` as written.
  - If it does (expected), use the parsing rule in 7.2.
  - If the platform decodes it first, stop and raise it in the PR. The Technical Architect then proposes a contract minor version that adds a `nodeId` query parameter as an alternative. Nothing is guessed.
- **E2: SOSL `WHERE` on a relationship field** in `RETURNING Knowledge_Node_Chunk__c(... WHERE Node__r.Valid_From__c <= :s ...)`. If it works, `searchCandidates` filters chunk hits in SOSL. Either way the SOQL step in 6.3 stays, so the result is the same.

### 7.2 Routes

Base path on Salesforce: `/services/apexrest/<ns>/knowledge/v1` (SB-7 4.1).

| Operation | Method and path | Class | Success |
|---|---|---|---|
| `getNode` | `GET /nodes/{nodeId}?includeBody=true\|false` | `KnowledgeNodesResource` | `200 NodeResult` |
| `getNeighbors` | `GET /nodes/{nodeId}/neighbors?direction=&types=&depth=&limit=` | `KnowledgeNodesResource` | `200 NeighborResult` |
| `searchNodes` | `POST /search` with a JSON body | `KnowledgeSearchResource` | `200 SearchResult` |
| `getContext` | `POST /context` with a JSON body | `KnowledgeContextResource` | `200 ContextResult` |

**Parsing `/nodes/*`:**

1. Take the part of `requestURI` after `/knowledge/v1/nodes/` and split it on a literal `/`.
2. One segment means `getNode`. Two segments, the second being exactly `neighbors`, means `getNeighbors`. Anything else is `400 INVALID_REQUEST`, rule `nodeId.encoding`, because a raw `/` means the client did not encode the id.
3. Decode the first segment with `EncodingUtil.urlDecode(segment, 'UTF-8')`, then validate it with the 6.2 pattern.
4. Because the id is encoded, a note whose id ends in `/neighbors` stays unambiguous.

**Query parameters:**

- `includeBody` accepts `true` or `false` only.
- `types` is repeated or comma-separated (OpenAPI `form`, `explode` true or false). Both forms are accepted.
- Integers must be decimal. A non-number gives `400` with rule `type`.
- An unknown parameter gives `400` with rule `additionalProperties`, so typos do not go unnoticed.

**POST bodies:**

- `Content-Type` must be `application/json`. Otherwise the response is `400`, rule `contentType`.
- The body is parsed with `JSON.deserializeUntyped`. A parse error gives `400`, rule `json`.
- Unknown properties give `400`, rule `additionalProperties`.
- Then the body is mapped to the request DTO and validated (6.6).

Other methods on a mapped path (for example `DELETE /nodes/x`) return `400 INVALID_REQUEST`, rule `method`, in the envelope. Apex REST only routes the methods a class annotates, so the Developer adds handlers that do nothing except return this error, which keeps the envelope consistent.

### 7.3 Responses (`KnowledgeRestSupport`)

- Success: `200`, `Content-Type: application/json; charset=utf-8`. The body is written with `JSONGenerator` using the contract's property names, including the renames in the section 4 table.
  - Optional properties that are null (`snippet`, `score`, `updatedAt`, `relation`, `anchor`, and `body` when not requested) are left out.
  - Required properties that may be null (`target`, `node` in a `NeighborEdge`, `nextCursor`, and `bundle` per 4.2) are written as `null`.
- Errors: the HTTP status from the 4.3 table, and the body `{"error": {"code", "message", "details", "retryable"}}` (SB-7 4.3). `details` is always present, `[]` when empty.
- Every response sets `Cache-Control: no-store`, because the content can change at every commit.
- The resources hold no logic. They parse, call `KnowledgeServiceResolver.get()`, and write the result or the `KnowledgeException`. Any other exception is turned into `INTERNAL` here.

## 8. Data and limits summary

| Item | Limit | Where enforced |
|---|---|---|
| Synchronous heap | 6 MB | Bodies loaded only where returned; groups of 10 for snippets; one text per node for context (6.3, 6.5) |
| SOQL queries | at most 7 per call (`getNeighbors` depth 2, `both`) | 6.4 |
| SOSL queries | at most 2 per call | 6.3, 6.5 |
| Search depth | 200 candidates (setting) | 6.3 |
| Request body | 16 KB | 7.2 |
| CPU | 10 s synchronous | Lexical scoring over at most 50 candidates and at most 10 texts; test 18 times the largest case |

## 9. Test approach

### 9.1 Apex unit tests (9a and 9b)

These run with `sf apex run test --test-level RunLocalTests` in a development scratch org, with at least 90 % coverage on the core, validator, text, cursor, resolver and resource classes.

- Data comes from `KnowledgeTestData`. It writes bundles through SB-8's `KnowledgeCommitStepRunner.runToCompletion`, so tests use real versioned rows, not records inserted by hand.
- Content is synthetic ("Example Corp").
- SOSL results are set with `Test.setFixedSearchResults`.
- REST tests set `RestContext.request` and `RestContext.response` and parse the response body.

| # | Test | Proves |
|---|---|---|
| 1 | `getNode` on a committed node; then `includeBody=false` | Every `NodeDetail` field; `body` left out |
| 2 | `getNode` for a deleted node, a node that never existed, and no current bundle | `404 NODE_NOT_FOUND` with the envelope |
| 3 | Bundle consistency: commit v1, start a read, commit v2 between the store calls (through a `@TestVisible` seam that commits after `currentBundle()`) | Results come only from *S* = v1 |
| 4 | Chunked node | `body` is the exact reassembled text (equal to the fixture) |
| 5 | `getNeighbors` out, in and both; types filter; depth 2; `limit` and `truncated`; unresolved edge with `node = null` | 6.4, including order |
| 6 | `searchNodes` with fixed results: node and chunk hits merged and de-duplicated; tag AND filter; a candidate not visible at *S* dropped | 6.3 candidates |
| 7 | Search cursor: three pages; tampered `h`; stale `s` after a new commit | `nextCursor` chain; `cursor.invalid`; `cursor.stale` |
| 8 | Search term building: reserved characters, a query of only punctuation, the AND then OR fallback | 6.3 term rules; empty result, not an error |
| 9 | Largest node (about 0.9 MB) through `getNode` over REST | `Limits.getHeapSize()` under 6 MB |
| 10 | Validation: one test per rule in 6.6 for every operation; all failures reported together | Same `details` for each input |
| 11 | Permission: a user without `Knowledge_Reader`, and a guest user (`System.runAs`) | `403 FORBIDDEN`, no content, for all four operations |
| 12 | Hook: a test subclass of `KnowledgeResultHook` configured through the setting (the test injects the setting through a `@TestVisible` seam, since custom metadata cannot be inserted in tests) | Hook runs on all four operations; changes are visible in the REST output |
| 13 | Hook errors: unknown class, a class that is not a subclass, a hook that throws, a hook that throws `notFound` | `INTERNAL` with `hook.invalid`; `INTERNAL`; `404` passed through |
| 14 | REST routing: `/nodes/a%2Fb`, `/nodes/a%2Fb/neighbors`, a raw `/nodes/a/b`, an id ending in `%2Fneighbors`, unknown query parameter, wrong method, wrong content type, bad JSON, 16 KB + 1 body | 7.2 rules and codes |
| 15 | Search page of 50 nodes with 100,000-character bodies | Heap under 6 MB; snippets right |
| 16 | `getContext` keyword extraction: stop words, short tokens, duplicates, 10-keyword cap, a question with no keywords | 6.5 step 1 |
| 17 | `getContext` ranking and passages: title and tag weights; matched chunk used; budget shared between nodes; citations `<path>@<commit>` | 6.5 steps 3 to 5 |
| 18 | `getContext` limits: total text never more than `maxChars` over a set of inputs; `truncated` set correctly; CPU time for 10 nodes of 100,000 characters under 5 s | 6.5 steps 4 and 6; section 8 |
| 19 | `getContext` with no match | `passages = []`, `truncated = false`, `200` |
| 20 | JSON shape: every response type through `KnowledgeRestSupport`, compared with the matching `contracts/services/v1/examples/` response file (copied into the test as a string by the Developer, with a comment naming the source file) | Property names, renames, null and omission rules (7.3) |

### 9.2 Contract tests (9c, Python)

`tools/contracts-check` gains `contracts_check/responses.py` and the command `contracts-check responses --operation <operationId> --status <code> <file.json>`. It validates a saved response body against the OpenAPI response schema for that operation and status. Its own pytest cases use the SB-7 examples (valid) and hand-broken copies (invalid). It uses no runtime code.

### 9.3 End to end (9c)

The script `packages/salesforce/scripts/e2e-read.sh` runs against a fresh scratch org (it needs the Dev Hub, which is an Alex account action):

1. Run SB-8's `e2e-sync.sh` steps 1 and 2, which sync the `basic/` fixture. Assign `Knowledge_Reader` to the running user. Wait 2 minutes for the search index.
2. Call each of the four operations with `curl`, using the instance URL and a token from `sf org display`. The token is masked as in SB-8 5.1 and never printed. Save each response.
3. Validate every saved response with `contracts-check responses` (9.2) and compare its content with the fixture's expected JSON.
4. Error paths: an unknown node (404), a bad `limit` (400), no token (platform 401, checked for status only), and a second user without `Knowledge_Reader` (403). Validate every envelope.
5. Commit the v2 fixture. Check that `getNode` on the deleted note returns 404, and that a cursor from before the commit returns `cursor.stale`.
6. The output of all steps is the PR's test evidence.

### 9.4 Install verification (9c)

SB-9 adds the following to `tools/package-check/expected-components.json`:

- The three resource classes.
- The `Knowledge_Reader` permission set.
- Its test classes, in `tests`.
- The `/nodes/*` probe from SB-12 section 7. The SB-9 entry accepts `404 NODE_NOT_FOUND` **or** `403 FORBIDDEN` in the SB-7 envelope, the same as the import probe, because the verifying user may not have `Knowledge_Reader`. Either response shows the resource is installed and conforms. The SB-12 text says "must return 404". The SB-9 entry is the more exact rule, and the Technical Architect notes this on PR #12.
- Probes for `POST /search` and `POST /context` with the body `{}`, which must return `400 INVALID_REQUEST` (rule `required`) or `403` in the envelope.

## 10. Acceptance-criteria mapping

| # | Acceptance criterion (story SB-9 / REQ-2) | Met by | Verified by |
|---|---|---|---|
| 1 | At least one knowledge-backed service call is reachable as a documented REST endpoint | Four read endpoints (7.2) over the core (6), documented by the SB-7 OpenAPI document and the REST README | 9.1 tests 1, 5, 6, 17 and 14; 9.3 step 2 |
| 2 | It returns structured content from synced knowledge | Results built only from rows visible at the current sequence (6, 6.1) | 9.1 tests 1, 3, 4 and 17; 9.3 steps 2, 3 and 5 |
| 3 | Unauthenticated calls are rejected with an error status and no content | Platform authentication (6.7) | 9.3 step 4 |
| 4 | Unauthorised calls are rejected with an error status and no content | `Knowledge_Read` check and guest check before any query (6.7); no object permissions for readers | 9.1 test 11; 9.3 step 4 |
| 5 | The endpoint matches the published service contract | DTOs mirror the OpenAPI schemas (4); JSON writer (7.3); one validator (6.6) | 9.1 tests 10 and 20; 9.2; 9.3 step 3 |
| 6 | REQ-8: no Salesforce-specific types leak into the contract | The contract is unchanged except for the nullable-`bundle` clarification (4.2); Salesforce-only behaviour (401 body, SOSL lag) is documented in the runtime README, not in `contracts/` | QA review; contracts-check neutrality scan |
| 7 | REQ-6 / C-application GA-1: extension hook defined without the base naming an extension | `KnowledgeResultHook` and the resolver by configuration (5) | 9.1 tests 12 and 13; `package-check static` |

## 11. Dependencies and open points

**Dependencies (build order):** the SB-7 contracts build, then SB-8 slice 8b, then SB-12 slice 12a. Specs: PR #7 (SB-7), PR #11 (SB-8) and PR #12 (SB-12) should merge before this one. If any of them changes in review, the Technical Architect updates this spec in the same run.

**Open points (none blocks the build):**

1. `bundle` nullable in `SearchResult` and `ContextResult` (4.2): the Developer writes it into the OpenAPI document in the SB-7 build PR. If Alex prefers, the Technical Architect adds an errata line to `SB-7.md` after PR #7 merges.
2. REQ-15 (Needs Alex): per-note access. MVP is package level (6.7).
3. REQ-13 (Needs Alex): citations. `citation` is filled anyway (6.5).
4. C-application AC-10 lists `KnowledgeService` as `global`. This spec keeps it `public` and makes `KnowledgeResultHook` the extension surface (5.1). The Technical Architect comments on PR #13.
5. AGENTS.md ownership rows for `packages/` and `tools/`: the open Technical Architect Inbox Blocker of 2026-10-15. Developer PRs call this out and do not edit AGENTS.md.

## 12. Definition of done for the Developer PRs

- The files in section 3 for the slice exist, and the tests in section 9 for the slice pass, with the commands and output in the PR.
- 9a: the E1 and E2 results are in the PR description.
- No change to `contracts/` except the nullable `bundle` (4.2, if not already in the SB-7 build) and, in 9c, the new `responses` command in `tools/contracts-check`.
- `package-check static` passes: layer rule, no dependencies, and no reference to a type outside the base namespace.
- No client content, credentials, org ids or instance URLs anywhere, including fixtures, scripts and logs.
- `python build.py` is unaffected (no changes to `research/`, `template.html` or `build.py`).
- Each PR links SB-9 and this spec. The story's PR Link points at the latest slice PR.
