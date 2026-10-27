# Decision Log

*Append-only. Every ruling and its reasoning, dated.*

## 1. Review: adversarial-design-review (2026-10-27)

Every open design question, asked one at a time, with your answer. Sources: the adversarial design review ([2026-10-16-adversarial-design-review](reviews/2026-10-16-adversarial-design-review.md "git:c29519177f29"), items R1 to R98) and its open E2E questions E1 to E3. Each answer is also written into `docs/design/` in the same turn.
Review file (open): docs/reviews/2026-10-16-adversarial-design-review.md

### 1.1 MVP scope of multi-repo work

**Context.** [1.1](design/01-principles.md#1.1%20What%20v2%20is "git:c29519177f29") says a feature can span several repos with full integration, and [13.2](design/13-testing.md#13.2%20The%20E2E%20tests "git:c29519177f29") requires E2E tests of multi-repo work on a four-repo diamond. But [open-questions §H](design/open-questions.md "git:c29519177f29") parks cross-repo features, and the [README](design/README.md "git:c29519177f29") leaves §H out of the MVP. Every lifecycle structure is keyed by one repo plus one branch: the lifecycle folder, the artifact root, session memory, one Primary ticket, one MR. The tests can't be written, and if one feature later touches several repos, all of those keys have to be redone. Is MVP multi-repo limited to watching many repos and adding or querying them mid-design, with each feature still changing exactly one repo?
**Decision.** Neither (a) nor (c): both are MVP. 1. Working on one repo, it must be easy to add, index and gather information from other repos in full depth. 2. Changing several repos is supported too: one design spans several repos. Each repo gets a worktree (worktrunk) with the same slug. The main design creates sub-designs in the related repos. `/design`, `/implement` and `/review` each run in their own repo with full repo-local omc context, no different from running the task directly there. Implementation builds the repos in order, each inside its own repo, never from the main repo. Amended 2026-10-27 (with [R94. How sub-designs are made](reviews/2026-10-16-adversarial-design-review.md#R94.%20[blocker]%20How%20sub-designs%20are%20made "git:c29519177f29")): changing several repos (point 2) is **not** MVP, but a design guideline: the MVP must not prevent it.
**Affected.** [14-cross-repo-features](design/14-cross-repo-features.md "git:c29519177f29"), [1.1](design/01-principles.md#1.1%20What%20v2%20is "git:c29519177f29"), [open-questions](design/open-questions.md "git:c29519177f29")
**Source.** [R1. [blocker] MVP scope of multi-repo work](reviews/2026-10-16-adversarial-design-review.md#R1.%20[blocker]%20MVP%20scope%20of%20multi-repo%20work "git:c29519177f29")
**Status.** recorded 2026-10-27 · applied 2026-10-27
Answers: R1

### 1.2 Trust: index-only by default, trusted repos and mirrors, user-only trust commands

**Context.** Trust grants code execution, and reset-rounds is what makes the fix loop's CRITICAL stop bounded. Under the 'CLI = MCP and vice versa' rule both become MCP tools on an endpoint with no authentication. The stub's `allowed-tools: Bash(omc …)` also pre-approves them as shell commands. The add-repo poll even prints the exact trust command for the agent. A prompt-injected agent, any local process or another local user can trust an attacker repo and run its code, or reset the fix budget. Frontmatter user-only flags don't help: they only block the Skill tool, not a direct `omc lifecycle publish` from Bash. Which commands are user-only, and what enforces that?
**Decision.** Trust supports whole mirrors, e.g. a company's. External mirrors can never be in the multi-repo chain apart from GitNexus indexing. Anything that runs build scripts must be explicitly listed, and the CLI command for that is not an MCP tool and is explicitly forbidden to the agent. The other gates are review item [R98. The other user-only gates: reset-rounds, configure, and unauthenticated MCP](reviews/2026-10-16-adversarial-design-review.md#R98.%20[blocker]%20The%20other%20user-only%20gates:%20reset-rounds,%20configure,%20and%20unauthenticated%20MCP "git:c29519177f29").
**Affected.** [2.6](design/02-repos-and-config.md#2.6%20Trust "git:c29519177f29"), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules "git:c29519177f29"), [4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree "git:c29519177f29"), [5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs "git:c29519177f29")
**Source.** [R2. [blocker] The agent can run the user-only gates: trust, trust --all, reset-rounds, configure](reviews/2026-10-16-adversarial-design-review.md#R2.%20[blocker]%20The%20agent%20can%20run%20the%20user-only%20gates:%20trust,%20trust%20--all,%20reset-rounds,%20configure "git:c29519177f29")
**Status.** recorded 2026-10-27 · applied 2026-10-27
Answers: R2

### 1.3 How sub-designs are made

**Context.** The main design creates sub-designs in the related repos, and `/design` runs in each repo with full repo-local context. It is not settled whether each sub-design is a full design session of its own (brainstorm, hardening, plan, approval with you, in that repo's worktree), or whether the main session writes the sub-designs and each repo only hardens, plans and approves them. `omc design` today also creates the worktree itself and refuses an existing branch. What runs in each related repo to produce its sub-design?
**Decision.** None of the options; `omc design` can't know the repos before the design exists. Design: `/design` in the main repo produces one main design covering every repo, using full omc context of each related repo, and hardens it across the sub-repos from the main repo. Then one hardening subagent per sub-repo, in build order, each with that repo's context only. Then a final pass over the main design integrates the findings and alerts the user to problems. Implement: the main repo's agent orchestrates subagents that implement each repo's part in build order, in their own sub-repos. Review, staged: each sub-repo is reviewed individually by a subagent running the review lifecycle there, in order; the changes are integrated so the whole chain builds; then the final `/review` runs in the main repo. Not MVP, but a design guideline so nothing built prevents adding it later.
**Affected.** [14.2](design/14-cross-repo-features.md#14.2%20Changing%20several%20repos%20in%20one%20feature%20(not%20MVP;%20a%20design%20guideline) "git:c29519177f29"), [14.3](design/14-cross-repo-features.md#14.3%20What%20the%20MVP%20must%20not%20prevent%20(assumed,%20not%20yet%20confirmed) "git:c29519177f29"), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules "git:c29519177f29"), [MVP](design/README.md#MVP "git:c29519177f29")
**Source.** [R94. [blocker] How sub-designs are made](reviews/2026-10-16-adversarial-design-review.md#R94.%20[blocker]%20How%20sub-designs%20are%20made "git:c29519177f29")
**Status.** recorded 2026-10-27 · applied 2026-10-27
Answers: R94

### 1.4 Parked

R95 and R96 are parked with [14.2](design/14-cross-repo-features.md#14.2%20Changing%20several%20repos%20in%20one%20feature%20(not%20MVP;%20a%20design%20guideline) "git:c29519177f29") and are not MVP.
**Status.** note

### 1.5 Provider fixed at launch; subagent models resolved live by complexity

**Context.** [R49](reviews/2026-10-16-adversarial-design-review.md#R49.%20[high]%20Model%20block%20schema:%20per%20provider,%20orchestrator%20slot,%20publish,%20review%20and%20subagent%20slots,%20pinning "git:9d2a6a6291c5") identifies conflicting model-selection contracts: [2.5](design/02-repos-and-config.md#2.5%20Config "git:9d2a6a6291c5") describes a provider and model set per lifecycle, while [8.1](design/08-implement-lifecycle.md#8.1%20Shape "git:9d2a6a6291c5") describes model slots per provider. The design needs one rule for provider selection and for resolving task models without embedding provider-specific model names in design and plan artifacts.
**Decision.** The provider is selected only in the initiating omc call, such as `omc design --claude`, and remains fixed once that provider has been launched; neither the running session nor its subagents switch providers. Designs and implementation plans use complexity markers matching the OMC configuration, never specific model names. Whenever it launches a subagent, the orchestrator looks up the current configuration for its own provider, resolves the task's complexity class to the configured model, and assigns that model to the subagent.
**Affected.** [2.5](design/02-repos-and-config.md#2.5%20Config "git:9d2a6a6291c5"), [07-design-lifecycle](design/07-design-lifecycle.md "git:9d2a6a6291c5"), [08-implement-lifecycle](design/08-implement-lifecycle.md "git:9d2a6a6291c5"), [10.1](design/10-review-lifecycle.md#10.1%20Shape "git:9d2a6a6291c5"), [11.1](design/11-publish-lifecycle.md#11.1%20Shape "git:9d2a6a6291c5")
**Source.** [R49. [high] Model block schema: per provider, orchestrator slot, publish, review and subagent slots, pinning](reviews/2026-10-16-adversarial-design-review.md#R49.%20[high]%20Model%20block%20schema:%20per%20provider,%20orchestrator%20slot,%20publish,%20review%20and%20subagent%20slots,%20pinning "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R49

### 1.6 Feedback requirements: full harness and final SPEC/PLAN consolidation

**Context.** [R5](reviews/2026-10-16-adversarial-design-review.md#R5.%20[blocker]%20Publish%20has%20no%20way%20to%20re-enter%20the%20design%20lifecycle%20for%20a%20feedback%20round "git:9d2a6a6291c5") exposes missing feedback-iteration contracts across the lifecycles. The owner has specified how feedback must be considered and what fixes and final artifacts must satisfy, but has not yet decided the best mechanism for clean repeated iterations.
**Decision.** All MR feedback and review-agent feedback must be considered against the full design through Superpowers brainstorming, with Superpowers deciding whether extensive brainstorming is warranted or a lightweight change suffices, without calling `/design` again. Fixes must flow through the same full harness: brainstorming, design hardening, implementation with proper building, testing and review, full branch review by its review agents, squashing, spec/plan merging and MR-description update. Artifacts must be preserved during iteration and accepted addenda deliberately consolidated into exactly one final SPEC and one PLAN for the final squashed MR push; clean repeated iterations still need to be designed, and no iteration mechanism has been decided.
**Affected.** [06-lifecycles](design/06-lifecycles.md "git:9d2a6a6291c5"), [07-design-lifecycle](design/07-design-lifecycle.md "git:9d2a6a6291c5"), [08-implement-lifecycle](design/08-implement-lifecycle.md "git:9d2a6a6291c5"), [10-review-lifecycle](design/10-review-lifecycle.md "git:9d2a6a6291c5"), [11-publish-lifecycle](design/11-publish-lifecycle.md "git:9d2a6a6291c5")
**Source.** [R5. [blocker] Publish has no way to re-enter the design lifecycle for a feedback round](reviews/2026-10-16-adversarial-design-review.md#R5.%20[blocker]%20Publish%20has%20no%20way%20to%20re-enter%20the%20design%20lifecycle%20for%20a%20feedback%20round "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R5

### 1.7 Question routing: consult existing material before escalating

**Context.** During discussion of [R5](reviews/2026-10-16-adversarial-design-review.md#R5.%20[blocker]%20Publish%20has%20no%20way%20to%20re-enter%20the%20design%20lifecycle%20for%20a%20feedback%20round "git:9d2a6a6291c5"), the owner was asked whether an orchestrator should relay every worker question or answer from existing decisions. The owner required escalation only for materially new questions that existing material cannot answer; this settles question routing, while the wider iteration architecture remains under discussion.
**Decision.** Before asking the owner, the orchestrator consults the existing design, plans, recorded rulings and review/iteration material. It answers worker questions already settled by that material and escalates only materially new questions that cannot be answered from it. This question-routing policy does not grant new approvals or treat a genuinely required new approval as implied by past material.
**Affected.** [06-lifecycles](design/06-lifecycles.md "git:9d2a6a6291c5"), [07-design-lifecycle](design/07-design-lifecycle.md "git:9d2a6a6291c5"), [08-implement-lifecycle](design/08-implement-lifecycle.md "git:9d2a6a6291c5"), [10-review-lifecycle](design/10-review-lifecycle.md "git:9d2a6a6291c5"), [11-publish-lifecycle](design/11-publish-lifecycle.md "git:9d2a6a6291c5")
**Source.** [R5. [blocker] Publish has no way to re-enter the design lifecycle for a feedback round](reviews/2026-10-16-adversarial-design-review.md#R5.%20[blocker]%20Publish%20has%20no%20way%20to%20re-enter%20the%20design%20lifecycle%20for%20a%20feedback%20round "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R5

### 1.8 Feedback iterations: owner decides when to stop, no automatic count cap

**Context.** During discussion of [R5](reviews/2026-10-16-adversarial-design-review.md#R5.%20[blocker]%20Publish%20has%20no%20way%20to%20re-enter%20the%20design%20lifecycle%20for%20a%20feedback%20round "git:9d2a6a6291c5"), a configurable cap on complete feedback cycles was proposed separately from build/test retries. The owner rejected that cap because the human remains involved in answering questions and will decide when enough iteration has occurred.
**Decision.** Complete feedback iterations have no automatic round or count cap; the owner remains in the loop for materially new questions and decides when to stop. The existing policy of answering worker questions from existing material and escalating only materially new questions that it cannot answer remains in force. This applies only to complete feedback cycles and does not remove or change existing bounded build/test job-repair budgets.
**Affected.** [06-lifecycles](design/06-lifecycles.md "git:9d2a6a6291c5"), [11-publish-lifecycle](design/11-publish-lifecycle.md "git:9d2a6a6291c5")
**Source.** [R5. [blocker] Publish has no way to re-enter the design lifecycle for a feedback round](reviews/2026-10-16-adversarial-design-review.md#R5.%20[blocker]%20Publish%20has%20no%20way%20to%20re-enter%20the%20design%20lifecycle%20for%20a%20feedback%20round "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R5

### 1.9 MR splitting: outside MVP, retained as a future design consideration

**Context.** [R46](reviews/2026-10-16-adversarial-design-review.md#R46.%20[high]%20Splitting%20a%20huge%20MR:%20chunk%20worktrees,%20failures,%20push%20and%20verification,%20later%20rounds "git:9d2a6a6291c5") asks whether splitting a feature into stacked MRs belongs in the MVP, given the unresolved execution and later-round contracts in [11.4](design/11-publish-lifecycle.md#11.4%20Splitting%20a%20huge%20MR "git:9d2a6a6291c5"). The owner answered: "Not needed but should be considered for the design."
**Decision.** Splitting a feature into stacked MRs is not required for the MVP and remains a future design consideration. This ruling does not prescribe the deferred splitting mechanics.
**Affected.** [11.4](design/11-publish-lifecycle.md#11.4%20Splitting%20a%20huge%20MR "git:9d2a6a6291c5"), [MVP](design/README.md#MVP "git:9d2a6a6291c5")
**Source.** [R46. [high] Splitting a huge MR: chunk worktrees, failures, push and verification, later rounds](reviews/2026-10-16-adversarial-design-review.md#R46.%20[high]%20Splitting%20a%20huge%20MR:%20chunk%20worktrees,%20failures,%20push%20and%20verification,%20later%20rounds "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R46

### 1.10 Remote CI: no post-push monitoring or automatic repair for now

**Context.** The narrowed [R51](reviews/2026-10-16-adversarial-design-review.md#R51.%20[high]%20The%20ci%20job:%20scope,%20CI%20steps%20that%20can't%20run%20locally,%20and%20its%20fix%20skill "git:9d2a6a6291c5") question asked whether OMC should push, monitor required remote CI and fix failures before reporting publication complete. The owner answered: "no, for now it should not monitor CI".
**Decision.** For now, OMC does not monitor remote CI after pushing and does not add automatic post-push CI polling or a remote-CI repair loop. Local pre-push checks remain in place, and publication reporting states only what was verified without claiming that remote CI passed.
**Affected.** [9.2](design/09-run-jobs.md#9.2%20Commands "git:9d2a6a6291c5"), [10.5](design/10-review-lifecycle.md#10.5%20%60ci-gate%60 "git:9d2a6a6291c5"), [11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60 "git:9d2a6a6291c5")
**Source.** [R51. [high] The ci job: scope, CI steps that can't run locally, and its fix skill](reviews/2026-10-16-adversarial-design-review.md#R51.%20[high]%20The%20ci%20job:%20scope,%20CI%20steps%20that%20can't%20run%20locally,%20and%20its%20fix%20skill "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R51

### 1.11 Updates adopt changed defaults while preserving explicit overrides

**Context.** [R4](reviews/2026-10-16-adversarial-design-review.md#R4.%20[blocker]%20Writing%20every%20key's%20default%20into%20repo.yaml%20disables%20the%20shared%20config%20layer%20and%20freezes%20old%20defaults "git:9d2a6a6291c5") concerns inherited defaults being frozen as explicit configuration. The foreground asked: "I recommend updates automatically adopt new OMC defaults for settings you haven’t overridden, while preserving your explicit overrides. Should updates work that way?" The owner answered: "yes".
**Decision.** Updates adopt changed OMC defaults for settings without explicit user overrides while preserving explicit overrides. Inherited values are not treated as frozen explicit choices.
**Affected.** [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules "git:9d2a6a6291c5"), [2.5](design/02-repos-and-config.md#2.5%20Config "git:9d2a6a6291c5"), [6.1](design/06-lifecycles.md#6.1%20Lifecycles "git:9d2a6a6291c5")
**Source.** [R4. [blocker] Writing every key's default into repo.yaml disables the shared config layer and freezes old defaults](reviews/2026-10-16-adversarial-design-review.md#R4.%20[blocker]%20Writing%20every%20key's%20default%20into%20repo.yaml%20disables%20the%20shared%20config%20layer%20and%20freezes%20old%20defaults "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R4

### 1.12 E2E fixtures: reaffirm use of the four existing test repositories

**Context.** For [R23](reviews/2026-10-16-adversarial-design-review.md#R23.%20[high]%20E2E%20environment:%20SSH-only%20identity,%20writes%20to%20a%20real%20forge,%20open-source-only%20rule,%20macOS%20features "git:9d2a6a6291c5"), the foreground asked: "I recommend real GitHub test repositories for MR creation and comments, with isolated resources and cleanup. Should those tests use real GitHub?" The owner answered: "Didn't I already provide you with 4 test repos? Use them". This reaffirms the existing four-repository fixture requirement rather than choosing new infrastructure.
**Decision.** Use the four test repositories already specified in [13.2](design/13-testing.md#13.2%20The%20E2E%20tests "git:9d2a6a6291c5") for E2E testing, including forge-facing MR creation and comments. Do not provision substitute or additional test repositories or a local replacement forge; the existing four-repo and scenario constraints apply.
**Affected.** [13.2](design/13-testing.md#13.2%20The%20E2E%20tests "git:9d2a6a6291c5")
**Source.** [R23. [high] E2E environment: SSH-only identity, writes to a real forge, open-source-only rule, macOS features](reviews/2026-10-16-adversarial-design-review.md#R23.%20[high]%20E2E%20environment:%20SSH-only%20identity,%20writes%20to%20a%20real%20forge,%20open-source-only%20rule,%20macOS%20features "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R23

### 1.13 E2E tests: deterministic drivers by default, real agents for agent behavior

**Context.** For [E1](reviews/2026-10-16-adversarial-design-review.md#E1.%20[high]%20Which%20E2E%20tests%20use%20an%20LLM "git:9d2a6a6291c5"), the owner approved the current question's proposed testing policy and explicitly clarified that the answer applies only to that current question, not the upcoming question about executable hooks.
**Decision.** Deterministic E2E tests drive the CLI and MCP directly. Real Claude/Codex sessions are reserved for E2E tests whose subject is agent behavior.
**Affected.** [13.2](design/13-testing.md#13.2%20The%20E2E%20tests "git:9d2a6a6291c5")
**Source.** [E1. [high] Which E2E tests use an LLM](reviews/2026-10-16-adversarial-design-review.md#E1.%20[high]%20Which%20E2E%20tests%20use%20an%20LLM "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: E1

### 1.14 Trust the personal OMC repo and activate synced executable updates automatically

**Context.** For [R28](reviews/2026-10-16-adversarial-design-review.md#R28.%20[high]%20Executables%20in%20the%20omc%20repo%20run%20without%20trust%20after%20auto-sync "git:9d2a6a6291c5"), the owner approved the current question's recommendation to trust the personal OMC configuration repository as a whole and let synchronized executable-hook updates take effect without fresh approval for each change. The upcoming baseline-repair question was a preview and is not answered by this approval.
**Decision.** The personal OMC configuration repository is trusted as a whole. Synchronized updates to its executable hooks may run automatically without fresh per-change approval. This does not grant execution trust to product repositories or change their separate trust requirements.
**Affected.** [2.3](design/02-repos-and-config.md#2.3%20Your%20omc%20repo "git:9d2a6a6291c5"), [3.3](design/03-watch.md#3.3%20Sync%20every%20tick "git:9d2a6a6291c5"), [5.5](design/05-skill-rendering.md#5.5%20Hook%20contributions "git:9d2a6a6291c5")
**Source.** [R28. [high] Executables in the omc repo run without trust after auto-sync](reviews/2026-10-16-adversarial-design-review.md#R28.%20[high]%20Executables%20in%20the%20omc%20repo%20run%20without%20trust%20after%20auto-sync "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R28

### 1.15 Investigate and fix observed failures without a separate baseline-repair task

**Context.** For [R42](reviews/2026-10-16-adversarial-design-review.md#R42.%20[high]%20A%20red%20base%20vs%20the%20no-bypass%20rule "git:9d2a6a6291c5"), the owner rejected offering a separate baseline-repair task before feature implementation. Existing gates and usually CI are expected to keep the baseline healthy; an observed failure should prompt investigation of the current changes or a flaky test rather than an assumption that unrelated baseline breakage explains it.
**Decision.** Do not introduce a separate baseline-repair task for failures labeled unrelated. Investigate failures encountered during feature work, including whether the current changes caused them or exposed a flaky test, and debug and fix them through the normal harness. Do not dismiss those failures as an accepted broken baseline or bypass the existing gates.
**Affected.** [03-watch](design/03-watch.md "git:9d2a6a6291c5"), [09-run-jobs](design/09-run-jobs.md "git:9d2a6a6291c5"), [08-implement-lifecycle](design/08-implement-lifecycle.md "git:9d2a6a6291c5")
**Source.** [R42. [high] A red base vs the no-bypass rule](reviews/2026-10-16-adversarial-design-review.md#R42.%20[high]%20A%20red%20base%20vs%20the%20no-bypass%20rule "git:9d2a6a6291c5")
**Status.** recorded 2026-10-27
Answers: R42
