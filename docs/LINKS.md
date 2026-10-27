# Links in this folder

Every reference in `docs/` is a link, so a reader and a tool both see every edge between the documents.
`just links-check` checks all of it on every `just build`; `/reconcile-links` fixes what it reports. What `docs/`
holds, and which of its files are corpus, history or generated, is declared in `tools/corpus.yaml`.

## Form

- A standard relative Markdown link: `[02 §2.6](design/02-repos-and-config.md#2.6%20Trust)`, written relative to
  the file it stands in. From inside `design/`: `[02 §2.6](02-repos-and-config.md#2.6%20Trust)`.
- A heading, by its exact text with every space as `%20`, every backtick as `%60`, every other character as it is:
  `[03 §3.8](design/03-watch.md#3.8%20%60/tmp%60%20retention)`. In the same file: `[§3.8](#3.8%20%60/tmp%60%20retention)`.
  A raw backtick would open a code span in CommonMark and break the link.
- Never a wikilink, a reference-style link, an angle-bracket destination, a GitHub slug, an absolute path, or a
  scheme other than `https:`, `http:` and `mailto:`.
- No link leaves `docs/`. A path outside the folder is written as text in a code span: `tools/corpus.yaml`.
- `docs/` holds Markdown and the images its pages embed; nothing else. Any other file, or an image no page embeds,
  is `stray`.

## A reference is a link

Any mention of a design document, a section, a ruling, a review item or an E2E definition is written as a link to it.
There are no reference kinds: the checker knows nothing about what a target is, only whether it exists. A link to a
file resolves when the file exists (`dead-file` otherwise); a link with an anchor resolves when that heading exists in
that file (`dead-heading` otherwise).

Plain text stays plain in every heading (a link would change the heading's text, and so every anchor to it), in code
spans and code blocks, in HTML comments, in the text of a link and in URLs.

## The link text names its target

The text of a link says what it points at (`wrong-target` otherwise):

- A heading starts with an id token when it starts with a number (`## 2.6 Trust`, `### 1.2 Title`), or with one or
  two capitals and digits followed by a period (`## H. Parked topics`, `### B1. …`, `### L4. …`).
- When the text holds an id token standing alone, a number such as `2.6` in `02 §2.6` or `1.2` in `ruling 1.2`
  (`v2.1` holds none; a sentence-ending period may follow, as in `decision 1.2.`), and the target heading starts with
  an id token, one of the text's tokens is that heading's leading token: `2.6` for `## 2.6 Trust`, `1.2` for
  `### 1.2 Title`. For a heading led by letters, a capital word of the text is a token too: `H`, `§H` or `L4`, as in
  `[open-questions §H](design/open-questions.md#H.%20Parked%20topics%20(not%20yet%20formulated%20as%20questions))`;
  elsewhere only a capital word after `§` is one.
- Otherwise the text contains the target heading's text, ignoring case; for a link without an anchor, the file's
  first heading or its file name without `.md`: `[09-run-jobs.md](design/09-run-jobs.md)`,
  `[README §MVP](design/README.md#MVP)`.
- Links into `reviews/` are exempt: their text names a review item in its own words.

## Rulings are the one id shape the checker knows

Rulings are the log's own headings: `N.k` is a ruling (`### N.k <title>`), `§N` a section of the log (`## N. <title>`).
A bare `N.k` that is a ruling of the log, written after the words "ruling", "rulings" or "decision log", or inside a
parenthesis that holds only references, is `unlinked` and fails. Any other bare `N.k` that is a ruling of the log is an
`unlinked?` warning, and a reader decides; outside the log, such a number that is also one of the file's own
heading numbers is not counted, inside a parenthesis too; after "ruling", "rulings" or "decision log" it still
is. No other bare token is checked.

## Links into the log

A link into `decision-log.md` lands on a `### N.k` entry that is applied (its `**Status.**` line says `applied`). A
link to a recorded entry, a note or a section heading is `unapplied-target`. Inside the log itself a link may target any
decision entry, recorded or applied, and a `**Supersedes.**` link a section heading too; no link targets a note. The entries themselves are
written only by `just decisions`.

## The log and the reviews are history: their links are pinned

The decision log and every file under `reviews/` (review files, `iterations/`, `raw-feedback/`) are history: what
they linked may be gone later. So in these files every link into the folder is either

- **pinned**: the link carries the title `"git:<sha>"`, 12 hex characters of a commit on `main` (`origin/main`, or
  the local `main` when there is no origin): `[02 §2.6](design/02-repos-and-config.md#2.6%20Trust "git:0123456789ab")`.
  Its target, the file and the heading when the link has an anchor, must exist at that commit (`pin` when the commit
  is not on `main`, `dead-pin` when the target is not there); whether it still exists today does not matter. In a
  repository without a `main` branch every pinned link reports `pin`. Or
- **unpinned**: allowed only while the link's line comes from the current branch (its `git blame` commit is not on
  `main`, or the line is uncommitted); it then resolves now like any link. An unpinned link on a line from `main` is
  `unpinned` and fails: run `just pin-links`, which adds the titles and leaves the link-free text unchanged, then
  commit. The pre-push hook (`just install-hooks`) refuses a push with an `unpinned` link.

A link to the file's own heading and an external link need no pin. Everywhere else in the folder nothing is pinned:
a link must resolve now.

## Generated files

A file `tools/corpus.yaml` lists under `generated` reports its link problems as warnings: the freshness chain
(`just ensure-up-to-date`, the pre-push hook) refuses it when it is stale, and its regeneration rewrites it. No file
is generated today. A file matching `exclude` (`superpowers/**`) is not checked at all.

## Links are invisible to programs

A link reads as its text to anything that extracts or compares references: `[02 §2.6](…)` reads as `02 §2.6`, so
adding a link never changes what a document says.

## Output

`just links-check` prints `PROBLEM: <file>:<line>: <kind>: <detail>` lines, then `WARNING: … unlinked?` lines, then
`OK` or `<n> problems`. The kinds: `escape`, `form`, `dead-file`, `dead-heading`, `wrong-target`, `unlinked`,
`unapplied-target`, `unpinned`, `pin`, `dead-pin`, `stray`.
