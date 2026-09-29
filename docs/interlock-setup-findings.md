# Interlock hook failure on Kara's machine: findings and fixes

Date: 2026-09-28 (evening, US Eastern; timestamps in the Record are UTC, so they read 2026-09-29).

## Summary

Every Claude Code hook in this repo was failing with `Cannot find module
'.../Code_Extractor/bin/interlock.js'`. The cause was a missing per-machine settings file, so
`INTERLOCK_HOME` was unset and the hooks looked for Interlock inside this repo. Creating
`.claude/settings.local.json` fixed it without a restart. Telemetry was already working because its
settings live in the user-level file, not the project one.

Getting a machine fully recording takes settings in two places:

| File | Scope | Committed | What it has to hold |
|---|---|---|---|
| `~/.claude/settings.json` | User, every project on the machine | No | The seven telemetry variables |
| `.claude/settings.local.json` | This copy of this repo | No (gitignored) | `INTERLOCK_HOME`, `INTERLOCK_ACTOR` |
| `.claude/settings.json` | Project, every clone | Yes | The six hook entries and the git permission rules |

## The error

```
Stop hook error: Failed with non-blocking status code
Error: Cannot find module '/Users/karasweatt/mikescorner/Code_Extractor/bin/interlock.js'
```

It appeared on all six hook events (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop,
SessionEnd). It is non-blocking: work continues, but nothing the hooks supply is recorded.

## Cause

The hooks in `.claude/settings.json` run:

```
node "${INTERLOCK_HOME:-$CLAUDE_PROJECT_DIR}/bin/interlock.js" hook <Event>
```

With `INTERLOCK_HOME` unset, the path falls back to the project directory, which has no `bin/`.

`INTERLOCK_HOME` is meant to come from `.claude/settings.local.json`. That file is gitignored, so it
never arrives with a clone, and it did not exist on this machine when the session started. It was
not exported in any shell profile either. Interlock itself was installed and working at
`~/mikescorner/interlock`.

Earlier sessions the same evening did record with `actor: kara`, so both values were available to
them. We did not establish how, or when the file went missing.

## What was changed

### Project-local settings (this session)

Created `.claude/settings.local.json`:

```json
{
  "env": {
    "INTERLOCK_HOME": "/Users/karasweatt/mikescorner/interlock",
    "INTERLOCK_ACTOR": "kara"
  }
}
```

- `INTERLOCK_HOME` must be an absolute path. The hook command quotes it, so `~` is not expanded.
- `INTERLOCK_ACTOR` is what names the person on each session row. It is also required by
  `open-run` and `close-run`, which refuse to guess it.
- Claude Code picked the file up mid-session. No restart was needed.

### User settings (earlier the same evening)

`~/.claude/settings.json` holds the telemetry environment. It was last modified at 22:45 local, in a
session before this one:

```
CLAUDE_CODE_ENABLE_TELEMETRY=1
OTEL_LOGS_EXPORTER=otlp
OTEL_EXPORTER_OTLP_PROTOCOL=http/json
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:47311
OTEL_LOG_USER_PROMPTS=1
OTEL_LOG_TOOL_DETAILS=1
OTEL_LOGS_EXPORT_INTERVAL=2000
```

These have to live here rather than in `.claude/settings.local.json`. Interlock's quick start notes
that on Claude Code 2.1.282 and later the telemetry values in the project-local file are ignored;
this machine runs 2.1.284. That is why sessions were metered even while the hooks were failing.

Because this file is user-wide, every Claude Code session on this machine, in any project, exports
to the local collector with prompt text included. The text stays in `~/.interlock/prompts/` (mode
0600) and never enters a repo, but the scope is wider than this project.

### Project settings (commit `65c1f3f`, merged in PR #2)

`.claude/settings.json` gained permission rules so the logs can be committed without prompts:

```json
"permissions": {
  "allow": ["Bash(git add interlock/*)", "Bash(git commit *)", "Bash(git push*)"]
}
```

### Runs and the Record (this session)

| Action | Result |
|---|---|
| `close-run TEST-0001` | Closed as kara at 03:13 UTC |
| `open-run KNS-0003 --kind ops` | Open; `interlock/.current_run` points to it |
| Commit `fca94d9` | 9 log files, 75 rows, on branch `chore/record-interlock-kns-0003` |

`interlock verify` passed on all 12 hash chains after each step.

## What was recovered and what was lost

Session `cb2216a5` is the one that ran with broken hooks.

| Data | Source | Outcome |
|---|---|---|
| Prompts, token usage, cost | Telemetry | Recovered. The collector spooled 23 records and replayed them once the first hook got through. |
| Tool-call events before the fix | Hooks | Lost. There is no other source for them. |
| Tool-call events after the fix | Hooks | Recorded normally. |
| Actor on the session row | Hook payload | Recorded as `null`. Rows are append-only, so it stays that way. |
| Run on the session row | Run marker | `TEST-0001`, the run open when the row was written. |

Spooled telemetry is only kept at full fidelity for about ten minutes, so a session whose hooks stay
broken for longer will not backfill this cleanly.

## Setting up another machine

1. Clone Interlock and note its absolute path.
2. Put the seven telemetry variables in `~/.claude/settings.json` under `env`.
3. Create `.claude/settings.local.json` in this repo with `INTERLOCK_HOME` and `INTERLOCK_ACTOR`.
4. Start a session and check that a new file appears in `interlock/sessions/`.
5. Open a run before starting work: `node "$INTERLOCK_HOME/bin/interlock.js" open-run <ID> --kind <kind>`.

`interlock install --actor <name>` automates step 3 and re-merges the hook entries. It also writes
the telemetry variables to the project-local file, where current Claude Code versions ignore them,
so step 2 is still needed by hand.

If nothing records, check in this order:

| Check | Command |
|---|---|
| Is a run open? | `cat interlock/.current_run` |
| Is the collector up? | `lsof -nP -iTCP:47311 -sTCP:LISTEN` |
| Is `INTERLOCK_HOME` set? | `cat .claude/settings.local.json` |
| Is telemetry on? | `grep CLAUDE_CODE_ENABLE_TELEMETRY ~/.claude/settings.json` |
| What did the collector see? | `tail ~/.interlock/collector.log` |

Rows are written when a prompt finishes, not as it runs, so a session file lags the work by one turn.

## Open items

- `CLAUDE.md` says the telemetry variables are set in `.claude/settings.local.json`. On this
  machine they are in the user settings, for the reason above.
- The hook fallback to `$CLAUDE_PROJECT_DIR` turns a missing variable into a misleading
  module-not-found error. That is Interlock's wiring, not this repo's.
- `.DS_Store` files are not gitignored; one is tracked and shows as modified.
- Session `cb2216a5` kept writing rows after commit `fca94d9`, so the Record needs one more commit
  when the session ends.
