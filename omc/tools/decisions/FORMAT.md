# The log

`paths.decision_log` of `omc/config.yaml` (`docs/decision-log.md` by default) is the one decision log: one file, one flat list of entries, no sections. It is
scratch space: an entry is recorded when the owner rules, applied when the protected documents carry it, and trimmed once
it is applied on `<base>`. It is written only through `just decisions` (the tool below).

```
# Design decision log

*Scratch space: decisions recorded and not yet carried through, trimmed once applied on main. Written only through
`just decisions`. Next: 42*

### 41 Incidents need a photo

**Context.** Members record incidents without proof and the owner cannot check them at close.
**Decision.** Every incident carries a photo; without one the row is a warning.
**Automated.** false
**Affected.** R9.3-2, T9.3, [W9.2](../stories/member.md#W9.2%20—%20An%20incident), [shift.incident](../screens/definitions/shift.incident.md), incident_row, [Incidents](../architecture/operations.md#Incidents)
**Source.** [Q3](2026-01-05-incident-photos-1.md#Q3%20A%20member's%20incident%20without%20a%20photo)
**Status.** recorded 2026-01-05 · applied 2026-01-05
```

**The header** is everything above the first entry. Its `Next: <n>` is the number the next entry takes; the tool
advances it with every entry it adds. It is the one state a trim keeps, so a number is never used twice. A header
without `Next:` (the log's old header) holds no entries for the tool and refuses `add-decision`.

# The entry

An entry is a `### <n> <title>` heading and its fields, one line each, in this order; a field with nothing in it is
not written. Its number is its id everywhere: a `Source` line, a commit message, a question file's `decision 41`.

- `Context` and `Decision` are the owner's words, cleaned up. Once committed they never change; a wrong decision gets a
  new entry. An entry no commit ever held (by its id or its title) is the worktree's own: `update` rewrites its fields
  and `remove` drops it. The tool links every story id and scene id mentioned in them (outside code spans and links).
- `Automated` is `true` for a decision no owner ruling was made for: settled by the existing docs (a rule carried into a
  page that lagged), or by the agreement of `/answer-doubt`'s two answers from `/design` on, its `Context` then saying
  it was ruled by that agreement; `false` for the owner's ruling, whether in their own words or as a picked option they
  confirmed. Always written; `list` shows the owner every entry they did not rule.
- `Affected` names what the decision reaches, in the names below. At recording it is the best guess;
  `apply-decision` replaces it with the real set. An entry applied with nothing to change has no `Affected`.
- `Source` is where the decision came from: a question of a question file, an item of a review file, a section of a
  record, always a heading, never only the file.
- `Status` is `recorded <date>` at recording and `recorded <date> · applied <date>` once applied: the two forms.

Technical and product decisions sit side by side; what tells them apart is what `Affected` names.

## The names `Affected` takes

`--affected` takes a comma-separated list; so a heading named in it holds no comma. Each name is resolved to the file
it reaches, and a name that reaches nothing is refused (the whole call, the log untouched). A name may also reach a
protected document deleted on the branch (present at the merge-base, gone from the working tree), so that an entry can
name the page it deletes.

| Name | Reaches | Written as |
|---|---|---|
| a rule, `R9.3-2` | the theme file (`paths.themes`) holding its line `- [R9.3-2] …` | `R9.3-2` |
| a subtheme or a theme, `T9.3`, `T9` | the theme file holding its heading | `T9.3` |
| a story, `W9.2` (level-3 or level-4 heading `W9.2 — …` of the vault's `stories/*.md`) | its stories page | its link, `[W9.2](../stories/member.md#W9.2%20—%20An%20incident)` |
| a scene, `shift.incident` | the vault's `screens/definitions/shift.incident.md` | its link; the plain id for a page deleted on the branch |
| a view, `views/shift_incident` | the vault's `screens/views/shift_incident.md` | `views/shift_incident` |
| a component, `incident_row` | the vault's `screens/components/incident_row.md` | `incident_row` |
| a protected file by its vault path, `architecture/objects/port.yaml`, `screens/FORMAT.md` (the vault, the top folder of `paths.decision_log`, may lead) | that file | the path |
| a heading of a protected document, `architecture/operations.md#Incidents` | that page | its link, `[Incidents](../architecture/operations.md#Incidents)` |

A story and a scene are written as links because `links-check` reports them as `unlinked` in `paths.questions`; every
other name is plain text. Every link is a standard relative Markdown link relative to the log, with its anchor as
Obsidian writes it (every space `%20`, every backtick `%60`, everything else raw), as the vault's `LINKS.md` says, where
the project keeps one. A vault without stories or screens has no such names: only the rules, the subthemes and the paths
and headings of protected documents. Reading `Affected` back, a link reaches the file of its destination and every other
name the file it resolves to.

# The guard

The protected documents are every file the globs of `paths.protected` of `omc/config.yaml` match (none by default).
Adding, deleting and renaming count as changes. They change only through an entry applied on the branch.

`just decisions guard` takes every protected document whose text differs between the merge-base
(`git merge-base HEAD origin/<base>`, `<base>` the base branch, `base` of `omc/config.yaml`; "main" in the tool's
output is that branch) and the working tree, untracked files included, and compares the two texts
normalized. A page whose normalized text differs (an added or a deleted page always differs) must be named in `Affected`
by an entry applied on the branch: applied in the working tree's log and not applied on `<base>`, that is neither applied
in the merge-base's log nor held by an earlier commit of `<base>`'s log and trimmed since (below, "Two branches at once").
The file is the grain: an entry naming a rule covers its whole theme file. Each page no such entry names is one line,
with the entries that name it and why they do not count (`1 recorded`, `1 applied on main`), or `no entry names it`.

The normalization strips what the link tools write without a decision, so that `/reconcile-links` keeps working without
an entry: a Markdown link becomes its text, an indented `[E2E: …]` line goes, and the `@hash` of a story's `**Rules.**`
line goes. Everything else is text, a `references` block included. A file that is not Markdown is compared as it is.

What it proves: every change to a protected document on the branch is backed by an applied entry that the pull request
shows, with its context, its decision and its source. It does not prove which agent edited the page or that the edit
matches the decision's words; that is the "decisions carried" review's reading (`omc/terminals/conformance` ›
"2. Decisions carried").

# Pending, trim and check

- `pending`: one line per recorded entry not applied, and per open question of a question file of `paths.questions`
  (below); none means everything recorded is carried through. `pending --questions` gives the open questions alone:
  before implementation the recorded entries wait, on purpose (`# The integrity check`).
- `trim` drops every entry applied on `<base>`: applied at the merge-base, or held by an earlier commit of `<base>`'s
  log and trimmed since; the header, `Next` included, stays, and so does every entry recorded or applied only on the
  branch. An entry is `<base>`'s only when `<base>`'s log holds or held the same id with the same title and `Context`
  (link-free); another decision under the same id is the branch's own (below, "Two branches at once"), which `trim`
  keeps and `guard` counts as applied on the branch.
- `check`: the header holds `Next:`; ids are unique, ascending and below `Next`; no entry holds an id that `<base>`'s log
  gives or gave another decision (`id-on-main`; a `duplicate-id` and an `id-on-main` both name the rebase step below);
  no entry is one `<base>` applied and trimmed since (`trimmed-on-main`: a rebase kept it from the branch's side;
  `renumber` at the rebase's stop, or `trim`, drops it); every entry has `Context`, `Decision` and `Automated` (`true`
  or `false`), no field twice, and a `Status` in one of the two forms. An entry new on the branch or still recorded in
  `HEAD`: every link resolves or reaches a protected document deleted on the branch (a link pinned to a commit, title
  `git:<sha>`, is `links-check`'s) and every `Affected` name resolves. An entry `HEAD` has: recorded there, its title,
  `Context`, `Decision`, `Automated` and `Source` are unchanged, link-free; applied there, its whole link-free text is
  unchanged. An entry `HEAD` has and the working tree lacks must be applied on `<base>`: only a trim removes. An entry
  `renumber` moved is followed to its new id by its title, and compared with its decision references' numbers masked; an
  id `HEAD` holds twice (a rebase's leftover) is left to `renumber`. An entry applied in `HEAD` is never re-resolved,
  since a later branch may delete a page it names.

## Two branches at once

Two branches that start from the same `<base>` and both record take the same `Next`: both hold, say, entry 2. When
the first has merged and the second rebases onto `<base>` (`/design`'s `fresh` or `/audit`'s `rebase` does; the steps
below are `omc/terminals/rebase` › "4. The log after the rebase"), the log conflicts, since both appended at its end.
The rebase step:

1. At every stop of the rebase where the log conflicts, `just decisions resolve`. It settles the log entry by entry
   from git's three sides (the common ancestor, `<base>`'s side as the rebase has built it so far, the commit being
   replayed), never by hand: `<base>`'s header and entries first, then the entries only the commit holds; an entry
   both sides hold is never copied twice, and takes the side that changed it (the commit's when it applied it); an
   entry one side trimmed stays trimmed. It stages the log, and refuses outside a rebase, on a log not in conflict,
   and on an entry both sides changed differently (that one is the owner's question). Ids may stand twice at this
   point. If the log was the stop's only conflict, `git rebase --continue`; any other conflicted file is the
   owner's.
2. Once the rebase is done, `just decisions renumber` (it refuses while a rebase, a merge, a cherry-pick or a revert is
   in progress: every commit of the branch has to be in what it rewrites). It first validates the base: `<base>`'s log has
   unique ids, in order, below its `Next`, and every reference to a decision anywhere on `<base>` (`decision 41`,
   `decisions 12 and 35`, `decisions 38, 41, 42` (a comma list only after the plural: `decision 20, 4 shards` names
   one), a link to an entry's heading) on `<base>`'s lines, as they stand on the branch, names an id `<base>`'s log holds or
   held; a base that does not validate is refused with every bad reference listed, and nothing is renumbered against it
   until it is fixed (on the branch, as any other line, or on `<base>`). The branch's own entries are those `<base>`'s log
   never held as the same decision: not at the merge-base, and not at any earlier commit of `<base>`, the branch's old
   fork point included. They take the ids from `<base>`'s `Next` on, in file order, after `<base>`'s, and `Next` follows
   them; an entry `<base>` held and trimmed since goes (`decision <n> dropped: applied on main and trimmed there`). Every
   reference to an own entry is rewritten to its new id: in the own entries' text, and in every line the branch added
   since the merge-base, in any file (a question file's status, a record, a code comment); a line `<base>` holds is never
   touched, so it keeps naming `<base>`'s decision. A reference the branch wrote names an id its log held when it was
   written, so one naming an own entry's old id means that entry. It refuses a reference the branch wrote that names no
   decision of `<base>`'s and no entry of the branch's, and checks its own result (ids sound, every reference naming what
   it named before) before it writes. It prints `decision <old> is now <new>` per moved entry and
   `<k> entries renumbered`; it refuses a log that still holds conflict markers, and changes nothing when nothing moved.
3. `just decisions check`, then commit the log and every file it changed (`Decisions renumbered after the rebase`).

A log conflict is resolved by this step alone: `resolve` at each stop, then `renumber` once the rebase is done;
never an entry merged, dropped, moved or renumbered by hand. The same predicate holds
when `renumber` was not run: `guard` never counts an entry `<base>` trimmed, `trim` drops it, and `check` reports it
(`trimmed-on-main`). A commit message that names the old id stays as it is; `/audit`'s `rebase` squashes them.

# The question file

One per worktree run: `<paths.questions><date>-<branch-slug>-<n>.md` (`n` counts the runs on the branch), whose first
line is `# Questions: <branch> run <n>`, then one block per question:

```
### Q3 A member's incident without a photo
**Where.** implement, task 4, `app/incidents.py` (`record_incident`)
**Question.** May an incident be recorded without a photo?
**Options.** (1) refused … (2) recorded as a warning row … (3) recorded plainly …
**Picked.** (2): R9.3-2 names a warning for a missing photo on a delivery; nothing names an incident.
**Subagent.** (2), agree.
**Acted on.** yes
**Status.** open
```

`Status` goes `open` → `answered` → `decision <n>` (the entry `/record-decision` wrote). A question acted on whose
ruling is not its `Picked` answer gets one more line, under `Status`, written by `/pose-questions`: what the code and
the tests did, so that the follow-through revisits them (`**Differs.** the incident is recorded as a warning row` under a
ruling of (1)). Only a file whose first line starts `# Questions: ` is a question file; the review files carry no such
line and `pending` does not read them.

# The integrity check

`omc/tools/decisions/integrity.py`, run as `just design-integrity-check [--phase design|implementation]
[--defer-questions]` (default `implementation`; `--docs <dir>` as the tool's), holds the mechanical checks of the
decisions in one command. It calls the tool's own functions over one read of git, and reads the log, the record, git
and the vault's links and nothing else: no build, no test, no gate stage. Every line it prints is
`PROBLEM: <check>: <detail>`, the inner line in its own form without its leading `PROBLEM: ` (`UNBACKED: …`,
`PENDING: …`), in the order of the table; then `OK` or `<k> problems`, and exit 1 on any. A refusal prints
`error: <why>` and exits 2, as the tool's does; so does a missing `origin/<base>` (`git fetch origin`).

| Check | `<check>` | Phase |
|---|---|---|
| the log is sound: `check` | `decisions check` | both |
| no question file holds an open question: `pending --questions` | `questions` | implementation, without `--defer-questions` |
| every entry of the branch has its row in the branch's record | `record` | both |
| the vault's links hold: `just links-check` (a run that did not happen is `did not run: …`, never `OK`) | `links-check` | both |
| every changed protected document is named by an entry applied on the branch: `guard` | `guard` | both |
| nothing recorded is left unapplied: the recorded half of `pending` | `pending` | implementation |

In design the recorded entries wait, on purpose; so do the open questions, in design and with `--defer-questions`
(`/implement`'s `decisions` step): they wait for the push gate, the verify terminal's run of the check (and a `pre-push`
hook, where the project installs one), which pass neither flag, so nothing is pushed with a question open
(`--defer-questions` with `--phase design` is accepted and changes nothing). The guard runs in both phases, so there any
changed protected document is `UNBACKED`. The entries of the branch are those `<base>`'s log never held as the same
decision (an entry `<base>` applied, still in the log before a trim, needs no row). The branch's records are the
`<paths.specs>*-design.md` files added since the merge-base, tracked or untracked; their rows are read together, and a
branch without one passes the `record` check with nothing to compare. A row is a table row inside a section headed, at
any level, "Decisions and the pages they change", outside code fences, whose first cell begins `decision <n>` (a
backtick before it allowed); a later cell (`replaces decision <m>`) never counts. That is the form `renumber` rewrites
in every line the branch added, so a row follows its entry to a new id. Whether an entry reached the pages its row
planned is not checked here: that is the "decisions carried" review's reading.

# The tool

`omc/tools/decisions/decisions.py`, run from the repository root as `just decisions <subcommand> …`
(`just decisions --help`, `just decisions <subcommand> --help`). It parses the whole log on every call and writes it
back whole; there is no other store. `--docs <dir>` before the subcommand points it at another vault, for a dry run on a
copy (outside a git repository, `guard`, `trim` and `check` refuse, and no page counts as deleted). It reads git in one
place only (the merge-base, the log at `HEAD` and at the merge-base, the log at every earlier commit of `<base>` that
changed it, the changed protected documents; for `update` and `remove`, the entry headings every commit of `HEAD`'s
history added to the log); every other function takes texts. A refusal prints `error: <why>` and exits 2, the log
untouched; so does a missing `origin/<base>` (`git fetch origin`).

| Subcommand | Does |
|---|---|
| `add-decision --title T --context C --decision D [--automated] [--affected "a, b"] [--source "<vault path>#<heading>"]` | appends `### <Next>` with `Status recorded <today>`, advances `Next`, prints the id; refuses a missing title, context or decision, a name or source that resolves to nothing, and a header without `Next` |
| `apply-decision --id n --affected "a, b"` | `--affected` required, the real set; `""` is applied with nothing to change (the field dropped); sets `recorded <date> · applied <today>`; refuses an unknown id and an entry already applied |
| `update n [--title T] [--context C] [--decision D] [--automated true\|false] [--affected "a, b"] [--source "…"]` | rewrites the fields given of an entry no commit ever held, as `add-decision` writes them (`--affected ""` and `--source ""` drop the field); the rest and the `Status` stay; refuses an entry a commit of `HEAD`'s history ever held, by its id or its title |
| `remove n` | drops an entry no commit ever held and lowers `Next` to what the remaining entries and `HEAD`'s log allow, never below `HEAD`'s `Next`; refuses an entry ever committed and one any file still names (`decision n`, a link to its heading) outside the entry itself |
| `show n [n…]` | the entries in full |
| `list` | every entry, one line each: `n  status  Automated: true\|false  title` |
| `pending [--questions]` | `OK`, or one `PENDING:` line per recorded entry and per open question (`--questions`: the open questions alone), exit 1 |
| `guard` | `OK`, or one `UNBACKED:` line per changed protected document no entry applied on the branch names, exit 1 |
| `trim` | drops the entries applied at the merge-base; prints `<k> entries trimmed` |
| `resolve` | at a rebase's stop where the log conflicts: settles it entry by entry from git's three sides (`<base>`'s entries, then the commit's own; never one twice) and stages it ("Two branches at once"); prints `decision <n> dropped: …` per trim kept and `resolved: …`; refuses outside a rebase and on an entry both sides changed |
| `renumber` | after a rebase's log conflict, resolved to `<base>`'s entries and the branch's: the branch's own entries take the ids from `<base>`'s `Next` on, an entry `<base>` trimmed goes, and every reference to them the branch wrote follows, after the rebase and against a base that validates ("Two branches at once"); prints `decision <n> dropped: …` per entry dropped, `decision <old> is now <new>` per moved entry and `<k> entries renumbered` |
| `check` | `OK`, or `PROBLEM: <the log's path in the vault>:<line>: <kind>: <detail>` lines, exit 1; the kinds `header`, `duplicate-id`, `id-on-main`, `trimmed-on-main`, `out-of-order`, `id-not-below-next`, `malformed-entry`, `malformed-status`, `dead-link`, `unknown-name`, `edited`, `removed` |

`check`, `guard` and `pending` run in `just design-integrity-check` (# The integrity check), which the verify terminal
(`/verify`) runs after each full run of the gate, and a `pre-push` hook may run before a push; never in the check gate.
