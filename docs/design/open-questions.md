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

## C. MCP tools (reopened: an earlier "ok" was wrongly taken as approval)

### C1. How `docs_grep` searches
- **(a) Recommended:** ripgrep run by watch with typed parameters only (`pattern`,
  `glob`, `ignore_case`, `context` 0–5, `files_only`); omc builds the argv, no shell.
- **(b)** Pass rg/ugrep arguments through ("use the same arguments as that tool").
- **(c)** Return root paths and let the agent grep with its own tool.
- **Cost if wrong:** (b) allows arbitrary code execution via rg `--pre` / ugrep
  `--filter` (LLM arguments are untrusted under prompt injection). (c) exposes cache
  and hidden-clone paths that sessions could then edit, triggers permission prompts,
  and loses the docs lock and output cap.

### C2. Search engine
- **(a) Recommended:** ripgrep (installed, 15.2.0; the engine behind Claude Code's Grep).
- **(b)** ugrep (`ug`), not installed here; its extras wouldn't be exposed by typed
  parameters anyway.
- **Cost if wrong:** small; behind typed parameters the engine can be swapped.

### C4. GitNexus tool granularity
- **(a) Recommended:** one `gitnexus` tool with `verb` ∈ `query|context|impact|cypher`.
- **(b)** Four tools.
- **Cost if wrong:** (b) puts three more tool schemas into every turn's context,
  against the astra budget.

## D. watch

### D1. Use GitNexus's own `gitnexus watch` for scheduling?
- **(a) Recommended: no.** omc needs per-piece locks, setup states, trust,
  `/auto-integrate` before build, and fail-fast messages; `gitnexus watch` runs its
  own pid/mutex files under `GITNEXUS_HOME` and only allows github.com, gitlab.com
  and gitee.com remotes unless allowlisted.
- **(b)** omc drives `gitnexus watch` and builds around it.
- **Cost if wrong:** (a) keeps a scheduler omc arguably could have reused. (b)
  coordinates two watch processes with separate locks: the hidden GitNexus state
  that drove most of v1's churn.

### D2. Does `/auto-index` generate the GitNexus wiki?
- **(a) Recommended: no.** It indexes, detects doc paths, and runs the context and
  ops surveys. The wiki stays opt-in per repo (`documentation: false`) and follows
  the interval and daily-check rules.
- **(b)** Yes, an initial wiki for every repo at setup.
- **Cost if wrong:** (b) adds a large LLM docs run to every repo a design discovers
  (v1's funds-rs wiki was ~277 pages). (a) leaves `docs_grep` with only the repo's
  own docs plus the surveys until you turn the wiki on.

## E. Run jobs

### E2. Does `omc run` use the same `--poll` form as `add-repo`?
Long operations share one pattern: a job ID, then a poll (01-principles.md).
`omc run` was specified as `omc run <type> --job-id <id> status|logs|stop`.
- **(a) Recommended:** align it: `omc run <type> --poll <job-id>` replaces
  `--job-id <id> status` (long-polls `run.poll_wait_seconds`); `logs` and `stop`
  stay as `omc run <type> --job-id <id> logs|stop`.
- **(b)** Keep `--job-id <id> status` for run jobs.
- **Cost if wrong:** (b) gives agents two spellings for the same thing. (a) is a
  rename before anything is built, so it costs nothing now.

## F. Skill rendering

### F1. A fact error when the `<match>` has no `<error>` branch
Decided earlier: nothing is inlined and the error is logged. Since then you set
fail-loud as a rule.
- **(a) Recommended:** keep it. Authors who need errors handled write an `<error>`
  branch; omc's own skill text always does.
- **(b)** Fail the whole skill, like a failing hook.
- **Cost if wrong:** (a) can silently drop a block when a fact breaks in a hook file
  without an `<error>` branch. (b) turns every fact hiccup in a hand-written hook
  into an aborted skill.

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
