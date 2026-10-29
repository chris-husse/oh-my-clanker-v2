---
name: try-answer-design-question
description: "Independently answer one design review question from the corpus and ruling history. Separate the choice, conditions and additions, report contradictions and confidence, and write one answer file. Used by /review-design in a fresh agent after the orchestrator saves its own answer, or standalone by the owner. Never records a ruling."
---

# Try to answer a design question

Input, in the prompt or as the argument:

- **Question:** the review reference (`R42`, `01.3`), the quoted passages with file and heading, the question.
- **Output:** the path to write, `<RUN>/answer-<ref>.md` in a review run; standalone,
  `.cache/try-answer/<ref>.md` under the repository root (`.cache/` is gitignored).
- Optional, for a test against a ruling already made: **Blind before N.k**: read the decision log only up to the
  entry before `### N.k`, treat that entry and every later one as nonexistent, and ignore those ids in any tool
  output. Enforce it with a truncated copy, never by reading around later entries: copy `docs/` to a fresh temporary
  directory, cut the copy's `decision-log.md` at the line before `### N.k`, and run every `just decisions` command
  as `just decisions --docs <copy> …`, so `history` and `search` cannot print a later ruling. **Corpus at <commit>**: read the corpus only as `git show <commit>:<path>` (before commit `c295191` the
  corpus lived under `design/`, not `docs/design/`).

Every command starts from `ROOT=$(git rev-parse --show-toplevel)`. Never edit a file but the output. Never read
`docs/reviews/` beyond the lines of the question's own item, nor `docs/superpowers/`.

In a review run, use fresh context: no inherited conversation, orchestrator answer, worksheet,
cluster recommendations, comparison or other agents' answer files. Read only the supplied neutral
question, its source passages, relevant corpus and decision history, and the skill/tool instructions
needed to investigate them. Do not inspect other files in the run directory. If a proposed answer
or previous comparison was supplied or exposed, report the contamination and do not claim an
independent answer; the caller must start a fresh agent. Your confidence alone never authorizes a ruling.

## 1. Where the question lives

List the sections the question cites. Map their neighbourhood through the knowledge graph (ignore an
`OMC_KNOWLEDGE` line and GitNexus warnings on stderr; in blind mode with an old corpus, skip the graph and use
`git show <commit>:<path> | grep -n '^#'`):

```bash
omc internal gitnexus cypher "MATCH (s:Section) WHERE s.filePath = 'docs/design/<file>' RETURN s.name"
omc internal gitnexus cypher "MATCH (f:File)-[r:CodeRelation]->(g:File) WHERE f.filePath = 'docs/design/<file>' AND r.type = 'IMPORTS' RETURN g.filePath"
```

Read the cited sections in full, then the sections of the linked documents that bear on the question. A
`recorded` ruling not yet `applied` overrides the corpus text it affects. `/omc:explain` is optional: use it only
for a question about `tools/` or when the graph's semantic search covers the corpus (on 2026-10-28 GitNexus embeds
code symbols only, so `query` ranks the tools above the design).

## 2. How it came to be

Follow steps 1 to 3 of `.claude/skills/how-we-got-here/SKILL.md` for the question's topic: `just decisions history
"<docs-relative path>#<heading>"` for every cited heading, `just decisions search --text '(?i)<word>' --oneline`
for the topic's words, then read the rulings in full and follow `later:` pointers. Note what each ruling already
settles for this question and its provenance: `**Automated.** true` means automated;
`**Automated.** false` means human-recorded. Missing means legacy/unspecified, not proof of human
authorship. For legacy entries, the old sentence `Decided automatically by the review session`
is evidence of automation; otherwise inspect the recorded source before claiming human authorship.
All effective existing rulings constrain the answer. Automated rulings carry less weight: never
prefer one over a conflicting human or legacy ruling because it is newer; surface the conflict.
An answer that would change an automated ruling may say so and name it. Follow human-directed
successors to determine what still holds. Never restore withdrawn rulings from git history.

## 3. The answer

- **The choice.** The option the question offers that you would take, or your own formulation when none fits.
- **Additions.** Anything beyond the choice that your ruling would also fix: mechanisms, keys, file names, a
  second behaviour. Each is listed apart, because an addition is where an answer most often decides what the owner
  did not ask and might not want.
- **Scope and conditions.** State the limits and qualifications that must hold for your choice,
  so the caller can compare substantive agreement rather than matching option names.
- **The ruling.** Context in one or two sentences, Decision in one to three, in the corpus's words, every reference
  a Markdown link relative to `docs/` with `%20` for spaces and `%60` for backticks in anchors
  (`[09 §9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop)`, a ruling `[1.2](#1.2%20<its title>)`). The Decision
  holds the choice; the additions stay out of it unless the choice cannot be stated without them.
- **Contradictions.** Any existing ruling, the owner's or automatic, that the choice or an addition contradicts,
  quoted. A contradiction with one of the owner's rulings forces the confidence to medium at most.
- **Confidence.**
  - high: one answer follows from the corpus and the rulings, no alternative is close, and no high-impact
    criterion applies;
  - medium: a clear preference with a defensible alternative, or one high-impact criterion applies;
  - low: no preference, or the answer depends on facts outside the corpus (the owner's environment, a licence, a
    budget).

  High-impact criteria: a change to the MVP's scope; a legal, licensing, credential or owner-environment matter;
  an architectural fork of a lifecycle, the render path or the watch process; a change to what the owner does by
  hand. When in doubt, the lower level.
- **Question for the owner**, when not high: as short as the open part allows. Start with what you would record
  anyway as one strikeable line each (`I would record: …`), then the open choice with its options named and your
  recommendation. The owner should be able to answer with one word or by striking a line.

## 4. Output

Write the output file, under 500 words, in this form, and reply with only the confidence:

```
## <ref>
**Confidence:** high | medium | low — <one sentence why, naming any high-impact criterion>
**Choice:** <the option, one line>
**Scope and conditions:** <limits and necessary qualifications, or "none">
**Closest alternative:** <the runner-up and why it is or is not close>
**Evidence:** <one line per section or ruling that decides it>
**Contradicts:** <ruling ids with the quoted clash, or "none">
### Proposed ruling
**Context.** …
**Decision.** …
### I would also record
- <addition, one line each, or "nothing">
### Question for the owner
<only when not high>
```
