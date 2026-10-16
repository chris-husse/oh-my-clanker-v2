# Decision log

Every open design question, asked one at a time, with your answer. Sources: the adversarial design review (`docs/reviews/2026-10-16-adversarial-design-review.md`, refs R1–R93) and the open E2E questions (E1–E3). Each answer is also written into `design/` in the same turn.

**Status: 0 of 96 answered.**

## Q1 (R1, blocker): MVP scope of multi-repo work

**Status:** open

**Where:** 01-principles.md §1.1, README.md §MVP, open-questions.md §H Cross-repo features, 13-testing.md §13.2, 04-mcp-and-cli.md §4.3, 05-skill-rendering.md §5.3 omc:is_multi_repo

**Problem:** §1.1 says a feature can span several repos with full integration, and 13.2 requires E2E tests of multi-repo work on a four-repo diamond. But open-questions §H parks cross-repo features, and the README leaves §H out of the MVP. Every lifecycle structure is keyed by one repo plus one branch: the lifecycle folder, the artifact root, session memory, one Primary ticket, one MR. The tests can't be written, and if one feature later touches several repos, all of those keys have to be redone.

**Question:** Is MVP multi-repo limited to watching many repos and adding or querying them mid-design, with each feature still changing exactly one repo?

- (a) Yes: multi-repo watch, repo_add mid-design and gitnexus/docs_grep across repos. Changing several repos in one feature stays parked. Reword §1.1 and scope 13.2 to match.
- (b) Unpark cross-repo features and design them before building.
- (c) Option (a), but key lifecycle, artifact and memory paths by a feature id now so multi-repo can be added later without migrating.

**Recommendation:** (a). The read-only multi-repo parts are already designed. Choose (c) only if cross-repo changes are expected right after the MVP.

**Cost if wrong:** E2E tests can't be written for a feature that isn't designed, and re-keying every per-branch path later means a migration.

**Answer:** —

**Recorded in:** —

## Q2 (R2, blocker): The agent can run the user-only gates: trust, trust --all, reset-rounds, configure

**Status:** open

**Where:** 01-principles.md §1.2 CLI = MCP, §1.3 no auth, 02-repos-and-config.md §2.6, 04-mcp-and-cli.md §4.1, §4.2, §4.6, 05-skill-rendering.md §5.2 allowed-tools Bash(omc …), §5.7, 08-implement-lifecycle.md §8.4, 03-watch.md §3.4

**Problem:** Trust grants code execution, and reset-rounds is what makes the fix loop's CRITICAL stop bounded. Under the 'CLI = MCP and vice versa' rule both become MCP tools on an endpoint with no authentication. The stub's `allowed-tools: Bash(omc …)` also pre-approves them as shell commands. The add-repo poll even prints the exact trust command for the agent. A prompt-injected agent, any local process or another local user can trust an attacker repo and run its code, or reset the fix budget. Frontmatter user-only flags don't help: they only block the Skill tool, not a direct `omc lifecycle publish` from Bash.

**Question:** Which commands are user-only, and what enforces that?

- (a) A named user-only list (repo trust, trust --all, reset-rounds, configure writes, uninstall) carved out of CLI=MCP. These are never MCP tools and refuse to run without an interactive TTY and a typed confirmation. Stubs allow-list exact subcommands, not `omc …`. Lifecycle entry (implement, review, publish) is gated by Python checks on state.
- (b) The commands exist, but trust and reset take effect only after a native dialog that watch raises.
- (c) Accept and document the risk.

**Recommendation:** (a). Also add a per-start secret in a 0600 file that the CLI presents, so other local processes can't drive watch.

**Cost if wrong:** The trust gate and the bounded fix loop can be bypassed with one tool call, and a malicious repo gets code execution.

**Answer:** —

**Recorded in:** —

## Q3 (R3, blocker): Who writes and locks the omc repo: configure/update run without watch, but only watch may write

**Status:** open

**Where:** 02-repos-and-config.md §2.3 Writes, §2.5 omc configure/update, 04-mcp-and-cli.md §4.2, 03-watch.md §3.5 omc repo piece, §3.3, 05-skill-rendering.md §5.5 temp-dir works without watch

**Problem:** §2.3 says watch makes every write to the omc repo, and §3.5 lists configure writes under watch's in-process 'omc repo' lock. But §4.2 says configure and update run without watch. A configure or update commit can then land in the middle of watch's per-tick fetch, rebase --autostash and LLM conflict resolution. An in-process lock can't serialize a separate process. The same gap covers local renders that read the omc repo while it is half-rebased, writes by `omc repo trust`, and concurrent writes to local config.

**Question:** Are the omc-repo and local-config locks cross-process file locks that every omc process takes, or does every write go through watch?

- (a) A filelock under the omc repo's .git (and one for local config) that watch's sync, commits, configure, update and rendering all take. Writes are atomic (temp file then rename).
- (b) Local config is written locally. Shared and repo.yaml writes go only through a watch MCP tool; without watch those sections are read-only, except for the first bootstrap.
- (c) configure and update always need watch.

**Recommendation:** (a). filelock is already a dependency, the lock becomes real across processes, and configure keeps working offline. Reword §2.3 to 'omc serializes every write'.

**Cost if wrong:** A corrupted rebase, edits swept into an autostash, renders that read conflict markers, and trust grants lost to overlapping write-backs.

**Answer:** —

**Recorded in:** —

## Q4 (R4, blocker): Writing every key's default into repo.yaml disables the shared config layer and freezes old defaults

**Status:** open

**Where:** 01-principles.md §1.2 No hidden config, 02-repos-and-config.md §2.5 split, omc update, 06-lifecycles.md §6.1, 04-mcp-and-cli.md §4.3 repo_add creates repo.yaml, 03-watch.md §3.2

**Problem:** repo.yaml overrides the shared config.yaml, and 'every key is written with its default'. If repo_add writes branch_prefix, design_artifact_root, the hook switches and the plugin lists into each repo.yaml, the shared values never take effect. Plugin lists copied at creation also never pick up omc's new defaults, and a renamed plugin breaks them. Hand-made repo.yaml files that lack keys have no defined behaviour.

**Question:** Which keys does each layer contain, and how does a changed omc default reach configs that already exist?

- (a) Each key is written only in the layer that owns its default. repo.yaml holds only repo-specific keys plus explicit overrides, and anything missing inherits from the shared file. Plugin lists are written as the sentinel `default`, which resolves to omc's current list.
- (b) Write every key everywhere and drop the shared layer for those keys.
- (c) Write every key but mark untouched defaults so update can refresh them.

**Recommendation:** (a). Restate §1.2 as 'every key exists in exactly one file of its layer chain'. omc configure shows inherited values and where they come from.

**Cost if wrong:** Editing shared config silently changes nothing, and fixes to defaults never reach existing users.

**Answer:** —

**Recorded in:** —

## Q5 (R5, blocker): Publish has no way to re-enter the design lifecycle for a feedback round

**Status:** open

**Where:** 11-publish-lifecycle.md §11.2, 06-lifecycles.md §6.2, §6.3, 07-design-lifecycle.md §7.1, §7.4, §7.7, §7.8, 08-implement-lifecycle.md §8.1, §8.3, 10-review-lifecycle.md §10.1

**Problem:** triage-comments is plugin 1 of 2, yet it has to hand over to design at superpowers-brainstorm, while §6.3 allows handoff only after the last plugin and `--done` always prints the next plugin. The design temp folder was deleted at approve-design, so `--from` has no document to start from, and `omc design` refuses an existing branch. Nothing turns brainstorm's classification into skipping hardening or jumping to create-mr. Every plugin hard-codes `<slug>.md` and `<slug>-plan.md`, so a feedback round overwrites the approved design. Implement's design-artifact then finds the original plan and rebuilds it, and a second round overwrites `<slug>-rulings.md`. Who allocates `<n>` is also unstated.

**Question:** What is the entry, naming and routing contract for a feedback design round?

- (a) Add `omc lifecycle design --feedback <n>`. Python allocates n (one plus the highest committed), builds a fresh temp folder with seed.md (the comments seed) and the committed design as read-only context, marks explain-seed done, and closes publish. A `{{doc}}` variable replaces the hard-coded `<slug>` names. Brainstorm writes a parsed `Classification: full|short|no-code` line that `--done` uses to skip or exit. design-artifact returns the newest feedback plan, and rulings go to per-round files.
- (b) Make feedback its own lifecycle with its own pipeline and artifact contract.
- (c) Append feedback sections to the original files.

**Recommendation:** (a). (c) breaks the rule that the approved design is never rewritten.

**Cost if wrong:** The core publish loop can't be built. Approved designs get overwritten, or implement rebuilds the original plan.

**Answer:** —

**Recorded in:** —

## Q6 (R6, blocker): Comment threads already answered are re-triaged on every publish, so replies loop or post twice

**Status:** open

**Where:** 11-publish-lifecycle.md §11.2, §11.3 step 5, §11.5, 11-publish-lifecycle.md §11.1

**Problem:** Replies are posted only by create-mr at the end of the next publish run. That run starts with triage-comments, which still sees the same threads unresolved (omc never resolves a thread), so it sends them back to brainstorming without end. Nothing records which threads have been decided or replied to, so a retry after a partial failure posts duplicate public replies. Top-level comments have no resolved state at all.

**Question:** How does triage tell new threads from ones a committed feedback design already decided or answered?

- (a) Python keeps a per-branch ledger: thread id, round n, decision, reply URL and last comment id seen. It is built from the committed `Thread <id>:` lines. A thread is seeded only if it has no entry or has reviewer activity after omc's reply. create-mr posts only pending replies and records each URL as it goes.
- (b) The LLM checks each thread on the forge for an existing omc reply.
- (c) Post replies at triage time.

**Recommendation:** (a). It is deterministic and makes posting idempotent. Define a triageable unit as a resolvable thread plus top-level comments newer than omc's last MR-level reply.

**Cost if wrong:** Publish never reaches create-mr, or reviewers get duplicate automatic replies.

**Answer:** —

**Recorded in:** —

## Q7 (R7, blocker): The on-disk shape of a plugin's output: file or folder, where the plan goes, which folder gets committed

**Status:** open

**Where:** 06-lifecycles.md §6.1, §6.2, §6.3, §6.5, §6.6, 07-design-lifecycle.md §7.6, §7.7, §7.8

**Problem:** §6.2 has each plugin write `design/<plugin>/<slug>.md`. design-hardening writes a folder `design/design-hardening/<slug>/`. The plan goes to '<slug>/<slug>-plan.md inside the design folder' without saying whose folder. approve-design takes 'the folder'. As a result `--done` doesn't know what to check, `--from` doesn't know what the 'current document' is, §6.5 doesn't know which folder to hash (findings written inside it would fail every hook), and the copy step doesn't know its source. Sub-documents from earlier plugins are left behind or end up as links that escape the folder, which check-artifact rejects after approval.

**Question:** What fixed layout does every design plugin write, and how do sub-documents move forward?

- (a) Every plugin writes `design/<plugin>/<slug>/`, holding `<slug>.md`, sub-documents and later the plan. Python copies the previous folder in at plugin start. Work files go to `design/<plugin>/work/`, outside the hashed set. The final folder is what gets committed.
- (b) Keep one file per plugin, and have approve-design assemble the folder and rewrite links.
- (c) Use one shared working folder, with Python snapshots for --from.

**Recommendation:** (a). Also run check-artifact's link checks at every `--done`, so a broken link fails at the plugin that made it.

**Cost if wrong:** Implementations disagree on paths, hooks fail on their own findings files, and sub-documents are lost at commit.

**Answer:** —

**Recorded in:** —

## Q8 (R8, blocker): TDD's expected red runs enter the fix loop and use up rounds, and nothing says when the counter resets

**Status:** open

**Where:** 09-run-jobs.md §9.2, §9.4, 07-design-lifecycle.md §7.7, 08-implement-lifecycle.md §8.3, §8.4, 10-review-lifecycle.md §10.5

**Problem:** Every TDD task first runs `omc run check --test` expecting failure. Under §9.4 that red run starts the fix skill, which is told to 'fix the cause', and every run after a failure counts against max_rounds 6. The only reset named is reset-rounds after a CRITICAL. Check failures from all tasks, milestone-gate and ci-gate therefore add up, and a normal multi-task plan reaches CRITICAL. Whether a `--test` pass counts as a pass, and whether it triggers the 'failed first, then full' rerun, is unstated.

**Question:** Do `--test` runs take part in the fix loop, and when does the round counter reset?

- (a) `--test` runs only report results: no fix skill, no rounds, no recorded pass. Only full runs enter the loop. A full pass resets the counter for that worktree and job type.
- (b) Add an `--expect-fail` flag that inverts the verdict for red steps.
- (c) Give each plugin invocation its own budget.

**Recommendation:** (a), stated in §9.4 and §7.7.

**Cost if wrong:** Healthy builds stop at CRITICAL, or the fix skill quietly removes newly written tests.

**Answer:** —

**Recorded in:** —

## Q9 (R9, blocker): The output cap and harness limits truncate rendered skills and JSON results

**Status:** open

**Where:** 04-mcp-and-cli.md §4.2, §4.5, 05-skill-rendering.md §5.2, §5.6, 06-lifecycles.md §6.3, 09-run-jobs.md §9.2, 01-principles.md §1.2 Fail loud

**Problem:** Every tool result is cut at 20000 characters with 'Narrow the request'. A rendered plugin (plugin text, several hooks of up to 8000 characters each, plus memory) can exceed that, and every `--done` output also passes through Claude's Bash output limit and Codex's exec truncation. The model then follows half a skill, often without the `--done` line, although §5.6 forbids exactly that. Cutting the poll JSON produces invalid JSON at the moment a job has failed. §1.2 says oversize output fails the skill while §4.5 says it is truncated.

**Question:** Which outputs may be truncated, and what happens when a rendered skill or a JSON verdict is too big?

- (a) Rendered skills and JSON verdicts are never cut. A total render budget, set below the smallest harness limit, renders an ABORT that lists the largest contributors. JSON tools cap their own lists (first N plus a total plus a spillover file). The truncating cap applies only to data results.
- (b) Use one cap for everything, with overflow becoming an ABORT for renders.
- (c) Write large renders to a file and print 'read it in full'.

**Recommendation:** (a). Truncation is acceptable for data the model can ask for in pieces, never for instructions or verdicts that tools parse.

**Cost if wrong:** Skills that half apply, and fix loops broken by unparseable JSON.

**Answer:** —

**Recorded in:** —

## Q10 (R10, blocker): Executable hooks run once at render time, so they can't serve per-section, per-round or per-hook checks

**Status:** open

**Where:** 05-skill-rendering.md §5.5, 06-lifecycles.md §6.3, §6.4, §6.5, 07-design-lifecycle.md §7.6, 10-review-lifecycle.md §10.4

**Problem:** An executable contribution runs when the plugin is rendered, before any section, round or design-explained.md exists, and its output stays fixed for every later round. Because all contributions are inlined as one block of text, Python never gets control between hooks, so 'hash after each hook' and 'validate findings after each hook' can't happen. The design has no command or construct for calling a hook. An executable's findings also have no path that Python knows to validate.

**Question:** When does a hook contribution run, and how does Python get control between contributions?

- (a) Hooks are invoked on demand: the plugin text runs `omc internal run-hook <lifecycle>:<hook> --input <file>` at each call site. Python runs the executables with that input, gives each contribution a known findings path, and hash-checks and validates after each one.
- (b) Executables only for hooks whose input exists at render time; findings hooks are markdown only, with one check at --done.
- (c) Each inlined contribution is followed by `omc internal hook-check <name>`.

**Recommendation:** (a). It is the only option that delivers §6.5's per-hook guarantees and per-round inputs. Define it next to `<match>` in 05.

**Cost if wrong:** Hardening and code review can't enforce read-only behaviour or validate findings as designed.

**Answer:** —

**Recorded in:** —

## Q11 (R11, blocker): No contract for keep-alive E2E: how the verdict is reported and how watch tears the environment down

**Status:** open

**Where:** 09-run-jobs.md §9.2, §9.3, §9.7, 03-watch.md §3.4, §3.6, 08-implement-lifecycle.md §8.4

**Problem:** To stay up after a failure, the environment's process has to keep running, so watch never gets an exit code and the job stays 'running' until it is terminated. Environments made of containers or detached services are not in the job's process tree, so 'kill the process tree' leaves ports and containers running across runs and restarts. That leads to port conflicts the fix skill chases for nothing. No teardown hook is named, and nothing says how /auto-integrate validates one.

**Question:** What is the watch-to-repo contract for keep-alive E2E?

- (a) The suite command exits with the verdict and may leave declared resources running. A required teardown executable in stages/e2e-tests/ is run by watch on pass, at the time limit, on the next run, and at watch start for environments that were left over. /auto-integrate sets keep_alive only after validating up, verdict and teardown.
- (b) A verdict file written by a long-running process.
- (c) Drop keep-alive from the MVP.

**Recommendation:** (a), with label-based container cleanup as a safety net, and §9.3's 'stays up' made conditional on keep_alive.

**Cost if wrong:** Leaked environments and endless false failures. Keep-alive repos also never report 'failed'.

**Answer:** —

**Recorded in:** —

## Q12 (R12, blocker): GitNexus has no vetting entry and is under PolyForm Noncommercial

**Status:** open

**Where:** 01-principles.md §1.4, §1.1, 03-watch.md §3.5, §3.6, 04-mcp-and-cli.md §4.3

**Problem:** The whole architecture depends on GitNexus (indexing, queries, atomic rebuilds traced to a fork commit), but §1.4 does not list it. Nothing records the fork or commit pin, the license (v1's copy reads PolyForm Noncommercial 1.0.0, which may forbid use on employer repos), the Node prerequisite, or whether omc may build it on its own (§1.3 says no unsupervised installs).

**Question:** Is GitNexus (which fork and commit) approved for the intended use, and how is it installed and updated?

- (a) Add it to §1.4 with a pinned fork commit, written license clearance and Node as a stated prerequisite. omc builds it into ~/.omc2/dependencies only from the approved source.
- (b) Treat it as a user-installed tool: omc checks the version and prints the install command.
- (c) Replace it if the license can't be cleared.

**Recommendation:** (a), but only once the license question has a written answer.

**Cost if wrong:** Building on a dependency that may not be usable for the work it is meant for.

**Answer:** —

**Recorded in:** —

## Q13 (R13, blocker): Naming before cutover: the v2 binary is omc2, but stubs, text and slash commands say omc and collide with v1

**Status:** open

**Where:** README.md §Naming, 01-principles.md §1.5, 05-skill-rendering.md §5.2, 07-design-lifecycle.md §7.8, 08-implement-lifecycle.md §8.1, 10-review-lifecycle.md §10.1, 11-publish-lifecycle.md §11.1, 09-run-jobs.md §9.8

**Problem:** The stub `!omc lifecycle design` runs v1's omc, which has no lifecycle verb, so it exits non-zero and Claude aborts the skill load. Every printed command (trust, memory add, run) and every `allowed-tools` pattern also reaches v1. The `/omc:implement` and `/omc:review` that v2 tells the user to type are v1's installed skills, with different contracts. v2's plugin name is never given. User hooks, facts and committed plans hard-code the name, so cutover breaks them.

**Question:** How is the program and plugin name rendered before and after cutover?

- (a) One constant (omc2, and plugin omc2) feeds the stubs, allowed-tools, all messages and the `{{omc}}`/`{{omc_plugin}}` variables in skill text. User executables get OMC_BIN. A render test rejects a bare `omc `. An omc2 shim stays for one release after cutover.
- (b) Hard-code omc2 now and run a search-and-replace at cutover.
- (c) Uninstall v1 first.

**Recommendation:** (a).

**Cost if wrong:** Every v2 skill fails to load, or v1's implement and review run on v2 branches.

**Answer:** —

**Recorded in:** —

## Q14 (R14, blocker): ~/.omc2 is called rebuildable, but it holds unpushed branches, config, trust and memory

**Status:** open

**Where:** 02-repos-and-config.md §2.2, §2.4, §2.3 Removing a repo, 03-watch.md §3.6, 09-run-jobs.md §9.4, 10-review-lifecycle.md §10.2, 12-session-memory.md §12.1

**Problem:** Worktrees are linked worktrees of the hidden clone, so every local branch and unpushed commit lives in clone/.git, and the claim that 'the path is never handed to a session' is false because git exposes it. ~/.omc2 also holds local config, trusted_repos, job state, round counters, pass tree hashes, stacked-branch parent tips and session memory, none of which can be rebuilt. Deleting the cache to fix a problem, or removing a repo, destroys all of it.

**Question:** Which parts of ~/.omc2 are state that must persist, and what protects local branches?

- (a) Split the home into ~/.omc2/state (config, jobs, rounds, hashes, parent tips, sessions) and ~/.omc2/cache (GitNexus stores, docs, logs). Hidden clones are documented as state that holds branch work. Clone removal refuses while any local branch has commits not on origin.
- (b) One tree with a documented list of what is state and what is cache, plus the same refusal.
- (c) Give each worktree its own clone so the cache really can be rebuilt.

**Recommendation:** (a).

**Cost if wrong:** Silent loss of unpushed work, trust grants and session memory.

**Answer:** —

**Recorded in:** —

## Q15 (R15, blocker): No format for what a job type actually runs

**Status:** open

**Where:** 09-run-jobs.md §9.2, §9.4, §9.5, 02-repos-and-config.md §2.3 layout, §2.5, 03-watch.md §3.4

**Problem:** Nothing defines where the steps of check, e2e-tests and ci live: their commands as argv, cwd, env, which steps are test steps tied to snippets, or the setup that runs first. The 'build hook' that §3.4 records fixes into is not a hook type. 'Failed step', fail-fast reruns and the per-step snippet layout all depend on this. Two snippet pairs for one job type also collide under `stages/<job-type>/`.

**Question:** Where, and in what format, is each job type's step list defined?

- (a) `stages/<job-type>/job.yaml`: an ordered list of steps {name, argv, cwd, env, test_step}, with snippets under `stages/<job-type>/<step>/`, plus a `setup:` list in repo.yaml. Written by /auto-integrate and editable by hand.
- (b) Executable step scripts run in order.
- (c) Sections in repo.yaml.

**Recommendation:** (a). Drop the 'build hook' wording.

**Cost if wrong:** The runner, /auto-integrate and the fix skill can't be written in a compatible way.

**Answer:** —

**Recorded in:** —

## Q16 (R16, blocker): Retrying failed setup: watch restarts strand repos, and omc's own commits retrigger setup

**Status:** open

**Where:** 03-watch.md §3.2, §3.4, §3.6, 02-repos-and-config.md §2.6, 09-run-jobs.md §9.5, §9.6, 04-mcp-and-cli.md §4.6, 07-design-lifecycle.md §7.3

**Problem:** A watch restart marks in-flight clone, index or integrate jobs failed. That isn't an 'input change', so the repo stays failed until origin moves, and network errors and LLM outages are treated the same way. In the other direction, a failing /auto-integrate files a suggestion-box entry into repos/<key>/, and that counts as an edit to the folder, so setup retries forever. No command exists to retry setup on purpose.

**Question:** What counts as a setup input, and how do interrupted, transient or user-requested retries work?

- (a) Fingerprint the inputs: the origin SHA plus a hash of repo.yaml, hooks/ and facts/, never suggestion-box/, docs/ or stages/. Setup interrupted by a restart is requeued at start. Transient failures retry with backoff a capped number of times. Add `omc repo <repo> retry-setup`.
- (b) Count only commits not authored by omc.
- (c) Keep it as written.

**Recommendation:** (a). Optionally add a `queryable (no graph)` degraded state for repos GitNexus can't parse.

**Cost if wrong:** Repos stuck for weeks, or LLM setup re-running in an endless loop.

**Answer:** —

**Recorded in:** —

## Q17 (R17, blocker): /auto-integrate can't run builds through watch, and E2E isolation deadlocks it

**Status:** open

**Where:** 03-watch.md §3.4, §3.6, 01-principles.md §1.2, 09-run-jobs.md §9.2, §9.3, §9.5

**Problem:** `omc run` refuses until a repo is integrated, so /auto-integrate's LLM has to run builds, baselines, injections, E2E and ci as direct tool calls. Those hit the timeouts §1.2 exists to avoid and sit outside the job limit and isolation. With isolate_e2e_execution, its E2E step waits for every running job to finish, including the /auto-integrate job itself. The design also doesn't say whether the 60-minute limit covers the whole integration.

**Question:** How does /auto-integrate run code under watch's limits?

- (a) Internal scratch-mode run jobs that need trust but not integration. Each one follows the normal limits and isolation, and the parent releases its slot while it waits. /auto-integrate as a whole has no wall-clock limit, and each validation run gets the normal per-run limit.
- (b) Treat the whole integration as one isolated job.
- (c) Python drives validation and the LLM only edits between runs.

**Recommendation:** (a), with (c) as the direction to grow in.

**Cost if wrong:** A deadlock on isolated repos and timed-out builds on large repos.

**Answer:** —

**Recorded in:** —

## Q18 (R18, blocker): A branch's base exists only as free-text memory, yet squash, diff and verify need a fixed value

**Status:** open

**Where:** 12-session-memory.md §12.1, 10-review-lifecycle.md §10.1, §10.2, 11-publish-lifecycle.md §11.3, §11.5, 08-implement-lifecycle.md §8.5, open-questions.md §H Per-branch cache contents, 07-design-lifecycle.md §7.1

**Problem:** Only rebase turns the memory prose into a branch name. Squash, the commit-over-base check, the fallback verification and the diff scope for review all read 'the base' on their own. A stacked branch then gets the parent's commits squashed in and reviewed as its own. If squash uses a freshly fetched origin/<base> after the base has moved, it silently reverts upstream work. The parent tip that `--onto` needs sits in the parked per-branch cache. A stacked branch is also still cut from origin/<base>, so design and implement run against code without the parent's changes.

**Question:** Where is the resolved base recorded for every Python step?

- (a) rebase (or `omc internal set-base`, which the LLM runs when you state a target) writes {base_ref, base_sha, parent_tip}, as a ref such as refs/omc/base/<branch> or a branch-cache file. Every base consumer reads only that. Setting a new base rebases immediately.
- (b) Every base-dependent command takes a required --base from the LLM.
- (c) Record the base when the worktree is cut, and let memory only override it explicitly.

**Recommendation:** (a). Squash onto the recorded base_sha, never onto a freshly fetched tip.

**Cost if wrong:** Stacked MRs fold in the parent's code, and a moved base gets silently reverted in the squash.

**Answer:** —

**Recorded in:** —

## Q19 (R19, blocker): omc-repo sync stashes and rewrites the user's uncommitted edits, with an LLM conflict resolver

**Status:** open

**Where:** 03-watch.md §3.3, 02-repos-and-config.md §2.3 Ownership, 03-watch.md §3.5

**Problem:** Every tick runs rebase --autostash and lets a headless LLM merge into the user's uncommitted edits, which §2.3 says are off-limits. If re-applying the stash conflicts, `rebase --abort` can't restore it, and the backup ref records only HEAD. Sync also aborts the user's own in-progress rebase or merge, rebases on a detached HEAD or a personal branch, re-runs the LLM on every tick for an unchanged conflict, writes a backup ref every tick (about 86k refs a month), and holds the lock while the LLM works, which blocks renders.

**Question:** When may sync touch the working tree, and who resolves conflicts?

- (a) Sync only on a clean tree on the configured branch with an upstream and no git operation in progress; otherwise skip with one line. Resolve commit-versus-commit conflicts in a scratch worktree, never in executables, then fast-forward. Retry only when (HEAD, upstream, tree) changes. Write a backup ref only before HEAD moves.
- (b) Keep autostash, but never let the LLM touch stashed content.
- (c) Keep as written and amend §2.3.

**Recommendation:** (a).

**Cost if wrong:** Lost or mangled user edits, and an unbounded LLM spend.

**Answer:** —

**Recorded in:** —

## Q20 (R20, blocker): Configurable pipelines can drop required plugins and gates, and the documented example is invalid

**Status:** open

**Where:** 06-lifecycles.md §6.1, §6.6, 07-design-lifecycle.md §7.2, §7.8, 08-implement-lifecycle.md §8.1, 01-principles.md §1.2 No bypass, 10-review-lifecycle.md §10.1, 11-publish-lifecycle.md §11.1

**Problem:** The §6.1 example `[explain-seed, pocock-grilling-with-docs, approve-design]` has no plan, so approve-design can't commit and implement ABORTs. It also names a parked plugin. Removing ci-gate or emptying review lets publish push ungated code. Commit is tied to the plugin named approve-design. Nothing validates a list or says what an unknown plugin name does, and lists are read live, so they can change mid-lifecycle.

**Question:** How are pipelines validated, and which steps can't be removed?

- (a) Python validates each list at render time, failing with an ABORT on an unknown name or a broken requires/provides chain. Copy and commit is the lifecycle's closing step. Lifecycle entry preconditions (committed artifact, clean branch, gate pass on the current tree) are Python checks and not configurable. The resolved list is snapshotted at start. Fix the §6.1 example.
- (b) No validation; fail downstream.
- (c) Make approve-design and the gates fixed tail plugins.

**Recommendation:** (a). Also state that MVP lists may name only omc-shipped plugins until plugin locations are decided.

**Cost if wrong:** A valid-looking config publishes ungated code or never commits a design.

**Answer:** —

**Recorded in:** —

## Q21 (R21, blocker): This repo's coverage rule in AGENTS.md vs §13.0, and how a design decision can be recorded

**Status:** open

**Where:** 13-testing.md §13.0, AGENTS.md, open-questions.md header, README.md

**Problem:** AGENTS.md (which agents follow) says 'no feature in design/ without test definitions'. e2e-tests/ doesn't exist, so the whole design already breaks the rule, and AGENTS.md itself isn't protected. §13.0 restates the rule differently: tandem change is unconditional there and conditional in AGENTS.md. Recording an answered question in design/ (open-questions.md included) needs one tandem proposal with test definitions, which a pure design decision can't produce. Approvals leave no record.

**Question:** Which text governs, does coverage apply only from now on, and how are design-only decisions approved?

- (a) AGENTS.md is authoritative and becomes protected, and §13.0 points to it. Coverage applies to features added or changed from now on, and existing ones are backfilled. Your answer approves the design edit, and the matching definitions (or 'none affected') follow for a separate yes. README.md and open-questions.md are exempt. Each approval is recorded as a commit trailer.
- (b) Gate coverage only once e2e-tests/ is bootstrapped.
- (c) Backfill everything first.

**Recommendation:** (a).

**Cost if wrong:** No design change can comply, or the governing rule drifts and can be weakened without anyone approving it.

**Answer:** —

**Recorded in:** —

## Q22 (E1, high): Which E2E tests use an LLM

**Status:** open

**Where:** 13-testing.md §13.0, §13.2

**Problem:** v1 ran every E2E test as a real Claude session judged by an LLM: minutes per test, flaky, token-heavy. Most of v2 is deterministic Python that needs no LLM to test.

**Question:** Which E2E tests run an agent?

- (a) Every definition declares a Kind; deterministic is the default (drive omc commands and MCP tools directly, check repo, files and output). Agent tests (real Claude or Codex) only where the design fact is about LLM behavior; they check state first and use an LLM judge only where state can't decide.
- (b) Every test runs an agent, as in v1.

**Recommendation:** (a).

**Cost if wrong:** (b) repeats v1's slow, flaky suite and defeats parallel runs; (a) tests LLM-dependent lifecycle parts less.

**Answer:** —

**Recorded in:** —

## Q23 (E2, high): The E2E definition format

**Status:** open

**Where:** 13-testing.md §13.0, AGENTS.md

**Problem:** e2e-tests/ holds only Markdown definitions, from which test code is derived. Without a fixed shape nothing can check that a definition names what it verifies or which scenario it uses.

**Question:** What shape does a definition have?

- (a) Fixed headings: `# <id>: <title>` (id = filename), Kind, Verifies (design sections), Why, Scenario (test repos + branches), Steps, Expected.
- (b) Free-form Markdown.

**Recommendation:** (a).

**Cost if wrong:** (b) makes approvals and checks depend on reading prose; (a) adds a little structure per file.

**Answer:** —

**Recorded in:** —

## Q24 (E3, high): How test code is derived and kept in line

**Status:** open

**Where:** 13-testing.md §13.0, AGENTS.md

**Problem:** Test code in tests/e2e/ must implement its definition and nothing more, but nothing ties a module to its definition.

**Question:** How are test modules tied to definitions?

- (a) One module per definition at tests/e2e/<id>.py; a quick check in `omc run check` fails on a definition without a module or a module without a definition; code review compares changed modules with their definitions.
- (b) Any layout; review alone keeps them matched.

**Recommendation:** (a).

**Cost if wrong:** (b) lets code drift from definitions unnoticed; (a) is one small script.

**Answer:** —

**Recorded in:** —

## Q25 (R22, high): The E2E fixture state that doesn't fit in four repos, and how scenarios are wired

**Status:** open

**Where:** 13-testing.md §13.2, 02-repos-and-config.md §2.2, §2.5, 06-lifecycles.md §6.6, 11-publish-lifecycle.md §11.2

**Problem:** Every scenario also needs an omc repo (repo.yaml, hooks, stages), local config, trust, committed design artifacts and MR comments. None of that is a branch in the four repos, yet 13.2 says anything not expressible there is 'reported, not worked around'. A scenario branch only takes effect if repo.yaml's base_branch points at it. The repos are empty, have no license, and their contents and dependency mechanism are undefined.

**Question:** Where does non-product scenario state come from, and what do the fixture repos contain?

- (a) A fifth fixture repo for the omc repo, with scenario branches. The harness generates local config and trust from each definition and sets base_branch: scenario/<name>, which is protected on the remote. A fixture spec in e2e-tests/ lists each repo's languages, CI, E2E, keep-alive hook and dependency mechanism. Add an OSI license.
- (b) Each definition declares its omc repo inline.
- (c) Restrict scenarios to repository mode.

**Recommendation:** (a). Narrow 'reported' to product-repo shapes the diamond can't express.

**Cost if wrong:** Test authors invent incompatible fixtures, or most tests can't be written.

**Answer:** —

**Recorded in:** —

## Q26 (R23, high): E2E environment: SSH-only identity, writes to a real forge, open-source-only rule, macOS features

**Status:** open

**Where:** 13-testing.md §13.2, 02-repos-and-config.md §2.1, §2.6, 04-mcp-and-cli.md §4.7, 11-publish-lifecycle.md §11.3, §11.4, 08-implement-lifecycle.md §8.2, 05-skill-rendering.md §5.2

**Problem:** GitHub has no anonymous SSH, so every parallel container needs a private key. Publish, MR, reply and ticket tests write to shared public repos with no isolation or cleanup, and LLM slug collisions hard-stop reruns. Claude-specific behaviour can only be proven with proprietary Claude Code and hosted models, which conflicts with 'open source only', and the credentials and cost are undefined. osascript and iTerm2 don't exist in Linux Docker. 'Except what is Kraken-related:' reads as if multi-repo is excluded.

**Question:** Which explicit exceptions and infrastructure does the E2E suite use?

- (a) A local SSH git server container with a throwaway key for all repo access. Forge-facing tests run against real GitHub with a per-run branch_prefix, teardown and serialisation. Harness CLIs and model APIs are named exceptions, credentials go in as Docker secrets, there is a budget cap, and a fake harness covers deterministic tests. The notifier and title use pluggable backends, recorded in tests. Reword the Kraken sentence and list the real exclusions.
- (b) A disposable Gitea forge.
- (c) Exclude these features from E2E.

**Recommendation:** (a).

**Cost if wrong:** Secrets in containers, polluted public repos, and features with no tests.

**Answer:** —

**Recorded in:** —

## Q27 (R24, high): How --headless supplies the explicit answers that every gate requires

**Status:** open

**Where:** 07-design-lifecycle.md §7.1, §7.4, §7.8, 06-lifecycles.md §6.5, 08-implement-lifecycle.md §8.2, §8.4, §8.5, 10-review-lifecycle.md §10.3, §10.4, 11-publish-lifecycle.md §11.4, 01-principles.md §1.2 Silence is not approval, 13-testing.md §13.2

**Problem:** --headless exists so the E2E suite can drive lifecycles, but every gate needs an explicit answer: move to hardening, another round, approve, takeover, CRITICAL, unplanned file, escalation, split. Auto-approving breaks 'silence is not approval', and stalling makes full-lifecycle tests impossible. CLI prompts (repo pick, find-repo, trust) also wait for input. No ABORT marker exists that a test can detect.

**Question:** What does a headless run do at a gate?

- (a) `--answers <file>` holds scripted answers keyed by stable gate ids, and an unmatched question fails loud with a distinct exit code. A test-actor model is used only for open-ended brainstorm turns. CLI prompts exit non-zero. ABORTs start with a fixed machine-readable marker.
- (b) A test-actor model answers everything.
- (c) Stop at the first gate.

**Recommendation:** (a). Rule out auto-approve explicitly.

**Cost if wrong:** Untestable lifecycles, or a bypass path built into the product.

**Answer:** —

**Recorded in:** —

## Q28 (R25, high): worktrunk `--yes` runs the repo's own hooks before trust, and doesn't pin the path or base

**Status:** open

**Where:** 02-repos-and-config.md §2.4 Worktrees, §2.6, 07-design-lifecycle.md §7.1 steps 4, 7, 04-mcp-and-cli.md §4.3

**Problem:** `wt switch --create --yes` auto-approves the product repo's .config/wt.toml post-create and post-start hooks, so repo code runs on a repo that is only queryable and not yet trusted, and post-start processes run in the background outside watch. Without --base, the branch is cut from wt's detected default branch. Without a pinned path template, the worktree lands next to the hidden clone or wherever the user's wt config says, not at `<worktree_location>/<key>/<slug>`.

**Question:** How does omc create worktrees?

- (a) Plain `git worktree add -b <branch> <path> <origin/base sha>` from Python. No hooks, no external tool.
- (b) Keep wt with --no-hooks, --base, an omc-owned --config, and no --yes.
- (c) Allow repo hooks after trust.

**Recommendation:** (a). Nothing from worktrunk is still needed, and it removes a prerequisite.

**Cost if wrong:** Code runs before trust, and worktrees appear at wrong paths or on wrong bases.

**Answer:** —

**Recorded in:** —

## Q29 (R26, high): Headless LLM sessions run with no permission model, and their output becomes instructions

**Status:** open

**Where:** 03-watch.md §3.3, §3.4, §3.7, 02-repos-and-config.md §2.6, 07-design-lifecycle.md §7.1 create-slug, find-repo, 01-principles.md §1.3, 05-skill-rendering.md §5.5

**Problem:** Pre-trust surveys, the daily freshness check, conflict resolution, create-slug and find-repo all read text an attacker can influence. A headless session started in the clone loads the repo's .claude/settings.json hooks, .mcp.json and AGENTS.md, and skips folder trust. The survey writes an explain-context hook contribution that is later inlined as instructions into every design. Nothing prevents /auto-integrate's LLM from running brew install, pip --user or curl | sh. The cwd, tools, model slot and output schema of these sessions are unspecified.

**Question:** What sandbox and output rules apply to each headless omc LLM call?

- (a) One headless-helper contract: an empty temp cwd, project settings, hooks and MCP disabled, a per-job tool allowlist (read-only before trust; scratch-worktree Bash with system-install deny rules for integrate), a named model slot, and strict JSON output. Survey output is stored as data and linked, never inlined as a contribution.
- (b) Move every LLM survey behind trust.
- (c) Accept the risk.

**Recommendation:** (a). Drop find-repo for the MVP. Add an E2E test with a malicious repo hook that must not fire.

**Cost if wrong:** Code runs before trust, and prompt injection persists into every later design.

**Answer:** —

**Recorded in:** —

## Q30 (R27, high): Trust doesn't cover the sessions omc launches, or harness folder trust

**Status:** open

**Where:** 02-repos-and-config.md §2.6, 07-design-lifecycle.md §7.1 step 9, 01-principles.md §1.2, 09-run-jobs.md §9.1

**Problem:** Trust covers watch jobs only. A session in an untrusted repo's worktree loads project hooks and settings (silently in headless mode), may run scripts directly for debugging, and every new worktree triggers the harness's own folder-trust prompt. Watch jobs also run code the agent has just edited with full user privileges outside the harness sandbox, and nobody has accepted that explicitly.

**Question:** How does omc trust map onto sessions and harness trust?

- (a) Launchers refuse an untrusted repo for implement, review and publish. Design sessions run with project settings disabled until trust. Trusting a repo marks its worktree_location in harness config. Running agent-edited code in watch jobs is documented in §1.3 as part of what trust means.
- (b) Trust covers watch only; document that.
- (c) Gate every launcher, design included.

**Recommendation:** (a).

**Cost if wrong:** Repo hooks run silently in sessions, and prompts appear for every worktree.

**Answer:** —

**Recorded in:** —

## Q31 (R28, high): Executables in the omc repo run without trust after auto-sync

**Status:** open

**Where:** 02-repos-and-config.md §2.2, §2.3, §2.6, 03-watch.md §3.3, 05-skill-rendering.md §5.3, §5.5, 09-run-jobs.md §9.5

**Problem:** Hooks, facts and snippets in the omc repo are executables. A teammate's push, a compromised remote or the LLM conflict resolver lands them in the working tree within one tick, and they run at the next render or job without anyone reviewing them. Trust also binds only to the folder key, so editing ssh_url points an already-trusted entry at different code.

**Question:** Do new or changed executables that arrive through sync need approval?

- (a) Declare the omc repo fully trusted and single-owner in §2.6, store trust as key plus canonical URL (a mismatch revokes it), and never let the resolver touch executables.
- (b) Approve executables by content hash, with renders aborting on anything unapproved.
- (c) Never auto-rebase.

**Recommendation:** (a) for the MVP. Add (b) before supporting team sharing.

**Cost if wrong:** Anyone who can push to your omc repo gets code execution on your machine.

**Answer:** —

**Recorded in:** —

## Q32 (R29, high): Untrusted text reaches rendered instructions through memory, stderr, error messages and fetched summaries

**Status:** open

**Where:** 01-principles.md §1.3, 12-session-memory.md §12.2, 05-skill-rendering.md §5.3, §5.4, §5.6, 07-design-lifecycle.md §7.3, §7.6, 09-run-jobs.md §9.4, 11-publish-lifecycle.md §11.2

**Problem:** §1.3 protects only hook STDOUT. Session memory is rendered verbatim into every skill and can hold paraphrased ticket or MR text. If it is templated, `{{x}}` or `<match>` in a memory breaks rendering or runs facts. ABORT inlines hook stderr, `{{error_message}}` inlines fact output, fix skills inline log excerpts, and the design doc carries ticket summaries and design-explained.md, all without any 'data, not instructions' framing. Nothing says whether substituted values are parsed again.

**Question:** How is text omc didn't write rendered?

- (a) Substitution is single-pass and never re-parsed. Memory goes after templating, in a labelled fenced block, and holds only the user's statements. stderr, error_message and log excerpts become data files or fenced one-line quotes with credentials redacted. The References and explain blocks get a data banner.
- (b) Inline everything inside fences.
- (c) Rely on the model.

**Recommendation:** (a). Extend §1.3 to cover anything omc renders that it did not author.

**Cost if wrong:** Prompt injection that persists across sessions and providers.

**Answer:** —

**Recorded in:** —

## Q33 (R30, high): Validating inputs: shell lines, git refs, selectors, docs paths, gitnexus args and cypher, the rg argv

**Status:** open

**Where:** 01-principles.md §1.3, 12-session-memory.md §12.2, 10-review-lifecycle.md §10.2, 09-run-jobs.md §9.2, §9.5, 04-mcp-and-cli.md §4.3, §4.4, 02-repos-and-config.md §2.1

**Problem:** `omc memory add "<text>"` puts user text into a double-quoted shell line. A base like `--exec=` or a selector like `-p` passes flags through. The selector grammar is undefined and may reach shell-building snippets. docs.paths (written by an LLM survey) can be `../..`, absolute or a symlink. gitnexus takes untyped args, and cypher can run LOAD FROM files. A pattern like `--pre=` becomes an rg flag unless it is passed as `-e`. User config from RIPGREP_CONFIG_PATH applies. SSH URLs from agents have no grammar, so a `-oProxyCommand` URL is possible.

**Question:** What validation and confinement does Python apply?

- (a) Free text only through stdin or a file. Refs checked with check-ref-format and passed after --end-of-options. Selectors rejected if they start with -, and snippets must use argv with no shell. docs paths canonicalised and confined, no symlinks followed. A typed schema per gitnexus verb, with cypher limited to a read-only allowlist (or dropped). rg run with -e, --no-config and no RIPGREP_* env. A strict SSH URL grammar, git called with --, and protocol.allow limited to ssh.
- (b) Leave it to the implementer.

**Recommendation:** (a), as a §1.3 rule with table tests.

**Cost if wrong:** Command execution or file disclosure through prompt injection.

**Answer:** —

**Recorded in:** —

## Q34 (R31, high): Credentials and PII committed into the omc repo

**Status:** open

**Where:** 01-principles.md §1.3, 09-run-jobs.md §9.4, §9.6, 03-watch.md §3.4, 06-lifecycles.md §6.6, 07-design-lifecycle.md §7.3

**Problem:** Suggestion-box entries embed log excerpts and 'both outputs' of flaky runs, setup gets recorded, and designs carry a verbatim seed and ticket summaries. Test and build logs routinely contain tokens, DSNs and PII. Only LLM goodwill keeps them out of a repo the user pushes, and policy forbids running Gitleaks locally. Git history also keeps them after the fix commit.

**Question:** How are secrets kept out of omc-repo commits?

- (a) One Python redaction and refusal filter on watch's write path and in check-artifact (token prefixes, user:pass@ URLs, PEM, AWS keys), failing loud. Committed entries carry only a summary, the test id and the job id, and full logs stay in the cache.
- (b) Prompt-only rule.
- (c) Don't commit the suggestion box.

**Recommendation:** (a).

**Cost if wrong:** Secrets pushed with git history that can't be cleaned up.

**Answer:** —

**Recorded in:** —

## Q35 (R32, high): --force-with-lease is defeated by background fetches, and lease rejections are 'resolved' by the LLM

**Status:** open

**Where:** 11-publish-lifecycle.md §11.3, §11.5, 02-repos-and-config.md §2.4, 03-watch.md §3.3, 10-review-lifecycle.md §10.2

**Problem:** Worktrees share refs with the hidden clone, which watch fetches every tick, so a bare lease always matches and silently overwrites a colleague's push. Post-push verification reads the same refs. A lease rejection is handed to the LLM fallback, which can only overwrite (forbidden) or integrate (which changes the tree, so verification fails). The 'never plain --force' rule can't be enforced while the LLM runs git itself.

**Question:** How does the push lease work, and who handles a rejection?

- (a) Python records the SHA it last pushed and pushes with --force-with-lease=<branch>:<sha>, verifying with ls-remote. A lease rejection stops and asks you, showing the foreign commits. The fallback only fixes causes (auth, hooks), and Python is the only thing that pushes.
- (b) Narrow the tick's refspec to base only.
- (c) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Teammates' commits are silently overwritten.

**Answer:** —

**Recorded in:** —

## Q36 (R33, high): Codex's MCP timeout (60 s) and sandbox vs omc's long polls and loopback CLI

**Status:** open

**Where:** 04-mcp-and-cli.md §4.1, §4.2, §4.3, 09-run-jobs.md §9.2, 05-skill-rendering.md §5.2, 06-lifecycles.md §6.2, 12-session-memory.md §12.2

**Problem:** repo_add_poll waits 60 s and run polls 100 s, against Codex's default 60 s tool_timeout_sec, which the registration doesn't set. Codex's default workspace-write sandbox has no network, so every CLI call to 127.0.0.1 fails, and writes to ~/.omc2 and /tmp/omc2 are denied. Claude prompts for writes outside the working directory. None of the launchers grant these paths. The CLI's own HTTP client timeout isn't specified either.

**Question:** How do omc's calls work inside each harness's default sandbox and timeouts?

- (a) `omc update` writes the Codex tool_timeout_sec above the longest wait, a loopback or command exemption for omc, and the writable roots. Launchers pass --add-dir with real paths. MCP-side waits stay under 45 s. check-watch probes from inside the session and fails loud with the setting to change.
- (b) Skills use MCP tools only for watch-backed operations.
- (c) Document that omc needs an unsandboxed session.

**Recommendation:** (a). Verify both harnesses in the first build.

**Cost if wrong:** omc fails on Codex by default in ways that are hard to diagnose.

**Answer:** —

**Recorded in:** —

## Q37 (R34, high): Watch's concurrency model: blocking FastMCP tools stall everything

**Status:** open

**Where:** 01-principles.md §1.4, 04-mcp-and-cli.md §4.1, §4.3, 09-run-jobs.md §9.2, 03-watch.md §3.5, §3.9

**Problem:** FastMCP calls sync tool functions directly on the event loop. A 100-second poll or a 30-second lock wait written as ordinary blocking Python freezes every other MCP call, the scheduler and the rich display, which shares the process. uvicorn's logging also writes to stderr and breaks the pinned display.

**Question:** What concurrency model does watch use?

- (a) One asyncio loop with all tools async, blocking work in to_thread or async subprocesses, a lint rule against sync tools, and uvicorn logging routed through rich with the access log off.
- (b) Server, scheduler and supervision in separate threads.
- (c) Sync tools in a bounded thread pool.

**Recommendation:** (a), plus a test that 10 concurrent long polls don't delay repo_list.

**Cost if wrong:** watch appears hung whenever agents poll.

**Answer:** —

**Recorded in:** —

## Q38 (R35, high): The CLI/MCP command and tool inventory is incomplete, and worktree identity isn't validated

**Status:** open

**Where:** 01-principles.md §1.2 CLI = MCP, 04-mcp-and-cli.md §4.2, §4.3, §4.6, 05-skill-rendering.md §5.3, 08-implement-lifecycle.md §8.4, 10-review-lifecycle.md §10.2, 11-publish-lifecycle.md §11.3, 12-session-memory.md §12.2, 09-run-jobs.md §9.2, §9.3

**Problem:** Only six MCP tools exist. run start, poll, logs and stop, memory add, facts, trust, status and wait, reset-rounds, rebase, squash and push have no tool, and several are missing from the command tree. Nothing says which commands are local and which need watch: the render commands must exit 0, and memory must survive watch being down. Stateless MCP calls have no cwd, so worktree-scoped tools would accept any path an LLM supplies, and watch would then kill jobs or run code there. `omc repo <repo> status|wait` is undefined, and repo_add has two CLI names.

**Question:** What is the complete, authoritative command and tool table?

- (a) An exhaustive table in §4.3/§4.6 with columns for MCP tool, local or watch, and user-only. Rendering, facts, memory and temp-dir are local. Worktree tools take an absolute path that watch realpaths and checks against its own registry of worktrees it created. wait is the same as ensure-repo --until. Narrow 'vice versa' in §1.2.
- (b) MCP is only a small query surface.
- (c) Generate the table from code later.

**Recommendation:** (a).

**Cost if wrong:** Invented tool shapes, renders that die with watch, and path-based attacks.

**Answer:** —

**Recorded in:** —

## Q39 (R36, high): Upstream superpowers: no version pin, the wrap protocol, and its exits that build code

**Status:** open

**Where:** 07-design-lifecycle.md §7.4, §7.7, 08-implement-lifecycle.md §8.3, 05-skill-rendering.md §5.6, §5.7, 01-principles.md §1.4

**Problem:** Python's --done parses SDD's ledger path, its `Task N: complete` lines and the final review, but only checks that superpowers is installed. Installed 7.0.0 conflicts with omc's overrides: one-sentence questions with no options, a size table that says 'build it', spikes, an opt-out that hands off to the normal workflow, and its own workspace rm -rf that runs before omc's --done. The overrides reach the model as Bash output before the stronger upstream skill loads. `$skill` is user syntax in Codex. Older versions have no Interfaces or Spec structure.

**Question:** How does omc pin and wrap upstream skills?

- (a) The fact checks a supported version range and ABORTs outside it. Python inlines the installed SKILL.md at render time, between omc's precedence preamble and the overrides. The overrides are rewritten against 7.0.0: never build, keep the workspace, a fixed ledger grammar. --done fails on any worktree change during brainstorm.
- (b) Vendor the parts omc relies on.
- (c) Float and fail loud on format drift.

**Recommendation:** (a).

**Cost if wrong:** --done breaks silently on upgrade, or brainstorm writes product code.

**Answer:** —

**Recorded in:** —

## Q40 (R37, high): /tmp/omc2 for lifecycle state: macOS cleanup, reboots, other users, retention

**Status:** open

**Where:** 01-principles.md §1.3, 06-lifecycles.md §6.2, §6.3, 03-watch.md §3.8, 04-mcp-and-cli.md §4.5, 05-skill-rendering.md §5.5

**Problem:** Uncommitted design work and --done progress live only in /tmp/omc2, which macOS clears on reboot and prunes after 3 days. The 14-day rule assumes date folders, but lifecycle folders have none, and a directory's mtime goes stale while work under it is active. The fixed path in world-writable /tmp can be created first by another user or swapped for a symlink, mkdir -m sets the mode only on the leaf, and a second OS user can't use omc at all.

**Question:** Where does lifecycle state live, and how is the temp root secured?

- (a) Lifecycle folders and progress go to ~/.omc2/state/<key>/<branch-file>/lifecycle (0700), deleted at the lifecycle's end or when the worktree closes. Spillover and temp go to a per-user root ($TMPDIR/omc2 or /tmp/omc2-<uid>), checked with lstat for owner and 0700 on every component. --done detects a missing folder and says why.
- (b) Keep /tmp and document the loss.
- (c) Keep as is.

**Recommendation:** (a). This also answers part of the parked per-branch cache topic.

**Cost if wrong:** Multi-day designs lost on reboot, and private data written into folders other users control.

**Answer:** —

**Recorded in:** —

## Q41 (R38, high): Watch exit and crash: orphaned jobs, interrupted operations, round penalties

**Status:** open

**Where:** 03-watch.md §3.1, §3.6, 09-run-jobs.md §9.3, §9.4, 01-principles.md §1.3, 03-watch.md §3.4, §3.5

**Problem:** On start, watch only relabels running jobs as failed. Builds, LLM sessions and E2E containers survive a crash or a closed tab, and the next jobs run beside them. Nothing aborts a half-finished omc-repo rebase, cleans lbug.staging dirs, or prunes scratch worktrees. A user's own Ctrl-C costs each active fix loop a round.

**Question:** What does watch do on shutdown and on start after an unclean exit?

- (a) Each job runs in its own process group, with pgid, start time and container labels persisted. Shutdown (INT, TERM, HUP) kills the groups and aborts watch's own rebase. Start reaps verified leftovers, runs teardown, prunes and cleans staging. A restart never counts as a round.
- (b) Same, but count a round only after an unclean exit.
- (c) Re-adopt running children.

**Recommendation:** (a).

**Cost if wrong:** Orphans hold ports, and runs fail for environmental reasons.

**Answer:** —

**Recorded in:** —

## Q42 (R39, high): Round accounting for stopped, superseded, terminated and queued jobs

**Status:** open

**Where:** 09-run-jobs.md §9.2, §9.3, §9.4, 03-watch.md §3.6, 08-implement-lifecycle.md §8.3, 10-review-lifecycle.md §10.4

**Problem:** Every omc run kills the worktree's current job, so subagents, a second session or the user cancel each other, and the victim's status and round count are undefined. Queue time counts toward the 1-hour limit, so jobs queued behind another repo's isolated drain are terminated without starting and still burn rounds. A lost job id forces a new run that kills the old one. Parallel review agents running `omc run` cancel each other.

**Question:** Which outcomes count as rounds, and how are runs within a worktree coordinated?

- (a) Add a `replaced` status that never counts. Queue time gets its own timeout and only run time counts toward the limit. terminated counts only if the job actually ran. Add `omc run status` and --current to find the job. An identical in-flight run is attached to, not killed. Only the main session or the single implementer starts runs, and review agents never do.
- (b) Everything that isn't passed counts.
- (c) Serialize runs per worktree.

**Recommendation:** (a).

**Cost if wrong:** Scheduling, not code, pushes gates into CRITICAL.

**Answer:** —

**Recorded in:** —

## Q43 (R40, high): Which tree a pass certifies, and repository-mode artifact commits

**Status:** open

**Where:** 09-run-jobs.md §9.4, 10-review-lifecycle.md §10.5, §10.6, 08-implement-lifecycle.md §8.5, 11-publish-lifecycle.md §11.2, §11.3, §11.5, 06-lifecycles.md §6.6

**Problem:** Fix rounds leave uncommitted changes and review has no commit step, so it's unclear whether the hash is HEAD's tree or the working tree. Hashing HEAD credits passes to code that was never tested, and create-mr's squash may fold in untested edits. In repository mode, the rulings commit (after milestone-gate), the deviations commit and a no-code feedback record all change the tree after the gate. The carry-over then never fires, and §11.5's 'tree identical to ci-gate's' fails. Job-definition changes aren't part of the key.

**Question:** What does the pass hash cover, and do artifact-only commits count?

- (a) Passes are recorded only on a clean worktree. Fix skills commit each fix before rerunning. The key is HEAD's tree with design_artifact_directory/<slug>/ excluded, plus a hash of the job definition. squash and publish refuse a dirty tree.
- (b) Hash the working tree, untracked files included, and have squash fold it in.
- (c) Accept full reruns in repository mode.

**Recommendation:** (a).

**Cost if wrong:** Untested trees get pushed, or every review reruns E2E for markdown changes.

**Answer:** —

**Recorded in:** —

## Q44 (R41, high): A fix in a later gate job leaves the earlier passes stale

**Status:** open

**Where:** 10-review-lifecycle.md §10.5, 08-implement-lifecycle.md §8.4, 09-run-jobs.md §9.4, 11-publish-lifecycle.md §11.3, §11.5

**Problem:** When a ci or e2e fix changes code, only that job reruns, so check last passed on an older tree. No single tree has passed all of the gate, and §11.5 has nothing well-defined to compare against. Nothing records a gate verdict that publish can read.

**Question:** Does a fix that changes the tree restart the gate?

- (a) Any fix that changes the tree restarts from check, and identical-tree skips keep that cheap. The gate's --done writes a verdict (tree hash plus job ids) only when every job passed on that one tree, and publish reads it.
- (b) Rerun only the failed job.
- (c) Rerun check at the end only.

**Recommendation:** (a).

**Cost if wrong:** MRs ship code that check or E2E never saw.

**Answer:** —

**Recorded in:** —

## Q45 (R42, high): A red base vs the no-bypass rule

**Status:** open

**Where:** 03-watch.md §3.4, 09-run-jobs.md §9.4, §9.5, 08-implement-lifecycle.md §8.3, 10-review-lifecycle.md §10.5

**Problem:** Integration accepts red tests on base, but validation step 6 ('everything passes') can't succeed then. Every feature branch fails check before making any change, so the fix loop fixes unrelated code (which task review then flags) or spends all 6 rounds. Nothing warns before implement, and CI jobs marked allow_failure have no rule.

**Question:** What happens when base is red?

- (a) Integration records 'base red: N tests' in the repo state, and design and implement warn. A preflight before Task 1 asks: fix it as a separate Task 0, or abort. Step 6 becomes 'returns to baseline'. allow_failure CI jobs are excluded from ci by construction.
- (b) Block design and implement until base is green.
- (c) Allow a baseline-failure list.

**Recommendation:** (a).

**Cost if wrong:** Every feature gets stuck on, or silently absorbs, fixes for unrelated breakage.

**Answer:** —

**Recorded in:** —

## Q46 (R43, high): Session memory retention deletes live intent, and stale memory leaks to reused branch names

**Status:** open

**Where:** 12-session-memory.md §12.1, §12.2, §12.3, 03-watch.md §3.8, 02-repos-and-config.md §2.4, 07-design-lifecycle.md §7.1

**Problem:** 'Unmodified for a month' deletes a stacked branch's only base memory while the branch and MR are still alive (reads don't touch the file), so rebase and create-mr silently fall back to main. close-worktree doesn't clear sessions/, so a reused branch name inherits the old memory. There are three different retention keys. The memory store is not 'rebuildable' cache, and whether it is a file or a folder is unspecified.

**Question:** When is a branch's memory deleted?

- (a) Use the per-branch rule: delete when the branch no longer exists locally or on origin and the file is untouched for retention_days, plus on close-worktree. One key, one file named optmem, and the store classed as state, not cache.
- (b) Touch the file on every render.
- (c) Never delete automatically.

**Recommendation:** (a).

**Cost if wrong:** Stacked MRs silently retarget main, or new branches get steered by stale memories.

**Answer:** —

**Recorded in:** —

## Q47 (R44, high): Stacked branches: unpushed parents, merge detection, retargeting

**Status:** open

**Where:** 10-review-lifecycle.md §10.2, 11-publish-lifecycle.md §11.3, §11.5, 12-session-memory.md §12.1, 07-design-lifecycle.md §7.1

**Problem:** An MR can't target a parent that exists only locally. Squash merges make 'parent merged' invisible to git, the parent branch may be deleted, and omc doesn't know the forge. Memory names a worktree, while rebase needs a branch. create-mr retargets to main after the parent merges without rebasing, so parent commits come along as duplicates.

**Question:** Who detects that a parent merged, and what must happen before a retarget?

- (a) triage-comments and rebase check the parent's MR state with forge tools. Python resolves worktree to branch. create-mr refuses when the parent isn't on origin, and refuses to retarget unless the recorded base equals the target (otherwise it sends you back to review). A memory line records the switch.
- (b) Python heuristics on origin.
- (c) Retarget manually only.

**Recommendation:** (a).

**Cost if wrong:** Duplicated diffs and broken stacked MRs.

**Answer:** —

**Recorded in:** —

## Q48 (R45, high): Lifecycle entry preconditions and who may start each lifecycle

**Status:** open

**Where:** 11-publish-lifecycle.md §11.1, §11.5, 10-review-lifecycle.md §10.1, 08-implement-lifecycle.md §8.1, §8.3, §8.4, 05-skill-rendering.md §5.7, 07-design-lifecycle.md §7.8, 03-watch.md §3.4

**Problem:** Nothing stops `omc publish` before review, or after a CRITICAL in ci-gate: it force-pushes and opens an MR on an ungated tree. Review can start after a red milestone gate or on a dirty tree. Implement can start before trust or integration, so ticket-start moves the ticket and the first run is refused, and subagents then improvise direct test runs. It is unspecified whether the review and publish continuations are automatic, so a session could chain all the way to a public push. Approval is enforced only by the model's own good behaviour.

**Question:** What does Python check at each lifecycle entry, and which entries are user-only?

- (a) Implement: committed artifact, plus ensure-repo --until integrated before ticket-start. Review: implement-complete marker and clean tree. Publish: recorded gate verdict on HEAD's tree and a clean tree. A failure renders an ABORT. The implement, review and publish stubs are user-only, and closing statements say to wait for the user. A refused run is its own status and never a round.
- (b) Make only publish user-only.
- (c) No gates.

**Recommendation:** (a).

**Cost if wrong:** Ungated public pushes and fix loops burned on refusals.

**Answer:** —

**Recorded in:** —

## Q49 (R46, high): Splitting a huge MR: chunk worktrees, failures, push and verification, later rounds

**Status:** open

**Where:** 11-publish-lifecycle.md §11.3, §11.4, §11.5, 09-run-jobs.md §9.3, §9.4, 10-review-lifecycle.md §10.1, §10.2, 11-publish-lifecycle.md §11.2

**Problem:** Chunk branches have no worktree to run check in. Fixing a red chunk breaks 'last tree equals gated tree'. 'Squash always', the single-branch push and §11.5's verification all contradict a stack, and the fate of the original <branch> is undefined. triage looks at one MR. Re-splitting outdates review threads. Merged lower chunks need restacking. The proposal has no format, and the size metric, intermediate CI, descriptions, naming collisions with -N slugs and headless behaviour are all open.

**Question:** Is MR splitting in the MVP, and if so, under what contract?

- (a) Post-MVP: create-mr never offers a split until this is designed.
- (b) In the MVP: scratch worktrees per chunk; a red chunk goes back to re-splitting, never to a code fix; <branch> stays the top of the stack; a recorded split plan in the branch cache; per-stack push and verification; triage reads every chunk MR.
- (c) Allow a split once, on the first publish only.

**Recommendation:** (a). Splitting touches every publish invariant and isn't needed for the first repos.

**Cost if wrong:** Broken invariants on every split publish, or the stack rebuilt over reviewers' threads.

**Answer:** —

**Recorded in:** —

## Q50 (R47, high): Repo identity: case, aliases, URL changes, folder/URL mismatch, trust identity

**Status:** open

**Where:** 02-repos-and-config.md §2.1, §2.3, §2.5, §2.6, 03-watch.md §3.2, 04-mcp-and-cli.md §4.3, 07-design-lifecycle.md §7.1

**Problem:** Paths keep their case, so a forge's canonical casing and a typed lowercase URL produce two keys, two clones and split trust. SSH aliases make a key depend on one machine's config. A hand-edited ssh_url or a hand-made folder makes the folder key and the URL hash disagree, and nothing says which one names the cache, worktrees and trust. trusted_repos and the notifications use bare names, which are ambiguous with forks. resolve-repo takes URLs 'as-is' without canonicalising them.

**Question:** What is a repo's identity once it is registered?

- (a) Fold host and path to lowercase for the hash, require a user, don't resolve aliases. A folder must equal get-repository-id(ssh_url), otherwise it is an invalid-config state and is not cloned. trusted_repos stores key plus URL. Every URL input goes through the one function. Changing the URL means adding a new repo.
- (b) The folder name is authoritative, and URL edits are allowed.
- (c) Rename folders automatically.

**Recommendation:** (a). Settle this before any key is persisted.

**Cost if wrong:** Duplicate repos, orphaned caches, or trust silently carried to a different remote.

**Answer:** —

**Recorded in:** —

## Q51 (R48, high): Bootstrapping a new machine and a new omc repo

**Status:** open

**Where:** 02-repos-and-config.md §2.2, §2.3, §2.5, 03-watch.md §3.1, §3.3, §3.4, 04-mcp-and-cli.md §4.1, §4.6

**Problem:** With no local config, watch doesn't know the omc repo path and takes no arguments. Nothing creates a new omc repo. A repo with no upstream breaks sync and the unpushed warning. On machine 2 it's unclear whether integrations committed on machine 1 are re-run (overwriting user-owned files), revalidated, or left stuck, and integration state per machine (for example a missing protoc) has no home. Who installs the plugin stubs and the fenced instruction section, and what uninstall removes, is also undefined.

**Question:** What is the first-run and new-machine flow?

- (a) Every command except configure and version fails with 'run omc configure'. The first configure clones, or git-inits and writes defaults. No upstream means sync is off, with one log line. Existing integrations are revalidated in a scratch worktree and never regenerated, and per-machine gaps go in the cache. update installs and refreshes stubs and the fence, and uninstall reverses exactly what omc registered.
- (b) watch runs configure interactively.
- (c) A default omc repo path.

**Recommendation:** (a). Correct §2.2's 'clone and run watch' promise.

**Cost if wrong:** No working path for first use, and integration files clobbered across machines.

**Answer:** —

**Recorded in:** —

## Q52 (R49, high): Model block schema: per provider, orchestrator slot, publish, review and subagent slots, pinning

**Status:** open

**Where:** 02-repos-and-config.md §2.5, 07-design-lifecycle.md §7.1, §7.6, §7.7, 08-implement-lifecycle.md §8.1, §8.3, 10-review-lifecycle.md §10.1, 11-publish-lifecycle.md §11.5

**Problem:** §2.5 gives each block one provider and one model set, while §8.1 says 'per provider', so --codex on a Claude-configured block passes Claude model ids. No block has an orchestrator slot. Design, review and watch slots aren't named, and neither are the plan, explain or hardening subagents or the fix waves. Publish has no block, so the feedback design runs on review's model. In-session /omc:implement keeps the design model. Claude's Agent tool may accept only aliases.

**Question:** What is the exact block schema?

- (a) `<lifecycle>: {provider, models: {claude: {orchestrator, simple, medium, high, review, plan, fix}, codex: {...}}}`, with the flag choosing the sub-map. Publish uses review's block, stated explicitly. omc configure validates values against what each harness accepts. When a model can't be pinned, fall back to the orchestrator model and say so in one line.
- (b) One provider per block, and refuse a flag that disagrees.
- (c) Provider-neutral tiers.

**Recommendation:** (a).

**Cost if wrong:** Wrong models, or invalid model ids passed to a harness.

**Answer:** —

**Recorded in:** —

## Q53 (R50, high): Snippet interface: layout per step, the log-dir, test-id grammar, rerun output

**Status:** open

**Where:** 09-run-jobs.md §9.2, §9.4, §9.5, 03-watch.md §3.9, 07-design-lifecycle.md §7.7

**Problem:** Snippets are 'per test step' but stored one pair per job type. detect-failures gets a 'log-dir' while each job writes one log file to a shared folder, and JUnit XML lives in the worktree, so stale files are a risk. No test-id or selector grammar exists for plan writers or for routing across several frameworks. rerun-tests exposes only an exit code, so 'zero tests ran' is indistinguishable from a pass. Stdlib-only rules mean every snippet hand-rolls its own XML hardening.

**Question:** What is the snippet I/O contract?

- (a) `stages/<type>/<step>/{detect-failures,rerun-tests}`. A fresh per-job directory holding output.log plus the artifacts each step declares. Ids are namespaced `<framework>:<native-id>` and selectors are `<step>:<id>`. rerun-tests prints `<id> passed|failed` per test, with exit codes 0, 1 or 2+. omc ships a tested JUnit helper module. A selections note per framework, not snippet code, goes to the planner.
- (b) One pair per job type acting as a dispatcher.
- (c) Leave to the implementer.

**Recommendation:** (a).

**Cost if wrong:** No-op reruns pass gates, and plan selectors don't work.

**Answer:** —

**Recorded in:** —

## Q54 (R51, high): The ci job: scope, CI steps that can't run locally, and its fix skill

**Status:** open

**Where:** 09-run-jobs.md §9.2, §9.4, §9.8, 10-review-lifecycle.md §10.5, 03-watch.md §3.4, 01-principles.md §1.2

**Problem:** §3.4 says ci covers what check and e2e don't. §9.2 and §10.5 say it is what CI runs. Real CI has secrets, forge-only scanners, commit-message lint on the squash (which only exists after the gate), deploys and Gitleaks (which must not run locally). With no-bypass, ci then either can never pass or silently drops those steps. No fix skill exists for ci, though ci-gate runs a fix loop on it.

**Question:** What does ci include, and how is it fixed?

- (a) The complement of check and e2e. /auto-integrate records each excluded CI job with a reason in repo.yaml, and the MR's Testing section lists them. Add /omc:fix-ci.
- (b) The full pipeline, with check and e2e dropped from ci-gate.
- (c) Reuse fix-check.

**Recommendation:** (a).

**Cost if wrong:** An unpassable gate, or silent claims that CI parity is complete.

**Answer:** —

**Recorded in:** —

## Q55 (R52, high): Fix skills and other non-lifecycle skills: render command, inventory, hook namespace, subagents

**Status:** open

**Where:** 09-run-jobs.md §9.4, §9.6, §9.8, 05-skill-rendering.md §5.2, 06-lifecycles.md §6.4, 08-implement-lifecycle.md §8.3, 11-publish-lifecycle.md §11.4, 02-repos-and-config.md §2.6, 03-watch.md §3.7, 12-session-memory.md §12.2

**Problem:** No render command exists outside `omc lifecycle`, so the fix skills, /integrate (never defined), /integrate-suggestions and /suggest-mr-split can't get hooks or memory, and nothing says how a fix skill finds its failed job, since there are no arguments. Fix hooks have no namespace: fix skills run in implement, review and publish, and §6.4 has only design hooks, while review:code-review is missing from the table. Inside SDD the implementer subagent sees the red result but not the fix skill. Subagent briefs don't carry session memory.

**Question:** How are these skills rendered and delivered?

- (a) `omc skill <name>` renders from the worktree's latest failed job plus the stored CRITICAL brief, with an ABORT if there is none. A skill inventory table goes in 05. A reserved `run:` namespace (`hooks/run/fix-<type>/`) and review:code-review are added to §6.4. The SDD controller renders the fix skill and dispatches a fix subagent. Briefs include the rendered memory file. /integrate re-queues /auto-integrate as a watch job.
- (b) Poll output prints the fix skill inline.
- (c) Static skills.

**Recommendation:** (a).

**Cost if wrong:** Fix loops without repo diagnosis hooks or memory, and undefined user skills.

**Answer:** —

**Recorded in:** —

## Q56 (R53, high): Stub install and refresh, CLI/watch version skew, provider detection

**Status:** open

**Where:** 05-skill-rendering.md §5.1, §5.2, §5.7, 04-mcp-and-cli.md §4.2, §4.6, 03-watch.md §3.1, 02-repos-and-config.md §2.5

**Problem:** The stub set, its frontmatter (allowed-tools, user-only flags) and Codex's openai.yaml are plugin content, so stale caches still matter, which is v1's version-pin trap again. Nothing says who installs or refreshes them. After an update, the new CLI talks to an old running watch. The renderer can't tell Claude from Codex on --done renders, yet text differs by provider (Skill tool vs reading the file, /omc vs $omc).

**Question:** How are stubs kept in sync, and how does the renderer know its context?

- (a) `omc update` generates the stubs from the package with a version stamp. A mismatch renders an ABORT saying 'run omc update'. Every call carries the CLI version, and watch refuses a mismatch with 'restart watch'. Stubs pass --provider, which every handoff line repeats.
- (b) A marketplace plugin with manual refresh.
- (c) Detect the harness from environment variables.

**Recommendation:** (a), using (c) as a cross-check.

**Cost if wrong:** Missing skills, wrong verbs, and confusing failures after updates.

**Answer:** —

**Recorded in:** —

## Q57 (R54, high): Render deadline and hook timeouts under Claude's 2-minute preprocessing limit

**Status:** open

**Where:** 05-skill-rendering.md §5.2, §5.3, §5.5, §5.6, 03-watch.md §3.5

**Problem:** Facts run one at a time with a 10 s timeout each, executable hooks have no timeout, and lock waits are 30 s each. Together they can exceed 120 s, and Claude then aborts the load with no ABORT block, which breaks 'always exit 0'. On Codex, anything over the 10 s yield returns partial output.

**Question:** What is the time budget for a whole render?

- (a) A render deadline written to config (e.g. 90 s) shared by facts, hooks and lock waits, plus a per-hook timeout. Going over kills the process tree and renders an ABORT naming the slow part. An end-of-render marker lets Codex detect a partial read.
- (b) Per-component timeouts only.
- (c) Forbid slow hooks.

**Recommendation:** (a).

**Cost if wrong:** Skill loads fail without a precise error.

**Answer:** —

**Recorded in:** —

## Q58 (R55, high): Where rendering runs, and consistency with the omc-repo sync

**Status:** open

**Where:** 05-skill-rendering.md §5.1, §5.5, 04-mcp-and-cli.md §4.2, 03-watch.md §3.3, §3.5, 02-repos-and-config.md §2.3

**Problem:** If rendering runs inside watch, facts and hooks get watch's cwd and environment, not the session's, and the 20k cap applies. If it runs locally, it can't take watch's in-process lock and can read a half-rebased working tree with conflict markers or stashed-away hooks. Neither is stated, and the exit-0 rule must still hold when watch is down.

**Question:** Which process renders, and how is a sync excluded?

- (a) The CLI renders locally in the session's cwd and environment, takes the shared filelock, and ABORTs with 'omc repo sync in progress' after a short wait. Watch-dependent facts return an error when watch is down.
- (b) watch renders, with the cap waived and cwd and env passed in.
- (c) Render from committed HEAD.

**Recommendation:** (a).

**Cost if wrong:** Renders that are wrong or vanish during a sync, and hooks run with the wrong environment.

**Answer:** —

**Recorded in:** —

## Q59 (R56, high): --done: non-document plugins, order, idempotency, --from, restart, concurrent sessions

**Status:** open

**Where:** 06-lifecycles.md §6.1, §6.2, §6.3, 08-implement-lifecycle.md §8.1, §8.2, §8.5, 10-review-lifecycle.md §10.1, §10.2, 11-publish-lifecycle.md §11.1, §11.3, 07-design-lifecycle.md §7.1, open-questions.md §H omc resume

**Problem:** ticket-start, gates, rebase and create-mr produce no document, so `--done` has nothing to check. A gate's 'pass' isn't verified by Python, and the model can run --done after a CRITICAL. Nothing enforces order or makes --done idempotent after an ABORT. --from doesn't define the 'current document' and leaves stale later folders behind. When progress already exists, a re-render doesn't say whether it resumes or restarts. A dead session with `omc resume` parked hits the existing-worktree and existing-branch stops. Two sessions share one progress record, and the slug isn't persisted.

**Question:** What is the generic --done contract?

- (a) Per-plugin evidence checks: gates check a watch pass on the current tree, git plugins check branch state, tracker and forge plugins check a small result file. Strict order, and rerunning --done re-renders without advancing. --from moves later folders aside. With existing progress, the stub resumes at the recorded plugin. A per-worktree owner lease. The slug is stored when the worktree is created.
- (b) Document plugins only.
- (c) Trust the model.

**Recommendation:** (a). It also gives the MVP a recovery path while resume stays parked.

**Cost if wrong:** Ungated commits and lost or duplicated work.

**Answer:** —

**Recorded in:** —

## Q60 (R57, high): check-artifact rules, plus the copy-and-commit step's ownership and failure path

**Status:** open

**Where:** 06-lifecycles.md §6.6, 07-design-lifecycle.md §7.3, §7.8, 02-repos-and-config.md §2.3, 13-testing.md §13.0

**Problem:** Rejecting any '/tmp/', '~/.omc2' or absolute path rejects legitimate designs, including every omc feature design, /etc/hosts in code blocks and a verbatim seed. The checks run after the user's yes, so a fix means editing approved content. Copy and commit has no command and no defined order with temp deletion. It also has no failure path (watch down, omc repo mid-conflict, pre-commit hooks, staged user changes), and no slug-collision rule against an existing folder.

**Question:** What does check-artifact match, and when and how is the artifact committed?

- (a) Check only link targets for escapes, missing files, file:// and private-location targets, plus a credential scan. Run it before the overview is shown. The lifecycle's final --done runs check, a path-limited copy and commit, then deletes temp last, with nothing deleted on failure. Slug folder uniqueness is checked at create-slug.
- (b) Skip code spans but keep text bans.
- (c) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Designs that can never be approved, or approvals given for content that differs from what is committed.

**Answer:** —

**Recorded in:** —

## Q61 (R58, high): GitNexus home is shared with v1, and analyze dirties the hidden clone

**Status:** open

**Where:** 03-watch.md §3.5, §3.6, 01-principles.md §1.5, 02-repos-and-config.md §2.4

**Problem:** Only two GitNexus environment variables are set, so v2 analyzes register in v1's global registry (v1 already had registry-pollution incidents) and use v1's install. Without --skip-agents-md and --skip-skills, every analyze writes AGENTS.md and skills into the clone, which then fails create-worktree's 'exactly on origin' check and pollutes docs_grep.

**Question:** Does v2 isolate GitNexus and fix the analyze argv?

- (a) Set GITNEXUS_HOME=~/.omc2/gitnexus in the child-environment builder, use a v2-owned pinned install, and specify the analyze argv with the suppression flags, plus a test that the clone stays clean.
- (b) Share with v1 until cutover.

**Recommendation:** (a).

**Cost if wrong:** v1 and v2 corrupt each other's registry, and spurious worktree failures.

**Answer:** —

**Recorded in:** —

## Q62 (R59, high): Answers from GitNexus reflect base only, never the branch under work

**Status:** open

**Where:** 01-principles.md §1.1, 03-watch.md §3.5, 04-mcp-and-cli.md §4.4, 10-review-lifecycle.md §10.3, §10.4, 11-publish-lifecycle.md §11.2

**Problem:** Only the hidden clone at base is indexed. After implement, the branch's new symbols and docs don't exist in the graph, so 'GitNexus first' gives wrong answers in deviation analysis, code review, feedback designs and stacked branches. Nothing tells the agent where the graph's view ends. Dependency repos have no read tool for their sources, and gitnexus paths can't be opened.

**Question:** How should skills treat the base-only view?

- (a) Every result carries a header 'index = origin/<base>@<sha>; branch changes not included'. Review and publish skills read the diff for changed code. Add a typed repo_show(repo, path, range) tool with display paths.
- (b) Index worktrees incrementally.
- (c) Restrict graph use to design.

**Recommendation:** (a).

**Cost if wrong:** Review and redesign reason from a stale graph.

**Answer:** —

**Recorded in:** —

## Q63 (R60, high): explain-seed's context gate runs before the ticket is fetched, and ticket fetching sits in a context-only hook

**Status:** open

**Where:** 07-design-lifecycle.md §7.3, §7.6, §7.1, 06-lifecycles.md §6.4

**Problem:** Seeds that are just a ticket key fail the 'clear problem and goal' gate because the ticket hasn't been fetched yet. The fetch and the parsed Primary: line live in omc's default explain-context contribution, so turning off the omc layer silently drops ticket linking, and per-section hardening subagents fetch again N times. The hook's input contract isn't defined.

**Question:** Where does the ticket fetch live, and when does the gate run?

- (a) The explain-seed plugin itself fetches tickets and URLs, writes ## Ticket and ## References, then applies the gate to the enriched context. explain-context stays code and docs context only, and its input is the text to explain.
- (b) Keep the hook and exempt ticket seeds from the gate.
- (c) Drop the gate.

**Recommendation:** (a). Also add a `## Clarifications` section for gate answers and validate the Primary line grammar at --done.

**Cost if wrong:** Every ticket design gets blocked, or ticket linking is silently lost.

**Answer:** —

**Recorded in:** —

## Q64 (R61, high): Code-review waivers have no home and fixes after deviation analysis go unrecorded

**Status:** open

**Where:** 10-review-lifecycle.md §10.3, §10.4, §10.6, 07-design-lifecycle.md §7.6, 11-publish-lifecycle.md §11.2, §11.3, 06-lifecycles.md §6.5

**Problem:** Waivers are supposed to go into `## Deliberate complexity`, a section that exists only in the approved design, which must never be rewritten. Code-review runs after deviation analysis and can apply fixes that change behaviour, and those never reach `<slug>-deviations.md` or the MR. `Section: <heading>` doesn't fit findings about code. The tracked-files check misses commits and untracked files. Re-running review overwrites or duplicates the deviations file and re-asks escalations already answered. An answered escalation stays labelled `escalated` and is dropped from the MR. Feedback designs have no precedence rule.

**Question:** What does the review lifecycle record, and where?

- (a) Swap the order to code-review then deviation-analysis. Waivers go in a `## Deliberate complexity` section of a per-round `<slug>-deviations[-feedback-<n>].md`, committed when review ends. An answered escalation becomes accepted or reverted with `Basis: user`. Findings use `Location: path:line`. The snapshot covers HEAD, index and untracked files. The latest feedback design wins.
- (b) Keep the order and limit code-review to fixes that keep behaviour the same.
- (c) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Approved designs get rewritten, and MRs claim no deviations when there are some.

**Answer:** —

**Recorded in:** —

## Q65 (R62, high): YAML writes without rewriting user files (pyyaml)

**Status:** open

**Where:** 02-repos-and-config.md §2.3 Ownership, §2.5 omc update, 01-principles.md §1.2, §1.4

**Problem:** pyyaml can't round-trip a file: any write drops comments and reformats the whole file the user owns, and that breaks 'never rewrites a whole file'. When a file has uncommitted edits, update must skip it, so the key ends up in no file, and code isn't allowed to fall back to a default.

**Question:** How are keys added to user-owned YAML?

- (a) Approve and vet ruamel.yaml round-trip mode for every write. A key missing because its file couldn't be written fails loud with 'commit and rerun omc update'.
- (b) Append the text at the end and never re-serialise.
- (c) Accept full rewrites.

**Recommendation:** (a).

**Cost if wrong:** User comments destroyed on every update, or code reading keys that don't exist.

**Answer:** —

**Recorded in:** —

## Q66 (R63, medium): Concurrency model for locks: setup as state, worktree creation as a writer, scope and hold times, sessions sharing .git

**Status:** open

**Where:** 03-watch.md §3.5, §3.6, 07-design-lifecycle.md §7.1 step 7, 04-mcp-and-cli.md §4.4, 02-repos-and-config.md §2.4, 10-review-lifecycle.md §10.2

**Problem:** If '/auto-integrate' holds a setup write lock, queries are blocked for the whole time it runs. Worktree creation is listed as a reader, but it fetches, resets and creates branches, and a fetch that moves origin can make its own 'exactly on origin' check fail. Long readers such as wiki generation, surveys and 60-minute run jobs either hold locks for that long, or see `reset --hard` swap files under them, and writer preference then stalls every render. docs_grep reads the clone's files without the refs lock. Sessions run fetch, push and gc against the clone's shared .git outside any lock. No lock order is defined.

**Question:** What does each lock guard, and for how long?

- (a) Setup is a persisted state that is checked, not locked. Long jobs read from immutable snapshots (a pinned commit and copied snippets), so locks are only held for seconds. Worktree creation cuts from the fetched SHA under a short per-repo mutex. The omc fetch, rebase and push go through watch's refs lock, and gc.auto=0. Fixed order: slot first, then setup, refs, index, docs, omc repo.
- (b) Readers hold locks for the whole run, and writers skip.
- (c) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** System-wide stalls, torn reads and git ref-lock failures.

**Answer:** —

**Recorded in:** —

## Q67 (R64, medium): Per-worktree setup and the job execution environment

**Status:** open

**Where:** 03-watch.md §3.1, §3.4, 02-repos-and-config.md §2.6, 09-run-jobs.md §9.2, 07-design-lifecycle.md §7.1 step 7

**Problem:** Recorded setup (uv sync, npm ci) runs only in the scratch worktree, so fresh worktrees have no dependencies and the first check spends rounds installing them. Jobs inherit the environment watch started with days earlier. direnv, mise and nvm never apply, and PATH changes made after start are invisible to jobs.

**Question:** When does setup run in user worktrees, and what environment do jobs get?

- (a) Every job runs recorded setup first (incremental), gated by trust and counted in the time limit. The job environment is watch's environment minus omc internals, plus a per-repo env block, run under `direnv exec` when there is an allowed .envrc. The job log records which environment was used.
- (b) Setup once at worktree creation if the repo is trusted.
- (c) Leave it to the check steps.

**Recommendation:** (a).

**Cost if wrong:** Fix loops chase environment differences instead of code.

**Answer:** —

**Recorded in:** —

## Q68 (R65, medium): Repo state enum, refusal messages, and stale or partial flags

**Status:** open

**Where:** 03-watch.md §3.4, §3.5, §3.7, 01-principles.md §1.1, 02-repos-and-config.md §2.6, 07-design-lifecycle.md §7.1, §7.3

**Problem:** 'usable', 'partial' and 'may be stale' don't appear in the state diagram. --until and facts parse display strings. The refusal message says 'indexing' or 'auto-integrate in progress' even while trust is awaited or integration has failed, so agents poll forever. Readiness for queries waits on LLM surveys. ensure-repo has no rule for failed states or timeouts. The stale flag has no storage and no rule for clearing it.

**Question:** What is the machine-readable state model?

- (a) Two fields, query (cloning|indexing|queryable|failed) and integration (none|awaiting-trust|integrating|integrated|partial|failed), plus a stale list. A table maps states to allowed operations. Every refusal names the real state and the next step. Surveys don't gate queryability. ensure-repo exits on failure.
- (b) One enum covering every combination.
- (c) Document the strings.

**Recommendation:** (a).

**Cost if wrong:** Agents misread states and either poll forever or ask the user the wrong thing.

**Answer:** —

**Recorded in:** —

## Q69 (R66, medium): Scheduling: which operations are jobs, queue order, time limits for non-run jobs, kept-alive environments and slots

**Status:** open

**Where:** 03-watch.md §3.2, §3.6, 09-run-jobs.md §9.2, §9.3, §9.7, 08-implement-lifecycle.md §8.4

**Problem:** It is unclear whether clone, surveys, conflict resolution, the daily check, omc-repo commits and worktree creation take slots or wait for isolation. A wait on commits would stall `approve-design` behind a one-hour drain. There is no queue order, so starvation is possible. Indexing, docs and integration have no time limits, so one hung job blocks a drain forever. A failed kept-alive environment may hold isolation for an hour. Two worktrees of the same repo collide on E2E ports. The 'resource locks' that §9.2 relies on don't exist.

**Question:** What are the scheduling rules?

- (a) One table listing every operation with 'takes slot' and 'runs during isolation'; short session-facing operations never wait. Interactive jobs run before background ones, FIFO within each class, with a bound on fairness. Each job type has a time limit in config, and a drain may pre-empt rebuildable jobs. A failed environment releases isolation but keeps its slot. A per-repo E2E lock unless the integration marks it parallel-safe.
- (b) Everything takes a slot.
- (c) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Session operations time out, and a single hung job can block the whole machine.

**Answer:** —

**Recorded in:** —

## Q70 (R67, medium): Daily freshness check: windows, size, sandbox, failure handling, scheduling

**Status:** open

**Where:** 03-watch.md §3.3, §3.7, 02-repos-and-config.md §2.5, 01-principles.md §1.2

**Problem:** Docs need commits since the last wiki run, and integration needs commits since the last pass, but there is a single dossier for both. Busy monorepos overflow it and break the cost estimate. One call covering every repo fails for all of them at once. Commit messages, which are untrusted, enter a headless call whose cwd and tools are undefined. Failures could be silently read as 'no change'. 'Once a day' has no anchor for a watch process that only runs some of the time. The first wiki run and its retry rule are undefined. The `documentation` key is both a bool and a mapping, and the 'longer of' rule contradicts how overrides normally work.

**Question:** How does the daily check work?

- (a) Each decision has its own window, anchored to a recorded commit. Every repo entry is capped, and work is split into chunks over a token budget. A Python pre-filter on CI and build paths runs first. The headless call runs sandboxed and returns strict JSON, and a missing repo means 'unknown'. The check runs on the first tick 24 hours after `last_check`. The first wiki is generated as soon as docs are turned on. Keys: `documentation` (bool) plus `documentation_min_interval_days` as a machine floor.
- (b) One call per repo.
- (c) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Wikis that never refresh, injected decisions, and runaway cost.

**Answer:** —

**Recorded in:** —

## Q71 (R68, medium): Suggestion box: who writes entries, dedup, dismissal, false positives, surfacing

**Status:** open

**Where:** 09-run-jobs.md §9.4, §9.5, §9.6, 02-repos-and-config.md §2.5, §2.6

**Problem:** Entries need 'a guess at the cause', but flaky entries are written by Python at no LLM cost, and §2.5 assigns reports to the watch model block. There is one file per occurrence with no naming scheme or dedup, so a recurring flake floods the repo. A compile or lint failure triggers 'detector found nothing', which files false incidents. The only way to remove an entry is a fix commit, so there is no dismiss, and nothing clears missing-tool entries. Nothing shows the count. /integrate-suggestions has no way to write to the repo.

**Question:** What is the suggestion-box contract?

- (a) Python writes from a template per type, with a fixed header: type, subject key, count, first/last seen. A repeat updates the existing file. The guess is made when the entry is read. Entries are filed only for failures of test steps. Outcomes are fixed, dismissed or deferred, and a successful /integrate clears tool entries. repo_list shows a count. /integrate-suggestions handles integration incidents through a watch commit tool.
- (b) LLM-written entries.
- (c) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** A box that fills with noise and never empties.

**Answer:** —

**Recorded in:** —

## Q72 (R69, medium): Snippet validation failures and regenerating integration files

**Status:** open

**Where:** 09-run-jobs.md §9.5, 03-watch.md §3.4, §3.7, 02-repos-and-config.md §2.3

**Problem:** There is no outcome for a framework that can't be validated (no injection is possible, partial detection, no single-test rerun). Re-running /integrate has to regenerate snippets, the ci job, setup and surveys, but anything that 'already exists' belongs to the user, so it either clobbers hand edits or can't update. Detection that is partially stale goes unnoticed. The location and fields of the validation record are undefined.

**Question:** How are partial validation and regeneration handled?

- (a) Commit the snippets that validated and mark the repo 'integrated (partial: …)', with a retry budget per snippet. omc records the content hash of each file it writes in validation.yaml and regenerates only files that still match that hash; otherwise it proposes a diff. A consistency check at run time flags an incomplete detector.
- (b) Fail integration.
- (c) Always overwrite omc's paths.

**Recommendation:** (a).

**Cost if wrong:** Hand fixes overwritten, or integrations stuck stale.

**Answer:** —

**Recorded in:** —

## Q73 (R70, medium): Hardening details: stale explain output, waiver authority, zero contributions, overrides by name, independence of inline hooks

**Status:** open

**Where:** 06-lifecycles.md §6.4, §6.5, 07-design-lifecycle.md §7.6, §7.7, 10-review-lifecycle.md §10.4, 05-skill-rendering.md §5.5

**Problem:** 'Explain once' leaves new or renamed sections without context in exactly the rounds that changed structure. §7.6 lets hardening waive findings on its own judgement, while §6.5 says it asks first, and 'recorded decision' has no format. With zero contributions, behaviour is undefined. Layer switches can't drop a single contribution, and a contribution with the same name in another layer might append or replace. Non-.md files and a lost exec bit aren't covered. Hooks running inline see each other's output, so they aren't independent. Plan hardening applies findings automatically while §7.7 forbids design edits, and an 'amendment record' has no format. design-sections has no edge-case rules.

**Question:** What are the hardening rules?

- (a) Re-explain only new or changed sections, using section hashes from design-sections (JSON with index, heading, sha256 and a file per section). Decisions use `Decision:` lines, and an automatic waiver must cite one. Zero contributions prints a note, writes `None.` and passes. A later layer with the same name replaces the earlier one, plus per-contribution switches. Unknown files fail loud. Each contribution runs in its own subagent. Plan findings that touch `<slug>.md` are forced to `Needs decision`, and Python records amendments with hashes before and after.
- (b) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Stale context, waivers nobody approved, and design edits nobody recorded.

**Answer:** —

**Recorded in:** —

## Q74 (R71, medium): Rendering grammar: <match> errors, fact contract, variables, substitution

**Status:** open

**Where:** 05-skill-rendering.md §5.3, §5.4, §5.5, §5.6, 01-principles.md §1.2, 07-design-lifecycle.md §7.3, 08-implement-lifecycle.md §8.2

**Problem:** A missing <error> branch silently drops content, which contradicts fail-loud. Facts get no repo, branch, worktree or provider context, args have no tokenization rule, and the output stream isn't defined. There is no way to abort or skip a whole skill. Lazy evaluation hides typos in branches that aren't taken, and markdown contributions written by users aren't tested. There is no variable registry, no grammar, and no escape for a literal `{{` (GitHub Actions `${{ }}`). `{{slug}}` has no persisted source. Unscoped fact names become ambiguous over time, and `<repo>:` scopes can't be written portably.

**Question:** What is the exact rendering grammar?

- (a) Parse each template statically up front, with a closed variable registry where each entry has a resolver and allowed contexts, and the strict form `{{[a-z_]+}}` plus an escape. A missing <error> branch, an unknown name or a bad syntax renders an ABORT. Directives <abort>/<skip/> are added. Facts get OMC_* environment variables, cwd set to the worktree, argv split with shlex and no shell, and JSON on stdout only. Scopes omc:, global: and repo: are mandatory. The slug is stored when the worktree is created.
- (b) Keep lazy and lenient.

**Recommendation:** (a). Add `omc hooks --check` as a lint.

**Cost if wrong:** Skills that silently half-render, and contributions broken by template syntax.

**Answer:** —

**Recorded in:** —

## Q75 (R72, medium): The commit plugin: classifying fix-round files, a clean-tree deadlock, staging and naming rulings

**Status:** open

**Where:** 08-implement-lifecycle.md §8.3, §8.5, 06-lifecycles.md §6.6, 02-repos-and-config.md §2.3, 11-publish-lifecycle.md §11.2

**Problem:** Bullet 1 auto-commits fix-round changes, while bullet 4 asks about any file the plan didn't produce, and fix-round files fit both. Keeping a file uncommitted makes the clean-tree check fail forever, and headless mode has no answer. Rulings are written at the build's --done but committed two plugins later, with no staging place, and copied verbatim, so check-artifact fails on paths nobody can fix. Product git hooks and signing have no failure path. 'At least one commit over base' passes trivially in repository mode.

**Question:** How does commit classify and record?

- (a) Auto-commit modified tracked files, and ask only about untracked files: commit, leave (added to .git/info/exclude) or stop. Rulings are committed at the build's --done through the shared artifact path with paths normalised. Never use --no-verify; a hook failure loops back into fixes. The commit check counts only commits outside the artifact directory.
- (b) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Implement can't finish, or rulings are lost when the gate stops.

**Answer:** —

**Recorded in:** —

## Q76 (R73, medium): ticket-start: feedback rounds, existing ticket states, decline behaviour, early ownership check

**Status:** open

**Where:** 08-implement-lifecycle.md §8.2, 11-publish-lifecycle.md §11.3, §11.5, 07-design-lifecycle.md §7.3, 13-testing.md §13.2

**Problem:** In a feedback round the ticket moves from In Review back to In Progress, and you are asked to take it over from the reviewer. A ticket that is already later in the workflow or closed is moved backwards. Assignment and the move can fail independently. 'Implement stops' on decline has no mechanism, and headless mode can never answer. Ownership is checked only after the whole design. Plain GitHub issues have no statuses, so the success path can't be tested. The ticket can't be added later, and a fact error has no branch.

**Question:** What does ticket-start do in each state?

- (a) Skip it on feedback rounds. Never move a ticket backwards. Report assign and move failures separately and continue. On decline, offer take over / continue without touching the ticket / stop, with headless choosing continue. explain-seed records the assignee early. A ticket named in session memory counts when there is no Primary line. Use a GitHub Projects board in one test repo.
- (b) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Board churn on every round, and designs blocked late.

**Answer:** —

**Recorded in:** —

## Q77 (R74, medium): Brainstorm output contract: skeleton checks, persistence, visual companion, decomposition, recon

**Status:** open

**Where:** 07-design-lifecycle.md §7.3, §7.4, 01-principles.md §1.1, §1.3, 04-mcp-and-cli.md §4.3

**Problem:** No --done check keeps the explain-seed skeleton intact (verbatim Seed, Ticket lines) or requires ### sections under ## Design, which design-sections relies on. The document is written once at the end, so a crash loses every answer. The visual companion writes into the worktree or a world-readable /tmp and leaves a server running. Breaking a seed into several projects doesn't fit one slug. Recon ignores GitNexus. Repos discovered along the way have no home in the document. The model used by the builder-check subagent is unspecified.

**Question:** What is brainstorm's output contract?

- (a) Python pre-creates the skeleton. --done checks that Seed is byte-identical, the headings are present, there is at least one ### under Design, and the ticket lines parse. The document is written each round. The companion is pointed at the plugin's temp folder and stopped at --done, or disabled. Sub-projects go to `## Follow-ups`. Recon uses gitnexus and docs_grep, and a `## Repos` section lists discovered repos. Subagents use the design model explicitly.
- (b) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Hardening receives unusable documents, and answers are lost.

**Answer:** —

**Recorded in:** —

## Q78 (R75, medium): create-slug and find-repo: headless call contract, seed via argv, slug determinism

**Status:** open

**Where:** 07-design-lifecycle.md §7.1, 04-mcp-and-cli.md §4.3, 01-principles.md §1.3

**Problem:** These LLM calls run before any session exists. Provider, permissions, timeout and tool allowlist are unspecified, and find-repo contradicts 'omc never searches a forge'. create-slug takes the seed as argv, against the files-only rule, and §7.1 says the seed is 'never placed in the prompt' although the slug prompt contains it. Re-running with the same seed gives a different slug, so the existing-worktree and existing-branch guards never fire and duplicate branches pile up.

**Question:** How do these calls work?

- (a) Drop find-repo for the MVP (the user supplies the URL). create-slug reads `--seed-file` (seed.md is written first) through the shared headless helper with read-only tracker tools, and caches the slug by seed hash. Add `--slug` to override.
- (b) Keep both.

**Recommendation:** (a).

**Cost if wrong:** Duplicate branches, and a separate LLM entry point with no permission model.

**Answer:** —

**Recorded in:** —

## Q79 (R76, medium): Session memory: superseding entries, format, detached HEAD, transport

**Status:** open

**Where:** 12-session-memory.md §12.2, §12.3, 02-repos-and-config.md §2.4, 04-mcp-and-cli.md §4.2, §4.6, 10-review-lifecycle.md §10.2

**Problem:** Memory is append-only, with no retract or list, so contradictory base intents are all injected and the LLM picks one. The line format, timestamp, newline handling and the over-280-byte behaviour are unspecified, and whether optmem is a file or a folder is unclear. `rev-parse --abbrev-ref` returns HEAD during a rebase, which is exactly when the base memory is needed. It's unclear whether memory add needs watch, and if watch is down the memory is lost.

**Question:** What is the memory store contract?

- (a) Local command under a filelock, a single `optmem` file with `<ISO UTC>\t<provider>\t<text>` lines, rejecting newlines and anything over 280 bytes. `memory list` and `memory retract <n>` add tombstones, and later lines win. Resolve the branch from rebase-merge/head-name when HEAD is detached. Text comes in through stdin or a file. Add to §4.6.
- (b) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Wrong rebase targets from stale or garbled memories.

**Answer:** —

**Recorded in:** —

## Q80 (R77, medium): design-artifact lookup: mapping a branch to its slug and root, and slug collisions

**Status:** open

**Where:** 08-implement-lifecycle.md §8.1, 02-repos-and-config.md §2.3, §2.5, 06-lifecycles.md §6.6, 07-design-lifecycle.md §7.1, §7.8

**Problem:** Getting the slug back by stripping branch_prefix breaks if the prefix changes. Searching 'either root' is ambiguous when both roots hold a folder with the slug. A slug reused after a merge, or a slug like `adr`, collides with an existing `repos/<key>/docs/<slug>/`, so it is overwritten at approve-design or fails at the very end. 'Committed' isn't verified against HEAD.

**Question:** How is a branch's artifact identified?

- (a) approve-design records slug, root, path and commit SHA in the per-branch state. design-artifact reads only that and checks it with git cat-file. create-slug refuses a folder that already exists, in either root.
- (b) Name folders by `<branch-file>`.
- (c) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Implement reads another feature's design, or an approved design gets overwritten.

**Answer:** —

**Recorded in:** —

## Q81 (R78, medium): Rebase protocol: conflicts, dirty tree, running jobs, mid-implement rebases, --onto state

**Status:** open

**Where:** 10-review-lifecycle.md §10.2, 09-run-jobs.md §9.3, 08-implement-lifecycle.md §8.3, 03-watch.md §3.5

**Problem:** There is no continue or abort contract, no rule for a dirty tree, and nothing stops jobs from running on a half-rebased tree. A session that dies mid-rebase leaves detached HEAD state, which gets gated anyway. A rebase between SDD tasks invalidates the SHAs in upstream's ledger and its final review. The first --onto has no 'last tip'. A tip recorded before a manual rebase replays duplicates. Whether the parent is local or on origin is undefined. The fetch runs outside watch's refs lock.

**Question:** What is the rebase contract?

- (a) Stop the worktree's jobs and refuse a dirty tree. On conflict exit non-zero and list the files. `--continue` checks that no unmerged paths or markers remain, and `--abort` restores ORIG_HEAD. `omc run` and --done refuse while a rebase is in progress. Rebasing during implement is deferred to review. When there is no tip or it's invalid, fall back to merge-base. The fetch is a watch sync request.
- (b) Let the LLM drive raw git.

**Recommendation:** (a).

**Cost if wrong:** Corrupted SDD state, and half-rebased trees getting gated.

**Answer:** —

**Recorded in:** —

## Q82 (R79, medium): Publish: triage when forge state is unknown, replies built from stale decisions, isolating comment text

**Status:** open

**Where:** 11-publish-lifecycle.md §11.2, §11.3, §11.5, 01-principles.md §1.2, §1.3, 10-review-lifecycle.md §10.3, 08-implement-lifecycle.md §8.3

**Problem:** Without forge tools or auth, triage falls through to create-mr, which force-pushes over open threads. Replies are built from brainstorm decisions that hardening, rulings or deviations may since have changed, so they claim things that aren't true. Raw comment text from anyone, including on public repos, enters a session that holds push and forge-write power, and its output is posted with no approval. Regenerating the description overwrites edits people made. The ticket bounces back to In Review from later states.

**Question:** How are these publish edge cases handled?

- (a) Triage has three outcomes, none, comments or unknown, and unknown asks before pushing. Raw threads go to a data file. Replies are reconciled with the round's rulings and deviations, and threads that can't be reconciled are shown to you. Description updates replace only an omc block between markers. Ticket moves only go forward.
- (b) Keep as written.

**Recommendation:** (a). Add a 'post N replies?' confirmation for repos with outside contributors.

**Cost if wrong:** Comments ignored, false public replies, and human edits lost.

**Answer:** —

**Recorded in:** —

## Q83 (R80, medium): E2E policy: custom milestone gate vs hardcoded ci-gate, and what configured:false means

**Status:** open

**Where:** 08-implement-lifecycle.md §8.4, 10-review-lifecycle.md §10.5, 09-run-jobs.md §9.2, §9.7, 03-watch.md §3.4

**Problem:** Milestone-gate is a separate plugin so a repo can change its E2E policy (`just up` first, or no E2E). Doing that means the LLM starts environments outside watch, and ci-gate's hardcoded `omc run e2e-tests` ignores the policy anyway. configured:false has no source key, no job-ID semantics and no poll field, and an integration that failed can look the same as 'not configured'.

**Question:** Where does E2E policy live?

- (a) In the e2e-tests job definition: pre-steps and an explicit `e2e.configured: false` written by /auto-integrate. Both gates just call `omc run e2e-tests`. configured:false returns a finished job with that field, and a failed setup fails.
- (b) Document that both plugins must be overridden.

**Recommendation:** (a). Rename verify.keep_alive to e2e.keep_alive.

**Cost if wrong:** E2E environments outside watch, and policies the two gates apply differently.

**Answer:** —

**Recorded in:** —

## Q84 (R81, medium): docs_grep: reading documents, global scope, missing paths, ordering, design artifacts, CLI form

**Status:** open

**Where:** 04-mcp-and-cli.md §4.3, §4.4, §4.6, 03-watch.md §3.5, §3.7, 02-repos-and-config.md §2.3

**Problem:** After a hit there is no way to read the document, apart from abusing grep under the cap. Global scope is undefined for wikis, for repos that aren't ready, and for the global docs alone, and it has no CLI form. A deleted doc path makes rg exit 2 and leaks clone paths in stderr. The scan has no time or size bound across 40 repos. Results come in no fixed order, so truncation is random. Past designs in omc mode are never searched. A wiki enabled but not yet generated has no behaviour.

**Question:** What is docs_grep's full contract?

- (a) Add docs_read(display_path, range). Scopes are repo, global-docs and all, and repos that aren't ready are listed in a header line. A missing path produces one stale-config line and the remaining paths are searched; stderr is rewritten. There is one deadline per call plus --max-count. Results are sorted by root and path. In omc mode, repos/<key>/docs is included. Top-level `omc docs-grep` with --scope.
- (b) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Agents can't follow up on hits, and searches return results that vary run to run.

**Answer:** —

**Recorded in:** —

## Q85 (R82, medium): Unclear repo.yaml changes, invalid config and removal semantics

**Status:** open

**Where:** 03-watch.md §3.1, §3.2, 02-repos-and-config.md §2.3 Removing a repo, §2.4, §2.5, 07-design-lifecycle.md §7.1

**Problem:** Reconcile covers only adding and deleting a repo. The design doesn't say what changing base_branch, documentation or ssh_url does. Malformed YAML, including conflict markers left by a failed sync, has no state. Deleting a folder removes design history, snippets and the suggestion box; it orphans open worktrees, which then can't be closed without repo.yaml; it leaves trust and cache in place; and the 'no worktrees remain' check needs `git worktree prune`. Reading the working tree mid-rebase can make a folder look deleted. Watch doesn't say when it re-reads local config, so a trust answer may not take effect.

**Question:** How does reconcile handle changes, invalid files and removal?

- (a) Re-read both configs each tick and apply them live, except mcp.port. Keep the last good config and log invalid files. Treat ssh_url as immutable. A base_branch change resets and re-indexes the repo and marks it stale. Add `omc repo <repo> remove`, which revokes trust, keeps docs, refuses while worktrees are open, prunes and cleans up. Reconcile runs after sync, never mid-rebase, and stops watching a folder only after two stable reads.
- (b) Keep as written.

**Recommendation:** (a).

**Cost if wrong:** Lost design history, and stuck or phantom repos.

**Answer:** —

**Recorded in:** —

## Q86 (R83, medium): Config key registry and hidden constants

**Status:** open

**Where:** 01-principles.md §1.2, 02-repos-and-config.md §2.4, §2.5, 03-watch.md §3.3, §3.7, §3.8, 04-mcp-and-cli.md §4.3, 05-skill-rendering.md §5.3, §5.6, 07-design-lifecycle.md §7.1, 09-run-jobs.md §9.2, §9.3, §9.4, 10-review-lifecycle.md §10.1, 11-publish-lifecycle.md §11.4

**Problem:** Several values have no key or no file: the one-minute add-repo poll, the 30-day backups, 'once a day', slug.max_length (no default), hook_stdout_max_chars, stages.max_rounds, run_time_limit_minutes and split_suggest_lines. `review:` is a plugin list in one file and a model block in another. Retention has three overlapping keys. Naming mixes dotted and flat forms. The merge rules (deep merge, replacing lists) are only described as 'repo wins'. 'auth' and 'server addresses' are undefined.

**Question:** Is there one registry of config keys?

- (a) A single schema table in §2.5 listing key, file, default and apply command for each. Namespaces lifecycles.<name>.plugins, providers.<name>, run.*, retention.*, publish.split_suggest_lines. Maps deep-merge and lists replace. auth holds only references to environment variables or the keychain, and the file is mode 0600.
- (b) Leave it to the implementation.

**Recommendation:** (a).

**Cost if wrong:** Hidden constants, and keys whose YAML type can't be loaded.

**Answer:** —

**Recorded in:** —

## Q87 (R84, medium): Cache layout gaps: job state, scratch worktrees, logs retention

**Status:** open

**Where:** 02-repos-and-config.md §2.4, 03-watch.md §3.4, §3.6, §3.8, §3.9, 09-run-jobs.md §9.2, §9.4, §9.5

**Problem:** The cache tree doesn't include job state, round counters, pass hashes, add-repo jobs, or scratch worktrees. Scratch worktrees block clone removal and survive crashes. Log files are named `<job>.log`, so concurrent worktrees collide, and logs and the jobs/ folder are never cleaned up. Global jobs such as conflict resolution have nowhere to log. Polls hand out paths inside the cache. Log files get no private mode.

**Question:** Where do these live and when are they cleaned up?

- (a) `state/jobs/<id>.json` with ULID ids; `repos/<key>/scratch/<job-id>` removed at job end and at start, and excluded from worktree counts; logs at `logs/<type>-<id>/` swept on the /tmp rule; global jobs log under `~/.omc2/watch/logs`; polls return a log handle, not a path; mode 0600/0700.
- (b) Leave to the implementation.

**Recommendation:** (a).

**Cost if wrong:** Unbounded disk growth and clones that can never be removed.

**Answer:** —

**Recorded in:** —

## Q88 (R85, medium): Watch writes to the omc repo: git state, the session write path, provenance

**Status:** open

**Where:** 02-repos-and-config.md §2.3, 03-watch.md §3.3, 04-mcp-and-cli.md §4.3, 09-run-jobs.md §9.6

**Problem:** Watch commits without checking the branch, in-progress operations, a detached HEAD, index.lock, or user pre-commit and signing hooks. Sessions that fix hooks or snippets have no tool to send writes through watch. Nothing records which files omc wrote, so 'yours vs mine' can't be decided on later reruns. omc-written suggestion and docs commits retrigger setup (covered under the retry question).

**Question:** What does watch check before committing, and how do sessions write?

- (a) Preflight: the expected branch, no git operation in progress, not detached; brief retries on index.lock; commit with --no-verify and no signing, set by an `omc_repo.run_git_hooks: false` key. A tool `omc_repo_commit(paths, message)` restricted to omc's paths. Content hashes of files omc wrote are kept for provenance.
- (b) Leave it to git errors.

**Recommendation:** (a).

**Cost if wrong:** Commits on the wrong branch, or a headless watch blocked on a pinentry prompt.

**Answer:** —

**Recorded in:** —

## Q89 (R86, medium): Coexistence leftovers: v1's global layer in .omc repos, fish hooks, cutover, distribution name

**Status:** open

**Where:** 01-principles.md §1.3, §1.5, README.md §Naming, 04-mcp-and-cli.md §4.1, §4.6, §4.7, 02-repos-and-config.md §2.4, 11-publish-lifecycle.md §11.3

**Problem:** Repos already integrated with v1 carry `.omc/` into v2 worktrees, so v1's behaviour layer (its gates, /omc:finish and models) fires there. The v1 and v2 fish title hooks fight over the tab, and a v2 conf.d hook contradicts 'no shell-startup launches'. Title failures outside iTerm2 and Docker, and v2 launchers, are unspecified. Cutover has no definition: what happens to ~/.omc2, the MCP name and check-artifact literals. If both versions use the same uv distribution name, installing one replaces the other. Branch names from v1 and v2 can collide.

**Question:** How is coexistence completed?

- (a) v2's fenced section applies under worktree_location and overrides v1 there (v1 is told to skip it). No v2 fish hook before cutover. Titles are best-effort and gated by environment, never fatal, and set after branch-name. Cutover renames only user-visible names, and `~/.omc2` stays. Distribution `oh-my-clanker-v2`. Use a v2/ branch_prefix during coexistence.
- (b) Require v1 uninstall.

**Recommendation:** (a).

**Cost if wrong:** v1 rules govern v2 sessions, and installs overwrite each other.

**Answer:** —

**Recorded in:** —

## Q90 (R87, medium): MCP registration: localhost vs 127.0.0.1, changing the port, server identity, drift

**Status:** open

**Where:** 04-mcp-and-cli.md §4.1, 02-repos-and-config.md §2.5, 03-watch.md §3.1, 07-design-lifecycle.md §7.1

**Problem:** Registrations hard-code `localhost:47850` while the server binds 127.0.0.1, so a client that tries ::1 first can fail, and host validation may reject `localhost`. Changing mcp.port has no apply command. A busy port has no defined failure. check-watch treats any process that answers as watch. filelock can't record the PID that §3.1 promises. Registering at user scope adds schemas to every session in every repo. A Codex TOML edit needs a TOML writer that isn't approved. Removal on uninstall is undefined.

**Question:** How are the address, identity and registration handled?

- (a) Register `127.0.0.1:<mcp.port>` from config, with an apply command to re-register; allow both host forms. Take the lock, write watch.pid, bind, and exit naming the holder if the port is busy. check-watch calls a watch_info tool that returns version and PID. Codex is registered with `codex mcp add --url` plus tool_timeout_sec. uninstall reverses the registration.
- (b) A fixed port.

**Recommendation:** (a).

**Cost if wrong:** Silent connection failures, and a squatter on the port posing as omc.

**Answer:** —

**Recorded in:** —

## Q91 (R88, medium): Watch output: standing conditions, progress model, log noise

**Status:** open

**Where:** 03-watch.md §3.9, 02-repos-and-config.md §2.3, §2.6, 03-watch.md §3.3, §3.4

**Problem:** An append-only log can't keep a trust request visible 'until answered', and repeating it each tick floods the log. Five places show live progress but nothing defines where that progress comes from. uvicorn and child processes write to the TTY and break the rich Live display. The line format, and non-TTY output used in Docker tests, are undefined.

**Question:** How does watch present state?

- (a) A pinned status area for standing conditions, with one log line when each starts and one when it clears. One in-process job record holding step, i/n and percent feeds every surface. Child processes never inherit the TTY. A normative line format and a plain mode for non-TTY output.
- (b) Rate-limited repeats.

**Recommendation:** (a).

**Cost if wrong:** Trust requests get missed, and the progress shown disagrees between surfaces.

**Answer:** —

**Recorded in:** —

## Q92 (R89, medium): Tool prerequisites and dependency vetting

**Status:** open

**Where:** 01-principles.md §1.3, §1.4, 04-mcp-and-cli.md §4.4, §4.6, 02-repos-and-config.md §2.4, 07-design-lifecycle.md §7.1 step 1, 05-skill-rendering.md §5.6

**Problem:** rg, wt, git, Node, Docker and the harness CLIs are never checked, so a missing one surfaces deep in a job. The carried dependencies (pyyaml, mininterface, iterm2, filelock) were never vetted against the staleness bar that rejected Jinja2. mcp is pinned without its transitive HTTP stack. Toolchain auto-downloads (uv python, rustup, corepack) have no rule. ABORT install commands invite the model to run them itself.

**Question:** What is checked and vetted?

- (a) A 'required system tools' table with minimum versions, checked at watch start and in check-watch with exact install commands. One vetting row per dependency, carried ones included. A locked install or exact pins plus a CI advisory job. Toolchain downloads are allowed when they come from the repo's pinned files after trust. ABORT text says 'tell the user; don't run it'.
- (b) Check lazily.

**Recommendation:** (a).

**Cost if wrong:** Late failures, dependencies nobody vetted, and installs nobody supervised.

**Answer:** —

**Recorded in:** —

## Q93 (R90, medium): MVP references to parked or undefined pieces

**Status:** open

**Where:** README.md §MVP, 05-skill-rendering.md §5.5, 06-lifecycles.md §6.4, 08-implement-lifecycle.md §8.4, 09-run-jobs.md §9.7, open-questions.md §H, 05-skill-rendering.md §5.2, §5.6, 08-implement-lifecycle.md §8.3, 10-review-lifecycle.md §10.6, 11-publish-lifecycle.md §11.5, 12-session-memory.md §12.3

**Problem:** The text recommends writing a lifecycle plugin, while plugin locations are parked. Fix-e2e redirects to v1's /investigate, which refuses to run without a repo-local .omc. Six 'Assumed (not yet confirmed)' sections and the unconfirmed 8000 value are neither decided nor listed in open-questions.md, and the README's MVP rule pulls them into the MVP. The ops survey gates queryability although the only skill that reads it is parked.

**Question:** How are these treated in the MVP?

- (a) The MVP allows only omc-shipped plugins; reword 5.5, 6.4 and 8.4. Drop the /investigate redirect and don't gate on the survey. Confirm the load-bearing assumptions (10.6, 11.5, 12.3) into the body text and list the rest in open-questions.md.
- (b) Decide plugin locations now.

**Recommendation:** (a).

**Cost if wrong:** MVP features point at things that don't exist.

**Answer:** —

**Recorded in:** —

## Q94 (R91, medium): 13.0: format of definitions, mapping to code, protection enforcement, citing design parts

**Status:** open

**Where:** 13-testing.md §13.0, AGENTS.md, 08-implement-lifecycle.md §8.3, open-questions.md §L4

**Problem:** Enforcement 'by hand' can't stop subagent builds that never stop to ask: they edit design/ or e2e-tests/ and log a Ruling. Definitions have no template and no mapping to tests/e2e, so unprotected code can quietly assert less than its definition. Citations by section number go stale. Scenario branches and judge rubrics fall outside both folders. design/ statements that are host-only, parked or Kraken-related have no exemption marker.

**Question:** How is §13.0 made checkable now?

- (a) A CI guard fails diffs to protected folders that lack an approval trailer. Definition template: kind, covers, why, design parts, numbered expectations; code at tests/e2e/<same-stem> cites each expectation. Adopt L4's fact ids for this repo now. Scenario state is generated from its definition. Exemptions are marked inline.
- (b) Keep enforcement manual.

**Recommendation:** (a).

**Cost if wrong:** Protection on paper only, and definitions that silently drift.

**Answer:** —

**Recorded in:** —

## Q95 (R92, low): Branch detection and the definition of an omc worktree

**Status:** open

**Where:** 02-repos-and-config.md §2.4, 12-session-memory.md §12.3, 05-skill-rendering.md §5.4

**Problem:** rev-parse --abbrev-ref returns HEAD while detached, and keying data only by origin URL and branch merges a user's own checkout with omc's. Nothing defines what an 'omc worktree' is.

**Question:** How is the worktree resolved?

- (a) Its git-common-dir must be a known hidden clone, and the branch comes from `git worktree list --porcelain`.
- (b) A registry recorded when the worktree is created.

**Recommendation:** (a).

**Cost if wrong:** Memory and per-branch data filed under the wrong branch.

**Answer:** —

**Recorded in:** —

## Q96 (R93, low): Small corrections in the text

**Status:** open

**Where:** 02-repos-and-config.md §2.4 branch-file example, 05-skill-rendering.md §5.2, 10-review-lifecycle.md §10.2 base vs base_branch, 02-repos-and-config.md §2.3 commit example, 04-mcp-and-cli.md §4.3, §4.6, 07-design-lifecycle.md §7.1, 03-watch.md §3.4, README.md

**Problem:** The branch-file example hash is wrong: it is 7d6cc14f, not 3f9a1c2e. §5.2 says Skill-tool preprocessing is both verified and still to verify. §10.2 says `base` where repo.yaml uses `base_branch`. The commit example credits explain-context to auto-integrate rather than auto-index. worktree_create(repo, slug) and create-worktree <repo> <branch> differ, and `omc repo add` duplicates `internal add-repo`. The --headless flag list leaves out publish. The v1 reference document is an untracked file in a feature worktree.

**Question:** Apply these corrections?

- (a) Yes: correct the hash and state UTF-8; delete the 'still to verify' bullet; standardise on base_branch; attribute explain-context to auto-index; one create_worktree(repo, branch, slug); `omc repo add` = add-repo plus poll; list publish's flags; commit the v1 reference to v1 main.
- (b) Leave as is.

**Recommendation:** (a).

**Cost if wrong:** Tests copied from the wrong vector, and mismatched implementations.

**Answer:** —

**Recorded in:** —
