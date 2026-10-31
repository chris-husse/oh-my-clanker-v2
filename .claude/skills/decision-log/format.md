# The log

`docs/decision-log.md` (the root and the log's name come from `tools/corpus.yaml`) is a title, a line of preamble,
and numbered sections, each holding entries. It is append-only and written only by the tool, `just decisions`;
nobody edits it by hand, and the tool rejects any call that would break the rules below, leaving the log untouched.

## The section

```
## N. <title> (<date>[, refined <date>])

<optional description, 2 to 3 sentences>
Review file (open): docs/reviews/<file>.md
```

- `new-section` opens section `N+1` at the end of the log with today's date. The open section is always the last
  `## N.`; every new entry goes there.
- A review section names its review file, repository-relative. While its cycle runs the line reads
  `Review file (open): docs/reviews/<file>.md`, which no "decided" check matches, so the cycle's commits never make
  the review look decided.
- `close-section` turns it into the contract line `Review file: docs/reviews/<file>.md`, writes
  `Iterations: <n>` below it, and sets the heading's dates to `(<first date>, refined <today>)` (just `(<date>)` when
  closed the day it opened). A review file is decided when the committed log carries its `Review file:` line.

## The entry

```
### N.k <Title>

**Context.** <the problem and the question, cleaned up; a link for every reference>
**Decision.** <what now holds; a link for every reference>
**Automated.** true | false
**Affected.** [<text>](<link>), [<text>](<link>)
**Supersedes.** [N.j](#N.j%20<title>), [§M](#M.%20<title>%20(<date>))
**Source.** [<item heading>](reviews/<file>.md#<item%20heading>)
**Status.** recorded YYYY-MM-DD[ · applied YYYY-MM-DD[, nothing to change]]
Answers: <ids>
```

Fields stand in this order, one line each; a field with nothing in it is not written.

- **Context** and **Decision** are required. Context is why: what was wrong, what was asked. Decision is what now
  holds, in one to three sentences. Once recorded they never change: a wrong decision gets a successor that names it
  in `Supersedes`.
- **Affected** holds links to what the decision changes: a heading of a corpus file, or a whole file. It is a best
  guess at recording (an empty set is fine) and is replaced by the set actually touched when the decision is
  applied, because the full impact is known only then. The tool writes the link text: the heading's leading id
  token (`2.6` for `2.6 Trust`), else the heading, else the file's stem.
- **Supersedes** holds pointers to earlier rulings the decision may have changed, nearly always in part: an entry
  `N.k` or a section of the log `§N`. They are leads for reading, not verdicts (`/how-we-got-here` reads both
  rulings and says what changed). It is the only field that may link a log section.
  An automated decision may supersede only automated decisions that no non-automated entry has
  superseded; never a human or legacy decision or a log section. Callers must also check semantic
  conflicts: omitting a pointer does not make a contradiction acceptable. Human successors may
  supersede anything while preserving the old ruling's provenance.
- **Automated** is provenance, separate from Status: exactly `true` for a ruling the owner only
  acknowledged (a bulk-accepted proposal, or a presented option picked with "ok"), `false` for a
  ruling the owner stated, changed or reasoned in their own words. New decisions always carry it;
  `add-decision --automated` writes true and ordinary recording writes false. It is immutable,
  including on recorded entries, and application preserves it. Notes never carry it. Older entries
  without the field remain valid and are displayed as `unspecified`; do not rewrite them or treat
  absence as proof of human authorship. A legacy automatic-attribution sentence is evidence of
  automation; read the source before attributing other legacy decisions to the owner.
  When a committed baseline is available, integrity checking requires provenance on decisions
  added since that baseline. With no baseline, missing fields cannot be distinguished from legacy.
- **Source** links the item the decision came from: the heading of an item in a review file, never the file alone.
  Optional.
- **Status** has exactly four forms:
  - `recorded <date>`: recorded, not yet applied;
  - `recorded <date> · applied <date>`: applied;
  - `recorded <date> · applied <date>, nothing to change`: applied with no document changed;
  - `note`: a note (below).
- `Answers:` is a bare line, never bold, so `^Answers:` matches it: the review item ids, iteration finding ids or
  quoted phrases the decision answers.

**Notes.** A review cycle closes with entries that are not decisions (`Settled by earlier rulings`, `Declared
minor`). A note is a `### N.k <Title>` heading, one line of text and `**Status.** note`, nothing else. A note is
never applied and never linked to.

**Ids.** A new entry takes `k + 1` in the open section. Ids are unique and ascending, and each entry sits under its
own section `N`. `N.k` is the one id shape `docs/LINKS.md` knows as a ruling, `§N` a section of the log.

## Rules

- Append-only: the tool appends sections and entries; it changes an existing entry only to apply it (Affected and
  Status) and a section only to close it. An applied entry's or a note's link-free text never changes again.
- A bulk-accepted automated ruling is recorded and applied on the owner's bulk accept, but it is
  never a human ruling: it carries less weight and never overrules a human or legacy ruling.
- Every field value is one line. Free text (a title, Context, Decision, a note's text, a description) must not start
  like a line of the log's structure: a heading, a fence, a bold `**Label.**`, `Review file`, `Iterations:` or
  `Answers:`.
- Every link in a new or still-recorded entry must resolve, or the call is rejected and the log untouched. The links
  of applied entries and notes age as the documents move on; they are the link checker's (`just links-check`).
- Links in the log are relative to the log, which sits at the docs root; a link to another entry of the log is a
  `#<heading>` anchor. Links into the log target only applied decisions; a link to a recorded entry, a note or a
  section heading is the link checker's `unapplied-target` (a log section only from `Supersedes`).
- The tool writes no pins. A link on a line that came from `main` is pinned with `just pin-links` (`docs/LINKS.md`);
  the tool reads a pinned link like any other.

## Links

- **Written by the tool** (`--affected`, `--supersedes`, `--source`, and `history`/`search` targets): a link argument
  is `<docs-relative path>[#<heading text>]`, the heading raw, as it stands after the `#`s:
  `design/02-repos-and-config.md#2.6 Trust`, `reviews/<file>.md#R7. <item heading>`. `N.k` names an entry of the
  log, `§N` a section. The tool encodes the anchor and checks that the file and the heading exist.
- **Written by the caller** (inside `--context`, `--decision`, a note's `--text`): every reference is a standard
  Markdown link relative to the docs root, its anchor encoded as `docs/LINKS.md` says: the exact heading text with
  every space `%20`, every backtick `%60`, everything else raw:
  `[2.6](design/02-repos-and-config.md#2.6%20Trust)`, `[1.2](#1.2%20<title>)`. The tool never infers a link from the
  text; it checks the links it is given.
- **Links are invisible to programs**: the link-free text of an entry is its text with every link replaced by its
  link text (`just decisions body <id>`).

# The tool

`tools/design/decisions.py`, run from the repository root as `just decisions <subcommand> …`. It parses the whole
log on every call and writes it back whole; there is no other store. `--docs <dir>` before the subcommand points it
at a copy of the docs folder, for a dry run: `just decisions --docs /tmp/<copy> add-decision …`. A hidden `--today`
exists for migrations only; no skill passes it.

| Subcommand | Does |
|---|---|
| `show <id>…` | prints the entries in full |
| `list [--section N]` | one line per decision: `N.k  <status>  Automated: true\|false\|unspecified  <title>`; notes omit provenance |
| `search [--affected <path-prefix>[#heading]] [--source <path-prefix>[#heading]] [--supersedes <id>] [--status recorded\|applied\|note] [--section N] [--since YYYY-MM-DD] [--text <regex>] [--oneline\|--ids]` | the entries matching every given filter, in file order, in full unless `--oneline` or `--ids`. `--affected` and `--source` match a link target by docs-relative path prefix (`design/02`), or exactly with `#heading`; a prefix nothing in the folder starts with is an error. `--supersedes` takes `N.k` or `§N`. `--since` compares the recorded date (a note: its section's date). `--text` is a regex over the link-free text |
| `history <path[#heading]>` | every entry whose Affected or Supersedes links hit that target (a file names every heading in it; an entry id `N.k` also names the entry itself; `§N` a log section), oldest first, each followed by `later: <ids>` when later entries name it in `Supersedes`, and those later entries themselves, through any chain |
| `check` | the integrity check below; prints its problems, then `<n> problems`, and exits 1; prints `OK` when the log is sound |
| `new-section --title t [--description d] [--review-file docs/reviews/<file>.md]` | opens section N+1 and prints `N+1`; the review file is repository-relative and must exist |
| `add-decision --title t --context c --decision d [--automated] [--affected link…] [--supersedes id…] [--source link] [--answers ids]` | appends an entry to the open section, status `recorded <today>`, and prints its id; with `--automated`, every `--supersedes` target must be an automated decision no non-automated entry supersedes |
| `add-note --title t --text t` | appends a note to the open section and prints its id |
| `set-provenance <id> --automated true\|false` | corrects the Automated field of a recorded decision that is not yet committed; refuses a committed entry, a note, an unchanged value, or `true` on an entry that supersedes a non-automated ruling |
| `apply-decision --id N.k (--affected link… \| --no-change)` | only on a recorded decision: replaces Affected with the set given and sets `applied <today>`; `--no-change` drops Affected and writes `applied <today>, nothing to change` |
| `close-section --section N --iterations n` | closes (or recloses) a review section as above; only `/review-design` uses it |
| `body <id>` | the entry's link-free text without its heading line: the body of a commit message |

`--affected` and `--supersedes` take several values (`--affected a b`, or the flag repeated).
`search --automated true|false|unspecified` combines with other filters and matches only decisions
with that provenance. `unspecified` means the field is absent, not human or automated; notes are
excluded. Without the filter, search behavior is unchanged.

## `check`

Prints `PROBLEM: <file>:<line>: <kind>: <detail>` lines, one per problem. The kinds:

| Kind | When |
|---|---|
| `unresolved-section` | a section's `Review file (open):` line names a file that does not exist |
| `duplicate-id` | an id appears twice |
| `out-of-order` | ids do not ascend |
| `wrong-section` | an entry `N.k` sits under a section other than `N` |
| `malformed-status` | a `Status` line is missing or not one of the four forms |
| `malformed-entry` | a decision lacks Context or Decision, a note carries a field, an entry has an unknown bold field, Automated is invalid or repeated, or an automated ruling supersedes a non-automated entry or a log section |
| `dead-link` | a link of a recorded entry, or of an entry new since `HEAD`, does not resolve (no such file or heading, leaves the folder, a note, a log section outside `Supersedes`) |
| `removed` | an entry applied or a note in `HEAD` is gone from the working tree |
| `edited` | an entry applied or a note in `HEAD` has a different link-free text in the working tree, or any existing entry's Automated provenance differs from `HEAD` |

`just decisions check` runs in `just build`.
