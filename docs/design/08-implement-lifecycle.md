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
- **Upstream behaviour kept:** a fresh implementer subagent per task, a task review
  (spec compliance + code quality) with upstream's own review fix loop (up to 5
  rounds, rounds 4–5 on a fresh, stronger implementer), no check-ins with you
  between tasks, and one final whole-branch review with a single fix wave.
  Upstream stops only for an irreversible action, a security-sensitive action, a
  side effect outside the worktree (merge, push, publish), or a plan too broken to
  continue.
- **Models come from omc's config,** never upstream's judgment. Each task's
  `Complexity:` (`simple | medium | high`; missing means `medium`) picks the
  matching slot of the `implement` block; every review uses the `review` slot;
  upstream's escalation in fix rounds 4–5 moves one slot up (`simple` → `medium` →
  `high`; `high` stays `high`). Models are always passed explicitly.
- **Ending:** the plugin stops after the final review and its fix wave. It never
  invokes `superpowers:finishing-a-development-branch`; publishing belongs to the
  publish lifecycle. The workspace is not deleted until `--done` passes, which has
  Python check that the ledger names this plan, that every plan task has a
  `Task <N>: complete` line, and that the final review ran.
- **Rulings are kept.** Upstream decides conflicts and ambiguities itself instead
  of asking, recording each in its ledger as
  `Ruling: <what> — <why> — <cost if wrong>`. Before the ledger is deleted, Python
  copies every `Ruling:` line, in order, into `<slug>/<slug>-rulings.md`. The
  `commit` plugin commits it next to the design and plan under the same artifact
  root; the implement summary links it, and the review lifecycle reads it with the
  design.
- **Assumed (not yet confirmed):** omc provides the worktree, so upstream's
  `using-git-worktrees` setup is skipped; a provider without a subagent tool falls
  back to `superpowers:executing-plans`, as upstream itself does.
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
- Commits `<slug>-rulings.md` next to the design and plan, under the design
  artifact root.
- Checks that the tree is clean and the branch has at least one commit over its
  base.
- Never discards work: an untracked or modified file the plan didn't produce is
  listed and put to you, never deleted.
