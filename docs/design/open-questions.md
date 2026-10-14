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

## I. Publish lifecycle (11-publish-lifecycle.md)

### I1. The pipeline for creating the MR, and where the rebase goes
- **(a) Recommended: a `rebase` plugin first in both review and publish.**

  ```yaml
  review:  [rebase, deviation-analysis, code-review, ci-gate]
  publish: [rebase, ci-gate, create-mr]
  ```

  Python (`omc internal rebase`) fetches and rebases the branch onto its base
  (`origin/<base>`, or the parent branch named in session memory, I3); on
  conflicts, the LLM resolves them and Python verifies none remain, else you are
  asked. When the branch is already on the latest base it is a no-op, the tree is
  unchanged, and publish's `ci-gate` skips every job (identical tree). If the base
  moved since review, the rebased tree is gated again before anything is pushed.
  The same command serves the parked `omc refresh`.
- **(b)** Rebase only in publish (`publish: [rebase, ci-gate, create-mr]`);
  review runs against the base the worktree was cut from.
- **(c)** No rebase; the forge merges with the base.
- **Cost if wrong:** (b) reviews against a stale base, so the deviation analysis
  and code review miss interactions with newer base changes. (c) pushes a branch
  that may conflict or break on the current base, found only on the MR. (a) costs
  one mostly no-op plugin in each lifecycle.

### I3. A stacked branch when its parent changes or merges
The base comes from session memory (12-session-memory.md), not from a record made
at design time.
- **(a) Recommended:** the plugin passes the base it read from memory to Python
  explicitly (`omc internal rebase --base <branch>`); Python checks the branch
  exists. Python keeps the parent tip it last rebased onto in the branch's cache
  folder and rebases with `git rebase --onto <parent's new tip> <last parent
  tip>`, because the parent's own squash rewrites its commits. Once the parent is
  merged, the base is the repo's `base` again (the same `--onto`) and `create-mr`
  retargets the MR there.
- **(b)** A plain `git rebase <parent>`; you fix duplicates by hand.
- **Cost if wrong:** (b) replays the parent's unsquashed commits onto its squashed
  commit after every parent squash: conflicts or duplicated changes in the child
  MR. (a) keeps one piece of git state per branch, written only by Python.

### I5. The ticket at MR time
- **(a) Recommended:** move the primary ticket to an "In Review"-type status with
  the session's tracker tools; nothing else, as with `ticket-start`. Skipped when
  the design has no `Primary:` line; a failure is stated in the output and the
  summary, and the plugin continues.
- **(b)** Also add the MR link as a ticket comment.
- **(c)** Don't touch the ticket.
- **Cost if wrong:** (b) adds a write omc refused at `ticket-start` (comments are
  noise when the forge already links MRs to tickets by key). (c) leaves the ticket
  "In Progress" while the MR waits for review.

### I6. Incorporating MR review comments (next question group)
- How publish is re-entered once comments arrive, how comments are triaged, and
  how a change goes again through design, review, `ci-gate` and push.

## J. Session memory (12-session-memory.md)

### J1. OptMem or omc's own store
OptMem's repository has **no license** (GitHub reports none), so by default all
rights are reserved: omc may not copy or ship its code. It installs with
`curl … | sh` into `~/.optmem/`, is one Python 3 file with no dependencies, and was
last pushed 2026-07-31.
- **(a) Recommended: omc's own minimal store, borrowing OptMem's format.** One
  file per branch, append-only, one memory per line (≤ 280 bytes), each with a
  timestamp. Injection prints it verbatim. No summary tree: a branch's memory is
  a few dozen lines.
- **(b)** Use an installed OptMem with `$MEMORY_DIR` pointing at the branch
  folder; the prerequisite checks it is installed, as for superpowers.
- **(c)** Ask the author for a license first, then vendor it.
- **Cost if wrong:** (b) makes every user run an unpinned `curl | sh`, and its
  `note` can stop mid-skill to ask the model for summary merges ("nap"). (a) loses
  OptMem's summaries and recall if a branch's memory ever grows to hundreds of
  lines.

### J2. Who adds memories
- **(a) Recommended:** you, with `omc memory add` in a shell, and the session's
  main agent when you state a standing instruction for the branch in the
  conversation: it runs `omc memory add` with your words and says so in one line.
  Subagents never write memories (OptMem's own rule).
- **(b)** Only you, by command.
- **(c)** The agent too, for anything it learns (OptMem's model).
- **Cost if wrong:** (b) loses everything you say in conversation unless you
  retype it as a command. (c) fills the memory with the agent's own notes, which
  then steer every later skill. (a) depends on the agent spotting a standing
  instruction; the one-line confirmation shows you when it did.

### J3. Where memory is injected
- **(a) Recommended: into every rendered skill for the branch** (every lifecycle
  plugin, fix skill and user-facing skill run in that worktree), as a
  `## Session memory` block right after the stub's header. Python renders it; an
  empty memory renders nothing.
- **(b)** Only into lifecycle orchestrator skills.
- **Cost if wrong:** (b) lets a fix skill or `create-mr` miss "target branch X".
  (a) adds the memory's size to every skill's context.
