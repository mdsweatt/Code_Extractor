# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [crewAI](https://docs.crewai.com) pipeline that reverse-engineers natural-language requirements from C source code. Five LLM agents run sequentially: parse the code into an AST, analyze control flow, analyze data flow, synthesize requirements, then validate the requirements against the original code. The input is whatever C files sit in `code_repository/`; the outputs are markdown/JSON files written to the repo root.

## Commands

Python >=3.10,<3.13, managed with `uv`. There is no `.venv` checked in and no test suite or linter configured.

```bash
crewai install            # or: uv sync  — creates .venv and installs crewai[tools]
crewai run                # or: uv run run_crew  — runs the full pipeline
uv run replay <task_id>   # re-run from a specific task of the last kickoff
uv run train <n_iter> <out_file>
uv run test <n_iter> <openai_model_name>
```

Requires a `.env` at the root with `OPENAI_API_KEY` (not committed). All five agents use `gpt-4o-mini`; the Gemini and Ollama `LLM` objects at the top of `crew.py` are defined but unused.

## Architecture

**Pipeline wiring lives in two places that must agree.** `src/code_extractor_crew/config/agents.yaml` and `tasks.yaml` define role/goal/backstory and task descriptions. `src/code_extractor_crew/crew.py` binds each YAML entry to an `@agent` / `@task` method, attaches tools, and can override YAML fields. The `@CrewBase` decorator auto-collects the decorated methods into `Crew(agents=..., tasks=..., process=Process.sequential)`. Task order is method definition order in `crew.py`. `main.py` is a thin entrypoint mapped to console scripts in `pyproject.toml`.

**Output files come from `tasks.yaml`.** Each task's `output_file` is set in YAML, and `crew.py` no longer overrides any of them. Python `Task(...)` kwargs win over YAML, so if you add an override there it will silently shadow the YAML name. Outputs land in the repo root:

| Task | Output |
|---|---|
| parse_code | `ast.json` |
| analyze_control_flow | `control_flow_analysis.md` |
| analyze_data_flow | `data_flow_analysis.md` |
| synthesize_requirements | `code_requirements.md` |
| validate_requirements | `validated_requirements.md` |

The `report.md` at the root is a leftover from before the two control-flow/synthesis tasks were un-collided; it will not be regenerated.

**Tool and knowledge inputs:**
- `DirectoryReadTool` reads `code_repository/` at the repo root, resolved from `crew.py`'s own location (`REPO_ROOT`), so it works regardless of the working directory.
- `PDFKnowledgeSource(file_paths=['37_Requirements_10_Best_Practices.pdf'])` resolves relative to the top-level `knowledge/` directory per crewAI convention. Only `requirement_synthesizer` receives it.
- `config/tools.yaml` is not referenced by any code; it is dead config.
- The `inputs={'topic': 'AI LLMs'}` passed from `main.py` is template leftover. No task or agent template interpolates `{topic}`.

## Repo layout beyond `src/`

- `code_repository/` — the C input for the next run (currently `BasicGame.c`).
- `Reports/` — archived results from past runs on other codebases (a BMS Arduino repo, `diyBMS`, a set of C exercise files). Each folder holds the input code plus the four output files. Reference material only; don't edit as code.
- `Agents.csv`, `Definitions.xlsx` — early design notes for a different five-agent concept (Code Analyst, Contextualizer, Documentation Specialist, Requirement Writer, Reviewer). They do not match the implemented agents in `agents.yaml`.
- `knowledge/user_preference.txt` — crewAI template boilerplate, unused.

## Interlock hooks

`.claude/settings.json` registers SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/Stop/SessionEnd hooks that shell out to `node $INTERLOCK_HOME/bin/interlock.js`. `INTERLOCK_HOME` and OTEL telemetry env vars are set in the gitignored `.claude/settings.local.json`. `interlock/config.json` classifies tool calls into stages (implement / run-crew / verify) and prompts into categories; session and run logs land in `interlock/sessions/` and `interlock/runs/`. If the hooks error, the cause is almost always a missing or stale `INTERLOCK_HOME`.
