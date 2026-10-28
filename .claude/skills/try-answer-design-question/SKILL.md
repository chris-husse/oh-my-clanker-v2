---
name: try-answer-design-question
description: Answer one design question of a review before the owner sees it - read the cited sections and their neighbours through the knowledge graph, read the decision history the way /how-we-got-here does, propose a ruling with its choice and its additions apart, rate confidence (high, medium, low), and reduce the question to its open part when not high. One answer file out, edits nothing. Run by /review-design step 4, one agent per question, or by the owner on a single question.
---

# Try to answer a design question

Input, in the prompt or as the argument:

- **Question:** the review reference (`R42`, `01.3`), the quoted passages with file and heading, the question.
- **Output:** the path to write, `<RUN>/answer-<ref>.md` in a review run; standalone,
  `.cache/try-answer/<ref>.md` under the repository root (`.cache/` is gitignored).
- Optional, for a test against a ruling already made: **Blind before N.k**: read the decision log only up to the
  entry before `### N.k`, treat that entry and every later one as nonexistent, and ignore those ids in any tool
  output. **Corpus at <commit>**: read the corpus only as `git show <commit>:<path>` (before commit `c295191` the
  corpus lived under `design/`, not `docs/design/`).

Every command starts from `ROOT=$(git rev-parse --show-toplevel)`. Never edit a file but the output. Never read
`docs/reviews/` beyond the lines of the question's own item, nor `docs/superpowers/`.

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
settles for this question, and which rulings are the owner's own (a Decision without the sentence `Decided
automatically by the review session`).

## 3. The answer

- **The choice.** The option the question offers that you would take, or your own formulation when none fits.
- **Additions.** Anything beyond the choice that your ruling would also fix: mechanisms, keys, file names, a
  second behaviour. Each is listed apart, because an addition is where an answer most often decides what the owner
  did not ask and might not want.
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
