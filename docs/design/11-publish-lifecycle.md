# 11. The publish lifecycle

Publish gets reviewed work onto the forge and keeps it there until it merges:
creating the MR, or splitting it into several, pushing, and incorporating review
comments. Incorporating comments likely needs some design again, then review,
`ci-gate` and another push. That makes publish big and complex, so it has its own
lifecycle; review (10-review-lifecycle.md) stays about whether the right thing was
built and meets the quality gates.

## 11.1 Shape

- **Entry:** the review orchestrator's continuation, or `omc publish
  [--claude|--codex]` for a fresh session in the worktree.
- **Default pipeline** for creating the MR:

  ```yaml
  publish: [rebase, ci-gate, create-mr]
  ```

  `ci-gate` is review's (10-review-lifecycle.md §10.4). When review left the
  branch on the latest base, `rebase` changes nothing and `ci-gate` skips every
  job (identical tree). If the base moved since review, the rebased tree is gated
  again before anything is pushed.
- Incorporating review comments is open (open-questions.md, I1–I4).

## 11.2 `rebase`

Shared by review and publish; the same command serves the parked `omc refresh`.

- **Python** (`omc internal rebase --base <branch>`) fetches and rebases the
  branch onto its base. The plugin passes the base explicitly: the branch named in
  session memory (12-session-memory.md) when there is one, else the repo's `base`.
  Python checks that the branch exists.
- **Conflicts:** the LLM resolves them; Python verifies none remain, else you are
  asked.
- Already on the latest base: a no-op, and the tree is unchanged.
- **Stacked branches:** Python keeps the parent tip it last rebased onto in the
  branch's cache folder and rebases with
  `git rebase --onto <parent's new tip> <last parent tip>`, because the parent's
  own squash rewrites its commits. Once the parent is merged, the base is the
  repo's `base` again (the same `--onto`), and `create-mr` retargets the MR there.

## 11.3 `create-mr`

Not `commit`: `commit` is for tasks and steps (08-implement-lifecycle.md §8.5).
`create-mr`:

1. squashes the branch;
2. prepares a human-facing MR description;
3. pushes;
4. opens the MR.

- **Squash and push are Python** (`omc internal squash`, `omc internal push`), with
  an **LLM fallback** when either fails: the LLM gets the command's error and
  resolves it.
  - The squash leaves one commit on top of the base; its message is the MR title
    plus a short body. The tree stays identical, so `ci-gate`'s passes still hold.
  - The push is `--force-with-lease` to `origin/<branch>`, so a re-review after an
    earlier push replaces the branch without clobbering commits someone else
    pushed.
- **The MR** is opened (or, if one exists, its description updated) by the LLM
  with whatever forge tools the session has; omc doesn't know the forge. It
  targets the branch's base and opens ready for review, not as a draft.
- **The description** is written for a human reviewer, from the design and the
  diff:
  - **Summary:** what changes and why, in a few sentences;
  - **Changes:** the notable changes, grouped;
  - **Deviations from the design:** the accepted entries of
    `<slug>-deviations.md`, one line each;
  - **Testing:** the `ci-gate` results;
  - **Links:** the primary and related tickets.

  No internal omc paths, plugin names or `/tmp` links.
- **If the MR can't be opened** (no forge tools, auth), the plugin says why in its
  output and again in the summary, and prints the description for you to paste;
  the push has still happened.
- **The ticket:** the primary ticket moves to an "In Review"-type status with the
  session's tracker tools; nothing else, as with `ticket-start`. Skipped when the
  design has no `Primary:` line. If it can't be moved, the plugin says why in its
  output and again in the summary, and continues.
- **Not always on `main`:** a branch can be based on another local worktree's
  branch. That intent is never fixed at design time; it comes from the branch's
  session memory (12-session-memory.md), whenever you said it (§11.2).

## 11.4 Splitting a huge MR

- `create-mr` offers a split when the diff exceeds `review.split_suggest_lines`
  (written into config, e.g. `800`), and on request.
- The proposal comes from **`/suggest-mr-split`**, a skill that does a deep
  analysis of the feature's seams and how to break it into logical increments
  that stack well and can each be deployed on their own. Each chunk: a title, its
  files and hunks, and why it stands alone. You approve or change it.
- Python builds a stack of branches `<branch>-1 … <branch>-n`, each one commit on
  the previous; the last one's tree is identical to the gated tree.
- Each intermediate chunk must pass `omc run check` (the full gate already passed
  on the last tree).
- The MRs open as a stack, each targeting the previous chunk, with "part i of n"
  in the description.


## 11.5 Assumed (not yet confirmed)

- After an LLM fallback in `create-mr`, Python verifies the result: exactly one
  commit over the base, its tree identical to the tree `ci-gate` passed, and
  `origin/<branch>` at local `HEAD`. A failed verification fails the skill. The
  fallback never uses a plain `--force`.
- Publish uses the `review` model block in local config.
