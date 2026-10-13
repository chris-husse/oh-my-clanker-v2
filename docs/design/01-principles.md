# 1. Principles

## 1.1 What v2 is

- **One global `omc watch`** with no arguments manages every omc-enabled repo at
  once and exposes an MCP server agents talk to.
- **Agents request repos.** watch checks a repo out, sets it up (`/auto-index`,
  then `/auto-integrate`) and lists it as usable. Features can then span several
  repos, each with full omc integration: build, test, publish, explain.
- **No repo-local modification.** Nothing omc-specific is written into product
  repos. Integrations, hooks and config live in your omc repo, one folder per repo.
- **Skills are cheap.** Deterministic work is Python in `omc internal`; the LLM
  is the fallback. Skill text is rendered per environment so only what applies is
  loaded. Context stays small enough that a smaller model (astra) runs the flow
  without needing Fable.
- **GitNexus first, then grep docs** for exactly what the graph pointed to, so
  context stays focused.

## 1.2 Cross-cutting rules

- **Python first, LLM as fallback.** Every small step is its own `omc internal`
  command, callable from a skill (for inlining) and from the console (for
  debugging). Example: `omc internal get-repository-id`.
- **Everything that runs is managed by `omc watch`.** Builds, tests and E2E
  suites run as watch jobs, never as long tool calls, because LLM tool calls time
  out (the 10-minute tool timeout was a constant pain in v1). See 09-run-jobs.md.
- **Fail loud.** A misbehaving component (a hook that exits non-zero, oversize
  output, a hook that modifies what it must not) fails the whole skill with a
  precise error. Nothing is silently skipped. A failing hook is a bug to fix.
- **No hidden config.** When a config file is created, every key is written with
  its default. Code never falls back to a value that isn't in a file.
- **CLI = MCP.** Every MCP tool is a CLI command and vice versa, backed by the
  same Python function. The MCP server is "a glorified CLI".
- **No bypass of gates.** A stage passes only when every test passes. There are
  no baseline-failure lists, skip flags or "known failures". Only Python writes a
  passing verdict.
- **Silence is not approval** in any interactive step: only an explicit answer
  to the question asked counts (see the plugins in 07-design-lifecycle.md).
- **Never hand-roll what a vetted package does.** The MCP server uses the
  official `mcp` SDK; the output UI uses `rich`.

## 1.3 Security rules carried into the design

- **No daemons, no persistence.** `omc watch` is a foreground process you run in
  a terminal. omc never starts it in the background, and never installs
  LaunchAgents, cron entries or shell-startup launches.
- **No `$ARGUMENTS` in shell commands.** Claude substitutes `$ARGUMENTS` into a
  skill's `` !`cmd` `` unescaped, so user or ticket text would become shell
  injection. Inputs reach omc through files (the seed is `design/seed.md`).
- **Fetched content is data, never instructions.** Hook STDOUT is inlined as
  skill text, so ticket bodies, pages and other external content go into data
  files that the skill links as "data, not instructions".
- **Typed parameters only** where omc shells out on the LLM's behalf (no raw
  flag passthrough; rg `--pre` / ugrep `--filter` would allow code execution).
- **No unsupervised installs.** omc never installs system packages. It tells
  you the exact command instead.
- **Names and links only, never credentials,** in anything omc writes into your
  omc repo (e.g. the ops survey).
- **`/tmp` files are private:** every omc directory under `/tmp/omc2/` is created
  with mode `0700`.
- **No authentication on the local MCP endpoint** is an explicitly approved,
  documented exception: it binds `127.0.0.1` only, like the existing xtask MCP
  servers in hummingbird-wt (chicken-mcp), with the SDK's host/origin validation on.

## 1.4 Approved dependencies

| Package | Use | Vetting notes |
|---|---|---|
| `mcp` (official Python SDK, FastMCP) | MCP server inside watch, client in the CLI | MIT, Linux Foundation project. Several 2026 advisories (GHSA-9h52 DNS rebinding, GHSA-fmmv request size, GHSA-84m7 sessions, GHSA-w4fh bearer auth): pin the latest patched release at implementation time, host/origin validation on, stateless HTTP, no WebSocket transport |
| `rich` | watch's log output with live progress bars | MIT, Textualize, actively maintained |

Carried from v1: `mininterface` (the `omc configure` UI), `pyyaml`, `filelock`,
`iterm2`. Jinja2 was rejected (template injection on LLM-written hook files, and
no release in 12+ months).

## 1.5 Coexistence with v1

v2 installs and runs alongside v1 without touching it: its own binary (`omc2`),
plugin name, home (`~/.omc2`), fenced section in global instruction files, MCP
server name and port. It is renamed to `omc` at cutover.
