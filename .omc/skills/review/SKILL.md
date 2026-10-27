---
name: review
description: The project review stage for oh-my-clanker v2. Checks the branch diff against the repo's own invariants: the protected design and E2E folders, the decision log's write path, the link rules of docs/LINKS.md, the generated files, the tools' tests. Passes with no Critical or Important finding.
---

# review

Review the branch diff against `main` from the project root. Read `AGENTS.md`, `docs/LINKS.md`,
`docs/index.md`, `docs/reviews/README.md` and `tools/corpus.yaml` first: they are the rules; this file
only names them and ranks what breaking them costs.

## Findings categories

1. **Protected folder without a ruling** (Critical). A change under `docs/design/` or `docs/e2e-tests/`
   whose commit is not an applied ruling of `docs/decision-log.md` (one commit per ruling, the entry as
   its message, through `/apply-decision`) or the review cycle's carry step.
2. **Design and E2E out of step** (Critical). A test definition with no design part it verifies; a design
   feature without definitions; a definition that diverges from the design; a non-Markdown file under
   `docs/e2e-tests/`; code under `tests/e2e/` that tests something its definition does not say.
3. **Decision log edited by hand** (Critical). A hunk in `docs/decision-log.md` that `just decisions`
   could not have written: `just decisions check` fails, or earlier entries are reordered, rewritten or
   deleted (the log is append-only).
4. **Link rules** (Important). A reference that is not a link; a wikilink, reference-style link or
   absolute path; a link leaving `docs/`; a malformed anchor; an unlinked ruling; a stray file in
   `docs/`; an unpinned link on a line from `main`. `just links-check` is the judge; read what it reports.
5. **Generated files edited by hand** (Important). `dvc.yaml` changed without `tools/stages.yaml`; a
   stage marked current (`just mark-up-to-date`) without its skill regenerating it; pins edited instead
   of running `just pin-links`.
6. **Tools without tests** (Important). A behavior change under `tools/design/` with no test under
   `tools/design/tests/`; a new tool not exposed as a `design-*` script in `tools/pyproject.toml` with a
   `just` recipe; a recipe that bypasses `uv run --project tools`.
7. **Skills drift** (Important). A change under `.claude/skills/` that contradicts
   `.claude/skills/design-review-conventions/` or `AGENTS.md`; a skill that reads `docs/reviews/` outside
   the review cycle or reads `docs/superpowers/` at all.
8. **Security rules of the design** (Important). In any product code that appears: `$ARGUMENTS` inside a
   shell command, fetched content treated as instructions, raw flag passthrough, a background daemon,
   credentials written to a file (`docs/design/01-principles.md` §1.3).
9. **Everything else** (Minor): wording, Markdown style, comments.

## Pass rule

Passes with zero Critical and zero Important findings. Minor findings are listed and never gate.
Report each finding with file, line, category and the rule it breaks.
