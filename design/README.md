# omc v2 design

omc v2 is a from-scratch rearchitecture of oh-my-clanker. v1 (the `oh-my-clanker`
repo) is evidence to borrow from, not a template. Its reference write-up lives in
the v1 repo (`docs/v1-reference/omc-v1-design.md`), never here.

This folder (`design/`) holds only the v2 high-level design; it is protected (13-testing.md). Per-feature designs live in `docs/design/`. It is written as the design discussion
goes, and every settled decision is recorded here. Anything not yet decided is
in [open-questions.md](open-questions.md), with its full options.

## MVP

The MVP is everything in this folder **except** what is marked parked or
"not part of the MVP" (currently: the product design workflow feature, 13 §13.1,
and the parked topics in open-questions.md §B and §H). That includes all four
lifecycles: design, implement, review and publish.

## Documents

| # | Document | Covers |
|---|---|---|
| 1 | [01-principles.md](01-principles.md) | Goals and the rules that cut across everything |
| 2 | [02-repos-and-config.md](02-repos-and-config.md) | Repo identity, your omc repo, local config, the cache, trust |
| 3 | [03-watch.md](03-watch.md) | The global `omc watch` process: sync, setup, locks, scheduling, freshness, output |
| 4 | [04-mcp-and-cli.md](04-mcp-and-cli.md) | MCP server, tools, output cap, command tree, `omc internal`, tab titles, `configure`/`update` |
| 5 | [05-skill-rendering.md](05-skill-rendering.md) | Provider stubs, `<match>` and facts, variables, hook contributions, temp dirs |
| 6 | [06-lifecycles.md](06-lifecycles.md) | Lifecycles, plugins, hooks, the `--done` handoff, artifacts |
| 7 | [07-design-lifecycle.md](07-design-lifecycle.md) | `omc design` and every design plugin |
| 8 | [08-implement-lifecycle.md](08-implement-lifecycle.md) | The implement lifecycle and its plugins |
| 9 | [09-run-jobs.md](09-run-jobs.md) | `omc run`: check and E2E jobs, the fix loop, test snippets |
| 10 | [10-review-lifecycle.md](10-review-lifecycle.md) | The review lifecycle: deviation analysis, code review, the CI gate |
| 11 | [11-publish-lifecycle.md](11-publish-lifecycle.md) | The publish lifecycle: creating, splitting and pushing MRs, review comments |
| 12 | [12-session-memory.md](12-session-memory.md) | Per-branch memory: `omc memory add`, injection, retention |
| 13 | [13-testing.md](13-testing.md) | Protected `design/` and `e2e-tests/`, E2E tests in Docker on the four test repos |
| 14 | [14-cross-repo-features.md](14-cross-repo-features.md) | Reading other repos in depth; one design changing several repos, each with its own lifecycles |
| — | [open-questions.md](open-questions.md) | Every open and parked question, in full |

## Naming

- **`omc`** in these documents means v2. It installs as `omc2` until cutover
  (see 01-principles.md, "Coexistence with v1").
- **Your omc repo** is the user-owned git repo holding all repo integrations and
  shared config. The discussion also called it "the state repo"; both names mean
  the same repo, and omc is a guest in it.
