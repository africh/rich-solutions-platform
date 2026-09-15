# Wave 2 — Research Convention

## Purpose

`research/wave2/` holds the same schema as wave-1 industry JSON files, extended with any
additional fields needed for new industries.

## File naming

`research/wave2/{industry-slug}.json`

where `{industry-slug}` follows the same kebab-case convention as wave 1:
`public-sector`, `education`, `nonprofit`, `hospitality`, or new slugs for wave-2 additions.

## Schema (same as wave 1)

```json
{
  "industry": "Display Name",
  "scope_note": "…",
  "domains": [
    {
      "name": "L1 Domain",
      "groups": [
        {
          "name": "L2 Capability Group",
          "capabilities": [
            {
              "name": "L3 Capability",
              "ai_readiness": 1,
              "market_coverage": 1,
              "whitespace_score": 0,
              "rationale": "…",
              "patterns": ["P01", "P02"],
              "vendors": ["…"],
              "sources": ["…"],
              "confidence": "high | medium | low"
            }
          ]
        }
      ]
    }
  ],
  "sources": ["…"]
}
```

## Build integration

`build.py` now auto-discovers wave-2 files via `research/wave2/*.json` glob.
Drop a new industry JSON in that folder and the next build will include it.

## CI

The smoke test workflow triggers on `research/**`, so wave-2 files in `research/wave2/`
will automatically trigger a rebuild + sanity check on push.
