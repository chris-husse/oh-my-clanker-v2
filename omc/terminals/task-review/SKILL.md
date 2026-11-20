---
name: task-review
description: "Review one task's commits against its plan task and the record: approved, or the changes it needs."
---

# task-review

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it reads one task of
the plan, the record's sections it serves and the task's commits, and ends with one `OUTCOME` line: `approved`, or
the findings that need a change. It fixes nothing: a finding is the task terminal's to fix, run again by the
orchestrator with it.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `plan:` the plan's path. `task:` the task's number.
`commits:` the task's commits, as the task terminal returned them, oldest first; `none` when the task made no commit:
then every step is read against the tree at `HEAD`, a step already there is named as done before, and a step nowhere
is a step left undone.

**It reads and changes nothing.** It edits no file, writes no entry and no question file, commits nothing, and runs
no build, no test and no gate (`check` runs after it). It reads with `git`, `grep` and the files themselves; its only
`just` command is `just decisions show`.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed is written out in the next one.

## 1. Read

- **The task's text**: its section of the plan, from its `### Task <n>:` heading to the next, whole, with the
  Interfaces it consumes and produces; and the plan's header (everything above its first `### Task`): the spec (the
  record's path), the Global Constraints, which every task's requirements include, and the Review Focus lines that
  name this task.
- **The record's sections** the task serves: those it names, and those whose subject its steps build. Where the plan
  and the record disagree, the record wins.
- **Each commit**, `(cd <root> && git show <commit>)`, one after another: its message, its paths, its diff. For an
  apply task, the entry too, `just decisions show <n>`.

## 2. Review

Every step of the task, against what the commits did:

- **Done as written**: every requirement of the step is there, the exact values verbatim (names, signatures, messages,
  paths); the tests the task names exist, test what it says (their assertions, the spec's values in them) and would
  fail without the code; the files are those the task lists.
- **The record**: the code says what the record's sections say; nothing contradicts a decision the record holds.
- **The Global Constraints and the Review Focus lines** of this task hold in the diff.
- **Nothing beyond the task**: no change the task does not ask (a lag fixed elsewhere, a refactor, a file it does not
  list) unless the task's own work needs it; no test skipped, deleted or loosened.
- **The protected documents** (files matched by `paths.protected` of `omc/config.yaml`) change only in an apply task's
  commit (its subject `Decision <n>: <title>`, the log and the pages together), and say what the entry's `Decision`
  says, nothing more; a protected document changed in any other commit is Critical.
- **The commits**: each stages the task's paths only, its message ends with the `Co-Authored-By` line.

A step the commits leave undone, or a task the report of the task terminal says is waiting for a doubt, is reviewed as
it is: what waits for an answer is named, not a finding.

## 3. Findings

One block per finding, numbered, in the report:

```text
FINDING 1
severity: Critical | Important | Minor
where: <file>:<line>
step: <the task's step it breaks, or the record's section, or the Global Constraint>
what: <what is wrong, in one or two sentences, and what the fix is>
```

**Critical**: a requirement of the task missing or broken, a test that does not test what the task says, a decision
of the record contradicted, a protected document changed outside an apply task. **Important**: a value not verbatim, a
change beyond the task, a missing case the task names, a Global Constraint broken. **Minor**: wording, naming, form.
A finding whose fix needs a ruling (it would change a rule or a protected document) says so in its `what`.

## The outcome

The report above the line is prose for the orchestrator: each step and how it was checked, then every `FINDING`
block, Minor ones included. No Critical or Important finding is `approved` (Minor alone is approved, and listed). The
last line is one of:

```text
OUTCOME {"outcome": "approved"}
OUTCOME {"outcome": "changes", "findings": ["Critical: omc/tools/plan.py:42: --tick ticks only the first box", "Important: …"]}
OUTCOME {"outcome": "failed", "reason": "a1b2c3d is no commit of this repository"}
```

`findings` holds the Critical and Important ones, one line each: its severity, `<file>:<line>` and what.

## Never

- Never edit a file, never commit, never fix a finding.
- Never write the log or an entry, never record a decision, never write a question file.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate.
- No `just` command but `just decisions show`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
