# oh-my-clanker v2: omc as an initialization

## Intent

The source project's own `omc/` is lifted out so any project can use it. v2 is not a toolchain a project depends
on at run time: it is the source a project is initialized from. After install the project owns its copy, as the source project
owns its `omc/` today. No trace of the source project stays in v2.

## What v2 holds

- `omc/`: the source project's `omc/` (`config.yaml`, `pipeline/`, `terminals/`, `tools/` and their tests), as it is.
- The skills the pipeline calls, as they are: record-decision, apply-decision, answer-doubt, pose-questions,
  review-decisions, review-design, explain, reconcile-links; the `decisions` tool; GitNexus (always on).
- `/oh-my-clanker`: the skill that installs into a project and updates an installed one.
- `justfile` with `just install <project-folder>`.

## The one rule: dormant by absence

Nothing is switched on or off. A part of the process whose inputs a project has not defined does nothing, and passes:

- no protected documents → no decision is recorded, applied, folded, or checked for consistency or integrity;
- no screenshots → nothing to regenerate, judge or present;
- no theme files / rule ids → nothing that reads them;
- likewise every other input-driven step.

## What becomes project definition

**`omc/config.yaml`** (today's keys plus the paths the source project hardcodes, each glob list empty by default):
protected documents, screenshots, baselines, briefs (`tasks/`), specs and plans (`docs/superpowers/…`), the decision
log and question files, theme files.

**`bin/`** (created by install, fully the project's): the commands that run the project — `check`, `build`,
`verify`, and the optional ones the skills call (`screenshots`, `deps-audit`). Pass/fail is the exit
code. A `bin/<gate>.md` beside a gate holds the project's notes for its reds (flakes, ratchets, baseline advances),
which the gate skill reads when it fixes. The gate skills keep only the fix loop; `done.py` records a gate pass
itself.

## What is cut

- Stays in the source project for now, ported to v2 later by the owner: DVC and everything around it; live debugging
  (debug-live, system-guided-run); the E2E tests (e2e-tests, derive-scenarios, the scenarios-review terminal,
  `wiring-tests`, the scenario steps of implement and audit). Where a shipped skill names one of them, that step is
  removed; it comes back with the port.
- Skills: review-screens (it drives the source project's app).
- From the shipped skills: verify's pglite/wrangler/chaos/T15/DVC-gap/baseline text; check's and build's gate-tool
  JSON contract, `stages.py` budget, ratchet, Wasm flake, Flutter/wrangler text; the objects-generator task rule; the
  whole-table-read rule; the macOS/VM screenshot rule. Each moves to the source project's own `bin/` notes or `AGENTS.md`.
- From `tools/`: `done.py`'s read of `.cache/gates/runs/*.json` and its `worktree_id` copy; the test importing
  `src/tools/gates`.
- Prose: citations of the source project's records (the rule they state stays), the source project's name, the owner as "him".

## Install

`just install <project-folder>` copies `omc/` and the skills into the project, records the v2 commit
(`omc/VERSION`), and launches `claude /oh-my-clanker` there. The skill links the skills into `.claude/skills/`, adds
the `omc`/`design`/`decisions` recipes to the justfile, the `.claude/settings.json` entries, the pipeline section of
`AGENTS.md`, writes `bin/` from what the repo already runs, and fills `omc/config.yaml`, asking the owner only what
the repo does not answer.

## Update

`/oh-my-clanker` against a newer v2: a three-way merge per file — base v2 at `omc/VERSION`, theirs v2 now, ours the
project's copy. Clean merges apply; Claude resolves conflicts by intent, keeping the project's changes; `omc/VERSION`
moves. `bin/` and `config.yaml` values are the project's and never overwritten.

## Approaches

- **Recorded base + three-way merge (chosen):** exact; Claude only where both sides changed.
- Claude ports v2's diff by intent with no base: rejected, it cannot tell the project's changes from old v2.

## Non-goals

A standalone toolchain; switches, hook slots or extension points; rewriting the lifted skills or tools beyond the
cuts above; harnesses other than Claude Code.

## Done when

`grep -ri <source name>` over v2 finds nothing; installing into a repo with no protected documents or screens
runs the pipeline end to end with those parts idle; installing into the source project leaves only its definitions (config,
`bin/`, notes) as the difference from today.
