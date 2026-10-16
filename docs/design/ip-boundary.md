# IP boundary: base package vs client extension packages

- **Story:** SB-13 "IP boundary: base package vs client extension package convention" (Notion Sprint Board)
- **Requirement:** REQ-6 Clear IP line between package and per-client logic (Must, Approved)
- **ADR:** [ADR-001](../adr/ADR-001-2gp-package-structure-and-knowledge-graph-sync.md) (Approved 2026-10-15), decision point 1 (option 1b, base package plus dependent extension packages)
- **Principles:** BP-1 Build once, deploy many; BP-2 Clear IP line; SP-1 Public-repo IP hygiene ([principles.md](../togaf/principles.md))
- **Author:** Technical Architect, 2026-10-16

## 1. The rule in one line

Everything in this repository is reusable Rich Solutions IP that any client could install unchanged. Anything that exists for one client lives in a separate extension package, in a separate repository, and depends on the base package. The base package never depends on it.

## 2. What goes where

| Belongs in this repo (Rich Solutions IP) | Belongs in a client extension (billable, outside this repo) |
|---|---|
| Runtime-neutral contracts: `contracts/kg-bundle`, `contracts/services` | Client vault content (the Obsidian notes themselves) and the vault repository |
| Tools that work for any vault: `tools/kg-compiler`, `tools/contracts-check` | Compiler configuration for one client (relation keys, folder filters) beyond the generic defaults |
| The Salesforce base package (`packages/salesforce/`): storage objects, service layer, REST, Apex API, Agentforce actions, permission sets | Custom Apex implementing the base package's `global` interfaces for one client's process |
| `global` extension interfaces and their default implementations | Client-specific Agentforce topics, prompts, actions and agent instructions |
| Templates: generic prompt templates, sample flows, sample vault with synthetic content | Client field mappings, record types, page layouts, profiles and org configuration |
| Documentation, ADRs, specs, TOGAF artefacts written generically | Client credentials, connected-app details, org IDs, namespaces registered for a client |
| Synthetic test data (for example "Example Corp") | Any real client data, names or engagement details, including in tests or examples |

**Test for a borderline case:** would a second, unrelated client want this unchanged (perhaps through configuration)? If yes, generalise it and put it here. If no, it is extension work. When unsure, keep it out and raise it in the Operator Inbox.

**Promotion path:** a feature first built for one client may move into the base package only after it is generalised (no client names, data or assumptions), reviewed, and accepted through a normal story and PR. The client extension then drops its copy and uses the base version.

## 3. Package structure

```
Rich Solutions base package  (unlocked 2GP, namespaced, this repo: packages/salesforce/)
  Contract layer   global interfaces + DTOs   <-- the only things extensions may reference
  Storage layer
  Service layer
  Exposure layer   REST, Apex API, Agentforce actions
        ^
        | depends on (one direction only)
        |
Client extension package  (unlocked 2GP, separate repo, per client)
  implements base global interfaces, adds client metadata
```

### 3.1 Base package rules

1. `packages/salesforce/sfdx-project.json` declares **no** `dependencies` on any package other than Salesforce platform features. In particular, it never lists a client extension package.
2. Base Apex never references an extension type by name. It finds extensions only through its own `global` interfaces (for example a `KnowledgeService` override resolved by a custom metadata record naming the implementing class, or `Type.forName` on a configured class name).
3. Defaults work alone: with no extension installed, the base package installs and passes its own tests in a fresh scratch org (REQ-12 / SB-12 install criterion).
4. The extension surface is the `global` Apex in the Contract layer plus the service contracts in `contracts/`. Anything else is internal and may change without notice. Changing or removing a `global` member is a breaking change for extensions and follows the contract versioning rules (SB-7 spec, section 7).

### 3.2 Extension package rules (for work done outside this repo)

1. One extension package per client, in a repository the client engagement owns (never this public repo).
2. Its `sfdx-project.json` lists the base package as a dependency, pinned to a released version (`<base>@<major>.<minor>.<patch>-<build>`, not `LATEST` in production).
3. It uses its own namespace or no namespace, never the Rich Solutions namespace.
4. It may extend the base only through `global` interfaces, custom metadata records, permission set groups and additive metadata. It does not patch or copy base package source.
5. Contract extensions travel in the namespaced `extensions` object of the kg-bundle (SB-7 spec, section 3.2), using a client prefix such as `acme:priority`, never by editing the base schemas.

## 4. How the boundary is enforced

| Check | Where | Who | When |
|---|---|---|---|
| PR template checklist item: "No client-specific logic, data or configuration; anything single-client belongs in an extension package outside this repo" | `.github/pull_request_template.md` (added by this PR) | PR author ticks it; QA Reviewer verifies | Every PR |
| QA review against section 2 of this doc | PR review | QA Reviewer | Every PR touching `packages/`, `contracts/`, `tools/` or templates |
| Dependency check: fail if `packages/salesforce/sfdx-project.json` lists any package dependency, or if base Apex references a type outside the base namespace | Added to CI by the Developer in SB-12 (package project story) | Developer builds; QA verifies | Every PR touching `packages/salesforce/` |
| Public-repo hygiene scan (client names, credentials, org IDs) | Existing rule in AGENTS.md; reviewers | All agents; QA Reviewer | Every PR |

The dependency check belongs to SB-12 because that story creates `sfdx-project.json`. Its spec will include this check and reference this doc.

## 5. Acceptance-criteria mapping

| # | Acceptance criterion (SB-13 / REQ-6) | Met by |
|---|---|---|
| 1 | Design doc defines what belongs in the base package/templates vs per-client extension packages kept outside this repo | Sections 2 and 3 of this doc |
| 2 | Base package has no dependency on any extension | Section 3.1 rules 1 to 3; CI dependency check in section 4 (built in SB-12) |
| 3 | A review checklist item in the PR template or AGENTS.md flags client-specific logic or data | New checklist item in `.github/pull_request_template.md` (this PR) |
| 4 | REQ-6: the repo contains only the reusable package and templates, no client logic or data | Section 2 table, section 4 checks |
| 5 | REQ-6: custom client behaviour lives outside the base package and the base does not depend on it | Section 3.2 rules; section 3.1 rule 1 |

## 6. Open points

- **Pilot repository:** where the first client extension repo lives is an account decision for Alex; it is not recorded here (public repo).
- **REQ-15 governed access** (Needs Alex) may add permission-related extension points; they would be added to the Contract layer as new `global` members, following section 3.1 rule 4.
