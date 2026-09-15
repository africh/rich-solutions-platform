# Accelerators — Whitespace-to-Solution Build-out

Each directory under `accelerators/` represents one whitespace capability (L3) that has been
selected for an accelerated solution build using the six-stage HITL-gated path from GOAL.md.

## Directory convention

```
accelerators/
├── README.md                      ← this file (index & status board)
├── {wave}-{industry}-{l3-slug}/   ← one directory per selected whitespace gap
│   ├── spec.md                    ← capability spec: scores, rationale, pattern refs
│   ├── blueprint.md               ← Stage 3: solution blueprint & reference architecture
│   ├── backlog.md                 ← Stage 4: user stories / agent specification
│   ├── gates/                     ← HITL gate records (one file per stage transition)
│   │   ├── stage1-to-2.md
│   │   ├── stage2-to-3.md
│   │   ├── stage3-to-4.md
│   │   ├── stage4-to-5.md
│   │   └── stage5-to-6.md
│   └── artifacts/                 ← Stage 5/6: scaffold code, deploy configs, test results
```

## Naming

`{wave}-{industry}-{l3-slug}`

- wave: `w1` | `w2` | …
- industry: `public-sector` | `education` | `nonprofit` | `hospitality` | (wave-2 additions)
- l3-slug: kebab-case of the L3 capability name, e.g. `document-intake-eligibility`

Example: `w1-education-document-intake-eligibility`

## Stage gate template (gates/stageN-to-N+1.md)

```markdown
# Gate: Stage N → Stage N+1
- **Capability:** {l3 name}
- **Industry:** {industry}
- **Date:** YYYY-MM-DD
- **Approver:** {name/role}
- **Decision:** APPROVED | REJECTED | CONDITIONAL
- **Notes:** {context, conditions if any}
- **Artifacts reviewed:** {list}
```

## Status board (maintained in README.md)

| Accelerator | Industry | L3 | Pattern | Stage | Status |
|---|---|---|---|---|---|
| (none yet) | | | | | |

Update the table as accelerators progress through stages.

## Compliance notes

All accelerators inherit the factory's mandatory constraints:
- HITL gate between every stage (no auto-advance)
- Cloud-agnostic defaults (no vendor lock-in in scaffolds)
- FedRAMP / GovRAMP / CJIS / FERPA / COPPA / PCI / GDPR awareness per industry
- Claude as default model, swappable via model gateway
