---
name: harden
description: "Harden the design record section by section against the vault and the code it cites, fold every entry without a row, bring it in line with the base branch's lags; edits the record only."
---

# harden

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it checks the design
record section by section against the vault and the code it cites, folds into it every entry of the branch that has no
row, brings it in line with what `<base>` brought, and ends with one `OUTCOME` line. It fixes what is wrong in the record
and returns every doubt as a question: a ruling is never this terminal's, and what becomes of a question (asked, its
ruling recorded, this terminal run again) is the orchestrator's. The log, the entry and the record's rows are
`omc/tools/decisions/FORMAT.md` ("The entry", "The names `Affected` takes", "The integrity check").

**Inputs** (in the prompt, one per line). `Root:` the worktree. `record:` the record's path, `<date>-<slug>-design.md`
in `paths.specs` of `omc/config.yaml`. `lags:` the `LAG` blocks of the impact terminal as it returned them, or `none`.
`problems:` the `PROBLEM:` lines of `just design-integrity-check --phase design` the orchestrator hands over (a `record`
line, a `links-check` line in the record), or `none`.

**It edits the record only.** No other file: no protected document (a file matched by `paths.protected`), no plan, no
code. It never writes the log, never records a decision, never writes a question file and never commits: the record is
committed by the orchestrator. It runs no build, no test and no gate; its only `just` commands are
`just decisions list`, `just decisions show` and the read verbs of `just omc gitnexus` (`query`, `context`, `impact`,
`cypher`, through `/explain`), never `install` or `refresh`.

**The tree it starts on is the run's.** The record may be uncommitted (an earlier pass's edits), and so may the log
(`paths.decision_log`): the orchestrator's step `fresh` trims it of `<base>`'s entries (`just decisions trim`) and
commits that trim later, so a log that differs from `HEAD` by entries marked applied and removed is the run's own
trim. Neither is someone else's change: the report never names them as such, and never as outside this terminal's
remit.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed (`<start hash>`) is written out in the next one.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

## 1. The record before

```bash
(cd <root> && git hash-object -- <record>)
```

It prints the record's hash as it is now, before this run edits anything: `<start hash>`, for the outcome. `changed`
means that this run edited the record, never that the record differs from `HEAD` (the record stays uncommitted
across runs, so a comparison with `HEAD` would say `changed` every time). A record that does not exist is `failed`.

## 2. Section by section

Every `##` section of the record, in order. For each, every claim it makes about the vault or the code is checked
against the page or the code it cites: the page by file and heading (a rule by its id in the theme files,
`paths.themes`), the code by file and symbol, read in the tree; for a section's cited code, `/explain` is run with the
section's question (where it is handled, what calls it) and its citations checked in the tree, as its step 3 says. A
claim that names no source but states a fact of the tree (a recipe of the justfile, a function's arguments, a file that
exists) is checked the same way. Then one of three:

- **It holds**: nothing to do.
- **It is wrong** (a renamed heading, a moved file or symbol, a misread rule, a count or a name that the tree says
  otherwise): the record is fixed, in that section, to say what the page or the code says. The rules win over every
  page; a page that says otherwise lags them.
- **It is a doubt**: the record disagrees with a rule or a protected document in force on purpose (it means to change
  it) and no entry of the branch rules that change (`just decisions list --branch`, `just decisions show <n>`); or the
  page and the code disagree and the record would follow one of them; or the source does not settle it. Nothing is
  edited for it: it is a question in the report (below). A disagreement an entry of the branch rules is no doubt: the
  record follows the entry.

## 3. The fold

Which entries: those of the branch the record has no row for in its section "Decisions and the pages they change".
`just decisions list --branch` against the record's rows (a row is a table row of that section, outside code fences,
whose first cell begins `decision <n>`, a backtick before it allowed; a later cell's `replaces decision <m>` never
counts), and every `PROBLEM: record:` line of `problems`, which names such an entry. `<base>`'s deferred entries, which
the plain `list` shows too, are not the branch's and are never folded (the owner picks which ones a branch takes
in). A row the seed put for a deferred entry the owner took into the branch (the brainstorm's seed) stays: it is kept,
never dropped as not the branch's. None: step 4. Otherwise each, in id order,
read with `just decisions show <n>`:

1. its row in the record's table of decisions taken (the brainstorm's table; the next id in the record's own
   numbering, the decision in one sentence, its source: the owner's words as the entry gives them);
2. its row in the section "Decisions and the pages they change", created when missing after that table's section,
   below its closing paragraphs and before the next `##` heading, one row per entry, in id order:

   ```text
   | Decision | Planned pages and rules | What it means for the code |
   |---|---|---|
   | `decision <n>`: <its title> | <the names the entry will reach> | <one or two sentences, or the record's section that says it> |
   ```

   The planned pages and rules are the names the entry will reach, plain as `just decisions add-decision --affected`
   takes them and not as links (e.g. `architecture/operations.md#Deploy`), the entry's Affected the starting point.
   The first cell reads `decision <n>` in those words: `just decisions renumber` rewrites that form after a rebase. A
   paragraph of the section that says no entry is recorded is rewritten once a row is there;
3. every section of the record the entry materially changes, rewritten so that the record says it: the record is the
   whole truth of the branch.

An entry that replaces another (`replaces decision <n>` in its Context) keeps the replaced entry's row, its last cell
saying "replaced by decision <m>", and the sections follow the new entry.

A passage an entry leaves unclear is a question in the report, with its options; the fold of what is clear goes on.

## 4. The lags and the problems

- **Each `LAG` block of `lags`**: its "what has to follow" names the record's section that has to follow what `<base>`
  changed; that section is rewritten to follow `<base>`'s rule or page, and the report names it. A lag that would change
  what an entry of the branch rules is not followed here: the entry is the owner's, and it is a question.
- **Each `PROBLEM:` line of `problems`**: a `record` line is folded (step 3, the entry it names). A `links-check` line
  in the record is fixed in the record: the link pointed at the heading, the file or the rule the vault holds now,
  read in the tree. A line no edit of the record settles is a question.

## 5. The questions

One block per question, numbered, in the report:

```text
QUESTION 1
where: <the record's section; the entry, page or code it touches: file and heading or symbol>
question: <the question, in one sentence>
options:
- <option>: <what it produces in the record, the pages and the code>
- <option>: <what it produces>
pick: <the option it would pick, and why>
```

A question is one whose answer would change a rule, a protected document or the design of the record; a choice that
changes none of them is made here and written into the record, never asked.

## The outcome

Then the record after this run:

```bash
(cd <root> && git hash-object -- <record>)
```

It prints `<start hash>`: `unchanged`; any other hash: `changed`. The report above the line is prose for the
orchestrator: the sections fixed (each heading and what was wrong), the entries folded, the lags followed and the
problems fixed, then every `QUESTION` block. The last line is one of:

```text
OUTCOME {"outcome": "changed", "questions": 1, "edits": "cosmetic"}
OUTCOME {"outcome": "unchanged", "questions": 0}
OUTCOME {"outcome": "failed", "reason": "docs/superpowers/specs/2026-01-05-x-design.md does not exist"}
```

`questions` counts the `QUESTION` blocks above it, on either outcome.

`changed` carries `"edits"`, `material` or `cosmetic` (`unchanged` carries none). Material: an edit that changes what
gets built or decided: a decision folded, a step, a dep or a hidden input added or removed, a behaviour, a page or rule
the record reaches, a lag followed. Cosmetic: a line citation, a quote, wording, a list of passages that stay true, a
table's layout. One material edit among cosmetic ones makes it `material`.

## Never

- Never edit a file but the record: no protected document, no plan, no code.
- Never write the log or an entry, never record a decision, never write a question file, never commit.
- Never settle a doubt: it is a question, returned.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate.
- No `just` command but `just decisions list`, `just decisions show`, `just omc gitnexus query`,
  `just omc gitnexus context`, `just omc gitnexus impact` and `just omc gitnexus cypher`; never `install` or
  `refresh`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
- Never `git add`, `git restore` or `git checkout` the record: its edits stay in the tree for the orchestrator.
