# oh-my-clanker v2: project rules

## Protected folders: `design/` and `e2e-tests/`

- `design/` holds the high-level design. `e2e-tests/` holds the E2E test
  definitions. Both are **protected**: change either only with the user's
  explicit approval. That holds during implementation too.
- **What the user approves is the nature of the change, never code:** what the
  test or design part covers, why it is needed, and which part of the design it
  verifies.
- **`e2e-tests/` contains only Markdown:** one definition per test or scenario.
  The test code is derived from those definitions and lives in `tests/e2e/`.
  Test code is not protected, but it implements its definition and nothing more.
  If the code needs to test something different, the definition changes first,
  and that change needs approval.
- **The design and the E2E tests change together:**
  - no test definition without a part of `design/` that it verifies;
  - no feature in `design/` without test definitions;
  - no definition that diverges from the design.
  A change to one that affects the other is proposed as one change, for one
  approval.
- Per-feature designs made by the design lifecycle live in `docs/design/` and
  are not protected.
