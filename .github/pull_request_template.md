## Story
<!-- Link to the Sprint Board story (Notion). Required. -->
Story:

## Summary
<!-- What changed and why, in a few lines. -->

## Plan
<!-- Steps written before the work: step, files it reads/writes, output, check. See "Run harness" in AGENTS.md. -->

## Checks
<!-- Paste the table from `python tools/preflight.py --role <role-slug>`, then add a row per acceptance criterion. Verdict: pass / fail / unresolved. -->
| Step | Requirement | Verdict | Evidence |
|---|---|---|---|

## Test evidence
<!-- Commands run and their results, screenshots, or CI links. -->

## Checklist
- [ ] Branch is named `agent/<role>/<story-id>`
- [ ] Only touches folders this role owns (see AGENTS.md)
- [ ] No client names, engagement details, credentials or secrets (repo is public)
- [ ] `python build.py` still works (if research/, template.html or build.py are touched)
- [ ] Specs/ADRs referenced are Approved (for build work)
- [ ] `python tools/preflight.py --role <role-slug>` passes
- [ ] Sprint Board story updated with this PR link
