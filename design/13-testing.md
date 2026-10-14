# 13. Testing

v1 was thin on testing. v2 tests everything, end to end.

## 13.1 Design, E2E tests and features are one thing

- **Two protected folders** in this repo: `design/` (this high-level design) and
  `e2e-tests/`. An implementation change may not modify either.
- **`e2e-tests/` codifies the design.** If it isn't in `design/`, it can't be in
  `e2e-tests/`. If it isn't in `e2e-tests/`, it isn't a feature.
- **Every feature has E2E tests, and therefore a design artifact** in `design/`.
- `design/` holds the high-level design artifacts. Per-feature designs made by
  the design lifecycle (superpowers-based) live in `docs/design/`
  (`design_artifact_root: repository`, `design_artifact_directory: docs/design`).

## 13.2 The E2E tests

- **Everything** is tested end to end, except what is Kraken-related: multi-repo
  support, `omc watch` with multiple repos and checkouts, repo discovery in the
  middle of a design, and so on. If the design describes it, a test proves it.
- **Open source and non-internal only:** every test, fixture and dependency.
- **In Docker,** fast and lightweight, so many run in parallel.
- **The test repos** are four public GitHub repos forming a diamond dependency:

  ```
                 oh-my-clanker-test-repo-a
                  ↗                     ↖
  oh-my-clanker-test-repo-b-depends-on-a   oh-my-clanker-test-repo-c-depends-on-a
                  ↖                     ↗
          oh-my-clanker-test-repo-d-depends-on-c-and-b
  ```

  All four live under `github.com/chris-husse/` and were empty on 2026-10-14
  (public, issues enabled, no license yet).
- **Scenarios are branches** in those repos: each scenario sets up whatever state
  a test needs.
- Anything that can't be expressed with these four repos is reported, not worked
  around.
