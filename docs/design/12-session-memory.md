# 12. Session memory

## 12.1 Why

Things you say about a branch arrive at any time: while implementation runs,
after review, between sessions. *"We are targeting local worktree X and need to
file the MR against that branch, if it wasn't merged yet."* None of that can be
fixed at design time, and none of it may be lost when a session ends or another
provider takes over. So each branch has a memory, and every skill sees it.

This replaces recording a branch's base when its worktree is cut: which branch an
MR targets, or whether it stacks on another worktree, is a memory like any other.

## 12.2 Shape

- **Per branch:** `~/.omc2/sessions/<repo-hash>/<branch-slug>/optmem`.
- **Written by the LLM, never by you.** The session's main agent runs
  `omc memory add "<text>"` when you say something that matters for the branch
  beyond the current step, for example
  `omc memory add "We are targeting local worktree bla and need to file the MR against that branch, if it wasn't merged yet."`
  It says so in one line. Subagents never write memories.
- **omc's own store, borrowing OptMem's format**
  ([VictorTaelin/OptMem](https://github.com/VictorTaelin/OptMem)). OptMem itself
  isn't used: its repository has no license, so omc may not copy or ship it, and
  it installs with an unpinned `curl | sh`. The store is one append-only file per
  branch, one memory per line (≤ 280 bytes), each with a timestamp. There is no
  summary tree: a branch's memory is a few dozen lines.
- **Injected into every skill rendered for the branch:** every lifecycle plugin,
  fix skill and user-facing skill run in that worktree, as a `## Session memory`
  block right after the stub's header. Python renders it verbatim; an empty
  memory renders nothing.
- **Retention:** watch clears a branch's subfolder once it has been unmodified
  for a month.

## 12.3 Assumed (not yet confirmed)

- `<repo-hash>` is the repo key (`{name}-{hash8}`) and `<branch-slug>` is the
  `<branch-file>` ([02 §2.4](02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60))), as everywhere else in the cache.
- The month is `sessions_retention_days: 30`, written into local config.
- `omc memory add` uses the current worktree's repo and branch; it fails outside
  an omc worktree.
