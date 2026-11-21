---
name: impact
description: "Read what the base branch brought between two merge-bases against what the branch touches: each overlap a lag or a conflict; reads and changes nothing."
---

# impact

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: after a rebase onto
`<base>` it reads what `<base>` brought between the old merge-base and the new one against what the branch touches,
sorts every overlap into a lag or a conflict, and ends with one `OUTCOME` line, which is its whole answer. It reads
and returns: the conflicts as questions, the lags as data. What becomes of them (a question asked and its ruling
recorded, a lag folded into the record or followed in the code) is the orchestrator's.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `old_base`: the old merge-base. `new_base`: the new
merge-base. `phase: design` or `phase: audit`: the phase that rebased, which says where a lag has to follow (below).

`old_base` is taken as given (it is the mark `.cache/omc/impact`, the oldest merge-base whose impact is pending, as
the rebase reported it): `<old base>` below; `new_base` is `<new base>`. The mark is the orchestrator's to remove,
never this terminal's.

**It reads and changes nothing.** It edits no file, changes no protected document, writes no entry and no question file,
commits nothing, and runs no build, no test and no gate. Its only `just` commands are `just decisions list` and
`just decisions show`.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a command
printed is written out in the next one; so are the configured paths, read from `omc/config.yaml`: `<log>` is
`paths.decision_log`, `<specs>` and `<plans>` are `paths.specs` and `paths.plans` (folders, ending with `/`),
`<protected>…` are the globs of `paths.protected`, each written as a `':(glob)<glob>'` pathspec, and `<not shots>…`
those of `paths.screenshots`, each as `':(glob,exclude)<glob>'` (none when the list is empty).
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

## 1. Nothing came in

`<old base>` equal to `<new base>`: `<base>` brought nothing, the outcome `none` at once. Otherwise what `<base>`
brought, in short:

```bash
(cd <root> && git diff --stat <old base> <new base> -- <log> <protected>… <not shots>…)
```

It prints nothing: `<base>` changed no decision and no protected document, the outcome `none` at once.

## 2. What `<base>` brought

```bash
(cd <root> && git diff <old base> <new base> -- <log> <protected>… <not shots>…)
```

The log's part is the entries `<base>` recorded, applied and trimmed between the two merge-bases; the rest is the
protected documents it changed (the screenshots aside). With `paths.protected` empty only the log is read.

## 3. What the branch touches

- **Its entries**: `just decisions list --branch`, and `just decisions show <n>` for each. After the rebase's trim the
  log still holds `<base>`'s deferred entries, left for a later branch: `--branch` leaves them out (but one the branch
  took in and applied).
- **Its record and plan**: the `*-design.md` of `paths.specs` and `*-plan.md` of `paths.plans` the branch added since
  `<new base>`, and their rows in the section "Decisions and the pages they change":

  ```bash
  (cd <root> && git diff --name-only --diff-filter=A <new base> -- '<specs>*-design.md' '<plans>*-plan.md')
  ```

- **Its changed code and tests**: every path the branch changed but the documents (the protected documents, the record,
  the plan, the log, the question files):

  ```bash
  (cd <root> && git diff --name-only <new base>)
  ```

## 4. Lag or conflict

Every overlap is one of two:

- **LAG**: the branch only has to follow a rule or a page `<base>` changed. A file overlap alone misses one: a rule `<base>`
  changed that the branch's new code or tests depend on is a lag too, though no file of the branch changed with it.
- **CONFLICT**: `<base>`'s ruling and the branch's disagree (an entry of the branch, a section of the record, code or a
  test that holds the other rule).

Where a lag has to follow, by phase. With `phase: design` (before implementation) the record's section that has to
follow it, or, with no record yet, the entry of the branch it reaches: nothing else is changed there. With
`phase: audit` the code, the test or the entry, file and symbol.

One block per item, numbered by kind:

```text
LAG 1
main's side: <the entry, or the page and its heading>
the branch's side: <the entry, the record's section, the code or the test: file and symbol>
what has to follow: <what changes, and where>

CONFLICT 1
main's side: <the entry, or the page and its heading>
the branch's side: <the entry, the record's section, the code or the test: file and symbol>
question: <the question, in one sentence>
options:
- <option>: <what it produces>
- <option>: <what it produces>
pick: <the option it would pick, and why>
```

Nothing overlaps: the outcome `none`.

## The outcome

The report above the line is prose for the orchestrator: the two merge-bases, what `<base>` brought in a line or two, then
every `LAG` and `CONFLICT` block, lags first. The last line is one of:

```text
OUTCOME {"outcome": "none"}
OUTCOME {"outcome": "found", "lags": 2, "conflicts": 1}
OUTCOME {"outcome": "failed", "reason": "fatal: bad object <old base>"}
```

`lags` and `conflicts` count the blocks above it. A conflict is never settled here, and it is not a `needs_user` of
this terminal: it is a `CONFLICT` block, and `found` carries it to the orchestrator. `failed` is a merge-base git
cannot read.

## Never

- Never edit a file: no protected document (a file matched by `paths.protected`), no record, no plan, no code.
- Never write the log or an entry, never record a decision, never write a question file, never commit.
- Never settle a conflict or follow a lag: both are returned.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate.
- No `just` command but `just decisions list` and `just decisions show`.
- Never start an agent or a skill that starts one or that talks to the owner: the `OUTCOME` line is the whole answer.
