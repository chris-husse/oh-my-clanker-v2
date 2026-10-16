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

## L. Testing: the product design workflow (13-testing.md §13.1) — parked, not MVP

Parked by you on 2026-10-16: the product design workflow is not part of the MVP.

### L1. Where the setting lives
- **(a) Recommended: per repo,** `product_design_workflow: false` in `repo.yaml`
  (written with its default), shown in `omc configure`'s Repositories section as
  *Use product design workflow*. The `<match "<repo>:product_design_workflow">`
  fact reads it.
- **(b)** Global, in shared config, for every repo.
- **Cost if wrong:** (b) turns the workflow on for existing repos that weren't
  built this way, or off for the new ones. (a) has to be set per new project.

### L2. Which steps get the rules
- **(a) Recommended: design, planning, review, and implement.** You named design,
  planning and review; implement is where an agent would modify `design/` or
  `e2e-tests/` by accident, so its plugins (`superpowers-subagent-build`, the fix
  skills, `commit`) get the protected-folder rule too.
- **(b)** Design, planning and review only.
- **Cost if wrong:** with (b), the rule reaches the implementer only through the
  plan's text, and review catches a violation after the fact. (a) adds a short
  block to implement's skills when the flag is on.

### L3. When you approve the nature of an E2E change
- **(a) Recommended: up front in the plan, and mid-task only for surprises.** With
  the workflow on, `write-implementation-plan` lists for each task the E2E tests it
  adds or changes, in spirit form: what it tests, why it is needed, which design
  facts it verifies, plus any `design/` change in tandem. Your yes at
  `approve-design` approves those. During implementation, a test or design change
  that isn't in the plan stops the task with one question in the same form; review
  checks each E2E change in the diff against the plan's approved list.
- **(b)** Ask at each change, whenever it happens.
- **Cost if wrong:** (b) interrupts implementation, which otherwise runs without
  check-ins, for every planned test. With (a), a change that slips past the
  mid-task stop is caught only in review.

### L4. How E2E tests point to design facts
- **(a) Recommended: a stable ID per design fact,** written visibly at the end of
  the statement in `design/`, e.g. `` `F:run.one-per-worktree` ``. IDs are names,
  not section numbers, so renumbering never breaks them. Each test declares what
  it covers (`@covers("run.one-per-worktree")` or the test framework's
  equivalent).
- **(b)** Point to section numbers (`09-run-jobs.md §9.3`).
- **(c)** A separate registry (`design/facts.yaml`) mapping IDs to sections.
- **Cost if wrong:** (b) breaks every pointer when sections move, and a section
  holds several facts. (c) drifts from the prose it describes. (a) adds an ID to
  every normative statement in `design/`.

### L5. The coverage check
- **(a) Recommended:** a script in `e2e-tests/` that lists design facts with no
  test, tests with no fact, and tests citing an unknown fact. This repo's CI fails
  on the last two now; facts without tests are only reported until you make full
  coverage a gate.
- **(b)** Manual review only.
- **Cost if wrong:** (b) can't answer "does every design artifact have a test"
  without reading everything. (a) needs the fact IDs from L4.
