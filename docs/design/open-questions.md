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

### C3. Waiting on repo setup
- **(a) Recommended:** `repo_add` returns immediately, then the agent repeats
  `repo_wait` with `timeout_s: 50` (under Codex's ~60 s tool timeout); each call
  returns the current checklist.
- **(b)** `repo_add` blocks for the whole setup with progress notifications.
- **Cost if wrong:** (b) breaks on client tool timeouts, and progress-notification
  support is unverified. (a) costs a few extra calls per setup.

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

### E1. May the LLM run tools directly while diagnosing a failure?
You approved this earlier (diagnosis only; only `omc run` can pass a job). Since
then you set the rule that everything that runs is managed by watch. They conflict.
- **(a) Recommended:** keep direct runs for short diagnostic probes only (e.g. one
  test with `-vv`), explicitly exempt from the watch rule; the job still passes
  only through `omc run`.
- **(b)** No direct runs: every probe is an `omc run … --test <selector>` job.
- **Cost if wrong:** (b) makes probes slower and spends rounds on diagnosis unless
  probe jobs are made round-free. (a) lets probes bypass watch's locks and the
  E2E isolation.

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

## G. To verify (no decision, a check)

- Codex's shell-tool timeout, before `run.poll_wait_seconds: 100` is final.
- The Codex equivalent of Claude's `disable-model-invocation`.
- Whether Claude's `` !`cmd` `` preprocessing runs when the model invokes a skill
  through the Skill tool.

## H. Parked topics (not yet formulated as questions)

- **`respond`:** addressing MR review comments after publish.
- **`omc refresh`:** rebasing a worktree onto base mid-work (v1's `rebase-main`).
- **`/investigate`:** scope, now that the ops survey gives it data.
- **`omc resume`:** detect the lifecycle stage, recreate the worktree, re-enter.
- **`/explain`:** whether a user-facing explain skill exists outside the design
  lifecycle's `design:explain-context` hook.
- **Plugin locations:** where global and per-repo lifecycle plugins live in your
  omc repo.
- **Per-branch cache contents:** what remains in `~/.omc2/repos/<key>/branches/<branch-file>/`
  now that lifecycle working files live in `/tmp`.
- **Cross-repo features:** how one feature spans several repos (v1's multi-repo
  workspace design is the reference), rebuilt on watch.

## I. Review lifecycle (10-review-lifecycle.md)

### I1. How `code-review` works
- **(a) Recommended: the read-only findings machinery from hardening, under a
  `review:code-review` hook.** omc's default contributions: `grug` (v1's diff
  rules, behaviour-preserving fixes only) and `multi-agent-review` (one agent per
  changed area of the diff). Project contributions (e.g. hummingbird's coding
  convention and `hb-review` rules) join by name. Python checks after each hook
  that the worktree's tracked files are unchanged, and fails the skill if not. The
  plugin merges the findings, applies them, asks you only when in doubt, and writes
  waivers into `## Deliberate complexity`; round overview and the offer of another
  round, as in hardening.
- **(b)** One review pass with no hooks, as v1's `review` stage.
- **Cost if wrong:** (b) leaves project review rules nowhere to plug in. Without
  the worktree check, a "read-only" reviewer that edits code changes the branch
  unnoticed. (a) costs one agent per changed area per round.

### I2. What a deviation judgment produces
- **(a) Recommended:** each notable deviation becomes one entry
  `Deviation: <what differs> — <design/plan section> — <file:line>`, followed by
  a ruling in the implement ledger's format
  `Ruling: accepted|reverted|escalated — <why> — <cost if wrong>`. The agent first
  checks `<slug>-rulings.md`: a deviation an implement ruling already explains is
  accepted citing that ruling. *Accepted* leaves code and design as they are;
  *reverted* means the agent judged the deviation wrong and fixes the code;
  *escalated* is put to you, with options and a recommendation. All entries go to
  `<slug>-deviations.md`, committed next to the design (the approved design itself
  is never rewritten). "Notable" means it changes behaviour, an interface, a data
  shape, or a stated constraint; naming, file layout and internal structure are
  not notable.
- **(b)** Accepted deviations are written back into `<slug>.md` so the design
  matches the code.
- **(c)** Judgments stay in the session; only escalations reach you.
- **Cost if wrong:** (b) rewrites the design you approved and loses what was
  originally decided. (c) leaves no record of why the code differs from the
  design. (a) adds one file per design.

### I3. How the project's extra CI checks run in `publish-gate`
- **(a) Recommended:** each extra check is a watch job type declared in
  `repo.yaml` (`jobs: {<name>: {command: […], fix_hints: …}}`), run as
  `omc run <name>` with the same one-run-per-worktree rule, 1-hour limit, fix
  loop, round counter and `detect-failures` / `rerun-tests` snippets.
  `/auto-integrate` proposes them by reading the repo's CI configuration (GitLab
  CI, GitHub workflows) and validates each one in the scratch worktree. A
  `review:publish-gate` contribution names the jobs it adds.
- **(b)** Contributions are skill text that tells the LLM which commands to run
  in its shell.
- **Cost if wrong:** (b) breaks "everything that runs goes through watch": tool
  timeouts, no locks, no time limit, no round counting. (a) needs `/auto-integrate`
  to learn each CI job once.

### I4. Does `publish-gate` rerun a job that passed on the identical tree?
- **(a) Recommended: no.** watch records the git tree hash of every full pass;
  `publish-gate` skips a job whose last full pass was on the identical tree and
  says so in one line ("e2e-tests: passed on this exact tree at 14:02, skipped").
  Any change during review changes the tree, so everything affected reruns.
- **(b)** Always rerun every job.
- **Cost if wrong:** (b) spends a full E2E run (minutes, maybe an isolation slot)
  re-proving an identical tree when review changed nothing. (a) won't catch a
  flake that only fails on a second run; your rule is to debug flakes when they
  fail, not hunt for them.

### I5. `create-mr` details (next question group)
- Rebasing onto the latest base before `publish-gate`, so the gate runs on what
  is pushed.
- Opening the MR on the forge (with the session's forge tools) and the shape of
  the human-facing description.
- The ticket transition (e.g. → In Review).
- Whether a separate `publish` lifecycle remains, now that `create-mr` pushes.
