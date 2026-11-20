---
name: audit
description: "The pipeline's push gate, entered by /implement or typed: squash and rebase onto the base branch, the three reviews, verify and the deferred questions, the owner's screenshot review, the description, the push. /audit <step-id> enters at that step."
---

# audit

The push gate of the `omc/` pipeline, in the owner's session (named so because a harness's built-in review command would
shadow one named "review"): from the implemented branch to one described commit pushed. It squashes and rebases the
branch onto `<base>` and reads what `<base>` brought, runs the three reviews and carries their findings through, builds and
verifies, takes the owner through every changed screenshot (`paths.screenshots` of `omc/config.yaml`; none configured,
nothing to take them through), writes the description into the commit and pushes. A rebase happens here and in
`/design`'s `fresh` only; ▣ verify runs here only, in `verify`. The log (`paths.decision_log`), the entry and the
question file are `omc/tools/decisions/FORMAT.md`.

**Where you are.** There is no run file. A skill started again, after a compaction or in a fresh session, begins at its
first step, and every step that is done skips itself on its tool's answer; "done" is read from the repository or a
record a tool wrote, never from what the session remembers, and whatever the owner decides that a restart must keep is
written to a file under `.cache/omc/`. Whatever the step entered, `just omc enter audit` runs first (it writes
`.cache/omc/current`, which puts this skill back into a compacted session). `/audit <step-id>` enters at that step;
`/audit` alone, or with anything that is not one of its step ids, begins at `rebase`. The branch stays one commit over
`<base>` from the squash in `rebase` to the push: every later change is amended into it.

**Terminals and tools.** ▣ (a terminal) and ✓ (a tool check). A terminal is run as: `just omc models <role>` (the role
is written at each call), then one fresh agent, `subagent_type: general-purpose`, with that model and effort where the
harness takes them (an empty model: the session's own, said in one line; an empty effort: the harness's default), its
prompt exactly `Read <root>/omc/terminals/<name>/SKILL.md and follow it. Root: <root>.` and then the inputs its step
names, one per line; `<root>` is the absolute path `git rev-parse --show-toplevel` prints. Its last line is
`OUTCOME {"outcome": "<word>", …}`: the step reads the word and the fields it names; the report above the line is prose
for this session, never parsed. Every terminal may also return `needs_user` (`question`, `options`, `picked`: "A
ruling", below) and `failed` (`reason`: told to the owner, who says whether it runs again); an agent that ends without
an `OUTCOME` line has failed. **Checked, not believed:** a terminal's word that a tool contradicts is a hard stop to the
owner (both answers shown, nothing goes on until they rule); an outcome no tool checks is taken as reported, and the
message says so. One terminal at a time: never a terminal beside another, nor a command of this session's while one
builds or tests (one build at a time on this machine).

**A ruling.** On `needs_user`, two kinds. A design doubt (a question whose answer would change a rule or a protected
document; ▣ task's report holds it as a `DOUBT` block) goes through `/answer-doubt` ("Talking to the owner"). Any other
question (a dirty path the terminal did not write, a run the gate did not start holding what the gate needs, a
conflicted file of the rebase) is asked of the owner directly, each option with what it produces, its `picked` as the
recommended one. Then a terminal that takes an `answer` (▣ rebase, ▣ task) is run again with it, its
`answer: <the answer>` input line; ▣ check, ▣ build and ▣ verify take none ("A gate's answers", below).

**Talking to the owner.** The run is autonomous from `/design` on (`omc/pipeline/design/SKILL.md` › "From `/design` on,
no question blocks the run") until they are here anyway: the deferred questions in `verify`, their screenshot review in
`push`. Every stop, every question that is not a design doubt and has a solid reason to block the run, the findings and
the screenshots are put to them in the conversation, one at a time; a question no protected document would change is
decided here, from the record, the plan and the code, and the message says how. A design doubt (the impact reading's
conflicts in `rebase` included) goes through `/answer-doubt` for the flow "an audit": both answers agree, the ruling is
recorded at once through `/record-decision` with `Automated: true` and acted on; they disagree, the question stays open
in the run's question file and the run goes on around it; only a disagreement that blocks the run, with a solid reason,
goes to them at once. The open ones are posed in `verify` (▣ verify's `integrity` outcome, `/review-decisions` inline,
its `/pose-questions`), before their screenshot review, and not before: a `/review-decisions` inline before `verify`
skips its pose ("`/review-decisions` inline", below). A ruling they give that changes a rule or a protected document is
recorded through `/record-decision` at once. Every message opens with the skill and step and its place,
`/audit › review (step 2 of 5)`, and progress as done of total (`finding 3 of 7`, `shot 2 of 5`). Every option shows
what it concretely produces, never a bare label, with the recommended one named; a long message that asks questions ends
with every question repeated as a numbered list, one line each with the recommended default. Their vocabulary: "the
log", "an entry", "recorded", "applied", "the protected documents", "the merge-base", "a question file", "the record",
"the plan", "in implementation"; no coined compressions.

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; a value a command printed (`<record>`, `<plan>`, `<merge-base>`, a path)
is written out in the next one; so are the configured paths, read from `omc/config.yaml`: `<log>` is
`paths.decision_log`, `<questions>` is `paths.questions` (a folder, ending with `/`), `<shots>…` are the globs of
`paths.screenshots` and `<baselines>…` those of `paths.baselines`, each glob written as a `':(glob)<glob>'` pathspec.
The log is written only through `just decisions` and `/record-decision`. A commit stages its paths by name,
`git add -- <path>…`, never `git add -A` or `git add .`; a new commit's message ends with
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

**The record and the plan.** `<record>` is the path `just omc record` prints (the `*-design.md` of `paths.specs` the
branch added and committed since the merge-base); more than one: the one with the branch's slug, else the owner says
which. `<plan>` is the path `just omc plan` prints, the plan ▣ task reads.

**The entry**, whatever step was entered (`/audit`, `/audit review`, …), runs first. A paused rebase first, since it
leaves `HEAD` on `<base>`'s tip with the branch's commit not replayed, and `just omc record` would find nothing:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc enter audit; { [ -e "$(git rev-parse --git-path rebase-merge)" ] || [ -e "$(git rev-parse --git-path rebase-apply)" ]; } && echo 'rebase paused' || echo 'no rebase')
```

`rebase paused` (an earlier session ended at a stop): `rebase` item 4 (▣ rebase) at once, before the record and the
clean tree, which a paused rebase would meet; once ▣ rebase is done and checked, the entry again (it then reads
`<record>` and `<plan>`), and on with `rebase` item 5. `no rebase`:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc record; just omc plan)
```

✓ `just omc record` prints `<record>` (exit 0); `no record committed on this branch` (exit 1): stop, to the owner: "No
design record is committed on this branch; run `/design` and `/implement` first." An `error:` (exit 2, no
`origin/<base>`): to the owner, with the error. `just omc plan` prints `<plan>`. Then the step entered, or `rebase`
item 5 when the entry runs again after a paused rebase (the impact reading, the check and `impact --done` come
first, whatever step was entered).

**The clean tree**, before every ▣ rebase, ▣ task, ▣ check, ▣ build, ▣ verify and ▣ describe, every
`/review-decisions` inline and every `just omc reviewed --record`: a run started on a dirty tree never holds, and the
rebase tool refuses one.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git status --porcelain --untracked-files=all; echo 'question files:'; for f in <questions>*.md; do head -1 "$f" | grep -q '^# Questions: ' && echo "$f"; done)
```

1. **The log and the question files** among the dirty paths (`<log>`, entries `/record-decision` wrote; a file whose
   first line starts `# Questions: `, the second part's list, which `/answer-doubt` writes and commits nothing) are
   amended into the branch's commit, by name (before the squash, into its last commit, which the squash folds with the
   rest):

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <path>… && git commit --amend --no-edit -- <path>… && git show --stat --format='%h %s' HEAD)
   ```

2. **The shots and the baselines** an earlier ▣ verify left uncommitted (paths `paths.screenshots` and `paths.baselines`
   match; both lists empty, this item skips itself) are restored from `HEAD` without asking in `verify` (the next
   ▣ verify writes them all again) and in `review` once ▣ screens-judge has judged them and each of its findings on them
   has its fix or its ruling (its findings keep them named). In `push` changed shots in the tree are shots nobody
   judged: back to `review` (▣ screens-judge judges them there), never restored in `push`; a baseline left dirty there,
   with no changed shot, is restored from `HEAD` without asking (a pass and a review both hold over it, so nothing else
   would clean it, and back to `review` would loop). Anywhere else they go to the owner with item 3, the restore
   recommended:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git diff --name-only -z HEAD -- <shots>… <baselines>… | xargs -0r git restore --source=HEAD --staged --worktree -- && git clean -fdq -- <shots>… <baselines>… && git status --porcelain)
   ```

3. **Any other dirty path** goes to the owner, the options: commit those paths by name into the branch's commit, as in
   item 1; set them aside in a temporary commit on a branch they name (never a bare `git stash`), to bring back later
   with `git checkout <name> -- <path>…`; a name a branch already has (`taken` below) is asked again, never reused:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git rev-parse -q --verify refs/heads/<name> >/dev/null && echo taken || echo free)
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <path>… && git commit -m "Set aside: <name>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <path>… && git branch <name> && git reset --keep HEAD~1 && git status --porcelain)
   ```

   or leave the step for now, which stops `/audit` here until they have committed or discarded them.

**One commit again.** `/review-decisions` commits each entry and each part of its follow-through on its own; after it
(or whenever `just omc git one-commit` counts more than one on a rebased branch) its commits are folded into the
branch's one commit, which keeps its message. The tree does not change, so a pass or a review that held still holds:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git reset --soft $(git rev-list --reverse $(git merge-base HEAD origin/<base>)..HEAD | head -1) && git commit --amend --no-edit -q && just omc git one-commit)
```

**A fix** (a finding of the reviews, a lag of the impact reading, a comment, the owner's word on a shot) is ▣ task,
role `orchestrator`, after the clean tree:

```text
plan: <plan>
finding: <the finding exactly as its report printed it, its block whole>
answer: none
commits: amend
```

- `done` (`commits`): ✓ `just omc git one-commit` holds and `git status --porcelain` lists nothing but the log and
  the question files; otherwise a hard stop.
- `needs_user` with a `DOUBT` block: `/answer-doubt` inline, through the Skill tool, for the flow "an audit" (its
  input: the question; where, `audit, <step>` and the block's `where`; the passages its `read` names). Its one-line
  report decides the `answer`: `subagent agree` (acted on), the picked answer; `subagent disagree` (collected),
  `open: Q<k> of <question file> waits for the owner; go on around it`; `settled from the docs` or `not a doubt`, the
  answer it gives; `merged into Q<k>`, as that question's `**Acted on.**` line stands. Then ▣ task again with that
  `answer`.
- `needs_user` without one (a dirty path, a run holding what the gate needs): asked of the owner directly; their answer
  goes back to ▣ task as its `answer`.
- `failed`: to the owner, with its reason, who says whether it runs again.

**`/review-decisions` inline**, through the Skill tool, after the clean tree, for the rulings recorded in this run and
the questions collected in it (`just decisions pending` prints one `PENDING:` line per recorded entry not applied,
`PENDING: decision <n> recorded, not applied: …`, and per open question, `PENDING: <question file>:<line>: … is open`).
**Before `verify`** (from `rebase` item 5 and `review` item 5) it is sent only for recorded entries, and it skips its
step 2, the pose, as it does when run from `/implement` (its deferred run, the caller saying `deferred`): the open
questions stay in their question file for `verify`, where the owner is anyway; open questions alone send no work there,
and the message says they wait for `verify`. **From `verify` on** (▣ verify's `integrity` outcome, `push` items 1 and 3)
and as the option the owner takes in "A gate's answers", it runs whole, its step 2 posing them. It runs inside `/audit`:
its follow-through ends at a green `/check`, never `/verify`, and its red check is fixed under this skill's gate:
▣ check as in "A gate", `why: the follow-through of the decisions`, its `failed` to the owner with the skip as their way
past. Its report is shown to the owner; then "One commit again".

**A gate** is ▣ check, ▣ build or ▣ verify, role `orchestrator`, after the clean tree, with `commits: amend`.

- `failed` (`summary`): the gate is still red at its limits; to the owner, with the summary, the options being the gate
  once more, `/audit` stopped here, or their skip of it. A skip of `check` or `verify` is written on their word only,
  then checked; it prints `skipped by the owner at <head>`, and a refusal (exit 2, the tree has changes the skip would
  not cover) goes to them with the paths:

  ```bash
  ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc gate skip <check|verify> && just omc gate passed <check|verify>)
  ```

  A skip of `build` is said in the conversation only (no tool asks about it later; a restart builds again).
- **A gate's answers.** Its `needs_user` takes no `answer`: this session acts on it itself, then the clean tree and the
  gate again with no answer line. A run holding what the gate needs, or a path it did not write: asked of the owner
  directly, each option with what it produces, and done on their word only: the run waited for or stopped; the named
  paths committed by name into the branch's commit or restored from `HEAD` (`git restore --staged --worktree -- <path>`,
  an untracked one removed). A fix that needs a protected document or a ruling: a design doubt, `/answer-doubt` as in "A
  fix"; an answer to act on is carried into the code by "A fix" (`finding:` the gate's question, `answer:` the answer),
  then the gate again. A collected one (`subagent disagree`) is never followed by the gate again, which would meet the
  same doubt: it goes to the owner as the gate's `failed`, the question quoted, the options being `/review-decisions`
  inline now (its `/pose-questions` takes the question to them), then the gate; their skip of the gate (written and
  checked as under `failed`, the question left open for `/review-decisions`); or `/audit` stopped here.

## `rebase` — squash and rebase the branch onto `<base>`.

1. **A rebase paused**: the entry (above) has sent it to item 4 already, and after it, with `<record>` and `<plan>`
   read again, to item 5.
2. **Is it done:**

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc git one-commit; just omc git rebased-on; just omc gate passed check; just omc impact; echo "impact: exit $?")
   ```

   `1 commits over the merge-base`, `rebased on origin/<base>`, `passed:` (or `skipped by the owner`) and
   `impact: exit 1` (no impact pending; the rebase terminal's `current` says nothing of one): the rest is done, on to
   `review`. Otherwise item 3. An `error:` (the fetch failed): to the owner, with the error.
3. **The clean tree** (above), then ✓ `just omc git clean`: `clean`, item 4; its lines are paths that go to the owner,
   as the clean tree's item 3 says.
4. **▣ rebase**, role `orchestrator`:

   ```text
   squash: yes
   phase: audit
   answer: none
   ```

   It squashes the branch into one commit, rebases it onto `origin/<base>`, settles a conflict of the log at each stop
   by `just decisions resolve`, then runs `renumber`, `trim` and the log's `check`, and amends what they changed.
   - `rebased` or `current`: ✓ `just omc git one-commit` and `just omc git rebased-on`; either false: a hard stop.
     Then item 5, whatever the word.
   - `needs_user`: a ruling. An entry `resolve` refused, or two sides whose intents exclude each other (the terminal
     merges every other conflicted file itself, both sides kept), is the owner's, put to them as that one question,
     never with an option to drop a side, merge by hand or abort: their ruled option goes back to ▣ rebase as its
     `answer`, and the terminal applies it and continues the paused rebase (never `git rebase --abort` or `--skip` by
     this session; an abort is the owner's own command, when an option they take says so). Uncommitted paths: with no
     rebase paused (the test of "The entry"), the clean tree's item 3, then ▣ rebase again with `answer: none`; while a
     rebase is paused, never an amend, a commit, a restore or a `reset --keep` by this session: the paths go to the
     owner only, and are committed or restored only once the rebase is done. A refused or red log step (`renumber`,
     `trim`, `check`): to the owner, the lines quoted; a bad base is fixed, never worked around. The question of a
     rebase the tool did not start (no mark) carries its literal shas: the option `old_base <sha>, new_base <sha>` is
     item 5 on those two shas, with no second rebase; `read no impact` is item 6.
   - `failed`: to the owner, with its reason.
5. **The impact reading.** The old merge-base is the mark (`just omc impact` exits 0 and prints it), or the `old_base`
   the owner took in item 4; none: item 6. ▣ impact, role `orchestrator`:

   ```text
   old_base: <the old merge-base>
   new_base: <git merge-base HEAD origin/<base>, or the new_base the owner took in item 4>
   phase: audit
   ```

   - `none`: item 6.
   - `found` (`lags`, `conflicts`), taken as reported. Before any is asked, the branch's entries (`just decisions list`,
     `just decisions show <n>`): a block an entry already rules (recorded at this reading before a restart, its
     `Context` naming `<base>`'s side of it) is named with that entry and not taken again. First each `CONFLICT` block,
     one at a time (`conflict 1 of 2`), taken as "Talking to the owner" says for a design doubt, its pick the answer
     weighed first; a ruling is recorded through `/record-decision` (an entry that replaces one of the branch's says
     `replaces decision <n>` in its `Context`). Then each `LAG` block (`lag 1 of 3`): one in code is followed by "A
     fix", the block as its `finding`; one that needs a protected document, or an entry of the branch, to change is a
     design doubt taken the same way, each option with what following it would change. Then ✓ `just decisions pending`:
     a `PENDING: decision <n> recorded, not applied` line (the rulings just recorded) → "`/review-decisions` inline",
     its pose skipped; a `PENDING: … is open` line (a question a fix collected) waits for `verify`.
   - `failed`: to the owner, with its reason; the mark stays.
6. **The check**, unless `just omc gate passed check` holds: ▣ check as in "A gate", `why: after the rebase onto <base>`.
   - `passed` (`attempts`): ✓ `just omc gate passed check`; `not passed`: a hard stop.
7. **The mark removed**, once the reading's conflicts are ruled and its lags handled, and also when no ▣ impact ran but
   a mark is there, or it would stay and this step would never skip again:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc impact --done)
   ```

   Then on to `review`.

## `review` — run the three reviews and carry their findings through.

Skip when `just omc reviewed` holds (`reviewed at <head>`): on to `verify`.

1. **The three reviews**, one after another, each role `orchestrator` and `record: <record>`: ▣ conformance (the record
   against the code, and every decision of the branch carried into the protected documents and the code),
   ▣ screens-judge (every changed shot, committed or regenerated, against the entry, record section or commit that
   explains it; it amends the explained and cosmetic ones into the one commit and leaves the broken and unexplained in
   the tree; with `paths.screenshots` empty it judges nothing and returns `clean`), ▣ architecture (the branch's code
   against the project's architecture documents and the code `<base>` brought). Before ▣ screens-judge nothing is staged
   (it amends).
   - `clean` (its Minor findings listed) or `findings` (`critical`, `important`, `minor`, and screens-judge's `judged`),
     taken as reported: each `FINDING` block is kept for item 2. After ▣ screens-judge, ✓ `just omc git one-commit`;
     false: a hard stop.
   - `failed`: to the owner, with its reason, who says whether it runs again.
2. **The findings**, all three's, shown to the owner whole: the counts per review, then every block, Critical first.
   Each is routed by its `fix` line, one at a time (`finding 3 of 7`); the routes are settled here, and the fixes they
   lead to run in item 3, after the shots' restore:
   - `code`: "A fix", the block as its `finding`.
   - `record` (the record lags behind code that is right): this session amends the section the finding names (the record
     is no protected document), amended into the branch's commit by name,
     `git add -- <record> && git commit --amend --no-edit -- <record>`; the amendment is shown to the owner.
   - `protected document` or `ruling`: never fixed by editing a protected document. `/answer-doubt` inline for the flow
     "an audit" (its input: the finding's `what`; where, `audit, review, <the review>` and its `where`; the passages its
     `checked against` names). `subagent agree`: acted on in the code by "A fix" with that `answer`, never in the
     document, which waits for the entry; `subagent disagree`: collected, the work goes on around it;
     `settled from the docs`: that answer, acted on the same way; `not a doubt` (no rule and no protected document
     changes, as the record against the code): decided by this session as the record and the code lead (the message says
     how), carried out by "A fix" or the record's amendment. The document itself changes only through the entry recorded
     for it: an agreeing ruling, recorded at once, is applied by `/review-decisions` in item 5; a collected question
     waits in the question file for `verify`, where `/review-decisions` poses it and applies the entry their ruling
     becomes.
   - **Minor** findings never stop the run: none is put to the owner. Each is routed the same way and fixed, unless
     this session judges the change not worth making (a drift of wording the record and the code both read well
     with), and every one, fixed or left standing, is named in the message and in the run's report. A finding left
     standing (a Minor this session leaves, a ruling the owner leaves as it is) is written to
     `.cache/omc/review/standing`, one line each, `<severity> <where>: <what>`, so that a restart, whose reviews return
     it again, names it as left standing instead of routing it again:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && mkdir -p .cache/omc/review && printf '%s\n' '<severity> <where>: <what>' >> .cache/omc/review/standing)
   ```

3. **The shots** ▣ screens-judge left in the tree (its broken and unexplained ones, each named in a finding) are
   restored from `HEAD` once each of their findings has its fix or its ruling, before the first ▣ task, ▣ check or
   `/review-decisions` of this step (the clean tree's item 2); the next ▣ verify regenerates them. The fixes of item 2
   then run one at a time.
4. **The new files `.gitnexusignore` should name:** for every file
   `git diff --name-only --diff-filter=A $(git merge-base HEAD origin/<base>)` lists, a new directory or file that is
   generated code, recorded data, a library or build output (judged by the file's content) gets a pattern in
   `.gitnexusignore`, under that kind's heading where the file has one, amended into the branch's one commit by name
   (`git add -- .gitnexusignore && git commit --amend --no-edit -- .gitnexusignore`). It never gates: no finding, no
   stop. ▣ conformance is not changed for it.
5. **The decisions:** ✓ `just decisions pending`; a `PENDING: decision <n> recorded, not applied` line (an entry
   recorded) → "`/review-decisions` inline", its pose skipped; a `PENDING: … is open` line (a question collected)
   waits for `verify`.
6. **The check**, unless `just omc gate passed check` holds (the shots' amend alone keeps it): ▣ check as in "A gate",
   `why: after the review's fixes`. `passed` (`attempts`): ✓ `just omc gate passed check`; `not passed`: a hard stop.
7. **The record of the review:** ✓ `just omc git one-commit`; more than one: "One commit again", then
   ✓ `just omc gate passed check` again (`not passed`: item 6); still more than one commit: a hard stop. Then the
   clean tree, and:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc reviewed --record && just omc reviewed)
   ```

   A refusal (exit 2, the tree has changes the review would not cover; it lists them): to the owner. The file
   `.cache/omc/review/standing` stays for the push's report. Then on to `verify`.

## `verify` — run the full verification and the owner's screenshot review.

Skip when `just omc gate passed verify` holds: on to `push`.

1. **▣ build** as in "A gate", `why: before verify`; `passed` (`attempts`) is taken as reported, and the message says
   so.
2. **▣ verify** as in "A gate" (its input `commits: amend` only). It regenerates the shots and never judges them.
   - `passed` (`attempts`, `shots_changed`): ✓ `just omc gate passed verify`; `not passed`: a hard stop. Then
     ✓ `just omc reviewed`: `not reviewed` (new or changed shots, `shots_changed` said in the message, or fixes that
     touched reviewed code): back to `review`. Otherwise on to `push`.
   - `integrity` (`problems`): the `PROBLEM` lines of the decisions' checks, which no gate fixes: shown to the owner,
     then "`/review-decisions` inline", then this step again. **The deferred questions are posed here**: ▣ verify's
     `just design-integrity-check` runs the `questions` check that `/design` and `/implement` left out, so a question
     left open in a question file from `/design` on comes back as a `questions` line, and `/review-decisions` (its step
     2, `/pose-questions`) takes it to the owner, who is here for their screenshot review anyway; this comes before that
     review (`push` item 1). A ruling of theirs that changes what was built (an entry recorded, a fix in the code) goes
     through `/review-decisions` there, its entries applied and its follow-through carried to a green `/check`, before
     the push; then this step again.
   - `failed`, `needs_user`: as in "A gate".

## `push` — write the description and push.

1. **The owner's final screenshot review.** With `paths.screenshots` empty there is none: said in the message, item 2.
   Otherwise every shot the branch changed, from the commit:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git merge-base HEAD origin/<base> && git diff --name-only $(git merge-base HEAD origin/<base>) HEAD -- <shots>…; echo 'shots tree:'; git ls-files -s -- <shots>… | git hash-object --stdin; cat .cache/omc/shots-accepted 2>/dev/null)
   ```

   The first line is `<merge-base>`. The two lines after `shots tree:` equal: they accepted these very shots before a
   restart, item 2. No shot listed: said in the message, item 2. Otherwise each shot `<shot>`, one at a time
   (`shot 2 of 5`), `<name>` its path with every `/` as `.`: its old picture (none for a new shot) and its new one (none
   for a deleted shot), out of Git LFS, into `.cache/shots/`:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && mkdir -p .cache/shots && for side in <merge-base>:base HEAD:head; do rev=${side%%:*}; f=.cache/shots/<name>.${side##*:}.png; if git cat-file -e "$rev:<shot>" 2>/dev/null; then { git cat-file --filters "$rev:<shot>" > "$f" && [ "$(head -c 4 "$f" | tail -c 3)" = PNG ] && echo "$f"; } || echo "error: $rev:<shot> not read out of Git LFS"; else echo "$rev: no picture"; fi; done)
   ```

   It prints each picture's path; `<rev>: no picture` for the old side of a new shot (no blob at the merge-base) or the
   new side of a deleted one; an `error:` line (the blob is there but its Git LFS object is missing, or git left the
   pointer unsmudged) is a hard stop to the owner, never taken for a new shot and never a shot shown without its
   picture. The pictures are read with the Read tool, and the message gives them the pictures' paths (to open them),
   what differs, and the entry that explains it: the shot's line in the commit's message (the last `Shots:` block
   ▣ screens-judge wrote, or the screenshots part of an earlier ▣ describe) and the entry it names
   (`just decisions show <n>`); a shot no line explains is said to be unexplained. They accept it or not. Every shot
   accepted: written down, so that a restart does not ask again:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && mkdir -p .cache/omc && git ls-files -s -- <shots>… | git hash-object --stdin > .cache/omc/shots-accepted)
   ```

   A shot they do not accept is a finding in their words: in the code, "A fix" with them as its `finding`; one that
   changes a protected document, their ruling recorded through `/record-decision` and "`/review-decisions` inline". Then
   back to `review`.
2. **▣ describe**, role `orchestrator`, after the clean tree:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && p=$(UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -c 'import yaml; print(yaml.safe_load(open("omc/config.yaml", encoding="utf-8"))["branch_prefix"])') && d=$(UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -c 'import yaml; print((yaml.safe_load(open("omc/config.yaml", encoding="utf-8")).get("paths") or {}).get("briefs", "tasks/"))') && b=$(git branch --show-current) && { test -f "$d${b#"$p"}.md" && echo "$d${b#"$p"}.md" || echo none; })
   ```

   ```text
   record: <record>
   brief: <the path printed, or none>
   ```

   It writes the PR description as the message of the one commit and deletes the brief (in `paths.briefs`) in it.
   `described` (`subject`): ✓ `git log -1 --format=%s` prints that subject; otherwise a hard stop. `failed`: to the
   owner.
3. **✓ The decisions:** `just design-integrity-check`. `OK`: item 4. Red: its lines shown to the owner, then
   "`/review-decisions` inline", then this item again (`just design-integrity-check` once more), until `OK`; the
   questions of item 4 then send the run where it has to go. Still red after a `/review-decisions` round that changed
   nothing (the same lines, no new commit), or on a question the owner leaves open: to the owner, with the lines, and
   `/audit` stops here; nothing is pushed. A `pre-push` hook may refuse the same push, but it is installed once per
   clone and may be missing, and a refused push is a worse place to learn it.
4. **✓ Asked again**, every one, from the tree of this moment ("Why the back-links are safe"):

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc git clean; just omc git one-commit; just omc git rebased-on; just omc reviewed; just omc gate passed verify)
   ```

   - `git clean` false: the clean tree (changed shots in it: back to `review`), then this item again.
   - `git one-commit` or `git rebased-on` false (`<base>` moved, or a commit was added): back to `rebase`.
   - `reviewed` false: back to `review`.
   - `gate passed verify` false: back to `verify`.
5. **The push.** The owner authorized it by typing `/design` (the run from there to the push) or `/audit`, and the
   message says so:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git push --force-with-lease -u origin "$(git branch --show-current)")
   ```

   A push the `pre-push` hook refuses: its output to the owner, never past it. A push that fails for any other reason
   (the remote unreachable or not a repository, the lease refused, the remote rejecting it) ends the step, and the
   run, `failed`: the message gives git's last lines and the command that failed, and asks nothing; no retry, never a
   change of the remote (`git remote set-url`, another remote), never a plain `--force`, and none of them offered as an
   option or a default: what follows is the owner's; `after` is not offered. A push that went through: the message,
   the branch and its commit, the description's subject, the gates as the tools answered (a skip said as the owner's,
   a build taken as reported), the findings left standing (`.cache/omc/review/standing`), and that the owner opens the
   PR: its title and text are the commit's message. Then on to `after`.

## `after` — offer what follows the push.

`just omc enter --done`, then, to the owner, three choices, each with what it produces:

- **Close the worktree**: `wt remove`, on their word, which removes this worktree and its branch's checkout (the branch
  stays on `origin`).
- **Address review comments**: each comment they bring is a fix ("A fix", the comment as its `finding`; one that would
  change a rule or a protected document through `/answer-doubt` as there), then `just omc enter audit` again (`--done`
  removed the marker `.cache/omc/current`, which a compacted session's resume reads), then back to `rebase`, and the
  gate is walked again from there.
- **Discuss**: nothing runs; the session stays open.

## Why the back-links are safe

`push` trusts nothing that came before it: it asks the five questions again, and "Is it done" answers each from the
tree of that moment. A rebase onto a moved `<base>` therefore walks the whole gate again, because what `<base>` brought can
change rulings and the design; a squash or an amended message walks nothing again.

## Never

- Never a push past a red question: `git clean`, `git one-commit`, `git rebased-on`, `reviewed`, `gate passed verify`
  and `just design-integrity-check` all hold, or the run goes where they send it; never `git push --no-verify`.
- Never a push but the one of `push` item 5; a failed push ends the run `failed`, never a question, a changed remote
  or a forced push.
- Never `git rebase --abort` or `git rebase --skip`: a paused rebase is ▣ rebase's to continue, or the owner's own
  command.
- Never edit a protected document (a file matched by `paths.protected`) but through `/apply-decision`
  (`/review-decisions`' step 3); never write the log but through `just decisions` and `/record-decision`; never record a
  decision but the owner's ruling or the agreement of `/answer-doubt`'s two answers (`Automated: true`).
- Never take a terminal's word where a tool answers: `just omc git …`, `just omc gate passed`, `just omc reviewed`,
  `just omc impact` and `just design-integrity-check` decide, the terminal's word only where none does.
- Never two terminals at once: one build at a time.
- Never write a skip but on the owner's word.
- Never a bare `git stash`.
- Never `git add -A` or `git add .`.
