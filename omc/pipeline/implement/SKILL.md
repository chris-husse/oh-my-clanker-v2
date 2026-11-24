---
name: implement
description: "The pipeline's implementation phase, entered by /design or typed: from the committed design record, the plan (written here only when /design did not), its tasks one at a time each gated as the plan's Gate: line says (/check without one), then the decisions of the build carried through, then /audit unless ask_for_provider_handoff. /implement <step-id> enters at that step."
---

# implement

The implementation phase of the `omc/` pipeline, in the owner's session: from a committed design record to an
unpublished branch of committed work, and nothing else. It writes the plan when `/design` did not, builds its tasks one
at a time, each gated as the plan's `Gate:` line says (▣ check, or ▣ build and the omc tool tests), and carries the
decisions of the build through; then it hands the run on to `/audit`. It never rebases (the branch moves onto `<base>`
only in `/design`'s `fresh` and `/audit`'s `rebase`) and never runs `/verify` (that is `/audit verify`'s). The plan rule
is `omc/terminals/write-plan/SKILL.md`'s; the log (`paths.decision_log` of `omc/config.yaml`), the entry and the
question file are `omc/tools/decisions/FORMAT.md`.

**Where you are.** There is no run file. A skill started again, after a compaction or in a fresh session, begins at its
first step, and every step that is done skips itself on its tool's answer; "done" is read from the repository or a
record a tool wrote, never from what the session remembers. Whatever the step entered, `just omc enter implement` runs
first (it writes `.cache/omc/current`, which puts this skill back into a compacted session). `/implement <step-id>`
enters at that step; `/implement` alone, or with anything that is not one of its step ids, begins at `record`. A
restart continues at the first task of the plan with an unticked box.

**Terminals and tools.** ▣ (a terminal) and ✓ (a tool check). A terminal is run as: `just omc models <role>` (the role
is written at each call), then one fresh agent, `subagent_type: general-purpose`, with that model and effort where the
harness takes them (an empty model: the session's own, said in one line; an empty effort: the harness's default), its
prompt exactly `Read <root>/omc/terminals/<name>/SKILL.md and follow it. Root: <root>.` and then the inputs its step
names, one per line; `<root>` is the absolute path `git rev-parse --show-toplevel` prints. Its last line is
`OUTCOME {"outcome": "<word>", …}`: the step reads the word and the fields it names; the report above the line is prose
for this session, never parsed. Every terminal may also return `needs_user` (`question`, `options`, `picked`: "A
ruling", below) and `failed` (`reason`: told to the owner, who says whether it runs again); an agent that ends without
an `OUTCOME` line has failed. **Checked, not believed:** a terminal's word that a tool contradicts is a hard stop to the
owner (both answers shown, nothing goes on until they rule); an outcome no tool checks is taken as reported, and the
message says so. One terminal at a time: never a terminal beside another, nor a command of this session's while one
builds or tests. One build, test or render at a time among this run's own agents and commands; never wait for another
worktree's or session's run (their load is reported, not waited out).

**A ruling.** On `needs_user`, two kinds. A design doubt (a question whose answer would change a rule or a protected
document; the task terminal's report holds it as a `DOUBT` block) goes through `/answer-doubt` ("Talking to the owner").
The three other kinds, and only these (a dirty path the terminal did not write, a run the gate did not start holding
what the gate needs: wait for it or stop it, a plan and the record that disagree where the record is not clear), are
asked of the owner directly, each option with what it produces, its `picked` as the recommended one: a stop no tool or
document can settle, which "From `/design` on" leaves to the owner as each step says. A `needs_user` of any other kind
(a finding of a step of `verify`, a budget, a warning) is never put to them in implementation: it is `/audit`'s, and
the terminal is run again with `answer: not the owner's in implementation: leave it for /audit, name it in the report,
and finish the task`. Then a terminal that takes an `answer` (▣ task) is run again with it, its `answer: <the answer>`
input line, and so is the plan written again inline; ▣ check and ▣ build take none (their `needs_user` in `tasks` item
6).

**Talking to the owner.** The run is autonomous from `/design` on (`omc/pipeline/design/SKILL.md` › "From `/design` on,
no question blocks the run"), the plan included: they may be away, and no question but the limit (below) blocks the
run. A question no protected document would change is decided here, from the record, the plan and the code, and the
message says how. A design doubt goes through `/answer-doubt` (the flow "a plan" while the plan is written, the
implementation flow from the first task on): both answers agree, the ruling is recorded at once through
`/record-decision` with `Automated: true` and acted on; they disagree, the run acts on its pick all the same, recorded
at once through `/record-decision --disagreed` (`Automated: disagreed`), and goes on; the owner rules the run's entries
after their screenshot review in `/audit` (`push`, through `/review-decisions`). The one question to them before then
is `/answer-doubt`'s limit: the sixth disagreed entry not yet ruled stops the run, and they are asked about all six,
one at a time. Every stop is put to them in the conversation, one at a time. Every message opens with the skill and
step and its place, `/implement › tasks (step 3 of 5)`, and progress as done of total (`task 4 of 12`,
`fix round 1 of 2`). Every option shows what it concretely produces, never a bare label, with the recommended one
named; a long message that asks questions ends with every question repeated as a numbered list, one line each with the
recommended default. Their vocabulary: "the log", "an entry", "recorded", "applied", "the protected documents", "the
merge-base", "a question file", "the record", "the plan", "in implementation"; no coined compressions.

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; a value a command printed (`<record>`, `<plan>`, a task's number, a
commit) is written out in the next one; so are the configured paths, read from `omc/config.yaml`: `<log>` is
`paths.decision_log` (no log configured: `<log>` is dropped from the command, and a step about the log is skipped),
`<questions>` is `paths.questions` and `<plans>` is `paths.plans` (folders, ending with `/`). The
log is written only through `just decisions` and `/record-decision`. A commit stages its paths by name,
`git add -- <path>…`, never `git add -A` or `git add .`, and its message ends with
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

**The record and the plan.** `<record>` is the path `just omc record` prints (the `*-design.md` of `paths.specs` the
branch added and committed since the merge-base); more than one: the one with the branch's slug, else the newest by its
date prefix, said in one line; never a question. `<plan>` is the path `just omc plan` prints (the `*-plan.md` of
`paths.plans` the branch added and committed).

**Before every ▣ check** (and every ▣ build), the tree must be clean for its run to count (a run started on a dirty
tree never holds):

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git status --porcelain --untracked-files=all; echo 'question files:'; for f in <questions>*.md; do head -1 "$f" | grep -q '^# Questions: ' && echo "$f"; done)
```

Exactly two kinds of path are committed here, by name: the log, `<log>` (entries `/record-decision` wrote), and the
question files among the dirty paths (a file whose first line starts `# Questions: `, the second part's list;
`/answer-doubt` writes them and commits nothing):

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <path>… && git commit -m "Implement: the log and the question files before the check" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <path>… && git show --stat --format='%h %s' HEAD)
```

Nothing of the two: no commit. Any other dirty path goes to the owner, the options being to commit those paths by name
and run the check, or to leave the check for now, which stops `/implement` here until they have committed or discarded
them.

## `record` — confirm the design record is committed.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc enter implement && just omc record)
```

✓ It prints `<record>` (exit 0): on to `plan`. `no record committed on this branch` (exit 1): stop, to the owner: "No
design record is committed on this branch; finish the brainstorm (`/brainstorm`) and type `/design` first." An `error:`
(exit 2, no `origin/<base>`): to the owner, with the error.

## `plan` — write the plan from the record, when `/design` did not.

Skip when `just omc plan` finds one (exit 0, the usual case: `/design` › `plan` wrote it): on to `tasks`.

Without one (a session started fresh after a hand-off, or an older branch), it is written as `/design` › `plan` does:
this session reads `<root>/omc/terminals/write-plan/SKILL.md` with the Read tool and follows it inline,
`record: <record>`, `answer: none`, never as a subagent. It writes the plan by `superpowers:writing-plans` and its plan
rule (one `/apply-decision` task per entry in id order, the links task, then the feature's own tasks, each with its
`Complexity:` line), and commits it. Its `OUTCOME` line is this step's own word:

- `written` (`path`, `tasks`): ✓ `just omc plan` prints that path; it does not: a hard stop. The tasks, one line each
  with its complexity and the main-session tasks named, are shown in the message; then on to `tasks`.
- `needs_user`: its doubt through `/answer-doubt` for the flow "a plan" ("Talking to the owner"), then the plan written
  again with `answer: <the answer>`.
- `failed`: to the owner, with its reason.

## `tasks` — build the plan's tasks one at a time, each gated.

Skip when `just omc plan --next` exits 1 (`every task of <plan> is ticked`): on to `decisions`.

One task at a time, in the plan's order, each through to its tick before the next begins. For each:

1. **The next task:**

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc plan; git status --porcelain -- <plans>; just omc plan --next; echo "next: exit $?")
   ```

   First the status: a line for `<plan>` is a tick an earlier session made and did not commit; it is committed first, as
   in item 7 without the `--tick`, `<n>` the task whose boxes its diff (`git diff -- <plan>`) ticks; then this item
   again. Then `--next`. Exit 0:
   `{"task": <n>, "title": "<…>", "complexity": "simple|medium|high", "gate": "build|check"}`, the task to build (of
   `<k>`, the plan's `### Task` headings), and `<gate>`, the plan's `Gate:` header line (`Gate: build` or `Gate: check`;
   no line: `check`; `build` made `check`, with the key `product` naming the paths, once the branch changes a path of
   `paths.product`), which items 3 and 6 read. Exit 1: every task is ticked, on to `decisions`. Exit 2 (two plans on
   the branch, no plan, or a plan with no `### Task <n>:` heading): stop, to the owner, with the error; nothing goes on
   until they rule.
2. **Who builds it.** A task whose section has a line beginning `Conducted by the main session` (bold or not) is
   followed inline from the start (item 4); any other goes to item 3, then to ▣ task (item 5):

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && sed -n '/^### Task <n>:/,/^### Task /p' <plan> | grep -q '^\(\*\*\)\{0,1\}Conducted by the main session' && echo 'main session' || echo 'task terminal')
   ```

3. **Is it done**, for a task ▣ task builds (a main-session task runs its own gate between its steps, so a pass says
   nothing of it). With `<gate>` `build` this item is skipped, on to item 5, whose ▣ task finds an earlier run's commits
   and the work they hold. With `check`, the task's commits so far, every commit above the last commit of the plan, and
   the gate:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git log --reverse --format=%h $(git log -1 --format=%h -- <plan>)..HEAD; just omc gate passed check)
   ```

   Commits listed, `passed:` (or `skipped by the owner`), and the pass's `<head>` descends from the task's first
   commit (the first line listed), so that the pass is of this task's work and not the previous task's:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git merge-base --is-ancestor <first commit> <head> && echo 'after the task' || echo 'before the task')
   ```

   `after the task`: the task was built, reviewed and gated before a restart, straight to item 7. Otherwise on to
   item 5.
4. **Inline.** This session reads the task's section with the Read tool and conducts it as the orchestrator (a task
   subagent cannot start agents): it carries out the task's steps and commits its own work. The agents it starts take
   `just omc models <role>`, a coding agent the complexity its step gives, a reviewer `orchestrator`. Its doubts go
   through `/answer-doubt` for the implementation flow. Then on to item 6, which gates it; it has no ▣ task-review (the
   reviews its steps start stand in for it). After a restart a main-session task is followed again whole, from the
   start, finding its own commits.
5. **▣ task**, role the task's `complexity` (`simple`, `medium` or `high`; a task with no `Complexity:` line is
   `medium`):

   ```text
   plan: <plan>
   task: <n>
   answer: none
   commits: new
   ```

   - `done` (`commits`): ✓ the commits above the plan's last commit (item 3's `git log`) are the ones it returned,
     and `git status --porcelain` lists nothing but the log and the question files; a mismatch is a hard stop. Then
     ▣ task-review, role `orchestrator`:

     ```text
     plan: <plan>
     task: <n>
     commits: <the commits, oldest first, separated by spaces; none: none>
     ```

     The commits are the task's: the `Implement: the log and the question files before the check` commits and
     check's `Check fix: …` commits a restart finds in the range are not the task's, and are left out. A `done` with no
     commit goes to it with `commits: none`.

     - `approved`, taken as reported (its Minor findings named in the message): on to item 6.
     - `changes` (`findings`): ▣ task again with both, `task: <n>` and `finding:` followed by the findings exactly as
       the outcome gave them, one per line, with `answer: none` and `commits: new`; then ▣ task-review again over all
       the task's commits (item 3's `git log`). At most two such fix rounds; still `changes` after the second: to the
       owner, the findings left quoted, the options being one more fix round, going on to the check with the findings
       standing, or stopping the build here. Left standing, they are written, one per line, to the ignored file
       `.cache/omc/standing/<n>` (not to the plan: a dirty plan would make check's run start dirty, and a commit of it
       would cut the task's commit range), so that a restart keeps their choice: with that file present, a `changes`
       whose findings it all holds goes on to item 6 at once.

       ```bash
       ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && mkdir -p .cache/omc/standing && printf '%s\n' '<finding>' >> .cache/omc/standing/<n>)
       ```
     - `failed`: to the owner, with its reason.
   - `needs_user` with a `DOUBT` block: `/answer-doubt` inline, through the Skill tool, for the implementation flow
     (its input: the question; where, `implement, task <n>` and the block's `where`; the passages its `read` names).
     Its one-line report decides the `answer` of ▣ task again: `subagent agree` (acted on) or `subagent disagree`
     (acted on, `decision <n> recorded (disagreed)`), the picked answer, to act on;
     `asked at the limit: decision <n>`, the owner's ruling as entry <n> of the log records it
     (`just decisions show <n>`), never the picked answer; the earlier disagreed entries they overruled at that stop are
     undone by their new entries' follow-through, as for any entry; `collected`,
     `open: Q<k> of <question file> waits for the owner; go on around it`;
     `settled from the docs` or `not a doubt`, the answer it gives; `merged into Q<k>`, as that question's
     `**Acted on.**` line stands. Then ▣ task again with `task: <n>`, that `answer` and
     `commits: new`.
   - `needs_user` without one (a dirty path, a run holding what the gate needs, an unclear disagreement of the plan and
     the record): asked of the owner directly ("A ruling"); their answer goes back to ▣ task as its `answer`. Any other
     kind is never asked: ▣ task again with the `answer` of "A ruling" (leave it for /audit).
   - `failed` whose reason reads `conducted by the main session`: the slip is this session's (it sent a main-session
     task to the terminal); the task is followed inline, item 4, and a skip of the gate is never offered for it.
   - `failed` for any other reason: to the owner, with its reason, who says whether it runs again.
6. **The gate.** First the clean tree ("Before every ▣ check", above). Then, by `<gate>`:

   **`build`** (a plan that changes nothing of the project's product, `paths.product`, or without it nothing of what
   the project's check gate tests): ▣ build, role `orchestrator`, then the omc tool tests:

   ```text
   commits: new
   why: after task <n> of the plan
   ```

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -X pycache_prefix=.cache/pycache -m unittest discover -s omc/tools -p 'test_omc_*.py'; echo "tests: exit $?")
   ```

   - ▣ build `passed` (`attempts`), taken as reported, and the message says so; then the tests. `tests: exit 0`: item 7.
     Any other exit: ▣ task with `task: <n>`, `finding:` the failing tests' lines, `answer: none`, `commits: new`, then
     this item again; red a second time with no fewer failing tests: to the owner, the failures quoted, the options
     being one more fix round or the build stopped here.
   - ▣ build `failed` (`summary`): to the owner, with the summary, the options being ▣ build once more, the build
     stopped here, or their skip of it, said in the conversation only (no tool asks about it later), then the tests as
     above.
   - ▣ build `needs_user`: as ▣ check's below.

   **`check`**: ▣ check, role `orchestrator`:

   ```text
   commits: new
   why: after task <n> of the plan
   ```

   - `passed` (`attempts`): ✓ `just omc gate passed check`; `not passed`: a hard stop. Then item 7.
   - `failed` (`summary`): the task is still red at its gate's limits; to the owner, with the summary, the options being
     ▣ check once more, the build stopped here, or their skip of the gate, which this session writes on their word only,
     then checks:

     ```bash
     ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc gate skip check && just omc gate passed check)
     ```

     It prints `skipped by the owner at <head>`: item 7. A refusal (exit 2, the tree has changes the skip would not
     cover): to the owner, with the paths.
   - `needs_user`: ▣ check takes no `answer`; this session acts on it itself, then the clean tree again and ▣ check
     again with no answer line. A run holding what the gate needs, or a path it did not write: asked of the owner
     directly, each option with what it produces, and done on their word only: the run waited for or stopped; the named
     paths committed by name or restored from `HEAD` (`git restore --staged --worktree -- <path>`, an untracked one
     removed). A fix that needs a protected document or a ruling: a design doubt, `/answer-doubt` as in item 5; an
     answer to act on is carried into the code by ▣ task (`task: <n>`, `finding:` check's question, `answer:` the
     answer, `commits: new`), then ▣ check again (a disagreement is acted on too, recorded `disagreed`). A collected
     one (`collected`) is never followed by ▣ check again, which would meet the same doubt: it goes to the owner as the
     gate's `failed`, the question quoted, the options being their skip of the gate (written and checked as under
     `failed`, `just omc gate skip check`, the question left open for `/audit`'s `push` item after the screenshot
     review) or the build stopped here.
7. **The tick**, right after the green gate (with `build`: ▣ build's `passed` and the tests' exit 0) and with nothing
   committed between, since the next task's commits are
   read as those above the plan's last commit:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc plan --tick <n> && git add -- <plan> && git commit -m "Plan: task <n> done" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <plan> && git show --stat --format='%h %s' HEAD)
   ```

   Findings the owner left standing (item 5, the lines of `.cache/omc/standing/<n>`) are named in one more
   paragraph before the `Co-Authored-By` line, `-m "Left standing by the owner: <finding>, …"`; after the commit the
   file is removed (`rm -f .cache/omc/standing/<n>`, in the shell form above). Then the next task, item 1.

## `decisions` — carry the decisions of the build through.

Skip when `just design-integrity-check --defer-questions` is green (it prints `OK`) and `just omc gate passed check`
holds: on to `done`.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just design-integrity-check --defer-questions; just omc gate passed check)
```

`--defer-questions` leaves the `questions` and `disagreed` checks out: an open question in a question file and an
entry recorded `disagreed` wait for the owner's rulings after their screenshot review (`/audit`'s `push`), and never stop
the night's run here.

Green without a pass: only the gate at the end of this step (the clean tree, ▣ check, ✓), below.

Its `PROBLEM:` lines (an entry recorded during the build and not applied, a missing row of the record, a protected
document no applied entry names) are the work of `/review-decisions`, inline through the Skill tool, for the rulings
made during the build, sent as its deferred run (the caller saying `deferred`). It runs inside `/implement`: it poses no
question here (its step 2 is skipped, an apply agent's doubt stays open in the question file, and it ends with those
questions open, for `/audit`'s `push` item after the screenshot review), and its follow-through ends at a green
`/check`, never `/verify`, and its red check is fixed under this skill's gate: ▣ check as in `tasks` item 6,
`why: the follow-through of the decisions`, its `failed` to the owner with the skip as their way past. Its report is
shown in the message. Then ✓ `just omc gate passed check`: `passed:` (or `skipped by the owner`), on to `done`.
`not passed` (its last run started on a dirty tree, or something changed after it): the clean tree ("Before every
▣ check") and ▣ check as in `tasks` item 6, `why: after the decisions of the build`, then ✓ again; still `not passed`:
a hard stop, to the owner with what it printed. Then on to `done`.

## `done` — hand the run on.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc enter --done && just omc handoff)
```

- `continue`: one line, "Implemented; going on to `/audit`.", then `/audit` through the Skill tool, in this same
  turn. Nothing else follows here.
- `ask` (`ask_for_provider_handoff: true` in `omc/config.yaml`): stop, to the owner: "Implemented; type `/audit`, in
  this session or a fresh one." Nothing follows.
- An `error:` (exit 2, the flag is not a boolean): to the owner, with the error.

## Never

- Never a rebase, and never `/verify` or `just omc gate run verify`, whole or partial; the check gate only through
  ▣ check and the follow-through of `/review-decisions`; the build gate only through ▣ build.
- Never take a terminal's word where a tool answers: `just omc plan`, `just omc plan --next`, `git log`,
  `just omc gate passed check`, the omc tool tests' exit and `just design-integrity-check` decide, the terminal's word
  only where none does.
- Never two terminals at once, nor two tasks: one build at a time among this run's own.
- Never tick a task whose gate has not passed or been skipped by the owner; never write a skip but on their word, and
  never offer one for a main-session task the terminal sent back.
- Never edit a protected document (a file matched by `paths.protected`) but through `/apply-decision` (a plan's apply
  task, or `/review-decisions`' step 3); never write the log but through `just decisions` and `/record-decision`; never
  record a decision but the owner's ruling, the agreement of `/answer-doubt`'s two answers (`Automated: true`) or its
  pick acted on although they disagreed (`Automated: disagreed`).
- Never put a design doubt to the owner directly: `/answer-doubt` rules it, agreed or disagreed, and the owner rules
  the run's entries after their screenshot review in `/audit`; the one exception is `/answer-doubt`'s limit, the sixth
  disagreed entry not yet ruled.
- Never `git add -A` or `git add .`.
