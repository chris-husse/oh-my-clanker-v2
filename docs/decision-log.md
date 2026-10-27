# Decision Log

*Append-only. Every ruling and its reasoning, dated.*

## 1. Review: adversarial-design-review (2026-10-27)

Every open design question, asked one at a time, with your answer. Sources: the adversarial design review ([2026-10-16-adversarial-design-review](reviews/2026-10-16-adversarial-design-review.md), items R1 to R98) and its open E2E questions E1 to E3. Each answer is also written into `docs/design/` in the same turn.
Review file (open): docs/reviews/2026-10-16-adversarial-design-review.md

### 1.1 MVP scope of multi-repo work

**Context.** [1.1](design/01-principles.md#1.1%20What%20v2%20is) says a feature can span several repos with full integration, and [13.2](design/13-testing.md#13.2%20The%20E2E%20tests) requires E2E tests of multi-repo work on a four-repo diamond. But [open-questions §H](design/open-questions.md) parks cross-repo features, and the [README](design/README.md) leaves §H out of the MVP. Every lifecycle structure is keyed by one repo plus one branch: the lifecycle folder, the artifact root, session memory, one Primary ticket, one MR. The tests can't be written, and if one feature later touches several repos, all of those keys have to be redone. Is MVP multi-repo limited to watching many repos and adding or querying them mid-design, with each feature still changing exactly one repo?
**Decision.** Neither (a) nor (c): both are MVP. 1. Working on one repo, it must be easy to add, index and gather information from other repos in full depth. 2. Changing several repos is supported too: one design spans several repos. Each repo gets a worktree (worktrunk) with the same slug. The main design creates sub-designs in the related repos. `/design`, `/implement` and `/review` each run in their own repo with full repo-local omc context, no different from running the task directly there. Implementation builds the repos in order, each inside its own repo, never from the main repo. Amended 2026-10-27 (with [R94. How sub-designs are made](reviews/2026-10-16-adversarial-design-review.md#R94.%20[blocker]%20How%20sub-designs%20are%20made)): changing several repos (point 2) is **not** MVP, but a design guideline: the MVP must not prevent it.
**Affected.** [14-cross-repo-features](design/14-cross-repo-features.md), [1.1](design/01-principles.md#1.1%20What%20v2%20is), [open-questions](design/open-questions.md)
**Source.** [R1. [blocker] MVP scope of multi-repo work](reviews/2026-10-16-adversarial-design-review.md#R1.%20[blocker]%20MVP%20scope%20of%20multi-repo%20work)
**Status.** recorded 2026-10-27 · applied 2026-10-27
Answers: R1

### 1.2 Trust: index-only by default, trusted repos and mirrors, user-only trust commands

**Context.** Trust grants code execution, and reset-rounds is what makes the fix loop's CRITICAL stop bounded. Under the 'CLI = MCP and vice versa' rule both become MCP tools on an endpoint with no authentication. The stub's `allowed-tools: Bash(omc …)` also pre-approves them as shell commands. The add-repo poll even prints the exact trust command for the agent. A prompt-injected agent, any local process or another local user can trust an attacker repo and run its code, or reset the fix budget. Frontmatter user-only flags don't help: they only block the Skill tool, not a direct `omc lifecycle publish` from Bash. Which commands are user-only, and what enforces that?
**Decision.** Trust supports whole mirrors, e.g. a company's. External mirrors can never be in the multi-repo chain apart from GitNexus indexing. Anything that runs build scripts must be explicitly listed, and the CLI command for that is not an MCP tool and is explicitly forbidden to the agent. The other gates are review item [R98. The other user-only gates: reset-rounds, configure, and unauthenticated MCP](reviews/2026-10-16-adversarial-design-review.md#R98.%20[blocker]%20The%20other%20user-only%20gates:%20reset-rounds,%20configure,%20and%20unauthenticated%20MCP).
**Affected.** [2.6](design/02-repos-and-config.md#2.6%20Trust), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules), [4.6](design/04-mcp-and-cli.md#4.6%20Command%20tree), [5.2](design/05-skill-rendering.md#5.2%20Provider%20stubs)
**Source.** [R2. [blocker] The agent can run the user-only gates: trust, trust --all, reset-rounds, configure](reviews/2026-10-16-adversarial-design-review.md#R2.%20[blocker]%20The%20agent%20can%20run%20the%20user-only%20gates:%20trust,%20trust%20--all,%20reset-rounds,%20configure)
**Status.** recorded 2026-10-27 · applied 2026-10-27
Answers: R2

### 1.3 How sub-designs are made

**Context.** The main design creates sub-designs in the related repos, and `/design` runs in each repo with full repo-local context. It is not settled whether each sub-design is a full design session of its own (brainstorm, hardening, plan, approval with you, in that repo's worktree), or whether the main session writes the sub-designs and each repo only hardens, plans and approves them. `omc design` today also creates the worktree itself and refuses an existing branch. What runs in each related repo to produce its sub-design?
**Decision.** None of the options; `omc design` can't know the repos before the design exists. Design: `/design` in the main repo produces one main design covering every repo, using full omc context of each related repo, and hardens it across the sub-repos from the main repo. Then one hardening subagent per sub-repo, in build order, each with that repo's context only. Then a final pass over the main design integrates the findings and alerts the user to problems. Implement: the main repo's agent orchestrates subagents that implement each repo's part in build order, in their own sub-repos. Review, staged: each sub-repo is reviewed individually by a subagent running the review lifecycle there, in order; the changes are integrated so the whole chain builds; then the final `/review` runs in the main repo. Not MVP, but a design guideline so nothing built prevents adding it later.
**Affected.** [14.2](design/14-cross-repo-features.md#14.2%20Changing%20several%20repos%20in%20one%20feature%20(not%20MVP;%20a%20design%20guideline)), [14.3](design/14-cross-repo-features.md#14.3%20What%20the%20MVP%20must%20not%20prevent%20(assumed,%20not%20yet%20confirmed)), [1.2](design/01-principles.md#1.2%20Cross-cutting%20rules), [MVP](design/README.md#MVP)
**Source.** [R94. [blocker] How sub-designs are made](reviews/2026-10-16-adversarial-design-review.md#R94.%20[blocker]%20How%20sub-designs%20are%20made)
**Status.** recorded 2026-10-27 · applied 2026-10-27
Answers: R94

### 1.4 Parked

R95 and R96 are parked with [14.2](design/14-cross-repo-features.md#14.2%20Changing%20several%20repos%20in%20one%20feature%20(not%20MVP;%20a%20design%20guideline)) and are not MVP.
**Status.** note
