"""Pre-push checks for agent runs. Prints a Checks table and exits non-zero on any fail.

Usage: python tools/preflight.py --role <role-slug> [--base origin/main]

Deterministic team rules from AGENTS.md live here so no agent has to remember them:
branch naming, folder ownership, public-repo secret scan, and `python build.py`.
"""
import argparse, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Mirrors the folder ownership table in AGENTS.md. Paths are prefixes.
TA_SCAFFOLD = ["AGENTS.md", ".github/pull_request_template.md", ".github/CODEOWNERS",
               "docs/README.md", "docs/design/", "docs/specs/", "docs/adr/", ".claude/", "tools/"]
OWNED = {
    "technical-architect": TA_SCAFFOLD,
    "enterprise-architect": ["docs/togaf/", "docs/adr/"],
    "business-analyst": ["docs/requirements/"],
    "project-manager": ["docs/vision/"],
    "developer": ["src/", "tests/", "force-app/", "sfdx-project.json", "packages/"],
    "qa-reviewer": [],
    "resource-manager": [],
}
ALEX_ONLY = ["README.md", "GOAL.md", "LICENSE", "build.py", "template.html",
             "whitespace-atlas.html", "research/", "accelerators/", ".github/workflows/"]
BUILD_INPUTS = ["research/", "template.html", "build.py"]

SECRET_PATTERNS = {
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{30,}",
    "Anthropic/OpenAI key": r"sk-(ant-)?[A-Za-z0-9_-]{20,}",
    "Slack token": r"xox[abprs]-[A-Za-z0-9-]{10,}",
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "Private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "Notion integration secret": r"(secret_|ntn_)[A-Za-z0-9]{30,}",
    "Notion collection id": r"collection://[0-9a-f-]{32,36}",
    "Salesforce org id": r"\b00D[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?\b",
}

rows = []


def check(step, requirement, ok, evidence):
    verdict = "pass" if ok is True else "fail" if ok is False else "unresolved"
    rows.append((step, requirement, verdict, evidence))


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def owned_by(path, prefixes):
    return any(path == p or (p.endswith("/") and path.startswith(p)) for p in prefixes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True, choices=sorted(OWNED))
    ap.add_argument("--base", default="origin/main")
    a = ap.parse_args()

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    check("branch", f"named agent/{a.role}/<story-id>",
          bool(re.fullmatch(rf"agent/{re.escape(a.role)}/[A-Za-z0-9._-]+", branch)), branch)

    diff = git("diff", "--name-only", f"{a.base}...HEAD")
    if diff.returncode != 0:
        check("diff", f"changes computable against {a.base}", None, diff.stderr.strip()[:200])
        changed = []
    else:
        # Include uncommitted work so the check runs on what is about to be committed too.
        local = git("diff", "--name-only", "HEAD").stdout.split()
        changed = sorted(set(diff.stdout.split()) | set(local))
    check("diff", "branch has changes", bool(changed), f"{len(changed)} file(s)")

    outside = [p for p in changed if not owned_by(p, OWNED[a.role])]
    alex = [p for p in outside if owned_by(p, ALEX_ONLY)]
    check("ownership", "only touches folders this role owns", not outside,
          "ok" if not outside else ", ".join(outside[:10]))
    if alex:
        check("ownership", "Alex-owned files need an Operator Inbox decision", None, ", ".join(alex))

    added = git("diff", f"{a.base}", "--unified=0", "--no-color").stdout
    added_lines = [l[1:] for l in added.splitlines() if l.startswith("+") and not l.startswith("+++")]
    hits = sorted({name for name, pat in SECRET_PATTERNS.items()
                   for l in added_lines if re.search(pat, l)})
    check("secrets", "no secrets or private ids (repo is public)", not hits,
          "clean" if not hits else "matched: " + ", ".join(hits))

    if any(owned_by(p, BUILD_INPUTS) for p in changed):
        atlas = ROOT / "whitespace-atlas.html"
        before = atlas.read_bytes() if atlas.exists() else None
        r = subprocess.run([sys.executable, "build.py"], cwd=ROOT, capture_output=True, text=True)
        if before is not None:
            atlas.write_bytes(before)  # build output is CI's job; keep the tracked file untouched
        tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
        check("build", "`python build.py` succeeds", r.returncode == 0, tail[0][:200])
    else:
        check("build", "`python build.py` succeeds", True, "skipped: no build inputs changed")

    print("| Step | Requirement | Verdict | Evidence |")
    print("|---|---|---|---|")
    for s, req, v, ev in rows:
        print(f"| {s} | {req} | {v} | {ev.replace('|', '/')} |")
    failed = [r for r in rows if r[2] == "fail"]
    print(f"\npreflight: {len(rows) - len(failed)}/{len(rows)} not failing")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
