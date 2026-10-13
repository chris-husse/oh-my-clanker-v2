# 8. The implement lifecycle

## 8.1 Shape

- **Input:** the committed design artifact: `<slug>.md` and `<slug>-plan.md`.
  `omc internal design-artifact` finds both for the branch under either artifact
  root; if either is missing, the skill renders only an ABORT naming the missing
  file.
- **Entry:** `/omc:implement` in the design session, or `omc implement
  [--claude|--codex]` for a fresh session in the worktree.
- **Models:** the `implement` block in local config has a model per task slot
  (`simple`, `medium`, `high`, `review`) per provider. A task's `Complexity:`
  picks its slot.
- **Default pipeline:**

  ```yaml
  implement: [ticket-start, superpowers-subagent-build, milestone-gate, commit]
  ```

- After `commit`, the lifecycle orchestrator states how to continue to review.

## 8.2 `ticket-start`

- Reads the primary ticket from the committed design's `Primary:` line.
  `<match "omc:design_has_primary_ticket">` decides whether it runs; false renders
  the plugin as a skip that just runs `--done`.
- Assigns the primary ticket to you and moves it to an "In Progress"-type status
  using whatever tracker tools the session has; omc doesn't know the tracker.
  Nothing else: no comment, no other field. Related tickets are never touched.
- If the ticket is assigned to someone else, it asks you before taking it over;
  if you decline, implement stops.
- **If the ticket can't be moved** (no tracker MCP, no matching transition), the
  plugin says why in one line in its output and again in the final implement
  summary, then continues.
- No hooks for now.

## 8.3 `superpowers-subagent-build`

- Runs upstream `superpowers:subagent-driven-development` over the plan.
- TDD steps use `omc run check --test <selector>`; each task ends with a full
  `omc run check`. A red check runs that job type's fix skill, and Python counts
  the rounds (09-run-jobs.md).
- **Progress tracking is upstream's own.** SDD keeps a per-plan ledger at
  `<worktree>/.superpowers/sdd/<plan-name>/progress.md` (the directory ignores
  itself with a `*` `.gitignore`, so no tracked file changes). A restart skips
  tasks marked complete and resumes mid-fix-loop tasks at their next round; a lost
  ledger is recovered from `git log`. omc adds nothing. A provider switch in the
  same worktree finds the same ledger.

## 8.4 `milestone-gate`

A full `omc run check`, then `omc run e2e-tests`, with the same bounded fix loop.
It is its own plugin so a repo can change its E2E policy (e.g. a `just up` first,
or no E2E) without replacing the build plugin.

## 8.5 `commit`

- Commits any tracked changes left from fix rounds, with a descriptive message.
- Checks that the tree is clean and the branch has at least one commit over its
  base.
- Never discards work: an untracked or modified file the plan didn't produce is
  listed and put to you, never deleted.
