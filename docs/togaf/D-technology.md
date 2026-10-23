# Phase D: Technology Architecture

- **Status:** Draft
- **Date:** 2026-10-23
- **Owner:** Enterprise Architect
- **Story:** SB-15 "TOGAF Phases B to F: Business, Data, Application, Technology, Opportunities & Migration" (Notion Sprint Board)
- **Sources:** Notion Vision Brief (approved 2026-10-13, gate G0), [`GOAL.md`](../../GOAL.md), Notion Requirements database, Operator Inbox
- **Related requirements:** REQ-1 to REQ-8 (Approved); REQ-12 to REQ-15 (Needs Alex); see [`docs/requirements/traceability.md`](../requirements/traceability.md)
- **Related ADRs:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) 2GP package structure and knowledge-graph sync (Approved 2026-10-15); [ADR-002](../adr/ADR-002-hybrid-agent-runtime.md) hybrid cloud/local agent runtime (Approved). No new ADR is proposed here.
- **Related specs and designs (open PRs, not yet on `main`):** `docs/specs/SB-7.md` contracts (PR #7); `docs/specs/SB-8.md` sync (PR #11); `docs/specs/SB-9.md` service core and REST (PR #14); `docs/specs/SB-10.md` Apex API (PR #15); `docs/specs/SB-11.md` Agentforce actions (PR #16); `docs/specs/SB-12.md` package project (PR #12); `docs/design/ip-boundary.md` (PR #8, SB-13); [`docs/design/hybrid-agent-runtime.md`](../design/hybrid-agent-runtime.md)
- **Previous:** Phase B Business (`B-business.md`, PR #6), Phase C Data (`C-data.md`, PR #10), Phase C Application (`C-application.md`, PR #13) · **Principles:** [principles.md](principles.md)

This phase names the platforms, environments and technology services that the Phase C application components run on, and where the trust boundaries and secrets sit. It is the enterprise view: exact CLI flags, scratch-org feature names and workflow steps belong to the Technical Architect's specs, and this document points to them (AP-1, one definition).

**Hosting outside Salesforce is undecided.** The Operator Inbox question "Hosting target for anything outside Salesforce (AWS vs on-platform only)" (Enterprise Architect, 2026-10-13) is still open. Section 6 records both options as a gap and does not choose. The MVP baseline in sections 2 to 5 needs no hosting, so nothing here waits on that answer.

Nothing here changes an Approved ADR. If a later spec needs to differ from this document, the spec wins for detail and this document is updated; if it would differ from ADR-001 or ADR-002, a new ADR is needed first.

## 1. Technology principles applied

| Principle | What it means for technology |
|---|---|
| TP-1 Cloud-agnostic, no new hosting by default | MVP technology is limited to GitHub (repos and Actions), a developer workstation, and Salesforce orgs. New hosting or a paid service needs an ADR approved by Alex |
| TP-2 Clean, repeatable install | Every in-org component ships in one unlocked 2GP package version and installs into the plainest scratch-org shape with no feature dependency |
| AP-1 Runtime-neutral contracts | Toolchain technology (Python 3.12, JSON Schema 2020-12, OpenAPI 3.1) carries no Salesforce dependency, so a second runtime reuses it |
| AP-3 Model and vendor swappability | The base package makes no model call. The factory's default model is Claude, swappable; the local tier runs an open-weight model (ADR-002) |
| DP-2 Data residency and least data | Client knowledge is processed only on the client's GitHub and in the client's Salesforce org. Rich Solutions technology holds none of it |
| SP-1 Public-repo IP hygiene | No org ids, instance hosts, keys or tokens in this repo. Secrets live only in GitHub Actions secrets of the repository that uses them |
| SP-2 Least privilege | One integration user and permission set per caller type; CI credentials are scoped to the one org and the one job that needs them |
| BP-3 Human-in-the-loop | Technology steps that change what clients receive (merge, package promote, tag, secret set-up, org creation) are Alex actions, never agent actions |

## 2. Technology landscape

Three technology groups match the Phase C application groups.

| Group | Platforms | Who operates it |
|---|---|---|
| **T1 Toolchain and delivery** (for C-application G1) | GitHub repositories, GitHub Actions runners, Python 3.12, Salesforce CLI (`sf`) | Rich Solutions for this repo; the client for the vault repo and its CI |
| **T2 Salesforce runtime** (for G2, accelerator #1) | Salesforce Platform: Dev Hub, scratch orgs, sandboxes, client production orgs; Apex, REST (`@RestResource`), async Apex, SOSL/SOQL; Agentforce where licensed | Rich Solutions for the Dev Hub and test orgs; the client for its own orgs |
| **T3 Factory** (for G3, not shipped) | Notion workspace, Claude Code cloud routines with the Notion and GitHub connectors, GitHub PR flow and rulesets; optional local workstation (Ollama, Hermes Agent, Docker) | Alex |

### 2.1 Technology component catalogue

| ID | Technology component | Version or standard | Used by (Phase C) | Defined by |
|---|---|---|---|---|
| TC-1 | **GitHub repository, this repo** (public) | – | AC-1 to AC-5 definitions, AC-10 to AC-21 source, AC-32 | `AGENTS.md`; ruleset on `main` |
| TC-2 | **GitHub repository, client vault repo** (private, client-owned) | Obsidian Markdown, YAML frontmatter | Vault content (C-data D1) | ADR-001 Consequences; SB-8 spec 5.2 |
| TC-3 | **GitHub Actions, GitHub-hosted runner** (`ubuntu-latest`) | Actions workflow syntax | AC-5 vault-sync in the client repo; AC-33 checks in this repo | SB-8 spec 5.2; SB-12 spec 6.2 |
| TC-4 | **GitHub Actions, self-hosted runner** (option, client-operated) | Same workflow, different `runs-on` | AC-5 for sensitive vaults only | Gap GT-2 (C-data GD-4) |
| TC-5 | **Python 3.12 runtime** | CPython 3.12; dependencies pinned per tool | AC-2 contracts-check, AC-3 kg-compiler, AC-4 kg-push, AC-21 package-check | SB-7 spec 6; SB-8 spec 4 and 5; SB-12 spec 3 |
| TC-6 | **Contract standards** | JSON Schema 2020-12; OpenAPI 3.1; MCP-style tool manifest | AC-1 | SB-7 spec 3 and 4 |
| TC-7 | **Salesforce CLI** (`sf`) | Current GA at build time, recorded in each PR | AC-4 auth adapter, AC-21 scripts, CI jobs | SB-8 spec 5.1; SB-12 spec 4 and 5 |
| TC-8 | **Salesforce Dev Hub** (Rich Solutions org) with registered namespace | Unlocked 2GP | Package and version creation; scratch-org creation | ADR-001 Consequences; SB-12 spec 10 |
| TC-9 | **Scratch orgs**, three shapes (section 3) | `project-scratch-def*.json` | Development, install proof, Agentforce testing | SB-12 spec 3.4 and 5.1 |
| TC-10 | **Sandbox** (Alex-provided) | – | Install proof for REQ-5 AC 4 | SB-12 spec 5.4 |
| TC-11 | **Client Salesforce org** (sandbox, then production for a pilot) | Edition and licences per client | Runs the installed G2 package | Pilot decision (REQ-14, Needs Alex) |
| TC-12 | **Apex runtime services**: `@RestResource`, `global` Apex, `@InvocableMethod`, Queueable and Schedulable jobs, SOSL/SOQL | API version pinned at build time (`sourceApiVersion`) | AC-13 to AC-19 | ADR-001 Part 1; SB-8 spec 7; SB-9 spec |
| TC-13 | **Agentforce** (in orgs where it is licensed and enabled) | Agent actions over invocable Apex | AC-19 consumers; model path for DF-7 | SB-11 spec; SB-12 spec 5.3 |
| TC-14 | **Notion workspace** (Agent Team HQ) | – | AC-31 | HQ page |
| TC-15 | **Claude Code cloud routines** (scheduled agent runs with repo, Notion and GitHub access) | Default model Claude, swappable | AC-30 | HQ schedule; `AGENTS.md` |
| TC-16 | **Local agent workstation** (optional): Ollama on loopback, Hermes Agent profile, Docker sandbox, repo-scoped GitHub App | Pinned model digest | AC-34 | ADR-002; hybrid-agent-runtime design |

No component in this catalogue is a new paid service or a new hosted runtime. TC-4, TC-10, TC-11 and TC-13 are provided by Alex or the client; agents never create or buy them.

## 3. Environments

### 3.1 Environment catalogue

| ID | Environment | Shape | Created by | Purpose | Lifetime |
|---|---|---|---|---|---|
| ENV-1 | **Developer workstation or cloud agent container** | Python 3.12, `sf` CLI, git | Developer agent session | Build and unit-test toolchain (AC-1 to AC-5, AC-21); run scripts against scratch orgs | Per session |
| ENV-2 | **Dev Hub** | Rich Solutions org with Dev Hub and namespace | Alex (account action) | Owns the package, versions and scratch orgs | Permanent |
| ENV-3 | **Development scratch org**, namespaced | `project-scratch-def.json` | `create-scratch.sh` | Day-to-day Apex development and tests | Short (days) |
| ENV-4 | **Install-target scratch org**, plain, `--no-namespace` | `project-scratch-def.json`, no features | `install-and-test.sh` | Proves REQ-5 / TP-2: install, subscriber tests, `verify-install` | Minutes; deleted on exit |
| ENV-5 | **Agentforce scratch org** | `project-scratch-def.agentforce.json` | `create-scratch.sh` | SB-11 action testing only, never the install target | Short |
| ENV-6 | **Sandbox** | Client-like org | Alex provides and authorises | REQ-5 AC 4 install proof | Alex-managed |
| ENV-7 | **This repo's CI** | GitHub-hosted runner | Workflow files (Alex-owned folder) | `build-smoke-test` today; proposed `contracts-check` and `package-ci` | Per run |
| ENV-8 | **Vault repo CI** | GitHub-hosted runner, or self-hosted (TC-4) | Client copies the AC-5 template | Compile, validate, push the client's knowledge | Per run |
| ENV-9 | **Client org(s)** | Client's sandbox, then production | Client | Runs the released package for a pilot | Client-managed |

ENV-3 to ENV-5 come from SB-12 spec sections 3.4 and 5. ENV-6 and ENV-9 stay outside agent control (SB-12 spec 5.4).

### 3.2 Promotion path

```
ENV-1 build ──PR──► ENV-7 CI checks ──Alex merge──► main
                                                     │ package-ci on main (once allowed) or Developer locally
                                                     ▼
                         ENV-2 version create (beta 04t) ──► ENV-4 install + tests + verify
                                                                │ pass
                                                                ▼
                                                     ENV-6 sandbox install (Alex-provided)
                                                                │ pass
                                                                ▼
                                    Alex: sf package version promote, tag pkg-v<x.y.z>
                                                                │
                                                                ▼
                                       ENV-9 client sandbox, then production (pilot)
```

Every arrow that crosses into a client-facing step (merge, promote, tag, client install) is a human gate (BP-3). Agents produce beta versions and evidence only (SB-12 spec 8).

## 4. Deployment view: application to technology

| Application component (Phase C) | Runs on | Environments |
|---|---|---|
| AC-1 contracts, AC-2 contracts-check | TC-5, TC-6 on TC-3 or ENV-1 | ENV-1, ENV-7, ENV-8 |
| AC-3 kg-compiler, AC-4 kg-push | TC-5, TC-7 (auth adapter) | ENV-1, ENV-8 |
| AC-5 vault-sync workflow template | TC-3 (default) or TC-4 | ENV-8 |
| AC-10 to AC-20 Salesforce base package | TC-12 inside TC-8/TC-9/TC-10/TC-11 | ENV-3 to ENV-6, ENV-9 |
| AC-19 Agentforce actions (consumed by agents) | TC-12, consumed through TC-13 | ENV-5, ENV-9 where Agentforce is on |
| AC-21 package-check and install scripts | TC-5, TC-7 | ENV-1, ENV-7 |
| AC-30 cloud agent team | TC-15 | – |
| AC-31 Notion HQ | TC-14 | – |
| AC-32 GitHub repo and PR flow, AC-33 CI | TC-1, TC-3 | ENV-7 |
| AC-34 local agent runtime | TC-16 | – |

The Salesforce package is the only shipped runtime. Everything a client runs outside Salesforce is a GitHub Actions workflow in the client's own repository.

## 5. Connectivity, trust boundaries and secrets

### 5.1 Trust zones

| Zone | Contains | Owner |
|---|---|---|
| Z1 Public | This repo (TC-1), its CI (ENV-7) | Rich Solutions |
| Z2 Client GitHub | Vault repo (TC-2), its CI and secrets (ENV-8) | Client |
| Z3 Client Salesforce | Client orgs (ENV-9) and the installed package | Client |
| Z4 Rich Solutions Salesforce | Dev Hub, scratch orgs, Rich Solutions sandbox (ENV-2 to ENV-6) | Rich Solutions (Alex) |
| Z5 Factory | Notion (TC-14), agent routines (TC-15), workstation (TC-16) | Rich Solutions (Alex) |

### 5.2 Connections

| Connection | From → To | Protocol and auth | Credential lives in | Interface (Phase C) |
|---|---|---|---|---|
| CN-1 | Author → vault repo | Git over HTTPS; client GitHub identity | Client | IF-1 |
| CN-2 | Vault CI → client org import | HTTPS; OAuth JWT bearer flow through a CI-only connected app; integration user with `Knowledge_Sync` only | Vault repo Actions secrets (`SF_CLIENT_ID`, `SF_JWT_KEY`, `SF_USERNAME`, `SF_INSTANCE_URL`) | IF-4 |
| CN-3 | Vault CI → this repo (tag of the toolchain) | HTTPS, public read | None | – |
| CN-4 | External caller → client org read REST | HTTPS; caller's Salesforce auth; `Knowledge_Reader` | Caller | IF-6 |
| CN-5 | Agentforce → model | Salesforce's own Agentforce model path | Salesforce | IF-9 |
| CN-6 | This repo CI → Dev Hub (`package-ci` scratch-install job, optional) | HTTPS; JWT to Dev Hub | This repo's Actions secrets (`SF_DEVHUB_*`), set by Alex | – |
| CN-7 | Cloud agents → Notion, GitHub | Connectors managed by the platform | Platform, never the repo | IF-11 |
| CN-8 | Local agent → GitHub | Repo-scoped GitHub App token; no admin, no workflows, no merge | Workstation, outside the container's worktree | ADR-002 |
| CN-9 | Local agent → Ollama | Loopback only (127.0.0.1) | None | ADR-002 |

### 5.3 Rules

1. **No outbound calls from the base package in the MVP.** No Named Credential, no callout, no external model call (C-application 5.2 rule 5). All connections into Z3 are inbound.
2. **Secrets stay in the zone that uses them.** Vault-sync secrets are in Z2, Dev Hub secrets in Z1's Actions secrets set by Alex, and none of them in any file. CI masks the Salesforce access token before writing it to the job environment (SB-8 spec 5.1).
3. **Rich Solutions never holds client credentials.** CN-2 is configured by the client (or by Alex inside the client's GitHub, under the engagement), not in this repo or in Notion.
4. **Full bundles are not stored as CI artifacts.** Only a summary, with 7-day retention (SB-8 spec 5.3, closes C-data GD-5).
5. **Fork PRs get no secrets.** The `package-ci` scratch-install job never runs on fork PRs (SB-12 spec 6.2).

## 6. Hosting outside Salesforce (open question: gap, not a choice)

The MVP baseline (sections 2 to 5) needs **no hosting**: ADR-001 option A compiles in GitHub Actions and pushes into the org. Hosting becomes relevant only for:

- ADR-001 option B2 (orgs pull the published bundle; needs somewhere to publish it, which could still be GitHub Releases),
- ADR-001 option C (an external sync service, for example for many orgs, large vaults or vector search),
- a second, non-Salesforce runtime (REQ-9, Won't for the MVP; Vision Brief future enhancement).

| Option | What it means | Fits MVP? | Needs | Effect on this document |
|---|---|---|---|---|
| **H0 On-platform only** | Salesforce plus GitHub (repos, Actions, optionally Releases). No other cloud | Yes, it is the baseline | Nothing new | None. B2 can still use GitHub Releases |
| **H1 External hosting** (AWS named in the Inbox question; any cloud, per TP-1) | A Rich Solutions or client cloud account runs a sync service, a bundle store or a second runtime | Not needed for MVP | Alex's hosting decision; an account (a paid service, so Alex only); a new ADR; residency review per pilot | Adds a zone, connections and a deployment row; contracts and toolchain stay unchanged (AP-1) |

Decision criteria to bring to the hosting decision, not a recommendation: whether a pilot needs more than one org fed from one vault; vault size against Apex limits; whether semantic search is wanted; the target sector's authorisation needs (for example FedRAMP or StateRAMP for public-sector pilots); and who would operate it.

Handling: the existing Operator Inbox question stays the single place for this decision. If Alex picks H1, the Enterprise Architect writes an enterprise ADR for the hosting target and updates this section; nothing built for the MVP changes.

## 7. Platform constraints that shape the design

| Constraint | Source | Where it is handled |
|---|---|---|
| Apex heap 6 MB sync / 12 MB async; 10,000 DML rows per transaction; 131,072 characters per Long Text Area | Salesforce governor limits (ADR-001 C6) | Paged import (default 200 nodes, 1 MB per page) and chunking (SB-8 spec 4); DML row budget per commit step (SB-8 spec 7.3) |
| Queueable chain depth and scheduled-job limits | Salesforce async limits | Commit step runner, resume and watchdog jobs (SB-8 spec 7.3) |
| Dev Hub daily limits on scratch orgs and package versions | Salesforce Dev Hub | `package-ci` creates versions only on `main` and manual dispatch, not per PR commit (SB-12 spec 6.2); scripts stop on limit errors, no retry loops |
| Agentforce needs licences and features a plain scratch org lacks | Salesforce | Invocable Apex is packaged; agent metadata is unpackaged and deployed after install (SB-12 spec 5.3) |
| GitHub-hosted runners are shared infrastructure; artifacts and logs default to long retention | GitHub | Summary-only artifacts (rule 5.3.4); self-hosted runner option (gap GT-2) |
| `.github/workflows/` is Alex-owned | `AGENTS.md` | New workflows wait on the Inbox decision (gap GT-4) |
| Path-filtered checks must not be required checks on `main` | ADR-002 Consequences; SB-12 spec 6.2 | No new required check proposed |

## 8. Residency and compliance notes (technology view)

This complements C-data section 7. It claims no certification.

| Where data is processed | Technology | Regulated-pilot question |
|---|---|---|
| Vault content at rest | TC-2, client GitHub | Is the client's GitHub plan and data location acceptable for this content? |
| Vault content during compile and push | TC-3 or TC-4 | GitHub-hosted runner acceptable, or self-hosted runner inside the client boundary (GT-2)? |
| Knowledge at rest and in use | TC-11, client Salesforce org | Which Salesforce instance and authorisation level does the client run (for example a government cloud offering)? The package adds no new data location |
| Grounding passages | TC-13 Agentforce model path | Are the client's Agentforce model terms acceptable for the sector (C-data GD-6)? |
| Factory artefacts | TC-1, TC-14, TC-15 | Never client data (SP-1); nothing to answer per pilot |

Because the base package has no outbound connection (rule 5.3.1), adopting it does not move client knowledge to any location the client does not already use.

## 9. ADR and spec alignment check

| Source | Statement | This document |
|---|---|---|
| ADR-001 decision 1 | One namespaced unlocked 2GP base package; extensions are separate dependent packages | TC-8 namespace; one package in ENV-3 to ENV-9 |
| ADR-001 decision 2 | Option A: compile in CI, push via the package's import endpoint; JWT connected app, key in Actions secrets | TC-3, CN-2, rule 5.3.2 |
| ADR-001 decision 4; C4 | B2 and C remain later adapters; hosting undecided | Section 6 records H0 and H1 as a gap |
| ADR-001 C1 | Zero-manual-step install into a fresh scratch org | ENV-4 plain shape; Agentforce metadata kept out of the package |
| ADR-002 | Cloud-governed hybrid runtime; local output only as reviewed PRs; no required path-filtered check | TC-16, CN-8, CN-9; section 7 last row |
| SB-12 spec | Alex promotes and tags; agents create beta versions only | Section 3.2 promotion path |

No conflict found.

## 10. Requirement traceability

| Requirement | Status | Technology components | Environments | Covered |
|---|---|---|---|---|
| REQ-1 Knowledge-graph sync | Approved, Must | TC-2, TC-3 (or TC-4), TC-5, TC-7, TC-12 | ENV-8, ENV-9 (ENV-3/4 for tests) | Yes |
| REQ-2 REST service calls | Approved, Must | TC-12 (`@RestResource`) | ENV-3, ENV-4, ENV-9 | Yes |
| REQ-3 Apex service calls | Approved, Must | TC-12 (`global` Apex) | ENV-3, ENV-4, ENV-9 | Yes |
| REQ-4 Agentforce actions | Approved, Must | TC-12 (`@InvocableMethod`), TC-13 | ENV-5, ENV-9 | Yes |
| REQ-5 Clean 2GP install | Approved, Must | TC-7, TC-8, TC-9, TC-10 | ENV-2, ENV-4, ENV-6 | Yes |
| REQ-6 Clear IP line | Approved, Must | TC-1 public repo vs TC-2 client repo; TC-8 namespace | Zones Z1 vs Z2/Z3 | Yes |
| REQ-7 Work logged in Notion | Approved, Must | TC-14, TC-15, TC-1 | – | Yes |
| REQ-8 Runtime-neutral contracts | Approved, Should | TC-5, TC-6 | ENV-1, ENV-7, ENV-8 | Yes |
| REQ-9 to REQ-11 | Won't (MVP) | None; REQ-9 hosting is section 6 | – | Out of scope |
| REQ-12 Zero-manual-step install | Needs Alex | TC-7 scripts, ENV-4 | ENV-4 | Pending Alex |
| REQ-13 End-to-end Agentforce answer | Needs Alex | TC-13 | ENV-5 or an Alex-provided org | Pending Alex |
| REQ-14 One client pilot by late January 2027 | Needs Alex | TC-11 | ENV-9 | Pending Alex |
| REQ-15 Governed access | Needs Alex | TC-12 permission sets, CN-2 and CN-4 auth | ENV-9 | Pending Alex |

## 11. Gaps and open items

| ID | Gap | Impact | Handling |
|---|---|---|---|
| GT-1 | Hosting outside Salesforce (H0 vs H1) | Only for ADR-001 options B2/C and a second runtime; MVP needs none | Existing Enterprise Architect Inbox question (2026-10-13). Section 6 records both options |
| GT-2 | Self-hosted runner for sensitive vaults (C-data GD-4) | GitHub-hosted runners process vault content | Client decision per pilot; the AC-5 template supports either `runs-on`. No Rich Solutions hosting involved |
| GT-3 | Dev Hub, namespace, package name, connected app, sandbox, Agentforce-capable scratch orgs | ENV-2, ENV-4 to ENV-6 cannot be exercised end to end | Existing Technical Architect Inbox item on account actions (2026-10-19) |
| GT-4 | Agent-added workflow files (`contracts-check`, `package-ci`) | ENV-7 runs only `build-smoke-test`; other checks run locally with output in the PR | Existing Technical Architect Inbox item (2026-10-20) |
| GT-5 | `python build.py` fails on `main` (placeholder `research/*.json`) | `build-smoke-test` would fail on PRs touching those paths | Existing Technical Architect FYI item; Alex-owned files |
| GT-6 | Factory usage budget | Caps how often TC-15 routines and CI can run | Existing Resource Manager Inbox question |
| GT-7 | Phases B and C and the SB-7 to SB-13 specs are in open PRs | This document cites them by PR | Update links to `main` paths once merged |

None of these gaps needs a new ADR now or blocks the SB-7 to SB-13 specs.

## 12. Next ADM steps

1. Phases E to F (`E-F-roadmap.md`): work packages mapped to SB-7 to SB-13, transition architectures (T0 factory only, T1 package skeleton, T2 sync and reads, T3 Agentforce and pilot-ready) and the gates.
2. Promote Phases A to D to Baseline once their PRs (#6, #10, #13 and this one) merge.
3. Then propose gate G1 ("G1 Design approved") in the Operator Inbox with evidence. ADR-001 and ADR-002 are already Approved.
