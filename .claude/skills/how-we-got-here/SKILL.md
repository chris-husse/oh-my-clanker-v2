---
name: how-we-got-here
description: "Answer a \"how did we get here\" question about the design (\"why is trust a user-only command?\", \"why are sub-designs made from the main repo?\") - find the design sections, E2E definitions and rulings the question is about, pull their decision chains with `just decisions`, read the rulings and follow the later ones that changed them, consult the design documents and the git history where the log leaves a gap, and answer with the history that led to today's design. Not \"what is it\" (that is /omc:explain); \"how did it come to be\". Commits nothing, edits nothing."
---

# How we got here

Argument: a question in the owner's words. The owner already knows what the design says today; they want to know
how it came to say it: the original idea, what changed it, why, and what is left of each step. Every command starts
from `ROOT=$(git rev-parse --show-toplevel)`.

## 1. Find what the question is about

The question names a topic, not a reference. Turn it into references:

- The design sections and E2E definitions that carry the topic today: read `docs/design/README.md` (the documents
  and what each covers), then the headings of the corpus,
  `(cd "$ROOT" && git ls-files -co --exclude-standard -- 'docs/design/*.md' 'docs/e2e-tests/*.md' | xargs grep -n '^##')` (the corpus is what
  `tools/corpus.yaml` lists under `corpus`), and read the candidates. A trust question lands on
  `design/02-repos-and-config.md#2.6 Trust`.
- Rulings that name the topic in their text:
  `(cd "$ROOT" && just decisions search --text '(?i)<word>' --oneline)`. Try the corpus words and their older names;
  `git log -S '<word>' -- docs/design` shows when a word came or went.

Keep every reference that carries the topic. Prefer too many over too few; the next step sorts them out.

## 2. Pull the chains

For every reference: `(cd "$ROOT" && just decisions history "<ref>")` with `<ref>` a heading
(`design/02-repos-and-config.md#2.6 Trust`), a whole document (`design/14-cross-repo-features.md`), a ruling (`1.2`)
or a section of the log (`§1`). Merge the outputs into one list of rulings in log order; the ids are the log's order.
`just decisions search --affected <path-prefix> --oneline` lists the rulings that touched a whole group of files.

`history` lists the rulings that touch the reference, and under a ruling `later: <ids>`: later rulings that may have
changed it, nearly always in part. A `later:` line is a lead, not a verdict. Follow it: run `history` on a later
ruling that brings in a new strand of the topic. A section pointer (`§N`) leads to a whole section of the log
(`just decisions history §N` and the section's header in `docs/decision-log.md`).

## 3. Read and untangle

Read the rulings in full, in log order (`just decisions show <id> …`, several at once). For every `later:` pointer,
read both rulings and decide what the later one actually changed, or that it only cites the earlier one. Never take
the pointer's word for it.

Read provenance from `Automated`: true is automated, false is human-recorded. Missing means
legacy/unspecified; the historical sentence `Decided automatically by the review session`
indicates legacy automation, but its absence alone does not prove a human decision. Inspect
the source before attributing a legacy ruling. Automated rulings were bulk-accepted by the owner
from proposals and carry less weight: one may supersede an automated ruling, never a human or
legacy one, and it never overrides a human decision because it is newer. Report such a conflict
explicitly. Distinguish recorded from applied.

Where the log is not enough, go further:

- the design documents as they stood at a ruling's date:
  `git log --follow --format='%h %ad %s' --date=short -- docs/design/<file>.md` (`--follow` crosses the move from
  the old root `design/`), `git show <commit>:<path at that commit>`;
- the commit that carried a ruling into the corpus (`git log -S '<phrase>' -- docs/design docs/e2e-tests`), whose
  diff shows what it changed;
- the review files that a ruling's `Answers:` line or `**Source.**` names (`docs/reviews/`), for what was asked.

## 4. Answer

To the conversation, and to `"$ROOT/.cache/how-we-got-here/<slug of the question>.md"` (`ROOT=$(git rev-parse
--show-toplevel); mkdir -p "$ROOT/.cache/how-we-got-here"`; `.cache/` is gitignored, so this edits nothing tracked):

- **The answer first**, in a few sentences: why the design has this, in the owner's terms.
- **The thesis.** The first ruling, or the earliest version of the design section, that set the idea out, quoted.
- **The steps.** One short paragraph per ruling that changed the idea, in order: id, date, what it changed and why,
  the decisive sentence quoted. Rulings that only cite or repeat stay out.
- **Where it stands.** What is left after every step, in the corpus's own words, and the section that says it today.
- **Gaps found.** A later ruling that changed an earlier one without a `Supersedes` pointer between them, or a corpus
  section that lags the chain: quote both. These are findings for the owner (`/record-decision` can mark them); this
  skill fixes nothing.

Nothing is committed and no document changes.
