---
name: record-decision
description: "Record a ruling of the owner in the one log the moment it is made, in any flow (brainstorm, design, plan, implementation, audit, a review, a question file's answer), through `just decisions add-decision` (with --defer, then `just decisions defer`, for a ruling the owner deferred in the same answer). Edits no page; /apply-decision does that. Used by the AI whenever the owner has ruled, for the agreement of /answer-doubt's two answers from /design on (Automated), and for a pick acted on there although the two answers disagreed (disagreed); never on the owner's word."
---

# Record a decision

The owner rules; the AI records. This skill is not run on the owner's word: the AI runs it itself, the moment the owner
has ruled, in whatever flow the ruling came up. A question answered during a brainstorm, `/design`, a plan, an
implementation task, an audit, a review, or an answer to a question file's question that affects a rule or the design is
a decision the moment it is answered. Its callers: `/pose-questions` after each answer, `/answer-doubt` for a page that
lags a rule and, from `/design` on, for the agreement of its two answers (both `Automated` entries) and for a pick acted
on although its two answers disagreed (`Automated: disagreed`), the screenshot review of `/audit`'s `screens` for a
ruling of a round, and any flow where the owner rules in passing, a remark in a conversation included. Recording is not
a step the owner authorizes, so it needs no lifecycle word; inside `/design`, `/implement` or `/audit` it is part of
that skill's work.

**No log configured.** The log is opt-in: when `omc/config.yaml` names no `paths.decision_log` (as shipped), there is
no log to write. The ruling is not recorded: the report says so in one line (`Not recorded: no decision log is
configured (paths.decision_log)`), the ruling stays in the conversation and in the record, and the calling flow goes on
as if the entry had been written. No `just decisions` command is run, and none is turned into a stop.

It writes one entry into the log (`paths.decision_log` of `omc/config.yaml`) through the decision tool; the entry, the
names `Affected` takes and the question file are in `omc/tools/decisions/FORMAT.md`; read it first. It edits no
protected document (a file `paths.protected` matches): `/apply-decision` does that. Until the entry is applied, the
branch's `just design-integrity-check`, and with it `/verify`, is red, on purpose. It spawns no agent; inside `/design`,
`/implement` or `/audit`, any agent a flow runs takes the model and effort `just omc models <role>` prints.

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; `<themes>…` (the theme files `paths.themes` matches) and `<protected>…`
(the files `paths.protected` matches) are written out in each command, and an empty list leaves its search out. The
texts of an entry go into shell variables set with single quotes or a single-quoted heredoc (`<<'EOF'`), so that a
backtick or a `$` in the owner's words is not read by the shell, and are passed in double quotes.

**Talking to the owner.** This skill talks to them rarely: one question when a ruling can be read two ways, and the
report. When one reply rules several things, each is its own entry, and the report opens with progress, done of
total (`Recorded 2 of 3; ahead: the stock-count ruling`). Every question shows what each option concretely produces,
never a bare label. A long message that asks questions ends with every question repeated as a numbered list, same
numbers, one line each with the recommended default.

## 1. Input

- The ruling in the owner's words, as they gave it: their own sentence, or a picked option they confirmed (`ok` to a
  batch of `/pose-questions` confirms each picked answer in it). For an `Automated` entry, the docs' reading or the
  answer `/answer-doubt`'s two answers agreed on, as that skill words it; for a `disagreed` entry, the answer it picked
  and acted on, with both answers.
- Its context: what was asked, what was wrong, the passages it was asked about.
- Where it came from: a question of a question file (`<date>-<branch-slug>-<n>.md` of `paths.questions`, `### Q<k> …`),
  an item of a review file, a section of a record (of `paths.specs`), or a remark in a conversation.

Look first whether the log already holds it: `(cd "$ROOT" && just decisions list)`, and `just decisions show <n>`
for a candidate. A ruling already recorded is not recorded again. A ruling that changes an entry no commit ever held
(recorded in this worktree since its last commit) changes that entry: `just decisions update <n> --decision …` (and
any other field), or `just decisions remove <n>` when the owner withdraws it, once no file names it any more. A
ruling that changes a committed entry gets a new entry whose `Context` names the earlier one (`replaces decision
41`); the committed entry is never changed (the tool refuses it), and `/apply-decision` applies it with
`--affected ""` so that only the new one reaches the pages.

## 2. Context and Decision

Separate the two. `Context` is why: what was asked, what was wrong. `Decision` is what now holds, in one to three
sentences. Both are the owner's words, cleaned up, never added to: no reason, no scope and no case they did not give.

Write them in their vocabulary, the words of the theme files: read their vocabulary rules, where a theme file holds
them, and the rules the ruling touches (`grep -n '<word>' <themes>…`); the rule wins where a page disagrees. Say what a
thing is called in the pages, never a coined shorthand. A story id or scene id written plainly is linked by the tool.

Missing context, or a ruling that can be read two ways, is one question to the owner at once, while they have the
context, with what each reading produces; never a guess. This question is not one for `/answer-doubt`: only they can
say what they meant.

## 3. Automated

- `false` (the default, no flag): the owner's ruling, in their own words or as a picked option they confirmed.
- `--automated`: only for a decision the owner did not rule, in two cases. Settled by the docs: a rule carried into a
  page that lagged it; the docs ruled. Or, inside `/design`, `/implement` or `/audit` (the autonomous run), ruled by the
  agreement of `/answer-doubt`'s two answers (its step 6): its `Context` says so, in the words "ruled by the agreement
  of `/answer-doubt`'s two answers", its `Decision` is the agreed answer, its `Source` the question of the run's
  question file. `just decisions list` shows the owner every such entry at the audit.
- `--disagreed`: only inside `/design`, `/implement` or `/audit`, for an answer the run acted on although
  `/answer-doubt`'s two answers disagreed (its step 6, "Act, record `disagreed`"): its `Context` holds the question,
  both answers and that the independent agent disagreed, its `Decision` the picked answer, its `Source` the question
  of the run's question file. It is not yet ruled: `just decisions pending` names it, and the push is red on it until
  the owner rules it after their screenshot review.

Never both flags: the tool refuses `--automated` with `--disagreed`. An owner's ruling is never `--automated` or
`--disagreed`, however small. Their later ruling on a committed `disagreed` or `true` entry is never an `update` of it:
they confirm it, `just decisions confirm <n>` (`disagreed` → `false`; a `true` entry they confirm changes nothing), or
overrule it, their ruling recorded as a new entry `<m>` (no flag) and then `just decisions overrule <n> --by <m>`
(`Automated: overruled by <m>`). `/pose-questions` and `/answer-doubt`'s limit run those two; this skill records the
new entry.

## 4. Title

One line, the gist of the decision, in the style of the log's headings (`Incidents need a photo`): what now holds,
not what was asked.

## 5. Affected

The best guess of what the decision reaches, in the names of FORMAT.md ("The names `Affected` takes"): a rule `R9.3-2`,
a subtheme or theme `T9.3`, a story `W9.2`, a scene `shift.incident`, a view `views/shift_incident`, a component
`incident_row`, a protected file by its vault path `architecture/objects/port.yaml`, a heading of a protected document
`architecture/operations.md#Incidents`. Find them with

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && grep -n '^#' <themes>…)
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && grep -n '<word>' <protected>…)
```

and read the candidates. The real set is `/apply-decision`'s, which replaces this one: a guess is fine, an empty set
is fine (no `--affected`), an invented name is not, and the tool refuses it. Names are comma-separated, so a heading
named here holds no comma.

## 6. Source

Where the decision came from, always a heading, as a vault path (relative to the vault, the top folder of
`paths.decision_log`) and the heading's text; with the default paths:

- a question of a question file: `reviews/<question file>.md#Q3 <title>`;
- an item of a review file: `reviews/<review file>.md#<item heading>`;
- a section of a record: `superpowers/specs/<record>.md#<section heading>`;
- a remark in a conversation: no `--source`.

The tool writes it as a link and refuses a file or a heading that does not exist.

## 7. Run it

```bash
ROOT=$(git rev-parse --show-toplevel)
TITLE='Incidents need a photo'
CONTEXT=$(cat <<'EOF'
Members record incidents without proof and the owner cannot check them at close.
EOF
)
DECISION=$(cat <<'EOF'
Every incident carries a photo; without one the row is a warning.
EOF
)
AFFECTED='R9.3-2, T9.3, W9.2, shift.incident, incident_row'
SOURCE="reviews/2026-01-05-incident-photos-1.md#Q3 A member's incident without a photo"
(cd "$ROOT" && just decisions add-decision --title "$TITLE" --context "$CONTEXT" --decision "$DECISION" \
  --affected "$AFFECTED" --source "$SOURCE")
```

Add `--automated` or `--disagreed` only as step 3 says; leave out `--affected` for an empty set and `--source` for a
remark in a conversation. The tool prints the id `<n>`, or refuses with `error: <why>` (an unknown name, a heading that
does not exist) and writes nothing: fix the name or the heading (or drop a name you cannot place) and run again. Read
the entry back:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions show <n>)
```

and check that `Context` and `Decision` say what the owner said. A wrong entry no commit ever held is corrected with
`just decisions update <n>`; a committed one is not edited: record a new one that replaces it (step 1).

**`--defer`**: run with it when the owner deferred this ruling in the same answer that gave it (a ruling made after
`/design`, which they chose to leave for a later branch: `omc/tools/decisions/FORMAT.md` › "The entry"). The entry is
recorded as above, then deferred, recorded on the base branch unapplied for a later branch:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions defer --id <n> && just decisions show <n>)
```

Its `Status` reads `recorded <date> · deferred <date>`; it is no longer pending and backs no page. Never on the
session's word alone, never in the brainstorm or `/design` (design-stage rulings are applied), and never for an
overruling entry (the `<m>` of `just decisions overrule <n> --by <m>`: it undoes work of this branch and is applied in
it; the tool refuses it). A refusal of `defer` leaves the entry recorded: say so in the report.

## 8. The question file

When the source is a question of a question file and its status line is still `open` or `answered`, it becomes the
entry's number:

```
**Status.** decision <n>
```

(`open` → `answered` → `decision <n>`, FORMAT.md). A status already `decision <n>` is left as it is: a follow-up
ruling recorded with the same `Source` keeps the first entry's number there. Change only that line of that block; the
question file is not a protected document.

## 9. Report, commit nothing

Commit nothing: the flow's next commit carries the log (and the question file); `/apply-decision` commits the log whole
with its pages. Report

```
decision <n> recorded: <title>
```

(`decision <n> recorded and deferred: <title>` with `--defer`, which is then no longer pending, applied on a later
branch) and, for a recorded one, that `/verify` stays red until it is applied: `just decisions pending` names it until
it is applied with `/apply-decision <n>`: by an apply task of the plan when it was recorded before implementation
(`/design`'s `harden` folds it into the record first), or by `/review-decisions` (at the end of `/implement`, or on its
own). Then go back to the flow that called this skill.

## Never

- Never edit a protected document; `/apply-decision` does that.
- Never edit the log by hand; it is written only through `just decisions`.
- Never change a committed entry; a wrong one gets a new entry. An entry no commit ever held changes only through
  `just decisions update` or `remove`.
- Never record a ruling the owner did not give, or add to their words what they did not say; the one exception is an
  `Automated` or `disagreed` entry of step 3 (the docs' reading, the agreement of `/answer-doubt`'s two answers from
  `/design` on, or a pick acted on there although they disagreed), which says so in its `Context`.
- Never pass `--automated` or `--disagreed` for an owner's ruling, and never both flags.
- Never `update` a committed entry for the owner's later ruling on it: `confirm`, or a new entry and `overrule`.
- Never wait for the owner's word to record a ruling they gave; never ask them whether to record it.
- Never commit; never start `/apply-decision` on your own.
- Never `--defer` a ruling the owner did not defer, a ruling of the brainstorm or `/design`, or an overruling entry.
