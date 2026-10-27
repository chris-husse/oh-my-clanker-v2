# oh-my-clanker v2: project agent instructions for omc lifecycles

Read after omc's global behavior layer. The project's rules are the root `AGENTS.md` (protected folders,
the decision log, generated files, the rollout); this file adds what omc's lifecycles need on top.
Deeper truth map: `.omc/skills/explain-context/SKILL.md`.

## What this repo is

A design, not yet a product. `docs/design/` is the deliverable, `docs/decision-log.md` its rulings,
`tools/` the Python that keeps both honest (`just` recipes over `uv run --project tools`). The v2 code
does not exist yet; when it starts, the design's rules in `docs/design/01-principles.md` §1.2 and §1.3
apply to it.

## Protected folders inside an omc lifecycle

- `/omc:implement` and `/omc:audit` workers never edit `docs/design/`, `docs/e2e-tests/` or
  `docs/decision-log.md`. A needed change there is a question to the owner, answered through
  `/record-decision` and applied through `/apply-decision`; it is never folded into a feature branch.
- Per-feature design records go to `docs/features/` (not protected). Everything under `docs/` is checked by
  `just links-check` unless `tools/corpus.yaml` excludes it: write such records with the link rules of
  `docs/LINKS.md`, or exclude the folder there first.
- `dvc.yaml` and `docs/LINKS.md` pins are generated: `tools/stages.yaml`, `/ensure-up-to-date` and
  `just pin-links` are the only ways to change them.

## Stages

- `/omc:check`: the tools' tests and the decision log's integrity, about 15 s. Run it constantly.
- `/omc:build`: the link check and the generated-file check, about 5 s, no tests.
- `/omc:verify`: unconfigured until the first `docs/e2e-tests/` definition exists.
- `/omc:review`: the invariants above as finding categories; zero Critical or Important findings pass.
- The pre-push hook (`just install-hooks`, once per clone) refuses a push with stale generated files or
  unpinned links from `main`. A red `just links-check` with only `unpinned` problems means the rollout step
  in the root `AGENTS.md` is pending: `just pin-links`, commit `Links: pinned`.

## Reading the design

- Start from `docs/design/README.md`; `open-questions.md` is what is still undecided.
- A `recorded` ruling not yet `applied` overrides the corpus text it affects.
- `docs/reviews/` is history; read it only in a review cycle. `docs/superpowers/` is this repo's own tooling
  record; the design agents never read it.
