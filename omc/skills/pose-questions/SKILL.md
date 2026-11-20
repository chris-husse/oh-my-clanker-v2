---
name: pose-questions
description: "Take the run's entries the owner did not rule and the open questions of question files to them: the disagreed entries one at a time, the agreed entries five at a time, then the agreeing questions five at a time with the picked answer and the rest one at a time; confirm or overrule each entry, record every ruling at once through /record-decision and ask the follow-up doubts while the owner has the context; after design (from /audit, or by hand), one message to apply or defer the new rulings, on their word."
---

# Pose the questions

The questions a run collected through `/answer-doubt` reach the owner here, and so do the entries the autonomous run
recorded without their ruling (`Automated: disagreed`, acted on although the two answers disagreed, and
`Automated: true`, ruled by their agreement): each is posed from its question, and they confirm or overrule it (step
3). Every open question of the question files is collected, similar ones merged, and asked in one process: the
agreeing ones five at a time, each shown with the answer picked for it, then the rest one by one, the picked answer
shown even where it was uncertain. Every ruling is recorded at once through `/record-decision`, and the gaps it leaves
are asked while the owner still has the context. The question file's form is `omc/tools/decisions/FORMAT.md`
("# The question file").

It runs as step 2 of `/review-decisions` (from `/audit`'s item after the owner's screenshot review it names the run's
entries), from `/design`'s `integrity` (a `questions` line of its check), or on the owner's word; never on your own
initiative. `/answer-doubt`'s limit asks in its one-by-one form (step 6). Its input is the entries and the question
files to pose, `/pose-questions [decision <n>…] <question file>…`; with no question file named, every question file of
`paths.questions` (of `omc/config.yaml`) that holds an open question, and with no entry named, no entry. It edits no
protected document. It writes only the question files' `**Status.**` lines and `**Differs.**` lines, and the log only
through `/record-decision`, the two commands of an entry's ruling, `just decisions confirm` and
`just decisions overrule` (step 3), and `just decisions defer` for a ruling they deferred (step 8). It commits nothing:
the question files and the log are the caller's to commit (`/review-decisions` step 2 commits the question files and the
log once this skill ends; `/design` commits them with the design).

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; the configured paths are written out in each command: `<questions>` is
the folder `paths.questions` (ending with `/`), `<themes>…` the theme files `paths.themes` matches (none: that search is
left out).

**Talking to the owner.** Every message opens with the progress line of step 3, counted from the files just before it is
written, never carried over from an earlier message. Every question shows what each option concretely produces, never a
bare label. A long message that asks questions ends with every question repeated as a numbered list, same numbers, one
line each with the recommended default. Inside this work an "ok" means continue: record what it accepts and go straight
on to the next batch or question; never stop between batches or questions to report. Use the owner's vocabulary (the
theme files' words): "the log", "an entry", "recorded", "applied", "deferred", "the protected documents", "a question
file", "a review file"; never a coined compression. Never make the owner repeat a comment: what they said once holds
for every question it answers, with every clause.

## 1. Collect and merge

Find the question files and their open questions:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions pending; grep -l '^# Questions: ' <questions>*.md)
```

Read each question file named (or, with none named, each one `pending` lists) whole. Every block whose
`**Status.**` is `open` is a question to pose; a block already `answered` or `decision <n>` is not asked again, but
it is read: it is the owner's earlier answer.

Merge the questions that ask the same choice about the same situation (the same rule, the same screen, the same
case met in two tasks or two runs): one item, shown once with every question id it holds (`Q3 and Q7`, or with the
run when the files differ, `Q3 of run 1 and Q2 of run 2`), its ruling written to each of them. An item whose
questions disagree in their `**Subagent.**` line or in their `**Picked.**` answer goes one by one.

## 2. Check before each message

Every batch entry, question and follow-up passes these checks each time, just before the message is written:

- **The owner's own words.** Check it against the owner's words in the log's entries (`just decisions list`, then
  `just decisions show <n>`: their `Context` and `Decision` hold their words) and in the question files' earlier
  answers. Strike every clause an agent or a lagging page added; never carry a ruling's scope wider or narrower than
  they said it. An agreeing question that would contradict a recorded entry goes one by one, with that entry quoted.
- **Already answered.** Search the old rulings before asking: the rules (`grep -n '<word>' <themes>…`; a rule's sources
  line names `owner <date>` for their ruling), the log's entries, the answered questions of the other question files
  (`grep -n '<word>' <questions>*.md`). A question the docs answer is not asked: its status becomes `answered`, and a
  page that lags the rule is an `Automated` entry through `/record-decision --automated`. Never ask again what the owner
  ruled as fundamental (for example: each person edits only their own records; nothing is accepted for a closed period).
- **The real question.** A case only a bug, a stale phone or an app on another version can cause is asked as the
  design question behind it (what the server does with an old app's call, say), or settled as `answered` when a rule
  covers it.

The next message names, one line each, the questions settled this way, with the rule or entry that settles them
(`Q5 is settled by R9.3-2, "…"; not asked`), so the owner sees every question of the run.

## 3. Sort and count

**The order.** Run from `/audit`'s item after the screenshot review (through `/review-decisions`, which names the
run's entries), the owner is asked in this order:

1. the run's `disagreed` entries, one at a time, in step 6's form;
2. the run's `Automated: true` entries, five at a time, in step 4's form; an entry they do not name wrong is confirmed;
3. then the open questions, as below: the agreeing ones five at a time, then the rest one by one.

Run with no entry named, only the third.

**Posing an entry.** An entry is posed from `just decisions show <n>` and the question its `Source` names, read in its
question file (its `Question`, `Options`, `Picked`, `Subagent` and `Where`); the entry's `Decision` is the picked answer
already acted on. Its two outcomes:

- **Confirmed** (an "ok", an accepted batch entry, the recommendation taken): a `disagreed` entry,
  `ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions confirm <n>)`, its `Automated` becoming `false`;
  a `true` entry, nothing. The question's status stays `decision <n>`.
- **Overruled** (any other ruling): their ruling recorded through `/record-decision`, not automated, as step 7 says, its
  `Context` naming the entry it replaces (`replaces decision <n>`) and its `Source` the same question; it prints `<m>`.
  Then `ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions overrule <n> --by <m>)`, the old entry's
  `Automated` becoming `overruled by <m>`. The question's status keeps `decision <n>` and gets its `**Differs.**` line
  (step 7), so that the follow-through undoes what was acted on; `/review-decisions` applies `<m>` (step 3 there).

An entry already `false` or `overruled by <m>` (ruled at the limit's stop, or earlier) is not posed again.

The agreeing items are those whose `**Subagent.**` line ends in `, agree.` (never `, disagree.`) and that passed step
2 unchanged; every other item is one by one: a disagreement, a question with no subagent answer, a conflict with a
recorded entry, a merged item that split. Within each list, the items go in consequence order: what the records and the counts
hold, then what a person may do or sees, then the rest.

The progress line, word for word:

```
**Progress: <d> of <total> answered. Ahead: <a> agreeing (<b> batches), <i> one by one.**
```

With entries posed, the line opens its `Ahead:` with them:
`Ahead: <x> disagreed entries one by one, <y> agreed entries (<c> batches), <a> agreeing (<b> batches), <i> one by one.`,
`<total>` and `<d>` counting the entries with the items.

`<total>` counts the items open when the run began (a merged item once); `<d>` those whose questions are no longer
`open` (an entry recorded, `answered`, or settled in step 2); `<a>` the agreeing items not yet shown or answered and
`<b>` their batches, five to a batch; `<i>` the one-by-one items not yet answered, those sent there from a batch
included. A message without this line is a defect.

## 4. The agreeing questions, five at a time

Every agreeing item first, five per message, numbered 1 to 5 (the last batch may hold fewer). Each entry: its title in
plain words; what a person sees today and what changes, in plain words, in two lines; the options with what each
produces; the picked answer; last, one short line `*Ref: …*` with the rule ids and file paths it rests on (a merged
item's question ids go there too). No id or path before that line. After the entries, the recap: every question of the batch repeated as a numbered list, same numbers, one line each with the picked answer as
the recommended default; then the closing sentence below, last, nothing after it.

```
**Progress: 0 of 12 answered. Ahead: 7 agreeing (2 batches), 5 one by one.**

Batch 1 of 2 (agreeing questions 1–5; then 5 one by one).

**1. A member's incident without a photo**
Today a member can record an incident with no photo, and nothing flags it. A delivery without a photo already shows a
warning at the close.
Options: (1) refused: it can't be saved without a photo · (2) saved, and the close shows a warning · (3) saved
plainly, no photo asked for.
Picked: (2), the same as a delivery; the subagent agrees.
*Ref: Q3, R9.3-2*

**2. …**
…

1. A member's incident without a photo: (2) saved, and the close shows a warning
2. …: (…)
…

Reply with the numbers that are wrong; the rest are accepted ("ok" accepts all).
```

## 5. The batch reply

Read the reply against the batch just shown, never guessing:

- **Accepted** is every number not named wrong ("ok" accepts all; "ok except 2" and "ok but 2 is wrong" are clear: 2
  wrong, the rest accepted). A number may also be given as the question id (`Q3`).
- **A number named wrong** goes to the one-by-one list, asked in step 6 after every batch, never in the next message.
  When the rejection carries a question or an objection ("What?", "that makes no sense"), answer it in the next
  message in a few sentences with the docs' evidence behind the picked answer; the question goes one by one all the
  same, and only a definite ruling in their own words is recorded from it.
- **A doubt** about one entry ("not sure about 3") sends it one by one.
- **An amendment** ("2, but only for the supervisor") sends that entry one by one, the amendment carried into its
  message as their words, so they never repeats it; the rest of the reply is read as usual.
- **A question about an entry** ("what does 3 change?") is answered, then the same batch is shown again: nothing is
  recorded from that reply, and it does not count as unclear.
- **An unclear reply**: a number or id that names nothing in the batch, or "ok" next to numbers without saying which
  way ("ok 2 4", "ok, 3"). Record nothing from it and show the same batch once more, saying which part did not match;
  a second unclear reply sends every entry of the batch one by one.

Record each accepted item in batch order (step 7). Just before each write, check it against the entries recorded so
far in this run: one that duplicates an entry is not recorded again (its questions take that entry's number), and one
that now contradicts an entry goes one by one. Then the same message reports the entries recorded (`decision 42:
<title>`) and goes on with the next batch; after the last batch, with the first one-by-one question.

## 6. The rest, one by one

This step starts only when no agreeing item waits: never a `Question n of N` while the progress line shows an
agreeing question ahead. The one exception is the run's `disagreed` entries, which come first, before every batch
(step 3's order). One question per message: `Question n of N` (`N` the one-by-one items; the same `n` while a
question and its follow-ups are discussed; `N` updated when items are added or merged). Show only the current
question; under Codex, whose replies come slowly, also the next one as a preview labelled exactly `Upcoming (Don't
answer yet)`, and read a reply against the current question only.

Each question: its title in plain words; what a person sees today and what changes, in plain words (what the pages
say now may be quoted, their file and heading going to the `Ref:` line); the question as one sentence ending in a
question mark, before the options; the options and what each produces; both answers (`Picked`, `Subagent`), the
disagreement or the conflict explained (a conflicting entry quoted); your recommendation with its reason; what was
already acted on (`Acted on. yes`); last, one short line `*Ref: …*` with where the question arose (the step, the file
and symbol), the rule ids and the pages' files and headings. No id or path before that line. The message ends with every question it asks repeated as a numbered list,
same numbers, one line each with the recommended default: one line for the question alone, one more per follow-up
when follow-ups are asked with it.

```
**Progress: 7 of 12 answered. Ahead: 0 agreeing (0 batches), 5 one by one.**

**Question 1 of 5: A photo added after the incident**

<what a person sees today and what changes, in plain words; what the pages say now: "…">

What does an incident row show once its missing photo is added later in the shift?

(1) a plain row: the warning goes the moment the photo is there · (2) the warning stays: the close still shows the
incident as recorded without proof · (3) …
Picked (1): <why>. Subagent (2): <its choice and conditions>, disagree.
Recommendation: (1), because …
Acted on: yes, (1).
*Ref: Q4; implement, task 4, `app/incidents.py` (`attach_incident_photo`); `<theme file>`, "T9.3 …"*

1. What does an incident row show once its missing photo is added later? Recommended: (1), a plain row.
```

A question the owner asks back is answered, then the same question is shown again under the same number. An "ok"
accepts the recommendation. An answer that leaves the choice open on purpose ("later") keeps the question `open`
(`pending` lists it, and the run's end names it); an answer readable two ways is asked once more while they have the
context. Never guess.

## 7. After each answer

- **A ruling** (an accepted batch entry, an answer, an "ok"): `/record-decision` with the ruling in the owner's words
  and every clause of them, or the picked option they confirmed; the question's situation as the context; `Automated`
  false; `Source` the question's heading, `<question file>#Q<k> <title>` (its path under the vault, the top folder of
  `paths.decision_log`) (the first question's, for a merged item); the best guess of `Affected` from its `Where` and
  `Picked`. The question's status becomes `decision <n>`; `/record-decision` writes it for the question it names, and
  you write it for every other question of a merged item.
- **"The docs already say so"**: the status becomes `answered`, and an `Automated` entry is recorded only when a page
  lagged (`/record-decision --automated`, which then writes `decision <n>`).
- **It differs from what was acted on**: when the question says `**Acted on.** yes` and the ruling is not its `Picked`
  answer, add `**Differs.** <what the code and tests did>` under its `**Status.**` line, so the follow-through revisits
  them.

Edit each line with the Edit tool on its own block (every block has a `**Status.**` line, so never a replacement
across the file); touch nothing else of the block.

**The gaps, while the owner has the context.** Before the next question, work out what the protected documents will need
that the answer does not say: when it happens, who does it, what it books, what a screen shows, the neighbouring case;
a new rule the answer brings (a new task kind, a new tab, a new setting) gets its gaps the same way. Each gap goes
through `/answer-doubt` (a) first: one the docs settle is not asked. What remains is asked at once, in the next
message, under the same question number, one short follow-up with a recommendation per gap, never deferred to the end;
that message ends with every follow-up repeated as a numbered list with the recommended default. Each ruling it brings
is recorded at once through `/record-decision` with the same `Source`; the question's status keeps the first entry's
number. A gap the owner leaves open is named at the run's end.

## 8. Apply or defer

After design, a ruling may be **deferred**: recorded on the base branch (`base` of `omc/config.yaml`) unapplied, for a
later branch (`omc/tools/decisions/FORMAT.md` › "The entry"). When every item is answered, this message follows, run
from `/audit` (its `push` item after the screenshot review, through `/review-decisions`) or by hand after design (a plan
is committed on the branch: `just omc plan` exits 0). Never in the brainstorm or `/design` (its `integrity`):
design-stage rulings are applied, and the step is skipped; nor when the screenshot review of `/audit`'s `screens` names
its round's question file, whose own apply-or-defer message lists these rulings with the rest of the round.

One message lists every entry this run recorded (`/record-decision` in step 7, its gaps' follow-ups included), each
with its title, the pages it reaches and the session's suggestion: **apply** (the branch's gist needs it) or **defer**
(unrelated to the branch, or a clear extension of it). Never listed, always applied: an **overruling entry**, the
`<m>` of `just decisions overrule <n> --by <m>` (it undoes work this branch did; `defer` refuses it), and an entry
already applied. The message ends with the list as a numbered recap, one line each with the suggestion as the
recommended default; the owner confirms or flips them in one answer ("ok" takes every suggestion). The session never
defers on its own. Each one they defer:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions defer --id <n>)
```

It prints the id; a refusal (`error: …`) leaves the entry recorded, applied with the rest, and is said in the report.
No entry recorded in this run: the step is skipped, said in one line.

## 9. The end

When every item is answered and step 8 is done: run `just decisions pending` and report the entries recorded
(`decision <n>: <title>`, `Automated` true or false), the entries confirmed (`decision <n> confirmed`) and overruled
(`decision <n> overruled by <m>`), the entries deferred (`decision <n> deferred`), the questions settled by the docs,
the `**Differs.**` lines written, and what the owner left open. Within `/review-decisions`, go on with its step 3;
within `/design`'s `integrity`, back to its `harden`; on the owner's word, end with
`Next: /review-decisions applies them (verify stays red until every entry is applied)`.

## Never

- Never record what the owner did not say: no clause an agent or a page added, no scope wider or narrower than theirs.
- Never ask a question the docs answer, or one the owner already ruled.
- Never skip the progress line.
- Never ask a one-by-one question while an agreeing question waits (the run's `disagreed` entries, first, aside),
  and never guess an unclear reply.
- Never make the owner repeat a comment; never stop between batches or questions to report.
- Never edit a protected document, write the log but through `/record-decision`, the two commands of an entry's ruling
  (step 3), `just decisions confirm` and `just decisions overrule`, and `just decisions defer` (step 8), or change a
  question block beyond its `**Status.**` and `**Differs.**` lines.
- Never run a `just decisions` subcommand FORMAT.md does not list; here only `pending`, `list`, `show`, `confirm` and
  `overrule` for an entry's ruling (step 3), and `defer` for a ruling the owner deferred (step 8).
- Never defer a ruling the owner did not confirm deferred, an overruling entry, or a ruling of the brainstorm or
  `/design`.
- Never start this skill on your own, and never apply an entry: that is an apply task of the plan or `/review-decisions`
  step 3.
