# Agent prompts

Every agent of `/review-design` and `/validate-design` is dispatched with one of the four
templates below. A prompt is the block of section 1, then one
template body, with every angle-bracket placeholder filled. Nothing else, except where a template says so. Agents do not
see the session's skills, so a template carries everything its agent needs. The session reaches
the decision log and the corpus only through agents; the templates are how.

## 1. Every prompt

The first lines of every prompt, verbatim. `<ROOT>` is the repository path from
`git rev-parse --show-toplevel`. `<OUTPUT PATH>` is the agent's file in the run directory;
the names are in `worksheet.md`.

```
You are a read-only agent on this repository's design folder, docs/ in the repository at <ROOT>.
Do not create, delete, move or trash any file outside your assigned output path.
Do not read: docs/reviews/ (except the file under review and its iterations), anything matching the exclude globs of tools/corpus.yaml (docs/superpowers/), or anything outside docs/.
The decision log docs/decision-log.md is rulings. The latest ruling wins. Read it fully before you report anything.
The corpus is every file matching the corpus globs of tools/corpus.yaml (`git ls-files -co --exclude-standard -- 'docs/design/*.md' 'docs/e2e-tests/*.md'`, untracked files included, Markdown only; it mirrors the globs `design/**/*.md` and `e2e-tests/**/*.md` of tools/corpus.yaml).
You cannot ask the owner. Put every doubt in your output under a heading "Doubts".
Write your output to <OUTPUT PATH> and reply with only the number of findings (or the number of passages touched).
```

## 2. Dispatch

- `subagent_type: general-purpose`. Never pass a `model` parameter; the agent inherits the
  session's model.
- Dispatch all agents of one step in a single message.
- Wait for every completion before reading any output.
- A missing output file means the agent failed (`findings-format.md`). Redispatch that agent
  once, with the same prompt.

## 3. check-cluster

Purpose: decide, for one cluster of comments from the review file, which comments a ruling
already answers, which need the owner, and which are dropped. One agent per cluster, in step 4
of `/review-design`.

Inputs:

- `<description>`: the two or three sentences the session wrote about the review file.
- `<cluster text>`: the comments of the cluster, each verbatim under its reference.
- `<OUTPUT PATH>`: `cluster-<k>.md` in the run directory.

Body:

```
The review file is: <description>
Your cluster is the comments at the end of this prompt. Find every passage in the corpus and the decision log that they concern.
Return exactly one verdict per comment. When one comment has a settled part and an open part, write two blocks under the same reference, one per part, and name the part in the first line of each.
Settled: a ruling answers the comment. Name the ruling, and name any document that still disagrees with it.
Needs a ruling: two documents can both be read as correct and they disagree, or the comment relies on something no document and no ruling defines. Two documents that disagree with the log silent are needs a ruling.
Dropped: taste, a restatement of something settled, or a repeat of another comment.
One block per comment, in this form:

## <comment reference>
**Verdict:** settled | needs a ruling | dropped
**Settled by:** <ruling number, and "document lags: <file, heading>" if a document still disagrees>   (settled only)
**This says:** <quoted passage, file and heading>   (needs a ruling only)
**Conflicts with:** <quoted passage, file and heading, or "nothing; undefined">   (needs a ruling only)
**Why it matters:** <one or two sentences>
**Question for the owner:** <one question>   (needs a ruling only)
**Reason:** <one line>   (dropped only: taste, restatement of something settled, or repeat)

The number of findings in your reply is the number of verdict blocks.

Comments:
<cluster text>
```

## 4. validate-document

Purpose: check one owned document against the rest of the corpus and report findings. One
agent per corpus document, in step 4 of `/validate-design`.

Inputs:

- `<document path>`: the owned document, repo-relative.
- `<OUTPUT PATH>`: `validate-<doc>.md` in the run directory.
- In cycle mode, `<N>`: the number of the section in progress.

Body:

```
Your document is <document path>, a corpus document.
It is checked against every other corpus document.
Where a passage matches the latest ruling, that passage is correct and the other document is the finding.
Report only genuine conflicts, gaps and wording findings. Conflict: two passages disagree. Gap: a document relies on something no other document and no ruling defines. Wording: one thing under two names. Quote both passages where two exist. No proposals, no restyling, no praise. Report a finding only if it is an actual problem: a user would experience something wrong or contradictory (a flow that dead-ends, two documents prescribing different behaviour); data, security or rights could go wrong; or a builder would have to guess between two behaviours that both look intended. Never report: wording, unless two names would show the user an actual inconsistency; technical internals the design leaves to the technical design; rare edge cases whose sensible answer is obvious; definitions nobody would act on differently; anything a reasonable builder would simply get right. When in doubt, leave it out.
When a ruling of the decision log settles the finding and a document lags behind it, name that ruling's number in **Why it matters** (for example: settled by 3.7; 02-repos-and-config.md §2.6 lags). When a `Declared minor` entry of the log covers the finding, name it the same way (for example: declared minor in 4.6).
Number findings from 1, one block per finding, in this form:

## n. <title>
**Group:** conflict | gap | wording
**This document says:** <quoted passage, file and heading>
**Conflicts with:** <quoted passage, file and heading, or "nothing; undefined">
**Why it matters:** <one or two sentences>
**Question for the owner:** <one question>

When you have nothing to report, write a file saying `No findings.`
```

In cycle mode, add this line to the body:

```
The section "## <N>. Review: ..." at the end of the decision log is in progress and counts as rulings.
```

## 5. carry-document

Purpose: make one document say what a ruling says, one agent per document. Used by
`/review-design` for settled-but-lagging comments (steps 7 and 8); new rulings of a review are
applied by `/apply-decision` (`.claude/skills/apply-decision/SKILL.md`).

This agent is not read-only for its one document. Its prompt replaces the first line of the
block in section 1 with:

```
You may edit exactly one file: <document>. Do not create, delete, move or trash any other file.
```

The other lines of the block stay as they are.

Inputs:

- `<document>`: the one document, absolute path.
- `<rulings>`: the decision-log entries to carry, verbatim.
- `<OUTPUT PATH>`: `carry-<doc>.md` in the run directory.

Body:

```
The repository is at <ROOT>.
The rulings at the end of this prompt are the decision-log entries to carry. Edit your document so it says what they say, in the corpus's own words, with every reference you write as a link (docs/LINKS.md). Change nothing a ruling does not require. Do not restyle, reorder or trim anything else.
In your output, list each passage you touched as one line: file, heading: before → after. Then your doubts under "Doubts".

Rulings:
<rulings>
```

## 6. verify-review

Purpose: check that the new decision-log section answers every unit of the review file or
iteration file. In step 6 of `/review-design`, repeated until every unit is answered or
dismissed.

Inputs:

- `<review file path>`: the review file or iteration file, repo-relative.
- `<unit>`: the unit of a comment for this file, as the session defined it.
- `<section>`: the new section, verbatim, as written so far.
- `<pending uncertainties>`: unresolved answer ambiguities from the worksheet, or `None`.
- `<OUTPUT PATH>`: `verify-<nn>.md` in the run directory.

Body:

```
The file under check is <review file path>. It is the file under review of the do-not-read line above: it is the file being answered, not a source of rulings, and nothing else under docs/reviews/ may be read. Its unit of a comment is: <unit>.
The new section of the decision log, as written so far:

<section>

Pending uncertainties (not rulings):
<pending uncertainties>

For each unit of the file, in file order, write one list item: the unit's reference, then `answered by N.n`, naming the entry whose ruling, settled line or declared-minor line covers it, or `not answered`, then one line why.
Check uncertainties against existing material. Only materially new unresolved choices belong
in the next question pass; ordinary implementation details and correctness requirements do not.
The number of findings in your reply is the number of units marked not answered.
```
