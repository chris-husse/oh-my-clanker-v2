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
- The pipeline is open (open-questions.md, I1), and so is incorporating comments
  (I6).

## 11.2 `create-mr`

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
- **Not always on `main`:** a branch can be based on another local worktree's
  branch, and a huge MR may need splitting into logical chunks. How both work is
  open (open-questions.md, I2–I4), as is the ticket (I5).

## 11.3 Assumed (not yet confirmed)

- After an LLM fallback in `create-mr`, Python verifies the result: exactly one
  commit over the base, its tree identical to the tree `ci-gate` passed, and
  `origin/<branch>` at local `HEAD`. A failed verification fails the skill. The
  fallback never uses a plain `--force`.
- Publish uses the `review` model block in local config.
