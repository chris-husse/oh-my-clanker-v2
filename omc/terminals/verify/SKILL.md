---
name: verify
description: "Run the milestone gate, the project's `omc/bin/verify` through `just omc gate run verify`, in the background and polled, then the design integrity check; fix while it runs, rerun the fixes, pass on a fresh full run of a clean tree. Commits the baselines it advanced, regenerates the screenshots, never judges them. Ends with a report and its OUTCOME line."
---

# verify

A terminal of the `omc/` pipeline, and the skill `/verify`. It runs in a fresh subagent of the pipeline (/audit), or
inline in whoever ran `/verify` (the owner, or an agent at any depth); either way it asks nothing of the owner: it runs
the project's milestone gate, fixes what is red while it runs, reruns what it fixed, gives its verdict from a fresh
full run on a clean tree, and ends with its report and one `OUTCOME` line, its last line. The pipeline reads the line,
a caller by hand the report above it; `needs_user` is an outcome its caller reads and acts on, never a question this
skill puts. The gate may outlast a command timeout, so it runs in the background and is polled, never in the
foreground.

**Inputs** (in the prompt, one per line; each has a default, for a `/verify` typed without them). `Root:` the
worktree; without it, `git rev-parse --show-toplevel` of the current directory. `commits: new` or `commits: amend`:
how its fixes and the baselines' advances are committed; without it, `new`. The audit passes `commits: amend`, on its
squashed branch: everything goes into the branch's one commit. `commits: new`, for a `/verify` by hand on a branch not
yet squashed: each fix its own commit, the baselines' advances one commit of their own, nothing amended.

**A gate terminal's rules** (`check`, `build` and `verify` each say them):

- **It fixes and reruns inside itself.** An attempt is one full run. A red attempt made progress when it has fewer red
  steps or fewer failing tests than the full run before it (the first is compared with nothing). The terminal ends
  with `failed` at the tenth red attempt, or at the second red attempt that made no progress.
- **A fix repairs the code under test**, never the gate's definition: nothing under `omc/bin/` (the command or its
  notes), never a recipe or script the command runs to define what the gate checks, never a step moved out of the
  gate, never a test skipped, deleted or loosened to pass.
- **A fix that needs a protected document** (a file matched by `paths.protected` of `omc/config.yaml`) **or a
  ruling** edits nothing of it: the terminal commits the fixes it has made and returns `needs_user` with the question,
  its options and the answer it would pick.
- **Its fixes are committed before the run that gives the verdict**, so that the passing run is a run of a clean tree: a
  run started with uncommitted changes never counts (`just omc gate passed verify` does not hold it). Each commit stages
  its paths by name, `git add -- <path>…`. With `commits: new`, one commit per fix, its subject `Verify fix: <what>`,
  its message ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. With `commits: amend`,
  `git commit --amend --no-edit` into the branch's one commit. A changed path this terminal did not write (the
  screenshots and the baselines aside, below) is neither committed nor discarded by it: `needs_user`, with the paths.
- **One build, test or render at a time in this worktree**: nothing else of its own runs beside `verify`; one run per
  worktree, so a rerun waits until the run before it has ended; runs in other checkouts take the gate's machine-wide
  slots (`concurrency` of `omc/config.yaml`; absent: one), and a run waits for one.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`.

## What it runs

The project's own command, `omc/bin/verify`: what it runs is the project's (often every step of the fast gate first,
then the slow ones), and this skill does not list it. `just omc gate run verify` runs it at the root, its output
streamed and teed to `.cache/omc/gates/verify.log` (truncated at each run), and exits with its exit code. A run with
arguments (`just omc gate run verify <ARGS…>`, when the project's command takes some to run a part of it) is a partial
run: it never records a pass and never gives the verdict. After each full run this terminal runs
`just design-integrity-check` itself, in the foreground (no build, no test); in a project without protected documents
or a decision log it finds nothing and passes.

The gate may write files: the screenshots it regenerates (`paths.screenshots` of `omc/config.yaml`) and the baselines
it advances (`paths.baselines`), each a list of globs. They are left as uncommitted changes by the run and handled
after the passing run (below). When both lists are empty, every step about them skips itself.

## The loop

1. **Clean.** Before every full run, the previous run's screenshots and baselines go back to `HEAD`, which holds every
   fix and advance this terminal committed, new or amended (the run writes every one of them again, so this hides
   nothing), and the tree must then be clean. With `<specs>` one pathspec `':(glob)<glob>'` per glob of
   `paths.screenshots` and `paths.baselines` (both empty: only `git status --porcelain`):

   ```bash
   (cd <root> && git diff --name-only -z HEAD -- <specs> | xargs -0r git restore --source=HEAD --staged --worktree -- && git clean -fdq -- <specs> && git status --porcelain)
   ```

   The last command prints nothing, or the rule above applies.
2. **Start.** `(cd <root> && just omc gate run verify)` with the Bash tool's `run_in_background`; its background task
   ends with the command's exit code. An exit 2 with `error: no gate command omc/bin/verify` (or `is not
   executable`) is the project's setup, not a red: `needs_user`, naming it. Never start a run while one of this
   terminal's is still going; a run this terminal did not start that holds what the project's command needs (its
   error names a lock, a port or a process held) is never stopped (the owner may have started it): `needs_user`,
   naming what holds it, with the options to wait for it or to stop it.
3. **Poll.** `(cd <root> && sleep 30 && tail -n 40 .cache/omc/gates/verify.log)` until the background task has ended;
   each call takes about half a minute, far below the command timeout. A log whose last line is
   `max concurrency of verify reached (…); waiting` is a run waiting for a slot (`concurrency` of `omc/config.yaml`:
   other runs of the gate on this machine), not stuck; the line comes again each minute. With a `silence` limit for
   `verify` in `omc/config.yaml`, the gate ends a run that writes nothing that long itself: the log's last line
   `no output for <s> s: killed` and exit 124 are the red of the step it was in: name the step in the report, fix it,
   commit the fix, and start again from step 1. Without one, the gate never stops a run for its time or its silence,
   and the check is this terminal's: the log has not grown for a minute while the task still runs (and is not waiting
   for a slot): it is likely stuck. Read the end of the log; when it is stuck, stop the background task, name the
   step in the report, fix it, commit the fix, and start again from step 1.
4. **Fix while it runs.** Analyze each failure as it appears in the log and fix it while the run goes on; do not wait
   for the end. Run nothing else meanwhile.
5. **Done.** When the task has ended, read its exit code and the log, then run `just design-integrity-check`. Exit 0
   of a full run started on a clean tree, no `PROBLEM` line, and then `just omc gate passed verify` exits 0: on to
   "After the passing run". Otherwise rerun what each fixed failure fixed (a single test in the foreground, or a
   partial run, `just omc gate run verify <ARGS…>`, in the background and polled the same way), one after another,
   fixing again what is still red without another rerun; a partial run truncates the log, so read the full run's log
   before it. Then commit the fixes, green or not, and a fresh full run from step 1 is the next attempt, where a
   failure still red counts; a partial run never gives the verdict.
6. **Died.** The task ended without an exit code (killed from outside, or crashed): read the end of the log, then
   start again from step 1; the dead run counts as an attempt.

## What is red, and how it is fixed

- **The project's notes.** Before fixing a red, read `omc/bin/verify.md` when it exists: the project's notes on its
  reds (known flakes, baselines, what a step's message means); a red it speaks to is handled as it says.
- **A step of the fast gate red inside `verify`** is never just rerun to green: it passed in `check`, and one that
  fails here is explained and fixed. A step green on a rerun and red in the verdict is flaky, and is fixed in the test
  or in the code under it, whatever made it pass one time and fail another.
- **`design-integrity-check`** is read line by line, by the check each `PROBLEM: <check>:` line names. Its
  `links-check` lines are fixed like any red step (`/reconcile-links`; where that skill would leave a question, or a
  link waits for a decision, `needs_user`). Every other check (`pending`, `questions`, `record`, `guard`,
  `decisions check`) is never fixed here: this terminal never edits the decision log, never records a decision, never
  writes a row into the record, never writes a question file and never undoes an edit of a protected document. The
  run's other failures are still fixed; once the run has ended, each fixed failure's rerun runs as in step 5, the
  fixes are committed, and the outcome is `integrity` with those `PROBLEM` lines, without a fresh run.

## After the passing run

1. **The baselines.** With `<specs>` one pathspec per glob of `paths.baselines` (empty: this step skips itself),
   `git diff HEAD -- <specs>` and `git status --porcelain -- <specs>` show the advances the run wrote. Analyze them:
   do they match what was fixed, or what the branch changed; was anything raised that should not be (name it in the
   report). Then commit them, when there are any. With `commits: amend`, into the branch's one commit:

   ```bash
   (cd <root> && { test -z "$(git status --porcelain -- <specs>)" || { git ls-files -z -m -o -d --exclude-standard -- <specs> | xargs -0r git add -- && git commit --amend --no-edit; }; } && git show --stat --format='%h %s' HEAD)
   ```

   With `commits: new`, as one commit of their own:

   ```bash
   (cd <root> && { test -z "$(git status --porcelain -- <specs>)" || { git ls-files -z -m -o -d --exclude-standard -- <specs> | xargs -0r git add -- && git commit -m 'Baselines: the advances of verify' -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'; }; } && git show --stat --format='%h %s' HEAD)
   ```

   A commit only under `paths.baselines` keeps the pass: `just omc gate passed verify` still holds.
2. **The screenshots.** The regenerated screenshots stay in the tree, uncommitted: this terminal never looks at them,
   judges them, adds, restores or deletes one after the passing run; judging them is `screens-judge`'s.
   `shots_changed` is `true` when `git status --porcelain -- <specs>`, `<specs>` one pathspec per glob of
   `paths.screenshots`, lists any line, else `false` (and `false` when the list is empty).

## The outcome

The report above the line is prose for the orchestrator: every red step and test of each attempt, what each fix
changed, the baselines' advances. The last line is one of:

```text
OUTCOME {"outcome": "passed", "attempts": 1, "shots_changed": true}
OUTCOME {"outcome": "failed", "summary": "2 steps red: slow tests (test/import_test › imports a large file), smoke test (GET / answered 500)"}
OUTCOME {"outcome": "integrity", "problems": ["PROBLEM: pending: …", "PROBLEM: record: …"]}
OUTCOME {"outcome": "needs_user", "question": "…", "options": ["…", "…"], "picked": "…"}
```

`attempts` counts the full runs this terminal started, the passing one included; `summary` names the red steps and
the failing tests of the last attempt; `problems` holds the `PROBLEM` lines of every check but `links-check`.

## Never

- Never judge a screenshot; never add, commit, restore or delete one but in the clean-tree step before a full run.
- Never edit `omc/bin/` or what its command runs to define the gate, never move a step out of `verify`, never skip or
  delete a test to pass.
- Never edit a protected document or the decision log (`paths.decision_log`), never record a decision, never write a
  row into the record or a question file: what needs a ruling is `needs_user`, and the log's own problems are
  `integrity`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and its `OUTCOME` line are
  the whole answer.
- Never run the gate in the foreground, never a run beside another, never stop a run this terminal did not start.
- Never take a partial run or a run started on a dirty tree for the verdict.
- Never `git add -A`, `git add .` or `git add -f`.
