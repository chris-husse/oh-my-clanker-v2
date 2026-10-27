---
name: check
description: The fast gate for oh-my-clanker v2: the design tools' unit tests and the decision log's integrity check. About 15 seconds, no LLM. No link check, no freshness check, no E2E (those are build and verify).
---

# check

Run every command from the project root. The stage passes when every command exits 0.

1. `uv run --project tools pytest tools/design/tests -q`
   The design tools' tests (decision log, links, pins, freshness, folder, pre-push hook, skeleton). About 11 s;
   `uv` builds `tools/.venv/` on the first run.
2. `just decisions check`
   The decision log's integrity: section and ruling format, numbering, status lines. Prints `OK`.

Not here: `just links-check` and `just ensure-up-to-date` are the `build` stage. There are no E2E tests yet;
`tests/e2e/` appears with the first definition in `docs/e2e-tests/`, and then belongs to `verify`.

On failure, name the first failing command and quote its last lines in the summary.
