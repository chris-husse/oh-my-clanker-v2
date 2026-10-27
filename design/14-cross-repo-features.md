# 14. Cross-repo features

Work touches other repos in two ways. §14.1 is part of the MVP. §14.2 is **not
part of the MVP**, but it is a design guideline: the MVP must not be built in a
way that prevents adding §14.2 later (§14.3).

## 14.1 Reading other repos while working on one (MVP)

While working on a single repo, it must be easy to add, index and gather
information from other repos, in full depth: add the repo (`repo_add`,
04-mcp-and-cli.md §4.3), let watch set it up (`/auto-index`, 03-watch.md §3.4),
then query it like the repo you're in (`gitnexus`, `docs_grep`).

## 14.2 Changing several repos in one feature (not MVP; a design guideline)

One feature can change several repos. The repo the work starts in is the *main
repo*; the others are *sub-repos*. Each sub-repo gets its own worktree, created
with worktrunk, on a branch with the same slug as the main design. The main
repo's session orchestrates everything; the work in each sub-repo is done by
subagents with that repo's full omc context.

- **Design.**
  1. `/design` runs in the main repo and produces **one main design that covers
     every repo**. It can do that because it has full omc context for each related
     repo (§14.1). Its hardening also runs across the sub-repos, from the main repo.
  2. Once the main design is written, **per-repo hardening**: one subagent per
     sub-repo, in build order, each with the context of that repo only, hardens the
     design against that repo.
  3. **A final pass over the main design** integrates their findings and alerts
     you to problems.
- **Implement.** The main repo's agent orchestrates; subagents implement each
  repo's part, in build order, each working in its own sub-repo.
- **Review, staged.**
  1. Each sub-repo's changes are reviewed individually by a subagent running the
     review lifecycle in that sub-repo, in order, so each one is sane on its own.
  2. Their changes are integrated so the whole repo chain builds.
  3. The final `/review` runs in the main repo over the whole chain.

## 14.3 What the MVP must not prevent (assumed, not yet confirmed)

Derived from §14.2; each is a constraint on MVP code, not a feature to build now.

- **A feature is identified by its slug across repos.** Nothing keyed by repo and
  branch (lifecycle state, artifacts, session memory) may assume the slug exists
  in only one repo.
- **Lifecycles and plugins take their target repo and worktree explicitly,** so a
  subagent of a session in the main repo can run them against a sub-repo's
  worktree. Nothing may infer the target only from the session's working
  directory.
- **Rendering works for a named repo,** so a subagent can load that repo's
  rendered skills and context, not the main repo's.
- **Per-plugin results are machine-readable** (verdicts and artifact paths), so an
  orchestrating session can consume a sub-repo's hardening, build or review
  result.
- **A design artifact can reference a design in another repo.**

Build order, building a sub-repo against an unmerged upstream change, and how the
per-repo MRs are tied together are parked with §14.2 (decision log Q98, Q99).
