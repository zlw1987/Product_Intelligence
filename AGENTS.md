# AGENTS.md — Product Intelligence Codex bridge

This repository's durable AI operating contract is `CLAUDE.md`.

For every Codex coding session in this repository:

1. Read this file completely.
2. Read `CLAUDE.md` completely and treat its rules as binding.
3. Read `docs/PRODUCT_INTELLIGENCE_STATUS.md` completely.
4. Read the relevant canonical sections of `docs/PRODUCT_INTELLIGENCE_PLAN.md`
   before implementing anything.
5. Inspect the actual repository and relevant tests before making changes.

If the repository, tests, STATUS, CLAUDE, or PLAN materially disagree about
architecture, phase state, or capability, STOP and report the conflict before
changing anything. Do not silently resolve it.

Additional Codex/Windows execution rules:

- This development machine is Windows. Prefer PowerShell-native commands.
- Do not assume Bash-only syntax such as heredocs, `ls -la`, `grep`, or `head`.
- If an `apply_patch` tool is unavailable, do not repeatedly retry it. Use a
  PowerShell here-string with `Set-Content` / `[System.IO.File]::WriteAllText`,
  or a narrow Python file edit instead.
- Do not modify tests merely to make a failing implementation pass.
- Do not commit, push, deploy, or change external infrastructure unless the
  user explicitly asks.
- Preserve all frozen Product Intelligence phase semantics and safety
  boundaries described in `CLAUDE.md`, STATUS, and PLAN.
- At task completion, run the relevant regression tests and report the exact
  test result. For broad changes, use the validation commands documented in
  `CLAUDE.md`.

**Bridge reminder (Codex harness only):**
Do not use `git restore`, `git reset`, `git checkout`, `git stash`, or
`git clean` unless explicitly authorized. The Codex harness is untracked
and should be modified via direct file replacement only.
