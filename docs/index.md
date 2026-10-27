# The design folder

`docs/` is this repository's design folder: Markdown and the images its pages embed. Its link rules are
[LINKS.md](LINKS.md); `tools/corpus.yaml` declares which of its files are corpus, history, generated or excluded.

- **High-level design** (`design/`, [omc v2 design](design/README.md)): the corpus. The numbered documents and the open questions;
  its README is the design's own index and naming. Protected: it changes only through a recorded ruling.
- **E2E test definitions** (`e2e-tests/`): Markdown only, one definition per test or scenario, when they appear.
  Corpus, protected, and changed together with the design.
- **[The decision log](decision-log.md)**: the rulings. Every decision about the corpus, recorded and applied
  through `just decisions`; never edited by hand.
- **[Design reviews](reviews/README.md)** (`reviews/`): every set of comments the design received, and the
  iterations of its review cycle. History, never corpus.
- **Specs and plans** (`superpowers/`): this repository's own working specs and implementation plans. Never corpus,
  never history, never read by the design agents.
