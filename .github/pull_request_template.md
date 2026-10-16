## Story
<!-- Link to the Sprint Board story (Notion). Required. -->
Story:

## Summary
<!-- What changed and why, in a few lines. -->

## Test evidence
<!-- Commands run and their results, screenshots, or CI links. -->

## Checklist
- [ ] Branch is named `agent/<role>/<story-id>`
- [ ] Only touches folders this role owns (see AGENTS.md)
- [ ] No client names, engagement details, credentials or secrets (repo is public)
- [ ] No client-specific logic, data or configuration; anything single-client belongs in an extension package outside this repo (see `docs/design/ip-boundary.md`)
- [ ] `python build.py` still works (if research/, template.html or build.py are touched)
- [ ] Specs/ADRs referenced are Approved (for build work)
- [ ] Sprint Board story updated with this PR link
