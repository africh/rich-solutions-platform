# Rich Solutions Platform

A continuously built library of solution accelerators for whitespace areas defined from an industry capability model.

The platform maps where AI is ready to do real business work but market coverage is still low, then turns those gaps into human-gated, reusable solution paths. Each accelerator is grounded in the [Whitespace Atlas](whitespace-atlas.html) — an interactive capability map built from a 14-pattern agentic library, a six-stage HITL solution path, and a cloud-agnostic, compliance-aware software factory.

## Wave 1 industries

- **Public Sector** — `research/public-sector.json`
- **Education** — `research/education.json`
- **Nonprofit** — `research/nonprofit.json`
- **Hospitality** — `research/hospitality.json`
- **Software factory** — `research/factory.json`

## Scoring model

```
Whitespace Score = AI Readiness × (6 − Market Coverage)
```

- **Market Coverage** (1–5): how saturated the market is for a given business capability.
- **AI Readiness** (1–5): how well the capability is suited to current agentic AI.
- **Whitespace Score**: higher means more open territory for a solution.

Bands: **High ≥ 16**, **Medium 9–15**, **Low ≤ 8**.

## Repository layout

| Path | Description |
|---|---|
| `GOAL.md` | Scoring rubric, 14-pattern agentic library, and six-stage HITL path |
| `build.py` | Build script that recomputes whitespace scores and injects data into the template |
| `template.html` | Presentation template for the Whitespace Atlas |
| `whitespace-atlas.html` | Pre-built interactive Whitespace Atlas |
| `research/` | Industry and factory research data (JSON) |

## How to rebuild the Atlas

```bash
python build.py
```

The build script reads the JSON files in `research/`, recomputes whitespace scores, and regenerates `whitespace-atlas.html` from `template.html`.

## Continuously building accelerators

Each whitespace opportunity is treated as a candidate accelerator. The platform is designed to grow over time: new industries, new capability patterns, and new HITL stages can be added without changing the core scoring model or the six-stage solution path.
