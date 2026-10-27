# 14. Cross-repo features

Work touches other repos in two ways, and the MVP needs both.

## 14.1 Reading other repos while working on one

While working on a single repo, it must be easy to add, index and gather
information from other repos, in full depth: add the repo (`repo_add`,
04-mcp-and-cli.md §4.3), let watch set it up (`/auto-index`, 03-watch.md §3.4),
then query it like the repo you're in (`gitnexus`, `docs_grep`).

## 14.2 Changing several repos in one feature

- **One design can span several repos.** It starts in one repo, the *main repo*:
  the repo the design was started in.
- **Each affected repo gets its own worktree,** created with worktrunk, on a branch
  with the **same slug** as the main design.
- **The main design creates the sub-designs** in the related repos.
- **Each repo runs its own lifecycles:** `/design`, `/implement` and `/review` run
  in that repo's worktree, with full repo-local omc context. There is no
  difference from running the task directly in that repo.
- **Implementation builds the repos in order,** each one inside its own repo with
  full omc context, never from the main repo.

Open details are in `docs/decision-log.md` (the follow-ups to Q1).
