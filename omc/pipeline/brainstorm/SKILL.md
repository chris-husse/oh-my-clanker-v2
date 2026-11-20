---
name: brainstorm
description: "The pipeline's brainstorm, seeded by just design or typed: prime, seed, brainstorm with the owner to the committed design doc; it never starts /design, which the owner types when they call the design done. /brainstorm <step-id> enters at that step."
disable-model-invocation: true
---

# brainstorm

The owner's conversation of the `omc/` pipeline, before `/design`: from the brief to a committed design doc
(`<date>-<slug>-design.md` in the specs folder, `paths.specs` of `omc/config.yaml`), and nothing else. It writes the doc
and records the owner's rulings in the log (`paths.decision_log`); it edits no protected document (a file matched by
`paths.protected`) and no code, and nothing in it builds, tests or runs a gate: no `/check`, `/build`, `/verify`, no
`just omc gate run`. The log and the entry are `omc/tools/decisions/FORMAT.md`.

**The brief** is the argument: a file (`.cache/omc/brief.md`, which `just design` writes, or a `<name>.md` in the briefs
folder, `paths.briefs`) or the text typed. With no argument, or a step id, it is `.cache/omc/brief.md` when that exists;
with none at all, `primer` asks the owner for it.

**Where you are.** There is no run file. A skill started again, after a compaction or in a fresh session, begins at its
first step, and every step that is done skips itself on its tool's answer; "done" is read from the repository or a
record a tool wrote, never from what the session remembers. Whatever the step entered, `just omc enter brainstorm`
runs first (it writes `.cache/omc/current`, which puts this skill back into a compacted session; `/design` writes its
own marker over it). `/brainstorm <step-id>` enters at that step; `/brainstorm` alone, or with anything that is not
one of its step ids (the brief's path, a sentence), begins at `primer`, and that argument is the brief.

**`/design` is the owner's to start, never the session's.**

- `/brainstorm` never starts `/design` or any of its steps (harden, consistency, integrity, plan), whatever it reads: a
  committed doc, an approved design, the owner's "fine" or "looks good". Committing the doc and showing it to the owner
  is where it stops; its last message tells them, literally, to type `/design` when they call the design done.
- Only the owner typing `/design` as a command starts it: the harness's `<command-name>/design</command-name>` in their
  turn. `/design` (or "design", "the design step") named in their prose (a question about it, a description of the flow,
  "then /design should…") is talking about it, never a start. When the session cannot tell which, it asks them and
  starts nothing.
- `just design` seeds `/brainstorm`, never `/design`, so the launch can no longer be mistaken for their start.
- `/design`'s own description and its first step say the same: entered by the owner's typed command only; a session in
  `/brainstorm` that finds itself about to run it stops and tells them to type it.

**Terminals and tools.** ▣ (a terminal) and ✓ (a tool check). A terminal is run as: `just omc models <role>` (the role
is written at each call), then one fresh agent, `subagent_type: general-purpose`, with that model where the harness
takes it (an empty model: the session's own, said in one line), its prompt exactly
`Read <root>/omc/terminals/<name>/SKILL.md and follow it. Root: <root>.` and then the inputs its step names, one per
line; `<root>` is the absolute path `git rev-parse --show-toplevel` prints. Its last line is
`OUTCOME {"outcome": "<word>", …}`: the step reads the word and the fields it names; the report above the line is prose
for this session, never parsed. Every terminal may also return `failed` (`reason`: told to the owner, who says whether
it runs again); an agent that ends without an `OUTCOME` line has failed.

**Talking to the owner.** This is their conversation: every question is asked there, one at a time; a design doubt goes
through `/answer-doubt` first, and a ruling is recorded through `/record-decision` when they give it. Every message
opens with the skill and step and its place, `/brainstorm › seed (step 2 of 3)`. Every option shows what it concretely
produces, never a bare label, with the recommended one named; a long message that asks questions ends with every
question repeated as a numbered list, one line each with the recommended default. Their vocabulary: "the log", "an
entry", "recorded", "applied", "the protected documents", "the merge-base", "a question file", "the record", "before
implementation"; no coined compressions.

**Shell.** Variables do not survive between commands: begin every command with
`ROOT=$(git rev-parse --show-toplevel)` and run it in a subshell, `(cd "$ROOT" && …)`; a value a command printed is
written out in the next one. The log is written only through `just decisions` and `/record-decision`. A commit stages
its paths by name, `git add -- <path>…`, never `git add -A` or `git add .`, and its message ends with
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## `primer` — read the work context and show it to the owner.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc enter brainstorm && just omc record)
```

Skip when `just omc record` finds one (exit 0): on to `brainstorm`.

▣ primer, role `orchestrator`: `brief: <the brief>` (its path, or the text). No brief at all: ask the owner for it
first. `done`, taken as reported: its report is shown to the owner, whole (the subthemes and rules, the stories, the
documents, the code, the open questions, the related open work, the scope questions); then on to `seed`. Its scope
questions are `seed`'s to ask.

## `seed` — take the owner's seed and scope answers.

Skip when `just omc record` finds one.

First the owner's own first thinking: what they have in mind for this work, asked open, before any option is put to
them. Then the scope questions whose answer changes the direction of the design (what is in and what is out, which rule
or document it would change): the primer's, and those their first thinking raises; a question whose answer changes
nothing of the direction is not asked. One at a time, each option with what it produces and the recommended one named. A
scope answer that rules on a rule or a protected document is a design doubt: `/answer-doubt`, and `/record-decision`
when they rule.

The primer's "Related open work" is one question, a multi-pick: which of its items the branch takes in, each with its
source, why it fits and what taking it means. The taken items go into the design doc: a taken deferred entry gets its
row in "Decisions and the pages they change", in the fold's row form (`omc/terminals/harden/SKILL.md` › "3. The
fold"), so that `/design`'s plan gives it an apply task (`/apply-decision`) like any recorded one; a taken brief
(of `paths.briefs`, which ▣ describe deletes in the branch's commit) or a taken question (answered in the branch) is
named in the doc's scope. None picked is a valid answer. Then on to `brainstorm`.

## `brainstorm` — discuss the design with the owner until it converges.

Skip when `just omc record` finds one and the owner did not reopen the design (entering at it, `/brainstorm brainstorm`,
is reopening it): the last message below, and nothing else.

`superpowers:brainstorming`, inline in this session through the Skill tool, unmodified but for one override: it stops at
the approved, committed design doc, `<date>-<slug>-design.md` in `paths.specs` (the branch's slug, committed by name),
and it never invokes `superpowers:writing-plans`; this skill ends instead. Its primer and seed are the two steps above.
Doubts in it go through `/answer-doubt`, rulings through `/record-decision`, in the conversation; the entries stay
uncommitted in the log until `/design` commits them. A new external dependency or system gets its spike here, and a run
over many units of the same kind its pilot with the owner, both before the design doc (AGENTS.md).

✓ `just omc record` finds the committed doc; it finds none: the brainstorm is not done, said to the owner, and it goes
on. Found: the doc is shown to them, and the last message tells them, literally: "The design doc is committed. Type
`/design` when you call the design done; until then we go on here." Nothing follows: not `/design`, not any of its
steps, whatever they answer short of typing it.

## Never

- Never start `/design` or any of its steps (harden, consistency, integrity, plan): only the owner's typed `/design`
  does.
- Never a build, a test or a gate: no `/check`, `/build`, `/verify`, no `just omc gate run`.
- Never edit a protected document (a file matched by `paths.protected`) or code.
- Never write the log but through `just decisions` and `/record-decision`; never invent a decision the owner did not
  rule.
- Never `superpowers:writing-plans`: the plan is `/design`'s.
- Never `git add -A` or `git add .`.
