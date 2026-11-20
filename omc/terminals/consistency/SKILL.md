---
name: consistency
description: "Read the branch's entries against each other, the record and the protected documents they reach; return each conflict with its options."
---

# consistency

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it reads every entry of
the branch against the other entries, the design record and the protected documents each entry reaches, and returns each
conflict as a question with its options, ending with one `OUTCOME` line. A conflict is never settled here: asking it,
recording the ruling and folding it into the record are the orchestrator's. The log and the entry are
`omc/tools/decisions/FORMAT.md` ("The entry", "The names `Affected` takes").

**Inputs** (in the prompt, one per line). `Root:` the worktree. `record:` the record's path, `<date>-<slug>-design.md`
in `paths.specs` of `omc/config.yaml`.

**It reads and changes nothing.** It edits no file, changes no protected document, writes no entry and no question file,
commits nothing, and runs no build, no test and no gate. Its only `just` commands are `just decisions list` and
`just decisions show`.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed (an id) is written out in the next one.

## 1. What it reads

- **Every entry of the log** (`paths.decision_log`): `just decisions list`, then `just decisions show <n>` for each. The
  log holds the branch's entries and no other. No entry: the outcome `consistent` at once.
- **The record** given.
- **Every protected document each entry's Affected names reach** (FORMAT.md › "The names `Affected` takes"): a theme
  file's subtheme and its rules, or the document a name reaches, at the heading the name gives.

## 2. Each entry

For each entry ask: does it contradict

- another entry;
- a rule or a page in force that it does not itself change; or
- the design of the record?

An entry that replaces another (`replaces decision <n>` in its Context) does not conflict with the entry it replaces:
that pair was ruled already, and the replaced entry is read as replaced.

## 3. The report

One block per conflict, numbered:

```text
CONFLICT 1
entries: decision <n>[, decision <m>]
passage: <the page and its heading, or the record's section>
what disagrees: <one sentence>
options:
- <option>: <what it produces>
- <option>: <what it produces>
pick: <the option it would pick, and why>
```

Then one line per entry that fits: `decision <n>: consistent`. The report above the `OUTCOME` line is prose for the
orchestrator: the entries read, every `CONFLICT` block, then the lines of the entries that fit.

## The outcome

The last line is one of:

```text
OUTCOME {"outcome": "consistent"}
OUTCOME {"outcome": "conflicts", "count": 2}
OUTCOME {"outcome": "failed", "reason": "just decisions list: error: <why>"}
```

`count` counts the `CONFLICT` blocks above it. A conflict is not a `needs_user` of this terminal: it is a `CONFLICT`
block, and `conflicts` carries it to the orchestrator.

## Never

- Never edit a file: no protected document (a file matched by `paths.protected`), no record, no plan, no code.
- Never write the log or an entry, never record a decision, never write a question file, never commit.
- Never settle a conflict: it is returned with its options.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate.
- No `just` command but `just decisions list` and `just decisions show`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
