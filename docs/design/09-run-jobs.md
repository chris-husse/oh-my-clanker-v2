# 9. Run jobs: `omc run`

## 9.1 Everything that runs goes through watch

Builds, tests and E2E suites regularly exceed LLM tool timeouts (the 10-minute
tool timeout was a constant pain in v1). So every run is a watch job: the session
starts it, gets an ID back immediately, and checks on it.

## 9.2 Commands

There are exactly three job types: `check`, `e2e-tests` and `ci`. Repos can't
define their own job types.

| Command | Does |
|---|---|
| `omc run check` | Starts a check job: build, unit tests, lint and format. Returns the job ID immediately |
| `omc run check --test <selector>` | Builds what is needed and runs only the selected tests, using the repo's validated rerun snippet (9.5) |
| `omc run e2e-tests` | Starts the E2E suite. Returns the job ID immediately |
| `omc run ci` | Starts the CI job: what the repo's CI runs. The repo's goal for it is that it fails whenever CI would fail. Returns the job ID immediately |
| `omc run <job-type> --job-id <id> status` | JSON status (default action): `queued \| running \| passed \| failed \| stopped \| terminated`, timestamps, failing tests, log path |
| `omc run <job-type> --job-id <id> logs` | The job's output, under the usual output cap with spillover |
| `omc run <job-type> --job-id <id> stop` | Kills the job's process tree (status `stopped`) |

- A `--job-id` that belongs to another job type is an error.
- watch runs jobs in the worktree within its limits: the global job limit, resource
  locks and `isolate_e2e_execution` (03-watch.md §3.6). Jobs need repo trust and an
  integrated repo.
- **Status polls long-poll** up to `run.poll_wait_seconds` (default `100`, local
  config), so each poll returns before Claude's 2-minute Bash timeout. In Codex
  (unified exec, on by default) a 100-second poll isn't killed: the tool call
  returns after its yield time (10 s by default, at most 30 s) with a session ID,
  the command keeps running, and the model reads the result by polling the
  session (`background_terminal_max_timeout`, default 300 s).

## 9.3 Time limit and teardown

Every run job, of every type, is killed one hour after its `run` command was
issued (`run_time_limit_minutes: 60`, written into config). Queue time counts. Its
status becomes `terminated` with reason `Reached execution time limit.`

**One worktree, one run.** An agent never has two `omc run` jobs going on the same
worktree. Every `omc run` (of any job type) first kills everything still running
for that worktree, including a kept-alive E2E environment, then starts its job.

An E2E suite's process tree is killed by watch, never by LLM logic, when any of
these happens:
- the suite **passes**;
- the **1-hour limit** is reached;
- **any new `omc run`** comes from the same worktree.

A failed suite therefore stays up for the fix skill and `/investigate local` until
the next `omc run` from that worktree or the time limit, whichever comes first.

## 9.4 The fix loop

```
omc run <type> → poll status ──passed──▶ done
                     │
                   failed
                     ▼
        run the job type's fix skill: investigate → fix the cause
                     ▼
        omc run <type> again   (Python counts the round)
                     │
       rounds exhausted ──▶ STOP: one CRITICAL report to the user
```

- A strict process: run tool, inspect error, fix error, run tool. Loop until done
  or rounds are exhausted. The LLM fixes the cause and reruns; everything else
  (what to run, in what order, counting rounds, when to stop) is Python's.
- **Separate fix skills per job type**, because they have completely different
  investigation and fix processes.
- **What the fix skill gets:** the failed step, the failing tests, an output
  excerpt and the round number; the job type's inlined hooks (how to diagnose this
  repo); a data file with full logs and links gathered by hooks; and one closing
  instruction: investigate, fix the cause, run `omc run <type>` again.
- **Rounds:** `stages.max_rounds: 6`. Every run after a failure counts as a round,
  including a rerun with no changes. When exhausted, the output is one CRITICAL
  report: what failed, what each round changed, and what answer is needed.
- **A job killed by a watch restart** is marked `failed` with reason *"omc watch
  restarted during the job"* and counts as a round (03-watch.md §3.6).
- **Rerun order:** after a failed round, the next run executes the failed tests or
  step first (fail fast), then the whole job from the top. Only a full pass counts
  as passing. Incremental tools (cargo, make, uv, gradle) keep "from the top" cheap,
  so a build continues where it left off.
- **Tree hash of every pass:** watch records the git tree hash of every full
  pass per worktree and job type. A gate may skip a job whose last full pass ran
  on the identical tree (`ci-gate`, 10-review-lifecycle.md §10.5).
- **No bypass:** a job passes only when every test passes in a full run. There are
  no baseline failures, known-failure lists or skip flags. A red test is a local
  machine problem or a flaky test, and either way it gets fixed. Only Python writes
  the passing verdict.
- **Flaky tests:** debug a test when it fails, but don't chase it when it passes. A
  rerun that passes with no changes passes the job. Python writes a suggestion-box
  entry for every flaky pass (`flaky: <test>`, both outputs, worktree and commit),
  at no LLM cost.

## 9.5 Test snippets generated by `/auto-integrate`

Baking failure detection and single-test reruns into Python is impossible for the
general case, so `/auto-integrate` generates per-repo snippets once, and the LLM
cost is paid only at setup.

- **Two Python snippets per test step**, stored in your omc repo under
  `repos/<key>/stages/<job-type>/`:
  - `detect-failures <log-dir>` prints the IDs of failing tests, one per line;
    empty output means none found;
  - `rerun-tests <id>…` runs exactly those tests; its exit code says pass or fail.

  Standard library only, run with omc's interpreter in isolated mode (`python -I`).
  A generated detector can read JUnit XML internally when a runner produces it
  (parsed with DTDs and external entities disabled).
- **Validation,** in the throwaway scratch worktree:
  1. inventory every language, test framework and runner each step uses,
     including cross-language setups (e.g. a `just check` running cargo and pytest);
  2. run a baseline;
  3. inject one failing test per framework and confirm `detect-failures` finds each;
  4. inject them all at once and confirm one run finds every one;
  5. confirm `rerun-tests` runs each injected test on its own;
  6. remove the injections and confirm everything passes again.

  The snippets and a short validation record are committed to your omc repo as one
  change.
- **At run time:** if a job fails and `detect-failures` returns nothing, the fix
  skill gets the full investigation brief and omc files a suggestion-box report. If
  `rerun-tests` can't do its job (errors, or runs zero tests), the job falls back
  to a full rerun, the LLM is told why, and a report is filed.

## 9.6 The suggestion box

- `repos/<key>/suggestion-box/` in your omc repo, **one file per incident** with
  all its context (what happened, log excerpts, a guess at the cause), committed by
  omc as a guest.
- **`/integrate-suggestions`** is a manual skill: it identifies the most impactful
  suggestion, asks you how to deal with it, and the fix commit removes the file.

## 9.7 E2E keep-alive and `/investigate local`

Keeping an E2E environment alive after a failure is implemented by the repository
itself and wired into its hooks; omc has no generic way to do it. When a repo
provides it (`verify.keep_alive: true`, set by the integration), failed E2E runs can
be debugged with `/investigate local` against the still-running environment. Repos
that can't provide it never get that redirect.

## 9.8 Assumed details (not yet confirmed)

- Fix skill names follow the job types: `/omc:fix-check` and `/omc:fix-e2e-tests`.
