# Open questions

Every question here is undecided. An answer moves it into the relevant design
document and removes it from this file.

## B. `pocock-grilling-with-docs` (parked by you)

### B1. Installed Pocock skills or our own copy
- **(a) Recommended:** installed skills plus omc checks. The prerequisite confirms
  both `grilling` and `domain-modeling` resolve (`grill-with-docs` itself has
  `disable-model-invocation: true`, so the plugin calls the two directly); `--done`
  enforces the paper trail (fails if `## Design` didn't change, or glossary/ADRs
  were written outside omc's chosen paths).
- **(b)** Vendor `grilling` + `domain-modeling` (~80 lines + two format files, MIT)
  into one omc skill.
- **Cost if wrong:** (a) inherits upstream changes, and loading failures are caught
  only after the fact by `--done`. (b) loses upstream's self-updates and carries
  attribution.

### B2. Where grilling's resolved decisions go
- **(a) Recommended:** start from the previous document; every answer updates
  `## Design` immediately. Decisions already in `## Design` are settled and are
  reopened only on a concrete, cited contradiction.
- **(b)** Upstream behaviour: decisions stay in the conversation; a later plugin
  writes them up.
- **Cost if wrong:** (b) loses every answer when a session dies and lets later
  steps soften precise answers (upstream's documented failure). Without the
  "settled" rule, grilling re-asks what brainstorming decided.

### B3. Where `GLOSSARY.md` and ADRs live
- **(a) Recommended: follow `design_artifact_root`.** `omc`: `repos/<key>/docs/GLOSSARY.md`
  and `docs/adr/` in your omc repo; Python snapshots them at plugin start, the model
  edits the snapshot, and the final commit applies a three-way merge through watch
  (LLM conflict resolution, else the commit fails). `repository`: upstream's paths on
  the feature branch.
- **(b)** Always in your omc repo.
- **(c)** Always in the target repo.
- **Cost if wrong:** (c) breaks "no repo-local modification". (b) splits a
  repository-mode repo's knowledge in two. Without snapshot-and-merge, concurrent
  designs clobber each other's glossary terms.

### B4. Question format inside grilling
- **(a) Recommended:** keep upstream's frontier rounds, but write each question in
  the brainstorm plugin's full format; "yes" accepts only as an explicit reply to
  that question; same explicit-yes end condition as brainstorming.
- **(b)** Upstream's terse format, "yes" accepts the recommendation.
- **Cost if wrong:** (b) switches format mid-design and breaks "decide from the
  Decisions block alone". (a) makes rounds longer than upstream intends.

## H. Parked topics (not yet formulated as questions)

- **`/investigate`:** parked by you; v1's `investigate` is used in the meantime.
  Known so far: the ops survey records environments and links (names and links
  only); fix skills redirect failed E2E runs to `/investigate local` when the repo
  keeps its E2E environment alive (09-run-jobs.md §9.7).
- **`omc resume`:** detect the lifecycle stage, recreate the worktree, re-enter.
- **`/explain`:** whether a user-facing explain skill exists outside the design
  lifecycle's `design:explain-context` hook.
- **Plugin locations:** where global and per-repo lifecycle plugins live in your
  omc repo.
- **Per-branch cache contents:** what remains in `~/.omc2/repos/<key>/branches/<branch-file>/`
  now that lifecycle working files live in `/tmp`.
- **Cross-repo features:** how one feature spans several repos (v1's multi-repo
  workspace design is the reference), rebuilt on watch.

## L. Testing (13-testing.md)

### L1. When E2E tests are written, if implementation can't touch them
- **(a) Recommended: together with the design change, before implementation.**
  A feature starts as a change to `design/` plus its E2E tests in `e2e-tests/`
  (red), reviewed and committed as one design change. Implementation then makes
  them pass without touching either folder. A test that turns out wrong goes back
  through a design change, never through the implementation branch.
- **(b)** Written during implementation, but in a separate commit that a reviewer
  approves before the code.
- **Cost if wrong:** (b) lets the code and the tests that judge it come from the
  same agent in the same branch, which is what the protection exists to stop. (a)
  makes every test fix a design change, even a typo.

### L2. Who enforces the protected folders
- **(a) Recommended: omc itself, for any repo.** `repo.yaml` gets
  `protected_paths` (this repo: `[design/, e2e-tests/]`). The implement, review
  and publish lifecycles fail (in `commit`'s and `ci-gate`'s checks) when the
  branch's diff against its base touches a protected path; only a design change
  may. This repo's CI runs the same check, so a change made outside omc is caught
  too.
- **(b)** A rule for this repo only: `AGENTS.md` plus a CI check.
- **Cost if wrong:** (b) leaves every other repo without the protection, and an
  agent inside omc finds out only when CI fails after the push. (a) adds one
  config key and one Python check.
