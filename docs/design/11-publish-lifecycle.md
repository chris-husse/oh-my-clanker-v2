# 11. The publish lifecycle

Publish gets reviewed work onto the forge and keeps it there until it merges:
creating the MR, or splitting it into several, pushing, and incorporating review
comments. Incorporating comments likely needs some design again, then review,
`ci-gate` and another push. That makes publish big and complex, so it has its own
lifecycle; review (10-review-lifecycle.md) stays about whether the right thing was
built and meets the quality gates.

## 11.1 Shape

- **Entry:** the review orchestrator's continuation, or `omc publish
  [--claude|--codex]` (or `/omc:publish`) in the worktree.
- **Default pipeline:**

  ```yaml
  publish: [triage-comments, create-mr]
  ```

## 11.2 `triage-comments`

- Detects whether the branch has an MR and whether it has review comments, with
  the session's forge tools.
- **No MR, or no comments:** straight to `create-mr`. Rebase, review and the CI
  gate were already done in review.
- **Comments:** they go to **brainstorming** (`superpowers-brainstorm`), which
  already classifies the work and decides whether it is worth a full design or
  not. The decisions made in that brainstorming are what the MR's replies are
  generated from (§11.3).
- **The comments seed:** one entry per unresolved thread, never the raw text:
  - the **interpreted version** of the comment: what the reviewer is asking for,
    across all its lines and replies, in the triage agent's words;
  - where it applies: a file and line range, or the MR as a whole;
  - the **link** to the comment, so brainstorming can check it when something is
    unclear or a bigger discussion is going on, and dive deep as needed.
- **The hand-over:** the orchestrator hands over to the design lifecycle **from
  `superpowers-brainstorm`**, with the seed and the committed design as context
  (`explain-seed` is skipped: the context exists). Brainstorming's classification
  picks the path:
  - **full design:** a feedback design through `design-hardening`,
    `write-implementation-plan` and `approve-design`; then implement, review,
    publish;
  - **not worth a full design:** brainstorming still writes the (short)
    document; `design-hardening` is skipped; `write-implementation-plan` and
    `approve-design` still run, because implement needs a plan; then implement,
    review, publish;
  - **no code change** (every thread is answered by an explanation): straight to
    `create-mr`, which posts the replies.
- **The record:** a feedback design `<slug>-feedback-<n>.md` (with
  `<slug>-feedback-<n>-plan.md` when code changes), committed next to the design.
  Brainstorming records one decision per thread,
  `Thread <id>: <decision> — <why>`, which the replies are generated from. The
  approved design is never rewritten.

## 11.3 `create-mr`

Not `commit`: `commit` is for tasks and steps (08-implement-lifecycle.md §8.5).
`create-mr`:

1. squashes the branch, **always**, including after a round of comments;
2. prepares a human-facing MR description;
3. pushes;
4. opens the MR, or, when one already exists for the branch, detects it and
   updates it instead;
5. after a round of comments, posts the replies (below).

- **Squash and push are Python** (`omc internal squash`, `omc internal push`), with
  an **LLM fallback** when either fails: the LLM gets the command's error and
  resolves it.
  - The squash leaves one commit on top of the base; its message is the MR title
    plus a short body. The tree stays identical, so `ci-gate`'s passes still hold.
  - The push is `--force-with-lease` to `origin/<branch>`, so a later round
    replaces the branch without clobbering commits someone else pushed.
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
  session memory (12-session-memory.md), whenever you said it; `rebase`
  (10-review-lifecycle.md §10.2) follows it.
- **Replies to comments** are generated automatically from the `Thread <id>:`
  decisions made in the brainstorming of those comments, and posted to their
  threads. They are not drafted for your approval. omc never resolves a thread;
  the reviewer does.

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
- omc doesn't know the forge, so nothing polls it for comments; publish is
  re-entered (`omc publish` or `/omc:publish`) when there are some.
- On an update, the MR description is regenerated for the whole branch, and the
  ticket move is a no-op when it is already "In Review".
