# Reference for the design folder plan: the source tools, described for the port

Companion to `2026-10-27-design-folder.md`. The source is `/home/openclaw/Projects/apuntalo.co` at commit
`467e9e9`. Every `file:line` below is relative to the tool named in its heading. The port drops everything the spec
(`../specs/2026-10-27-design-folder-design.md`, section 2) removes; where this reference describes a removed feature
it says so.

## A. The decision log tool (Python): `.claude/skills/decision-log/tool/decisions.py`

Single file, 856 lines, standard library only. Read it directly; it is the model for `log.py` and `decisions.py`.
Its functions, in order (line numbers of the source):

- 47 `RefError(Exception)`: an unresolvable reference; every writing command catches it and leaves the log
  untouched.
- 52 `Target(file, heading)`, 58 `Link(start, end, text_start, text_end, dest, title; pin; markdown)`, 76
  `Heading(line, level, text)`.
- 82 `encode_anchor(heading)`: space to `%20`, backtick to `%60`. 87 `decode_anchor(fragment)`.
- 94 `scan_links(text)`: inline links with balanced parentheses in the destination and an optional quoted title.
  136 `unlink(text)`: every link becomes its text. 147 `sentence_around(text, link)`. 157 `mask_code(text)`: code
  spans and fences blanked, length kept. 162 `headings_of(text)`.
- 180 `Vault(docs_dir)`: walks every `.md` under the folder, builds the reference indexes (**removed**: the port
  keeps only the log's own ruling index), `text(rel)`, `headings(rel)`, `is_file(rel)`, `link_to(text, target)`,
  `resolve(kind, ref)` (**removed**, replaced by resolving a link), `target_of(dest)`, `kind_of(target)`
  (**removed**).
- 299 `Entry`: `kind()` (legacy, note, decision), `status()`, `date()`, `text()`, `links()`, `prose()`,
  `affected(label)`, `prose_affected(label)` (**removed**: legacy prose affected).
- 381 `Section`, 391 `Log`, 397 `parse_log(text)` with `close_entry()` and `trim_header()`.
- 448 `entry_matches`, 460 `search(vault, log, story=, screen=, document=, source=, supersedes=, status=, section=,
  since=, text=)` (the three kinds become one `affected=`), 493 `direct_later`, 501 `later_chain`, 514 `history`,
  534 `format_oneline`, 538 `format_history`.
- 548 `check(vault, log, head_text=None)` with the kinds `duplicate-id`, `out-of-order`, `wrong-section`,
  `malformed-entry`, `malformed-status`, `dead-link`, `edited`, `removed`.
- 601 `link_mentions(vault, text)` (**removed**: auto-linking).
- 620 `render_entry(entry_id, title, fields, answers=None)`, 631 `write_log(vault, lines)`, 640 `_append`, 647
  `_today`, 651 `_clean`, 657 `new_section`, 671 `_next_id`, 678 `_links`, 682 `add_decision`, 699 `add_note`, 705
  `_replace_entry`, 712 `apply_decision`, 731 `close_section`, 749 `head_log_text` (`git show HEAD:docs/decision-log.md`),
  758 `_split`, 762 `repo_root`, 766 `main` (argparse; subcommands at 772-810).

Its tests, `test_decisions.py` (62 tests, 697 lines): read them for the fixtures. Port every test that does not
exercise a removed feature (legacy, backfill, kinds, mentions). The test names that survive, as a checklist:
`scan_links_handles_parentheses_in_the_anchor`, `a_link_with_a_title_is_one_link_and_unlinks_without_it`,
`anchor_encoding`, `mask_code_keeps_length`, `no_link_leaves_the_vault` (renamed: folder), `target_of_a_destination`,
`sections`, `entries`, `body_excludes_the_next_heading_and_trailing_blanks`, `kind_status_date`,
`search_and_history_read_the_fields`, `check_accepts_the_fields_and_refuses_context_decision_or_fields_without_status`,
`search_by_field`, `search_rejects_an_unknown_reference`, `history_follows_supersession`,
`history_annotates_direct_superseders_only`, `a_section_of_the_log_is_a_supersedes_target`,
`check_is_green_on_the_fixture`, `check_reports`, `oneline`, `show_search_history_check`, `new_section`,
`add_decision`, `add_decision_without_optional_fields`, `add_decision_refuses_and_leaves_the_log_untouched`,
`add_decision_refuses_without_a_section`, `add_note`, `cli_add_decision_prints_the_id`,
`apply_replaces_the_affected_set_and_marks_applied`, `apply_with_nothing_to_change`, `apply_refuses`,
`close_section`, `check_immutability_against_head`, `check_uses_head`,
`check_leaves_aged_links_of_committed_applied_entries_to_links_check`, `check_leaves_the_committed_log_byte_identical`.

The regexes the port keeps (source lines 22-45), verbatim:

```python
SECTION_RE = re.compile(r'^## (\d+)\. (.*?) \(([^)]*)\)\s*$')
ENTRY_RE = re.compile(r'^### (\d+)\.(\d+) (.+?)\s*$')
HEADING_RE = re.compile(r'^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$')
FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
FIELD_RE = re.compile(r'^\*\*(Context|Decision|Affected|Supersedes|Source|Status)\.\*\* ?(.*)$')
ANSWERS_RE = re.compile(r'^Answers: (.*)$')
STATUS_RE = re.compile(r'^(?:note|recorded (\d{4}-\d\d-\d\d)(?: · applied (\d{4}-\d\d-\d\d)(, nothing to change)?)?)$')
DATE_RE = re.compile(r'\d{4}-\d\d-\d\d')
RULING_HEADING_RE = re.compile(r'^(\d+\.\d+)[ .]')
RULING_ID_RE = re.compile(r'^\d{1,3}\.\d{1,3}$')
LOG_SECTION_ID_RE = re.compile(r'^§\d{1,3}$')
LOG_SECTION_HEADING_RE = re.compile(r'^(\d+)\. ')
PIN_RE = re.compile(r'^git:([0-9a-f]{7,40})$')
```

The entry the tool writes (source `format.md:6-18`, adapted to one Affected field):

```
### 1.2 Trust: index-only by default, trusted repos and mirrors

**Context.** …
**Decision.** …
**Affected.** [2.6](design/02-repos-and-config.md#2.6%20Trust), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules)
**Supersedes.** [1.1](#1.1%20MVP%20scope%20of%20multi-repo%20work)
**Source.** [R2. [blocker] The agent can run the user-only gates: trust, trust --all, reset-rounds, configure](reviews/2026-10-16-adversarial-design-review.md#R2.%20%5Bblocker%5D%20The%20agent%20can%20run%20the%20user-only%20gates:%20trust,%20trust%20--all,%20reset-rounds,%20configure)
**Status.** recorded 2026-10-27 · applied 2026-10-27
Answers: R2
```

Note on the Source link above: the anchor encoding writes only space and backtick; `[` and `]` stay raw, so the
real anchor is `#R2.%20[blocker]%20The%20agent…`. The example shows the rule; the tool produces the real form.

## B. The link checker and pinning tool (Dart): `.claude/skills/reconcile-links/tool/`

Package `docs_links`, 1,948 lines: `bin/links_check.dart`, `bin/pin_links.dart`, `lib/src/{vault,text,scan,
references,log,check,history,pin,unlink,repo}.dart`, tests `test/{check_test,pin_test,unlink_test}.dart`.

### B.1 repo.dart
- `repoRoot()` (5-13): walk up from the working directory to the first directory containing `.git` (a directory
  or a file, for a worktree). Throws `no .git above <cwd>`.

### B.2 vault.dart: the folder walk (port as `Folder`)
- `Vault.git(root)` (12-18): `git -C <root> ls-files --cached --others --exclude-standard -z .`; split on NUL,
  drop empty entries and paths that do not exist on disk; sort. Root absolute and normalized; paths posix and
  relative to the root. Non-zero exit: `git ls-files in <root>: <stderr>`.
- `Vault.dir(root)` (21-27): every file under the root, recursively, sorted (tests).
- `markdown` (35): files ending in `.md`. `text(rel)` (36): read, `\r\n` to `\n`, cached. `headings(rel)` (37):
  `headingsOf(text)`, cached.
- `slugs(rel)` (40-50): GitHub slug to heading text; duplicates `base`, `base-1`, …; first wins.
- `isFile(rel)`, `isDir(rel)` (52-53): the filesystem, not the git list.

### B.3 text.dart: masking, headings, anchors
- `blank(s)` (6): every character except `\n` becomes a space, so offsets and line numbers stay.
- Fence regex (8): `^\s*(`{3,}|~{3,})`.
- `mask(text)` (11-29): (1) fences line by line: outside a fence a matching line opens one and is blanked; inside,
  every line is blanked; the fence closes on a line whose run has the same first character, is at least as long as
  the opener, and `line.trim() == run`; unclosed runs to the end. (2) HTML comments `<!--[\s\S]*?-->` blanked, may
  span lines. (3) code spans (33-63): on a run of n backticks, search the rest for `(?<!`)`{n}(?!`)`; if found,
  blank from the opening run through the closing run (spans may cross newlines); otherwise literal. On `](`, call
  `destinationAt(s, i+2)` and copy the whole destination unmasked (a backtick inside an anchor never opens a span);
  if null, copy only `]`.
- `decodePercent(s)` (65-90): for each run `(?:%[0-9A-Fa-f]{2})+`: turn into bytes; the lead byte decides the
  length (`<0x80` 1; `0xC2..0xDF` 2; `0xE0..0xEF` 3; `0xF0..0xF4` 4; else 0); if n > 0 and enough bytes remain,
  strict UTF-8 decode of those n bytes; on success emit the character and advance n; otherwise emit that byte's
  `%XX` as written and advance 1. Raw characters untouched. `%65` decodes to `e`.
- `Heading(line, level, text)` (92-97): line 1-based, text raw. Heading regex (99):
  `^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$`. `headingsOf(text)` (102-120): same fence logic, fenced content skipped;
  non-empty group 2 becomes a heading; closing `#`s not stripped; no setext; comments not skipped.
- `encodeAnchor(heading)` (125): `replaceAll(' ', '%20').replaceAll('`', '%60')`; everything else raw.
- `githubSlug(heading)` (128-132): lowercase; remove `[^\p{L}\p{N}\s_-]`; trim; each single space to `-` (spaces
  not collapsed: `W16 — A` gives `w16--a`). Python: `[^\w\s-]` with `re.UNICODE` is close enough; it only feeds
  the `GitHub slug` form hint.

### B.4 scan.dart: links
- `MdLink` (2-13): `start`, `end` (whole link, including `!` of an image), `textStart`, `textEnd` (inside the
  brackets), `dest` (as written, without `<>`), `image`, `angle`, `title` (without quotes, or null);
  `pin` = `^git:([0-9a-f]{7,40})$` group 1 of the title.
- `scanLinks(masked)` (18-50): find the next `[`, `i = open+1`; skip if preceded by `\`; if the next char is `[`
  (wikilink) `i = open+2`, continue; match brackets on the same line by depth (a newline aborts; escapes ignored);
  the close must be followed by `(`; then `destinationAt(s, close+2)`; image if `s[open-1]=='!'`, then
  `start = open-1`; after a link `i = d.end` (nested links never found); no link: restart at `open+1`.
- `destinationAt(s, k)` (54-79) returns `(dest, end, angle, title)` or null. Angle form (`s[k]=='<'`): find `>`
  (null if none or a `\n` before it); `end = indexOf(')', gt)` (null if none); dest `s[k+1:gt]`, `end+1`, angle
  true, title `_title(s[gt+1:end])`. Plain form: scan from k, stop at `\n`, space, tab, or `)` at depth 0 (`(`
  adds depth, `)` above 0 subtracts); reaching the end or `\n` is null; at `)` return `(dest, m+1, false, null)`;
  at a space or tab, `end = indexOf(')', m)`, null if none or a `\n` between; title `_title(s[m:end])`. `[x]()` is
  allowed.
- `_title(between)` (82-86): trim; strip matching `"…"` or `'…'` if length ≥ 2; else the trimmed text or null.

### B.5 unlink.dart
- `unlink(text)` (5-17): every non-image link from `scanLinks(mask(text))` becomes the raw text between its
  brackets (backticks kept); the title goes with the link; images and links in code stay.

### B.6 references.dart (**removed**, except what is noted)
Everything here is reference-kind machinery: the story/scene/section/node indexes, `lookup`, `Mention`,
`mentionsIn` and its regexes. The port keeps:
- `Target(file, heading)` (8-16) and `linkTo(from, t)` (19-23): same file with a heading gives
  `#<encodeAnchor(heading)>`; otherwise `posix.relative(t.file, from: dirname(from))` plus `#anchor` when a heading.
- The ruling index: in the log, a heading of level 2 or more matching `^(\d+\.\d+)[ .]` gives `rulings[N.k]`.
- The `unlinked?` heuristic for rulings only (88-98, 132-189):
  - `_numRe = (?<![\w.])(?<!(?<!\w)0\d §)\d{1,2}\.\d{1,3}(?![\w]|\.\d)` (the port widens to `\d{1,3}\.\d{1,3}`
    and drops the inner `0\d §` lookbehind, which belonged to design-section references);
  - `_keyedRe = (?:[Dd]ecision[ -]log|[Rr]ulings?)((?:(?:\s*,\s*|\s+and\s+|\s+)§?\d{1,2}\.\d{1,3}(?![\w]|\.\d))+)`;
  - `_parenRe = \(([^()\n]*)\)`; `_urlRe = \bhttps?://\S+`;
  - `prose(v, f)` (102-129): `mask(text)` with heading lines, every link and image span, wikilinks, reference-style
    links, reference definitions and URLs blanked; in the log only, every line starting with `Answers: ` blanked;
  - keyed offsets: for each `_keyedRe` match, `g = m.start + len(m[0]) - len(m[1])`; every `_numRe` match on the
    substring `m[1]` adds `g + n.start`;
  - grouped offsets: for each `_parenRe` match, split the inner text on `,|;|\band\b`, trim, drop empty; a token
    is named when it is a ruling id or `§` plus one; if at least one token and every token is named, every `_numRe`
    match in the inner text adds `m.start + 1 + n.start`;
  - for every `_numRe` match in the prose whose ruling exists: keyed is certain; else if the file is not the log
    and the number is one of the file's own heading numbers, skipped; else certain if grouped, otherwise uncertain
    (the `unlinked?` warning);
  - overlap removal: sort by start ascending then end descending, keep a mention only if `start >= last.end`.
  - Compile with `re.ASCII` (Dart's `\w` and `\b` are ASCII). Run sub-regexes on substrings so lookbehinds see
    the string start.

### B.7 log.dart (the log as the checker sees it)
- `LogEntry(id, heading, line, status)`. `_entryRe = ^(\d+\.\d+) `; `_statusRe = ^\*\*Status\.\*\* ?(.*)$`;
  `_statusForm` as in A without `legacy`.
- `logEntriesByHeading(text)` (16-35): level-3 headings matching `_entryRe`; the entry's lines run to the next
  entry heading, stopping early at a line starting with `## `; the first Status line decides: `malformed` if it
  fails `_statusForm`, else `note` as written, else `applied` if it contains `applied`, else `recorded`. With no
  Status line: `malformed` in the port (the source said `legacy`). The port imports `log.py` instead of
  re-parsing.

### B.8 check.dart: the problems
- `Problem(file, line, kind, detail, warning=false)`; output `'${warning ? 'WARNING' : 'PROBLEM'}: $file:$line: $kind: $detail'`;
  sort key `(warning, file, line, kind)`.
- Regexes (30-34): `_schemeRe = ^[a-zA-Z][a-zA-Z0-9+.-]*:`; `_externalRe = ^(https?|mailto):` (case-insensitive);
  `_wikiRe = \[\[[^\]\n]+\]\]`; `_refUseRe = \[[^\[\]\n]+\]\[[^\[\]\n]*\]`; `_refDefRe = ^ {0,3}\[[^\]\n]+\]:[ \t]*\S`
  (multiline).
- `isPinnedFile(f)` (39): the log or `reviews/` (the port reads `history` from `corpus.yaml`).
- `checkVault(v, label='docs', git)` (44-192), per markdown file `f`: `raw = v.text(f)`, `masked = mask(raw)`,
  `lineOf(off)` by binary search over line starts, 1-based. Generated files (66-72, the port reads `generated`
  from `corpus.yaml`): every problem added through `add()` becomes a warning with ` (generated)` appended.
  Problems are `Problem('$label/$f', line, kind, detail)`.
- Kinds in check order:
  1. `form`: wikilink, detail `wikilink <m>; write a relative Markdown link`.
  2. `form`: reference use, `reference-style link <m>; write an inline link`.
  3. `form`: reference definition, `reference definition; write inline links`.
  4. Per link, `dest = l.dest`:
     - angle: `form`, `angle-bracket destination <dest>; write each space as %20`; nothing more checked;
     - scheme matches and not external: `form`, `scheme not allowed: <dest>`; external links skipped silently;
     - starts with `/`: `form`, `absolute path: <dest>`;
     - resolve: `path` before the first `#`, `frag` after (or null); target is `f` when the path is empty, else
       `normalize(join(dirname(f), decodePercent(path)))`;
     - `escape`: target is `..` or starts with `../`; `link leaves <label>/: <dest>`;
     - history-file branch (only with git, a history file, a non-empty path): unpinned link: `commit =
       git.commitOf(f, line)`; if not null and `onMain(commit)`: `unpinned`, `<dest>: run just pin-links`, stop;
       else fall through. Pinned link: `heading = decodePercent(frag)` when frag non-empty and target is `.md`;
       chain: `!onMain(pin)` gives `pin`, `git:<pin> is not a commit on main: <dest>`; else
       `!existedAt(pin, target, null)` gives `dead-pin`, `no such file at git:<pin>: <dest>`; else heading set and
       `!existedAt(pin, target, heading)` gives `dead-pin`, `no heading "<heading>" in <target> at git:<pin>`; else
       heading set and `frag != encodeAnchor(heading)` gives `form`, `anchor not in the written form: #<frag>;
       write #<encoded>`. After the chain: if the target is missing today, or the heading is missing today, stop
       (gone today is fine); otherwise record `embedded` for an image, run `checkToday`, stop;
     - `dead-file`: `!isFile(target)`; detail `a folder, not a file: <dest>` or `no such file: <dest>`;
     - image: target joins `embedded`;
     - anchors (frag non-empty, target `.md`): `asText = decodePercent(frag)`; if it equals a heading's text:
       heading = asText, and if `frag != encodeAnchor(asText)`: `form`, `anchor not in the written form: #<frag>;
       write #<encoded>`; else if `slugs(target)[frag]` exists: `form`, `GitHub slug #<frag>; write
       #<encodeAnchor(slug heading)>`, stop; else `dead-heading`, `no heading "<asText>" in <target>`, stop;
     - `checkToday(l, target, heading, frag)`.
  5. `checkToday` (76-93): `unapplied-target` when the target is the log, `f` is not the log, and frag is non-empty:
     no entry at that heading gives `links a heading of the log that is not a decision entry: #<frag>`; status not
     `applied` gives `<id> is <status>; only an applied entry may be linked`. `wrong-target` (skipped for images and
     targets under `reviews/`): the spec's rule (section 5) applied to `token = raw[textStart:textEnd]` without
     backticks, trimmed; detail `"<token>" links to <linkTo(f, Target(target, heading))>; …`.
  6. `unlinked` / `unlinked?` per mention (rulings only in the port): `<token>: link it to <linkTo(f, target)>`;
     uncertain is a warning.
  7. `stray` (185-189), after all files: every file not ending in `.md` and not in `embedded`:
     `Problem('$label/$f', 0, 'stray', detail)`, never a warning; detail `an image no page embeds` for `.png`,
     else `not Markdown; it does not belong in docs/`. Only a resolving image link embeds.
- Final sort.

### B.9 history.dart: `GitHistory(repoRoot, prefix)`, every answer cached
- `GitHistory.of(folderRoot)` (21-26): `git -C <root> rev-parse --show-toplevel --show-prefix`; null on failure;
  line 0 the repo root, line 1 the prefix (`docs/`). Later commands run `git -C <repoRoot>`.
- `main` (31-38): first of `refs/remotes/origin/main`, `refs/heads/main` that `git rev-parse --verify -q
  <ref>^{commit}` accepts; null if neither.
- commits on main (40-42): `git rev-list <main>` lines. `onMain(sha)` (45-48): a 40-char sha is in the set; a
  shorter one is a prefix of some member.
- `lineCommits(rel)` (52-67): `git blame --porcelain -- <prefix><rel>` (working tree, no revision); empty on
  failure; header `^([0-9a-f]{40}) \d+ (\d+)`, group 2 the final line number; a sha starting with `0000000000` is
  null (uncommitted). Blame follows renames.
- `commitOf(rel, line)` (70-73): the entry for a 1-based line or null.
- `show(commit, repoPath)` (76-79): `git show <commit>:<repoPath>`, CRLF to LF, null on failure.
- `existedAt(commit, rel, heading?)` (84-93): `show(commit, prefix+rel)`; missing: false; else true with no
  heading, otherwise whether `headingsOf(text)` includes the heading. (The source tried old locations first; the
  port has none.)
- `latestOnMainWith(rel, heading?)` (97-105): null without main; `git log --format=%H <main> -- <prefix+rel>`;
  newest first, the first commit where `existedAt` holds.

### B.10 pin.dart
- `PinReport(pinned: int, unpinnable: list[str])`.
- `pinLinks(v, git, label='docs')` (24-66), for each markdown history file: links from `scanLinks(mask(raw))`,
  the line by counting `\n` up to `l.start`. Skipped: already pinned, angle, any scheme, absolute, empty path.
  Per link: target normalized; heading decoded when frag non-empty and `.md`; `escapes` as the check;
  `commit = git.commitOf(f, line)`; `fromMain = commit != null && onMain(commit)`. Branch lines: if `!fromMain &&
  (escapes || _resolves(v, target, heading, frag))`, skip. Choosing the commit: `at = escapes ? null : (fromMain
  && existedAt(commit, target, heading) ? commit : latestOnMainWith(target, heading))`. Unpinnable: `at == null`
  or the link has a non-pin title: `'$label/$f:$line: <raw link>'`. Otherwise insert `' "git:<at[:12]>"'` at
  `l.end - 1`, applied in reverse order; write the file; `pinned` += insertions.
- `_resolves` (69-71): `isFile(target) && (heading == null || a heading text == heading || slugs(target) has frag)`.

### B.11 The binaries
- `links_check`: root is `args[0]` or `<repoRoot>/docs`; prints each problem; `failing` = non-warnings; if > 0
  prints `<n> problems` and exits 1; else `OK`, exit 0 (warnings do not fail). A duplicate heading key or a git
  failure raises.
- `pin_links`: same root; no git or no main: stderr `pin-links: <root> is not in a git repository with a main
  branch`, exit 2; prints `pinned <n> links`; one `NOT PINNED: <u>` per unpinnable; if any: `<n> links not
  pinned: no commit on main has their target`, exit 1; else 0.

### B.12 Test inventory (port every test not about a removed kind)
Fixture `_vault(extra)` builds a temp `docs/`: a log with `## 9. Devices` and `### 9.18 Device kill is an
emergency act`, a `design/02-the-day.md` with `## 3. On the route`, a page embedding a png, plus the png. The port's
fixture: a log with section 1 and entries 1.1 (applied), 1.2 (recorded), 1.3 (note); `design/02-x.md` with
`## 2.1 Title`; a page embedding `images/a.png`.

check_test.dart (no git): base clean · generated dead link is a warning, elsewhere a problem · linked references
clean · escape · dead-file and a folder · dead-heading · form: wikilink, reference style, angle, slug, encoded dash,
absolute, file scheme (https and mailto fine) · `decision log 9.18` unlinked (certain) · a ruling in a
reference-only parenthesis certain, bare one a warning · plain stays plain in headings, code, comments, link text,
URLs, versions, own heading numbers · wrong-target · a link into a review file is exempt · the log's `Answers:`
lines are skipped · stray and an unembedded image · linkTo relative and same file · three-digit rulings keyed,
grouped, bare · `§`-written rulings keyed, grouped, bare · backtick heading linked with `%60` is clean, unlink
reads the text · raw backtick in an anchor is `form` with the encoded anchor in the detail · decoding cases
(`bad%zz%C3%20end` gives `bad%zz%C3 end`; `phon%65` is `form`) · a link into the log must land on an applied entry
(recorded, note, section heading give `unapplied-target`; the file alone is fine) · inside the log a Supersedes link
may point at a section heading, from another file it may not · a link title is scanned without quotes and the pin
read from it · round trip: wrapping every mention with linkTo leaves only the non-mention problems.

Pinned group (a real git repo with `docs/` inside; commit `one` on main has a heading that commit `two` drops;
branch `feature` from `two`): an unpinned link on a line from main is `unpinned`, gone today or not, a review file
too · pinned links resolve at their commit though gone today · a pin must be a commit on main and its target exist
there (`pin`, `dead-pin` for a missing heading and a missing file, `form` for a mis-encoded anchor, `pin` for a
non-commit) · an unpinned link on a branch line resolves now; same-file and external links exempt · main is
origin/main when there is one, else the local main; `onMain` with a 12-char prefix; `commitOf` follows a rename;
`existedAt`; `latestOnMainWith`.

pin_test.dart: pins main lines to their commit, else to the newest commit with the target, lists the rest (`pinned
== 4`, one unpinnable `docs/decision-log.md:9: [x](nothere.md)`, branch and same-file and https untouched, unlink
text unchanged; a second run pins 0) · pins a branch line whose target is gone from the working tree to the last
main commit with it.

unlink_test.dart: a link becomes its text · same-file link · balanced parentheses inside the destination · a pinned
link drops its title · images stay · links in code stay · no links unchanged · mask keeps newlines and length ·
headings keep raw text · anchor encoding · GitHub slug keeps accented letters.

## C. The freshness tool (Dart): `.claude/skills/ensure-up-to-date/tool/`

`bin/{check,mark,recorded_at}.dart`, `lib/src/{declaration,files,generate,dvc,report,recorded}.dart`,
`lib/record.py`, tests `test/{check_test,generate_test,hook_test}.dart`. Depends on `docs_links`, `glob`, `path`,
`yaml`.

### C.1 stages.yaml schema (declaration.dart:19-54)
Top level: `dvc` (string, required, the exact DVC version), `stages` (map, required; order kept). Missing or wrong
type: `stages.yaml needs "dvc: <version>" and a "stages:" map`. Zero stages must be written `stages: {}` (a bare
`stages:` is null and fails).

Per stage: `skill` (scalar, required; the DVC `cmd`), `inputs` (list, required, non-empty; globs, placeholders
allowed in one-to-one stages), `outputs` (list, default `[]`), `each` (string; makes the stage one-to-one; the glob
whose matches are the items), `root` (string; required with `each`; an item's id is its path relative to root
without extension), `exclude` (list of exact repo-relative paths).

Errors (FormatException): `stage <name> needs a map (skill, inputs, outputs)`; `stage <name>: <k> must be a list`;
`stage <name>: <k> must be a string`; `stage <name> needs a skill and inputs`; `one-to-one stage <name> needs a
root`; `stage name <name> contains --`.

### C.2 Expansion (generate.dart, files.dart)
- Universe: `git -C <root> ls-files --cached --others --exclude-standard -z`, existing on disk, sorted, posix.
- Glob matching: `*` within one folder, `**` across; `?`, `[…]`, `{a,b}` work; no wildcard matches the exact file.
  Python: `fnmatch` does not do `**`; implement a small translator: `**/` matches zero or more folders, `**` alone
  matches everything, `*` is `[^/]*`, `?` is `[^/]`, `{a,b}` alternation, `[…]` classes; anchor the regex.
- All-to-all stage: one DVC stage named after it; deps the union of input matches minus `exclude`, sorted; outs
  likewise.
- One-to-one: items `_expand([each], exclude)`; per item `rel = relative(item, root)`, `id = rel` minus the last
  extension; an id containing `--` raises `item id "<id>" of stage <name> contains --`; DVC stage `<name>--<id>`;
  each input and output pattern filled by `_fill` then expanded with `keepLiteral`.
- `_fill`, plain replacement in order: `{each}` the item path, `{id}`, `{group}` id up to the first `.` (whole id
  if none), `{name}` id after the first `.` (whole id if none).
- `keepLiteral`: a filled pattern matching nothing and containing no `*` is kept as a literal path (an output not
  built yet; DVC reports it missing).
- `exclude`: exact removal from deps, outs and items, after filling.

### C.3 dvc.yaml rendering (generate.dart:66-91)
```
# Generated by `just ensure-up-to-date` from tools/stages.yaml. Do not edit.
stages:
  '<name>':
    cmd: '<skill>'
    deps:
    - '<dep>'
    outs:
    - '<out>':
        cache: false
```
Stages sorted by name; every scalar single-quoted with `'` doubled; `deps:` always written (null when empty);
`outs:` only when there are outputs, each with `cache: false`. Byte-stable. With zero stages the port writes
`stages: {}` so DVC parses it.

In step (report.dart:87-90): if `dvc.yaml` is missing or differs byte for byte from the rendering, the check
prints `dvc.yaml is out of step with stages.yaml and the files (a file was added, removed or moved).`, counts it
as stale, and goes on. Only `mark` writes dvc.yaml.

### C.4 The check (report.dart:74-147, check.dart)
Flags: `--root <dir>` (absolute; default `git rev-parse --show-toplevel`), `--full`, `--target <path>`,
`--warnings-as-errors`. A value flag without a value: stderr `<flag> needs a value`, exit 2. Exit 0 when ok, 1
otherwise.

Order: (1) declaration problem: missing file `no tools/stages.yaml at <root>` plus, only then, `this commit
predates the freshness check; merge main into it, or push with --no-verify`, then `run /ensure-up-to-date`; parse
error `tools/stages.yaml at <root>: <message>`. (2) DVC version: `dvc --version` trimmed must equal `dvc:`; not
found: `DVC is not installed. Install it: uv sync in tools/`; wrong: `DVC <wanted> is required, found "<have>".
Install it: uv sync in tools/`; that line alone, no run line. (3) in step. (4) `dvc status --json` in the root;
non-zero exit gives `dvc status failed: <msg>` plus the run line; empty stdout is `{}`; per stage key the value is a
list; a non-map element becomes a line as-is; per map element, key `changed deps` gives tag `dep`, `changed outs`
tag `out`, anything else its own key; each `path: state` pair becomes `<tag> <path> <state>` (for example `dep
defs/a.one.md modified`, `out out/page.md deleted`); lines sorted within a stage, stages by name. (5) `--target`:
`t` normalized (backslashes to `/`, leading `./` and trailing `/` stripped repeatedly); a stale stage is kept when
any expanded out `isUnder(o, t)` or its stages.yaml stage has an output glob with `isUnder(staticDir(g), t)`;
`isUnder(p, t)`: t empty, or `p == t`, or `p.startswith(t + '/')`; `staticDir` cuts the glob at the first
`[*?\[{]` then back to the last `/`. (6) grouping: stale stages grouped by the part before the first `--`, groups
sorted; per group `<decl>: <n> stale (<skill>)`; then `  <name>` for the first 20 items or all with `--full`; under
each `    <line>` for the first 5 lines or all with `--full`; over 20 without `--full`: `  … and <n> more`. (7)
links, only with `--target`: run the link checker on `<root>/docs`, keep problems whose file is under `t`; print
each; if any: `links in <t>: <p> problems, <w> warnings` plus ` (warnings do not fail without
--warnings-as-errors)` when warnings and the flag is off; fail when `p > 0` or (flag and `w > 0`): `fix the links
in <t> (just links-check, /reconcile-links)`. (8) ending: nothing stale and links fine: `OK`; stale: `run
/ensure-up-to-date`; links failing alone: no run line.

### C.5 mark (mark.dart, record.py)
Root always `git rev-parse --show-toplevel`. Declaration problem or DVC problem: stderr, exit 1. No arguments:
`usage: mark <stage>… | --generate-only`, exit 2. Always rewrites `dvc.yaml`. `--generate-only` alone: `dvc.yaml
generated: <n> stage(s), none marked`, exit 0. Name resolution: every expanded stage whose name or declaration name
equals an argument; unknown arguments dropped if at least one matches; none: `no stage named <args>`, exit 1. Then
in-process DVC (the port imports `dvc.repo.Repo`; the source ran `record.py` through DVC's own Python):

```python
from dvc.repo import Repo
from dvc.exceptions import DvcException
with Repo(root) as repo, repo.lock:
    stages = [s for s in repo.index.stages if s.name in wanted]
    missing = wanted - {s.name for s in stages}
    if missing: raise DvcException('no stage named ' + ', '.join(sorted(missing)))
    for stage in stages: stage.save(run_cache=False)
    stages[0].dvcfile.dump_stages(stages, update_pipeline=False)
```
On error: stderr `dvc commit <stages> failed:` plus the message, exit 1, no trace. Success: `marked up to date: <n>
stage(s)`. Writes only `dvc.lock`.

### C.6 recorded-at (recorded.dart)
Exactly one argument or exit 1. `entry(commit)` = `git show <commit>:dvc.lock` parsed, `json.dumps(stages[stage])`
(key order kept), null if missing. `head = entry('HEAD')`; null: exit 1. Candidates `git log --full-history
--format=%H -- dvc.lock`, newest first; the first `c` with `entry(c) == head` and every parent (`git rev-list
--parents -n1 c`, fields after the first) with `entry(parent) != head` wins; a root commit wins vacuously. None:
exit 1, no output. Prints the sha.

### C.7 Test inventory
check_test (temp git repo, `dvc init`, stages `screen` one-to-one over `defs/*.md` and `docs`): DVC version ok ·
other wanted version names the install command · nothing marked: every stage stale, ends with run · all marked:
exactly `OK` · an edited definition makes only `screen--a.one` stale with `dep defs/a.one.md modified` · an edited
shared input makes every screen stale · a hand-edited output is `out out/page.md modified` · a new definition:
out of step · a deleted still-tracked page: out of step and the rendering drops it · 24 stale items show 20 plus
`… and 4 more`, `--full` all · marking `docs` leaves only the screens · recorded-at null before marking, then the
commit · recorded-at ignores a `--no-ff` merge · recorded-at null when HEAD's lock lacks the stage · a mark DVC
refuses (a removed one-to-one output) exits 1 naming the file, no trace · a failing `dvc status` is `dvc status
failed:` plus run · missing stages.yaml: the no-file line, the predates line, run, exit 1 · malformed stages.yaml:
the parse error, exit 1 · mark with missing or malformed file: stderr, exit 1 · wrongly typed fields: exactly two
lines, exit 1 · `--target` keeps only stages with outputs under it (`lib/`, `lib/a`, `./out`) · a target with
nothing stale is OK while others are stale · a link warning in the target prints and is OK, fails with
`--warnings-as-errors` · a warning outside the target is ignored · a problem in the target fails · no target: links
not checked, exactly `OK` · exit codes 0, 1, 2 for a bare `--target`.

generate_test (in-memory file list): declaration parses keeping version, order, `each` · globs expand sorted, `**`
recursive, literal matches itself, no match empty · all-to-all stage with excludes · one-to-one `screen--<id>` with
group/name fills · a not-yet-built one-to-one output is declared · `stageDeclOf` · rendering byte-stable, header,
quoting and `cache: false` layout · a single quote doubled · an id with `--` refused · a stage without inputs
refused.

hook_test (a work repo and a bare remote, the hook installed): a stale tip refused with `run /ensure-up-to-date` ·
a tip without stages.yaml refused with the predates line · a current tip accepted · an uncommitted edit changes
nothing · an unpinned log link from main refused with `unpinned links from main: run just pin-links, commit, push
again`, accepted once pinned · a fake failing `dvc` on PATH refuses with the install line · a push from a linked
worktree gets the right verdicts and leaves the clone's config untouched · a hook killed by SIGTERM removes its
temporary worktree.
