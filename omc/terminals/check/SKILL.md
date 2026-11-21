---
name: check
description: "Run the fast gate, the project's `omc/bin/check` through `just omc gate run check`, started detached and polled; fix and rerun until a full run on a clean tree is green. Ends with a report and its OUTCOME line."
---

# check

A terminal of the `omc/` pipeline, and the skill `/check`. It runs in a fresh subagent of the pipeline (/implement,
/audit), or inline in whoever ran `/check` (the owner, or an agent at any depth); either way it asks nothing of the
owner: it runs the project's fast gate, fixes what is red, runs it again, and ends with its report and one `OUTCOME`
line, its last line. The pipeline reads the line, a caller by hand the report above it; `needs_user` is an outcome its
caller reads and acts on, never a question this skill puts. The gate is the project's own command, `omc/bin/check`:
what it runs is the project's, and this skill does not list it. `just omc gate run check` runs it at the root, its
output streamed and teed to `.cache/omc/gates/check.log` (truncated at each run), and exits with its exit code.

**A full run** is a run without arguments: `just omc gate run check`. A run with arguments (`just omc gate run check
<ARGS…>`, when the project's command takes some to run a part of it) is a partial run: it never records a pass and
never gives the verdict.

**Inputs** (in the prompt, one per line; each has a default, for a `/check` typed without them). `Root:` the worktree;
without it, `git rev-parse --show-toplevel` of the current directory. `commits: new` or `commits: amend`: how the fixes
are committed; without it, `new`. `why` (it may be absent): why the gate runs now (after a task, after a rebase, after
review fixes); it frames the fixes and the report, nothing more.

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
- **Its fixes are committed before the run that gives the verdict**, so that the passing run is a run of a clean tree:
  a run started with uncommitted changes never counts (`just omc gate passed check` does not hold it). Each commit
  stages its paths by name, `git add -- <path>…`. With `commits: new`, one commit per fix, its subject
  `Check fix: <what>`, its message ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. With
  `commits: amend`, `git commit --amend --no-edit` into the branch's one commit. A changed path this terminal did not
  write is neither committed nor discarded by it: `needs_user`, with the paths.
- **One run of this terminal's at a time**: never a run beside another of its own; runs of the gate in other checkouts
  take the machine's slots (`concurrency` of `omc/config.yaml`), and a run waits for one; beyond that slot, never wait
  for another worktree's or session's run (their load is reported, not waited out). The project's command runs its
  steps as it does, and the test runners parallelize inside.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`.

**A run, detached.** `just omc gate run check` is a foreground process: it runs the project's command and ends with
its exit code. A run may outlast a tool call (ten minutes at most), and this terminal's Bash has no background option,
so it starts the run detached, from the worktree, and polls it:

```bash
(cd <root> && rm -f .cache/omc/gates/check.exit && nohup just omc gate run check >/dev/null 2>&1 & echo $!)
```

The line it prints is the run's pid. The run writes its exit code into `.cache/omc/gates/check.exit` when it ends,
beside its log `.cache/omc/gates/check.log`; those two files are the whole of its state. Never a file outside the
worktree (a `/tmp/…` path is shared with the runs of every other worktree), never a wrapper of this terminal's own
around the command. A stop of a run of this terminal's is `kill <pid>`: the run ends its command's group and writes
143. A run whose pid is gone (`kill -0 <pid>` fails) with no exit file died.

## The loop

1. **Clean.** `git status --porcelain` prints nothing (else the rule above).
2. **Start** the run detached, as above. An exit 2 with `error: no gate command omc/bin/check` (or `is not
   executable`, the log's last line) is the project's setup, not a red: `needs_user`, naming it.
3. **Poll.** `(cd <root> && sleep 5 && tail -n 40 .cache/omc/gates/check.log; cat .cache/omc/gates/check.exit)` until
   the exit file holds the code (`cat` fails while the run goes on); read the new lines each time, and analyze a
   failure as it appears.
4. **Stuck?** A log whose last line is `max concurrency of check reached (…); waiting` is a run waiting for a slot
   (`concurrency` of `omc/config.yaml`: other runs of the gate on this machine), not stuck: it starts once one ends,
   and the line comes again each minute. With a `silence` limit for `check` in `omc/config.yaml`, the gate ends a run
   that writes nothing that long itself: the log's last line `no output for <s> s: killed` and exit 124 are a red
   attempt, the step it was in its red step. Without one, the gate never stops a run on its own, and the check is
   this terminal's: the log has not grown for a minute while the run still goes (and is not waiting for a slot): it
   is likely stuck. Read the end of the log; when it is stuck, stop the run (`kill <pid>`): the attempt is red, the
   step it was in its red step. A run that died is a red attempt too.
5. **Done.** The exit file's code and the log are the attempt's report. Exit 0 of a full run started on a clean
   tree, and then `just omc gate passed check` exits 0, ends the loop: the outcome `passed`. Anything else is a red
   attempt (exit 0 with `passed` refused means the run did not start clean: commit, and step 1 starts the next attempt).

## A red attempt

Every red step and failing test the log shows is read, not only the first. Before fixing a red, read
`omc/bin/check.md` when it exists: the project's notes on its reds (known flakes, files a step regenerates,
what a message means); a red it speaks to is handled as it says. For each failure: its message, its excerpt, the log.
Fix it, then rerun what it fixed (a single test in the foreground with the project's test runner, or a partial run,
`just omc gate run check <ARGS…>`, started detached and polled as above), once per fixed failure; a rerun still red
is fixed again without another rerun. A partial run truncates the log: read the full run's log before it. Then commit
the fixes, green or not, and a full run from step 1 is the next attempt, where a failure still red counts. A partial
run never gives the verdict.

## The lock

`just omc gate run` takes only a slot of the gate's machine-wide limit (`concurrency`; absent: one) and waits for one;
it takes no lock of this worktree: one run at a time here is this terminal's own discipline. Never start a run while an
earlier one of this terminal's is still going (its exit file is not written and its pid lives). A run this terminal
did not start that holds what the project's command needs (its error names a lock, a port or a process held) is never
stopped: the owner may have started it. `needs_user`, naming what holds it, with the options to wait for it or to stop
it.

## The outcome

The report above the line is prose for the orchestrator: every red step and test of the last attempt, what each fix
changed and its commit. The last line is one of:

```text
OUTCOME {"outcome": "passed", "attempts": 2}
OUTCOME {"outcome": "failed", "summary": "2 steps red: unit tests (test/parser_test › reads an empty file), lint (src/io.py:12: unused import)"}
OUTCOME {"outcome": "needs_user", "question": "…", "options": ["…", "…"], "picked": "…"}
```

`attempts` counts the full runs this terminal started, the passing one included; `summary` names the red steps and
the failing tests of the last attempt.

## Never

- Never edit `omc/bin/` or what its command runs to define the gate, never move a step out of the gate, never skip or
  delete a test to pass.
- Never edit a protected document or the decision log (`paths.decision_log`), never record a decision, never write a
  question file: what needs a ruling is `needs_user`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and its `OUTCOME` line are
  the whole answer.
- Never take a partial run, or a run started on a dirty tree, for the verdict.
- Never start a run beside another of this run's, and never stop a run this terminal did not start.
- Never `git add -A`, `git add .` or `git add -f`.
