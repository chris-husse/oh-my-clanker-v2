---
name: answer-doubt
description: "Use whenever you have a design doubt, a question whose answer would change a rule or a protected document, in any flow (a brainstorm, /design, a plan, an implementation task, an audit, a test fix): first the gate (which page would change; none means it is not a doubt, ask or decide it yourself), then the docs. In the brainstorm a doubt that needs a ruling is asked in the conversation and recorded when the owner rules; from /design on (the autonomous run to the push) an independent agent answers it too and the question goes to the run's question file with your picked answer: both agreeing, the ruling is recorded at once (Automated) and acted on; a disagreement stays open for /audit's verify, or goes to the owner at once only when it blocks the run with a solid reason."
---

# Answer a doubt

The one way the AI handles a design doubt: a question about what the product does or what the docs say, one whose answer
would change a rule or a protected document (does an incident need a photo; which screen a refusal lands on). The AI
invokes it, in any flow (a brainstorm, `/design`, a plan, an implementation task, an audit, a test fix, the
follow-through of `/review-decisions`, `/review-design`), the moment such a doubt arises. It is not for the
conversation's own questions: the brainstorm's seed and scope, the owner's preferences, their environment and accounts,
fees and budgets, how a tool is proven or when a branch merges, a tool's internals, or anything a design record lists
under "decisions taken during brainstorm". Those the AI asks the owner directly in the conversation, one at a time, or
decides as a builder would (from `/design` on it decides them, from the record, the conversation and the code); they
never reach this skill. The owner's words: a question the existing docs answer without a ruling is not asked, that is
the answer right there, and no agent is needed; a ruling is a decision-log entry, and an entry exists only to change a
protected document, so a question that changes no page can never need one. In the brainstorm (`/brainstorm`, before
`/design`) the owner is in the conversation: a doubt that needs a ruling is asked there, now, and recorded through
`/record-decision` when they rule; nothing is written under `paths.questions` and no agent runs. From `/design` on (its
steps and the plan, `/implement`'s tasks, `/audit`, a test fix, the follow-through) the run is autonomous to the push
and they may be away: an agent is used only when the question looks like it needs a ruling. When the agent's answer
agrees with yours, that agreement rules it: the ruling is recorded at once through `/record-decision` with
`Automated: true` and acted on. When it disagrees, the question stays open in the run's question file and the run goes
on around it (it is deferred); the open questions are merged, then posed in batches and one by one in `/audit` ›
`verify`, before the push; only a disagreement that blocks the run, with a solid reason to, goes to them at once. Every
question is shown with the answer picked, even when uncertain. The question file's form is
`omc/tools/decisions/FORMAT.md` ("The question file").

**Shell.** Variables do not survive between commands: begin every command with `ROOT=$(git rev-parse --show-toplevel)`
and run it in a subshell, `(cd "$ROOT" && …)`; a path a command printed (the hidden folder) is written out in the next
one; so are the configured paths of `omc/config.yaml`: `<themes>…` the theme files `paths.themes` matches,
`<protected>…` the files `paths.protected` matches, `<questions>`, `<specs>` and `<plans>` the folders
`paths.questions`, `paths.specs` and `paths.plans` (each ending with `/`), `<prefix>` its `branch_prefix`. An empty list
leaves its read out. The only `just decisions` subcommands this skill runs are `list` and `show`.

**Talking to the owner.** In the brainstorm this skill asks them in the conversation (step 2). From `/design` on it asks
them only a disagreement that blocks the run, with a solid reason (step 6): every other question that needs a ruling
goes to the run's question file, ruled there by the agreement of the two answers or left open; `/pose-questions` takes
the open ones to them in `/audit` › `verify` (▣ verify's `integrity` outcome, step 2 of `/review-decisions`), the
agreeing ones in batches, the rest one by one. Either way write each question as they will read it: the concrete
situation, the options each with what it concretely produces, never a bare label, and the answer you picked with its
reason, even when you are unsure of it. Plain words in their vocabulary (the theme files' words).

## 1. Input

- **The question**, as it arose, in one or two sentences.
- **Where**: the flow, the task, the file and the symbol (`implement, task 4, app/incidents.py (record_incident)`).
- **The passages read** so far, each with file and line.
- **The flow**, which decides step 6: test fixing, implementation, audit, a brainstorm, `/design`, a plan, a review
  (`/review-design`); and whether it runs inside `/design`, `/implement` or `/audit` (the autonomous run) or outside
  them (the owner's own run of a skill).
- When the caller holds one: **the owner's answer on record** (an item they already answered in a review file). It is
  theirs, not yours: it goes to the agent as well, marked as the owner's.

## 2. (a) The gate, then the docs

**The gate, first, in every flow.** Name the protected document and the sentence the answer would change (a rule of the
theme files, `paths.themes`, or a file `paths.protected` matches; with both empty no answer changes one, and no question
is a doubt). A ruling is a decision-log entry, and an entry exists only to change such a page through `/apply-decision`;
a question that changes no page can never become one. None → stop: it is not a doubt for this skill. A fact of the
owner's environment, a preference, a process or proof question, a tool's internals: in the brainstorm ask it in the
conversation, or decide it yourself as a builder would; from `/design` on decide it yourself, from the record, the
conversation and the code. No agent, no question file, nothing recorded. Report
`not a doubt: <what it is>; asked in the conversation | decided: <answer>`.

**Where is the owner.** In the brainstorm (`/brainstorm`, before `/design`) they are in the conversation: after the docs
below, a doubt that needs a ruling is asked there, now, with the passages, the options each with what it produces, and
the answer you picked with its reason; when they rule, `/record-decision` records it on the spot. Steps 3 to 5 do not
run, nothing is written under `paths.questions`, no agent runs. From `/design` on (the plan included, whether `/design`
or `/implement` writes it), steps 3 to 6 run as written.

Read what the question touches, in this order:

- the theme files first: `grep -n '^#' <themes>…` for the subthemes, `grep -n 'R9.3-2' <themes>…` for a rule and the
  rules pointing at it (`grep -n 'See R9.3-2'`), `grep -n '<word>' <themes>…` for the words;
- the project's `AGENTS.md`;
- the protected documents: `grep -n '<word>' <protected>…`;
- the log's recorded entries: `ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions list)`, then
  `just decisions show <n>` for the ones on the topic. A recorded entry overrides the pages it names: its `Decision`
  holds even where a page does not say it yet.

Where they disagree, the rule wins and the page lags.

Then the materiality test, the owner's: "Only actual problems reach the owner: a user would experience
something wrong or contradictory; data, safety or rights could go wrong; or a builder would have to guess between two
behaviours that both look intended. Not material: wording unless two names would show the user an actual
inconsistency; technical internals left to the technical design; rare edge cases whose sensible answer is obvious;
definitions nobody would act on differently; anything a reasonable builder would simply get right."

**Settled by the docs, or not material**: that is the answer. Act on it (on the obvious answer, for a doubt that is not
material), write no question, record nothing, spawn no agent. One exception: a protected document found lagging a rule
this way becomes an `Automated` entry through `/record-decision --automated` (the rule quoted as the context, the page's
new reading as the decision, the rule and the page as `Affected`), so that `/apply-decision` carries the rule into the
page (an apply task of the plan, or `/review-decisions`). Never edit the page yourself. Report and stop:
`settled from the docs: <answer> (<file:line>)`, plus `decision <n> recorded (Automated)` when a lag was recorded.

## 3. (b) Needs a ruling: an open question that asks the same

Find the run's question file (step 5 says how) and read its open questions. One that asks the same thing (the same
passages, the same choice) takes this doubt: add this place to its `**Where.**` line (`; ` between places), and go to
step 6 with its `Picked` and `Subagent` (agree or disagree as written there); no second question, no second agent.
Otherwise go on.

## 4. (b) Needs a ruling: two answers

**The neutral question.** Write it down before anything else: the question in one sentence; the passages with file,
line and quote; the options, each with what it produces, in no ranked order, none marked recommended. Nothing else:
no reading of yours, no leaning, no "the docs seem to say".

**Your own answer, hidden.** Before the agent runs, write your picked answer in the agent's return form below (the
option, its scope and conditions, the passages that decide it, your confidence) to a hidden folder outside the
repository:

```bash
HIDDEN=$(mktemp -d /tmp/answer-doubt-XXXXXXXX); echo "$HIDDEN"
```

Write `<HIDDEN>/<ref>.md`, `<ref>` a short name of the doubt (`incident-photo`). The folder's path never appears in a
prompt; never show your answer to anyone before step 5, and never write or change it after reading the agent's.

**The independent answer.** One fresh agent, `subagent_type: general-purpose`, no inherited conversation; inside
`/design`, `/implement` or `/audit` it takes the model and effort `just omc models orchestrator` prints, otherwise the
harness default; this skill names no model. Its prompt is the brief below with the angle brackets filled from the
neutral question and the configured paths, and nothing else:

```
You answer one design question for this project independently, from the project's docs alone. Edit no file.

Question: <the question, one sentence>
Where it arose: <flow, task, file and symbol>
Passages: <file:line and the quote, one per line>
Options (in no order; none is recommended): <(1) … produces …; (2) … produces …; …>
<only when the caller holds one: The owner's answer on record, their own words: "<quote>" (<review file, item>)>

Read only the docs: the theme files <themes>… first (grep -n '^#' for the subthemes, grep -n for the rule
ids and the words), the project's AGENTS.md, the documents <protected>…, and the decision log's
recorded entries through `just decisions list` and `just decisions show <n>` (no other command but reading ones:
cat, grep, sed -n, ls). A recorded entry overrides the pages it names; where a page and a rule disagree, the rule
wins and the page lags. Never read <questions>, <specs>, <plans>, .superpowers/ or anything under /tmp/. If an
answer to this question by anyone else was given to you or you came across one, say so in your first line and give
no answer: the caller starts a fresh agent.

Answer with the option you would take, or your own formulation when none fits. Separate the choice from its limits
and conditions, so that the caller can compare substance, not option names. Your confidence alone never settles the
question; it is not a ruling.

Confidence: high when one answer follows from the docs and the recorded entries, no alternative is close and no
high-impact criterion applies; medium when you have a clear preference with a defensible alternative, or one
high-impact criterion applies; low when you have no preference, or the answer depends on facts outside the docs (the
owner's environment, a licence, a budget). High-impact criteria: a change to what a person sees or may do; to what
the product records (a stock figure, a record's history, a person's data); to the MVP's scope; to what the owner does by hand; a
legal, licensing or credential matter. A choice that contradicts a rule or an owner's recorded entry is medium at
most. When in doubt, the lower level.

Return, under 300 words, exactly these fields:
Choice: <the option, one line>
Scope and conditions: <the limits and qualifications that must hold, or "none">
Evidence: <file:line and the quote, one line per passage or entry that decides it>
Contradicts: <the rule or recorded entry the choice contradicts, quoted, or "none">
Confidence: high | medium | low — <one sentence why, naming any high-impact criterion>
Settled by the docs: yes "<the quote that settles it>" (file:line) | no
```

An agent that returns nothing, not this form, or reports that it saw another answer: one fresh agent with the same
prompt; failing again, the question is written with `**Subagent.** no answer, disagree.`

## 5. (b) Needs a ruling: compare and write the question

Read your hidden answer again, then compare. Agreement means the same choice, scope and conditions, not the same
words or the same confidence. When the agent says `Settled by the docs: yes` and you agree on reading its quote, the
docs settle it: back to step 2 (act, no question; a lagging page is an `Automated` entry), remove the hidden folder,
and stop. When you do not agree with its quote, it is a disagreement.

Otherwise write the question to the run's question file, `<questions><date>-<branch-slug>-<n>.md`: `<branch-slug>` is
`git branch --show-current` without `<prefix>`, every run of characters other than letters and digits turned into `-`;
`<n>` is the highest of the branch's question files when it still has an open question, else the next number (1 for the
first). This lists the branch's question files and their open questions:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && b=$(git branch --show-current); s=$(printf '%s' "${b#<prefix>}" | sed -E 's/[^A-Za-z0-9]+/-/g'); echo "branch $b, slug $s, today $(date +%F)"; for f in <questions>*.md; do case "$(head -1 "$f")" in "# Questions: $b run "*) echo "$f: $(grep -c '^\*\*Status\.\*\* open' "$f") open";; esac; done)
```

A new file is `<questions><today>-<branch-slug>-<n>.md`, its first line `# Questions: <branch> run <n>` (the branch as
`git branch --show-current` prints it), then an empty line and an italic line saying what the file is: *The questions of
this run that the docs did not settle, each with the answer the AI picked and an independent agent's; `/pose-questions`
takes them to the owner, and the file stays on the branch as the record of what the AI did on its own and why.*

Append one block, `<k>` the file's highest `Q` number plus one (`Q1` in a new file), the fields in this order, one line
each:

```
### Q<k> <title>
**Where.** <flow>, <task>, `<file>` (`<symbol>`)
**Question.** <the question, one sentence ending in a question mark>
**Options.** (1) <… and what it produces> (2) <…> (3) <…>
**Picked.** (<n>): <your reason, with the passages>
**Subagent.** (<n>), agree.
**Acted on.** yes
**Status.** open
```

`**Subagent.**` is the agent's choice and `agree` or `disagree` (`(3), disagree.`); `**Acted on.**` is `yes` or `no`
(step 6). The title is one line, the gist. Every story id and scene id in the block is a link, as the vault's `LINKS.md`
writes it where the project keeps one, relative to the question file:
`[W9.2](../stories/member.md#W9.2%20—%20An%20incident)`, `[shift.incident](../screens/definitions/shift.incident.md)`; in
the heading and in code spans they stay plain text (`just links-check` reads `paths.questions`). Then remove the hidden
folder: `rm -r <HIDDEN>`.

## 6. (c) Act or collect

| Flow | Agree | Disagree |
|---|---|---|
| A brainstorm (`/brainstorm`, before `/design`) | asked in the conversation (step 2); never a file, never an agent | the same |
| `/design` (its steps, the plan it writes), a plan (`/implement`'s `plan`) | rule and act | defer, or ask at once when it blocks |
| An implementation task, an audit | rule and act | defer, or ask at once when it blocks |
| Test fixing (any test, the follow-through's included) | inside the autonomous run: rule and act at once; else act at once | defer |
| A review (`/review-design`) | collect | collect |

- **Rule and act** (inside `/design`, `/implement` or `/audit`; outside them, as **Act**): the agreement of the two
  answers is the ruling. Record it at once through `/record-decision --automated`: its `Context` the question and that
  it was ruled by the agreement of `/answer-doubt`'s two answers (no owner ruling), its `Decision` the picked answer,
  its `Source` the question (`<question file>#Q<k> <title>`, its path under the vault), so that the question's status becomes
  `decision <n>`; then carry it out in the work and set `**Acted on.** yes`. The entry is applied as any entry of the
  build (an apply task of the plan when recorded before it, else `/review-decisions` at the end of `/implement`); the
  owner sees it among the entries they did not rule (`just decisions list`) at the audit.
- **Act**: carry out the picked answer in the work, then set `**Acted on.** yes`. The owner confirms or corrects it at
  the end of the flow; a different answer is revisited by the follow-through.
- **Defer**: `**Acted on.** no`, the question stays `open`; the work goes on around the point and does not guess it, and
  `/audit` › `verify` poses it before the push (outside the autonomous run, `/pose-questions` at the end of the flow).
- **Ask at once when it blocks**: only when nothing of the flow can go on without the answer, and there is a solid
  reason it cannot wait for the audit. Ask the owner in the conversation, now (this skill runs in the main session),
  with the passages, the options each with what it produces and the picked one recommended; their ruling is recorded
  through `/record-decision` (not `--automated`), the question's status becoming `decision <n>`. A terminal that met the
  doubt returns it as its `needs_user`; the orchestrator runs this skill.
- **Collect**: `**Acted on.** no`; the work goes on around the point and does not guess it.

Acting edits code and tests only (in `/design` and a plan, the record and the plan), never a protected document: the
page waits for the ruling and the entry applied through `/apply-decision`, and `just decisions guard` in
`just design-integrity-check` refuses anything else. This skill commits nothing: the flow's next commit carries the
question file with the work.

**Report** to the flow in one line: `Q<k> in <question file>: picked (<n>), subagent <agree|disagree>, acted on
<yes|no>`, plus `decision <n> recorded (Automated)` for a ruling by agreement, `deferred` or `asked: decision <n>`
for a disagreement, or `merged into Q<k> of <question file>`, or step 2's line.

## Never

- Never write under `paths.questions` in the brainstorm, and never spawn the agent there: the question file is for the
  flows from `/design` on, where the owner may be away. In the brainstorm, ask them.
- Never bring a question through this skill that changes no protected document (a preference, a fact of the owner's
  environment, a process or proof question, a tool's internals): ask it in the conversation or decide it yourself.
- Never ask the owner directly from `/design` on but a disagreement that blocks the run with a solid reason: the
  rest is the agreement's ruling or `/pose-questions`, in `/audit` › `verify`.
- Never show the agent your answer, your leaning, the hidden folder's path, or the options ranked; never write your
  answer after reading the agent's.
- Never record a ruling the owner did not give but the two this skill causes, both `/record-decision --automated`: a
  page found lagging in step 2, and, inside `/design`, `/implement` or `/audit`, the agreement of the two answers
  (step 6).
- Never edit a protected document; acting edits code and tests only.
- Never spawn an agent for a question the docs settle, nor a second agent but the one retry of step 4.
- Never write a second question for one an open question of the run's question file already asks; merge it.
- Never act on a question that needs a ruling in a review, nor from `/design` on on a disagreement; in the
  brainstorm the owner's answer in the conversation, recorded, is what is acted on (a
  docs-settled or immaterial answer of step 2 is acted on in every flow).
- Never leave out `Picked` because you are unsure: the owner sees your answer even when uncertain.
- Never name a model for the agent: `just omc models orchestrator` inside `/design`, `/implement` or `/audit`, otherwise
  the harness default.
- Never run a `just decisions` subcommand yourself but `list` and `show`; `/record-decision` runs its own.
