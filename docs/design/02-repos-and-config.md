# 2. Repos, your omc repo, config and trust

## 2.1 Repo identity

- **SSH only.** Accepted forms: `git@host:group/name.git` and
  `ssh://user@host[:port]/group/name.git`. An HTTPS URL is refused, with the SSH
  form to use instead. SSH gives one canonical identity to hash.
- **Canonical form:** `ssh://<user>@<host>[:<port>]/<path>`. The short
  `git@host:path` form is rewritten into it. Host lowercased; user, port and path
  kept as given; port 22 dropped; trailing `.git` and `/` stripped.
- **Repo key:** `{name}-{hash8}`. `name` is the last path segment; `hash8` is the
  first 8 hex characters of SHA-256 over the canonical form.
  Example: `git@github.com:chris-husse/oh-my-clanker.git` → `oh-my-clanker-<hash8>`.
- One pure function, unit-tested against a table of URL forms.
  `omc internal get-repository-id` exposes it.

## 2.2 Three places things live

| Where | What |
|---|---|
| **Your omc repo** (a git checkout you own; its path is in local config) | Which repos exist (`repos/<key>/repo.yaml`) and everything that can be shared: root `config.yaml`, per-repo settings, hooks, facts, test snippets, the suggestion box, design artifacts (when `design_artifact_root: omc`), and anything else of yours |
| **Local config** (`~/.omc2/config.yaml`) | Only what is specific to you or this machine ([2.5](#2.5%20Config)) |
| **Cache** (`~/.omc2/`) | Data that can be rebuilt: hidden clones, GitNexus stores, wiki docs of repos with docs on, per-branch data, logs |

Clone your omc repo on a new machine, run `omc watch`, and every repo in it is
checked out and indexed.

## 2.3 Your omc repo

### Ownership

- **You own it.** You edit it by hand however you like: skills, hooks, notes,
  anything. omc is a guest.
- **Everything that already exists is yours.** omc creates files that don't exist
  yet, and changes an existing file only for a specific, requested change. It
  never rewrites a whole file and never regenerates over your edits.
- **Your uncommitted changes are off-limits.** If a file omc needs to change has
  uncommitted edits, omc leaves it alone and reports which file and why.
- **Unknown files and folders are yours.** omc never reads, moves or removes them.
- omc reads the **working tree** directly, so an uncommitted hook edit takes
  effect on the next render.

### Writes

- **watch makes every write.** Sessions and `omc internal …` commands ask watch,
  which makes the edit and commits.
- **One commit per logical change group,** with a proper message, e.g.
  `hummingbird-bridge-1a2b3c4d: auto-integrate (check, e2e snippets; explain-context)`,
  `config: hummingbird-bridge-1a2b3c4d documentation on`. Commits are path-limited
  to omc's own files and never stage your other changes.
- **omc never pushes it.** Pushing is yours. watch warns when the oldest
  unpushed commit is more than 7 days old, e.g.
  `⚠ omc repo: 5 commits unpushed since 2026-10-01`.
- Sharing with a team is possible but not a goal; the repo is personalized.

### Layout omc depends on

```
<your omc repo>/
  config.yaml                         # shared settings (2.5)
  hooks/<lifecycle>/<hook>/<name>.md  # global hook contributions (company)
  hooks/<lifecycle>/<hook>/<name>     #   …or executable contributions
  facts/<name>                        # global facts (05-skill-rendering.md)
  repos/<name>-<hash8>/
    repo.yaml                         # per-repo settings (2.5)
    hooks/<lifecycle>/<hook>/…        # repo hook contributions
    facts/<name>                      # repo facts
    stages/<job-type>/…               # validated test snippets (09-run-jobs.md)
    suggestion-box/<incident>.md      # integration incidents (09-run-jobs.md)
    docs/…                            # design artifacts, when design_artifact_root: omc
```

Everything else in the repo is yours and ignored by omc. Where global and repo
lifecycle plugins live is still open ([open-questions.md](open-questions.md)).

### Removing a repo

Delete `repos/<key>/`. watch stops watching it; the hidden clone is removed once
no worktrees remain under its folder.

## 2.4 The cache (`~/.omc2/`)

```
~/.omc2/
  config.yaml                       # local config
  watch.lock                        # instance lock
  repos/<repo-key>/
    clone/                          # hidden clone + its .gitnexus store
    docs/                           # wiki cache, when documentation is on
    branches/<branch-file>/         # per-branch data
    logs/                           # watch job logs for this repo
  sessions/<repo-key>/<branch-file>/
    optmem/                         # the branch's session memory (12-session-memory.md)
```

- **Hidden clones** are full clones only watch touches. They always sit on the
  tip of `origin/<base>`, and their path is never handed to a session, so nobody
  edits them.
- **`<branch-file>`** is the branch name turned into a directory name:
  percent-encode everything outside `[A-Za-z0-9._-]`, then append `-` and the
  first 8 hex characters of SHA-256 of the exact branch name. Example:
  `feature/omc-v2-from-scratch-design-docs` →
  `feature%2Fomc-v2-from-scratch-design-docs-3f9a1c2e`. Deterministic, readable,
  and safe on case-insensitive filesystems.
- **Per-branch data** is scoped by repo and branch, found from the worktree's
  origin URL and `git rev-parse --abbrev-ref HEAD`. Its folder is deleted when
  the branch's worktree is closed through omc, plus a watch sweep for folders
  whose branch no longer exists locally or on origin and that are untouched for
  `features.retention_days` (default `30`, local config).
- **Wiki docs** live only here, and only for repos with `documentation: true`
  (off by default).

### Worktrees

Worktrees are created under the user's `worktree_location`, grouped by repo:
`<worktree_location>/<repo-key>/<slug>`. They are created through worktrunk
(`wt -C <hidden clone> switch --create … --no-cd --yes`); no `wt.toml` is
written into any repo.

## 2.5 Config

### The split

| File | Holds |
|---|---|
| **Local** `~/.omc2/config.yaml` | omc repo location, `worktree_location`, auth, server addresses, per-lifecycle providers and models, `trusted_repos`, machine limits (`watch.tick_seconds`, `watch.max_parallel_jobs`, `watch.read_wait_seconds`, `mcp.port`, `mcp.output_max_chars`, `/tmp` retention, run time limit, …) |
| **Shared** `<omc repo>/config.yaml` | Defaults for every repo: `branch_prefix`, `design_artifact_root`, `documentation`, global docs paths, hook-layer switches, lifecycle plugin lists |
| **Per repo** `repos/<key>/repo.yaml` | `ssh_url`, `base_branch`, `branch_prefix`, `design_artifact_root` / `design_artifact_directory`, `documentation` and its interval, `docs.paths`, `isolate_e2e_execution`, `verify.keep_alive`, lifecycle overrides, hook-layer switches |

`repo.yaml` wins over the shared `config.yaml`. The heavy-job limit is local
because it depends on the machine.

### Per-lifecycle providers and models

Local config has one block each for `design`, `implement`, `review` and `watch`.
Each block has a `provider` and the `models` for every task slot, all written
out with defaults. Design can run top-tier while implement runs lighter and
review sits in between. The `watch` block covers `/auto-index`,
`/auto-integrate`, the daily freshness check and suggestion-box reports.
`create-slug` uses `design.models.simple`. Every major command
(`omc design|implement|review`) also takes `--claude` / `--codex`.

### Design artifact location

```yaml
design_artifact_root: omc            # default: your omc repo, repos/<key>/docs/
# design_artifact_root: repository
# design_artifact_directory: docs    # only when the root is `repository`
```

### `omc configure`

- Manages **all** config, local, shared and per repo, with v1's navigable menu
  (mininterface). A **Repositories** section lists every repo and opens its
  `repo.yaml` settings.
- Changes to your omc repo are committed as one logical change group.
- Each setting can name the `omc internal` command that applies it; changing the
  value runs that command (e.g. turning `shell.fish_title` off runs
  `omc internal shell-integration fish disable`).
- **`omc update`** runs `omc configure --reapply`: non-interactive, reads and
  writes the config once (your values unchanged, only new keys get their
  defaults), then runs every setting's apply command, in parallel where safe.

## 2.6 Trust

- **Code execution needs trust.** Before anything builds, tests or otherwise runs
  a repo's code, you confirm that you trust the repo.
- **Every repo is index-only unless explicitly listed.** An index-only repo is
  cloned, GitNexus-indexed and queryable ([14 §14.1](14-cross-repo-features.md#14.1%20Reading%20other%20repos%20while%20working%20on%20one%20(MVP))), and
  nothing of it ever runs: no `/auto-integrate`, no setup, no `omc run` job.
  Anything that runs build scripts must be explicitly listed.
- **The list has two kinds of entry:** single repos (`trusted_repos`) and whole
  **mirrors** (`trusted_mirrors`), for example a company's Git host or group,
  given as an SSH URL prefix (`git@gitlab.example.com:company/`). A repo is
  trusted when it is listed or its SSH URL starts with a trusted mirror's prefix.
- **External mirrors are index-only in a multi-repo chain.** A repo whose URL is
  under no trusted mirror can never be part of a multi-repo chain
  ([14 §14.2](14-cross-repo-features.md#14.2%20Changing%20several%20repos%20in%20one%20feature%20(not%20MVP;%20a%20design%20guideline))), apart from GitNexus indexing.
- **The trust commands are user-only.** `omc repo <repo> trust` and
  `omc repo trust --mirror <ssh-url-prefix>` are CLI commands only: never MCP
  tools (the one exception to "CLI = MCP", [01 §1.2](01-principles.md#1.2%20Cross-cutting%20rules)), never
  pre-approved in any stub's `allowed-tools`, and every skill forbids the agent to
  call them. An agent that needs a repo trusted tells you the command.
  Assumed: both also refuse to run without an interactive terminal.
- **How you're asked:** watch sends a plain macOS notification via `osascript`
  (no new dependency): *"omc: trust hummingbird-bridge? It will try to build and
  test it. Run `omc repo hummingbird-bridge trust`."* The request also shows in
  watch's log until answered. You answer with `omc repo <repo> trust` or in the
  Repositories section of `omc configure`.
- **Where it's stored:** local config, `trusted_repos` and `trusted_mirrors`,
  because trust grants code execution on this machine. On a new machine,
  trusting your company's mirrors covers most repos at once.
- **What it covers:** every code execution watch does for that repo:
  `/auto-integrate` and every `omc run` job. Indexing, doc surveys and queries
  don't need it.
- **System tools are never installed.** If a build needs an undeclared tool
  (e.g. `protoc`), omc notifies you with the exact command
  (`brew install protobuf`) and records it in watch's log and the suggestion box.
  The repo stays `integrated (partial: missing protoc)` until you install it and
  rerun `/integrate`. Setup the repo itself declares (`uv sync`, `npm ci`,
  `just setup`, pinned by its lockfiles) runs automatically once trusted.
