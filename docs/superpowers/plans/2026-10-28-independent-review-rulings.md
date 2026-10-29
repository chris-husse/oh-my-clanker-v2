# Proposed Rulings and Bulk Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace automatic recording of agreed review answers with proposed rulings that the owner bulk-accepts five at a time, and let automated rulings supersede automated ones only.

**Architecture:** One tool change in `tools/design/decisions.py` (supersession guard in `add_decision` and `check`). Everything else is Markdown: `/review-design` steps 4–7 and the shared conventions files get the parallel answer waves, the comparison, the batch format and reply handling, and the human-conflict route. This builds on the uncommitted provenance work already in the tree (`Automated` field, `--automated`), which stays.

**Tech Stack:** Python 3, pytest via `uv run --project tools`, `just`, Markdown skills.

**Spec:** `docs/superpowers/specs/2026-10-28-independent-review-rulings-design.md`

## Global Constraints

- Write `docs/decision-log.md` only through `just decisions`; edit nothing in `docs/design/` or `docs/e2e-tests/`.
- Leave the untracked `.config/` and the existing uncommitted provenance changes in place; build on them.
- At most 20 independent agents at a time, one question each; batches of exactly five proposals (the last may hold fewer).
- A bulk-accepted ruling is recorded with `--automated` (`Automated: true`); an individually decided one without it.
- Automated → automated supersession only; human, legacy (`unspecified`) and log-section (`§1`) targets are refused.
- Legacy rulings (`Automated: unspecified`) count as human.
- Bulk accept is the owner's approval to apply; `Automated: true` alone grants none.
- No commit or push unless the owner asks.

## Review Focus

- A Supersedes chain naming several targets where only one is not automated: the whole write is refused, nothing written.
- An automated ruling that supersedes an automated ruling which itself was superseded by a human ruling: refused (target is not effective; a human successor exists).
- A batch reply that names a number outside 1–5, or mixes "ok" with numbers: unclear numbers go to the individual flow, never guessed.
- A batch whose agents finish after the owner has accepted an earlier batch that a later proposal contradicts: routed to individual, not superseded.
- Resume with a pair whose first answer file is missing: re-answered from scratch, never reconstructed.

---

### Task 1: Automated → automated supersession in the tool

**Files:**
- Modify: `tools/design/decisions.py` (`add_decision`, `check` near the `automated decisions cannot supersede` line, the `--automated` help text in `cli`)
- Test: `tools/design/tests/test_decisions.py`

**Interfaces:**
- Consumes: `log.entries[id].fields.get('Automated')`, `e.targets('Supersedes')`, `_entry_target(e)`, `later_superseders` (the direct-superseders helper at the `"""Ids of the later entries whose Supersedes names e itself` docstring).
- Produces: `_automated_supersedable(log: Log, entry_id: str) -> str | None` — returns `None` when the id is a decision with `Automated: true` and no later superseder whose `Automated` is not `true`, else one of the reasons `'is a human ruling'`, `'is a legacy ruling (Automated unspecified), treated as human'`, `'is superseded by a human ruling'`, `'is not a decision'`. `add_decision(..., supersedes=..., automated=True)` uses it for every target before writing; `check` uses it on each Supersedes target of an automated entry (resolved back to an entry id through `_entry_target`).

- [ ] **Step 1: Replace `test_automated_supersession_is_refused_without_writing` with these tests**

```python
def test_automated_may_supersede_automated(repo, docs):
    first = add_decision(*load(docs), 'A', 'c', 'd', automated=True)
    second = add_decision(*load(docs), 'B', 'c', 'd2', supersedes=[first], automated=True)
    assert first in load(docs)[1].entries[second].fields['Supersedes']
    assert check(*load(docs), head_log_text(docs)) == []

def test_automated_cannot_supersede_human_legacy_or_section(repo, docs):
    human = add_decision(*load(docs), 'H', 'c', 'd')
    before = log_text(docs)
    for supersedes in ([human], ['1.1'], ['§1']):          # human, legacy unspecified, section
        with pytest.raises(RefError, match='[Aa]utomated'):
            add_decision(*load(docs), 'X', 'c', 'd', supersedes=supersedes, automated=True)
    assert log_text(docs) == before

def test_mixed_targets_refuse_the_whole_write(repo, docs):
    auto = add_decision(*load(docs), 'A', 'c', 'd', automated=True)
    before = log_text(docs)
    with pytest.raises(RefError, match='[Aa]utomated'):
        add_decision(*load(docs), 'X', 'c', 'd', supersedes=[auto, '1.1'], automated=True)
    assert log_text(docs) == before

def test_automated_cannot_supersede_an_automated_ruling_a_human_replaced(repo, docs):
    auto = add_decision(*load(docs), 'A', 'c', 'd', automated=True)
    add_decision(*load(docs), 'H', 'c', 'd2', supersedes=[auto])
    with pytest.raises(RefError, match='human'):
        add_decision(*load(docs), 'X', 'c', 'd3', supersedes=[auto], automated=True)

def test_check_flags_automated_superseding_a_non_automated_entry(repo, docs):
    bad = LOG.replace('**Decision.** d\n', '**Decision.** d\n**Automated.** true\n')   # existing fixture: entry with Supersedes → legacy target
    assert 'malformed-entry' in kinds(check(load(docs)[0], parse_log(bad), None))
```

Adjust the `bad` fixture line to the one the old test used, if its Supersedes target is legacy (it is in the current fixture `LOG`).

- [ ] **Step 2: Run** `uv run --project tools pytest tools/design/tests/test_decisions.py -q -k supersede` — expect the first test to FAIL with the old "cannot supersede" error.

- [ ] **Step 3: Implement `_automated_supersedable` and use it in `add_decision` and `check`**

In `add_decision`, replace the blanket `if automated and supersedes: raise` with: for each target, a section id raises `RefError('automated decisions cannot supersede a log section; obtain a human decision')`; an entry id raises `RefError(f'automated decisions supersede only automated rulings: {id} {reason}')` when `_automated_supersedable` returns a reason. Check every target before any write. In `check`, replace the blanket message with the same rule per target. Update the `--automated` help to `record an owner-accepted proposed ruling; may supersede only automated rulings`.

- [ ] **Step 4: Run** `uv run --project tools pytest tools/design/tests -q` — expect all PASS.

### Task 2: `/review-design` and the conventions

**Files:**
- Modify: `.claude/skills/review-design/SKILL.md` (Before anything, steps 4, 5, 6, 7, Never)
- Modify: `.claude/skills/design-review-conventions/agent-prompts.md` (section 7), `triage.md`, `worksheet.md`, `decision-log-section.md`
- Modify: `.claude/skills/decision-log/format.md`, `decision-log/SKILL.md`, `record-decision/SKILL.md`, `apply-decision/SKILL.md`, `how-we-got-here/SKILL.md` (the supersession and weight wording only)

**Interfaces:**
- Consumes: Task 1's CLI behaviour (`add-decision --automated --supersedes <automated id>` allowed; other targets refused).
- Produces: worksheet routes `proposed` and `individual` (replacing `auto`/`ask`), batch/number and owner reply per question; the batch display format below.

- [ ] **Step 1: Step 4 of `review-design/SKILL.md`** — replace the one-question-at-a-time sequence with the spec's flow steps 1–4: orchestrator answers saved as `<RUN>/orchestrator-<ref>.md` for a wave before it is dispatched; waves of at most 20 fresh agents in one message, each per `agent-prompts.md` section 7; compare as each finishes; conflict check against the current history with legacy counted as human; route `proposed` or `individual`. A human-conflict route records which human ruling, the quoted passage and why. Remove "agents run individually after their orchestrator answer is saved" from the dispatch paragraph near the top.

- [ ] **Step 2: Step 5** — replace "Automatic rulings first, without asking" and "Summarize every automated pass" with: batches of five shown as soon as five proposals are ready; individual questions only after the last batch. Batch format, per proposal:

```
**1. R40 — <title>**
Context: <one line, more for complex questions>
Question: <one line>
Proposed ruling: <one to several lines, scaled to complexity>
Supersedes: <id — what it said>   (only when replacing an automated ruling)
```

End each batch with `Reply with the numbers that are wrong; the rest are accepted ("ok" accepts all).` Reply handling: listed numbers → `individual`; others recorded with `--automated` (plus `--supersedes` where shown), each re-checked against rulings recorded earlier in the pass immediately before the write; an unclear number → `individual`. After each batch, report the ids recorded. The individual flow keeps today's current question / `Upcoming (Don't answer yet)` / `Question n of N` rules; a rejected proposal shows both answers there.

- [ ] **Step 3: Step 6 and 7** — step 6 counts bulk-accepted rulings as answered; step 7 states that a bulk accept is the owner's approval to apply, so `/apply-decision` runs on them like any other ruling, and that an `Automated: true` ruling recorded without a bulk accept still needs approval.

- [ ] **Step 4: Never list and Before anything** — replace "Never record automated disagreement…" with: never record a ruling the owner hasn't seen in a batch or answered; never put a human-conflicting proposal in a batch; automated supersession only of automated rulings.

- [ ] **Step 5: Conventions and history skills** — `agent-prompts.md` §7: the prompt is unchanged but dispatched in waves of up to 20. `triage.md`/`worksheet.md`: the routes, batch fields and resume rule (missing first answer → answer again from scratch). `decision-log-section.md`, `decision-log/format.md`, `record-decision`, `apply-decision`, `how-we-got-here`: automated rulings carry less weight than human ones; they may supersede automated rulings only; legacy counts as human; a bulk accept authorizes application.

- [ ] **Step 6: Fresh review** — dispatch one fresh general-purpose agent to read the changed skills and walk through: a full agreement, a disagreement, an agreement conflicting with ruling 1.2 (legacy), an agreement replacing an automated ruling, the reply "2, 5 are wrong", the reply "ok but 7", a late proposal contradicting a ruling accepted in an earlier batch, and a resume with a missing `orchestrator-<ref>.md`. It reports any step where the skills leak the first answer, record unseen rulings or route wrongly. Fix what it finds.

### Task 3: Verification

- [ ] **Step 1:** `just build` — expect the tools tests, log integrity, links and generated-file checks to pass.
- [ ] **Step 2:** `git diff --check` and `git status --short` — expect no changes to `docs/design/`, `docs/e2e-tests/`, `docs/decision-log.md` or `.config/`.

## After the plan

Resume `/review-design docs/reviews/2026-10-16-adversarial-design-review.md` from `/tmp/design-review-20261027-105615` under the new flow: map the worksheet's `ask` items to `individual` (R73 first), give the 51 questions without a completed pair the new step 4, and show the first batch when five proposals are ready.
