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

The gate before the MR. Its job is `ci` (09-run-jobs.md §9.2): the job type whose
purpose is to fail whenever the repo's CI would fail. Repos can't add job types of
their own; everything their CI checks belongs in `ci`.

Open: the plugin's name (you suggested `ci-gate`) and whether it also runs the
milestone gate's `check` and `e2e-tests` (open-questions.md, I3); whether a job
that already passed on the identical tree is rerun (I4).

## 10.5 `create-mr`

Not `commit`: `commit` is for tasks and steps (08-implement-lifecycle.md §8.5).
`create-mr`:

1. squashes the branch;
2. prepares a human-facing MR description;
3. pushes.

Its remaining details (rebase onto the latest base, opening the MR on the forge,
the ticket transition, whether a separate `publish` lifecycle remains) are the
next question group (open-questions.md, I5).
