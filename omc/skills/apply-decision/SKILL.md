---
name: apply-decision
description: "Apply one recorded (or deferred) decision of the log to the protected documents it reaches (the rules of the theme files, the stories, every file paths.protected matches), mark it applied with the real Affected set, and commit the pages and the log together. Run as an apply task of an implementation plan, as step 3 of /review-decisions, or on the owner's word; never on your own initiative."
---

# Apply a decision

The protected documents (every file `paths.protected` of `omc/config.yaml` matches) change only through an entry of the
log applied on the branch, and this is the only skill that edits them. It takes one entry of the log,
`paths.decision_log`, recorded by `/record-decision`, makes every passage it reaches say what it says, marks it applied
with the pages it really touched, and commits those pages and the log in one commit. The entry, the names `Affected`
takes and the guard are in `omc/tools/decisions/FORMAT.md`; the link rule is the vault's `LINKS.md`, where the project
keeps one.

**When it runs.** An implementation plan runs it in one task per entry, in id order, each a fresh agent (the plan rule
of `omc/terminals/write-plan/SKILL.md`); `/review-decisions` step 3 runs it in one fresh agent per pending entry, in id
order; the owner may run it themselves, `/apply-decision <n>`. A deferred entry (the owner deferred it to `<base>`, for
a later branch) is applied the same way, by the plan task of the branch that takes it in. Never start it on your own
initiative.

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; the configured paths of `omc/config.yaml` are written out in each
command: `<log>` is `paths.decision_log` (no log configured: `<log>` is dropped from the command, and a step about the
log is skipped), `<questions>` the folder `paths.questions` (ending with `/`), `<themes>…` the
theme files `paths.themes` matches and `<protected>…` the files `paths.protected` matches (an empty list leaves its read
out). The log is written only through `just decisions` (`just decisions <subcommand> --help`); its subcommands are
`add-decision`, `apply-decision`, `defer`, `undefer`, `update`, `remove`, `confirm`, `overrule`, `show`, `list`,
`pending`, `guard`, `trim`, `resolve`, `renumber` and `check`, no other; this skill runs `show`, `list`,
`apply-decision` and `guard`. A text that goes into a command (a title, a commit body) travels in a shell variable,
never pasted into the command, so a backtick or a `$` in it is not read by the shell.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

**Talking to the owner.** Run on the owner's word, every message to them opens with progress: done of total and what is
ahead (`Step 3 of 8: 2 of 4 pages edited; then the mark, the guard and the commit`). Every question shows what each
option concretely produces, never a bare label. A long message that asks questions ends with every question repeated as
a numbered list, same numbers, one line each with the recommended default. Run by a plan task or by `/review-decisions`,
the agent talks to no one: its stop or its report goes back to the caller, which prints done and left.

## 1. Gate

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions show <n>)
```

The entry's `**Status.**` line must read `recorded <date>` or `recorded <date> · deferred <date>` (a deferred entry,
taken in by this branch), with no `· applied`; an entry already applied, or an id the tool refuses, stops with what it
printed. A deferred entry is applied as a recorded one; its status then reads
`recorded <date> · deferred <date> · applied <date>`, the history kept. Then the tree:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git status --porcelain --untracked-files=all | while IFS= read -r l; do p=${l:3}; [ "$p" = <log> ] && continue; case "$p" in <questions>*.md) head -1 -- "$p" 2>/dev/null | grep -q '^# Questions: ' && continue;; esac; printf '%s\n' "$l"; done)
```

It lists every change but the log and the question files under `paths.questions` (a question file's first line starts
`# Questions: `). Anything listed stops the run with the list: a protected document edited by hand, a review file, code.

**A replaced entry.** An entry a later recorded entry replaces (its `Context` says `replaces decision <n>`,
`/record-decision` step 1) reaches no page: its decision no longer holds. Find it with
`(cd "$ROOT" && just decisions list)` and `just decisions show` of the later recorded entries. Skip steps 2–4, mark it
applied with `--affected ""` (step 5), then steps 6–8; the commit carries the log alone, and the later entry is
applied in its own run.

## 2. Read

Read the entry whole: its `Context`, `Decision`, `Automated`, `Affected` (the recorder's best guess, not the set)
and `Source`. Then the pages it names and what they link, in this order:

- **The theme files first** (`paths.themes`): the rule, its subtheme, and the rules pointing at it,
  `(cd "$ROOT" && grep -n 'See R<id>' <themes>…)`. Where a page disagrees with a rule, the rule wins and the page lags.
- **The stories** (`stories/*.md` of the vault, the top folder of `paths.decision_log`), where the project has them.
- **The other protected documents**: every heading the decision reaches; a document's form is the `FORMAT.md` of its
  folder, where the project keeps one.

A passage the decision reaches may be on a page `Affected` does not name: search the rule ids and the words of the
decision, `(cd "$ROOT" && grep -n '<word>' <themes>… <protected>…)`. The pages you will touch are the real set.

When the decision does not settle how a passage it reaches must read (it is readable two ways there, or the page needs a
ruling the entry does not give), stop before editing anything: report the passage (file and heading), the question as
one sentence and its options with what each produces; the entry stays recorded. The caller takes the question to the
owner (`/answer-doubt`, `/pose-questions`); run on the owner's word, ask them.

## 3. Edit

Make every passage the decision reaches say what the decision says, in the pages' vocabulary, nothing more: no rewording
of what it does not touch, no fix of a lag it does not cause (a lag you notice elsewhere: name it in the report, do not
fix it). The order is the docs' own: rules, then stories, then the other protected documents.

- **A changed rule**: its text in place, the line `- [R9.3-2] …` keeping its id.
- **A new rule**: under its subtheme, with the next number after the subtheme's highest; an id is never reused, so a
  number a withdrawn rule once had is skipped (`(cd "$ROOT" && git log -1 --oneline -S '[R9.3-5]' -- <themes>…)` prints
  nothing for a number never used). A new subtheme gets the next number under its theme, the same way.
- **A withdrawn rule**: its line and its sources line removed, with a sentence on the rule that replaces it where one
  does, as the theme files write it ("(9.4's … is withdrawn)"). A `See R<id>` rule pointing at it is removed with it or
  pointed at the rule that replaces it.
- **The sources line** of a new or changed rule, the indented ` (…)` line under it, names the pages it rests on
  (`data-model.md › shift`, `member.md › [W2](…)`, as its neighbours write them) and `owner <date>` for an owner's
  ruling (`Automated: false`; the date the entry was recorded), never the entry's number: it is scratch.
- **A story**: the passage the decision changes, in the story's words. Its `**Rules.**` line names a new subtheme
  the story rests on; the `@hash` on that line is not yours.
- **Another protected document**: edited under its headings, in the page's own words and in the form of its folder's
  `FORMAT.md` where there is one; a heading keeps its text unless the decision renames it. A `references` block gets no
  `{ref: <n>, …}` line: the entry's number is scratch.

New text is written as its neighbours are (a story id in a rule as its link, as the vault's `LINKS.md` writes it).

A ruling that would remove from a page a button, row or step the person uses to solve the situation the page
shows is not applied there: list the page and the step it would lose, and stop for the owner (apply the ruling
everywhere else).

## 4. Never in this step

- Links: a renamed heading or a moved page breaks links elsewhere; that is `/reconcile-links`.
- The tests and the code.

A changed rule or a renamed heading may leave a link stale in `just links-check` (a story's `stale-rule`); that is
expected and is the follow-through's (the plan's links task, or `/review-decisions` step 4), not this skill's.

## 5. Mark applied

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions apply-decision --id <n> --affected "<every page touched, by name>" && just decisions show <n>)
```

`--affected` is comma-separated, every page touched at least once, by the names of `FORMAT.md`: a rule (`R9.3-2`) or a
subtheme (`T9.3`) for its theme file (a withdrawn rule's id reaches nothing: name its subtheme), a story (`W9.2`), a
scene (`shift.incident`), a view (`views/shift_incident`), a component (`incident_row`), a heading of a protected document
(`architecture/operations.md#Incidents`), or the page's vault path (`architecture/objects/port.yaml`,
`screens/FORMAT.md`), which always reaches it; a page deleted on the branch by its vault path or its plain scene id. A
name holds no comma: a heading with one is named by its page's path. `--affected ""` when the pages already said it
and nothing was touched, and for a replaced entry (step 1). The tool refuses a name that reaches nothing and leaves
the log untouched: fix the name and run again.

## 6. Guard

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions guard)
```

It must name none of the files this step changed. An `UNBACKED:` line for another file belongs to another entry:
report it, do not fix it. A line for one of yours means a name in step 5 missed it: stop and report it, with no
commit; the entry is applied and the log is never edited by hand, so the caller decides. A missing `origin/<base>`
is `error: no origin/<base>: git fetch origin`: fetch, then run the guard again.

## 7. Commit

One commit: the log whole (other entries recorded and not yet applied travel with it) and exactly the pages
touched, each by its path (a deleted page by its old path, a renamed one by both); never `git add -A` or `.`.
Question files stay as they are: their caller commits them. The subject is `Decision <n>: <title>`; the body is the
entry's text below its heading with its links read as text, through the tool's own `unlink`, so an anchor with
parentheses survives:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && entry=$(just decisions show <n>) && title=$(printf '%s\n' "$entry" | sed -n '1s/^### [0-9][0-9]* //p') && body=$(printf '%s\n' "$entry" | tail -n +2 | UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -c 'import sys; sys.path.insert(0, "omc/tools/decisions"); from decisions import unlink; print(unlink(sys.stdin.read()).strip())') && test -n "$title" && test -n "$body" && git add -- <log> <page> … && git commit -m "Decision <n>: $title" -m "$body" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <log> <page> … && git show --stat --format='%h %s' HEAD)
```

## 8. Report

`decision <n> applied: <title>`, the commit and the pages touched (or that the pages already said it), and the
`UNBACKED:` lines of other entries and the lags noticed, if any. When a rule changed (changed, added or withdrawn),
end with:

`Next: the follow-through (the plan's links task, or /review-decisions step 4): just links-check names what went stale`

One entry per run; the plan or `/review-decisions` runs the next.

## Never

- Never start this skill on your own initiative: a plan's apply task, `/review-decisions` step 3 or the owner invokes
  it.
- Never change `Context` or `Decision`: a wrong decision gets a new entry through `/record-decision`.
- Never apply two entries in one commit.
- Never edit the log by hand: `just decisions apply-decision` is this skill's only write to it.
- Never touch the review files under `paths.questions`.
- Never edit a protected document beyond what the decision says, and never one outside this skill.
- Never write an entry's number into a page: not in a `references` block, not in a rule's sources line.
- Never fix links, tests or code here: the follow-through does.
- Never `git add -A` or `git add .`.
