# 3. `omc watch`

## 3.1 One instance, no arguments

- `omc watch` takes no arguments. It reads local config for user and machine
  settings, and your omc repo for repos and shared settings.
- It runs in the **foreground** in a terminal tab. It is not a daemon, not a
  LaunchAgent, and omc never starts it in the background.
- An instance lock (`~/.omc2/watch.lock`) allows exactly one watch per machine. A
  second start exits and names the PID holding the lock.
- You never interact with watch directly. You use the `omc` CLI, which talks to
  watch when it needs to. Commands that need watch exit with
  *"omc watch is not running — start it in a terminal"* when it isn't.
- The MCP server (04-mcp-and-cli.md) runs inside this process.

## 3.2 Known repos

The source of truth is `repos/*/repo.yaml` in your omc repo. On start and every
tick, watch reconciles against it: a new folder is cloned and set up; a deleted
folder stops being watched (its hidden clone is removed once no worktrees remain).
watch also syncs your omc repo itself (3.3).

## 3.3 Sync every tick

The tick is `watch.tick_seconds` in local config.

- **Hidden clones:** fetch, then `git reset --hard origin/<base>`. Nobody edits
  these clones, so a hard reset is safe. Re-index if HEAD moved; re-document if
  docs are on and the freshness rules allow it (3.7).
- **Your omc repo:**
  1. Fetch.
  2. Write a backup ref, `refs/omc/backup/<timestamp>`, recording HEAD. Backups
     are kept for 30 days.
  3. `rebase --autostash` onto its upstream.
  4. On conflicts (between commits, or re-applying your uncommitted edits), a
     headless session on your default LLM resolves them.
  5. If that fails, `rebase --abort` restores HEAD and your autostashed edits
     exactly; the backup ref is the second safety net.
  6. watch then prints `omc repo: could not sync — <reason>` every tick until
     the conflict is fixed.
- omc never pushes your omc repo (02-repos-and-config.md).

## 3.4 Setup: `/auto-index`, trust, `/auto-integrate`

```
requested → cloning → /auto-index → queryable → [awaiting trust] → /auto-integrate → integrated
                          ↘ failed: auto-index                          ↘ failed: auto-integrate
```

- **`omc repo list`** (and its MCP tool) shows each repo's state, e.g. `usable`,
  `setting up (indexing 43%)`, `failed setup: auto-index — <reason>`,
  `queryable — awaiting trust`, `integrated (may be stale: <reason>)`, so an LLM
  knows what it can and can't do with a repo.
- A failed setup is retried only when an input changes: a new origin commit or
  an edit to the repo's folder in your omc repo. v1 learned not to loop on an
  unchanged failure.

### `/auto-index` → queryable

Reads code only, so it needs no trust:
- GitNexus indexing of the hidden clone;
- detection of the repo's doc paths (`docs.paths`);
- a **context survey** that writes the repo's explain context (the
  `design:explain-context` hook contribution: where truth lives, conventions);
- an **ops survey** that records what `/investigate` needs: the environments that
  exist and links to logs, metrics, databases, hosts and anything else useful for
  investigations. **Names and links only, never credentials.**

A repo becomes queryable once GitNexus and these surveys are done. Whether
`/auto-index` also generates the GitNexus wiki is open (open-questions.md).

### Trust

Anything that runs the repo's code waits for trust (02-repos-and-config.md).
Polling the add-repo job (`omc internal add-repo --poll <job-id>`) returns
`queryable — awaiting trust: ask the user to run omc repo <repo> trust`, so an
agent that requested the repo knows what to tell you.

### `/auto-integrate` → integrated

- **Runs the repo's code**, after trust, in a **throwaway scratch worktree** in
  the cache, cut from the hidden clone at `base` (never the hidden clone itself,
  never one of your worktrees), under the job limit and E2E isolation.
- **Goal: always a decent setup with sane defaults.** Not perfect, maybe
  incomplete, but something that builds, runs tests and, where possible, runs E2E.
- **Build failures** on `base`: the LLM fixes them in the scratch worktree and
  learns the repo along the way. Whatever made the build work is recorded as setup
  in `repo.yaml` or the build hook.
- **Red tests on `base` don't block it**; real failures help validate detection.
- It may run setup the repo declares (`uv sync`, `npm ci`, `cargo fetch`,
  `just setup`); it never installs system tools (02-repos-and-config.md).
- It generates and validates the **test snippets** (09-run-jobs.md): framework
  inventory, injected failures per framework and all at once, targeted reruns.
- It builds the **`ci` job** from the repo's CI configuration (GitLab CI, GitHub
  workflows), covering what `check` and `e2e-tests` don't, so that `ci` fails
  whenever the repo's CI would; it validates it in the scratch worktree.
- `check`, E2E and `ci` jobs refuse with *"not available: auto-integrate in
  progress (validating jest snippets 2/4)"* until the repo is integrated.
- **E2E keep-alive** is the repo's own job: it must be implemented in the
  repository and wired into its hooks; omc can't do it generically. The
  integration sets `verify.keep_alive: true` in `repo.yaml` when the repo
  provides it. Only then do failed E2E runs redirect to `/investigate local`
  with the environment still up.

## 3.5 Concurrency

### What a write is

A write is a job that changes state another job reads. State is split into
pieces, each with its own read/write lock with basic fairness (a waiting writer
blocks new readers). Repos run in parallel.

| Piece | Changed by | Read by |
|---|---|---|
| **setup** | clone, `/auto-index`, `/auto-integrate`, the first index | everything: until queryable, every operation fails with *"Repository not ready: indexing"*; build/test until integrated |
| **refs** (hidden clone branches and checkout) | sync (fetch + reset) | worktree creation, index build |
| **index** (GitNexus store) | index swap | `gitnexus` queries |
| **docs** (wiki in the cache) | docs swap (atomic directory rename) | `docs_grep` |
| **omc repo** | its sync/rebase, omc's commits, `configure` writes | hook rendering, config reads |

A sync blocks worktree creation for a few seconds. A sync that finds `refs` busy
skips that tick.

### Re-indexing doesn't block queries

GitNexus already serves the old index while it rebuilds (traced in the fork at
`20c559d2`): queries open the store read-only, full rebuilds build into
`lbug.staging.<uuid>` and rename over the live store, and incremental rebuilds do
the same when `GITNEXUS_ATOMIC_INCREMENTAL=1` is set.

- omc sets `GITNEXUS_ATOMIC_INCREMENTAL=1` and `GITNEXUS_SHARED_STORE=off` for
  every analyze, in the one place that builds child-process environments.
- **The in-place exception:** if the live store has leftover WAL/shadow side
  files, GitNexus edits in place. watch checks for them before each analyze and,
  if found, holds the index write lock for that run.
- **Reads wait at most `watch.read_wait_seconds`** (default `30`), then fail fast
  with a message naming what is running, e.g.
  *"Index not ready. Try again later (indexing 43%)"*.
- GitNexus always indexes the hidden clone; no worktree is ever indexed.
- **Test:** an E2E test runs queries in a loop during an incremental analyze of a
  real repo and asserts every query succeeds with either the old or the new result.

## 3.6 Scheduling

- **One global limit, `watch.max_parallel_jobs: 10`** (local config), shared by
  every job type: run jobs, indexing, docs generation, `/auto-integrate`. There
  is no load-based gating.
- **E2E isolation is per repo:** `isolate_e2e_execution: false` by default in
  `repo.yaml`. When `true`:
  - nothing else runs while that repo's E2E suite runs: every other watch job on
    the machine waits (other repos' jobs, indexing, docs, integration);
  - lightweight work keeps going: git fetches, GitNexus queries, `docs_grep`,
    status calls and skill rendering;
  - it gets priority by **draining**: once queued, no new jobs start, running ones
    finish, then it runs alone. Isolated suites from different repos run one
    after another.
- **Job state is persisted** in `~/.omc2/`. On start, any job still marked
  `running` belonged to a previous watch. It is marked `failed` with reason
  *"omc watch restarted during the job"*, and that counts as a failed round.

## 3.7 Freshness checks

- **Docs** (only for repos with `documentation: true`): a rerun is considered
  only after the interval, the longer of the repo's and the local
  `documentation.min_interval_days`. Then an LLM "substantial change" check
  decides whether enough architectural change came in to justify one.
- **Integration:** a quick pass once a day looks for noteworthy changes to test
  infrastructure, the build system or CI. If found, watch logs it, the repo shows
  `integrated (may be stale: <reason>)`, and tool output tells the LLM the
  integration info may be stale or incomplete, so it warns you to run
  `/integrate` again. There is no automatic rerun.
- **How:** once a day Python collects every repo's commits (message, files
  touched, lines changed per file) into one dossier, and one cheap call
  (`simple` slot of the `watch` block, via the harness CLI) makes both decisions
  for every repo. Estimated at ~$0.20–0.40/day for 40 repos at Sonnet 5.5 list
  prices ($2/M input, $10/M output); on a subscription it uses plan quota instead.

## 3.8 `/tmp` retention

Everything omc writes under `/tmp/omc2/` (`temp/`, `spillover/`, `lifecycle/`)
follows one rule. Each tick, watch deletes folders older than
`tmp_retention_days: 14`. Once a day it measures the total size, and if it
exceeds `tmp_max_gb: 100`, it deletes the oldest day folders first until under.
Both are local config values.

Session memories (12-session-memory.md) follow their own rule: watch clears a
branch's `~/.omc2/sessions/` subfolder once it has been unmodified for a month.

## 3.9 Output

- **An append-only log, not a UI.** New lines append at the bottom; live progress
  bars for running jobs stay pinned below them; there is no interactivity. Built
  on `rich` (`Live` + `Progress` with `console.log`).
- Example lines:
  - `12:01:03 hummingbird-bridge-1a2b3c4d  ✓ fetched (3 new commits)`
  - `12:01:04 hummingbird-bridge-1a2b3c4d  ◐ indexing ━━━━━╸━━━━ 43%`
  - `12:01:30 omc repo  ⚠ 5 commits unpushed since 2026-10-01`
- Each job writes its full log to `~/.omc2/repos/<key>/logs/<job>.log`, and the
  log line points at it.
