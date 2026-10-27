---
name: validate-design
description: Multi-agent closure pass over every corpus document (the files matching the `corpus` globs of tools/corpus.yaml, each against the rest of the corpus and the decision log), producing one review file in docs/reviews/. Standalone with no argument it commits that file; with a review file path as argument it runs as a step of /review-design and writes that review's next iteration file. Only on the owner's explicit word; it commits.
---

# Validate the design corpus

One agent per corpus document checks its document against the rest; the session
merges what they report into one review file. Nothing in that file is a ruling; only the owner
rules, through `/review-design`. The rules this skill follows live in
`.claude/skills/design-review-conventions/`: `review-files.md` (names, gate, iteration files,
the shell functions), `findings-format.md` (the block an agent writes), `agent-prompts.md`
(the prompt), `triage.md` (buckets, consequence sort, status line), `worksheet.md` (the run
directory and the output file names). This file names them by path and does not restate them.

Two modes, decided by argument presence alone:

- **Standalone**: no argument; the owner asked for a pass. Writes a new review file and commits
  it alone.
- **Cycle**: the argument is the original review file path, passed by `/review-design` at its
  validate step. Writes that review's next iteration file, leaves it in the working tree, and
  ends with the status line.

The skill runs inline in the calling session, never forked, never as a subagent. The session
reads only the agent outputs in the run directory, the files of its own cycle under
`docs/reviews/`, and the conventions files. The corpus and the decision log are read by
agents, never by the session.

Every command below starts from `ROOT=$(git rev-parse --show-toplevel)` and runs in a subshell
in `ROOT`, so it works from anywhere in the repository. Shell state does not survive between
calls: write the run directory path in place of `<RUN>` in every command. Where a command uses
`review_gate`, `review_undecided` or `review_next_iteration`, paste the whole function block of
`review-files.md` section 3 into that subshell where the comment says so.

## 1. Mode

The argument is `$ARGUMENTS`.

- Empty: standalone. Say `Mode: standalone.`
- Otherwise: cycle. The argument is the original review file, repo-relative, and must pass the
  gate as `OK`:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT"
# paste the function block of review-files.md section 3 here
review_gate "<argument>")
```

`OK`: say `Mode: cycle, next iteration of <argument>.` Anything else: stop and report the line
the gate printed. `/review-design` commits the file at its own gate (`review-files.md` section
5), and an iteration file, raw feedback or any path not directly in the folder is never the
argument.

## 2. Run directory

Standalone: create one.

```bash
RUN=/tmp/design-review-$(date +%Y%m%d-%H%M%S); mkdir -p "$RUN"; echo "$RUN"
```

Cycle: `/review-design` states its directory in the conversation as `Run directory: <path>`.
Use that path. When the line is absent or the directory does not exist, create one with the
command above and say that you did.

## 3. Inventory

The corpus is every file matching the `corpus` globs of `tools/corpus.yaml`
(`design/**/*.md`, `e2e-tests/**/*.md`, relative to `docs/`):

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git ls-files -co --exclude-standard -- 'docs/design/*.md' 'docs/e2e-tests/*.md')
```

The command mirrors those globs (git's `*` crosses folders), untracked files included and Markdown only, so a
document written but not yet committed is validated too. Print the list and its count. Each file gets one agent. Nothing else is checked:
`decision-log.md` is rulings, `docs/reviews/` is history and `docs/superpowers/` is excluded.

## 4. Dispatch

One validate-document agent per document, all in one message, `subagent_type:
general-purpose`, no `model` parameter. Each prompt is the every-prompt block of
`agent-prompts.md` section 1 followed by the validate-document body of section 4, placeholders
filled and nothing added:

- `<ROOT>`: the output of `git rev-parse --show-toplevel`.
- `<OUTPUT PATH>`: `<RUN>/validate-<doc>.md`, `<doc>` the document's path below `docs/` without
  `.md`, every `/` as `-` (`worksheet.md` section 3); `docs/design/02-repos-and-config.md`
  writes `<RUN>/validate-design-02-repos-and-config.md`.
- `<document path>`: repo-relative, as listed in step 3.

In cycle mode append the cycle line of `agent-prompts.md` section 4, with `<N>` the number of
the section `/review-design` is writing. Take N from the conversation when `/review-design`
stated `Section: N`. `Section: none` means no section is in progress; leave the cycle line out.
When neither was stated, take N from the working-tree log with one scan, which prints one
line and does not load the log into the session: a section is in progress when the last
section's header still carries `Review file (open):`; otherwise the cycle line is left out:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && awk '/^## [0-9]+\. /{n=$2; o=0} /^Review file \(open\): /{o=1} END{if (o) print "## " n; else print "no section in progress"}' docs/decision-log.md)
```

Wait for every agent to complete. An agent replies with only its number of findings; the file
is what counts. Then check that every document has its output:

```bash
ROOT=$(git rev-parse --show-toplevel); RUN=<RUN>; (cd "$ROOT" && for d in $(git ls-files -co --exclude-standard -- 'docs/design/*.md' 'docs/e2e-tests/*.md'); do doc=${d#docs/}; doc=${doc%.md}; doc=${doc//\//-}; [ -f "$RUN/validate-$doc.md" ] || echo "missing $d"; done; ls "$RUN"/validate-*.md | wc -l)
```

The count must equal the inventory count and no `missing` line may print. Redispatch each
missing agent once, with the same prompt, wait, and check again. Still missing: stop, name the
documents without output, keep the run directory, and report.

## 5. Merge and triage

Read every `<RUN>/validate-*.md`; a file saying `No findings.` contributes nothing. Then:

1. Drop duplicates: the same two passages, or the same gap, reported by two agents become one
   finding.
2. Merge both sides of one conflict: the agents of the two documents each report the other
   document; keep one block with both passages, one title, one question.
3. Sort by consequence, `triage.md` section 2: conflicts, then gaps, then wording; within a
   group, the finding whose passages the most other findings cite first; ties by your
   judgement.
4. Number the findings from 1 in that order. A finding keeps its number wherever it lands.
5. Bucket per `triage.md` section 1, from what the agents wrote, never from the log. A finding
   goes to `already ruled, not carried` only when its block names the ruling that settles it and
   the document that lags; in cycle mode the rulings under `## Rulings as written` in
   `<RUN>/worksheet.md` count the same way. A finding whose block names no ruling `needs a
   ruling`. A `dropped` finding gets a one-line reason. A finding with a settled part and an
   open part is one entry under `needs a ruling` whose block names the settled part with its
   ruling number and the open part.

Write the result to `<RUN>/merged.md` first: the three bucket headings in the order below, each
finding under its bucket as a `findings-format.md` block with its number, already-ruled
findings with the ruling number, dropped findings with the reason. Then build the review file
from `merged.md`, not from memory. A failed merge keeps the run directory so the merge can be
redone from the files on disk.

## 6. Write the review file

Shape:

```
# Validation pass: <one sentence on what dominated>

Date: YYYY-MM-DD. Mode: standalone | iteration NN of <review file>. Documents checked: <count>.

## Needs a ruling
<findings in findings-format.md blocks, numbered>

## Already ruled, not carried
<findings, each with the ruling number>

## Dropped
<findings, each with a one-line reason>

## Undecided review files        (standalone only)
<output of review_undecided, or "none">
```

`Date` is `date +%F`. The first sentence names what the findings mostly concerned, not the
process. Write every design document, section, ruling, review item and E2E definition as a link, per `docs/LINKS.md`. The last section exists in standalone mode only; its parenthetical is not written.

**Standalone name.** `docs/reviews/$(date +%F)-<slug>.md`. The slug is the first finding
after the sort, in the words of `review-files.md` section 1, and must not plainly name an actor
or the process (`review-files.md` section 4). Check the name with the gate before writing:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT"
# paste the function block of review-files.md section 3 here
review_gate "docs/reviews/$(date +%F)-<slug>.md"; review_undecided)
```

`REJECT file does not exist` is the answer you want: the name is valid and free. `OK` or
`UNCOMMITTED` means the name exists: take the slug from the next finding down and check again;
when every finding's slug exists, stop and report the names. Any other `REJECT` means the slug
breaks the pattern: rewrite it. The `review_undecided` lines, or `none`, fill the last section
of the file; this contract check runs in standalone mode only.

**Cycle name.** The next iteration file of the argument,
`docs/reviews/iterations/<YYYY-MM-DD>-<slug>-iteration-NN.md`; NN in its name is the
iteration number. Create `docs/reviews/iterations/` with `mkdir -p` before writing the
file. The name:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT"
# paste the function block of review-files.md section 3 here
review_next_iteration "<argument>")
```

**Zero findings, cycle.** Write the file anyway:

```
# Validation pass: no findings

Date: YYYY-MM-DD. Mode: iteration NN of <review file>. Documents checked: <count>.

## Needs a ruling
No findings.

## Already ruled, not carried
No findings.

## Dropped
No findings.
```

**Zero findings, standalone.** Write nothing. Say `No findings; nothing written.`, then list the
undecided review files; there is no slug, so this is the only check:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT"
# paste the function block of review-files.md section 3 here
review_undecided)
```

Remove the run directory with `rm -rf <RUN>` and stop.

## 7. Finish

**Links.** `ROOT=$(git rev-parse --show-toplevel); rm -f "$ROOT/.cache/reconcile-links/changed.txt"; (cd "$ROOT" && just links-check)`
must print `OK`. Otherwise run `/reconcile-links` (it edits only Markdown in `docs/` and lists the files it changed in
`.cache/reconcile-links/changed.txt`), and commit the files it changed with this skill's own: the commit command below
adds `$(cat "$ROOT/.cache/reconcile-links/changed.txt" 2>/dev/null)`. The rule is `docs/LINKS.md`.
In cycle mode skip it: `/review-design` runs the same check before the commit that carries the iteration file.

**Standalone.** Commit the review file and the files /reconcile-links changed (`.cache/reconcile-links/changed.txt`)
alone; the paths after `--` limit the commit to them even when something else is staged. The stat must list that one file and the files /reconcile-links changed (`.cache/reconcile-links/changed.txt`).

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add "<file>" $(cat "$ROOT/.cache/reconcile-links/changed.txt" 2>/dev/null) && git commit -m "Review: validation pass, <slug>

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- "<file>" $(cat "$ROOT/.cache/reconcile-links/changed.txt" 2>/dev/null) && git show --stat --format= HEAD)
```

Then `rm -rf <RUN>`. Report: the file path, the count per bucket, the undecided review files,
and last: `Run /review-design <file> to decide it.`

**Cycle.** Do not `git add` anything; the iteration file stays unstaged, and `<RUN>` stays.
Report in a few lines: the iteration file path, then each bucket with its findings by number
and title. Then the status line of `triage.md` section 3 as the last line of output, nothing
after it. Iteration number: NN. New: findings in the first bucket that are not a split or
re-raise of one the owner saw in an earlier iteration of this cycle; judge that against the
earlier iteration files of this slug and `## Questions` in `<RUN>/worksheet.md`; in iteration
01 every finding is new and the previous-count stop rule does not apply. The previous
iteration's first-bucket count, for the stop rule, is in `## Status lines` in
`<RUN>/worksheet.md`. The second bucket is carried by `/review-design` after this skill ends,
so the line gives its count without the `carried` mark; `/review-design` re-emits the line
with the `carried` mark after carrying. `/review-design` continues from the status line.

## Never

- Never edit a corpus document or the decision log. The only write in the repository
  is the review file or the iteration file.
- Never read a corpus document or the decision log into the session; agents read them. The
  scan of step 4 prints one line, nothing more.
- Never read `docs/reviews/` beyond listing it and the files of the current cycle: the
  argument file and its iteration files in `docs/reviews/iterations/`.
- Never pass a `model` parameter, and never use a `subagent_type` other than
  `general-purpose`.
- Never delete, move or trash a file. The run directory under `/tmp` at the end of a
  standalone run is the one exception.
- Never run when the owner has not asked, and never from a fork or a subagent.
