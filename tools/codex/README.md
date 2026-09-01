# Product Intelligence — Codex local-model setup

## Interactive launcher

From the repository root:

```cmd
tools\codex\codex-pi.cmd qwen
tools\codex\codex-pi.cmd minimax
tools\codex\codex-pi.cmd nemotron
```

No argument defaults to Qwen3.6:

```cmd
tools\codex\codex-pi.cmd
```

## v4: explicit model lock

Codex `/model` selections can persist outside the current interaction and can
override what a profile would otherwise select.

To make the launcher deterministic, v4 passes both:

```text
--profile <profile-name>
-m <exact-model-id>
```

for every qualified local implementer.

Current mappings:

```text
qwen
  profile: qwen-local
  model:   Qwen3.6-27B-262K

minimax
  profile: b300-minimax-thinking
  model:   minimax-m2.7-thinking

nemotron
  profile: b300-nemotron
  model:   nemotron-3-super
```

This means a prior `/model` choice such as an OpenAI GPT model should not
silently replace the Product Intelligence implementer selected by the launcher.

## Approval mode: Auto Review

Interactive sessions continue to use:

```text
--approve-for-me
```

The launcher does not use:

```text
--dangerously-bypass-approvals-and-sandbox
```

and it fails closed if the resolved Codex build does not advertise
`--approve-for-me`.

## Executable discovery

`resolve-codex.cmd` is unchanged. It selects the newest usable Codex Desktop
build instead of relying on a stale fixed build-hash path.

## MiniMax shim

MiniMax Thinking still uses the narrow localhost compatibility shim on port
18081. The launcher starts it on demand only when MiniMax is selected.

## Verification

`verify-codex-pi.cmd` is intentionally unchanged. Its read-only smoke tests
continue using `--ask-for-approval never`.

## What v4 does not change

This update does not modify:

- `%USERPROFILE%\.codex\config.toml`
- any `*.config.toml` model profile
- plugins / Apps settings
- Windows environment variables
- the 18080 LiteLLM proxy
- scheduled tasks
- `AGENTS.md`
- `CLAUDE.md`
- Product Intelligence source code or tests

## Rollback

Restore the previous:

- `tools\codex\codex-pi.cmd`
- `tools\codex\README.md`

No user-level Codex configuration needs to be restored.
