# try-answer-design-question: answer a review question before the owner sees it

Date: 2026-10-28. Status: approved in discussion, written for review.

## 1. Goal

A large review produces more questions than the owner can answer, and most have one answer that follows from the
corpus and the earlier rulings. This skill answers one question the way the owner would have to: from the design
as it stands, the decision history, and the corpus around the cited passages. It states how confident it is.
`/review-design` runs it on every prepared question, records the confident answers, and asks the owner only the
rest, each reduced to its open part.

It replaces the "obvious" class that `/review-design` step 4 gained on 2026-10-27, where the session judged
obviousness from the cluster agent's one-line question without any analysis.

## 2. Why it looks like this

Two blind runs on rulings the owner had already made (1.11 config defaults, 1.15 red base), each reading the log
only up to the ruling before, settled the shape:

- 1.11: the run rated itself high and agreed with the owner, adding the mechanism the owner's one-line answer
  left implicit. Agreement, more specific text.
- 1.15: the run rated itself medium. It agreed with the owner on the open choice but stated a "settled" part the
  owner had in fact rejected: recording the red tests and handing them to the fix loop, which is the "accepted
  broken baseline" the owner ruled out.

So everything an answer adds beyond the choice asked is listed apart (`I would also record`) where the owner can
strike it; medium is never recorded automatically; and an answer that contradicts an in-person ruling is always
asked, never recorded over it.

## 3. The skill

`.claude/skills/try-answer-design-question/SKILL.md`. One question in, one answer file out. Read-only.

- **Input.** One prepared question: its reference in the review file, the quoted passages, the question, and an
  output path. Optional: `Blind before N.k` and `Corpus at <commit>` for a test against an existing ruling.
- **Evidence.** The cited sections and the documents they link to (the knowledge graph's `Section` nodes and
  `IMPORTS` edges through `omc internal gitnexus cypher`, then reading the text); the decision history the way
  `/how-we-got-here` reads it (`just decisions history` and `search`, following `later:` pointers). `/omc:explain`
  is optional and used only when the graph's semantic search covers the corpus or the question is about `tools/`;
  on 2026-10-28 GitNexus embeds code symbols only, so its `query` verb ranks the tools above the design.
- **Answer.** A proposed ruling in the log's style (Context, Decision, every reference a link), the choice
  separated from the additions, a confidence, the closest alternative, any contradiction with an existing ruling,
  and for anything not high a question for the owner reduced to its open part.
- **Confidence.** High: one answer follows from the corpus and the rulings, no alternative is close, and no
  high-impact criterion applies (MVP scope; legal, licensing, credential or owner-environment matters; an
  architectural fork of a lifecycle, the render path or the watch process; a change to what the owner does by
  hand). Medium: a clear preference with a defensible alternative, or one high-impact criterion. Low: no
  preference, or the answer depends on facts outside the corpus.

## 4. In `/review-design`

Step 4, after the cluster verdicts are merged: one try-answer agent per question in the needs-a-ruling list, about
twelve per message, outputs `<RUN>/answer-<ref>.md`. Step 5 records every high answer that contradicts no ruling,
its Decision ending in the fixed sentence `Decided automatically by the review session under the owner's standing
delegation: one clear recommendation, no close alternative.`, with its `I would also record` part left out unless
the owner later confirms it. Everything else is asked in the current-and-upcoming format, using the answer's
reduced question and showing its proposal and additions as strikeable lines.

## 5. Checking it

Before the skill decides a review's questions, it is run blind on every in-person ruling of the log (`Blind
before` that ruling, `Corpus at` the parent of the commit that applied it, or HEAD when not applied). Every
disagreement in the choice, and every addition that contradicts the ruling, is shown to the owner before the
review continues.
