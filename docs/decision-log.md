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

### 1.16 Small text corrections from the review

**Context.** Review item R93 listed small places where the text contradicts itself or a checkable fact: the branch-file hash example in [02 §2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60) "git:797fb384d568"), a verified claim that [05 §5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs "git:797fb384d568") also lists as still to verify, the key named `base` in [10 §10.2](design/10-review-lifecycle.md#10.2%20%60rebase%60 "git:797fb384d568") against `base_branch` in [02 §2.5](design/02-repos-and-config.md#2.5%20Config "git:797fb384d568"), the explain-context survey attributed to auto-integrate in [02 §2.3](design/02-repos-and-config.md#2.3%20Your%20omc%20repo "git:797fb384d568") but to auto-index in [03 §3.4](design/03-watch.md#3.4%20Setup:%20%60/auto-index%60,%20trust,%20%60/auto-integrate%60 "git:797fb384d568"), two worktree-creation signatures and two repo-add commands between [04 §4.3](design/04-mcp-and-cli.md#4.3%20Tools "git:797fb384d568"), [04 §4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree "git:797fb384d568") and [07 §7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60 "git:797fb384d568"), and a flags sentence in 07 §7.1 that omits publish.
**Decision.** Apply the corrections: the hash example in [02 §2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60) "git:797fb384d568") becomes `7d6cc14f` and states UTF-8 encoding; the still-to-verify bullet about Skill-tool preprocessing is dropped from [05 §5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs "git:797fb384d568"); [10 §10.2](design/10-review-lifecycle.md#10.2%20%60rebase%60 "git:797fb384d568") names the key `base_branch`; the explain-context survey is attributed to auto-index in [02 §2.3](design/02-repos-and-config.md#2.3%20Your%20omc%20repo "git:797fb384d568"); one worktree-creation signature is used in [04 §4.3](design/04-mcp-and-cli.md#4.3%20Tools "git:797fb384d568"), [04 §4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree "git:797fb384d568") and [07 §7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60 "git:797fb384d568"); `omc repo add` is defined as add-repo plus its poll; and the flags sentence of 07 §7.1 includes publish. The item about the v1 reference write-up is set aside as not relevant now.
**Affected.** [2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60) "git:797fb384d568"), [5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs "git:797fb384d568"), [10.2](design/10-review-lifecycle.md#10.2%20%60rebase%60 "git:797fb384d568"), [2.3](design/02-repos-and-config.md#2.3%20Your%20omc%20repo "git:797fb384d568"), [4.3](design/04-mcp-and-cli.md#4.3%20Tools "git:797fb384d568"), [4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree "git:797fb384d568"), [7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60 "git:797fb384d568")
**Source.** [R93. [low] Small corrections in the text](reviews/2026-10-16-adversarial-design-review.md#R93.%20[low]%20Small%20corrections%20in%20the%20text "git:797fb384d568")
**Status.** recorded 2026-10-27
Answers: R93

### 1.17 User-only gates beyond trust: reset-rounds, configure writes, and a per-start secret for watch

**Context.** Ruling [1.2](#1.2%20Trust:%20index-only%20by%20default,%20trusted%20repos%20and%20mirrors,%20user-only%20trust%20commands) made the trust commands user-only and deferred the other gates. `omc internal reset-rounds` lifts the fix loop CRITICAL stop and is "called only after your reply" in [08 §8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60 "git:797fb384d568"), yet under CLI = MCP in [01 §1.2](design/01-principles.md#1.2%20Cross-cutting%20rules "git:797fb384d568") it is an agent-callable tool and the stubs of [05 §5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs "git:797fb384d568") pre-approve every `omc` subcommand from Bash; `configure` stays local per [04 §4.2](design/04-mcp-and-cli.md#4.2%20The%20CLI%20is%20an%20MCP%20client "git:797fb384d568") but the agent can run it; and the endpoint of [04 §4.1](design/04-mcp-and-cli.md#4.1%20The%20server "git:797fb384d568") accepts calls from any local process with no authentication, an exception stated in [01 §1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design "git:797fb384d568"). What enforces these gates?
**Decision.** `omc internal reset-rounds` and `omc configure` writes are user-only like the trust commands of [02 §2.6](design/02-repos-and-config.md#2.6%20Trust "git:797fb384d568"): CLI only, never MCP tools, refused without an interactive terminal, and never covered by a stub's `allowed-tools`, which lists exact `omc` subcommands instead of `omc …` ([05 §5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs "git:797fb384d568"), [04 §4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree "git:797fb384d568")). Watch generates a per-start secret in a 0600 file that the CLI and the agent's MCP client must present, so other local processes cannot drive it; the no-authentication exception of [01 §1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design "git:797fb384d568") and [04 §4.1](design/04-mcp-and-cli.md#4.1%20The%20server "git:797fb384d568") is replaced by that secret.
**Affected.** [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules "git:797fb384d568"), [1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design "git:797fb384d568"), [4.1](design/04-mcp-and-cli.md#4.1%20The%20server "git:797fb384d568"), [4.2](design/04-mcp-and-cli.md#4.2%20The%20CLI%20is%20an%20MCP%20client "git:797fb384d568"), [4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree "git:797fb384d568"), [5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs "git:797fb384d568"), [8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60 "git:797fb384d568"), [2.6](design/02-repos-and-config.md#2.6%20Trust "git:797fb384d568")
**Supersedes.** [1.2](#1.2%20Trust:%20index-only%20by%20default,%20trusted%20repos%20and%20mirrors,%20user-only%20trust%20commands)
**Source.** [R98. [blocker] The other user-only gates: reset-rounds, configure, and unauthenticated MCP](reviews/2026-10-16-adversarial-design-review.md#R98.%20[blocker]%20The%20other%20user-only%20gates:%20reset-rounds,%20configure,%20and%20unauthenticated%20MCP "git:797fb384d568")
**Status.** recorded 2026-10-27
Answers: R98, R2

### 1.18 Sessions and headless LLM calls omc launches: one contract, and trust gates the lifecycle launchers

**Context.** omc runs LLM calls outside a user session: the context and ops surveys of [03 §3.4](design/03-watch.md#3.4%20Setup:%20%60/auto-index%60,%20trust,%20%60/auto-integrate%60 "git:797fb384d568") before trust, the freshness check of [03 §3.7](design/03-watch.md#3.7%20Freshness%20checks "git:797fb384d568"), the conflict resolver of [03 §3.3](design/03-watch.md#3.3%20Sync%20every%20tick "git:797fb384d568"), `create-slug` and `find-repo` of [07 §7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60 "git:797fb384d568"), and `/auto-integrate`. No document states their cwd, whether the target repo's harness settings, hooks and MCP servers load, their tools or output schema, and the survey's output is inlined as the `design:explain-context` contribution per [05 §5.5](design/05-skill-rendering.md#5.5%20Hook%20contributions "git:797fb384d568"). Trust in [02 §2.6](design/02-repos-and-config.md#2.6%20Trust "git:797fb384d568") covers only what watch executes, while [08 §8.1](design/08-implement-lifecycle.md#8.1%20Shape "git:797fb384d568"), [10 §10.1](design/10-review-lifecycle.md#10.1%20Shape "git:797fb384d568") and [11 §11.1](design/11-publish-lifecycle.md#11.1%20Shape "git:797fb384d568") launch sessions in a worktree with no trust check, and the harness raises its own folder-trust prompt on every new worktree.
**Decision.** Every headless LLM call omc makes runs under one contract: an omc-owned working directory, the target repo's harness project settings, hooks and MCP servers disabled, a per-job tool allowlist that is read-only before trust, a named model slot, and strict JSON output; the pre-trust survey's result is stored as a linked data file, never inlined as the `design:explain-context` contribution of [05 §5.5](design/05-skill-rendering.md#5.5%20Hook%20contributions "git:797fb384d568"). The lifecycle launchers `omc implement`, `omc review` and `omc publish` and their `/omc:` entries refuse an untrusted repo, and trusting a repo per [02 §2.6](design/02-repos-and-config.md#2.6%20Trust "git:797fb384d568") also marks its worktree location trusted in the harness configuration, so that trust includes running agent-edited code in sessions and watch jobs.
**Affected.** [3.4](design/03-watch.md#3.4%20Setup:%20%60/auto-index%60,%20trust,%20%60/auto-integrate%60 "git:797fb384d568"), [3.7](design/03-watch.md#3.7%20Freshness%20checks "git:797fb384d568"), [3.3](design/03-watch.md#3.3%20Sync%20every%20tick "git:797fb384d568"), [7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60 "git:797fb384d568"), [5.5](design/05-skill-rendering.md#5.5%20Hook%20contributions "git:797fb384d568"), [2.6](design/02-repos-and-config.md#2.6%20Trust "git:797fb384d568"), [8.1](design/08-implement-lifecycle.md#8.1%20Shape "git:797fb384d568"), [10.1](design/10-review-lifecycle.md#10.1%20Shape "git:797fb384d568"), [11.1](design/11-publish-lifecycle.md#11.1%20Shape "git:797fb384d568"), [1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design "git:797fb384d568")
**Source.** [R26. [high] Headless LLM sessions run with no permission model, and their output becomes instructions](reviews/2026-10-16-adversarial-design-review.md#R26.%20[high]%20Headless%20LLM%20sessions%20run%20with%20no%20permission%20model,%20and%20their%20output%20becomes%20instructions "git:797fb384d568")
**Status.** recorded 2026-10-27
Answers: R26, R27

### 1.19 Worktrees are cut by Python with git, base and path pinned; worktrunk is dropped

**Context.** [02 §2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60) "git:797fb384d568") creates worktrees through worktrunk with `--yes`, which passes no base and no path and auto-approves the product repo's own hooks, while [07 §7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60 "git:797fb384d568") step 7 and [04 §4.3](design/04-mcp-and-cli.md#4.3%20Tools "git:797fb384d568") promise a branch from `origin/<base>` under `<worktree_location>/<repo-key>/<slug>`, and ruling [1.2](#1.2%20Trust:%20index-only%20by%20default,%20trusted%20repos%20and%20mirrors,%20user-only%20trust%20commands) forbids running a repo's code before trust. How are worktrees cut so that base, path and the no-hooks rule hold?
**Decision.** Python cuts every worktree itself with `git worktree add -b <branch> <path> origin/<base>` from the hidden clone, after the fetch and the on-`origin/<base>` check of [07 §7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60 "git:797fb384d568") step 7; the path is `<worktree_location>/<repo-key>/<slug>` by construction and no repo hook runs. Worktrunk is dropped from the design: [02 §2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60) "git:797fb384d568"), [14 §14.2](design/14-cross-repo-features.md#14.2%20Changing%20several%20repos%20in%20one%20feature%20(not%20MVP;%20a%20design%20guideline) "git:797fb384d568") and [01 §1.4](design/01-principles.md#1.4%20Approved%20dependencies "git:797fb384d568") no longer name it.
**Affected.** [2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60) "git:797fb384d568"), [7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60 "git:797fb384d568"), [4.3](design/04-mcp-and-cli.md#4.3%20Tools "git:797fb384d568"), [14.2](design/14-cross-repo-features.md#14.2%20Changing%20several%20repos%20in%20one%20feature%20(not%20MVP;%20a%20design%20guideline) "git:797fb384d568"), [1.4](design/01-principles.md#1.4%20Approved%20dependencies "git:797fb384d568")
**Supersedes.** [1.1](#1.1%20MVP%20scope%20of%20multi-repo%20work)
**Source.** [R25. [high] worktrunk `--yes` runs the repo's own hooks before trust, and doesn't pin the path or base](reviews/2026-10-16-adversarial-design-review.md#R25.%20[high]%20worktrunk%20%60--yes%60%20runs%20the%20repo's%20own%20hooks%20before%20trust,%20and%20doesn't%20pin%20the%20path%20or%20base "git:797fb384d568")
**Status.** recorded 2026-10-27
Answers: R25

### 1.20 TDD selector runs only report; a full pass resets the round counter

**Context.** TDD steps run `omc run check --test <selector>` expecting red ([07 §7.7](design/07-design-lifecycle.md#7.7%20%60write-implementation-plan%60)); under [09 §9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop) every red run starts the fix skill and counts against the round budget, and the only reset is the user-only one after a CRITICAL stop ([08 §8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60)), so a normal multi-task plan reaches CRITICAL.
**Decision.** `omc run check --test <selector>` only reports its result: it starts no fix skill, counts no round and records no pass. Only full runs take part in the fix loop of [09 §9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop). A full pass resets the round counter for that worktree and job type; the user-only reset after a CRITICAL stop ([08 §8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60)) is unchanged.
**Automated.** true
**Affected.** [9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop), [7.7](design/07-design-lifecycle.md#7.7%20%60write-implementation-plan%60), [8.3](design/08-implement-lifecycle.md#8.3%20%60superpowers-subagent-build%60)
**Source.** [R8. [blocker] TDD's expected red runs enter the fix loop and use up rounds, and nothing says when the counter resets](reviews/2026-10-16-adversarial-design-review.md#R8.%20[blocker]%20TDD's%20expected%20red%20runs%20enter%20the%20fix%20loop%20and%20use%20up%20rounds,%20and%20nothing%20says%20when%20the%20counter%20resets)
**Status.** recorded 2026-10-29
Answers: R8

### 1.21 Rendered skills and JSON verdicts are never truncated

**Context.** Every tool result is cut at the output cap of [04 §4.5](design/04-mcp-and-cli.md#4.5%20Output%20cap%20for%20all%20tool%20output); a rendered skill can exceed it and lose its `--done` line, and a cut poll result is invalid JSON, against the fail-loud rule of [01 §1.2](design/01-principles.md#1.2%20Cross-cutting%20rules).
**Decision.** The truncating cap of [04 §4.5](design/04-mcp-and-cli.md#4.5%20Output%20cap%20for%20all%20tool%20output) applies to data results only. Rendered skills and JSON verdicts are never cut: a render over a total budget, set below the smallest harness output limit, becomes an ABORT listing its largest contributors, and JSON tools cap their own lists (the first N items, a total and a spillover file).
**Automated.** true
**Affected.** [4.5](design/04-mcp-and-cli.md#4.5%20Output%20cap%20for%20all%20tool%20output), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules), [5.6](design/05-skill-rendering.md#5.6%20Failures%20are%20fatal)
**Source.** [R9. [blocker] The output cap and harness limits truncate rendered skills and JSON results](reviews/2026-10-16-adversarial-design-review.md#R9.%20[blocker]%20The%20output%20cap%20and%20harness%20limits%20truncate%20rendered%20skills%20and%20JSON%20results)
**Status.** recorded 2026-10-29
Answers: R9

### 1.22 Every design plugin writes one artifact folder; work files live beside it

**Context.** [06 §6.2](design/06-lifecycles.md#6.2%20Plugins) has each plugin write a file while [07 §7.6](design/07-design-lifecycle.md#7.6%20%60design-hardening%60) writes a folder and [07 §7.7](design/07-design-lifecycle.md#7.7%20%60write-implementation-plan%60) leaves the plan's location open, so `--done`, `--from`, the hash check of [06 §6.5](design/06-lifecycles.md#6.5%20Read-only%20findings%20hooks) and the final copy do not know what to act on.
**Decision.** Every design plugin writes `design/<plugin>/<slug>/`, holding `<slug>.md`, its sub-documents and, from write-implementation-plan on, `<slug>-plan.md`. Python copies the previous plugin's folder in when a plugin starts. Work files (findings, `design-explained.md`) go to `design/<plugin>/work/`, outside the hashed folder. The last plugin's folder is the artifact that is checked and committed.
**Automated.** true
**Affected.** [6.2](design/06-lifecycles.md#6.2%20Plugins), [6.3](design/06-lifecycles.md#6.3%20Commands%20and%20the%20handoff%20between%20plugins), [6.5](design/06-lifecycles.md#6.5%20Read-only%20findings%20hooks), [7.6](design/07-design-lifecycle.md#7.6%20%60design-hardening%60), [7.7](design/07-design-lifecycle.md#7.7%20%60write-implementation-plan%60), [7.8](design/07-design-lifecycle.md#7.8%20%60approve-design%60)
**Source.** [R7. [blocker] The on-disk shape of a plugin's output: file or folder, where the plan goes, which folder gets committed](reviews/2026-10-16-adversarial-design-review.md#R7.%20[blocker]%20The%20on-disk%20shape%20of%20a%20plugin's%20output:%20file%20or%20folder,%20where%20the%20plan%20goes,%20which%20folder%20gets%20committed)
**Status.** recorded 2026-10-29
Answers: R7

### 1.23 Upstream Superpowers: a supported version range, overrides first, drift fails --done

**Context.** omc checks only that Superpowers is installed ([07 §7.4](design/07-design-lifecycle.md#7.4%20%60superpowers-brainstorm%60)) while `--done` in [08 §8.3](design/08-implement-lifecycle.md#8.3%20%60superpowers-subagent-build%60) parses SDD's ledger lines and final review, so an upstream upgrade can silently break `--done` or contradict omc's overrides.
**Decision.** The Superpowers prerequisite fact checks a supported version range and renders only an ABORT outside it. omc's overrides take precedence over the upstream text; they and the grammar `--done` parses are written against that range. Any drift in machine-read output (plan structure, ledger lines, final review) fails `--done` loudly. Whether the installed skill text is inlined at render time is not decided.
**Automated.** true
**Affected.** [7.4](design/07-design-lifecycle.md#7.4%20%60superpowers-brainstorm%60), [7.7](design/07-design-lifecycle.md#7.7%20%60write-implementation-plan%60), [8.3](design/08-implement-lifecycle.md#8.3%20%60superpowers-subagent-build%60), [5.6](design/05-skill-rendering.md#5.6%20Failures%20are%20fatal)
**Source.** [R36. [high] Upstream superpowers: no version pin, the wrap protocol, and its exits that build code](reviews/2026-10-16-adversarial-design-review.md#R36.%20[high]%20Upstream%20superpowers:%20no%20version%20pin,%20the%20wrap%20protocol,%20and%20its%20exits%20that%20build%20code)
**Status.** recorded 2026-10-29
Answers: R36

### 1.24 E2E suites: results through JUnit and logs, shutdown through a CLI command, watch kills at a per-repo limit

**Context.** A kept-alive E2E environment never exits, so watch gets no verdict, and killing the process tree ([09 §9.3](design/09-run-jobs.md#9.3%20Time%20limit%20and%20teardown)) misses containers and detached services; [09 §9.7](design/09-run-jobs.md#9.7%20E2E%20keep-alive%20and%20%60/investigate%20local%60) leaves the contract to the repo. The owner rejected a teardown-executable contract as overcomplicated.
**Decision.** The E2E suite boots as a watch job. It reports its results through a JUnit dump and logs that omc's E2E CLI command polls; each repo implements that command as needed to fit omc's polling. The suite is shut down through an abstract CLI command that the repo implements. If it does not shut down, watch kills it after the time limit: one hour by default, configurable per repo.
**Automated.** false
**Affected.** [9.3](design/09-run-jobs.md#9.3%20Time%20limit%20and%20teardown), [9.7](design/09-run-jobs.md#9.7%20E2E%20keep-alive%20and%20%60/investigate%20local%60), [9.2](design/09-run-jobs.md#9.2%20Commands), [3.4](design/03-watch.md#3.4%20Setup:%20%60/auto-index%60,%20trust,%20%60/auto-integrate%60), [8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60)
**Source.** [R11. [blocker] No contract for keep-alive E2E: how the verdict is reported and how watch tears the environment down](reviews/2026-10-16-adversarial-design-review.md#R11.%20[blocker]%20No%20contract%20for%20keep-alive%20E2E:%20how%20the%20verdict%20is%20reported%20and%20how%20watch%20tears%20the%20environment%20down)
**Status.** recorded 2026-10-29
Answers: R11

### 1.25 A pass certifies a clean committed tree, keyed without the artifact folder and with the job definition

**Context.** [09 §9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop) records the tree hash of every full pass, but fix rounds leave uncommitted changes, artifact-only commits change the tree after the gate ([08 §8.5](design/08-implement-lifecycle.md#8.5%20%60commit%60)), and the job definition is not part of the key, so carry-over in [10 §10.5](design/10-review-lifecycle.md#10.5%20%60ci-gate%60) and the identical-tree check of [11 §11.5](design/11-publish-lifecycle.md#11.5%20Assumed%20(not%20yet%20confirmed)) are undefined.
**Decision.** watch records a full pass only on a clean, committed worktree: no tracked changes and no untracked files outside `.gitignore`. The key is HEAD's tree plus a hash of the job definition; with `design_artifact_root: repository` it excludes the feature's artifact folder `<design_artifact_directory>/<slug>/`. Squash and push refuse a dirty tree.
**Automated.** true
**Affected.** [9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop), [10.5](design/10-review-lifecycle.md#10.5%20%60ci-gate%60), [8.5](design/08-implement-lifecycle.md#8.5%20%60commit%60), [11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60), [11.5](design/11-publish-lifecycle.md#11.5%20Assumed%20(not%20yet%20confirmed))
**Source.** [R40. [high] Which tree a pass certifies, and repository-mode artifact commits](reviews/2026-10-16-adversarial-design-review.md#R40.%20[high]%20Which%20tree%20a%20pass%20certifies,%20and%20repository-mode%20artifact%20commits)
**Status.** recorded 2026-10-29
Answers: R40

### 1.26 Committed entries carry summaries and ids only; one credential check refuses on every omc commit

**Context.** Suggestion-box and flaky-pass entries embed log excerpts and full outputs ([09 §9.6](design/09-run-jobs.md#9.6%20The%20suggestion%20box), [09 §9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop)), and logs routinely hold tokens and personal data; only LLM goodwill keeps them out of the omc repo despite [01 §1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design).
**Decision.** Committed suggestion-box and flaky-pass entries hold a summary, the test id and the job id; full logs and outputs stay in the cache. Every write watch commits into the omc repo, and `check-artifact` ([06 §6.6](design/06-lifecycles.md#6.6%20The%20final%20artifact)), passes one Python credential-pattern check that refuses on a match and fails loud, naming the file and line; nothing is redacted and committed anyway.
**Automated.** true
**Affected.** [1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design), [9.6](design/09-run-jobs.md#9.6%20The%20suggestion%20box), [9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop), [6.6](design/06-lifecycles.md#6.6%20The%20final%20artifact), [2.3](design/02-repos-and-config.md#2.3%20Your%20omc%20repo)
**Source.** [R31. [high] Credentials and PII committed into the omc repo](reviews/2026-10-16-adversarial-design-review.md#R31.%20[high]%20Credentials%20and%20PII%20committed%20into%20the%20omc%20repo)
**Status.** recorded 2026-10-29
Answers: R31

### 1.27 Session memory follows the per-branch retention rule and is state, not cache

**Context.** Memory is cleared after a month unmodified ([12 §12.2](design/12-session-memory.md#12.2%20Shape), [03 §3.8](design/03-watch.md#3.8%20%60/tmp%60%20retention)), which deletes a stacked branch's live base intent, and closing a worktree does not clear it, so a reused branch name inherits stale memory.
**Decision.** A branch's session memory follows the per-branch rule of [02 §2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60)): it is deleted when the worktree is closed through omc, or by watch's sweep once the branch exists neither locally nor on origin and the file has been untouched for `features.retention_days`. It is one file, `optmem`, classed as state, not rebuildable cache.
**Automated.** true
**Affected.** [12.2](design/12-session-memory.md#12.2%20Shape), [12.3](design/12-session-memory.md#12.3%20Assumed%20(not%20yet%20confirmed)), [3.8](design/03-watch.md#3.8%20%60/tmp%60%20retention), [2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60)), [2.2](design/02-repos-and-config.md#2.2%20Three%20places%20things%20live)
**Source.** [R43. [high] Session memory retention deletes live intent, and stale memory leaks to reused branch names](reviews/2026-10-16-adversarial-design-review.md#R43.%20[high]%20Session%20memory%20retention%20deletes%20live%20intent,%20and%20stale%20memory%20leaks%20to%20reused%20branch%20names)
**Status.** recorded 2026-10-29
Answers: R43

### 1.28 User-owned YAML is edited round-trip with ruamel.yaml

**Context.** pyyaml cannot round-trip a file, so any write drops comments and reformats a file the user owns, against "never rewrites a whole file" in [02 §2.3](design/02-repos-and-config.md#2.3%20Your%20omc%20repo).
**Decision.** omc's writes into user-owned YAML use `ruamel.yaml` in round-trip mode, so comments and formatting survive; `ruamel.yaml` is added to [01 §1.4](design/01-principles.md#1.4%20Approved%20dependencies) after vetting. A key that cannot be written because its file has uncommitted edits fails loud: "commit or stash <file>, then rerun `omc update`".
**Automated.** true
**Affected.** [2.3](design/02-repos-and-config.md#2.3%20Your%20omc%20repo), [2.5](design/02-repos-and-config.md#2.5%20Config), [1.4](design/01-principles.md#1.4%20Approved%20dependencies)
**Source.** [R62. [high] YAML writes without rewriting user files (pyyaml)](reviews/2026-10-16-adversarial-design-review.md#R62.%20[high]%20YAML%20writes%20without%20rewriting%20user%20files%20(pyyaml))
**Status.** recorded 2026-10-29
Answers: R62

### 1.29 A gate run counts only when a full series changed nothing; otherwise commit and rerun the whole series

**Context.** When an E2E or ci fix changes code mid-gate, only that job reruns, so no single tree has passed the whole gate ([10 §10.5](design/10-review-lifecycle.md#10.5%20%60ci-gate%60), [08 §8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60)). The owner rejected restarting the gate after every change as too slow; earlier stages rarely fail.
**Decision.** A gate runs its whole series of jobs, each with its fix loop. Only after the series has passed does it check whether anything changed since the gate started: a different commit hash, or staged, unstaged or uncommitted changes in the tree. If so, it commits and runs the whole series again. The gate passes only on a clean series that changed nothing. It does not restart after each individual change.
**Automated.** false
**Affected.** [10.5](design/10-review-lifecycle.md#10.5%20%60ci-gate%60), [8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60), [9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop), [11.5](design/11-publish-lifecycle.md#11.5%20Assumed%20(not%20yet%20confirmed))
**Source.** [R41. [high] A fix in a later gate job leaves the earlier passes stale](reviews/2026-10-16-adversarial-design-review.md#R41.%20[high]%20A%20fix%20in%20a%20later%20gate%20job%20leaves%20the%20earlier%20passes%20stale)
**Status.** recorded 2026-10-29
Answers: R41

### 1.30 check-artifact checks link targets before approval; the final --done commits, then deletes temp

**Context.** check-artifact rejects any `/tmp/`, `~/.omc2` or absolute path anywhere in the text ([06 §6.6](design/06-lifecycles.md#6.6%20The%20final%20artifact)), which blocks legitimate designs, and it runs only after the approval ([07 §7.8](design/07-design-lifecycle.md#7.8%20%60approve-design%60)); copy and commit has no defined order or failure path.
**Decision.** check-artifact checks link targets, not text: links that escape the folder, point to a missing file, use `file://` or point into private locations, plus the credential check of [1.26](#1.26%20Committed%20entries%20carry%20summaries%20and%20ids%20only;%20one%20credential%20check%20refuses%20on%20every%20omc%20commit). It runs before the approval overview. The lifecycle's final `--done` runs the check, a path-limited copy and commit, and deletes the temp folder last; nothing is deleted on failure. `create-slug` refuses a slug whose artifact folder already exists.
**Automated.** true
**Affected.** [6.6](design/06-lifecycles.md#6.6%20The%20final%20artifact), [7.8](design/07-design-lifecycle.md#7.8%20%60approve-design%60), [7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60)
**Source.** [R57. [high] check-artifact rules, plus the copy-and-commit step's ownership and failure path](reviews/2026-10-16-adversarial-design-review.md#R57.%20[high]%20check-artifact%20rules,%20plus%20the%20copy-and-commit%20step's%20ownership%20and%20failure%20path)
**Status.** recorded 2026-10-29
Answers: R57

### 1.31 Review: code-review before deviation-analysis; waivers and deviations in a per-round record

**Context.** Code-review waivers go into `## Deliberate complexity` of the approved design ([10 §10.4](design/10-review-lifecycle.md#10.4%20%60code-review%60)), which is never rewritten, and code-review runs after deviation-analysis ([10 §10.3](design/10-review-lifecycle.md#10.3%20%60deviation-analysis%60)), so its behaviour-changing fixes never reach `<slug>-deviations.md`.
**Decision.** The review pipeline runs code-review before deviation-analysis. Code-review waivers go into a `## Deliberate complexity` section of `<slug>-deviations.md` (per feedback round `<slug>-deviations-feedback-<n>.md`), committed when review ends. An escalation the owner answered is recorded as accepted or reverted with the owner as its basis. Code findings name `Location: path:line`. The approved design is never rewritten.
**Automated.** true
**Affected.** [10.1](design/10-review-lifecycle.md#10.1%20Shape), [10.3](design/10-review-lifecycle.md#10.3%20%60deviation-analysis%60), [10.4](design/10-review-lifecycle.md#10.4%20%60code-review%60), [10.6](design/10-review-lifecycle.md#10.6%20Assumed%20(not%20yet%20confirmed))
**Source.** [R61. [high] Code-review waivers have no home and fixes after deviation analysis go unrecorded](reviews/2026-10-16-adversarial-design-review.md#R61.%20[high]%20Code-review%20waivers%20have%20no%20home%20and%20fixes%20after%20deviation%20analysis%20go%20unrecorded)
**Status.** recorded 2026-10-29
Answers: R61

### 1.32 Templates are parsed up front; uncertain renders ABORT; facts get an explicit context

**Context.** A missing `<error>` branch silently drops content ([05 §5.3](design/05-skill-rendering.md#5.3%20%60<match>%60%20blocks%20and%20facts)), facts get no repo, branch or worktree context, and variables have no registry or escape for a literal `{{` ([05 §5.4](design/05-skill-rendering.md#5.4%20Variables)).
**Decision.** Every template is parsed up front, including branches not taken; facts still run only in the branch taken. Variables come from a closed registry and `{{` can be escaped. An unknown variable, bad syntax, or a fact error with no `<error>` branch renders an ABORT; a missing `<true>` or `<false>` branch still inlines nothing. Facts get the repo, branch, worktree and provider in `OMC_*` environment variables, run with the worktree as cwd and argv split without a shell, and print JSON on stdout only. Mandatory fact scopes and `<abort>`/`<skip/>` directives are not decided.
**Automated.** true
**Affected.** [5.3](design/05-skill-rendering.md#5.3%20%60<match>%60%20blocks%20and%20facts), [5.4](design/05-skill-rendering.md#5.4%20Variables), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules)
**Source.** [R71. [medium] Rendering grammar: <match> errors, fact contract, variables, substitution](reviews/2026-10-16-adversarial-design-review.md#R71.%20[medium]%20Rendering%20grammar:%20<match>%20errors,%20fact%20contract,%20variables,%20substitution)
**Status.** recorded 2026-10-29
Answers: R71

### 1.33 E2E runs only inside omc watch; no plugin starts processes outside it

**Context.** [08 §8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60) keeps milestone-gate a separate plugin so a repo can change its E2E policy (e.g. a `just up` first), which reads as a plugin starting environments outside watch, while [10 §10.5](design/10-review-lifecycle.md#10.5%20%60ci-gate%60) calls `omc run e2e-tests` directly. The owner rejected that reading: running through watch is a core pillar, not a plugin.
**Decision.** Everything an E2E policy runs happens inside `omc watch` as a watch job; no plugin, milestone-gate or any other, starts or manages processes outside it. watch manages the lifetime of the job's process tree and communicates with the LLM by polling ([01 §1.2](design/01-principles.md#1.2%20Cross-cutting%20rules)). What `configured: false` means is not decided here.
**Automated.** false
**Affected.** [8.4](design/08-implement-lifecycle.md#8.4%20%60milestone-gate%60), [10.5](design/10-review-lifecycle.md#10.5%20%60ci-gate%60), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules), [9.1](design/09-run-jobs.md#9.1%20Everything%20that%20runs%20goes%20through%20watch)
**Source.** [R80. [medium] E2E policy: custom milestone gate vs hardcoded ci-gate, and what configured:false means](reviews/2026-10-16-adversarial-design-review.md#R80.%20[medium]%20E2E%20policy:%20custom%20milestone%20gate%20vs%20hardcoded%20ci-gate,%20and%20what%20configured:false%20means)
**Status.** recorded 2026-10-29
Answers: R80

### 1.34 explain-seed resolves the seed once into seed.md; each explain-context contribution writes its own document beside it

**Context.** In [07 §7.3](design/07-design-lifecycle.md#7.3%20%60explain-seed%60) the context gate runs before the `design:explain-context` hook, and the ticket and link fetch lives inside omc's default contribution, so a ticket-only seed fails the gate, disabling the omc layer drops ticket linking, and every caller (also [07 §7.6](design/07-design-lifecycle.md#7.6%20%60design-hardening%60)) re-resolves the same sources.
**Decision.** `explain-seed` keeps the `design:explain-context` hook ([06 §6.4](design/06-lifecycles.md#6.4%20Hooks)): it gathers context, it is not a findings pipeline like [06 §6.5](design/06-lifecycles.md#6.5%20Read-only%20findings%20hooks). It works like a variant of that machinery: the plugin builds the explain context in a temp directory, first writing the original seed with its initial resolution of the ticket, links and similar data as `seed.md`. Each contribution then writes its own context document `hook_<hook-name>.md` in that directory. Every contribution gets the link to `seed.md` and the directory and is free to explore it, so no contribution re-resolves the seed's sources from scratch.
**Automated.** false
**Affected.** [7.3](design/07-design-lifecycle.md#7.3%20%60explain-seed%60), [6.4](design/06-lifecycles.md#6.4%20Hooks), [7.6](design/07-design-lifecycle.md#7.6%20%60design-hardening%60), [5.5](design/05-skill-rendering.md#5.5%20Hook%20contributions)
**Source.** [R60. [high] explain-seed's context gate runs before the ticket is fetched, and ticket fetching sits in a context-only hook](reviews/2026-10-16-adversarial-design-review.md#R60.%20[high]%20explain-seed's%20context%20gate%20runs%20before%20the%20ticket%20is%20fetched,%20and%20ticket%20fetching%20sits%20in%20a%20context-only%20hook)
**Status.** recorded 2026-10-29
Answers: R60

### 1.35 Hooks are called on demand through run-hook; Python checks after each contribution

**Context.** Executable contributions run once when the plugin renders ([05 §5.5](design/05-skill-rendering.md#5.5%20Hook%20contributions)), before any section, round or input exists, and all contributions are inlined as one text, so Python never gets control between them for the per-hook checks of [06 §6.5](design/06-lifecycles.md#6.5%20Read-only%20findings%20hooks).
**Decision.** Hooks are called on demand: at each call site the plugin text runs `omc internal run-hook <lifecycle>:<hook> --input <file>`. Python runs the contributions one at a time, in layer order, gives each the input and a known output path, and hash-checks and validates after each one. How a markdown contribution, which the LLM carries out, hands control back is not decided.
**Automated.** true
**Affected.** [5.5](design/05-skill-rendering.md#5.5%20Hook%20contributions), [6.4](design/06-lifecycles.md#6.4%20Hooks), [6.5](design/06-lifecycles.md#6.5%20Read-only%20findings%20hooks)
**Source.** [R10. [blocker] Executable hooks run once at render time, so they can't serve per-section, per-round or per-hook checks](reviews/2026-10-16-adversarial-design-review.md#R10.%20[blocker]%20Executable%20hooks%20run%20once%20at%20render%20time,%20so%20they%20can't%20serve%20per-section,%20per-round%20or%20per-hook%20checks)
**Status.** recorded 2026-10-29
Answers: R10

### 1.36 Each branch has one recorded base; every base consumer reads only that

**Context.** Only `rebase` turns the memory text into a base ([10 §10.2](design/10-review-lifecycle.md#10.2%20%60rebase%60), [12 §12.1](design/12-session-memory.md#12.1%20Why)); squash, the review diff and the verification after a fallback read the base on their own, so a stacked branch can squash in its parent and a squash onto a fresh tip reverts upstream work.
**Decision.** Each branch has one base record: base branch, base commit and parent tip. Only `rebase` and `omc internal set-base` change it; the LLM runs `set-base` when the owner states a target, and it rebases at once. Every step that needs the base (squash, the diff review reads, the commit-over-base check, the fallback verification) reads only this record. Squash goes onto the recorded base commit, never a freshly fetched tip. Session memory still carries the intent.
**Automated.** true
**Affected.** [10.2](design/10-review-lifecycle.md#10.2%20%60rebase%60), [11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60), [11.5](design/11-publish-lifecycle.md#11.5%20Assumed%20(not%20yet%20confirmed)), [12.1](design/12-session-memory.md#12.1%20Why)
**Source.** [R18. [blocker] A branch's base exists only as free-text memory, yet squash, diff and verify need a fixed value](reviews/2026-10-16-adversarial-design-review.md#R18.%20[blocker]%20A%20branch's%20base%20exists%20only%20as%20free-text%20memory,%20yet%20squash,%20diff%20and%20verify%20need%20a%20fixed%20value)
**Status.** recorded 2026-10-29
Answers: R18

### 1.37 One authoritative command table; watch commands are MCP tools; worktree paths are checked

**Context.** Only six MCP tools exist ([04 §4.3](design/04-mcp-and-cli.md#4.3%20Tools)), several commands are missing from [04 §4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree), nothing says which commands are local, and worktree-scoped tools would accept any path an LLM supplies.
**Decision.** One exhaustive table in [04 §4.3](design/04-mcp-and-cli.md#4.3%20Tools) and [04 §4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree) lists every command with its MCP tool or none, whether it runs locally or through watch, and whether it is user-only. Every command that goes through watch is an MCP tool; local and user-only commands ([1.17](#1.17%20User-only%20gates%20beyond%20trust:%20reset-rounds,%20configure%20writes,%20and%20a%20per-start%20secret%20for%20watch)) are CLI only, narrowing "vice versa" in [01 §1.2](design/01-principles.md#1.2%20Cross-cutting%20rules). Rendering, facts, `omc memory` and `temp-dir` run locally without watch. Worktree tools take an absolute path that watch resolves and accepts only for worktrees it created. `omc repo <repo> status|wait` becomes `ensure-repo --until`.
**Automated.** true
**Affected.** [4.3](design/04-mcp-and-cli.md#4.3%20Tools), [4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree), [4.2](design/04-mcp-and-cli.md#4.2%20The%20CLI%20is%20an%20MCP%20client), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules)
**Source.** [R35. [high] The CLI/MCP command and tool inventory is incomplete, and worktree identity isn't validated](reviews/2026-10-16-adversarial-design-review.md#R35.%20[high]%20The%20CLI/MCP%20command%20and%20tool%20inventory%20is%20incomplete,%20and%20worktree%20identity%20isn't%20validated)
**Status.** recorded 2026-10-29
Answers: R35

### 1.38 Setup that does not complete fails the repo add; the agent retries the add

**Context.** [03 §3.4](design/03-watch.md#3.4%20Setup:%20%60/auto-index%60,%20trust,%20%60/auto-integrate%60) retries a failed setup only when an input changes, so a setup interrupted by a watch restart ([03 §3.6](design/03-watch.md#3.6%20Scheduling)) or a transient error leaves a repo stuck, and omc's own commits to the repo folder count as input changes.
**Decision.** Setup that does not complete makes the repo-add job fail, and the LLM retries by adding the repo again (`repo_add`, [04 §4.3](design/04-mcp-and-cli.md#4.3%20Tools)). Whether watch also retries on its own when an input changes is not decided.
**Automated.** false
**Affected.** [3.4](design/03-watch.md#3.4%20Setup:%20%60/auto-index%60,%20trust,%20%60/auto-integrate%60), [3.6](design/03-watch.md#3.6%20Scheduling), [4.3](design/04-mcp-and-cli.md#4.3%20Tools)
**Source.** [R16. [blocker] Retrying failed setup: watch restarts strand repos, and omc's own commits retrigger setup](reviews/2026-10-16-adversarial-design-review.md#R16.%20[blocker]%20Retrying%20failed%20setup:%20watch%20restarts%20strand%20repos,%20and%20omc's%20own%20commits%20retrigger%20setup)
**Status.** recorded 2026-10-29
Answers: R16

### 1.39 First run goes through omc configure; a new machine revalidates integrations

**Context.** With no local config watch does not know the omc repo and takes no arguments, nothing creates a new omc repo, and [02 §2.2](design/02-repos-and-config.md#2.2%20Three%20places%20things%20live) promises "clone and run watch" without saying whether another machine's integrations are re-run, revalidated or left stuck.
**Decision.** Without local config every command except `configure`, `version` and `uninstall` refuses with "run `omc configure`". The first `configure` clones the owner's omc repo or creates one with defaults. With no upstream, sync is off and watch logs it once. Integrations committed on another machine are revalidated in a scratch worktree once the repo is trusted there, never regenerated; per-machine gaps such as a missing system tool live in the cache. `omc update` installs and refreshes the provider stubs and the fenced instruction section; `uninstall` reverses exactly what omc registered. [02 §2.2](design/02-repos-and-config.md#2.2%20Three%20places%20things%20live) reads "run configure, then watch".
**Automated.** true
**Affected.** [2.2](design/02-repos-and-config.md#2.2%20Three%20places%20things%20live), [2.5](design/02-repos-and-config.md#2.5%20Config), [4.2](design/04-mcp-and-cli.md#4.2%20The%20CLI%20is%20an%20MCP%20client), [3.3](design/03-watch.md#3.3%20Sync%20every%20tick)
**Source.** [R48. [high] Bootstrapping a new machine and a new omc repo](reviews/2026-10-16-adversarial-design-review.md#R48.%20[high]%20Bootstrapping%20a%20new%20machine%20and%20a%20new%20omc%20repo)
**Status.** recorded 2026-10-29
Answers: R48

### 1.40 Repo identity is case-sensitive; repo folders are managed by watch

**Context.** [02 §2.1](design/02-repos-and-config.md#2.1%20Repo%20identity) keeps the path's case, so differently cased URLs give different keys, and the review assumed hand-edited folders or URLs could make a folder name and its URL's key disagree.
**Decision.** Repo identity is case-sensitive: the canonical form of [02 §2.1](design/02-repos-and-config.md#2.1%20Repo%20identity) keeps the path's case as given. Repo folders under `repos/` are created and managed by watch, not edited by hand, so a folder always matches its URL's key. Alias resolution and the form of `trusted_repos` entries are not decided.
**Automated.** false
**Affected.** [2.1](design/02-repos-and-config.md#2.1%20Repo%20identity), [2.3](design/02-repos-and-config.md#2.3%20Your%20omc%20repo)
**Source.** [R47. [high] Repo identity: case, aliases, URL changes, folder/URL mismatch, trust identity](reviews/2026-10-16-adversarial-design-review.md#R47.%20[high]%20Repo%20identity:%20case,%20aliases,%20URL%20changes,%20folder/URL%20mismatch,%20trust%20identity)
**Status.** recorded 2026-10-29
Answers: R47

### 1.41 On shutdown and after a crash, watch kills everything it started

**Context.** On start watch only relabels running jobs as failed ([03 §3.6](design/03-watch.md#3.6%20Scheduling)); builds, sessions and E2E environments survive a crash or a closed tab and run beside the next jobs.
**Decision.** When watch shuts down, and when it starts after an unclean exit, every process it started is killed: every job's process tree, E2E environments included. Nothing leaks. Whether a restart counts as a round is not decided.
**Automated.** false
**Affected.** [3.6](design/03-watch.md#3.6%20Scheduling), [9.3](design/09-run-jobs.md#9.3%20Time%20limit%20and%20teardown), [9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop)
**Source.** [R38. [high] Watch exit and crash: orphaned jobs, interrupted operations, round penalties](reviews/2026-10-16-adversarial-design-review.md#R38.%20[high]%20Watch%20exit%20and%20crash:%20orphaned%20jobs,%20interrupted%20operations,%20round%20penalties)
**Status.** recorded 2026-10-29
Answers: R38

### 1.42 Python checks each lifecycle entry; implement, review and publish start only on the owner's word

**Context.** Nothing stops publish before review or after a CRITICAL in ci-gate ([11 §11.1](design/11-publish-lifecycle.md#11.1%20Shape)), review can start after a red gate ([10 §10.1](design/10-review-lifecycle.md#10.1%20Shape)), and implement can start before trust or integration ([08 §8.1](design/08-implement-lifecycle.md#8.1%20Shape)); approval rests on the model's good behaviour.
**Decision.** Python checks each lifecycle's entry before its first plugin; a failure renders an ABORT. Implement needs the committed artifact, a trusted repo ([1.18](#1.18%20Sessions%20and%20headless%20LLM%20calls%20omc%20launches:%20one%20contract,%20and%20trust%20gates%20the%20lifecycle%20launchers)) and an integrated repo. Review needs a clean tree and `check` and `e2e-tests` passes recorded for HEAD's tree. Publish needs a clean tree and passes of every ci-gate job for HEAD's tree. The implement, review and publish entries are user-only, and every closing statement tells the model to wait for the owner. A refused run is its own status and never a round.
**Automated.** true
**Affected.** [8.1](design/08-implement-lifecycle.md#8.1%20Shape), [10.1](design/10-review-lifecycle.md#10.1%20Shape), [11.1](design/11-publish-lifecycle.md#11.1%20Shape), [5.7](design/05-skill-rendering.md#5.7%20User-only%20commands)
**Source.** [R45. [high] Lifecycle entry preconditions and who may start each lifecycle](reviews/2026-10-16-adversarial-design-review.md#R45.%20[high]%20Lifecycle%20entry%20preconditions%20and%20who%20may%20start%20each%20lifecycle)
**Status.** recorded 2026-10-30
Answers: R45

### 1.43 Inputs are validated and reach processes only as argv, never as options or through a shell

**Context.** User text enters a double-quoted shell line, refs and selectors can pass as flags, docs paths can escape, cypher can read files and an SSH URL can carry `-oProxyCommand`; [01 §1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design) has no general rule.
**Decision.** One rule in [01 §1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design), with a table test per input class: free text arrives only through stdin or a file; refs are checked with `git check-ref-format` and passed after `--end-of-options`; selectors starting with `-` are refused and snippets use argv with no shell; docs paths are canonicalised and confined, symlinks not followed; each gitnexus verb has a typed schema and cypher is limited to a read-only allowlist; rg runs with `-e`, `--no-config` and no `RIPGREP_*` environment; SSH URLs follow a strict grammar, git is called with `--` and only the ssh protocol is allowed.
**Automated.** true
**Affected.** [1.3](design/01-principles.md#1.3%20Security%20rules%20carried%20into%20the%20design), [4.4](design/04-mcp-and-cli.md#4.4%20%60docs_grep%60), [4.3](design/04-mcp-and-cli.md#4.3%20Tools), [12.2](design/12-session-memory.md#12.2%20Shape), [9.5](design/09-run-jobs.md#9.5%20Test%20snippets%20generated%20by%20%60/auto-integrate%60)
**Source.** [R30. [high] Validating inputs: shell lines, git refs, selectors, docs paths, gitnexus args and cypher, the rg argv](reviews/2026-10-16-adversarial-design-review.md#R30.%20[high]%20Validating%20inputs:%20shell%20lines,%20git%20refs,%20selectors,%20docs%20paths,%20gitnexus%20args%20and%20cypher,%20the%20rg%20argv)
**Status.** recorded 2026-10-30
Answers: R30

### 1.44 Replaced, stopped and never-started jobs cost no round; identical runs attach

**Context.** Every `omc run` kills the worktree's current job ([09 §9.3](design/09-run-jobs.md#9.3%20Time%20limit%20and%20teardown)), so sessions cancel each other with undefined round accounting, and queue time counts toward the limit, so a job that never started is terminated and still burns a round.
**Decision.** A job killed by a newer run gets the status `replaced`; neither `replaced` nor `stopped` counts as a round. Only run time counts toward the time limit, and a job that never started costs no round. `omc run <type> --current` finds the worktree's current job. An identical run already in flight is attached to, not killed. Only the main session or the single implementer starts runs; review agents never do.
**Automated.** true
**Affected.** [9.3](design/09-run-jobs.md#9.3%20Time%20limit%20and%20teardown), [9.4](design/09-run-jobs.md#9.4%20The%20fix%20loop), [9.2](design/09-run-jobs.md#9.2%20Commands)
**Source.** [R39. [high] Round accounting for stopped, superseded, terminated and queued jobs](reviews/2026-10-16-adversarial-design-review.md#R39.%20[high]%20Round%20accounting%20for%20stopped,%20superseded,%20terminated%20and%20queued%20jobs)
**Status.** recorded 2026-10-30
Answers: R39

### 1.45 omc writes the narrowest harness settings it needs and checks them in every session

**Context.** Codex's default 60 s MCP timeout races `repo_add_poll` and its default sandbox blocks loopback calls and writes to omc's paths; the registration of [04 §4.1](design/04-mcp-and-cli.md#4.1%20The%20server) and the waits of [09 §9.2](design/09-run-jobs.md#9.2%20Commands) set nothing for this.
**Decision.** `omc update` writes the narrowest settings each harness needs: a Codex `tool_timeout_sec` above every MCP wait, a loopback or omc-command network exception, and the writable paths; the launchers pass those paths. MCP-side waits stay under 45 s. Every in-session render first checks that it can reach watch and write those paths, otherwise it renders an ABORT naming the setting to change. omc never asks for an unsandboxed session.
**Automated.** true
**Affected.** [4.1](design/04-mcp-and-cli.md#4.1%20The%20server), [9.2](design/09-run-jobs.md#9.2%20Commands), [4.3](design/04-mcp-and-cli.md#4.3%20Tools), [7.1](design/07-design-lifecycle.md#7.1%20%60omc%20design%20<repo-hint>%20"<seed>"%60)
**Source.** [R33. [high] Codex's MCP timeout (60 s) and sandbox vs omc's long polls and loopback CLI](reviews/2026-10-16-adversarial-design-review.md#R33.%20[high]%20Codex's%20MCP%20timeout%20(60%20s)%20and%20sandbox%20vs%20omc's%20long%20polls%20and%20loopback%20CLI)
**Status.** recorded 2026-10-30
Answers: R33

### 1.46 Hardening: re-explain changed sections, waivers cite decisions, later layers replace by name

**Context.** "Explain once" in [07 §7.6](design/07-design-lifecycle.md#7.6%20%60design-hardening%60) leaves new sections without context, it lets hardening waive on its own judgement while [06 §6.5](design/06-lifecycles.md#6.5%20Read-only%20findings%20hooks) asks first, zero contributions and same-named contributions are undefined, and plan findings can change the design without a record ([07 §7.7](design/07-design-lifecycle.md#7.7%20%60write-implementation-plan%60)).
**Decision.** Only new or changed sections are re-explained, using section hashes from `design-sections`. An automatic waiver must cite a recorded decision; every other waiver is asked. Each findings contribution runs in its own subagent, in order. A later layer's contribution with the same name replaces the earlier one. Zero contributions write `None.` and pass with a note. A contribution file that is neither `.md` nor executable fails loud. Plan findings that touch `<slug>.md` are forced to `Needs decision: yes`, and Python records each amendment with its hashes before and after.
**Automated.** true
**Affected.** [7.6](design/07-design-lifecycle.md#7.6%20%60design-hardening%60), [6.5](design/06-lifecycles.md#6.5%20Read-only%20findings%20hooks), [7.7](design/07-design-lifecycle.md#7.7%20%60write-implementation-plan%60), [6.4](design/06-lifecycles.md#6.4%20Hooks)
**Source.** [R70. [medium] Hardening details: stale explain output, waiver authority, zero contributions, overrides by name, independence of inline hooks](reviews/2026-10-16-adversarial-design-review.md#R70.%20[medium]%20Hardening%20details:%20stale%20explain%20output,%20waiver%20authority,%20zero%20contributions,%20overrides%20by%20name,%20independence%20of%20inline%20hooks)
**Status.** recorded 2026-10-30
Answers: R70

### 1.47 Publish: unknown forge state asks first; thread text is data; replies are reconciled; only an omc block is regenerated

**Context.** Without forge tools triage falls through to create-mr and force-pushes over open threads ([11 §11.2](design/11-publish-lifecycle.md#11.2%20%60triage-comments%60)); replies come from brainstorm decisions later rulings may have changed, raw comment text enters a session that can push, and regenerating the description overwrites human edits ([11 §11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60)).
**Decision.** Triage has three outcomes: no comments, comments, or unknown; unknown asks the owner before pushing. Raw thread text goes to a data file, never into the prompt. Replies are reconciled with the round's rulings and deviations, and threads that cannot be reconciled are shown to the owner. Description updates replace only an omc block between markers. Ticket moves are not decided here.
**Automated.** true
**Affected.** [11.2](design/11-publish-lifecycle.md#11.2%20%60triage-comments%60), [11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60), [11.5](design/11-publish-lifecycle.md#11.5%20Assumed%20(not%20yet%20confirmed))
**Source.** [R79. [medium] Publish: triage when forge state is unknown, replies built from stale decisions, isolating comment text](reviews/2026-10-16-adversarial-design-review.md#R79.%20[medium]%20Publish:%20triage%20when%20forge%20state%20is%20unknown,%20replies%20built%20from%20stale%20decisions,%20isolating%20comment%20text)
**Status.** recorded 2026-10-30
Answers: R79

### 1.48 docs_grep gains docs_read, defined scopes, stable order and bounds

**Context.** [04 §4.4](design/04-mcp-and-cli.md#4.4%20%60docs_grep%60) offers no way to read a hit, leaves global scope undefined for repos that are not ready, leaks paths when a doc path is missing, returns results in no fixed order and never searches past designs in omc mode.
**Decision.** `docs_read(display_path, range)` reads a hit. Scopes are `repo`, `global-docs` and `all`: `repo` still fails for a repo that is not ready, and the multi-repo scopes list skipped repos in a header line. A missing path gives one stale-config line, and no filesystem path appears in any output. Each call has one deadline plus `--max-count`; results are sorted by root and path. In omc mode `repos/<key>/docs/` counts as that repo's docs. The CLI is a top-level `omc docs-grep --scope`.
**Automated.** true
**Affected.** [4.4](design/04-mcp-and-cli.md#4.4%20%60docs_grep%60), [4.3](design/04-mcp-and-cli.md#4.3%20Tools), [4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree)
**Source.** [R81. [medium] docs_grep: reading documents, global scope, missing paths, ordering, design artifacts, CLI form](reviews/2026-10-16-adversarial-design-review.md#R81.%20[medium]%20docs_grep:%20reading%20documents,%20global%20scope,%20missing%20paths,%20ordering,%20design%20artifacts,%20CLI%20form)
**Status.** recorded 2026-10-30
Answers: R81

### 1.49 commit: tracked changes are committed, only untracked files are asked, rulings committed at the build's --done

**Context.** [08 §8.5](design/08-implement-lifecycle.md#8.5%20%60commit%60) both auto-commits fix-round files and asks about any file the plan did not produce, a file kept uncommitted blocks the clean-tree check forever, and rulings written at the build's `--done` are committed two plugins later.
**Decision.** `commit` commits modified tracked files and asks only about untracked files the plan did not produce: commit, leave (excluded without affecting other worktrees) or stop. Rulings are committed at the build's `--done` with paths normalised. Commits never use `--no-verify`; a hook failure goes back into the fix flow. The at-least-one-commit check counts only commits outside the artifact folder.
**Automated.** true
**Affected.** [8.5](design/08-implement-lifecycle.md#8.5%20%60commit%60), [8.3](design/08-implement-lifecycle.md#8.3%20%60superpowers-subagent-build%60)
**Source.** [R72. [medium] The commit plugin: classifying fix-round files, a clean-tree deadlock, staging and naming rulings](reviews/2026-10-16-adversarial-design-review.md#R72.%20[medium]%20The%20commit%20plugin:%20classifying%20fix-round%20files,%20a%20clean-tree%20deadlock,%20staging%20and%20naming%20rulings)
**Status.** recorded 2026-10-30
Answers: R72

### 1.50 Session memory: one locked file, a fixed line format, list and retract, rebase-aware branch

**Context.** Memory is append-only with no retract ([12 §12.2](design/12-session-memory.md#12.2%20Shape)), so contradictory intents are all injected; the line format and newline handling are unspecified, and during a rebase HEAD is detached exactly when the base memory is needed.
**Decision.** `omc memory` is local and writes under a file lock to one `optmem` file per branch, one line `<ISO UTC>\t<provider>\t<text>` each; newlines and lines over 280 bytes are refused, and text arrives through stdin or a file. `omc memory list` numbers the entries and `omc memory retract <n>` appends a tombstone; only entries not retracted are rendered. During a rebase the branch is read from git's rebase head-name.
**Automated.** true
**Affected.** [12.2](design/12-session-memory.md#12.2%20Shape), [4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree), [2.4](design/02-repos-and-config.md#2.4%20The%20cache%20(%60~/.omc2/%60))
**Source.** [R76. [medium] Session memory: superseding entries, format, detached HEAD, transport](reviews/2026-10-16-adversarial-design-review.md#R76.%20[medium]%20Session%20memory:%20superseding%20entries,%20format,%20detached%20HEAD,%20transport)
**Status.** recorded 2026-10-30
Answers: R76

### 1.51 One naming constant renders every name: omc2 until cutover, then omc

**Context.** Before cutover the v2 binary is `omc2` ([01 §1.5](design/01-principles.md#1.5%20Coexistence%20with%20v1)), yet the stub `!omc lifecycle design` ([05 §5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs)), every printed command and `allowed-tools` pattern, and `/omc:implement` reach v1, which aborts the skill load or runs v1's skills.
**Decision.** One naming constant supplies every installed, rendered or printed name: `omc2` (binary and plugin) until cutover, then `omc`. It feeds the stubs and their exact `allowed-tools`, every message, the `/<plugin>:` and `$<plugin>:` names, the MCP server name, and the home and `/tmp` roots. Skill text reaches it only through the registry variables `{{omc}}` and `{{omc_plugin}}`; hooks and facts get `OMC_BIN`. A render test rejects a bare `omc ` before cutover. An `omc2` shim stays for one release after cutover.
**Automated.** true
**Affected.** [1.5](design/01-principles.md#1.5%20Coexistence%20with%20v1), [5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs), [5.4](design/05-skill-rendering.md#5.4%20Variables), [4.1](design/04-mcp-and-cli.md#4.1%20The%20server)
**Source.** [R13. [blocker] Naming before cutover: the v2 binary is omc2, but stubs, text and slash commands say omc and collide with v1](reviews/2026-10-16-adversarial-design-review.md#R13.%20[blocker]%20Naming%20before%20cutover:%20the%20v2%20binary%20is%20omc2,%20but%20stubs,%20text%20and%20slash%20commands%20say%20omc%20and%20collide%20with%20v1)
**Status.** recorded 2026-10-30
Answers: R13

### 1.52 A per-branch thread ledger: only new activity is triaged, replies are posted once

**Context.** Replies are posted only at the end of the next publish run, which starts by triaging the same unresolved threads again ([11 §11.2](design/11-publish-lifecycle.md#11.2%20%60triage-comments%60)); omc never resolves a thread ([11 §11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60)) and nothing records what was decided or replied, so feedback loops and retries post duplicate replies.
**Decision.** Python keeps a per-branch thread ledger outside the tree: thread id, round, decision, reply URL and the last comment seen, built from the committed `Thread <id>:` lines. Triage seeds a thread only when it has no entry or a reviewer commented after omc's reply; top-level comments count as new only when newer than omc's last MR-level reply. `create-mr` posts only pending replies and records each URL as it is posted, so a retry never posts twice.
**Automated.** true
**Affected.** [11.2](design/11-publish-lifecycle.md#11.2%20%60triage-comments%60), [11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60)
**Source.** [R6. [blocker] Comment threads already answered are re-triaged on every publish, so replies loop or post twice](reviews/2026-10-16-adversarial-design-review.md#R6.%20[blocker]%20Comment%20threads%20already%20answered%20are%20re-triaged%20on%20every%20publish,%20so%20replies%20loop%20or%20post%20twice)
**Status.** recorded 2026-10-30
Answers: R6

### 1.53 Python leases pushes on the commit it last pushed; a rejection asks the owner

**Context.** Worktrees share refs with the hidden clone that watch fetches every tick, so a bare `--force-with-lease` in [11 §11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60) always matches and can overwrite a colleague's push, and a lease rejection goes to the LLM fallback.
**Decision.** Python records the commit it last pushed and pushes with `--force-with-lease=<branch>:<that commit>`, then checks with `git ls-remote` that the remote equals HEAD. A lease rejection stops and asks the owner, showing the foreign commits. Python is the only thing that pushes; the LLM fallback only fixes causes (auth, hooks, network) and reruns the push.
**Automated.** true
**Affected.** [11.3](design/11-publish-lifecycle.md#11.3%20%60create-mr%60), [11.5](design/11-publish-lifecycle.md#11.5%20Assumed%20(not%20yet%20confirmed))
**Source.** [R32. [high] --force-with-lease is defeated by background fetches, and lease rejections are 'resolved' by the LLM](reviews/2026-10-16-adversarial-design-review.md#R32.%20[high]%20--force-with-lease%20is%20defeated%20by%20background%20fetches,%20and%20lease%20rejections%20are%20'resolved'%20by%20the%20LLM)
**Status.** recorded 2026-10-30
Answers: R32

### 1.54 Stubs are stamped with the omc version; CLI, stub and watch must match

**Context.** The stubs of [05 §5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs) are installed content that can go stale, a new CLI can talk to an old running watch, and the renderer cannot tell Claude from Codex on `--done` renders.
**Decision.** `omc update` writes the stubs from the installed package, stamped with its version. Each stub names its provider in its fixed command, and every handoff line repeats it. CLI, stub and watch must carry the same version; a mismatch renders an ABORT naming `omc update` or a restart of `omc watch`.
**Automated.** true
**Affected.** [5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs), [5.7](design/05-skill-rendering.md#5.7%20User-only%20commands), [4.1](design/04-mcp-and-cli.md#4.1%20The%20server)
**Source.** [R53. [high] Stub install and refresh, CLI/watch version skew, provider detection](reviews/2026-10-16-adversarial-design-review.md#R53.%20[high]%20Stub%20install%20and%20refresh,%20CLI/watch%20version%20skew,%20provider%20detection)
**Status.** recorded 2026-10-30
Answers: R53

### 1.55 The four test repos stand in for dependency configurations; E2E tests define the rest

**Context.** Every scenario also needs an omc repo, local config, trust, design artifacts and MR comments, none of which is a branch in the four test repos of [13 §13.2](design/13-testing.md#13.2%20The%20E2E%20tests); the review proposed a fifth fixture repo.
**Decision.** The four test repos of [13 §13.2](design/13-testing.md#13.2%20The%20E2E%20tests) are material for building test cases: they stand in for dependency configurations. Everything else a scenario needs is defined by the E2E tests in the omc v2 repo itself.
**Automated.** false
**Affected.** [13.2](design/13-testing.md#13.2%20The%20E2E%20tests)
**Source.** [R22. [high] The E2E fixture state that doesn't fit in four repos, and how scenarios are wired](reviews/2026-10-16-adversarial-design-review.md#R22.%20[high]%20The%20E2E%20fixture%20state%20that%20doesn't%20fit%20in%20four%20repos,%20and%20how%20scenarios%20are%20wired)
**Status.** recorded 2026-10-30
Answers: R22

### 1.56 The daily freshness check: separate anchored windows, capped chunks, strict JSON, unknown is never no change

**Context.** [03 §3.7](design/03-watch.md#3.7%20Freshness%20checks) builds one dossier and makes one call for both decisions and every repo, so busy repos overflow it, one failure fails all, a failure can read as "no change", and "once a day" has no anchor.
**Decision.** Each decision has its own window, anchored to the commit last checked. Each repo's part of the dossier is capped and the work is split into chunks; a Python pre-filter on CI and build paths runs first. Calls follow the headless contract of [1.18](#1.18%20Sessions%20and%20headless%20LLM%20calls%20omc%20launches:%20one%20contract,%20and%20trust%20gates%20the%20lifecycle%20launchers) and return strict JSON; a repo missing from the answer is "unknown", never "no change". The check runs on the first tick 24 hours after the last one. A repo's first wiki is generated when documentation is turned on.
**Automated.** true
**Affected.** [3.7](design/03-watch.md#3.7%20Freshness%20checks)
**Source.** [R67. [medium] Daily freshness check: windows, size, sandbox, failure handling, scheduling](reviews/2026-10-16-adversarial-design-review.md#R67.%20[medium]%20Daily%20freshness%20check:%20windows,%20size,%20sandbox,%20failure%20handling,%20scheduling)
**Status.** recorded 2026-10-30
Answers: R67

### 1.57 GitNexus indexes worktrees incrementally

**Context.** Only the hidden clone at base is indexed ([03 §3.5](design/03-watch.md#3.5%20Concurrency): "no worktree is ever indexed"), so after implement the branch's own symbols and docs are missing from the graph and "GitNexus first" gives wrong answers in review and feedback work.
**Decision.** In omc v2 GitNexus indexes the worktree too, incrementally; the incremental-indexing bugs are fixed, and any that remain are patched. This replaces "no worktree is ever indexed" in [03 §3.5](design/03-watch.md#3.5%20Concurrency).
**Automated.** false
**Affected.** [3.5](design/03-watch.md#3.5%20Concurrency), [1.1](design/01-principles.md#1.1%20What%20v2%20is), [4.3](design/04-mcp-and-cli.md#4.3%20Tools)
**Source.** [R59. [high] Answers from GitNexus reflect base only, never the branch under work](reviews/2026-10-16-adversarial-design-review.md#R59.%20[high]%20Answers%20from%20GitNexus%20reflect%20base%20only,%20never%20the%20branch%20under%20work)
**Status.** recorded 2026-10-30
Answers: R59

### 1.58 E2E definitions are Cucumber/Gherkin features over a shared step library

**Context.** [13 §13.0](design/13-testing.md#13.0%20This%20repo's%20rule%20(in%20effect%20now)) says `docs/e2e-tests/` holds Markdown definitions from which test code in `tests/e2e/` is derived, but fixes no definition shape and nothing ties code to its definition.
**Decision.** E2E definitions are Cucumber/Gherkin scenarios, run against one shared step library. The step library is the test code; that also answers how code is tied to definitions. How this fits the Markdown-only rule of `docs/e2e-tests/` in [13 §13.0](design/13-testing.md#13.0%20This%20repo's%20rule%20(in%20effect%20now)) and AGENTS.md is not decided.
**Automated.** false
**Affected.** [13.0](design/13-testing.md#13.0%20This%20repo's%20rule%20(in%20effect%20now)), [13.2](design/13-testing.md#13.2%20The%20E2E%20tests)
**Source.** [E2. [high] The E2E definition format](reviews/2026-10-16-adversarial-design-review.md#E2.%20[high]%20The%20E2E%20definition%20format)
**Status.** recorded 2026-10-30
Answers: E2, E3

### 1.59 v1 and v2 are distinct products with no intersection

**Context.** The review assumed v1's `.omc/` layer, fish hooks and install names leak into v2 worktrees and asked how coexistence ([01 §1.5](design/01-principles.md#1.5%20Coexistence%20with%20v1)) is completed.
**Decision.** v1 and v2 are conceptually and technically distinct products with no intersection: v2 ignores `.omc/`, and its skills are its own. The one link is migration: v2's `/auto-integrate` ([03 §3.4](design/03-watch.md#3.4%20Setup:%20%60/auto-index%60,%20trust,%20%60/auto-integrate%60)) may take a repo's existing `.omc/` structure into account, since it already answers many integration questions.
**Automated.** false
**Affected.** [1.5](design/01-principles.md#1.5%20Coexistence%20with%20v1), [3.4](design/03-watch.md#3.4%20Setup:%20%60/auto-index%60,%20trust,%20%60/auto-integrate%60)
**Source.** [R86. [medium] Coexistence leftovers: v1's global layer in .omc repos, fish hooks, cutover, distribution name](reviews/2026-10-16-adversarial-design-review.md#R86.%20[medium]%20Coexistence%20leftovers:%20v1's%20global%20layer%20in%20.omc%20repos,%20fish%20hooks,%20cutover,%20distribution%20name)
**Status.** recorded 2026-10-30
Answers: R86

### 1.60 Plugin lists are validated and frozen at start; a missing plan fails at design's closing check

**Context.** [06 §6.1](design/06-lifecycles.md#6.1%20Lifecycles) lets a repo override any plugin list, and its example has no plan step, so implement only ABORTs after a whole design session; entry preconditions are already Python checks ([1.42](#1.42%20Python%20checks%20each%20lifecycle%20entry;%20implement,%20review%20and%20publish%20start%20only%20on%20the%20owner's%20word)).
**Decision.** At lifecycle start Python validates the resolved plugin list (an unknown name renders an ABORT) and freezes it for the rest of the lifecycle. A list that cannot produce what later lifecycles need fails at design's closing copy-and-commit ([06 §6.6](design/06-lifecycles.md#6.6%20The%20final%20artifact)), where the plan must exist; plugin manifests stay intent-only ([06 §6.2](design/06-lifecycles.md#6.2%20Plugins)), with no requires/provides fields. The [06 §6.1](design/06-lifecycles.md#6.1%20Lifecycles) example is replaced by a valid one. MVP lists name only plugins omc ships.
**Automated.** true
**Affected.** [6.1](design/06-lifecycles.md#6.1%20Lifecycles), [6.2](design/06-lifecycles.md#6.2%20Plugins), [6.6](design/06-lifecycles.md#6.6%20The%20final%20artifact)
**Source.** [R20. [blocker] Configurable pipelines can drop required plugins and gates, and the documented example is invalid](reviews/2026-10-16-adversarial-design-review.md#R20.%20[blocker]%20Configurable%20pipelines%20can%20drop%20required%20plugins%20and%20gates,%20and%20the%20documented%20example%20is%20invalid)
**Status.** recorded 2026-10-30
Answers: R20
