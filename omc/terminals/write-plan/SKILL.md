---
name: write-plan
description: "Write the implementation plan from the committed design record with superpowers:writing-plans and its plan rule, and commit it; followed inline by the plan step of the design phase (and of the implementation phase when the design phase did not write it)."
---

# write-plan

A text of the `omc/` pipeline. It is followed inline, read with the Read tool, by the design phase's `plan` step (in the
session that hardened the record, on the orchestrator model, with the design's conversation) and by the implementation
phase's `plan` step when the design phase did not write the plan; it may also run in a fresh subagent. Either way it
speaks to no one: it writes the implementation plan from the committed design record with `superpowers:writing-plans`,
commits it by name, and ends with one `OUTCOME` line, which the step that follows it reads as its own word. The plan is
the record's argument: where the two disagree, the record wins. A question whose answer the record does not give is
never settled here: it is returned as `needs_user`, nothing committed.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `record:` the record's path, `<date>-<slug>-design.md`
in `paths.specs` of `omc/config.yaml`, committed on the branch. `answer:` the ruling the orchestrator brings back to
this terminal's earlier `needs_user`, or `none`. A rerun with an answer reads it as the answer to the question it
returned: the plan is written again (section 2) with that question settled as the answer says, in the tasks it touches,
and the report names where; an answer that rules on a rule or a protected document is an entry the orchestrator
recorded, and its task is planned as the plan rule says for an entry (`just decisions list` shows it).

**It writes the plan only.** No other file: no protected document (a file matched by `paths.protected`), no record, no
code. It never writes the log, never records a decision, never writes a question file. It runs no build, no test and no
gate; its only `just` commands are `just decisions list`, `just decisions show`, `just decisions pending` and the read
verbs of `just omc gitnexus` (`query`, `context`, `impact`, `cypher`, through `/explain`), never `install` or `refresh`.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed is written out in the next one.

## 1. Read

```bash
(cd <root> && git log -1 --format=%h -- <record> && git status --porcelain -- <record>)
```

It prints one hash and no status line: the record is committed as it is. No hash, or a status line, is `failed`.

- **The record**, whole: its decisions, its sections, its section "Decisions and the pages they change" (one row per
  entry of the branch, with the pages it plans), its Testing.
- **The plan rule** (section 2): the entries it orders are those of the record's rows, checked against the log with
  `just decisions list` and `just decisions show <n>` (an entry already applied has no task).
- **The code and the pages** the record cites, as far as a task needs its files, names and tests exact.
- **The callers of what a task changes**: `/explain` run for each symbol or file a task changes (what calls it, what
  a change to it reaches), its citations checked in the tree as its step 3 says; a caller it finds is in the task's
  files or its tests.

## 2. Write

`superpowers:writing-plans`, with the record as its spec, and with these additions to it:

- **The plan rule** decides the order. A plan written from a record with the section "Decisions and the pages they
  change" begins with these tasks, then the feature's own code: (1) one task per entry, in id order,
  `/apply-decision <n>` in a fresh agent and one commit each; (2) `just links-check` and `/reconcile-links`. Every task
  carries its `Complexity:` line and is gated by the check gate after it; a plan with the header line `Gate: build` is
  gated by the build gate and the omc tool tests after each task instead, and by the check gate once at the end of the
  implementation phase. The plan has that line when the branch changes no file of the project's product: with
  `paths.product` of `omc/config.yaml` (the globs of what the project ships), no file the record's work and the
  plan's tasks change matches one of them (a tool, a document, a test of the tooling are not the product); without
  it, the branch changes nothing of what the project's check gate tests. A branch that changes a product path after
  all is gated by the check gate from then on (`just omc plan --next` gives `check` for it). An apply task whose agent
  stops on a passage the decision does not settle leaves the entry recorded and takes the doubt through the answer-doubt
  skill, as any doubt of the build; the review-decisions skill at the end of the implementation phase carries the entry
  that replaces it.
- **A task the main session must conduct** (a task whose steps start agents) carries the line
  `Conducted by the main session.` under its heading, beside its `Complexity:` line: a task subagent cannot start
  agents, so the orchestrator follows that task itself.
- **The complexity** (omc's definition, in full): "Every implementation task in the plan carries a
  `Complexity: simple | medium | high` line, choosing one value. Label multi-file, architecturally tricky or ambiguous
  coding work `high`; choose `simple` for narrow routine work and `medium` otherwise. The plan stores complexity,
  never model ids. Write about five to seven tasks, each a coherent chunk of the work; a small change may need fewer,
  and a plan is never padded to reach five. Inside a task, independent edits (different files) fan out to parallel
  edit-only agents that run no build and no test, followed by one build-and-fix pass; never one task per file or per
  page. The project's testing policy still governs the order inside a task." The line sits under the task's heading,
  as `Complexity: medium`; a task without one is read as `medium`.
- **The form the tools read**: each task is a heading `### Task <n>: <title>`, numbered from 1, and its steps are
  `- [ ]` checkboxes inside its section; `just omc plan --next` takes the first task with an unticked box as the next.
- **Where it is saved**: `<date>-<slug>-plan.md` in `paths.plans`, `<date>-<slug>` the record's own
  (`<date>-<slug>-design.md` in `paths.specs`). An uncommitted file at that path is an earlier run's and is written
  again.
- **What writing-plans would put to its human partner** is not put here: its scope check is decided from the record
  (one record, one plan), and its closing question about the execution approach is not asked (the pipeline builds
  the plan, one task at a time). Its self-review is run.
- **A doubt** (the record leaves open how a task must be built, and the answer would change a rule, a protected document
  or the design of the record): the plan is not committed, and the outcome is `needs_user` with the question, its
  options (what each produces in the plan, the pages and the code) and the answer it would pick. Followed inline from
  the design phase on, that `needs_user` is no question put to anyone: it is a doubt the session takes through the
  answer-doubt skill (the flow "a plan"), as the run's rule from the design phase on says, and the plan is written again
  with its answer. A choice that changes none of them is made here and written into the plan.

## 3. Commit

```bash
(cd <root> && git add -- <plan> && git commit -m "Plan: <the record's title>, <k> tasks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <plan> && git show --stat --format='%h %s' HEAD)
```

`<k>` is the number of `### Task <n>:` headings. Only the plan is staged, by name; any other changed path is left as it
is.

## The outcome

The report above the line is prose for the orchestrator: the tasks, one line each with its complexity, the apply tasks
named, the main-session tasks named, and every choice the record left that the plan made. The last line is one of:

```text
OUTCOME {"outcome": "written", "path": "docs/superpowers/plans/2026-01-05-x-plan.md", "tasks": 9}
OUTCOME {"outcome": "needs_user", "question": "…", "options": ["…", "…"], "picked": "…"}
OUTCOME {"outcome": "failed", "reason": "docs/superpowers/specs/2026-01-05-x-design.md is not committed"}
```

## Never

- Never edit a file but the plan: no protected document, no record, no code.
- Never write the log or an entry, never record a decision, never write a question file.
- Never write a model id into the plan: complexity only.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate.
- Never put a gate or a step of `verify` into a task (`/check`, `/build`, `/verify`, `just omc gate run`, a command of
  `omc/bin/`): the gates are the orchestrator's and the audit's; a task's steps are its own tests and the commands that
  build it. Never write a "bring back to the conductor" or "stop" into a task or the plan's constraints for a finding: a
  task stops only as the task terminal's `needs_user` allows (a design doubt, a foreign dirty path, a run holding the
  lock); a blocker the record's Risks name is a `failed` of the task, with its reason.
- Never start an agent or a skill that starts one or that talks to the owner, as a subagent or inline: the report and
  the `OUTCOME` line are the whole answer; writing-plans' execution question is not asked.
- Never `git add -A`, `git add .` or `git add -f`.
