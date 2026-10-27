---
name: explain-context
description: Where oh-my-clanker v2 keeps its truth - the design corpus, the E2E definitions, the rules, the workflows - and the order they take precedence.
---

# explain-context (this repo)

This repository is a design, not yet a product: `docs/` is the deliverable and `tools/` keeps it honest.
Most authoritative first:

1. **`docs/design/`**, the corpus. `README.md` is its index (chapter table, MVP scope, naming);
   `01-principles.md` to `14-cross-repo-features.md` are the design; `open-questions.md` holds everything
   undecided, with its options. What the design says is here and nowhere else.
2. **`docs/e2e-tests/`**, the E2E definitions (Markdown only, one per test), once it exists. Changes
   together with the corpus; the code derived from it lives in `tests/e2e/`.
3. **The rules:** `AGENTS.md` (protected folders, generated files, the rollout), `docs/index.md` (what
   `docs/` holds), `docs/LINKS.md` (every reference is a link, its form, pins), `tools/corpus.yaml`
   (which files are corpus, history, generated, excluded).
4. **`.claude/skills/`**, the workflows: `record-decision`, `apply-decision`, `review-design`,
   `validate-design`, `how-we-got-here`, `reconcile-links`, `ensure-up-to-date`; `decision-log` (the
   entry format) and `design-review-conventions` (shared rules) are read by path, not invoked.
5. **`docs/superpowers/`**, this repository's own specs and plans for the tools. Never corpus, never
   read by the design agents. For "why does the tool do that", the record of intent; the code still wins.

Conventions worth knowing: `omc` in the design means v2 (installs as `omc2` until cutover); "your omc
repo" and "the state repo" are the same thing; every reference in `docs/` is a relative Markdown link
with `%20` for spaces and `%60` for backticks in anchors, and no link leaves `docs/`; a file written
under `docs/` outside `tools/corpus.yaml`'s `exclude` list is link-checked by `just links-check`.
