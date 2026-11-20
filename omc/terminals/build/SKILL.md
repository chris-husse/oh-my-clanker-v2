---
name: build
description: "Run the project's build, `omc/bin/build` through `just omc gate run build` (no tests), started detached and polled; fix and rerun until a whole run on a clean tree exits 0. Ends with a report and its OUTCOME line."
---

# build

A terminal of the `omc/` pipeline, and the skill `/build`. It runs in a fresh subagent of the pipeline (/audit), or
inline in whoever ran `/build` (the owner, or an agent at any depth); either way it asks nothing of the owner: it runs
the project's build, fixes what fails, runs it again, and ends with its report and one `OUTCOME` line, its last line.
The pipeline reads the line, a caller by hand the report above it; `needs_user` is an outcome its caller reads and acts
on, never a question this skill puts.

**What it builds.** The project's own command, `omc/bin/build`: what it builds is the project's, no tests.
`just omc gate run build` runs it at the root, its output streamed and teed to `.cache/omc/gates/build.log`
(truncated at each run), and exits with its exit code.

**Passing: exit code 0.** Any failing command fails the run; the report names the first failing command and its
error. A pass is recorded only for a whole run (`just omc gate run build`, no arguments) that exits 0 and started on a
clean tree; `just omc gate passed build` then confirms it. The passing run is therefore always a whole run, from its
first command, on a clean tree.

**Inputs** (in the prompt, one per line; each has a default, for a `/build` typed without them). `Root:` the worktree;
without it, `git rev-parse --show-toplevel` of the current directory. `commits: new` or `commits: amend`: how the fixes
are committed; without it, `new`. `why` (it may be absent): why the gate runs now; it frames the fixes and the report,
nothing more.

**A gate terminal's rules** (`check`, `build` and `verify` each say them):

- **It fixes and reruns inside itself.** An attempt is one whole run of the build. A failed attempt made progress
  when fewer commands or fewer errors fail than in the run before it (the first is compared with nothing). The
  terminal ends with `failed` at the tenth failed attempt, or at the second failed attempt that made no progress.
- **A fix repairs the code under test**, never the gate's definition: nothing under `omc/bin/` (the command or its
  notes), never a recipe or script the command runs to define the build, never a build step dropped or a check of the
  build switched off to pass.
- **A fix that needs a protected document** (a file matched by `paths.protected` of `omc/config.yaml`) **or a
  ruling** edits nothing of it: the terminal commits the fixes it has made and returns `needs_user` with the question,
  its options and the answer it would pick.
- **Its fixes are committed before the run that gives the verdict**, so that the passing run is a run of a clean tree
  (`git status --porcelain` prints nothing before it starts). Each commit stages its paths by name,
  `git add -- <path>…`. With `commits: new`, one commit per fix, its subject `Fix: <what>`, its message ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. With `commits: amend`, `git commit --amend --no-edit` into
  the branch's one commit. A changed path this terminal did not write is neither committed nor discarded by it:
  `needs_user`, with the paths.
- **One build of this terminal's at a time**: never in parallel with another build, test or render of its own;
  `just omc gate run` waits only for a slot of the gate's machine-wide limit (`concurrency` of `omc/config.yaml`;
  absent: one) and takes no lock of this worktree, so the rest is the terminal's own discipline. Beyond that slot, never
  wait for another worktree's or session's run (their load is reported, not waited out).

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`.

**A run, detached.** `just omc gate run build` is a foreground process: it runs the project's command and ends with
its exit code. A build may outlast a tool call (ten minutes at most), and this terminal's Bash has no background
option, so it starts the run detached, from the worktree:

```bash
(cd <root> && rm -f .cache/omc/gates/build.exit && nohup just omc gate run build >/dev/null 2>&1 & echo $!)
```

The line it prints is the run's pid. The run writes its exit code into `.cache/omc/gates/build.exit` when it ends,
beside its log `.cache/omc/gates/build.log`; read the two every 30 seconds until the exit file holds the code (`cat`
fails while the run goes on):

```bash
(cd <root> && sleep 30 && tail -n 40 .cache/omc/gates/build.log; cat .cache/omc/gates/build.exit)
```

Never a file outside the worktree (a `/tmp/…` path is shared with the runs of every other worktree), never a wrapper of
this terminal's own around the command. A run whose pid is gone (`kill -0 <pid>` fails) with no exit file died: the
attempt starts again from step 1. An exit 2 with `error: no gate command omc/bin/build` (or `is not executable`, the
log's last line) is the project's setup, not a failure: `needs_user`, naming it. Never start a second build while the
first is running.

## The loop

1. **Clean.** `git status --porcelain` prints nothing (else the rule above).
2. **Run** the build as above. Exit 0, and then `just omc gate passed build` exits 0: the outcome `passed`.
3. **Failed.** Before fixing, read `omc/bin/build.md` when it exists: the project's notes on its reds; a failure it
   speaks to is handled as it says. Read the first failing command and its error, and the errors after it. Fix the
   code, commit the fixes, and step 1 starts the next attempt.

## The outcome

The report above the line is prose for the orchestrator: the failing command and its error of each attempt, what each
fix changed and its commit. The last line is one of:

```text
OUTCOME {"outcome": "passed", "attempts": 1}
OUTCOME {"outcome": "failed", "summary": "compile: src/report.ts:41: cannot find name 'dueDay'"}
OUTCOME {"outcome": "needs_user", "question": "…", "options": ["…", "…"], "picked": "…"}
```

`attempts` counts the whole runs this terminal started, the passing one included; `summary` names the first failing
command of the last attempt and its error.

## Never

- Never edit `omc/bin/` or what its command runs to define the build, never drop a build step to pass.
- Never edit a protected document or the decision log (`paths.decision_log`), never record a decision, never write a
  question file: what needs a ruling is `needs_user`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and its `OUTCOME` line are
  the whole answer.
- Never run two builds at once, or a build beside a test or a render.
- Never `git add -A`, `git add .` or `git add -f`.
