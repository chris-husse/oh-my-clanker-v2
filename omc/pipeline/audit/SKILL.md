---
name: audit
description: "The pipeline's push gate, entered by /implement or typed: squash and rebase onto the base branch, the reviews, verify, the shots assessed and the owner's screenshot review, their rulings on the run's entries (each applied or deferred), the description, the push. /audit <step-id> enters at that step."
---

# audit

The push gate of the `omc/` pipeline, in the owner's session (named so because a harness's built-in review command would
shadow one named "review"): from the implemented branch to one described commit pushed. It squashes and rebases the
branch onto `<base>` and reads what `<base>` brought, runs the reviews and carries their findings through, builds
and verifies, has every changed shot (`paths.screenshots` of `omc/config.yaml`; none configured, nothing to assess)
given its verdict by ▣ screens-assess and puts them before the owner (the project's own screenshot review, when it has
one), takes their rulings on the run's entries, writes the description into the commit and pushes. A rebase happens
here and in `/design`'s `fresh` only; ▣ verify runs here only, in `verify`. The log (`paths.decision_log`), the entry,
its deferral and the question file are `omc/tools/decisions/FORMAT.md`; the shots' verdicts are ▣ screens-assess's.

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
builds or tests. One build, test or render at a time among this run's own agents and commands; never wait for another
worktree's or session's run (their load is reported, not waited out).

**A ruling.** On `needs_user`, two kinds. A design doubt (a question whose answer would change a rule or a protected
document; ▣ task's report holds it as a `DOUBT` block) goes through `/answer-doubt` ("Talking to the owner"). Any other
question (a dirty path the terminal did not write, a run the gate did not start holding what the gate needs, a
conflicted file of the rebase) is asked of the owner directly, each option with what it produces, its `picked` as the
recommended one. Then a terminal that takes an `answer` (▣ rebase, ▣ task) is run again with it, its
`answer: <the answer>` input line; ▣ check, ▣ build and ▣ verify take none ("A gate's answers", below).

**Talking to the owner.** The run is autonomous from `/design` on (`omc/pipeline/design/SKILL.md` › "From `/design` on,
no question blocks the run") until they are here anyway: their screenshot review in `screens`, then their rulings on
the run's entries in `push` item 1. Every stop ("A ruling", above) and the findings are put to them in the
conversation, one at a time, the screenshots in their screenshot review; any other question no protected document would
change is decided here, from the record, the plan and the code, and the message says how. A design doubt (the impact
reading's conflicts in `rebase` included) goes through `/answer-doubt` for the flow "an audit": both answers agree, the
ruling is recorded at once through `/record-decision` with `Automated: true` and acted on; they disagree, the run acts
on its pick all the same, recorded at once through `/record-decision --disagreed` (`Automated: disagreed`). The one
question to them before their screenshot review is `/answer-doubt`'s limit: the sixth disagreed entry not yet ruled
stops the run, and they are asked about all six, one at a time. The run's entries they did not rule, and the questions
still open, are posed in `push` item 1 (`/review-decisions` inline, `after review`, its `/pose-questions`), after
their screenshot review, and not before: a `/review-decisions` inline before that item skips its pose
("`/review-decisions` inline", below); in `screens` the only questions put to them are those of their own comments. A
ruling they give that changes a rule or a protected document is recorded through `/record-decision` at once; a ruling
made here may be deferred, on their word only (FORMAT.md › "The entry": recorded on `<base>` unapplied, for a later
branch), never an overruling entry. Every message opens with the skill and step and its place,
`/audit › review (step 2 of 6)`, and progress as done of total (`finding 3 of 7`, `round 1: comments 1 of 3 kinds`).
Every option shows what it concretely produces, never a bare label, with the recommended one named; a long message that
asks questions ends with every question repeated as a numbered list, one line each with the recommended default. Their
vocabulary: "the log", "an entry", "recorded", "applied", "deferred", "the protected documents", "the merge-base", "a
question file", "the record", "the plan", "in implementation"; no coined compressions.

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; a value a command printed (`<record>`, `<plan>`, `<merge-base>`, a path)
is written out in the next one; so are the configured paths, read from `omc/config.yaml`: `<log>` is
`paths.decision_log` (no log configured: `<log>` is dropped from the command, and a step about the log is skipped),
`<questions>` is `paths.questions` (a folder, ending with `/`), `<shots>…` are the globs of
`paths.screenshots` and `<baselines>…` those of `paths.baselines`, each glob written as a `':(glob)<glob>'` pathspec;
`<verdicts>` is `<questions>shots/` (the shots' verdicts, `<verdicts><slug>.yaml`, `<slug>` the branch without
`branch_prefix`) and `<screen-reviews>` is `<questions>screens/` (the owner's review rounds).
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

**The clean tree**, before every ▣ rebase, ▣ task, ▣ check, ▣ build, ▣ verify, ▣ screens-assess and ▣ describe, every
`/review-decisions` inline and every `just omc reviewed --record`: a run started on a dirty tree never holds, and the
rebase tool refuses one.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git status --porcelain --untracked-files=all; echo 'question files:'; for f in <questions>*.md; do head -1 "$f" | grep -q '^# Questions: ' && echo "$f"; done)
```

1. **The log and the question files** among the dirty paths (`<log>`, entries `/record-decision` wrote; a file whose
   first line starts `# Questions: `, the second part's list, which `/answer-doubt` writes and commits nothing), and the
   verdicts' yaml and the feedback file of a `screens` round a restart cut short (`<verdicts><slug>.yaml`,
   `<screen-reviews><date>-<slug>-<n>.md`), are amended into the branch's commit, by name (before the squash, into
   its last commit, which the squash folds with the rest):

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <path>… && git commit --amend --no-edit -- <path>… && git show --stat --format='%h %s' HEAD)
   ```

2. **The shots and the baselines** an earlier ▣ verify left uncommitted (paths `paths.screenshots` and `paths.baselines`
   match; both lists empty, this item skips itself) are restored from `HEAD` without asking in `verify` and in `review`
   (an earlier ▣ verify's, which the next one writes all again). In `screens` the shots are kept: they are its input,
   which ▣ screens-assess judges and the step amends into the branch's commit; a baseline left dirty there is restored
   from `HEAD` without asking. In `push` changed shots in the tree are shots no round reviewed: back to `screens`, never
   restored in `push`; a baseline left dirty there, with no changed shot, is restored from `HEAD` without asking (a pass
   and a review both hold over it, so nothing else would clean it, and going back would loop). Anywhere else they go to
   the owner with item 3, the restore recommended:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git diff --name-only -z HEAD -- <shots>… <baselines>… | xargs -0r git restore --source=HEAD --staged --worktree -- && git clean -fdq -- <shots>… <baselines>… && git status --porcelain)
   ```

   In `screens`, the baselines alone: the same command with `<baselines>…` as its only paths, both times.

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

**A fix** (a finding of the reviews, a lag of the impact reading, a comment, a "should have been right" of the owner's
screenshot review) is ▣ task,
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
  report decides the `answer`: `subagent agree` (acted on) or `subagent disagree` (acted on,
  `decision <n> recorded (disagreed)`), the picked answer;
  `asked at the limit: decision <n>`, the owner's ruling as entry <n> of the log records it (`just decisions show <n>`),
  never the picked answer; the earlier disagreed entries they overruled at that stop are undone by their new entries'
  follow-through, as for any entry; `collected`,
  `open: Q<k> of <question file> waits for the owner; go on around it`; `settled from the docs` or `not a doubt`, the
  answer it gives; `merged into Q<k>`, as that question's `**Acted on.**` line stands. Then ▣ task again with that
  `answer`.
- `needs_user` without one (a dirty path, a run holding what the gate needs): asked of the owner directly; their answer
  goes back to ▣ task as its `answer`.
- `failed`: to the owner, with its reason, who says whether it runs again.

**`/review-decisions` inline**, through the Skill tool, after the clean tree, for the rulings recorded in this run and
the questions collected in it (`just decisions pending` prints one `PENDING:` line per recorded entry not applied,
`PENDING: decision <n> recorded, not applied: …`, per entry not ruled, `PENDING: decision <n> disagreed, not ruled:
…`, and per open question, `PENDING: <question file>:<line>: … is open`; a deferred entry prints none and is applied on
a later branch). **Before `push` item 1** (from `rebase` item 5, `review` item 4, ▣ verify's `integrity` outcome and
`screens`) it is sent only for recorded entries, and it skips its step 2, the pose, as it does when run from
`/implement` (its deferred run, the caller saying `deferred`): the run's entries and the open questions wait for `push`
item 1, after the owner's screenshot review; a disagreed entry or an open question alone sends no work there, and the
message says it waits for that item. **From `push` item 1 on** (item 1 itself, the caller saying `after review`, and
item 3's red lines) and as the option the owner takes in "A gate's answers", it runs whole, its step 2 posing them. It
runs inside `/audit`: its follow-through ends at a green `/check`, never `/verify`, and its red check is fixed under
this skill's gate: ▣ check as in "A gate", `why: the follow-through of the decisions`, its `failed` to the owner with
the skip as their way past. Its report is shown to the owner; then "One commit again".

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
  then the gate again (a disagreement is acted on too, recorded `disagreed`). A collected one (`collected`) is never
  followed by the gate again, which would meet the same doubt: it goes to the owner as the gate's `failed`, the question
  quoted, the options being `/review-decisions` inline now (its `/pose-questions` takes the question to them), then the
  gate; their skip of the gate (written and checked as under `failed`, the question left open for
  `/review-decisions`); or `/audit` stopped here.

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
   - `found` (`lags`, `conflicts`), taken as reported. Before any is asked, the branch's entries (`just decisions list --branch`,
     `just decisions show <n>`): a block an entry already rules (recorded at this reading before a restart, its
     `Context` naming `<base>`'s side of it) is named with that entry and not taken again. First each `CONFLICT` block,
     one at a time (`conflict 1 of 2`), taken as "Talking to the owner" says for a design doubt, its pick the answer
     weighed first; a ruling is recorded through `/record-decision` (an entry that replaces one of the branch's says
     `replaces decision <n>` in its `Context`). Then each `LAG` block (`lag 1 of 3`): one in code is followed by "A
     fix", the block as its `finding`; one that needs a protected document, or an entry of the branch, to change is a
     design doubt taken the same way, each option with what following it would change. Then ✓ `just decisions pending`:
     a `PENDING: decision <n> recorded, not applied` line (the rulings just recorded) → "`/review-decisions` inline",
     its pose skipped; a `PENDING: … disagreed, not ruled` line or a `PENDING: … is open` line (a question a fix
     collected) waits for `push` item 1.
   - `failed`: to the owner, with its reason; the mark stays.
6. **The check**, unless `just omc gate passed check` holds: ▣ check as in "A gate", `why: after the rebase onto <base>`.
   - `passed` (`attempts`): ✓ `just omc gate passed check`; `not passed`: a hard stop.
7. **The mark removed**, once the reading's conflicts are ruled and its lags handled, and also when no ▣ impact ran but
   a mark is there, or it would stay and this step would never skip again:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc impact --done)
   ```

   Then on to `review`.

## `review` — run the reviews and carry their findings through.

Skip when `just omc reviewed` holds (`reviewed at <head>`): on to `verify`.

1. **The reviews**, one after another, each role `orchestrator` and `record: <record>`: ▣ conformance (the record
   against the code, and every decision of the branch carried into the protected documents and the code),
   ▣ architecture (the branch's code against the project's architecture documents and the code `<base>` brought). The
   shots are no review's: ▣ screens-assess judges them in `screens`, after `verify` has written them.
   - `clean` (its Minor findings listed) or `findings` (`critical`, `important`, `minor`), taken as reported: each
     `FINDING` block is kept for item 2.
   - `failed`: to the owner, with its reason, who says whether it runs again.
2. **The findings**, all the reviews', shown to the owner whole: the counts per review, then every block, Critical
   first. Each is routed by its `fix` line, one at a time (`finding 3 of 7`); the routes are settled here, and the
   fixes they lead to then run one at a time:
   - `code`: "A fix", the block as its `finding`.
   - `record` (the record lags behind code that is right): this session amends the section the finding names (the record
     is no protected document), amended into the branch's commit by name,
     `git add -- <record> && git commit --amend --no-edit -- <record>`; the amendment is shown to the owner.
   - `protected document` or `ruling`: never fixed by editing a protected document. `/answer-doubt` inline for the flow
     "an audit" (its input: the finding's `what`; where, `audit, review, <the review>` and its `where`; the passages its
     `checked against` names). `subagent agree`: acted on in the code by "A fix" with that `answer`, never in the
     document, which waits for the entry; `subagent disagree`: acted on the same way, its entry recorded `disagreed`;
     `collected`: the work goes on around it;
     `settled from the docs`: that answer, acted on the same way; `not a doubt` (no rule and no protected document
     changes, as the record against the code): decided by this session as the record and the code lead (the message says
     how), carried out by "A fix" or the record's amendment. The document itself changes only through the entry recorded
     for it: an agreeing ruling, recorded at once, is applied by `/review-decisions` in item 4, and so is a disagreed
     one; a disagreed entry and a collected question wait for `push` item 1, where `/review-decisions` poses them and
     applies the entry their ruling becomes.
   - **Minor** findings never stop the run: none is put to the owner. Each is routed the same way and fixed, unless
     this session judges the change not worth making (a drift of wording the record and the code both read well
     with), and every one, fixed or left standing, is named in the message and in the run's report. A finding left
     standing (a Minor this session leaves, a ruling the owner leaves as it is) is written to
     `.cache/omc/review/standing`, one line each, `<severity> <where>: <what>`, so that a restart, whose reviews return
     it again, names it as left standing instead of routing it again:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && mkdir -p .cache/omc/review && printf '%s\n' '<severity> <where>: <what>' >> .cache/omc/review/standing)
   ```

3. **The new files `.gitnexusignore` should name:** for every file
   `git diff --name-only --diff-filter=A $(git merge-base HEAD origin/<base>)` lists, a new directory or file that is
   generated code, recorded data, a library or build output (judged by the file's content) gets a pattern in
   `.gitnexusignore`, under that kind's heading where the file has one, amended into the branch's one commit by name
   (`git add -- .gitnexusignore && git commit --amend --no-edit -- .gitnexusignore`). It never gates: no finding, no
   stop. ▣ conformance is not changed for it.
4. **The decisions:** ✓ `just decisions pending`; a `PENDING: decision <n> recorded, not applied` line (an entry
   recorded) → "`/review-decisions` inline", its pose skipped; a `PENDING: … disagreed, not ruled` line or a
   `PENDING: … is open` line (a question collected) waits for `push` item 1.
5. **The check**, unless `just omc gate passed check` holds: ▣ check as in "A gate", `why: after the review's fixes`.
   `passed` (`attempts`): ✓ `just omc gate passed check`; `not passed`: a hard stop.
6. **The record of the review:** ✓ `just omc git one-commit`; more than one: "One commit again", then
   ✓ `just omc gate passed check` again (`not passed`: item 5); still more than one commit: a hard stop. Then the
   clean tree, and:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc reviewed --record && just omc reviewed)
   ```

   A refusal (exit 2, the tree has changes the review would not cover; it lists them): to the owner. The file
   `.cache/omc/review/standing` stays for the push's report. Then on to `verify`.

## `verify` — run the full verification.

Skip when `just omc gate passed verify` holds: on to `screens`.

1. **▣ build** as in "A gate", `why: before verify`; `passed` (`attempts`) is taken as reported, and the message says
   so.
2. **▣ verify** as in "A gate" (its input `commits: amend` only). It regenerates the shots and never judges them.
   - `passed` (`attempts`, `shots_changed`): ✓ `just omc gate passed verify`; `not passed`: a hard stop. Then
     ✓ `just omc reviewed`: `not reviewed` (fixes that touched reviewed code): back to `review`. Otherwise on to
     `screens`, `shots_changed` said in the message: changed shots no longer send the run back to `review`, since the
     review and the passed `verify` hold over the shots, the verdicts' yaml and the feedback file (`REVIEW_KEEP` and
     `GATE_KEEP`, `omc/tools/done.py`), and `screens` judges them.
   - `integrity` (`problems`): the `PROBLEM` lines of the decisions' checks, which no gate fixes: shown to the owner,
     then "`/review-decisions` inline", its pose skipped, then this step again. Nothing is posed here: ▣ verify runs
     `just design-integrity-check` with the deferral (`--defer-questions`, as `/implement` does), so an open question
     and an entry still `disagreed` are no `PROBLEM` line here; they wait for `push` item 1, after the owner's
     screenshot review.
   - `failed`, `needs_user`: as in "A gate".

## `screens` — the shots assessed, and the owner's screenshot review.

With `paths.screenshots` empty there is nothing to assess: said in the message, on to `push`. Skip when
✓ `just omc shots accepted` holds (`accepted`, exit 0: every shot that differs from the base has its current pair's row
in `<verdicts><slug>.yaml` `review: accepted`, and no shot differing holds too): on to `push`. A restart thus never
shows them a round they finished. `not accepted: <ids>` (exit 1): item 1. An `error:` (exit 2): to the owner, with the
error.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc shots accepted; echo "accepted: exit $?"; git merge-base HEAD origin/<base>)
```

The last line is `<merge-base>`.

1. **The clean tree** (above; the shots are kept here, the baselines restored), then **▣ screens-assess**, role
   `orchestrator`:

   ```text
   base: <merge-base>
   mode: changed
   ```

   - `done` (`unexpected`, `expected`, `judged`, `file`): its counts open the next message. The yaml and the changed
     shots are amended into the branch's one commit, by name, so that the reviewed pair is the committed one and
     `push`'s clean tree holds (`git add` of a removed shot stages its removal):

     ```bash
     ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <file> $(git status --porcelain -- <shots>… | sed 's/^...//') && { git diff --cached --quiet || git commit --amend --no-edit -q; } && just omc git one-commit && git status --porcelain)
     ```

     ✓ `just omc git one-commit` holds and the status lists nothing but the log and the question files; otherwise a
     hard stop. Then item 2.
   - `none`: no shot differs from the base, said in one line; the yaml it emptied, when the tree shows it changed,
     amended the same way; then ✓ `just omc shots accepted` (`accepted`; otherwise a hard stop) and on to `push`.
   - `failed`: to the owner, with its reason, who says whether it runs again.
2. **The round** (`round <n>`, one more than the files of `<screen-reviews>` for this branch). The project's own review,
   when it has one (`.claude/skills/review-screens/SKILL.md`), is read with the Read tool and followed in this session,
   its form "From `/audit`" (not through the Skill tool, which may not start it): it shows the round's pairs its own way
   and tells this session when the owner is done; while they review, this session ends its turn and waits for their
   answer, never polling or ending what the review serves while they are quiet or between turns. Without one, the round
   is held in the conversation: every row of the yaml whose `review` is not `accepted`, the `unexpected` bucket first,
   one at a time (`shot 2 of 3`), then the `expected` ones as one list, grouped by `group`; each with its two pictures
   (the base's and the current one, out of Git LFS into `.cache/shots/review/`, opened with the Read tool, their paths
   given to open them), its verdict, reason and cause. They accept each, or the whole expected list at once, or comment
   on it. Their answers are written to the yaml's `review` field (`accepted`; `commented (round <n>)`), and the round to
   `<screen-reviews><date>-<slug>-<n>.md` (each shot, its answer and their comment in their words). Either way, their
   comments are then analysed and carried: each clear layout change recorded at once through `/record-decision` (their
   ruling); each unclear or conflicting layout change and every change of what a screen does in the round's question
   file, posed by `/pose-questions` with that file only; each "should have been right" "A fix", the comment as its
   `finding`; then the apply-or-defer message of `/pose-questions` (each ruling of the round with the session's
   suggestion, apply or defer, confirmed or flipped by them in one answer; never an overruling entry), the deferred
   ones `just decisions defer --id <n>`, the applied ones through "`/review-decisions` inline", its pose skipped. The
   round's file, the yaml, the log and the question file are amended into the branch's one commit by name. Nothing of
   the run's own entries and open questions is posed before or in this step: the only questions put to them here are
   those of their own comments; the rest wait for `push` item 1.
3. **After the round:** ✓ `just omc git one-commit`; more than one: "One commit again". Then the clean tree, and
   ✓ `just omc reviewed`: `not reviewed` (a fix or an applied ruling changed what the reviews read, or the log moved):
   back to `review`, then `verify`, then this step again, whose next round shows only the pairs whose hash changed (a
   commented row whose comment is carried and whose picture did not change is `accepted (carried)`, written by the
   project's review, else by this session into the yaml, amended by name). `reviewed`:
   ✓ `just omc shots accepted`; `accepted` (a round with nothing to show or with no comment ends the review): on to
   `push`; `not accepted: <ids>`: item 1 again.

## `push` — the owner's rulings, the description and the push.

1. **The owner's rulings** on the run's entries they did not rule and the questions still open, after their screenshot
   review and before the description. Done before a restart when the log is the one they ruled:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git hash-object -- <log>; cat .cache/omc/entries-ruled 2>/dev/null; just decisions pending)
   ```

   The first two lines equal: they ruled this very log before a restart, item 2 (a question they left open on purpose
   stays open, for item 3). Otherwise, with no `PENDING: … disagreed, not ruled` or `PENDING: … is open` line and no
   entry of the run left `Automated: true` that `.cache/omc/entries-posed` does not hold (the list of
   `/review-decisions` step 2's second command, which leaves out every id posed to them: a confirmed `true` entry reads
   as an unconfirmed one, and one they were posed is never asked again): item 2.
   Otherwise, after the clean tree, "`/review-decisions` inline", the caller saying `after review`: its step 2
   (`/pose-questions`) takes them the run's entries (the `disagreed` ones one at a time, then the `Automated: true`
   ones five at a time, a skipped one confirmed; every id posed appended to `.cache/omc/entries-posed`), then every
   question still open; each entry they confirm is
   `just decisions confirm <n>`, each they overrule a new entry recorded through `/record-decision` and
   `just decisions overrule <n> --by <m>`, the new entry applied and its follow-through undoing the work to a green
   `/check`. After the rulings, its apply-or-defer message (`/pose-questions`, run from `/audit`): every ruling of
   this item that is a new entry, but an overruling one (always applied here: its follow-through undoes this branch's
   work), each with the session's suggestion, **apply** (the branch's gist needs it) or **defer** (unrelated, or a
   clear extension: recorded on `<base>` unapplied, for a later branch), confirmed or flipped by them in one answer; the
   deferred ones `just decisions defer --id <n>`, never on the session's word alone; the rest applied by its step 3.
   Then "One commit again", and the log they ruled written down, so that a restart does not ask again:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && mkdir -p .cache/omc && git hash-object -- <log> > .cache/omc/entries-ruled)
   ```

   - Nothing changed but the log and the question files (every entry confirmed or deferred, no answer that changes
     the work): item 2.
   - The work changed (an overrule's undo, an applied ruling, a fix): back to `verify`, whose ▣ verify regenerates
     the shots; `screens` then shows them only the pairs whose hash changed, and this item finds nothing left to rule.
   - A question they leave open on purpose: `/audit` stops at item 3, which stays red on it; nothing is pushed.
2. **▣ describe**, role `orchestrator`, after the clean tree:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && p=$(UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -c 'import yaml; print(yaml.safe_load(open("omc/config.yaml", encoding="utf-8"))["branch_prefix"])') && d=$(UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -c 'import yaml; print((yaml.safe_load(open("omc/config.yaml", encoding="utf-8")).get("paths") or {}).get("briefs", "tasks/"))') && b=$(git branch --show-current) && { test -f "$d${b#"$p"}.md" && echo "$d${b#"$p"}.md" || echo none; })
   ```

   ```text
   record: <record>
   brief: <the path printed, or none>
   ```

   It writes the PR description as the message of the one commit, with the changed shots and their verdicts from the
   yaml and the branch's deferred rulings, and deletes the brief (in `paths.briefs`) in it. `described` (`subject`):
   ✓ `git log -1 --format=%s` prints that subject; otherwise a hard stop. `failed`: to the owner.
3. **✓ The decisions:** `just design-integrity-check`. `OK`: item 4. Red: its lines shown to the owner; a `disagreed` or
   `questions` line (an entry not ruled, a question still open) sends the run to item 1, then this item again; any other
   line, "`/review-decisions` inline", then this item again (`just design-integrity-check` once more), until `OK`; the
   questions of item 4 then send the run where it has to go. Still red after a `/review-decisions` round that changed
   nothing (the same lines, no new commit), or on a question the owner leaves open: to the owner, with the lines, and
   `/audit` stops here; nothing is pushed. A `pre-push` hook may refuse the same push, but it is installed once per
   clone and may be missing, and a refused push is a worse place to learn it.
4. **✓ Asked again**, every one, from the tree of this moment ("Why the back-links are safe"):

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc git clean; just omc git one-commit; just omc git rebased-on; just omc reviewed; just omc gate passed verify; just omc shots accepted)
   ```

   - `git clean` false: the clean tree (changed shots in it: back to `screens`), then this item again.
   - `git one-commit` or `git rebased-on` false (`<base>` moved, or a commit was added): back to `rebase`.
   - `reviewed` false: back to `review`.
   - `gate passed verify` false: back to `verify`.
   - `shots accepted` false (`not accepted: <ids>`, a pair no round reviewed): back to `screens`.
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

`push` trusts nothing that came before it: it asks the six questions again, and "Is it done" answers each from the
tree of that moment. A rebase onto a moved `<base>` therefore walks the whole gate again, because what `<base>` brought can
change rulings and the design; a squash or an amended message walks nothing again.

## Never

- Never a push past a red question: `git clean`, `git one-commit`, `git rebased-on`, `reviewed`, `gate passed verify`,
  `shots accepted` and `just design-integrity-check` all hold, or the run goes where they send it; never
  `git push --no-verify`.
- Never a push but the one of `push` item 5; a failed push ends the run `failed`, never a question, a changed remote
  or a forced push.
- Never `git rebase --abort` or `git rebase --skip`: a paused rebase is ▣ rebase's to continue, or the owner's own
  command.
- Never edit a protected document (a file matched by `paths.protected`) but through `/apply-decision`
  (`/review-decisions`' step 3); never write the log but through `just decisions` and `/record-decision`; never record a
  decision but the owner's ruling, the agreement of `/answer-doubt`'s two answers (`Automated: true`) or its pick acted
  on although they disagreed (`Automated: disagreed`).
- Never pose the run's entries or its open questions before the owner's screenshot review is done (`push` item 1), but
  `/answer-doubt`'s limit; in `screens` only the questions of their own comments.
- Never defer a ruling the owner did not confirm deferred, nor an overruling entry; never end a review the owner is
  still in.
- Never take a terminal's word where a tool answers: `just omc git …`, `just omc gate passed`, `just omc reviewed`,
  `just omc shots accepted`, `just omc impact` and `just design-integrity-check` decide, the terminal's word only where
  none does.
- Never two terminals at once: one build at a time among this run's own.
- Never write a skip but on the owner's word.
- Never a bare `git stash`.
- Never `git add -A` or `git add .`.
