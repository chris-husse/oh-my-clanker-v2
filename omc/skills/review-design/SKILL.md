---
name: review-design
description: "Review an owner-written review file under paths.questions (a rulings file, an open-items file, a future review): extract its questions, merge similar ones, answer each through /answer-doubt with the owner's recorded answers as input, write the run's question file, and hand over to /review-decisions. The owner invokes this; never run it on your own."
disable-model-invocation: true
---

# Review a review file

A review file is one the owner wrote or signed off under the questions folder, `paths.questions` of `omc/config.yaml`
(`<questions>` below, ending with `/`), that is neither the log nor a question file: a file of rulings, a file of open
items, a future review. This skill reads it, cuts it into units, merges the units that ask the same, and takes each
question through `/answer-doubt` in its review flow, which answers it from the docs or collects it in the run's question
file with the picked answer and an independent agent's. Then `/review-decisions` takes over: it poses the questions,
records the answers, applies every entry and carries the change through. The log, the entry and the question file are in
`omc/tools/decisions/FORMAT.md`; read it first.

It runs on the owner's word only, `/review-design <review file>`; never on your own initiative. It edits no protected
document (a file `paths.protected` matches) and never the review file. It writes only the run's question file (through
`/answer-doubt`, and its italic line in step 5); the log only through `/record-decision`, which `/answer-doubt` runs for
a page found lagging a rule. It commits nothing itself but the review file, alone, when the owner says so at the start;
`/review-decisions` commits the question file with the log.

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; a path or a number a command printed is written out in the next one, and
so are `<questions>` and `<log>` (`paths.decision_log`). The only `just decisions` subcommands this skill runs are
`list` and `show`; `/answer-doubt`, `/record-decision` and `/review-decisions` run their own.

**Talking to the owner.** This skill asks them at most one question, at the start: which file, when none is named, or
whether to commit the review file, when it has changes git does not hold. That message opens with progress (before step
1 of 5, and what is ahead), shows what each option concretely produces, and ends with the question repeated as a
numbered list with the recommended default. Every other question goes into the run's question file, and
`/pose-questions` (step 2 of `/review-decisions`) takes it to them; never ask one mid-run. Between waves print only the
progress line of step 4 and go straight on; never stop to report. Use their vocabulary (the theme files' words): "the
log", "an entry", "recorded", "applied", "the protected documents", "a question file", "a review file"; never a coined
compression.

## 1. The file

**The argument** is one file under `<questions>`, as a repository path (`<questions><name>.md`) or its name alone
(`<name>.md`). With none, ask which: list the files under `<questions>` that are neither the log nor a question file,
each with its first heading, and recommend the oldest. Then check it:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && f='<argument>'; case "$f" in */*) ;; *) f="<questions>$f";; esac; f=$(realpath -m --relative-to=. -- "$f"); case "$f" in <questions>*.md) ;; *) echo "REFUSED $f: not a Markdown file under <questions>"; exit 0;; esac; [ -f "$f" ] || { echo "REFUSED $f: no such file"; exit 0; }; [ "$f" = <log> ] && { echo "REFUSED $f: the log"; exit 0; }; head -1 -- "$f" | grep -q '^# Questions: ' && { echo "REFUSED $f: a question file"; exit 0; }; s=$(git status --porcelain -- "$f"); if [ -n "$s" ]; then echo "UNCOMMITTED $s"; else echo "OK $f"; fi)
```

- `REFUSED`: tell the owner the reason and stop. A file outside `<questions>` is no review file. The log holds entries
  already recorded: `/review-decisions` applies them. A question file (its first line starts `# Questions: `) holds
  questions already collected: `/pose-questions` takes those to them.
- `UNCOMMITTED`: the file has changes git does not hold. The run's questions point at its headings, and
  `/apply-decision` stops on any change but the log and the question files, so the file is committed first. Ask:

  ```
  **Progress: before step 1 of 5. Ahead: the units, the merge, the answers, the question file, then /review-decisions.**

    `<questions><name>.md` has changes git does not hold (`<the status line>`).

  Commit it alone first? (1) yes, with a one-line message you give: the file is committed alone with it, and the review
  starts · (2) no: the review stops, nothing is written.

    1. Commit `<questions><name>.md` alone first, with your one-line message? Recommended: (1).
  ```

  Yes, with their message:

  ```bash
  ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && MSG=$(cat <<'EOF'
  <the owner's one-line message>
  EOF
  ) && git add -- '<questions><name>.md' && git commit -m "$MSG" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- '<questions><name>.md' && git show --stat --format='%h %s' HEAD)
  ```

  No: stop.
- `OK`: go on.

**Understand the file.** Read it whole (a long file in parts, `sed -n '<a>,<b>p'`). No form is assumed. Write two or
three sentences: what the file is, where it came from, what it mostly concerns; the first names the review file as a
link relative to `<questions>` (`[2026-01-05-rulings.md](2026-01-05-rulings.md)`). Tell the owner these sentences and go
on; they become the question file's italic line in step 5.

## 2. The units

The unit is a numbered item where the file has them (`### 1. A task's end on a phone`,
`### Q3 A write-off sent offline`), else a heading, else a paragraph. A heading over a list of separate items, each its
own choice (a `### person` heading over its fields' disagreements), is cut into one unit per item. Each unit has a
reference in the file's own terms: `1`, `Q3`, a heading's text, and for a paragraph or a list item the heading above it
and a short quoted phrase (`person, "next_pay_day: the old core steps"`); no line number, no number of your own. When
the file holds a merged list and the findings it merged, the units are the merged entries, and the findings are reached
through the references each cites.

**A confirmation** is a unit the owner already answered in the file (`**Answer:** …`). They have ruled; the question is
whether the docs already say so. Their answer, quoted with the unit's reference, is "the owner's answer on record" for
`/answer-doubt`. A confirmation is never dropped as not material: they answered it, so it is settled only when the docs
already say what they answered. Every other unit is a real question: two passages that both read as right and disagree,
a choice the file leaves open, two items or answers that pull apart. When in doubt, a real question.

## 3. Merge

Merge the units that concern the same passage and the same choice: one question, listing every unit it merges (`Q3,
Q7 and Q12`). A confirmation and a real question merge only when the owner's answer settles the question's choice;
two confirmations whose answers differ do not merge. Each question keeps, from its units, the passages they quote and
cite, and the owner's answers on record, each with its unit's reference.

Number the questions in file order of their first unit; `<total>` is their count. Print
`units: <u>; questions: <total> (<m> of them merged)` and go on.

## 4. The answers, in waves

First find the run's question file as `/answer-doubt` step 5 does (its command lists the branch's question files and
their open questions) and note whether it exists yet, and note the log's last id:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions list | tail -1)
```

Each question goes through `/answer-doubt` (`.claude/skills/answer-doubt/SKILL.md`), followed by reading it, with this
input (its step 1):

- **The question**, in one or two sentences, in the owner's words where the unit has them.
- **Where**: `review, [<item heading>](<review file's path relative to <questions>>#<anchor>)`, the heading of the
  question's first unit (for a paragraph or a list item, the heading above it), then every other merged unit's
  reference:
  `review, [Q3 A write-off sent offline](2026-01-05-open-items.md#Q3%20A%20write-off%20sent%20offline), merging Q7, Q12`.
  The anchor is the heading's text without its `#`s, every space `%20`, every backtick `%60`, every other character as
  it is (the vault's `LINKS.md`, where the project keeps one). This is the block's `**Where.**` line.
- **The passages read**: each unit's text quoted with the review file's path and line, and the pages it cites.
- **The flow**: a review (`/review-design`): collect only, never act.
- **The owner's answer on record**, for a confirmation: their words quoted with the review file and the unit. It goes to
  both answers: into your hidden answer as their ruling, and into the agent's prompt, marked as the owner's, as
  `/answer-doubt` step 4 writes it. It is theirs, not yours: the hidden discipline covers only your own answer.

The questions go in waves of at most twenty, in their order. For each wave:

1. **From the docs.** For each question of the wave, `/answer-doubt` steps 1–3. A question the docs settle ends there
   with its `settled from the docs: <answer> (<file:line>)` line, and an `Automated` entry through
   `/record-decision --automated` when a protected document lags a rule. One that an open question of the run's question
   file already asks is merged into it (step 3).
2. **Two answers.** For every remaining question of the wave, step 4's neutral question and your hidden answer, each
   in its own hidden folder, all written before any agent runs.
3. **The agents.** Every independent agent of the wave in one message, one per question, at most twenty, each with
   step 4's brief and nothing else; the retries of step 4 together in one message after them.
4. **Compare and write.** Step 5 for each question, in order: a docs-settled one goes back to step 2's line, every
   other is appended to the run's question file. Then step 6, a review: `**Acted on.** no`.

After each wave print exactly, and go straight on:

```
questions answered: <d> of <total>
```

`<d>` counts the questions done: settled from the docs, merged into an open question, or written.

## 5. The question file, then /review-decisions

**Its italic line.** When the run's question file is new (the first `/answer-doubt` of this run created it), replace
its italic line with step 1's sentences followed by `/answer-doubt`'s fixed sentence, as one italic line. A file that
already held open questions of this branch keeps its line; step 1's sentences go below it as an italic line of their
own, after an empty line. Use the Edit tool on that line only. No question written: no file, nothing to edit.

**The tally.** Print it:

- the units (confirmations, real questions) and the questions after merging, each merged one with the units it holds;
- the questions settled by the docs, each with its quote (file and line);
- the questions written: the question file, their `Q` ids, how many agree and how many disagree, and the units each
  holds;
- the `Automated` entries recorded, from `just decisions list` against the last id noted in step 4: `decision <n>:
  <title>`.

**Hand over.** Invoke `/review-decisions` with the Skill tool (`skill: review-decisions`). It poses the questions,
records the answers, applies every entry and carries the change through; its step 2 commits the question file with
the log. This skill commits nothing more.

## Not ported

- The worksheet: the question file alone holds the run.
- The waves of the old skill's form, its cluster, verify-review and iteration passes: here each question has
  `/answer-doubt`'s one agent, at most twenty at once.
- The log's sections: one flat log, no `new-section` or `close-section`.
- `/validate-design`.
- `/how-we-got-here`.

## Never

- Never run on your own: the owner invokes it.
- Never ask the owner a question mid-run; the only ones are the argument's and the commit question of step 1.
  `/pose-questions` asks the rest.
- Never show the independent agent your answer, your leaning or the hidden folder's path.
- Never edit a protected document, or the review file beyond its commit at the owner's word.
- Never write the log but through `/record-decision`, and never record a ruling yourself: the owner's answers on
  record reach the log through `/pose-questions`, once they have confirmed them.
- Never run a `just decisions` subcommand but `list` and `show`.
- Never more than twenty agents in one message.
