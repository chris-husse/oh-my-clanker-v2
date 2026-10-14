# 10. The review lifecycle

Review makes sure the right thing was built and that it meets the quality gates.
Creating, splitting, pushing and updating MRs is the publish lifecycle's job
(11-publish-lifecycle.md).

## 10.1 Shape

- **Input:** the committed design artifact (`<slug>.md`, `<slug>-plan.md`,
  `<slug>-rulings.md`) and the branch's diff against its base.
- **Entry:** `/omc:review` in the implement session, or `omc review
  [--claude|--codex]` for a fresh session in the worktree.
- **Models:** the `review` block in local config.
- **Default pipeline:**

  ```yaml
  review: [rebase, deviation-analysis, code-review, ci-gate]
  ```

  Review judges and gates the branch on its current base. Publish doesn't rebase
  or gate again (11-publish-lifecycle.md): if the base moves between review and
  publish, the MR's own CI catches it.
- After `ci-gate`, the lifecycle orchestrator states how to continue to publish.

## 10.2 `rebase`

The same command serves the parked `omc refresh`.

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

## 10.3 `deviation-analysis`

Not a conformance review. A difference between the code and the design is not a
defect by default: the implementing agent had a reason for it.

- Identifies in what way the implementation differs from the design and the plan,
  and from every feedback design and plan (11-publish-lifecycle.md §11.2).
- **Notable** means the difference changes behaviour, an interface, a data shape
  or a stated constraint. Naming, file layout and internal structure are not
  notable.
- Every notable difference is judged. The agent first checks `<slug>-rulings.md`:
  a deviation an implement ruling already explains is accepted, citing that
  ruling.
- Each one becomes an entry in the implement ledger's ruling format:

  ```
  Deviation: <what differs> — <design/plan section> — <file:line>
  Ruling: accepted|reverted|escalated — <why> — <cost if wrong>
  ```

  - **accepted:** code and design stay as they are;
  - **reverted:** the agent judged the deviation wrong and fixes the code;
  - **escalated:** the agent can't rule reliably, so it is put to you with
    options and a recommendation, and your answer becomes the ruling.
- All entries go to `<slug>-deviations.md`, committed next to the design, plan
  and rulings under the design artifact root. The approved design is never
  rewritten.

## 10.4 `code-review`

The read-only findings machinery from hardening (06-lifecycles.md §6.5), under a
`review:code-review` hook.

- **omc's default contributions:**
  - **`grug`** — v1's diff rules; behaviour-preserving fixes only;
  - **`multi-agent-review`** — one review agent per changed area of the diff,
    merged into one findings file.
- **Project contributions** (e.g. hummingbird's coding convention and `hb-review`
  rules) join by name, in the usual omc, global, repo order.
- **Hooks never modify anything.** After each hook, Python checks that the
  worktree's tracked files are unchanged; any change fails the skill.
- The plugin merges the findings, applies them, asks you only when in doubt, and
  writes waivers into `## Deliberate complexity`.
- After a round: the round overview and whether to run another, with a
  recommendation, as in hardening.

## 10.5 `ci-gate`

The gate before the MR. It runs, in order, each with the usual fix loop
(09-run-jobs.md §9.4):

1. `omc run check`
2. `omc run e2e-tests`
3. `omc run ci` — the job whose purpose is to fail whenever the repo's CI would
   fail (09-run-jobs.md §9.2). Repos can't add job types; everything else their
   CI checks belongs in `ci`.

- **Identical tree, no rerun.** A job whose last full pass ran on the identical
  git tree is skipped with one line, e.g. *"e2e-tests: passed on this exact tree
  at 14:02, skipped"* (09-run-jobs.md §9.4). Any change during review changes the
  tree, so everything reruns. When review changed nothing, the milestone gate's
  passes from implement carry over and only `ci` runs.
- Rounds exhausted: the CRITICAL stop, as in `milestone-gate`
  (08-implement-lifecycle.md §8.4); the orchestrator states no continuation.

## 10.6 Assumed (not yet confirmed)

- `deviation-analysis` reverts and `code-review` fixes are committed on the branch
  with descriptive messages as they are applied; publish's `create-mr` squashes
  them.
- `<slug>-deviations.md` is committed by Python at `deviation-analysis`'s `--done`,
  the same way `<slug>-rulings.md` is.
