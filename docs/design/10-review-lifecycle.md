# 10. The review lifecycle

## 10.1 Shape

- **Input:** the committed design artifact (`<slug>.md`, `<slug>-plan.md`,
  `<slug>-rulings.md`) and the branch's diff against its base.
- **Entry:** `/omc:review` in the implement session, or `omc review
  [--claude|--codex]` for a fresh session in the worktree.
- **Models:** the `review` block in local config.
- **Default pipeline:**

  ```yaml
  review: [deviation-analysis, code-review, publish-gate, create-mr]
  ```

  `code-review`'s shape is still open (open-questions.md, I1).

## 10.2 `deviation-analysis`

Not a conformance review. A difference between the code and the design is not a
defect by default: the implementing agent had a reason for it.

- Identifies in what way the implementation differs from the design and the plan.
- Every notable difference is judged.
- If the agent can't rule reliably, the difference is escalated to you.

What a judgment produces, and where it is recorded, is open (open-questions.md,
I2).

## 10.3 `code-review`

Open (open-questions.md, I1).

## 10.4 `publish-gate`

Replaces a rerun of `milestone-gate`. It runs the milestone gate (full check, then
E2E) under its `review:publish-gate` hook, as omc's default contribution, and does
more: the project adds contributions so the gate runs **every check its CI runs**.

How the project's extra checks run is open (open-questions.md, I3), as is whether
a job that already passed on the identical tree is rerun (I4).

## 10.5 `create-mr`

Not `commit`: `commit` is for tasks and steps (08-implement-lifecycle.md §8.5).
`create-mr`:

1. squashes the branch;
2. prepares a human-facing MR description;
3. pushes.

Its remaining details (rebase onto the latest base, opening the MR on the forge,
the ticket transition, whether a separate `publish` lifecycle remains) are the
next question group (open-questions.md, I5).
