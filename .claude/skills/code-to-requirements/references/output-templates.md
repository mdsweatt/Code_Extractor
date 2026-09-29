# Output templates

Five files, written in order to the output directory. Each stage's file is the input to
the next, so keep the headings exactly as shown: the validation stage in particular
greps for requirement IDs and the traceability table.

---

## 1. `code_inventory.md` and `code_inventory.json`

Produced by `scripts/inventory.py`. Do not hand-edit. If the script mis-parses something
(a macro-heavy signature, a K&R-style definition), add a short "Inventory corrections"
note at the top of `control_flow_analysis.md` instead.

---

## 2. `control_flow_analysis.md`

```markdown
# Control flow analysis: <system name>

Source: <paths analyzed>   Inventory: code_inventory.md

## Entry points and top-level sequence
<For each entry point (main, setup/loop, ISR): the ordered sequence of what happens,
as a numbered list. Name the functions called and the conditions that gate them.>

## Call graph
<Indented tree from each entry point. Mark recursion, mark functions reached from more
than one place, mark functions never reached (from the inventory's "never called" list).>

## Decision points
| # | Location (file:function:lines) | Condition (quoted or paraphrased from code) | Branch outcomes |
|---|---|---|---|
<Every if/switch/loop-exit that changes externally observable behavior. Skip pure
formatting branches unless they matter to the output format.>

## Loops and termination
| Location | Loop kind | Continues while | Exits when | Can it fail to terminate? |
|---|---|---|---|---|

## Error and validation paths
<How bad input, out-of-range values, and failed operations are handled. Quote the
retry/reject behavior. This section feeds the IF-THEN requirements.>

## Observations
<Dead code, unreachable branches, suspicious conditions (off-by-one, unseeded RNG,
uninitialized reads). Facts only, one line each, with location.>
```

---

## 3. `data_flow_analysis.md`

```markdown
# Data flow analysis: <system name>

Source: <paths analyzed>   Inventory: code_inventory.md

## State
| Name | Kind (global / param-by-pointer / static / EEPROM / file) | Type | Declared at | Initialized by | Read by | Written by |
|---|---|---|---|---|---|---|
<Every piece of state that outlives a single function call.>

## Inputs
| Input | Mechanism (stdin / argv / pin / bus / file / sensor) | Where read | Validation applied | Range or format accepted |
|---|---|---|---|---|

## Outputs
| Output | Mechanism (stdout / pin / bus / EEPROM / file / network) | Where written | Format or content |
|---|---|---|---|

## Transformations
<For each computed value that matters externally (score, SOC, position, checksum):
the formula as the code computes it, with the source line. Include units and constants
with their macro names.>

## Data dependencies and hazards
<Values used before set, shared globals written from multiple places, buffer bounds
versus index ranges, integer overflow candidates, precision loss. Facts with locations.>
```

---

## 4. `code_requirements.md`

```markdown
# Requirements: <system name>

Reverse-engineered from: <paths>
Analysis inputs: control_flow_analysis.md, data_flow_analysis.md
Status: DRAFT (pending validation)

## 1. Definitions
| Term | Meaning in this document |
|---|---|
| <system name> | <the program/firmware under analysis, one line> |
| shall | binding functional behavior, verifiable |
| must | binding quality/performance property, verifiable |
| Observed | behavior directly readable in the code |
| Inferred | intent read from names, comments, or unused declarations; rationale given |
<Domain terms the code uses: "prize", "cell", "board", with the code's meaning.>

## 2. System overview
<Three to six sentences. What it is, who or what interacts with it, the main loop or
lifecycle. No requirements here.>

## 3. Functional requirements
### 3.x <Feature or subsystem name>
| ID | Requirement | EARS | Source | Evidence | Confidence | Verification |
|---|---|---|---|---|---|---|
| FR-01 | WHEN ..., the <system> shall ... | Event | file.c:func:12-18 | `if (roll > MAX)` | Observed | <concrete check> |

## 4. Interface requirements
| ID | Requirement | EARS | Source | Evidence | Confidence | Verification |
|---|---|---|---|---|---|---|

## 5. Non-functional requirements
| ID | Requirement | EARS | Source | Evidence | Confidence | Verification |
|---|---|---|---|---|---|---|
<Only where the code carries evidence. An empty table with the line "No timing,
capacity, or persistence constraints are present in the code" is a valid result.>

## 6. Constraints
| ID | Requirement | Source | Evidence |
|---|---|---|---|

## 7. Assumptions and rationale notes
<Numbered, each referencing the requirement IDs it supports.>
```

Column rules:
- **Requirement**: one sentence, one `shall`/`must`, system-named, no identifiers from the code.
- **Source**: `file:function:startline-endline`. Multiple sources separated by `;`.
- **Evidence**: a fragment of the actual code, at most one line, in backticks. This is what
  makes the validator's job mechanical.
- **Verification**: an action and an expected result a tester could execute without
  reading the code.

---

## 5. `validated_requirements.md`

```markdown
# Validated requirements: <system name>

Reverse-engineered from: <paths>
Validated against: <paths, re-read during validation>
Status: VALIDATED

## 1. Validation summary
| Result | Count |
|---|---|
| Confirmed | n |
| Revised | n |
| Split | n |
| Rejected | n |
| Added during validation | n |

## 2. Definitions
<Carried forward from the draft, corrected if needed.>

## 3. System overview
<Carried forward, corrected if needed.>

## 4. Requirements
<The final tables, same layout as the draft, same section numbering (functional,
interface, non-functional, constraints). Only requirements that survived validation.
Keep original IDs for Confirmed and Revised; Split produces FR-07a/FR-07b; Added gets
the next free number. Rejected IDs are retired, never reused.>

## 5. Validation log
| ID | Result | Finding | Action taken |
|---|---|---|---|
| FR-03 | Revised | Statement said "3 dice"; code reads dice count from user, range 1-3 (BasicGame.c:playerRoll:210) | Rewrote with WHEN pattern and the actual range |
| NFR-01 | Rejected | No timing constraint exists in the code | Removed |
<One row per draft requirement. Rejections must say what evidence was missing.>

## 6. Traceability matrix
| Function (file:name) | Lines | Requirements | Classification |
|---|---|---|---|
| BasicGame.c:playGame | 405-454 | FR-02, FR-05, FR-06 | covered |
| BasicGame.c:space | 17-20 | - | helper (formatting, covered by IF-01) |
| BasicGame.c:seed | 13-16 | - | dead (never called) |
<Every function in code_inventory.json appears exactly once. Classification is one of:
covered, helper, dead, platform. "helper" and "platform" name the requirement that covers
the caller's behavior.>

## 7. Coverage gaps
<Observable behaviors found during re-reading that have no requirement, and why they were
or were not promoted to one. "None" is acceptable only after the matrix is complete.>

## 8. Observations and likely defects
<Carried forward from both analyses plus anything new. These are not requirements. Each
line: location, what the code does, why it looks unintended.>
```
