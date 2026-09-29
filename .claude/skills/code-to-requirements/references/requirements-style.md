# Requirements style guide

Distilled from "10 Best Practices in Writing Requirements" (Value Management Framework,
`knowledge/37_Requirements_10_Best_Practices.pdf`) and adapted for requirements that are
reverse-engineered from existing code rather than elicited from stakeholders.

## 1. Sentence structure: use EARS

Every requirement is one sentence, active voice, present tense, exactly one `shall`.
Pick the EARS pattern that matches the trigger structure in the code:

| Pattern | Syntax | Typical code shape |
|---|---|---|
| Ubiquitous | The `<system>` shall `<response>`. | Unconditional behavior, constants, always-on properties |
| Event-driven | WHEN `<trigger>`, the `<system>` shall `<response>`. | `if` on an input/event, interrupt handler, menu choice |
| Unwanted behavior | IF `<undesired condition>`, THEN the `<system>` shall `<response>`. | Error branches, validation-failure loops, bounds checks |
| State-driven | WHILE `<state>`, the `<system>` shall `<response>`. | Behavior inside a loop guarded by a state flag or mode |
| Optional feature | WHERE `<feature is present>`, the `<system>` shall `<response>`. | `#ifdef`, configuration flags, optional peripherals |

Most "general" functional requirements hide a trigger. Before writing a Ubiquitous
requirement, check whether an `if`, a loop condition, or an input actually gates it.
True Ubiquitous requirements are usually non-functional.

One requirement per sentence. No "and", "or", "also", "with" joining two behaviors.
If you need a conjunction, split the requirement; each half becomes its own test case.

Name the system consistently. Pick a short name for the thing under analysis ("the game",
"the BMS controller", "the program") in the Definitions section and use it in every
statement. Do not put function names, variable names, or types in the statement itself.
Those belong in the Source and Evidence columns. A statement that says "via the
`checkout()` function" is a description of the implementation, not a requirement, and it
breaks the moment someone renames the function.

## 2. Imperatives

- **shall**: binding functional behavior. Verifiable.
- **must**: binding quality or performance property (non-functional). Verifiable.
- **will**: statement of fact or expected occurrence. Not binding. Use in rationale, never in a requirement.
- **should**: goal or best practice. Not binding. Do not use in reverse-engineered requirements; the code either does it or it does not.

## 3. Weak words to remove

These have no measurable meaning. If one appears in a draft requirement, replace it with
the concrete condition from the code or delete the requirement:

> efficient, powerful, fast, easy, effective, reliable, compatible, normal, user-friendly,
> intuitive, few, most, quickly, versatile, robust, timely, strengthen, enhance, flexible,
> large, small, sufficient, safe, adequate, approximate, minimal impact, as appropriate,
> but not limited to, be able to, be capable of, responsive, gracefully, clear, appropriate

Also avoid: passive voice ("shall be displayed"), suggestions ("may", "might", "could"),
"TBD", and double negatives. Prefer positive phrasing: "shall reject" not "shall not accept".

## 4. Evidence discipline for reverse-engineered requirements

This is the part that differs from forward requirements engineering. The code is the
only stakeholder in the room, so:

- **Every number comes from the code.** A limit, a delay, a threshold, a count, or a range
  in a requirement must be traceable to a literal, a macro, an array size, or an
  arithmetic expression in the source. Cite it. If the code has no timing constraint,
  there is no timing requirement. Do not invent "within 2 seconds".
- **Every requirement cites a source location.** File, function, and line range. A
  requirement you cannot point at is speculation.
- **Label confidence.** `Observed` means the behavior is directly readable in the code.
  `Inferred` means you are reading intent from names, comments, or context (for example,
  a `#define` that is declared but never used, or a comment describing a feature that is
  half-implemented). Inferred requirements are allowed but must say why.
- **Document the code as it is, not as it should be.** If a function is never called, the
  program does not do what that function does. If the random generator is never seeded,
  the sequence is deterministic. Write the requirement to match actual behavior and put
  the concern in the Observations section. Requirements that describe wished-for behavior
  are the single most common failure mode of LLM-generated specs.
- **Requirements are about the system, never about the document.** "All requirements shall
  have a unique ID" is a process rule for the author, not a requirement on the software.
  Do not emit it.
- **Non-functional requirements need evidence too.** Legitimate sources: `delay()` calls and
  timer periods (timing), array sizes and `MAX` macros (capacity), validation loops
  (input robustness), `#include`s of platform headers and pin numbers (environment and
  interface), EEPROM or file writes (persistence). "Shall be compatible with standard C
  compilers" is only a requirement if something in the code actually constrains it, such
  as a non-portable call like `scanf_s`.

## 5. Supporting information

Keep each statement short and put the rest in separate fields:

- **Rationale**: one sentence on why the behavior exists, when the code or comments make it
  evident. Leave blank rather than guess.
- **Assumptions**: anything the requirement depends on that the code does not enforce.
- **Exceptions**: conditions where the requirement does not apply.
- **Verification**: the concrete check a tester would perform. Writing this often exposes a
  requirement that is not actually testable.

## 6. Identifiers and grouping

Project-unique IDs, zero-padded, grouped by type:

| Prefix | Meaning |
|---|---|
| `FR-nn` | Functional: externally observable behavior |
| `IF-nn` | Interface: user I/O formats, prompts, hardware pins, bus addresses, file formats |
| `NFR-nn` | Non-functional: timing, capacity, persistence, resource limits, where evidenced |
| `CON-nn` | Constraint: build environment, platform, libraries, non-portable calls |

Organize hierarchically by feature or subsystem, not by source file. A reader who has
never seen the code should be able to follow the document.

## 7. Traceability

Every requirement links down to code. Every function in the inventory links up to at
least one requirement, or is explicitly classed as one of:

- **helper**: internal decomposition with no externally observable behavior of its own
  (its behavior is covered by the requirement of its caller).
- **dead**: defined but never reached from an entry point. Note it in Observations.
- **platform**: framework-mandated entry point such as `setup()`/`loop()` (still needs a
  requirement for what it does, but the existence of the function is not a requirement).

The traceability matrix in the validated output is where this gets checked. Gaps in either
direction (behavior with no requirement, requirement with no code) are findings.
