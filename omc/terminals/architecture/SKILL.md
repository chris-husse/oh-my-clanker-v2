---
name: architecture
description: "Read the branch's code against the project's technical design (the protected documents that describe the code) and against the code the base branch brought."
---

# architecture

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it reads the branch's code
against the technical design (the protected documents, `paths.protected` of `omc/config.yaml`, that describe the code:
its modules, layers, seams and contracts), and against the code `<base>` holds around what the branch touches, and ends
with one `OUTCOME` line. It reads what no other terminal reads: `conformance` holds the code to the record and the
decisions, while this one holds the code to the pages it must follow whether or not the branch has a decision, and to
the code it now sits beside. It fixes nothing: a finding in code is the task terminal's, run by the orchestrator with
it; a finding that needs a ruling goes back in the outcome, never settled here.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `record:` the record's path, `<date>-<slug>-design.md`
in `paths.specs` (read for why the code is as it is; where the record chose against a page, that choice is the finding's
subject).

**It reads and changes nothing.** It edits no file, changes no protected document (a file matched by `paths.protected`),
writes no entry and no question file, commits nothing, and runs no build, no test and no gate. It reads with `git`,
`grep` and the files themselves.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed (the merge-base) is written out in the next one.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

## 1. The branch's code

```bash
(cd <root> && git merge-base HEAD origin/<base> && git diff --stat $(git merge-base HEAD origin/<base>))
```

The first line is the merge-base. The code is every changed path but the documents (the protected documents, the record,
the plan, the log, the question files and the briefs of `omc/config.yaml`'s `paths`). No such path: say "no code change;
nothing to review" in the report, and the outcome is `clean`. Otherwise read `git diff <merge-base> -- <path>…` over
those paths, and each changed file whole where the diff alone does not show what a function reads, writes or calls.

## 2. Against the technical design

With `paths.protected` empty, or none of its documents describing the code, this section finds nothing: say so in the
report, and on to section 3.

- **The index first**, where the technical design has one (a page that says which page holds what). From it, the pages
  of the modules, tables, operations and components the diff touches, each read at the headings the diff reaches.
- **The rules code follows**, where the technical design holds a page of them (an implementation guide), whole: every
  change the diff makes is read against it.

For each change ask: does it do what the page says this part does, in the place the page puts it (the layer, the
package, the seam), through the doors the page names, with the names, errors and contracts the page fixes? Code that is
right where the page lags (a page that does not yet say what the code rightly does) is a protected-document finding:
reported as such; never fixed here.

## 3. Against the code `<base>` brought

The branch was squashed and rebased onto `origin/<base>` before this review, so `git log --stat <merge-base>..origin/<base>`
is empty: what `<base>` brought is in the code at the merge-base. Read it around each symbol the branch touches:

```bash
(cd <root> && git grep -n '<symbol>' <merge-base> && git show <merge-base>:<path>)
```

- its callers and its callees as `<base>` has them, and the helpers beside it: a helper, a type or a pattern `<base>`
  holds that the branch duplicates, bypasses or reimplements is a finding;
- a function, a table or an operation the branch relies on whose meaning `<base>` changed (it builds and its tests
  pass, but it no longer does what the branch's code assumes);
- the conventions of the module as `<base>` writes them now (errors, names, the order of a body's steps), where the
  branch's code follows an older form.

## 4. Findings

One block per finding, numbered, in the report:

```text
FINDING 1
severity: Critical | Important | Minor
where: <file>:<line>
checked against: <the page and its heading, or <path> at the merge-base and its symbol>
what: <what differs, in one or two sentences, and the fix>
fix: code | protected document | ruling
```

`fix` says whose the fix is: `code` (the task terminal's); `protected document` (the page must change: never fixed by
editing the page, it needs a ruling); `ruling` (the code and the page disagree and neither is plainly right).
**Critical**: a rule of the implementation guide broken, a layer or a seam crossed that a page forbids, code that breaks
what `<base>`'s code relies on. **Important**: code that contradicts a page's structure or contract, a helper of `<base>`
duplicated or bypassed, a meaning `<base>` changed that the branch's code still assumes, a page that lags behind code that
is right. **Minor**: naming, placement, an older form of a convention.

## The outcome

The report above the line is prose for the orchestrator: the code read, the pages read and the symbols looked up at
the merge-base, then every `FINDING` block, Minor ones included. No Critical or Important finding is `clean` (Minor
alone is clean, and listed). The last line is one of:

```text
OUTCOME {"outcome": "clean"}
OUTCOME {"outcome": "findings", "critical": 1, "important": 0, "minor": 2}
OUTCOME {"outcome": "failed", "reason": "git merge-base HEAD origin/<base>: no merge-base"}
```

`critical`, `important` and `minor` count the `FINDING` blocks of each severity. A finding that needs a ruling is not
a `needs_user` of this terminal: it is a `FINDING` block, and `findings` carries it to the orchestrator.

## Never

- Never edit a file: no protected document, no code, no record.
- Never write the log or an entry, never record a decision, never write a question file, never commit.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
