# 7. The design lifecycle

## 7.1 `omc design <repo-hint> "<seed>"`

Goes from one shell command to a fresh worktree on a new branch with a session
open in it, running the design lifecycle. The first argument names the repo; the
second is the design seed. Every step is its own `omc internal` command, so it can
be run from the console or inlined in skills. `omc design` calls them in order.

| # | Command | Does |
|---|---|---|
| 1 | `omc internal check-watch` | watch is up (MCP responds) and the provider's harness CLI is on PATH |
| 2 | `omc internal resolve-repo <hint>` | Python lookup that prints the repo key: exact key or name, then a unique case-insensitive prefix or substring; a full SSH URL is accepted as-is. If ambiguous, exits with the candidates and the CLI asks you to pick |
| — | `omc internal find-repo <hint>` | Only for a repo omc has never seen: an LLM call with the agent's forge tools proposes an SSH URL; you confirm before it is added |
| 3 | `omc internal create-slug <seed…>` | Joins all its arguments as the raw seed. An LLM call on `design.models.simple` makes the slug, doing a basic ticket fetch of its own (separate from the full fetch in `explain-seed`). Python only checks the format (`[a-z0-9-]`, ≤ `slug.max_length`). The slug is always LLM-generated: omc can't know the tracker or what it is reading |
| 4 | `omc internal ensure-repo <repo> --until queryable` | Adds the repo if needed (`add-repo`) and polls the job until the state is reached, showing watch's checklist and any trust prompt |
| 5 | `omc internal branch-name <repo> <slug>` | Prints `<branch_prefix><slug>` |
| 6 | `omc internal branch-dir <repo> <branch>` | Prints `~/.omc2/repos/<repo-key>/branches/<branch-file>/` |
| 7 | `omc internal create-worktree <repo> <branch>` | Through watch: fetch, verify the hidden clone is exactly on `origin/<base>` (so a worktree is never cut from an odd state), cut `<worktree_location>/<repo-key>/<slug>`. Fails if the worktree exists |
| 8 | `omc internal title set -- <branch>` | Tab title |
| 9 | (exec) | The design lifecycle's provider and orchestrator model, in the worktree; the seed is written to `design/seed.md` in the lifecycle temp folder and never placed in the prompt |

- **An existing worktree** is a hard stop. `omc design` fails and offers to
  recreate it through `omc internal close-worktree <repo> <branch>`, which refuses
  if the worktree has uncommitted changes or commits not on origin, and names what
  would be lost.
- **An existing branch** (local or on origin) without a worktree: `omc design`
  fails and points to `omc resume`. `omc design` never continues a branch.
  `omc resume` (detect the lifecycle stage, create the worktree, check out the
  branch, re-enter the lifecycle) is parked.
- **Flags:** `--claude` / `--codex`, and `--headless` (non-interactive, so omc's
  own E2E suite can drive the lifecycle). The same flags exist on `omc implement`
  and `omc review`.

## 7.2 Default pipeline

```yaml
design: [explain-seed, superpowers-brainstorm, pocock-grilling-with-docs,
         design-hardening, write-implementation-plan, approve-design]
```

`pocock-grilling-with-docs` is parked (open-questions.md). There is no
`design-review` plugin; it was replaced by `write-implementation-plan`.

## 7.3 `explain-seed`

- **Input:** `design/seed.md`. **Output:** `design/explain-seed/<slug>.md`, the
  seed enriched with context.
- **Skill:**
  1. `<match "omc:repo_queryable">` — if not, the skill is only an ABORT naming
     the repo's state (a safety net; `omc design` normally guarantees it).
  2. **Context gate:** is there a clear problem and goal? If not, it says exactly
     what is missing and waits.
  3. Runs the `design:explain-context` hook against the seed.
  4. Writes the output document.
- **omc's default `design:explain-context` contribution:**
  - if the seed names a ticket or URL, fetch it with whatever tracker or doc
    tools the session has (omc never needs to know the tracker): parent or epic,
    linked issues, linked documents, each with a 1–3 sentence summary and link,
    or *"couldn't fetch — reason"*;
  - GitNexus first (`query`/`context` on the seed's concepts), then `docs_grep`
    for exactly what the graph pointed to.
- **Output skeleton** (fixed, so later plugins know where to look):
  - `## Seed` — verbatim
  - `## Ticket` — only if there is one; it opens with fixed lines that Python
    parses, followed by prose:

    ```
    Primary: <KEY or URL>
    Related: <KEY or URL>, <KEY or URL>
    ```
  - `## References` — links and summaries, plus any that couldn't be fetched
  - `## Code context` — findings from graph and docs, cited as `file:symbol`
  - `## Open gaps` — what is still unknown

  The first plugin that drafts the design adds `## Design` and keeps the rest.
- **Ticket reference:** the design carries one **primary** ticket (the one being
  worked on) plus an optional list of **related** tickets, in the `Primary:` /
  `Related:` lines above. Any design plugin may edit those lines (e.g. when
  brainstorming finds the real ticket). With no primary ticket, `ticket-start` in
  implement is skipped. There is no way to add a ticket later.

## 7.4 `superpowers-brainstorm`

- **Input:** `design/explain-seed/<slug>.md`. **Output:**
  `design/superpowers-brainstorm/<slug>.md`, the same document with `## Design`.
- **Prerequisite:** `<match "omc:superpowers_installed">`, else ABORT with the
  provider's install instructions (Claude:
  `/plugin install superpowers@claude-plugins-official`).
- **Calls the installed `superpowers:brainstorming`** (Skill tool in Claude,
  `$superpowers:brainstorming` in Codex), wrapped by omc's overrides. omc does not
  copy its text.
- **Overrides:**
  - always write the document; a bounded or spike classification only makes it
    shorter;
  - write to the plugin's `/tmp` folder, never `docs/superpowers/specs/`;
  - no commit;
  - no `writing-plans` handoff;
  - the end condition below.

  Kept from upstream: the intent write-back, 2–3 approaches with a recommendation,
  the opt-in visual companion.
- **Presentation rule, built in** (replacing upstream's one-question-per-message
  pacing):
  - one complete, formatted document per round;
  - one question group at a time;
  - every question listed in full at the end: what is decided, the options, the
    recommendation, the cost of choosing wrong;
  - unanswered questions stay open and are listed again in full, never compressed.
- **End condition:** once no question is open, the plugin asks *"The design is
  complete. Move on to grilling?"* Only an explicit yes to that question runs
  `--done`. A bare "ok" to another question doesn't count.
- No hooks.

## 7.5 `pocock-grilling-with-docs` (parked)

Matt Pocock's `grill-with-docs` ([mattpocock/skills](https://github.com/mattpocock/skills),
MIT) is a one-line delegation to his `grilling` (decision-tree interview in rounds)
and `domain-modeling` (writes `GLOSSARY.md` and ADRs) skills, and has
`disable-model-invocation: true`. Known upstream problems: partial skill loading,
silent no-writes inside orchestration layers, decisions living only in the
conversation, and writes into the target repo. Install: Claude
`claude plugin install mattpocock-skills@claude-plugins-official`; Codex
`codex plugin marketplace add mattpocock/skills` +
`codex plugin add mattpocock-skills@mattpocock`. Its four open questions are in
open-questions.md.

## 7.6 `design-hardening`

A thin orchestrator over `design:hardening` hooks (06-lifecycles.md §6.5).

- **Input:** the previous plugin's document. **Output:**
  `design/design-hardening/<slug>/`, ending in a mandatory
  `## Deliberate complexity` section (`None.` when nothing was waived).
- **A round:**
  1. Split the design into sections (`omc internal design-sections`: each `###`
     under `## Design`).
  2. **Explain each section** with the `design:explain-context` hook, in parallel
     subagents (one per section, on the design model). Python joins the blocks
     into `design-explained.md` in section order. This happens **once**; later
     rounds never re-explain.
  3. Run every `design:hardening` hook, inlined in order (omc, global, repo; by
     name within a layer). Each reads the design and `design-explained.md` and
     writes findings. Python hash-checks the design after each hook.
  4. Merge the findings, apply them, ask about whatever needs a decision, and
     write waivers into `## Deliberate complexity`.
  5. Show the round overview and ask whether to run another round, with a
     recommendation.
- `design-explained.md` and the findings files live in the work directory, never
  in the committed design.
- **Default hooks:**
  - **`grug`** — v1's complexity lens: the spec rules of grugbrain.dev, each
    finding citing a rule and naming the simpler alternative. Findings only.
  - **`multi-agent-hardening`** — one hardening agent per design section (v1's
    explain check: architectural sense, what it touches, what could go wrong),
    merged into one findings file.
- **Carried from v1:** fix first, then waive (when a finding contradicts a
  recorded decision), then ask; waivers go to `## Deliberate complexity`.

## 7.7 `write-implementation-plan`

The plan is written in the design lifecycle because plan quality is critical for
good results, and implement may run on another, cheaper provider.

- **Uses the installed `superpowers:writing-plans`** with overrides:
  - keep its structure: header (Goal, Architecture, Tech Stack, `Spec:` link),
    `## Global Constraints`, `## Review Focus`, tasks with **Files** and
    **Interfaces** and TDD steps, the no-placeholders rule, the self-review;
  - add v1's instruction word for word: every task carries
    `Complexity: simple | medium | high` (multi-file, architecturally tricky or
    ambiguous work is `high`; narrow routine work `simple`; otherwise `medium`);
    the plan stores complexity, never model IDs;
  - save to `<slug>/<slug>-plan.md` inside the design folder; its `Spec:` line is
    the relative link `./<slug>.md`;
  - never ask for an execution method, never start building.
- **TDD steps run tests through watch:** `omc run check --test <selector>`, using
  the per-repo snippets `/auto-integrate` learned (the plan subagent gets them as
  context); each task ends with a full `omc run check`. Where no selector snippet
  exists, the step falls back to the full check and the plan says so.
- The plan is written by a subagent on the design lifecycle's model.
- **Plan hardening:** the same read-only findings machinery with
  `design:plan-hardening` hooks. The default hook only says *"harden the
  implementation plan, one agent per task"*, with no checklist; more can be added
  later.
- **Design changes found while planning:** the plugin never edits `<slug>.md` on
  its own. Each needed change is a `Needs decision: yes` question to you; on yes
  it is applied and listed in the plan overview. Python hash-checks `<slug>.md` at
  `--done`; a change without a recorded amendment fails the skill.
- **`--done` checks:** every task has `Complexity:`, **Files** and **Interfaces**,
  and no placeholder patterns remain.

## 7.8 `approve-design`

- **Input:** the folder with `<slug>.md` and `<slug>-plan.md`.
- **Shows an overview:** the goal in one paragraph, one line per `## Design`
  section, every decision with its source plugin, `## Deliberate complexity`, any
  planning amendments, the plan's task list with each `Complexity:`, and links to
  both files. It ends with *"Approve and commit?"* Only an explicit yes commits.
- **On no:** you say what's wrong; the plugin offers, with a recommendation,
  either **edit here** (small, local changes, applied and listed, then asked
  again) or **rerun from a plugin** (`omc lifecycle design --from <plugin>`).
  Changes that touch the design's structure are recommended as a rerun.
- **On yes:** `check-artifact` and the ticket-line check (the `Primary:` /
  `Related:` lines must be well-formed; `Primary:` may be absent but never
  appears twice), then Python copies and commits (06-lifecycles.md
  §6.6). Commit messages: `<repo-key>: design and plan for <slug>` in your omc
  repo; `docs: design and plan for <slug>` on a feature branch. The temp folder is
  deleted afterwards and the session stays open.
- **The orchestrator's closing statement** (a statement, not a question): type
  `/omc:implement` here (`$omc:implement` in Codex) to implement on this provider,
  or exit and run `omc implement --claude|--codex` in the worktree for a fresh
  session on another provider. Implement reads `<slug>.md` and `<slug>-plan.md`
  from the committed artifact.
