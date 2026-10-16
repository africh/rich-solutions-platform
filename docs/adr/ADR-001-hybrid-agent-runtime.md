# ADR-001: Hybrid cloud/local agent runtime

## Status

Proposed

## Context

The agent team runs entirely on cloud models. Much of the delivery work is bounded and mechanically checkable (test scaffolding from specs, doc formatting, log triage, extraction into drafts), and it competes for the same cloud capacity as design and review work. The operator now has a workstation that can run a large open-weight model locally through Ollama, and Hermes Agent as a local agent harness.

Local execution is cheaper per task and keeps context on the machine, but the local model is weaker, slower, and runs with access to the operator's workstation. Any adoption must keep the existing gates: branch, PR, CI, QA review, operator merge.

## Options considered

1. **Cloud only (status quo).** Simplest and strongest quality, but every task consumes cloud capacity and nothing is learned about local runtimes the product may later need.
2. **Local agents as peers.** Local agents take roles end to end, including Notion updates and PR review. Fastest, but places a weaker model in judgment roles and gives a workstation process broad write access to shared state.
3. **Hybrid, cloud-governed (chosen).** Cloud agents keep judgment roles and route bounded, checkable tasks to a sandboxed local agent. Local output enters only as `runtime:local` PRs, reviewed by the QA Reviewer and merged by the operator. Task classes move to local only after passing an evaluation gate.

## Decision

Adopt option 3 as described in [docs/design/hybrid-agent-runtime.md](../design/hybrid-agent-runtime.md), with the controls in [docs/design/local-agent-setup-and-governance.md](../design/local-agent-setup-and-governance.md):

- Risk tiers L0-L3; only L0 and L1 may run locally, L1 always with cloud review.
- Dedicated local-only Hermes profile, no cloud fallback, Docker terminal sandbox, minimal toolsets.
- Local agents push only through a repo-scoped GitHub App (Phase 2+); `main` protected by ruleset and CODEOWNERS.
- Phased rollout: Harden → Shadow (operator pushes) → PR flow → Automated dispatch.

## Consequences

- `AGENTS.md` needs a follow-up change (Technical Architect, after approval): `local-<role>` branch slugs, the `runtime:local` label, the `Runtime` field, and how local runs log to the Agent Handoff Log.
- Notion Sprint Board gains a `Runtime` property and the Agent Handoff Log a `Runtime` property (operator or PM to add).
- The Resource Manager takes on routing and weekly local-tier metrics.
- The QA Reviewer's load rises with local PR volume; a WIP limit of 2 open local PRs caps it.
- The workstation is not on the critical path; if it is offline, cards return to `Cloud`.
- Operator setup work: GitHub ruleset, GitHub App (Phase 2), Hermes profile and sandbox.

## Links

- Sprint Board story: TBD
- Decisions Log row: TBD (confirm ADR number against the Decisions Log before approval)
