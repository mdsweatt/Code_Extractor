---
name: code-to-requirements
description: Reverse-engineer a traceable, EARS-style requirements specification from existing source code (C, C++, Arduino .ino, and similar). Use this whenever the user asks to extract, derive, generate, recover, or document requirements, a spec, or "what this code is supposed to do" from a codebase, file, or directory, including phrasings like "write the requirements for this program", "what are the functional and non-functional requirements of this firmware", "document the behavior of BasicGame.c", or "run the code extractor". Also use it when the user wants control-flow or data-flow analysis as a step toward requirements, or wants to validate an existing requirements document against code. Replaces the crewAI pipeline in src/code_extractor_crew for interactive use.
---

# Code to requirements

Turn source code into a requirements document that a reader who has never seen the code
could use to re-implement or test the system, with every statement traceable to a line.

The pipeline has five stages, run in order. Each stage writes one file and the next stage
reads it. Do them as five distinct passes rather than one big read, because the failure
mode this skill exists to prevent is a plausible-sounding spec that quietly drifts from
the code: invented timing limits, requirements for functions that are never called,
"requirements" about the document itself. Separating analysis from synthesis, and
synthesis from validation, is what catches that drift.

## Inputs and outputs

- **Input**: a file or directory the user names. If they do not name one and the repo has
  a `code_repository/` directory, use that. Ask only if there is genuinely no candidate.
- **Output directory**: what the user names, otherwise `requirements/` under the current
  working directory (create it). The five files, in order:

| Stage | File |
|---|---|
| 1 Inventory | `code_inventory.md`, `code_inventory.json` |
| 2 Control flow | `control_flow_analysis.md` |
| 3 Data flow | `data_flow_analysis.md` |
| 4 Synthesis | `code_requirements.md` |
| 5 Validation | `validated_requirements.md` |

Exact section layouts for stages 2 to 5 are in `references/output-templates.md`. Read it
before writing stage 2 and keep it open; the validation stage depends on the draft's
column layout. Read `references/requirements-style.md` before stage 4.

## Stage 1: Inventory

Run the bundled script. It is deterministic and dependency-free, and it gives you a
checklist of every function, macro, file-scope variable, and call edge so nothing is
skipped and nothing is invented:

```bash
python3 <skill-dir>/scripts/inventory.py <input> --json <out>/code_inventory.json --md <out>/code_inventory.md
```

Then read `code_inventory.md`. Pay attention to the "never called" list: those functions
describe behavior the program does not actually have. Also read the source files
themselves, in full, now. The script is regex-based, so for macro-heavy or unusual code
verify its function list against what you see and note corrections at the top of the
control-flow file.

## Stage 2: Control flow

Trace execution from each entry point (`main`, or `setup`/`loop`, or interrupt handlers).
Write `control_flow_analysis.md` following the template. The things that matter most
downstream are the decision-point table and the error/validation-path section: every
`if` that gates an observable behavior becomes a WHEN or IF-THEN requirement later, and
every retry loop on bad input becomes an unwanted-behavior requirement.

Quote conditions from the code rather than paraphrasing loosely. `if (score >= 200)` is
evidence; "when the score is high enough" is not.

## Stage 3: Data flow

Write `data_flow_analysis.md`. Enumerate state that outlives a function call, every
input with its validation and accepted range, every output with its format, and the
formulas behind computed values. Cite the line for each constant and read the macro
value, not just the macro name. This stage is where you find the numbers that are
allowed to appear in requirements; if a number is not in this file, it should not be in
a requirement.

## Stage 4: Synthesize the draft

Read `references/requirements-style.md`, then write `code_requirements.md` from the two
analysis files, checking back against the source whenever a detail is uncertain.

The rules that matter most, and why:

- **EARS sentence patterns, one behavior per sentence.** A requirement with "and" in it
  is two test cases wearing one ID.
- **Name the system, not the function.** "The game shall end WHEN the checked-out score
  reaches 200" is a requirement. "The system shall end the game via `checkout()`" is a
  code comment. Function names go in the Source column, where they enable traceability
  without polluting the statement.
- **Every requirement has Source, Evidence, and Confidence.** Evidence is a fragment of
  real code. If you cannot find a fragment to quote, you are about to invent a
  requirement.
- **Numbers come from the data-flow file.** No thresholds, timings, or limits that the
  code does not contain.
- **Describe the code as it is.** Unseeded random generator, unused validation function,
  off-by-one in a loop: the requirement reflects actual behavior, and the concern goes
  in Observations. The reader is trying to learn what the software does, and a
  requirements document that silently fixes bugs lies to them.
- **Non-functional requirements only where evidenced.** `delay(1000)`, an array bound, an
  EEPROM write, a pin assignment. An empty non-functional table is a legitimate result
  for a small console program. Never write requirements about the requirements document.
- **No weak words.** The style guide has the list. "Gracefully", "responsive", and
  "appropriate" are the ones that slip through most often.

Group requirements by feature or subsystem so the document reads top-down. Aim for
completeness over brevity: a 500-line C program typically yields 15 to 40 requirements
plus a handful of interface and constraint entries.

## Stage 5: Validate against the code

This is a fresh pass, not a re-read of your own draft. Re-open the source. For each
draft requirement, go to its cited Source lines and check that the Evidence fragment is
really there and that the statement matches what the code does, including the exact
numbers and the exact trigger. Record one of:

- **Confirmed**: matches.
- **Revised**: right idea, wrong detail. Fix it and keep the ID.
- **Split**: two behaviors in one sentence. Produce `-a`/`-b` IDs.
- **Rejected**: no supporting code, or describes the document rather than the system, or
  describes behavior the code cannot exhibit (for example, a function that is never
  called). Say what evidence was missing.

Then check coverage in the other direction. Build the traceability matrix from
`code_inventory.json`: every function appears once and is either covered by at least one
requirement or classified as helper, dead, or platform with a note. Any observable
behavior you find during re-reading that has no requirement gets added with a new ID and
logged as "Added during validation".

Write `validated_requirements.md` with the summary counts, final tables, validation log,
matrix, coverage gaps, and observations. The validation log is the audit trail; a reader
should be able to see what changed between draft and final and why.

## Finishing

Tell the user where the five files are, give the confirmed/revised/rejected counts, and
call out the two or three most useful observations (dead code, likely defects, portability
issues). Do not paste the requirements into the chat; the file is the deliverable.

If the user only wants part of the pipeline (just control flow, or just validation of a
spec they already have), run that stage alone using the same templates. For validating an
existing document, treat it as the stage 4 draft and run stage 5 on it.
