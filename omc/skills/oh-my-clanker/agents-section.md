<!-- omc:begin -->
## The pipeline

This project's lifecycle is the `omc/` pipeline, in Claude Code only, installed from oh-my-clanker (the commit in
`omc/VERSION`; `just install <this-project>` from a newer oh-my-clanker, then `/oh-my-clanker`, updates it). The text
between `omc:begin` and `omc:end` is omc's: an update replaces it. The owner types the first two steps; from
`/design` on the run goes to the push by itself:

- `just design <brief-or-text>`, in any checkout (a `<name>.md` of `paths.briefs` or a sentence), the primary
  checkout on the base branch (`base` of `omc/config.yaml`), clean and not diverged from its origin: waits for the
  lock, cuts `<branch_prefix><slug>` from the origin's base in its worktree, wires it (the tab title, the herdr
  sidebar, the notification channel) and launches an interactive shell there that runs
  `claude --model <orchestrator-model> /brainstorm`.
- `/brainstorm`: the primer, the seed and the brainstorm with the owner, up to the committed design doc (in
  `paths.specs`); it never starts `/design`.
- `/design`, typed by the owner when they call the design done (refused without the committed doc): hardens and
  commits the design record and writes the plan (in `paths.plans`), building and testing nothing; then `/implement`.
- `/implement` builds the plan, one task at a time, each gated (it writes the plan first only when `/design` did
  not); then `/audit`.
- `/audit` is the push gate: rebase and squash, review, verify, `screens` (when `paths.screenshots` names some:
  ▣ screens-assess gives each changed shot its verdict by hash pair, then the owner's screenshot review), the owner's
  rulings on the run's entries and open questions (each applied or deferred), describe, push.

`just omc todos` lists the known open work (briefs, deferred rulings, open questions, the project's own sources in
`omc/bin/todos`, `TODO` comments); `/summarize-todos` shows it all, each item with the `just design` that starts it,
and `/find-related-todos` picks what fits a brief (the primer runs it).

`/design` enters `/implement` and `/implement` enters `/audit` on their own, unless `ask_for_provider_handoff: true`
in `omc/config.yaml` (`just omc handoff`): then each stops at that boundary and the owner types the next skill, here
or in a fresh session.

**Gates.** The project's own commands, in `omc/bin/`: `check` (fast, constantly: lint and unit tests), `build` (the
build, no tests), `verify` (everything slow: the full tests, end-to-end tests when there are some; inside a run only
`/audit`'s `verify` runs it; by hand, whenever the owner asks). Pass or fail is the exit code. Each runs through
`just omc gate run <gate>`, with its fix loop as the skill `/check`, `/build`, `/verify`; a gate's notes on its reds
(known flakes, files it regenerates) are `omc/bin/<gate>.md` beside it. `just design-integrity-check` is the
decisions' mechanical check; `/audit`'s `verify` runs it with `--defer-questions`, its push without.

```text
omc/config.yaml    the base, the branch prefix, the orchestrator model, the tiers and the complexity mapping, the hand-off flag, the paths
omc/bin/           the project's gates (check, build, verify), its hooks (links-check, todos) and their notes; the project's own, never shipped
omc/pipeline/      brainstorm, design, implement, audit: the orchestrators, linked from .claude/skills/; they talk to the owner
omc/terminals/     the subagent skills; each ends with one OUTCOME line and never talks to the owner
omc/skills/        the skills the pipeline calls (decisions, doubts, questions, reviews, links), linked from .claude/skills/
omc/tools/         `just omc <verb>`, `just design`, `just decisions`: Python run through `uv run`, a test beside each file
omc/VERSION        the oh-my-clanker commit this copy was installed or updated from
.cache/omc/        current (the running skill) and impact (a rebase not yet read): where a run is
```

`just omc --help` lists the verbs. A skill started again, after a compaction or in a fresh session, begins at its
first step, and every done step skips itself; `/<skill> <step-id>` enters it at that step.

**Rules of the pipeline.**

- The protected documents are the files `paths.protected` of `omc/config.yaml` matches. They change only through
  `/apply-decision` of a decision recorded in the log (`paths.decision_log`) with `/record-decision`, the moment the
  owner rules. With none listed, no decision is recorded, applied or checked: that part of the process stays dormant.
  Every ruling goes into the log; one made after `/design` may be **deferred**, the owner's call per ruling on the
  session's suggestion (applied when the branch's gist needs it, deferred when unrelated or a clear extension):
  recorded on the base branch unapplied (`just decisions defer`), picked up by a later branch (the primer's related
  open work, `just design --deferred <ids>`); a design-stage ruling and an overruling entry are always applied.
- A design doubt, one whose answer would change a protected document, is checked against the documents first
  (`/answer-doubt`). Before `/design` (the brainstorm) it is then asked in the conversation and recorded when the
  owner rules. From `/design` on the run is autonomous to the push: `/answer-doubt` has an independent agent answer it
  too; both answers agreeing, the ruling is recorded at once (`/record-decision`, `Automated: true`) and acted on; a
  disagreement is acted on all the same and recorded at once, `Automated: disagreed` (its question in the run's
  question file, `paths.questions`); the sixth disagreed entry not yet ruled stops the run, and the owner is asked
  about all six, one at a time. The owner rules the run's entries and its open questions after the screenshot review
  (`/audit`'s `screens`), through `/review-decisions` (`/audit`'s `push`, `/pose-questions`): the disagreed ones one at
  a time, confirmed or overruled. Every other question (the seed, scope, preferences, their environment, process) is asked in
  the conversation, one at a time, before `/design`, and decided by the run from it on.
- A conflict at a stop of a rebase onto the base branch is never a question for the owner and never merged by hand:
  the log through `just decisions resolve`; any other file by the rebase terminal, keeping both sides (the base's
  change and the branch's, the branch's ported into the base's new form). Only an entry `resolve` refuses, or two
  sides whose intents exclude each other, go to the owner, as that one contradiction and which intent wins.
- Nothing before implementation builds or tests: no `/check`, `/build`, `/verify`, no `just omc gate run`, no build or
  test of the project's own, in the brainstorm, in `/design`, or in a rebase while the branch changes nothing outside
  the specs, plans and question files.
- At most as many runs of a gate at once on this machine, over every checkout, as `concurrency` of `omc/config.yaml`
  allows (absent: one; `just omc gate run` waits for a slot); any other build, test or render one at a time among this
  run's own agents and commands; never wait for another worktree's or session's run beyond a gate's slot (their load is
  reported, not waited out). Parallel agents only edit (no build, no test), as many as a step needs.
- Skip expensive work (a comparison, a regeneration, a render) when its inputs' bytes have not changed; check by
  content hash first.
- Scratch files and helper scripts go under the worktree's `.cache/<task>/`, never a fixed path in `/tmp`; another
  session can overwrite it.
- An operation no caller reaches, or a test red because something is missing, is worked out from the design, never
  assumed. Design wins: when the protected documents or a design record call for it, it simply is not built yet, so
  build it, and never propose removing what the design requires. When nothing calls for it (no protected document or
  design record, no caller, no test that needs it), propose removing it, with that evidence.
- A run that drives agents over many units of the same kind (every theme file, every screen, every page) pilots one
  unit with the owner first; the design record and the plan describe what the pilot settled, so they are written
  after it.
- A new external dependency or system (a library, a plugin, a platform API, a service) gets a spike in `/brainstorm`,
  before `/design`: a throwaway proof that it does what is needed, run on the real target (the device or emulator for a
  device library, the real service for an API), kept in the feature's worktree under `.cache/spike/<name>/` and never
  committed. The design record builds on what the spike showed and names what it did not cover. Changes within the
  project's own code need no spike.
- The cheap/fast model tier (Haiku-class) is never used, for any agent.
- Questions to the owner: show what each option produces, with the recommended one named; a long message that asks
  questions ends with every question repeated as a numbered list, one line each with the recommended default; show
  progress (done of total).
- A question the owner skips that carried a recommended default is answered by that default: act on it, record it
  when it changes a protected document, and never ask it again in any form, in a later message, a question file or
  `/pose-questions`. Trivial fidelity corners (how a copied app behaves in a detail nobody would notice) are the run's
  to pick; say the pick in one line.
<!-- omc:end -->
