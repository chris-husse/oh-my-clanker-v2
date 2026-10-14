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
- **Adding:** `omc memory add "<text>"`, for example
  `omc memory add "We are targeting local worktree bla and need to file the MR against that branch, if it wasn't merged yet."`
- **Injected at the top** of the skill, as memory.
- **Retention:** watch clears a branch's subfolder once it has been unmodified
  for a month.
- **OptMem** ([VictorTaelin/OptMem](https://github.com/VictorTaelin/OptMem)) is the
  candidate for the store: plain files, an append-only log of one-line memories
  (≤ 280 bytes), summaries kept as a rebuildable tree, regex recall, and
  `$MEMORY_DIR` to put the memory anywhere. Whether omc uses it is open
  (open-questions.md, J1).

## 12.3 Assumed (not yet confirmed)

- `<repo-hash>` is the repo key (`{name}-{hash8}`) and `<branch-slug>` is the
  `<branch-file>` (02-repos-and-config.md §2.4), as everywhere else in the cache.
- The month is `sessions_retention_days: 30`, written into local config.
- `omc memory add` uses the current worktree's repo and branch; it fails outside
  an omc worktree.
