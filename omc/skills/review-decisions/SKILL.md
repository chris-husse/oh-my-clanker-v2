---
name: review-decisions
description: "Carry every pending decision through: trim the log, pose the run's open questions, apply every recorded entry in id order (one fresh agent and one commit each), append the record's missing rows, then the follow-through (links, then code) until the gate is green: /check run from /implement or /audit, /verify run by hand. Runs at the end of /implement, from /audit's rebase (the impact reading) and its red decision checks, and on its own."
---

# Review the decisions

Every ruling the owner gives is recorded in the log (`paths.decision_log` of `omc/config.yaml`) the moment they give it
(`/record-decision`); every question the AI could not settle from the docs waits in the run's question file
(`/answer-doubt`). This skill carries all of it through: it trims what `<base>` already applied, takes the open questions
to the owner, applies every recorded entry to the protected documents, one fresh agent and one commit per entry, and
then walks the follow-through: the links follow the changed documents, the code follows the applied entries, until the
gate is green: `/check` run from `/implement` or `/audit`, `/verify` run by hand. The log, the entry and the question
file are in `omc/tools/decisions/FORMAT.md`.

**Who runs it.** It runs at the end of `/implement` (its step `decisions`); from `/audit`'s `rebase`, after the impact
reading (`omc/terminals/impact`); from a red `design-integrity-check` in `/audit`'s `verify` or before its push; and on
its own, `/review-decisions`. **Nothing runs it before implementation** (the brainstorm, `/design`, its `harden`, a
rebase while the branch changes nothing outside `paths.specs`, `paths.plans`, the log and `paths.questions`): there
nothing builds or tests, and the plan, not this skill, applies the record's entries. A run the owner asks for, typed or
handed over on their word, is theirs, whenever they ask. "Run from `/implement` or `/audit`" means any of those callers
but the owner's own `/review-decisions` (and `/review-design`'s hand-over on their word): the caller says so when it
sends work here, and a run the owner typed, or handed over on their word, is run by hand. Run from `/implement` or
`/audit` it is part of that skill's work: its authorization covers it, and its next step comes after this report.

**Deferred or whole.** Run from `/implement` (its step `decisions`) or from `/audit` before its `verify` (`rebase` item
5, `review` item 5), the run is **deferred**: it poses no question, since the run is autonomous from `/design` on and
the open questions wait for `/audit` › `verify`, where the owner is anyway. Step 2 is skipped, an apply agent's doubt
stays open in the question file (step 3), and the run ends with its deferred questions open (step 4 (d)). The caller
says `deferred` when it sends work here. Run from `/audit`'s `verify` on (▣ verify's `integrity` outcome, `push`, the
option the owner takes in its "A gate's answers"), or by hand, the run is **whole**: every step as written. Every skill
it calls (`/pose-questions`, `/apply-decision` in its agents, `/answer-doubt`, `/record-decision`, `/reconcile-links`)
ends with a report; that report ends the called skill, never this run. The agents it spawns are fresh,
`subagent_type: general-purpose`; inside `/design`, `/implement` or `/audit` they take the model and effort
`just omc models <role>` prints for their role, otherwise the harness default; this skill names no model.

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; the configured paths of `omc/config.yaml` are written out in each
command: `<log>` is `paths.decision_log`, `<questions>` and `<specs>` the folders `paths.questions` and `paths.specs`
(ending with `/`), `<baselines>…` the globs of `paths.baselines`, each as a `':(glob)<glob>'` pathspec. The log is
written only through `just decisions`; its subcommands are `add-decision`, `apply-decision`, `update`, `remove`, `show`,
`list`, `pending`, `guard`, `trim`, `resolve`, `renumber` and `check`, no other; this skill runs `trim`, `check`,
`pending`, `list`, `show` and `guard` itself, `renumber` only as `omc/terminals/rebase` › "4. The log after the rebase"
runs it, and the others only through `/record-decision` and `/apply-decision`. A commit stages its paths by name, never
`git add -A` or `git add .`, and its message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. One
build, test or render at a time on this machine: never a run beside another, and never a command of yours while an agent
of yours builds.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

**Talking to the owner.** They are asked through `/pose-questions` (step 2, and an apply agent's stop in step 3; neither
in a deferred run); this skill's own messages to them are rare: a stop it cannot settle, a CRITICAL question, and the
report. Every message to them opens with progress, done of total and what is ahead
(`Step 3 of 5: 2 of 4 entries applied; ahead: decisions 7 and 9, then the follow-through`). Every question shows what
each option concretely produces, never a bare label. A long message that asks questions ends with every question
repeated as a numbered list, same numbers, one line each with the recommended default. Inside this work an "ok" means
continue; never stop between entries to report. Use their vocabulary: "the log", "an entry", "recorded",
"applied", "the protected documents", "the merge-base", "a question file", "a review file", "the follow-through"; never
a coined compression.

## 0. The start

The steps run in order: 1 trim, 2 the questions, 3 apply every recorded entry, then "The record's rows", 4 the
follow-through until the gate is green (`/check` run from `/implement` or `/audit`, `/verify` run by hand), 5 the
report. First write down where the run starts and what the tree holds:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git rev-parse HEAD && git status --porcelain --untracked-files=all)
```

The HEAD printed is `<start>` for step 5. The tree may hold uncommitted changes to the log and to the question files
under `paths.questions` (a question file's first line starts `# Questions: `): the flow that called this skill leaves
them for this run's commits. Anything else uncommitted (code, a test, a protected document, a review file) stops the run
before step 1, with the list: `/apply-decision`'s gate would stop on it, and the calling flow commits its own work
first. A missing `origin/<base>` (`error: no origin/<base>: git fetch origin` from a `just decisions` command): run
`git fetch origin` and go on.

## 1. Trim

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions trim && just decisions check)
```

`trim` prints `<k> entries trimmed`: the entries applied at the merge-base, that is on `<base>`, are gone from the log.
`check` is the log's own check, not the gate `/check`; it prints `OK` or one problem per line. With `k` above 0, commit
the log alone (whole, with any entry recorded and not yet committed in it):

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <log> && git commit -m "Decisions trimmed: <k> applied on <base>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <log> && git show --stat --format='%h %s' HEAD)
```

With `k` 0, no commit.

After a rebase onto `<base>` the log's renumber, trim and check are `omc/terminals/rebase` › "4. The log after the
rebase"'s, and `just decisions resolve` at the rebase's stops is that terminal's too. A `check` problem `id-on-main`,
`duplicate-id` or `trimmed-on-main` here means a rebase whose log step did not run: read `omc/terminals/rebase` › "4.
The log after the rebase" and run its `renumber`, `trim` and `check` now, its commit as `squash: no` says, then go on.
Any other kind is the log's own (`omc/tools/decisions/FORMAT.md` names each kind). Never merge the log by hand, never
drop an entry to pass.

## 2. The questions

**Deferred: skipped.** No pose, no commit here; the open questions stay in their question files for `/audit` ›
`verify`, and the run goes on to step 3.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions pending; just decisions pending | sed -n 's/^PENDING: \([^:]*\.md\):[0-9][0-9]*: .*/\1/p' | sort -u)
```

`pending` prints `OK`, or one `PENDING:` line per recorded entry
(`PENDING: decision <n> recorded, not applied: <title>`) and per open question
(`PENDING: <questions><question file>.md:<line>: Q<k> <title> is open`), and exits 1 when it prints any. The second part
lists the question files that hold an open question. None: go on to step 3, no commit here.

Otherwise run `/pose-questions` with those files, through the Skill tool:
`/pose-questions <questions><question file>.md …`. It takes every open question to the owner, records every ruling
through `/record-decision` (the question's status becomes `decision <n>`), writes `answered` and the `**Differs.**`
lines, and commits nothing. When it ends, commit the question files and the log together (the log holds the entries just
recorded); this commit has to come before step 3, because `/apply-decision`'s gate stops on any uncommitted change but
the log and the question files, and the question files would otherwise stay uncommitted through the run:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git status --porcelain -- <log> <questions><question file>.md …)
```

When it lists nothing, no commit. Otherwise, the question files named by their file name without `<questions>` and
`.md`, and the entries `/pose-questions` reported as recorded:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <log> <questions><question file>.md … && git commit -m "Questions answered: <question file names> (decisions <n>…)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <log> <questions><question file>.md … && git show --stat --format='%h %s' HEAD)
```

`(decisions <n>…)` names every entry recorded, `42, 43`; when no entry was recorded (every question answered from the
docs, or left open), the subject ends at the file names.

A question the owner leaves open on purpose ("later") stays `open`: `just decisions pending` keeps naming it and
`verify`'s `design-integrity-check` stays red on it (`questions`). The run goes on with the rest, never comes back to
this step for it, and step 5 names it.

## 3. Apply every recorded entry

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions list)
```

Each line is `n  status  Automated: true|false  title`. The entries whose status is `recorded`, in id order, are the
total; each one gets one fresh agent, `subagent_type: general-purpose`, one at a time: start the next only when the
previous one has returned and its commit is checked. Its prompt is exactly the brief below, `<n>` the entry's id and
`<worktree root>` the absolute path `git rev-parse --show-toplevel` printed:

### Brief "apply"

```
Run /apply-decision <n> in <worktree root>; return the commit and the pages.
```

When it returns, check its commit and the entry:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git log -1 --format='%h %s' && just decisions show <n> | grep '^\*\*Status\.\*\*' && git status --porcelain --untracked-files=all)
```

The subject reads `Decision <n>: <title>`, the status `recorded <date> · applied <date>`, and the tree holds nothing
but the question files' changes (the log went with the commit). Then print, exactly:

```
decision <n> applied: <done> of <total>; left: <ids>
```

(`<ids>` the entries still to apply, comma-separated, or `none`).

**Where the owner's answer equals what the code already acted on**, that is its question reads `**Acted on.** yes` and
has no `**Differs.**` line, the entry reaches the pages only: the code and the tests already follow it. The checks of
step 4 still run over it.

**An agent that stops on a passage the decision does not settle** (`/apply-decision` step 2: the passage, file and
heading, the question as one sentence, its options with what each produces; the entry stays recorded and nothing was
edited):

1. Run `/answer-doubt` with that question, through the Skill tool: the flow is a review (collect), the passages the
   agent named. It settles it from the docs, or writes it to the run's question file.
2. When it wrote a question, **deferred**: no pose; the question stays open in the question file, committed with the log
   as in step 2's commit (`Questions collected: <question file names>`), the stopped entry stays recorded, and the run
   goes on with the next entry; `/audit` › `verify` poses it and applies the entry the ruling becomes. **Whole**: run
   `/pose-questions` over that question file at once. The ruling the owner gives is recorded as a new entry that
   replaces the stopped one (`/record-decision` step 1: its `Context` says `replaces decision <n>`, its `Decision` is
   the stopped entry's decision with the owner's answer in it); commit the question file and the log as in step 2. When
   `/answer-doubt` settled it from the docs instead, the same: a new entry whose `Decision` carries the reading the docs
   settle, replacing the stopped one; it keeps the stopped entry's `Automated` value (an owner's ruling stays `false`,
   `/record-decision` step 3), since its decision is still theirs.
3. The stopped entry runs again, in a fresh agent with the same brief: `/apply-decision` applies a replaced entry with
   nothing to change and commits the log alone. The new entry runs in its turn, in id order. Update the total and
   `<ids>` of the progress line.

**An agent that reports an `UNBACKED:` line for its own pages** (`/apply-decision` step 6: the entry is applied and
not committed), **or that stops on anything else** (its gate, a refused name, a guard error): the run stops and the
owner gets one question: what happened (the entry, the agent's report quoted, `git status --short`), the options and
what each produces, the recommended one, and the numbered list at the end. Never edit the log by hand to get past it.

**An agent that returns nothing**, or no commit and no stop: check the tree (`git status --porcelain`); when it is as
before the agent, one fresh agent with the same prompt. Failing again: a CRITICAL question (the entry, both returns,
the tree, the answer needed).

### The record's rows

On a branch with a record (the `*-design.md` of `paths.specs` added since the merge-base), after the last entry:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git diff --name-only --diff-filter=A $(git merge-base HEAD origin/<base>) -- '<specs>*-design.md'; just design-integrity-check --phase design)
```

The first part is the record (`<record>`); nothing listed: no record, nothing to do here. Each `PROBLEM: record:` line
the check prints is an entry of the branch without its row. For each, append its row to the record's section "Decisions
and the pages they change" (created when missing after the record's table of decisions taken, below its closing
paragraphs and before the next `##` heading), in the form of `omc/terminals/harden` › "3. The fold" item 2 (`/design`'s
`harden`), the planned pages now its real `Affected`, written plain as item 2 says (it is applied:
`just decisions show <n>`), without hardening and without touching any other section. Then commit the record alone:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <record> && git commit -m "Record: rows of the decisions applied on the branch" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <record> && git show --stat --format='%h %s' HEAD)
```

No `PROBLEM: record:` line: no commit. A `PROBLEM: decisions check:` line goes to step 1's paragraph on the rebase
kinds; the check's other lines are not this part's (step 4 and `verify` carry them).
This serves a ruling of the build, a rebase in implementation, and a branch designed before this change.

## 4. The follow-through

The code follows the applied entries, until the gate is green: run from `/implement` or `/audit` a green `/check`
after (c); run by hand a green `/verify` after (c). Run the parts in this order; `/check` after every part (d).

The entries a commit of this part names, `(decisions <n>…)`, are the applied entries that reach what it changes; the
entries applied on the branch, with the files each commit touched:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git log --name-only --format='%h %s' --grep='^Decision [0-9]' $(git merge-base HEAD origin/<base>)..HEAD)
```

### (a) The links

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just links-check)
```

It prints one `PROBLEM: <file>:<line>: <kind>: <detail>` per break, then `OK` or `<n> problems`.

- **A story's `stale-rule` or `orphan-rule`, a dead link, and any other problem**: `/reconcile-links`, through the
  Skill tool. Commit the files it lists in `.cache/reconcile-links/changed.txt`, by name:

  ```bash
  ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && test -s .cache/reconcile-links/changed.txt && xargs -d '\n' -a .cache/reconcile-links/changed.txt git add -- && git commit -m "Follow-through: links reconciled (decisions <n>…)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git show --stat --format='%h %s' HEAD)
  ```

  A problem it leaves on a protected document waiting for a decision went through `/answer-doubt`: an `Automated` entry
  when the docs settle it, else a question in the run's question file. Either way, go back at once: step 2 for a
  question written (deferred: it stands, nothing posed), step 3 for every entry recorded (each applied in its own
  agent), then (a) again from the top.

`just links-check` again until it prints `OK`; a round that only lists problems waiting for an entry or a question
is not a loop to repeat: it goes back to steps 2–3 first, as above.

### (b) The code follows the entries

Only after the links. Nothing to do here when no applied entry asks anything of the code and no `**Differs.**`
question names code: go on to (c) and (d). Otherwise the code, for the behaviour the applied entries ask for, the
rules they changed (the theme files, `paths.themes`) and the protected documents they reached the yardstick: the code
changes when it disagrees with them, a test only to say what its rule says.

Run from `/implement` or `/audit`, no `/verify`, whole or partial: `/check` is the check here.

A question on the way goes through `/answer-doubt`, flow test fixing: it acts on its picked answer when the docs settle
it or the agent agrees, and the question waits in the run's question file; part (d) takes it to the owner before the
run ends (deferred: it stands, for `/audit` › `verify`). Commit each piece of code work by its paths, with the question
file when it changed:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add -- <path> … && git commit -m "Follow-through: <what> (decisions <n>…)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <path> … && git show --stat --format='%h %s' HEAD)
```

### (c) The questions marked Differs

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && for f in <questions>*.md; do head -1 "$f" | grep -q '^# Questions: ' && grep -Hn -B8 '^\*\*Differs\.\*\*' "$f"; done)
```

Each `**Differs.**` line of a question whose entry this run applied says what the code and the tests did on the picked
answer the owner then ruled against. Revisit the code and the tests it names, to the entry's `Decision` and the rules
it changed: the code changes to the rule; a test changes only to say what its rule now says. Check and commit as in
(b).

### (d) The gates

`/check` after every part: run `/check` (through the Skill tool, inline; it runs the check gate in the background and
polled, fixes and reruns within its own bound, and ends with its report and `OUTCOME` line, which are the answer).
Before the run ends, `just decisions pending` must print `OK`, or name only what the owner left open on purpose (step
2's "later", or a conflict of the impact reading they left open, named by `/audit` when it sends the run here), which
step 5 names: a question the follow-through wrote (an `/answer-doubt` on the way) or an entry it recorded sends the run
back to step 2 and step 3 for them, then through (a)–(c) for what they changed. A question left open on purpose sends
the run back nowhere: it stays open, and `pending` keeps naming it. **Deferred**, every open question stands too (and an
entry stopped on one, step 3 item 2): a question sends the run back nowhere, only an entry recorded sends it to step 3;
`pending` may still name them, and step 5 names them as waiting for `/audit` › `verify`, where the run is whole.

**Run from `/implement` or `/audit`** the run ends here, at a green `/check` after (c): no `/verify`, whole or partial,
and no fix loop around one; `verify` is `/audit`'s `verify` step. A `/check` that ends `failed` ends this run with its
report: the calling skill's own gate (its ▣ check) takes the red check up.

**Run by hand**, at the end, after (c): run `/verify` (through the Skill tool, inline, `commits: new` on a branch not
yet squashed; it fixes while the run goes on, reruns what it fixed and gives its verdict from a fresh full run). Its
`integrity` outcome holds the log's checks, the `PROBLEM:` lines of its step `design-integrity-check`, which it never
fixes: by the check each line names, `pending` goes back to step 3, `questions` stays open (step 2), `record` to step
3's rows, `links-check` to `/reconcile-links` as in (a), `guard` to the entry that should name the page through the
owner's question of step 3; `decisions check` is the log's own (`omc/tools/decisions/FORMAT.md` names each kind), and
`id-on-main`, `duplicate-id` and `trimmed-on-main` mean a rebase whose log step did not run: `omc/terminals/rebase` ›
"4. The log after the rebase". Never an edit of the log; then `/verify` again. After its `passed`, the baseline advances
it committed (none to read when `paths.baselines` is empty),

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git log -p <start>..HEAD -- <baselines>…)
```

are analysed: do they match what was fixed; was anything raised that should not be.

**Red.** Run by hand, a `/verify` (or `/check`) that ends `failed` (its own bound reached) gets one CRITICAL question
naming the red stage, its failure, what the fixes tried and the answer needed, with the options and what each
produces, and the numbered list at the end; its `needs_user` is asked of the owner the same way. No later step runs
on a red gate. One build or test at a time; never a run beside another.

## 5. The report

Gathered by commands, never from memory:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git log --oneline <start>..HEAD && just decisions pending; git status --short)
```

- the entries applied, one line each: `decision <n>: <title>`;

- the commits, `git log --oneline <start>..HEAD`;
- the verdict the run ended on: `/check`'s run from `/implement` or `/audit`, the fresh `/verify`'s by hand;
- the questions left open (the `PENDING:` lines of open questions; in a deferred run, those that wait for `/audit` ›
  `verify`, with the entries stopped on them), and the gaps the owner left open.

When anything is asked, the report ends with every question repeated as a numbered list, same numbers, one line each
with the recommended default. Then the calling flow goes on with its next step.

## Never

- Never apply two entries in one agent.
- Never run two builds at once.
- Never edit a protected document but through `/apply-decision`.
- Never edit the log by hand; it is written only through `just decisions`.

- Never two apply agents at once.
- Never `git add -A` or `git add .`.
- Never take a red gate as green.
- Never run `/verify` when run from `/implement` or `/audit`; never run this skill before implementation; a run the
  owner asks for is theirs.
