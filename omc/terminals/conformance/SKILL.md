---
name: conformance
description: "Read the record against the branch's code, and every decision of the branch carried into the protected documents and the code."
---

# conformance

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it reads the design
record against what the branch built, then every decision of the branch against the record, the protected documents it
reached and the code, and ends with one `OUTCOME` line. It fixes nothing: a finding in code is the task terminal's,
run by the orchestrator with it; a finding that needs a ruling goes back in the outcome, never settled here.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `record:` the record's path, `<date>-<slug>-design.md`
in `paths.specs` of `omc/config.yaml`, one of those `just omc record` prints.

**It reads and changes nothing.** It edits no file, changes no protected document (a file matched by `paths.protected`),
writes no entry and no question file, commits nothing, and runs no build, no test and no gate. Its only `just` commands
are `just omc record`, `just decisions list`, `just decisions show` and the read verbs of `just omc gitnexus` (`query`,
`context`, `impact`, `cypher`, through `/explain`), never `install` or `refresh`.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed (the merge-base, an id) is written out in the next one.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

```bash
(cd <root> && git merge-base HEAD origin/<base> && just omc record)
```

The first line is the merge-base; the record given is one of the paths after it, or the outcome is `failed`.

## 1. The record against the code

Read the record whole, then the branch's change, `git diff $(git merge-base HEAD origin/<base>)` (the branch is one
squashed commit by now; `--stat` first for its shape, then each file whole where a section is about it). For each
section of the record:

- **Built as written**: what the section says is built (a file, a verb, a table, a step, a behaviour, an exit code, a
  message) is in the diff and does what the section says; its exact values (names, paths, words) are the record's.
- **Nothing missing**: every path of `git diff --name-only` is explained by a section (or, when the record has one,
  by a row of its list of the files the work changes, and every such row is in the diff); a section's work the diff
  does not hold is a finding, unless the record itself leaves it out ("Out of scope", "Left to the builder"). The
  record's form is the brainstorm's and harden's: a section it does not have (a list of files, a table) is never a
  finding.
- **What the diff reaches**: `/explain` run for the symbols the diff changes (what calls them, what a change to them
  reaches), its citations checked in the tree as its step 3 says; a caller the diff reaches and did not follow is a
  finding when a section's rule says it should have.
- **Nothing contradicted**: no code contradicts a decision of the record's tables or a section's rule; where the code
  went another way, the record says so (an amendment) or it is a finding.
- **The record lags**: where the code is right and the record says otherwise (a value that moved during
  implementation, a row missing), the finding's fix is the record's amendment, the orchestrator's, never made here.

## 2. Decisions carried

The reading the guard does not do: `just decisions guard` proves that every changed protected document is named by an
applied entry, and `omc/tools/decisions/FORMAT.md` leaves the rest to a reader ("It does not prove … that the edit
matches the decision's words"). This part reads every decision of the branch against the record, the protected documents
and the code.

Run `just decisions list --branch`: every line is an entry recorded or applied on the branch (the log also holds
`<base>`'s deferred entries, left for a later branch, which `--branch` leaves out). None: say "no decision on this
branch; nothing to review" in the report, and this part has
no finding.

Otherwise read the record's section "Decisions and the pages they change", and per entry (`just decisions show <n>`):

1. **The record.** Its `Decision` against its row and the record's sections: does the record say what was ruled?
2. **The pages planned and reached.** Its real `Affected` against the row's planned pages and rules: a page planned
   and not reached, or reached and not planned, is explained (by the entry or the record) or is a finding.
3. **The pages.** `git diff $(git merge-base HEAD origin/<base>) -- <each page it reached>`, each page the file its real
   `Affected` names resolve to (`omc/tools/decisions/FORMAT.md` › "The names `Affected` takes"; the branch is one
   squashed commit by now, so the `Decision <n>: …` subjects are gone): do the pages now say what the decision says, and
   nothing beyond it?
4. **The code.** What the row says the decision means for the code, read against the diff of the branch's code (every
   changed path but the documents: the protected documents, the record, the plan, the log and the question files).

The grading of these readings: **Critical** for a decision missing from the pages or the code; **Important** for a page
or code that contradicts it; **Minor** for a drift of wording. So: a page the row planned and the entry did not reach,
unexplained, is **Critical** (the decision is missing from the pages); a page reached that the row did not plan,
unexplained, or a page that says more than the decision ruled, is **Important** (it contradicts what was ruled); the
record's row not saying what was ruled is **Important**. A finding in code is the task terminal's, as any finding. A
finding in a protected document is reported as a protected-document finding; never fixed here. Every entry is listed in
the report, a carried one as `decision <n>: carried`, so the report accounts for each.

## 3. Findings

One block per finding, numbered, in the report:

```text
FINDING 1
severity: Critical | Important | Minor
where: <file>:<line>
checked against: <the record's section, or decision <n> and its reading (1 to 4)>
what: <what differs, in one or two sentences, and the fix>
fix: code | protected document | record | ruling
```

`fix` says whose the fix is: `code` (code or tests: the task terminal's); `protected document` (a protected document
says other than the decision, or than what the code rightly does: never fixed by editing the page, it needs a ruling);
`record` (the record lags behind code that is right: its amendment); `ruling` (the record and the code disagree and
neither is plainly right). Section 1's grading: **Critical** for a section's work missing or a decision of the record
contradicted; **Important** for work built otherwise than the section says, a change no section explains, or the record
lagging; **Minor** for wording and naming.

## The outcome

The report above the line is prose for the orchestrator: each section of the record and how it was checked, every
entry and its four readings, then every `FINDING` block, Minor ones included. No Critical or Important finding is
`clean` (Minor alone is clean, and listed). The last line is one of:

```text
OUTCOME {"outcome": "clean"}
OUTCOME {"outcome": "findings", "critical": 1, "important": 2, "minor": 0}
OUTCOME {"outcome": "failed", "reason": "the record given is not one of just omc record's paths"}
```

`critical`, `important` and `minor` count the `FINDING` blocks of each severity. A finding that needs a ruling is not
a `needs_user` of this terminal: it is a `FINDING` block, and `findings` carries it to the orchestrator.

## Never

- Never edit a file: no protected document, no record, no plan, no code.
- Never write the log or an entry, never record a decision, never write a question file, never commit.
- Never settle a finding that needs a ruling: it is returned with its `fix`.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate.
- No `just` command but `just omc record`, `just decisions list`, `just decisions show`, `just omc gitnexus query`,
  `just omc gitnexus context`, `just omc gitnexus impact` and `just omc gitnexus cypher`; never `install` or
  `refresh`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
