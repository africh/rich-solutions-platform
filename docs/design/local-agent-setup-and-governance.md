# Local agent setup and governance guide

Operator guide for the local tier in [hybrid-agent-runtime.md](hybrid-agent-runtime.md). Written for Windows 11 with Ollama, Hermes Agent (v0.22.x), Docker Desktop and the GitHub CLI. Commands are PowerShell unless marked otherwise.

Do the parts in order. Parts 1-4 are Phase 0 (harden); part 6 must pass before any local run touches the repo.

> Public repo reminder: nothing produced by these steps (tokens, App IDs, private keys, local paths with usernames) goes into this repository.

---

## Part 1 - Ollama: local-only inference

1. **Keep Ollama on loopback.** Leave `OLLAMA_HOST` unset (default `127.0.0.1:11434`) or set it explicitly. Never `0.0.0.0`. Check:
   ```powershell
   Get-NetTCPConnection -LocalPort 11434 -State Listen | Select-Object LocalAddress
   ```
   Expected: `127.0.0.1` only.

2. **Set server limits for one agent at a time** (user environment variables, then restart Ollama):
   ```powershell
   [Environment]::SetEnvironmentVariable('OLLAMA_NUM_PARALLEL','1','User')
   [Environment]::SetEnvironmentVariable('OLLAMA_MAX_LOADED_MODELS','1','User')
   [Environment]::SetEnvironmentVariable('OLLAMA_CONTEXT_LENGTH','32768','User')
   ```
   32K is a starting point; raise it only if evaluations show the agent running out of context. Every extra token of context costs VRAM and pushes more layers to CPU.

3. **Pin and record the model.** Ollama tags are mutable. Record the `ID` column from `ollama list` in the evaluation log. Do not `ollama pull` an existing tag again without re-running the evaluation set (part 7). Pull only from the official Ollama library and record the model licence.

4. **Measure throughput** so routing decisions use real numbers:
   ```powershell
   ollama run <model> --verbose "Write a 200-word summary of what a git worktree is."
   ollama ps
   ```
   Note `eval rate` (tokens/s) and the CPU/GPU split in `ollama ps`. If the split is far from 100% GPU, also benchmark a smaller tool-capable model that fits entirely in VRAM at 4-bit and compare them on the evaluation set.

## Part 2 - Hermes: a dedicated local-only profile

Your default Hermes profile points at a **cloud** provider and has broad toolsets (browser, computer use, web search). Leave it for personal use. Build agents get their own profile, created empty so no cloud keys are copied in.

1. **Create the profile** (no `--clone`, so `.env` and cloud credentials are not copied):
   ```powershell
   hermes profile create rslocal --description "Rich Solutions local build agent. Bounded L0/L1 tasks from a task card; local model only; output is a branch in its own worktree."
   hermes -p rslocal config path
   hermes -p rslocal config env-path
   ```
   Open the `.env` it prints and confirm it holds no API keys.

2. **Point it at Ollama only:**
   ```powershell
   hermes -p rslocal config set model.provider custom
   hermes -p rslocal config set model.base_url http://127.0.0.1:11434/v1
   hermes -p rslocal config set model.default <model>
   hermes -p rslocal config set model.ollama_num_ctx 32768
   ```

3. **No fallback, no borrowed logins, no telemetry upload:**
   ```powershell
   hermes -p rslocal fallback list          # must say "No fallback providers configured."
   hermes -p rslocal config set auth.adopt_external_logins false
   hermes -p rslocal config set telemetry.shared_metrics.send false
   ```
   `adopt_external_logins` defaults to `true`, which lets Hermes borrow your Claude Code and Codex logins. For a build agent that is both a data-egress path and a privilege escalation.

4. **Lock down toolsets.** Keep only what a coding task needs:
   ```powershell
   hermes -p rslocal tools disable web browser computer_use image_gen tts vision connections cronjob delegation
   hermes -p rslocal tools list
   ```
   Expected enabled: `terminal`, `file`, `code_execution`, `todo`, `skills`, `memory`, `session_search`, `clarify`. Re-enable `delegation` or `kanban` only in Phase 3, and never `web`/`browser` for a profile that writes code (prompt-injection path).

5. **Keep instruction files protected.** In the profile's `config.yaml`, under `security:`, make sure `protected_instruction_files: true` (the default). This forces human approval before the agent edits `AGENTS.md`, `SOUL.md` and similar files, even under `--yolo`.

6. **Give the profile its rules.** Hermes injects the `AGENTS.md` of the working directory automatically. Put local-agent specifics in the profile's `SOUL.md`:
   ```text
   You are a local build agent for the Rich Solutions Platform.
   - Work only on the task card you were given and only in the files it lists.
   - Never push, never open PRs, never edit .github/, AGENTS.md, build.py or Alex-owned paths.
   - Never write secrets, client names or engagement details to any file.
   - Finish by running the card's acceptance command and writing RUN_REPORT.md in the worktree root
     (not committed) with: what you changed, commands run, acceptance output, open questions.
   - If the card is ambiguous or the acceptance check fails twice, stop and say BLOCKED with the reason.
   ```

## Part 3 - Sandbox: run tools in Docker, not on the host

With `terminal.backend: local`, agent shell commands run as you, with your `gh` login (which has `repo` and `workflow` scopes) and everything else on the machine. Move build agents into a container.

1. **Set the Docker backend** in the `rslocal` profile's `config.yaml` (`hermes -p rslocal config edit`):
   ```yaml
   terminal:
     backend: "docker"
     cwd: "/workspace"
     timeout: 180
     lifetime_seconds: 900
     docker_image: "nousresearch/hermes-sandbox:desktop"
     docker_mount_cwd_to_workspace: true   # mounts ONLY the directory you launch from
     docker_run_as_host_user: true
   ```
   Launch every run from inside a dedicated worktree (part 5) so the mount is that worktree and nothing else. Do not forward `GH_TOKEN`, `GITHUB_TOKEN` or cloud API keys into the container.

2. **Later (Salesforce phase):** build a project image `rs-agent-sandbox` with Python, the Salesforce CLI and Node pinned, and switch `docker_image` to it. Keep it in a separate, operator-owned location until an ADR places it in the repo.

3. **Headless runs bypass approvals.** `hermes -z` (one-shot) auto-approves dangerous commands. Only run headless with the Docker backend and the locked-down toolsets above. Never use `--yolo` interactively.

4. **Optional egress firewall.** `hermes egress setup` installs iron-proxy to restrict what leaves the sandbox. Worth enabling before Phase 3 automation.

5. **Supply-chain check** after any Hermes update, plugin or MCP server change:
   ```powershell
   hermes -p rslocal security
   hermes -p rslocal hooks list
   ```

## Part 4 - GitHub: identity and guardrails

Phase 1 needs **no** agent credentials: the agent commits locally and you push. Set up the guardrails now anyway; they protect against every agent, cloud or local.

1. **Ruleset on `main`** (Settings → Rules → Rulesets → New branch ruleset, target `main`):
   - Require a pull request before merging, 1 approval, require review from Code Owners.
   - Do **not** require `build-smoke-test` yet. It only runs when `research/`, `template.html` or `build.py` change, so a docs-only PR would wait forever on a check that never reports, and it currently fails on `main` (placeholder `research/*.json`). Add a required check once there is one that runs on every PR, e.g. a workflow without path filters or a skip job that reports success for unrelated paths. `.github/workflows/` is operator-owned, so that is your decision.
   - Block force pushes; restrict deletions.
   - Bypass list: you only.

2. **Phase 2 identity: a GitHub App, not a PAT on your account.** PRs opened with your own token show you as author, which breaks "someone else reviews". Create a GitHub App (Settings → Developer settings → GitHub Apps), e.g. `rs-local-agent`:
   - Repository permissions: Contents read/write, Pull requests read/write, Metadata read. **No** Workflows, Administration, Secrets or Actions write.
   - Install it on this repository only.
   - Keep the private key out of the repo: store it with `hermes secrets` (Bitwarden or 1Password source) or Windows Credential Manager. Mint short-lived installation tokens per run; never put a long-lived token in the container.
   - Optional second ruleset: the App may create branches only matching `agent/local-*`.

3. **Labels:** create `runtime:local` so local PRs are easy to filter and to route to the QA Reviewer.

## Part 5 - Running a task (Phase 1, operator-driven)

1. **Write a task card** (in the Sprint Board story or a local file outside the repo):
   ```markdown
   Story: SB-<n> (link)
   Tier: L1
   Goal: <one sentence>
   Spec: docs/specs/SB-<n>.md (ADR-<nnn> Approved)
   Files in scope: <explicit list or glob>
   Out of scope: everything else
   Acceptance command: python build.py && <tests>
   Done when: acceptance command exits 0 and RUN_REPORT.md is written
   ```
   If you cannot write the acceptance command, the task is not L1 (see routing rules).

2. **Create an isolated worktree** outside the main checkout:
   ```powershell
   git -C "C:\RS Platform" fetch origin
   git -C "C:\RS Platform" worktree add "C:\RS Platform-wt\SB-<n>" -b agent/local-developer/SB-<n> origin/main
   ```

3. **Run the agent from that worktree** (interactive, so approvals stay on):
   ```powershell
   hermes -p rslocal --in "C:\RS Platform-wt\SB-<n>" chat
   ```
   Paste the task card as the first message. For unattended L0 work use one-shot with a usage report:
   ```powershell
   hermes -p rslocal --in "C:\RS Platform-wt\SB-<n>" -z "<task card>" --usage-file "$env:TEMP\SB-<n>-usage.json"
   ```

4. **Review before anything leaves the machine:**
   ```powershell
   git -C "C:\RS Platform-wt\SB-<n>" status
   git -C "C:\RS Platform-wt\SB-<n>" diff origin/main --stat
   python "C:\RS Platform-wt\SB-<n>\build.py"
   ```
   Reject the run if any file outside "Files in scope" changed, if the diff contains anything secret-shaped, or if the acceptance command fails.

5. **Integrate:** push the branch, open the PR with the template, add `runtime:local`, paste the run report (Hermes version, profile, model name + ID, usage JSON totals, acceptance output). The QA Reviewer reviews it like any other PR.

6. **Log it:** one Agent Handoff Log entry, `Run = Local Developer - YYYY-MM-DD`, `Runtime = Local`. Add the task and result to the golden set if it is a good example.

7. **Clean up** after merge or rejection: `git worktree remove "C:\RS Platform-wt\SB-<n>"` (and `hermes worktree` to audit stale ones).

## Part 6 - Verification checklist (run before first use and after any update)

| # | Check | How | Pass |
|---|---|---|---|
| 1 | Provider is local | `hermes -p rslocal status` | Provider shows custom / `127.0.0.1:11434`; no cloud provider |
| 2 | No fallback | `hermes -p rslocal fallback list` | None configured |
| 3 | Inference really is local | Run `hermes -p rslocal -z "Reply OK" --usage-file u.json`, then `ollama ps` | Model loaded in Ollama; `u.json` names the local model; cost 0 |
| 4 | No borrowed logins | `hermes -p rslocal config get auth.adopt_external_logins` | `false` |
| 5 | Toolsets minimal | `hermes -p rslocal tools list` | No `web`, `browser`, `computer_use` |
| 6 | Sandbox active | In a chat, ask the agent to run `whoami; ls /; gh auth status` | Runs in container; `gh` not logged in; only the worktree under `/workspace` |
| 7 | Ollama loopback only | Part 1 step 1 | `127.0.0.1` |
| 8 | Instruction files gated | Ask the agent to append a line to `AGENTS.md` | Approval prompt appears; decline it |
| 9 | `main` protected | Try `git push origin HEAD:main` from a test worktree | Rejected by ruleset |

Optional hard guarantee for check 3: a Windows Firewall outbound rule that blocks the Hermes Python runtime except to `127.0.0.1`. Make that change yourself; it is a system security setting.

## Part 7 - Governance operations

**Roles**

| Who | Owns |
|---|---|
| Alex | Kill switch, merges, ADR approval, promotion/demotion of task classes, GitHub App and its keys |
| Resource Manager (cloud) | Sets `Runtime` on stories using the routing rules; weekly local-tier metrics |
| QA Reviewer (cloud) | Reviews every `runtime:local` PR; files Defects for them, marked local (Defects has no `Runtime` property yet; until it is added, start Steps / Evidence with `Runtime: Local`) |
| Local agent (`rslocal`) | Executes one card at a time; writes RUN_REPORT.md; stops on BLOCKED |

**Kill switch** (any one is enough, from least to most drastic):
```powershell
hermes -p rslocal pause --reason "<why>"     # stops new cron/kanban/gateway work; resume with: hermes -p rslocal resume
ollama stop <model>                           # unloads the model
```
Then on GitHub: suspend the `rs-local-agent` App installation (Phase 2+).

**Audit trail**
- Hermes: `hermes -p rslocal sessions list`, `hermes -p rslocal logs --since 24h`, `hermes -p rslocal insights`.
- Per run: usage JSON, RUN_REPORT.md content in the PR body, Handoff Log entry.
- Back up the profile before upgrades: `hermes -p rslocal backup`.

**Evaluation set** (kept outside the public repo until it is scrubbed): for each task class, 10+ cards with known-good outputs. Re-run after any change to model, quantisation, context size, Hermes version or SOUL.md. Promotion and demotion thresholds are in the design doc, section 5.

**Weekly review** (Resource Manager drafts, Alex decides): local runs, acceptance rate, QA findings per PR, rework cycles, governance violations, recommended promotions/demotions → Decisions Log.

**Change control:** changes to the `rslocal` profile config, SOUL.md, sandbox image or model are recorded as a Decisions Log row before use. Anything that changes `AGENTS.md` or the routing tiers needs an ADR.

## Part 8 - Phase 3 automation (later)

Only after Phase 2 exit criteria are met:

1. Enable the `kanban` toolset on a separate `rsdispatch` profile (not on `rslocal`).
2. A dispatch bridge (Hermes cron job or a small script) reads Sprint Board stories with `Status = Ready for Dev` and `Runtime = Local`, creates `hermes kanban` tasks assigned to `rslocal`, and writes the PR link and run report back. It uses a Notion integration that can read the Sprint Board and append to the Handoff Log and Operator Inbox only.
3. Keep `kanban.review_dispatch` on if you like, but treat its verdict as advisory; the QA Reviewer and CI are the gates.
4. WIP limit: no more than 2 open `runtime:local` PRs. The bridge stops dispatching above that.
5. `hermes egress` enabled; headless runs only.
