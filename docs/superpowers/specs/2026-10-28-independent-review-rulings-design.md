# Independent answers, proposed rulings, bulk acceptance

The owner wants review questions with an easy answer to cost seconds, not one long turn each.
For every open question, the orchestrator and a fresh `/try-answer-design-question` agent
each answer it independently. Where the two answers agree, the result is a **proposed
ruling**. The owner looks at proposed rulings five at a time and bulk-accepts them. Nothing
reaches the decision log unless the owner has seen it. Human rulings stay authoritative.

This replaces the earlier version of this spec, where every agreement was recorded
automatically.

## Flow (`/review-design` steps 4 to 6)

1. **Orchestrator answers first, hidden.** For each prepared question, the orchestrator reads
   the cited corpus and decision chains and saves its answer as `<RUN>-hidden/orchestrator-<ref>.md` (a folder no prompt names),
   in the output structure of `/try-answer-design-question`. Nothing goes into the log. The
   independent agents never see these answers.
2. **Independent answers in parallel.** One fresh agent per question, at most 20 running at a
   time, each with only the neutral question, its source references, the quoted passages and
   any explicit human constraints. Each writes `<RUN>/answer-<ref>.md` and reads nothing else
   in the run directory. The orchestrator saves its own answers for a wave before that wave is
   dispatched. *Builder's call:* whether the orchestrator answers all questions before the
   first wave or one wave ahead.
3. **Compare as answers arrive.** The answers agree when they make the same substantive
   choice, with the same scope, conditions and necessary additions. Wording, confidence and a
   bare yes/no don't count. An addition only one answer makes is dropped from the proposal,
   unless leaving it out changes the meaning. In that case, or on any disagreement, missing
   evidence or deferred choice, the question goes to the individual flow.
4. **Conflict check against the current history.** An agreed answer that conflicts with an
   earlier **human** ruling never becomes a proposal: it goes to the individual flow. There
   the question names the human ruling it conflicts with, quotes it and explains why the
   proposal would contradict it. Legacy rulings (`Automated: unspecified`, which today covers
   1.1–1.19) count as human. An agreed answer that replaces an earlier **automated** ruling
   becomes a proposal that supersedes it, and its batch entry names the ruling it replaces.
5. **Batches of five, then individual questions.** All batches come first, then the individual
   questions in consequence order, with the existing current question and
   `Upcoming (Don't answer yet)` preview and the `Question n of N` counts. *Orchestrator's
   call:* a batch is shown as soon as five proposals are ready, while later waves still run;
   the last batch may hold fewer. Individual questions wait until every batch is done.
   Before each write, the proposal is checked again against the rulings recorded so far in
   this pass; one that now contradicts a ruling accepted in an earlier batch goes to the
   individual flow rather than superseding it.

"Less weight" means only the supersession rule below. An automated ruling still settles a later
review question the way any ruling does (the check-cluster `settled` bucket is unchanged); a
later answer that would change it is a supersession proposal, or an individual question when
it touches a human ruling.

## A batch

Proposals are numbered 1–5 within the batch, each with its review reference (`R40`). Each has
three parts: **Context**, **Question**, **Proposed ruling**, plus **Supersedes** when it
replaces an automated ruling. Length depends on how complex the question is: two or three lines
for an easy one, more for a hard one, never the full write-up of an individual question.

The owner replies by number, for example "1, 3, 4 are wrong". The others are accepted and
recorded; the rejected ones join the individual flow and are asked there like any other
question, with both answers and the full explanation. A bare "ok" or "all good" accepts all
five; "ok except 2" rejects 2 and accepts the rest. A doubt about one number moves that proposal
to the individual flow. A number outside the batch, or "ok" next to numbers without saying which
way, makes the reply unclear: nothing is recorded and the batch is shown once more; a second
unclear reply sends all its proposals to the individual flow. Nothing is ever guessed.

## Recording and provenance

- A bulk-accepted ruling is recorded with `just decisions add-decision --automated`
  (`Automated: true`). It carries less weight than a human ruling: the owner's bulk accept is
  a filter before recording, not a human decision.
- A ruling decided in the individual flow is recorded the ordinary way (`Automated: false`).
- The orchestrator records, reads back with `just decisions show <id>`, and checks for a
  duplicate immediately before each write. Recording is never delegated.

## Supersession rules (tool and skills)

- An automated ruling may supersede an automated ruling. `add-decision --automated
  --supersedes <id>` is allowed only when every target is an entry with `Automated: true`.
  It refuses a human ruling, a legacy (`unspecified`) ruling or a log section (`§1`), and
  writes nothing.
- The integrity check flags any automated entry whose Supersedes names something that isn't an
  automated entry.
- A human ruling may supersede anything, as today.
- The skills apply the same rule semantically: a proposal whose meaning contradicts a human
  ruling is an individual question even when the agents' `Contradicts` field is empty.

## Worksheet and resume

For each question the worksheet keeps both answer paths, the comparison, the conflict check,
the route (`proposed`, `individual`), the batch and number it was shown in, the owner's reply,
and the recorded id after readback. On resume, completed answer pairs and recorded rulings are
reused. A first answer is never reconstructed after reading the second; when it is missing, the
question is answered again from scratch.

## The review in progress

`docs/reviews/2026-10-16-adversarial-design-review.md` (section 1, 52 questions left, from R73)
switches to this flow once the skills are updated. R73 already has a completed pair that
disagrees, so it goes to the individual flow. The remaining questions go through steps 1 to 5.
The withdrawn rulings 1.20–1.80 stay withdrawn.

## Application and reporting

The owner's bulk accept is the explicit approval AGENTS.md requires for the change: the owner
has seen the context, question and ruling, which is the nature of the change. Step 7 runs
`/apply-decision` on accepted rulings, in id order, with no further prompt. The `Automated`
field alone grants nothing: an automated ruling recorded any other way is not applied without
the owner's approval. After each batch, the
orchestrator reports the ids it recorded. The final summary lists the automated rulings of the
pass, with the important ones first (scope, architecture, security/trust, compatibility, manual
user work).

## Out of scope

No product design or E2E definition changes. No historical ruling is rewritten or restored.
The `--automated` flag and provenance field stay as they are, apart from the supersession rule.

## Files touched

- `.claude/skills/review-design/SKILL.md`: steps 4 to 6 and Never.
- `.claude/skills/design-review-conventions/`: `agent-prompts.md` (section 7, the wave
  dispatch), `triage.md`, `worksheet.md`, `decision-log-section.md`.
- `.claude/skills/decision-log/` (`SKILL.md`, `format.md`) and `.claude/skills/record-decision/`,
  `apply-decision/`, `how-we-got-here/`: the supersession rule.
- `tools/design/decisions.py`, `tools/design/log.py`, `tools/design/tests/test_decisions.py`:
  allow automated → automated supersession, refuse other targets, and the integrity check.
- `docs/superpowers/plans/2026-10-28-independent-review-rulings.md`: replaced by the new plan.

## Validation

Tests cover automated → automated supersession accepted, automated → human, legacy and section
refused with nothing written, and the integrity check on a hand-made bad chain. A fresh
reviewer checks the skills for answer leakage, the human-conflict route and the batch reply
handling. Run the tools tests, the log integrity check, `just links-check` and
`just ensure-up-to-date`.
