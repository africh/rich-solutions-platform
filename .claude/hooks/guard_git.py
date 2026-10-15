"""PreToolUse hook: blocks git commands AGENTS.md forbids, so the rule never depends on memory.

Blocks: pushing to main, force-push, deleting branches (local or remote), and merging into main.
Exit code 2 blocks the tool call and shows stderr to the agent.
"""
import json, re, sys

try:
    cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "")
except Exception:
    sys.exit(0)

PUSH = r"\bgit\s+(-C\s+\S+\s+)?push\b[^;&|]*"
RULES = [
    (PUSH + r"(\s--force(-with-lease)?\b|\s-[a-zA-Z]*f\b|\s\+\S)", "force-push"),
    (PUSH + r"(\s--delete\b|\s-d\b|\s:\S)", "deleting a remote branch"),
    (PUSH + r"\s(\S+:)?(refs/heads/)?main\b", "pushing to main"),
    (r"\bgit\s+(-C\s+\S+\s+)?branch\b[^;&|]*\s-(d|D|-delete)\b", "deleting a branch"),
    (r"\bgh\b[^;&|]*\bpr\s+merge\b", "merging a PR"),
]

for pattern, what in RULES:
    if re.search(pattern, cmd):
        print(f"Blocked by .claude/hooks/guard_git.py: {what} is not allowed (AGENTS.md). "
              "Only Alex merges to main; no force-push or branch deletion. "
              "Raise an Operator Inbox item if you need this.", file=sys.stderr)
        sys.exit(2)
sys.exit(0)
