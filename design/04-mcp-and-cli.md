# 4. MCP server and CLI

## 4.1 The server

- watch hosts MCP with the official `mcp` SDK's FastMCP, over **streamable HTTP**
  at `http://127.0.0.1:<mcp.port>/mcp`. `mcp.port` defaults to `47850` (local
  config), next to chicken-mcp's 47839–47842 without overlap.
- Binds `127.0.0.1` only. **No authentication** (approved exception, see
  01-principles.md). The SDK's host and origin validation is on.
- **Stateless HTTP mode** (`stateless_http=True`): every call is independent, so
  no MCP sessions accumulate.
- Harnesses connect to it like any other HTTP MCP server. `omc update` (and the
  first `omc configure`) registers it once per user and repairs drift:
  - Claude: `claude mcp add --transport http --scope user omc2 http://localhost:47850/mcp`
  - Codex: `[mcp_servers.omc2] url = "http://localhost:47850/mcp"` in `~/.codex/config.toml`

## 4.2 The CLI is an MCP client

Every repo command calls the matching tool on watch over the same endpoint and
prints exactly what the tool returns. One implementation, one output format.
Commands that work without watch stay local: `watch`, `configure`, `update`,
`uninstall`, `version`, and the session launchers.

## 4.3 Tools

| MCP tool | CLI | What it does |
|---|---|---|
| `repo_list` | `omc repo list` | One line per known repo: key, setup state, indexed commit vs tip, docs on/off |
| `repo_add(ssh_url)` | `omc internal add-repo <ssh-url>` | Registers the repo (creates `repos/<key>/repo.yaml`, commits it), queues setup and returns a job ID at once. Adding a known repo returns a job that reports its state |
| `repo_add_poll(job_id)` | `omc internal add-repo --poll <job-id>` | Waits up to a minute, then returns the repo's info (key, setup state, indexed commit) or a pending info with watch's current checklist |
| `gitnexus(repo, verb, args)` | `omc repo <repo> gitnexus <verb> …` | `query`, `context`, `impact`, `cypher` against the repo's index (one tool with a `verb`, so one schema per turn instead of four) |
| `docs_grep(repo, …, scope)` | `omc repo <repo> docs-grep …` | Searches the configured docs context (4.4) |
| `worktree_create(repo, slug)` | `omc repo <repo> worktree create <slug>` | Creates the branch from `origin/<base>` under `<worktree_location>/<repo-key>/<slug>` |

- **Repo arguments** accept a key, a unique name or an SSH URL, matched with the
  same Python lookup `omc design` uses. Ambiguous or unknown names fail and list
  candidates.
- **Repo additions never cancel each other.** Unlike run jobs (one run per
  worktree, 09-run-jobs.md §9.3), a branch can add ten repos in parallel and poll
  each job.
- **Finding unknown repos is the agent's job.** This happens constantly as a
  design finds dependencies and repos that need changes: the agent finds the SSH
  URL with its own forge tools (GitLab/GitHub), then calls `repo_add` and polls the job. omc never
  searches a forge itself.

## 4.4 `docs_grep`

- **What is searched:** the full configured docs context:
  - each repo's configured doc paths (`repo.yaml` → `docs.paths`, set by setup
    or by you), read from the hidden clone at `base`;
  - that repo's GitNexus wiki, when `documentation: true`;
  - the global docs (`config.yaml` → `docs.global_paths`, paths inside your omc
    repo, e.g. a `knowledge/` folder).
- **`scope`:** `repo` (default) searches that repo's doc paths and wiki;
  `global` searches every known repo's docs plus the global docs (the `repo`
  argument is then optional).
- **Output paths are display paths**, never filesystem paths, so hidden-clone and
  cache paths never reach a session: `hummingbird-bridge-1a2b3c4d:docs/ingestion.md:42: …`,
  `wiki:hummingbird-bridge-1a2b3c4d/alerts.md:7: …`, `global:knowledge/release.md:3: …`.
- Takes a read lock on each searched repo's `docs` piece.
- **ripgrep, run by watch with typed parameters only:** `pattern`, `glob`,
  `ignore_case`, `context` (0–5), `files_only`. omc builds the argv itself, with
  no shell. Raw flag passthrough is ruled out: LLM arguments are untrusted under
  prompt injection, and rg `--pre` / ugrep `--filter` would run arbitrary code.
  Behind typed parameters the engine can be swapped later.

## 4.5 Output cap for all tool output

- One wrapper in watch around the SDK's tool-call handler caps every tool result
  at `mcp.output_max_chars` (default `20000`, local config). No individual tool
  implements the cap; the CLI prints the tool result unchanged, so it gets the
  same cap.
- Past the cap, the result is cut and ends with:
  `… truncated at 20000 characters. Narrow the request. Full output was written to /tmp/omc2/spillover/2026-10-09/<random-id>.txt`
- Spill directories are created with mode `0700`. Retention follows
  03-watch.md §3.8.
- Output is compact text (`file:line`, `symbol (kind) file:line`,
  `key  state  commit`), not prose. JSON only where a skill parses it.
- Errors are short and say what to do next: *"Index not ready. Try again later
  (indexing 43%)"*, *"Repository not ready: indexing"*,
  *"failed setup: auto-index — <reason>"*.

## 4.6 Command tree

User-facing:
```
omc watch
omc configure
omc update | uninstall | version
omc design <repo-hint> "<seed>" [--claude|--codex] [--headless]
omc implement [--claude|--codex] [--headless]
omc review [--claude|--codex] [--headless]
omc publish [--claude|--codex] [--headless]
omc resume                                  # parked
omc repo list
omc repo add <ssh-url>
omc repo trust --mirror <ssh-url-prefix>     # user-only, never an MCP tool
omc repo <repo> status | wait
omc repo <repo> trust                       # user-only, never an MCP tool
omc repo <repo> gitnexus query|context|impact|cypher …
omc repo <repo> docs-grep …
omc repo <repo> worktree create <slug>
omc lifecycle <lifecycle> [--<plugin> | --done <plugin> | --from <plugin>]
omc hooks --help | --list
omc hooks <lifecycle> <hook>
omc run <job-type> [--test <selector>]
omc run <job-type> --poll <job-id>
omc run <job-type> --job-id <id> logs|stop
```

There is no user-facing `omc install`. Bootstrapping after `uv tool install` goes
through `omc internal install` if needed at all.

### `omc internal`

- Every small step is an `omc internal <cmd>`, usable from skills and the console.
- The group is **hidden** from `omc --help`; `omc internal --help` lists it.
- Commands named so far: `get-repository-id`, `check-watch`, `resolve-repo`,
  `find-repo`, `create-slug`, `ensure-repo`, `branch-name`, `branch-dir`,
  `create-worktree`, `close-worktree`, `title set|release|apply`,
  `shell-integration fish enable|disable|status|reconcile`, `temp-dir`,
  `check-artifact`, `design-sections`, `design-artifact`, `install`.

### `omc hooks`

- `omc hooks --help` lists every hook type omc defines, with its contract
  (what it receives, how its outputs are merged).
- `omc hooks --list` walks the environment and shows the active hook
  contributions: which markdown files and executables make up each hook, and
  whether each comes from omc, global or the repo.
- `omc hooks <lifecycle> <hook>` (e.g. `omc hooks design hardening`) shows the
  merged result for that hook.

## 4.7 Tab titles

Tab titles are a day-one feature. They carry v1's behaviour: the iTerm2 tab is
pinned to the literal branch, with the fish hook under `conf.d`.
- The commands are internal: `omc internal title set|release|apply`. The fish
  hook and `omc design` call them under that name.
- Shell integration is a config setting (e.g. `shell.fish_title`). `omc
  configure` runs `omc internal shell-integration fish enable|disable` when it
  changes, and `omc update` reapplies it.
- `omc design` titles the tab from its first command.
