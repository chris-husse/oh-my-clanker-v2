# oh-my-clanker v2: project rules

## Protected folders: `docs/design/` and `docs/e2e-tests/`

- `docs/design/` holds the high-level design. `docs/e2e-tests/` holds the E2E test
  definitions. Both are **protected**: change either only with the user's
  explicit approval. That holds during implementation too.
- **What the user approves is the nature of the change, never code:** what the
  test or design part covers, why it is needed, and which part of the design it
  verifies.
- **`docs/e2e-tests/` contains only Markdown:** one definition per test or scenario.
  The test code is derived from those definitions and lives in `tests/e2e/`.
  Test code is not protected, but it implements its definition and nothing more.
  If the code needs to test something different, the definition changes first,
  and that change needs approval.
- **The design and the E2E tests change together:**
  - no test definition without a part of `docs/design/` that it verifies;
  - no feature in `docs/design/` without test definitions;
  - no definition that diverges from the design.
  A change to one that affects the other is proposed as one change, for one
  approval.
- Per-feature designs made by the design lifecycle live in `docs/features/` and
  are not protected.

In this framework the user's explicit approval of a change to the protected
folders is a recorded ruling in `docs/decision-log.md`. An agent edits the
protected folders only through `/apply-decision` (one commit per ruling, the
entry as its message) or through the review cycle's carry step.

## Generated files and the decision log

- Generated files are always current: `just ensure-up-to-date` checks them,
  `/ensure-up-to-date` regenerates what is stale, and the pre-push hook refuses a
  stale push (`just install-hooks`, once per clone).
- `docs/decision-log.md` is written only through `just decisions`: record with
  `/record-decision`, apply with `/apply-decision <id>`, ask with
  `/how-we-got-here`. Never edit it by hand.

## Rollout, in this order

Merge the branch that brings the link pins and the pre-push hook. Then, on `main`: `git pull` (`just pin-links` pins
to `origin/main`), `just pin-links`, commit (`Links: pinned`) and push. Only then run `just install-hooks` in each
clone. Installed earlier, the hook refuses every push until the pins are committed, and until then `just build` on
`main` fails with `unpinned`.
