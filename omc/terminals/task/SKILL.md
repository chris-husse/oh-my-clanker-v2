---
name: task
description: "Carry out one task of the plan, or one review finding, test first where it is code, and commit it by name."
---

# task

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it carries out one task
of the plan (or one review finding), test first where it is code, commits its work by name, and ends with one
`OUTCOME` line. The gate is the orchestrator's: `check` runs after this terminal, on the clean tree it leaves. A
ruling is never this terminal's: a design doubt is returned as `needs_user`, nothing of it edited.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `plan:` the plan's path. `task:` the task's number, or
`finding:` the finding to fix (a review finding or a lag of the impact reading, as the orchestrator words it); after a
task review that asked for changes, both: the task, and its findings as the `finding`. `answer:` the answer the
orchestrator brings back to this terminal's earlier `needs_user`, or `none`. `commits: new` or `commits: amend`: how
the work is committed.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed is written out in the next one.

## 1. Read

- **The plan's header** (everything above its first `### Task`): the goal, the architecture, the spec (the record's
  path), the Global Constraints, which every task's requirements include, and the Review Focus lines that name this
  task. The header's line for agentic workers is not for this terminal: it carries out one task and starts no agent.
- **The one task**: its section, from its `### Task <n>:` heading to the next, whole, with the Interfaces it consumes
  and produces. Not the rest of the plan. With a `finding`: the finding, and the task whose code it touches when it
  names one.
- **The record's sections** the task or the finding serves, and the code and pages they name.
- **The callers of what the task changes**, before it edits: `/explain` run for each symbol or file the task changes
  (what calls it, what a change to it reaches), its citations checked in the tree as its step 3 says.

A task whose section carries the line `Conducted by the main session.` is not carried out here (it starts agents, which
a subagent cannot): the outcome is `failed` at once, its reason `task <n> is conducted by the main session`.

Where the plan and the record disagree, the record wins when it is clear; when it is not, `needs_user`.

## 2. The tree

```bash
(cd <root> && git status --porcelain --untracked-files=all)
```

The log (`paths.decision_log` of `omc/config.yaml`) and the question files under `paths.questions` (a file whose first
line starts `# Questions: `) are the orchestrator's: left as they are, never committed, never discarded here. Any other
path listed was not written by this run: `needs_user`, with the paths, before anything is edited.

## 3. Do the work

- **Code, test first** (`superpowers:test-driven-development`): the failing test the task names, run and seen red for
  the reason the task gives; then the code, the test seen green. Exact values come from the task and the record
  verbatim. Nothing beyond the task: a lag or a bug noticed elsewhere is named in the report, not fixed.
- **An apply task** (`/apply-decision <n>` of an entry): that skill is followed as it says, run by a plan task; it
  commits the pages and the log itself. Its stop on a passage the decision does not settle is a design doubt (below),
  with its passage, question and options; any other stop of it is `failed`, with what it printed.
- **The links task** (`just links-check`, then `/reconcile-links`): that skill is followed; what it would take
  through the doubt skill or put as a question is a design doubt here (below), the other links fixed.
- **The commands the task names** are run, one at a time, nothing beside another build or test on this machine:
    - its test files, each in the foreground, one after another, with the project's test runner;
  - never `/check`, `/build`, `/verify`, `just omc gate run`, a command of `omc/bin/` or any other step that `verify`
    runs (the project's `omc/bin/verify`), even where the task's text names them: `check` is the orchestrator's gate
    after this terminal, `verify` and its steps run only in the audit. A task step that names one is left out and named
    in the report, never turned into a stop.
- **A fix of a `finding`**: the finding is fixed where it points, test first where it is code, and nothing else.

## 4. A design doubt

A doubt is a question whose answer would change a rule or a protected document (a file matched by `paths.protected`).
First the gate: which rule or page would change. None: it is no doubt; it is decided here, as the task, the record and
the code lead, and the report says how. One that would: nothing of it is edited. The work the doubt does not touch is
done and committed (section 5), then the outcome is `needs_user`, and the report holds the block:

```text
DOUBT
where: <the task's step; the rule, page or code it touches: file and heading or symbol>
question: <the question, in one sentence>
read: <each passage read, by file and heading, and what it says>
options:
- <option>: <what it produces in the pages and the code>
- <option>: <what it produces>
pick: <the option it would pick, and why>
```

It never edits a protected document outside an apply task, never writes the log or a question file and never records a
decision: what becomes of the doubt is the orchestrator's.

**With an `answer`.** The rerun reads the answer and acts on it. An answer to act on is carried out in the code and the
tests, as if the task had said it, and the task finished; never in a protected document, which waits for the entry the
owner's ruling becomes. An answer that leaves the doubt open is not guessed: the work goes on around the point, and the
report names what waits for it. For an apply task the answer edits no page here: the entry stays recorded, the task ends
`done`, and the report says that the entry carrying the ruling is applied at the end of the build.

## 5. Commit

Every outcome leaves the tree clean but for the log and the question files: what this run wrote is committed before
it ends, so that `check` after it runs on a clean tree. Each commit stages its paths by name, `git add -- <path>…`.

- **`commits: new`**: one commit per step the task's text commits, its subject the one the task gives (else a subject
  in the repository's style), its message ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. An
  apply task's commit is the one its skill makes.
- **`commits: amend`**: `git commit --amend --no-edit` into the branch's one commit.

Then the commits of the task, oldest first:

```bash
(cd <root> && git log --reverse --format=%h $(git log -1 --format=%h -- <plan>)..HEAD)
```

With `commits: new`, they are every commit above the last commit of the plan (the plan's commit, or the last tick), an
earlier run's of this task included. With `commits: amend`, the one commit: `git rev-parse --short HEAD`.

## The outcome

The report above the line is prose for the orchestrator: what was built, the tests run (each red, then green), the
commands run and their verdicts, the commits, the lags and bugs noticed and not fixed, and the `DOUBT` block when
there is one. The last line is one of:

```text
OUTCOME {"outcome": "done", "commits": ["a1b2c3d", "e4f5a6b"]}
OUTCOME {"outcome": "needs_user", "question": "…", "options": ["…", "…"], "picked": "…"}
OUTCOME {"outcome": "failed", "reason": "task 4 is conducted by the main session"}
```

## Never

- Never edit a protected document outside an apply task's skill; never edit the plan or the record, and never tick a
  task: the orchestrator ticks it.
- Never write the log or an entry, never record a decision, never write a question file: a doubt is `needs_user`.
- Never run `/check`, `/build`, `/verify`, `just omc gate run` or another step of `verify`; never a build or test beside
  another.
- Never `needs_user` but for a design doubt (section 4), a path this run did not write (section 2), and a plan and a
  record that disagree unclearly: anything else the task meets (a finding of a tool outside the task, a budget, a
  warning) is named in the report and the task goes on to `done`.
- Never skip, delete or loosen a test to pass.
- Never start an agent or a skill that starts one or that talks to the owner: the `OUTCOME` line is the whole answer.

- Never `git add -A`, `git add .` or `git add -f`.
