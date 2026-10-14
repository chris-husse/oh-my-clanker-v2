# 13. Testing

v1 was thin on testing. v2 tests everything, end to end.

## 13.1 The product design workflow

A critical workflow fork of omc v2, **off by default**, for new projects
developed from the ground up this way (this repo is the first, as a prototype).

- **The rules:**
  - two protected folders: `design/` (the high-level design) and `e2e-tests/`;
    an implementation change may not modify either;
  - `e2e-tests/` codifies the design: if it isn't in `design/`, it can't be in
    `e2e-tests/`; if it isn't in `e2e-tests/`, it isn't a feature;
  - every feature has E2E tests, and therefore a design artifact in `design/`;
  - every E2E test points clearly to the design facts it exercises.
- `design/` holds the high-level design artifacts. Per-feature designs made by
  the design lifecycle (superpowers-based) live in `docs/design/`
  (`design_artifact_root: repository`, `design_artifact_directory: docs/design`).
- **Enabled in `omc configure`:** *Use product design workflow: Enabled |
  Disabled*.
- **When enabled, omc imports the rules** into the design, planning and review
  steps, through a `<match>` on the flag, so agents can't break them by accident.
  For now that is the whole harness: rules in the skills, no Python enforcement.
  Later the exact flow gets baked into lifecycles and plugins.
- **Coverage must be reviewable:** that each E2E test covers specific design
  artifacts, and, eventually, that every design artifact has an E2E test.

### The flow for this repo (prototype)

1. Iterate on the design in `design/`.
2. Build the Jira tasks that implement the design.
3. Harden each task: does it actually work, roughly in that order, and what can
   run in parallel.
4. Each task adds E2E tests, each pointing clearly to the design facts it
   exercises.

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
