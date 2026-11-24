---
name: design
description: "The pipeline's design phase, entered only by the owner's typed /design once /brainstorm has committed the design doc: bring the branch onto the base branch, harden the record, gather and check the decisions, commit, write the plan, then /implement unless ask_for_provider_handoff; no build, no test. /design <step-id> enters at that step."
disable-model-invocation: true
---

# design

The design phase of the `omc/` pipeline, in the owner's session: from the committed design doc `/brainstorm` left to a
hardened, committed design record and its committed plan, and nothing else. It writes the record and the plan and
records the rulings in the log (`paths.decision_log` of `omc/config.yaml`); it edits no protected document (a file
matched by `paths.protected`) and no code, and nothing in it builds, tests or runs a gate: no `/check`, `/build`,
`/verify`, no `just omc gate run`, in any step and in its rebase. The log, the entry and the question file are
`omc/tools/decisions/FORMAT.md`.

**Entered by the owner's typed command only.** `/design` starts when the owner types it as a command (the harness's
`<command-name>/design</command-name>` in their turn), when they call the design done; never from `/brainstorm`, never
on the session's own reading of a committed doc or of their "fine", never from their prose naming it (the compacted
session's resume, `just omc enter --resume`, continues a run they started; it starts none). A session in `/brainstorm`
that finds itself about to run it stops and tells them to type it. Once they have typed it, the design is defined and
the run is autonomous to the push ("From `/design` on, no question blocks the run").

**Where you are.** There is no run file. A skill started again, after a compaction or in a fresh session, begins at its
first step, and every step that is done skips itself on its tool's answer; "done" is read from the repository or a
record a tool wrote, never from what the session remembers. Whatever the step entered, `just omc enter design` runs
first (it writes `.cache/omc/current`, which puts this skill back into a compacted session). `/design <step-id>` enters
at that step; `/design` alone, or with anything that is not one of its step ids, begins at `record`. One exception,
after a compaction: when the conversation (or its summary) shows that the owner called the design settled, the session
enters at `integrity`, as `/design integrity`, not at `record`, so that their stop holds ("The loop").

**Terminals and tools.** ▣ (a terminal) and ✓ (a tool check). A terminal is run as: `just omc models <role>` (the role
is written at each call), then one fresh agent, `subagent_type: general-purpose`, with that model where the harness
takes it (an empty model: the session's own, said in one line; an empty effort: the harness's default), its prompt
exactly `Read <root>/omc/terminals/<name>/SKILL.md and follow it. Root: <root>.` and then the inputs its step names, one
per line; `<root>` is the absolute path `git rev-parse --show-toplevel` prints. Its last line is
`OUTCOME {"outcome": "<word>", …}`: the step reads the word and the fields it names; the report above the line is prose
for this session, never parsed. Every terminal may also return `needs_user` (`question`, `options`, `picked`: "A
ruling", below) and `failed` (`reason`: told to the owner, who says whether it runs again); an agent that ends without
an `OUTCOME` line has failed. **Checked, not believed:** a terminal's word that a tool contradicts is a hard stop to the
owner (both answers shown, nothing goes on until they rule); an outcome no tool checks is taken as reported, and the
message says so.

**From `/design` on, no question blocks the run.** Every question from here to the push (harden's `QUESTION` blocks,
consistency's and the impact reading's `CONFLICT` blocks, a terminal's `needs_user`, the plan's doubts) is taken so,
never put straight to the owner:

- **No protected document would change** (`/answer-doubt`'s gate: no rule and no protected document): this session
  decides it itself, from the record, the conversation and the code, and writes it where it belongs (the record's
  section, the plan); the message says how it was decided.
- **A design doubt** (a rule or a protected document would change): `/answer-doubt` inline, through the Skill tool, as
  it works from implementation on: the docs first, an independent agent answers too, the question goes to the run's
  question file with the picked answer. Both agree: the ruling is recorded through `/record-decision` at once with
  `Automated: true`, its `Context` saying it was ruled by the agreement of `/answer-doubt`'s two answers, and the run
  acts on it. They disagree: the run acts on its pick all the same, recorded at once through
  `/record-decision --disagreed` (`Automated: disagreed`), and goes on; the owner rules it after their screenshot
  review in `/audit` (`push`, through `/review-decisions`), confirmed or overruled.
- **The limit** (`/answer-doubt` step 6): the sixth disagreed entry not yet ruled stops the run there; the owner is
  asked about all six in the conversation, one at a time, each ruling recorded at once, and the run goes on. It is the
  only question the run puts to them before their screenshot review.

Stops that are not questions (a hard stop, a `failed`, a refused tool, a path the session did not write) still go to
the owner as each step says.

**A ruling.** On `needs_user`: its question is taken as "From `/design` on" says, its `picked` the answer this session
weighs first. An answer that changes a rule or a protected document is a decision, recorded at once through
`/record-decision`. Then a terminal that takes an `answer` is run again with it, one more input line
`answer: <the answer>` (for ▣ rebase that is its own `answer` input).

**Talking to the owner.** They may be away from here to the push: the session writes for them to read later, and asks
them only what "From `/design` on" sends to them. Every message opens with the skill and step and its place,
`/design › harden (step 3 of 7)`, and progress as done of total where a step has several items (`conflict 2 of 3`).
Every question decided or ruled shows its options, each with what it concretely produces, never a bare label, and the
one taken; a long message that asks questions ends with every question repeated as a numbered list, one line each with
the recommended default. Their vocabulary: "the log", "an entry", "recorded", "applied", "the protected documents", "the
merge-base", "a question file", "the record", "the plan", "before implementation"; no coined compressions.

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; a value a command printed (`<record>`, `<old base>`, a path) is written
out in the next one; so are the configured paths, read from `omc/config.yaml`: `<log>` is `paths.decision_log` (no log
configured: `<log>` is dropped from the command, and a step about the log is skipped),
`<questions>` is `paths.questions` (a folder, ending with `/`), and `<protected>…` are the globs of `paths.protected`,
each written as a `':(glob)<glob>'` pathspec. The log is written only through `just decisions` and `/record-decision`. A
commit stages its paths by name, `git add -- <path>…`, never `git add -A` or `git add .`, and its message ends with
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

**The record.** `<record>` is the path `just omc record` prints (the `*-design.md` of `paths.specs` the branch added and
committed since the merge-base). More than one: the one with the branch's slug, else the newest by its date prefix, said
in one line; never a question.

## `record` — refuse without the committed design doc.

Entered by the owner's typed `/design` only (above), never by the session.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc enter design && just omc record)
```

✓ It prints `<record>` (exit 0): on to `fresh`. `no record committed on this branch` (exit 1): stop, nothing else
run, to the owner: "No design doc is committed on this branch; finish the brainstorm first (`/brainstorm`), then type
`/design` when you call the design done." An `error:` (exit 2, no `origin/<base>`): to the owner, with the error.

## `fresh` — bring the branch onto `<base>`.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc enter design && { [ -e "$(git rev-parse --git-path rebase-merge)" ] || [ -e "$(git rev-parse --git-path rebase-apply)" ]; } && echo 'rebase paused' || echo 'no rebase')
```

1. **A rebase paused** (an earlier session ended at a stop): it goes straight to ▣ rebase (item 5), before the trim,
   which a paused rebase would meet; once ▣ rebase is done and checked, on with item 2, whose check (item 3) then finds
   the mark and leads to the reading.
2. **The trim**, so that the log holds the branch's entries and no other:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions trim)
   ```

   It prints `<k> entries trimmed`. Its change is committed in item 4, before any rebase; with no rebase, `integrity`
   commits it.
3. **Is it done:**

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc git rebased-on; just omc impact)
   ```

   `rebased on origin/<base>` and `no impact pending`: the rest is done, on to `harden`. Rebased with an old merge-base
   printed (a rebase whose impact was not read): item 6. `behind origin/<base> by <k> commits`: item 4. An `error:` (the
   fetch failed): to the owner, with the error.
4. **Before the rebase**, the tree must be clean, since the tool refuses a dirty one:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git status --porcelain --untracked-files=all; echo 'question files:'; for f in <questions>*.md; do head -1 "$f" | grep -q '^# Questions: ' && echo "$f"; done)
   ```

   Exactly two kinds of path are committed here, by name: the log, `<log>` (the trim's change, entries an earlier
   session recorded), and the question files among the dirty paths (a file whose first line starts `# Questions: `,
   FORMAT.md › "The question file", the second part's list; an answered one included, which
   `just decisions pending --questions` no longer names):

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <path>… && git commit -m "Design: the log and the question files before the rebase" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <path>… && git show --stat --format='%h %s' HEAD)
   ```

   Any other dirty path (the record mid-hardening, another file under `<questions>`) goes to the owner, the options
   being to commit those paths by name and rebase, or to leave the rebase for now, which stops `/design` here until they
   have committed or discarded them.
5. **▣ rebase**, role `orchestrator`: `squash: no`, `phase: design`, `answer: none` (or the ruled option). A conflict of
   the log is settled inside it by `just decisions resolve`, then `renumber`, `trim` and the log's `check`; it builds
   and tests nothing.
   - `rebased` or `current`: ✓ `just omc git rebased-on`; `behind`: a hard stop. Then item 6, whatever the word
     (`current` says nothing of a pending impact).
   - `needs_user`: a ruling. An entry `resolve` refused, or two sides whose intents exclude each other (the terminal
     merges every other conflicted file itself, both sides kept; never an option to drop a side, merge by hand or
     abort), is the owner's (the project's `AGENTS.md`, its rebase-conflict rule: "Only an entry `resolve` refuses, or
     two sides whose intents exclude each other … go to the owner"): their ruled option goes back to ▣ rebase as its
     `answer`, and the terminal applies it and continues the paused rebase (never `git rebase --abort` or `--skip` by
     this session; an abort is the owner's own command, when an option they take says so). Uncommitted paths after a
     continued paused rebase: to the owner, the paths named; while a rebase is paused (the test of `fresh`'s first
     command), never a commit, a restore or a `reset --keep` by this session; once no rebase is paused, they are
     committed by name as item 4 says (its two kinds; any other path theirs), then ▣ rebase again with `answer: none`.
     A refused or red log step (`renumber`, `trim`, `check`): to the owner, the lines quoted; a bad base is fixed, never
     worked around. The question of a rebase the tool did not start (no mark) carries its literal shas: the option
     `old_base <sha>, new_base <sha>` is item 6 on those two shas, with no second rebase; `read no impact` is item 7.
   - `failed`: to the owner, with its reason.
6. **The impact reading.** The old merge-base is the mark (`just omc impact`), or the `old_base` the owner took in
   item 5; none: item 7. The branch holds a record (`record` found it), so ▣ impact, role `orchestrator`:

   ```text
   old_base: <the old merge-base>
   new_base: <git merge-base HEAD origin/<base>, or the new_base the owner took in item 5>
   phase: design
   ```

   - `none`: item 7.
   - `found` (`lags`, `conflicts`), taken as reported: each `CONFLICT` block, one at a time (`conflict 1 of 2`), is
     taken as "From `/design` on" says, its pick the answer weighed first; a ruling is recorded through
     `/record-decision` (an entry that replaces one of the branch's says `replaces decision <n>` in its `Context`). Then
     the lags: ▣ harden at once, its role the one `just omc pass harden` prints (a pass of `harden`, counted as in
     `harden`): `record: <record>`, `lags:` followed by every `LAG` block exactly as the report printed it (the
     multi-line blocks verbatim, one after the other, a blank line between two), `problems: none`, its hash checked
     before and after as in `harden`. Its outcome: on either `changed` or `unchanged`, its `QUESTION` blocks
     (`questions` > 0) are taken first, as in `harden`, whose own run comes later;
     `unchanged` although lags were given (none followed): each lag is then taken as a question of "From `/design` on",
     with what following it would change in the record, before the mark goes; `failed`, to the owner, with its reason,
     and the mark stays. A lag that would change what an entry of the branch rules is taken like a conflict.
   - `failed`: to the owner, with its reason.
7. **The mark removed**, once the reading's conflicts are ruled and its lags handed to ▣ harden (or to the owner), and
   also when no ▣ impact ran but a mark is there, or it would stay and `fresh` would never skip again:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc impact --done)
   ```

   Then on to `harden`. No `/check` after this rebase, and nothing else builds or tests.

## `harden` — harden the record section by section.

Skip when `just omc settled`.

The record first, then its hash before the run, for the check after it:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc record)
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git hash-object -- <record>)
```

No record (exit 1): back to `record`, which stops. The pass is counted by the tool, not the session, so that a restart
or a compaction cannot reset it (on the tiers of `omc/config.yaml`: the first pass of ▣ harden runs on the role
`harden`, the `max` tier, every later one on `harden-repeat`, the `medium` tier); its role, then its model:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc pass harden)
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc models <the role it printed>)
```

A printed `"pass"` above 3 (reached through `consistency`'s way back, `integrity`'s, the impact reading taking pass 3,
or a restart) runs no ▣ harden. Entered with `PROBLEM:` lines from `integrity`: those lines go to the owner, as after
their stop ("The loop"), never on to `consistency`; otherwise on to `consistency`, the message naming that the cap is
spent.

▣ harden, that role:

```text
record: <record>
lags: none
problems: none
```

`problems:` holds instead the `PROBLEM:` lines `integrity` sent back, verbatim, one per line. It checks every section
against the vault and the code it cites, folds every entry that has no row into "Decisions and the pages they change",
edits the record only and commits nothing. ✓ `git hash-object -- <record>` again: a new hash is `changed`, the same
`unchanged`; a word that disagrees is a hard stop.

- Each `QUESTION` block, one at a time (`question 1 of 3`), is taken as "From `/design` on" says, its pick the answer
  weighed first. A ruling that changes a rule or a protected document is recorded through `/record-decision` (the next
  run folds it, and this step runs again within the cap); any other answer changes the record's design only, and this
  session writes it into the section the block names. A disagreement acted on and recorded `disagreed` does not hold
  the step: the work goes on on its picked answer, and the owner rules it after their screenshot review.
- `changed` with `edits: material`: this step again, unless this was the third pass.
- `changed` with `edits: cosmetic`, or `unchanged`: on to `consistency`, the edits kept. Its `QUESTION` blocks are taken
  either way, each ruling handled as above, and a ruling that changes the record sends this step again, unless this was
  the third pass.
- After the third pass (`just omc pass harden` printed `"pass": 3`): on to `consistency` whatever the outcome, the
  message naming the edits still coming in; a `PROBLEM:` line of `integrity` this pass did not settle goes to the owner,
  as after their stop.
- `failed`: to the owner, with its reason.

## `consistency` — check the entries against each other, the record and the protected documents.

Skip when `just omc settled`, or when `just decisions list --branch` prints no entry and the record's section
"Decisions and the pages they change" has no row (on to `integrity`): `<base>`'s deferred entries, which the plain
`list` shows too, are not the branch's.

Its pass counted as in `harden` (`just omc pass consistency`); it prints the role `orchestrator` on every pass, the
orchestrator's model (`fable` is for ▣ harden's first pass only):

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc pass consistency)
```

▣ consistency, role `orchestrator`: `record: <record>`.

- `consistent`, taken as reported: on to `integrity`.
- `conflicts` (`count`): each `CONFLICT` block, one at a time (`conflict 1 of 2`), is taken as "From `/design` on"
  says, the terminal's pick the answer weighed first; a ruling is recorded through `/record-decision`, an entry that
  replaces another saying `replaces decision <n>` in its `Context`. "Both stand" records nothing. A new ruling: back
  to `harden`. None (every conflict left to stand): on to `integrity`.
- `failed`: to the owner, with its reason.

## `integrity` — check the decisions mechanically and commit the design.

Skip when `just omc settled`.

**Entered at it** (`/design integrity`), this step is the owner's stop ("The loop"): a line below that goes back to
`harden` goes to them instead, never back to `harden`.

✓ the mechanical check of the decisions; it reads the log, the record, git and the vault's links, and builds nothing:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just design-integrity-check --phase design)
```

It prints one `PROBLEM: <check>: <detail>` line per break, `<check>` one of `decisions check`, `record`,
`links-check`, `guard`, then `OK` or `<k> problems`. The `questions` and `disagreed` checks wait for the push gate:
with `--phase design` an open question in a question file and an entry recorded `disagreed` are no problem here (the
owner rules them after their screenshot review, in `/audit`'s `push`).

- **A `record` line, or a `links-check` line in the record**: back to `harden`, its `problems` those lines. The same
  line again after a `harden` that returned `unchanged`: hardening did not settle it, a stop, and the owner is offered
  it explicitly, each option with what it produces: harden again with it; or call the design settled and leave the line
  standing ("The loop"), in this session or, on a restart, by typing `/design integrity`.
- **A `guard` line**: a protected document changed before implementation, a stray edit, whose one remedy here is the
  restore, making the page equal the merge-base (`<page>` the page the line names: edited, deleted, renamed, added,
  staged or untracked alike). First the message shows what the restore removes, the page's diff against the merge-base
  (an untracked page's whole text, as the second part prints it):

  ```bash
  ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git diff $(git merge-base HEAD origin/<base>) -- <page>; git ls-files --error-unmatch -- <page> >/dev/null 2>&1 || [ ! -e <page> ] || git diff --no-index -- /dev/null <page>)
  ```

  The message names the page, shows that diff and says it will be restored from the merge-base; whether the change is
  wanted is a design doubt, taken as "From `/design` on" says: wanted (ruled), it is recorded as an entry through
  `/record-decision`, its ruling saying what the diff says, to be folded by `harden` and applied by the plan; not
  wanted, or left open, nothing is recorded. The page is restored either way, after that, since an entry never backs
  a page before it is applied:

  ```bash
  ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git cat-file -e $(git merge-base HEAD origin/<base>):<page> 2>/dev/null && echo 'merge-base has it' || echo 'merge-base lacks it')
  ```

  The merge-base has it: `git restore --source=$(git merge-base HEAD origin/<base>) --staged --worktree -- <page>`. It
  lacks it: `git rm -qf --cached --ignore-unmatch -- <page> && rm -f -- <page>`, each in the shell form above. The
  restore stages itself; it removes a change and edits nothing. Each restored page is then written down in the
  ignored file `.cache/omc/restored`, so that the green commit names it after a restart too (the removal of a page git
  did not know leaves no trace in the repository):

  ```bash
  ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && mkdir -p .cache/omc && printf '%s\n' '<page>' >> .cache/omc/restored)
  ```

  Wanted: back to `harden`; not wanted, or left open: this step again.
- **A `decisions check` line of a rebase kind** (`id-on-main`, `duplicate-id`, `trimmed-on-main`): a rebase whose log
  step did not run. Not `fresh`, which skips on a rebased branch, but the log's steps here:

  ```bash
  ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git status --porcelain)
  ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions renumber && just decisions trim && just decisions check && git status --porcelain)
  ```

  The paths the second `git status` lists that the first did not are theirs (the log, each file whose references
  `renumber` rewrote), committed by name, `Decisions renumbered after the rebase`; none: no commit. A path already dirty
  before stays for the commit below. A refusal or a red `check`: to the owner, the lines quoted. Then this step again.
- **Any other line** (another kind of `decisions check`, a `links-check` line outside the record): taken as "From
  `/design` on" says, its options each with what it produces.

**Green** (`OK`). What the commit holds: the log and the question files, the record, and the pages a restore staged:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions list --branch; git status --porcelain -- <log> <questions> <record>; echo 'staged restores:'; git diff --cached --name-only -- <protected>…; echo 'restored:'; sort -u .cache/omc/restored 2>/dev/null)
```

With `paths.protected` empty no page can be restored: the `staged restores:` part is left out of the command (a
`git diff` with no pathspec would list every staged path). Nothing listed in the first three parts: no commit. Otherwise
one commit, by name, `<k>` the entries `just decisions list --branch` printed. The staged restores go only into the
commit's pathspec, never into `git add` (the restore staged them, and `git add` fails on a page it deleted); a staged
restore alone is a commit too. Every page of `restored:` is named in one more paragraph,
`-m "Restored from the merge-base: <page>, …"`, before the `Co-Authored-By` line; a page there that is not a staged
restore (HEAD and the merge-base both lack it: it was untracked, or only staged) is named in that paragraph only and
never put into the pathspec, since `git commit --` fails on a path git does not know. With `restored:` empty, that
paragraph is left out.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <listed path>… && git commit -m "Design: decisions gathered (<k>)" -m "Restored from the merge-base: <page>, …" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <listed path>… <staged restore>… && git show --stat --format='%h %s' HEAD)
```

Then `.cache/omc/restored` is removed: after the commit, or, with no commit, once a message has named the pages it
holds as restored. And, committed or not, the design settled:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && rm -f .cache/omc/restored && just omc settled --record)
```

A refusal (the tree has changes the record would not cover; it lists them): to the owner. Then on to `plan`.

## `plan` — write the plan from the record, in this session.

Skip when `just omc plan` finds one (exit 0): on to `done`.

The plan is written here, on the orchestrator model, from the committed record and this session's conversation (a
hand-off would lose them). This session reads `<root>/omc/terminals/write-plan/SKILL.md` with the Read tool and follows
it inline, `record: <record>`, `answer: none`, never as a subagent: `superpowers:writing-plans` and its plan rule (one
`/apply-decision` task per entry in id order, the links task, then the feature's own tasks, each with its `Complexity:`
line), saved as `<date>-<slug>-plan.md` in `paths.plans` and committed by name. Writing the plan builds and tests
nothing. Its `OUTCOME` line is this step's own word:

- `written` (`path`, `tasks`): ✓ `just omc plan` prints that path; it does not: a hard stop. The tasks, one line each
  with its complexity and the main-session tasks named, are shown in the message; then on to `done`.
- `needs_user`: its doubt taken as "From `/design` on" says (`/answer-doubt` for the flow "a plan"), then the plan
  written again with `answer: <the answer>`.
- `failed`: to the owner, with its reason.

## `done` — hand the run on.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc enter --done && just omc handoff)
```

- `continue`: one line, "The design and the plan are committed; going on to `/implement`.", then `/implement`
  through the Skill tool, in this same turn. Nothing else follows here.
- `ask` (`ask_for_provider_handoff: true` in `omc/config.yaml`): stop, to the owner: "The design and the plan are
  committed; type `/implement`, in this session or a fresh one." Nothing follows.
- An `error:` (exit 2, the flag is not a boolean): to the owner, with the error.

## The loop

`harden` runs three passes at most per record, the impact reading's included: the pass count is the tool's, so a fourth
is never run, whether `consistency`'s way back to `harden`, a `PROBLEM` line of `integrity`, a ruling recorded through
`/record-decision` or a restart would send it there. Where the way back would be a fourth pass, the loop goes on to
`consistency` or, for a `PROBLEM` line of `integrity`, to the owner, as after their stop (below). `consistency` and the
rest of the loop have no bound: they are expected to converge. The owner may stop it at any round and call the design
settled; then on to `integrity`, which writes `just omc settled --record` once it is green. Their stop is not kept in
the session's memory: it is entering at `integrity`. In this session `/design` goes on there at once; after a restart
before `settled --record` they type `/design integrity`, and the message that offers them the stop says so ("on a
restart, type `/design integrity`"), so that no restart runs `harden` and `consistency` again or asks a closed question
again. After their stop no step goes back to `harden`: a line `integrity` would send there is put to them instead, and
one they leave standing is named in the commit's message (one more paragraph,
`-m "Left standing by the owner: <line>"`), the commit and `settled --record` then as on green.

## Never

- Never a build, a test or a gate: no `/check`, `/build`, `/verify`, no `just omc gate run`, in any step or rebase.
- Never edit a protected document (a file matched by `paths.protected`) or code. The one exception, `integrity`'s
  restore of a stray edit, removes a change and edits nothing; never a page restored whose diff no message has shown.
- Never write the log but through `just decisions` and `/record-decision`; never record a decision but the owner's
  ruling, the agreement of `/answer-doubt`'s two answers (`Automated: true`) or its pick acted on although they
  disagreed (`Automated: disagreed`).
- Never put a question to the owner but one "From `/design` on" sends to them.
- Never apply an entry: that is the plan's.
- Never `git add -A` or `git add .`.
