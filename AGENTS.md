# AGENTS.md

Operating rules for the autonomous agent team that builds the Rich Solutions Platform. Alex Rich is the principal operator. Agents keep no memory between runs: all shared state lives in Notion (Agent Team HQ) and in this repository.

## This repository is PUBLIC

Never commit client names, engagement details, pilot candidates, credentials, tokens, org IDs, or any other secret. Describe engagements generically (for example "a public-sector pilot"). If in doubt, leave it out and raise it in the Operator Inbox.

## Every run

1. Start by reading the Vision Brief and Agent Team HQ in Notion, this file, and the 3 newest Agent Handoff Log entries.
2. Touch only what your role owns (table below). Comment on other agents' items; never edit them.
3. Blocked, conflicting requirements, or a decision needed: create an Operator Inbox item (Status Open, From Agent = your role) and stop on that item.
4. Never merge, force-push, delete branches or pages, or sign up for paid services or external accounts. Only Alex sets an ADR to Approved.
5. End every run with exactly one Agent Handoff Log entry (Run = `<Role> - YYYY-MM-DD`, Outcome Progress / No change / Blocked / Failed). If Notion or GitHub is unreachable, still try to log Outcome = Failed with the exact error. If you cannot push, say so in the log and raise a Blocker in the Operator Inbox.

## Run harness

Every run works inside a harness: a plan, the context it needs, scripts that enforce the fixed rules, checks with real evidence, and a handoff. Adapted from the plan → verify → feedback habits Boris Cherny has shared about Claude Code. The Agent Handoff Log is the progress record; this file is the rule memory.

1. **Plan before editing.** Write the run's steps, each naming the files or Notion items it reads and writes, its one output, and the check that proves it. Write the checks before the work. The plan opens the PR description (or the Handoff entry when there is no PR). Routines are unattended, so do not pause for approval: anything that needs Alex goes to the Operator Inbox.
2. **Load only what a step needs.** The story, its Requirements, its spec, the Approved ADRs it depends on. Keep raw logs out of Notion and PRs; summarise them as paths, verdicts and evidence.
3. **Scripts enforce fixed rules, not memory.**
   - `.claude/hooks/guard_git.py` (PreToolUse hook) blocks pushing to `main`, force-push, branch deletion and `gh pr merge`.
   - `python tools/preflight.py --role <role-slug>` checks branch name, folder ownership, the public-repo secret scan and `python build.py`, and prints a Checks table. Run it before every push; a fail blocks the push.
   If a required tool is unavailable, name the blocker and finish the steps that can still be done.
4. **Verify with real signals.** Each output proves itself: preflight, tests, the build, the rendered file, a re-read of the Notion row you changed. Your own confidence counts last. Record a Checks table, `Step | Requirement | Verdict | Evidence`, with verdict `pass`, `fail` or `unresolved`. Leave missing evidence visible as `unresolved`. Never weaken a check to get a pass.
5. **Feedback loop.** A failed check sends only that step back, with the reason and the evidence. At most three attempts per step; after that mark it `fail`, set Outcome = Blocked if it blocks the story, and raise an Operator Inbox item.
6. **Completion checklist** before the Handoff entry: every output exists and opens at its path or URL; every check ran against the pushed version; failures are fixed or reported; rule proposals are recorded.
7. **Handoff.** The Handoff Log entry's What Changed carries: Plan (steps done / blocked), Outputs (exact paths and URLs), Decisions (and why), Open issues, and Next Agent Pickup as the next ready step. Report usage only when measured; never estimate it from the prompt.
8. **Memory.** When you catch a mistake, or a correction lands (a QA defect, a review comment from Alex, a red CI run), add `Rule proposal: <one-line rule>` to your Handoff entry. The Technical Architect folds proposals into **Learned rules** below by PR, so the next run never repeats the mistake.

## Learned rules

Rules added from Rule proposals in the Handoff Log. One line each, newest last, with the date and source run.

- _None yet._

## Git workflow

- Branch: `agent/<role>/<story-id>`, e.g. `agent/technical-architect/SB-2`. Role slugs: `project-manager`, `business-analyst`, `enterprise-architect`, `technical-architect`, `developer`, `qa-reviewer`, `resource-manager`.
- Open a PR to `main` using the PR template; link the Sprint Board story in the description and put the PR URL in the story's PR Link.
- Only Alex merges to `main`. No force-push. No branch deletion.
- Keep `python build.py` working; the `build-smoke-test` workflow checks it.

## Folder ownership

| Path | Owner | Notes |
|---|---|---|
| `AGENTS.md`, `.github/pull_request_template.md`, `.github/CODEOWNERS`, `.claude/`, `tools/`, `docs/README.md`, every `docs/*/README.md`, other repo scaffolding | Technical Architect | Folder owners may propose README changes via the Operator Inbox |
| `docs/design/`, `docs/specs/` | Technical Architect | Specs are named `<story-id>.md` |
| `docs/adr/` | Technical Architect (technical ADRs), Enterprise Architect (enterprise ADRs) | Matching Decisions Log row required |
| `docs/togaf/` | Enterprise Architect | |
| `docs/requirements/` | Business Analyst | |
| `docs/vision/` | Project Manager | Notion Vision Brief is source of truth |
| Package source, tests (added in later phases) | Developer | Only from Ready for Dev stories with an Approved-ADR spec |
| PR reviews; Defects database | QA Reviewer | Review comments only; no pushes to others' branches |
| `README.md`, `GOAL.md`, `LICENSE`, `build.py`, `template.html`, `whitespace-atlas.html`, `research/`, `accelerators/`, `.github/workflows/` | Alex | Agents do not move or rewrite these without an Operator Inbox decision |

## Story flow

Backlog → Ready for Design (Business Analyst) → Ready for Dev (Technical Architect, once requirements and related ADRs are Approved and a spec exists) → In PR (Developer) → In QA (QA Reviewer) → Awaiting Merge → Done (Alex merges).

## Architecture guardrails

- First package: Salesforce unlocked 2GP package exposing knowledge-backed service calls via REST, Apex and Agentforce actions, driven by an Obsidian knowledge graph synced through GitHub.
- Keep the knowledge-graph sync format and service contracts runtime-neutral so future non-Salesforce runtimes reuse them instead of forking.
- IP line: package and templates are Rich Solutions IP; per-client logic is billable and lives outside this repo.
