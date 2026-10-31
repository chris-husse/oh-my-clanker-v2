---
name: review-design
description: "Review a committed file under docs/reviews/. Independently answer each question in the orchestrator and fresh try-answer agents (waves of up to 20); non-conflicting agreements become proposed rulings shown in numbered batches of five, accepted ones are recorded as Automated, and the rest are asked individually with one upcoming preview. Apply authorized rulings and validate until the owner stops. The owner invokes this; never run it on your own."
disable-model-invocation: true
---

# Decide one review file

One review file in, one decision-log section out. The rules this skill follows live in
`.claude/skills/design-review-conventions/`: `review-files.md` (names, gate, the shell
functions, slug warning, commit question), `decision-log-section.md` (the section and its
`Review file:` contract line), `findings-format.md` (the block an agent writes),
`agent-prompts.md` (the four agent templates and the lines every prompt carries), `triage.md`
(buckets, consequence sort, status line), `worksheet.md` (the run directory, the worksheet,
the output file names). This file names them by path and does not restate them.

Before anything:

- The orchestrator reads the relevant corpus and decision history to form its own answers
  and check conflicts. It never edits a corpus document itself: `/apply-decision` (step 7)
  edits for an authorized new ruling and carry-document agents (steps 7 and 8) for an
  authorized settled-but-lagging comment. The owner's bulk accept of a batch (step 5) is the
  approval to apply those rulings; the `Automated` field alone grants none.
- The orchestrator presents questions, records answers through `just decisions`, and maintains
  progress itself. Do not delegate answer recording or create a background recording queue.
- Show one current question and the next unanswered question as a preview labeled exactly
  `Upcoming (Don't answer yet)`; show only the current question if one remains. Each displays
  `Question n of N` and the count remaining after it, taken from the worksheet. Only the
  current question requests an answer; displaying the preview never answers or approves it.
  Interpret an unnumbered reply only against the current question: repeated affirmations
  such as "yes yes" do not answer the upcoming preview.
- Record each answer, then promote the preview and show the next prepared question without
  rerunning the audit or applying documents between answers. Do not normally ask immediate
  follow-ups: preserve uncertainties for the next review/validation pass without inventing policy.
- Ask only about materially different workable choices not settled by existing material.
  Resolve ordinary implementation details and correctness requirements without asking the owner.
  Every unresolved prepared question first gets two independent answers (step 4): the
  orchestrator's saved, hidden answer, then a fresh `/try-answer-design-question` agent's answer.
  Their substantive agreement, with no conflict with a human ruling, is a **proposed ruling**;
  nothing reaches the log until the owner has seen it in a batch of five (step 5). A confidence
  score alone never makes a proposal. Bulk-accepted rulings are recorded with `Automated: true`
  and carry less weight than human rulings: they may supersede automated rulings only.
- The commits of a cycle are the review file at the gate, the commits of steps 7 and 8 (one per
  ruling by `/apply-decision`, one `Carried:` commit per pass for the documents the carry-document
  agents edited) and the
  closing commit of step 10; nothing else is committed. The log is committed only by `/apply-decision` (whole, with each
  ruling) and at step 10; the iteration files only at step 10.

Every command starts from `ROOT=$(git rev-parse --show-toplevel)` and runs in a subshell in
`ROOT`. Shell state does not survive between calls: write the run directory path in place of
`<RUN>`, the section number in place of `N`, and the argument in place of `<argument>` in every
command. Where a command uses `review_gate` or `review_undecided`, paste the whole function
block of `review-files.md` section 3 into that subshell where the comment says so. Every agent
is `subagent_type: general-purpose` with no `model` parameter; cluster, validation and carry agents of one step go in one
message; try-answer agents go in waves of at most 20, one question each, dispatched only after the
orchestrator's answers for that wave are saved. Wait for completion before reading output; a missing output file is redispatched
once with the same prompt (`agent-prompts.md` section 2). A session that dies mid-cycle is
resumed from its worksheet, not restarted.

## With an argument

The argument is `$ARGUMENTS`, a repo-relative path directly in `docs/reviews/`.

### 1. Gate

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT"
# paste the function block of review-files.md section 3 here
review_gate "<argument>")
```

- `REJECT <reason>`: quote the printed reason and the naming rule of `review-files.md`
  section 1 to the owner, and stop.
- `UNCOMMITTED`: ask once, as the whole turn:
  `Commit <file> now so the review can start? (one-line message)`
  Yes: commit that file alone with the owner's message and continue. No: stop.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add "<argument>" && git commit -m "<owner's one-line message>

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- "<argument>" && git show --stat --format= HEAD)
```

- `OK`, or after that commit: slug warning per `review-files.md` section 4. When the slug
  plainly names the product, an actor or the process, say so, propose a slug from the file's
  first finding, and continue; the gate does not stop on meaning.

### 2. Run directory

```bash
RUN=/tmp/design-review-$(date +%Y%m%d-%H%M%S); mkdir -p "$RUN"; printf '## Units\n\n## Questions\n\n## Status lines\n\n## Rulings as written\n' > "$RUN/worksheet.md"; echo "$RUN"
```

Say `Run directory: <RUN>` in the conversation; `/validate-design` reads it from there at
step 8. The worksheet has the four headings of `worksheet.md` section 2 and is updated at
every step below; whenever you need the list of units, questions or rulings, re-read the
worksheet, not your own history.

### 3. Understand the file

Read the argument file. No format is assumed. Write two or three sentences: what the file is,
where it came from, what it mostly concerned. Tell the owner, and write those sentences as the
first line under `## Units` in the worksheet, so they survive compaction before the first
ruling; that text becomes the section description. Choose the unit of a comment: a numbered
finding where the file has them, a question where it has questions, otherwise a paragraph.
When a file holds a merged list and the findings it merged (the folded third pass: Part 1
questions, Part 2 findings), the units are the merged entries and only that part is read; the
findings are reached through the references each entry cites. List the units in file order
under `## Units`, each with a reference in the file's own terms (`Q3`, `W2.7`, `¶12`). A `¶12`
reference is for the worksheet only; the log names a paragraph by a short quoted phrase
(step 5).

### 4. Cluster and check

Group the units into clusters by the passage they concern. Dispatch one check-cluster agent per
cluster, all in one message. Each prompt is the every-prompt block of `agent-prompts.md`
section 1 followed by the check-cluster body of section 3, placeholders filled and nothing
added: `<ROOT>` the repository path, `<OUTPUT PATH>` `<RUN>/cluster-<k>.md` with `k` the
cluster number from 1, `<description>` the sentences of step 3, `<cluster text>` the cluster's
comments verbatim, each under its reference.

Wait for every agent. Check the outputs:

```bash
RUN=<RUN>; for k in $(seq 1 <number of clusters>); do [ -f "$RUN/cluster-$k.md" ] || echo "missing cluster-$k"; done; ls "$RUN"/cluster-*.md | wc -l
```

Redispatch each missing agent once, with the same prompt, and check again. Then read every
`<RUN>/cluster-*.md` and merge the verdicts into `## Questions` of the worksheet, one entry per
unit or per merged question, each with the references it merges and its bucket for this pass:

- `needs a ruling`: the question list, in the consequence order of `triage.md` section 2, with
  both quoted passages and the agent's question.
- `settled`: the settled list, each with the ruling number that settles it and, where the agent
  wrote `document lags`, the file and heading that lags.
- `dropped`: the dropped list, each with the agent's one-line reason.

A unit with a settled part and an open part gets both marks.

Then split the question list into two classes:

- **confirmation**: the comment already states a decision (or the review file records the
  owner's answer to it), and what disagrees is only text written before it. Asking is approval,
  not deciding: the owner mostly says yes.
- **real question**: genuine friction. Two passages that can both be read as right disagree and
  the comment does not choose; the comment leaves the actual choice open; or two comments or
  answers pull apart.

When in doubt, a real question.

**Independent answers, in waves.** For every unresolved prepared question, including
confirmations, follow this sequence. A wave is at most 20 questions.

1. For each question of the wave, read its cited corpus sections and relevant decision chains
   (the first two steps of `.claude/skills/try-answer-design-question/SKILL.md`). Form your own
   answer and save it as `<RUN>-hidden/orchestrator-<ref>.md` using that skill's output
   structure. The `-hidden` folder sits beside the run directory and its path never appears in
   an agent prompt.
   Save the evidence version (HEAD plus any relevant working-tree changes and latest ruling id)
   in the worksheet. Do this for the whole wave before dispatching it; never show these answers
   to anyone, and do not delegate them. Whether you answer every question before the first wave
   or stay one wave ahead is your call.
2. Dispatch the wave in one message: one fresh agent per question, with no inherited
   conversation or prior agent context. Use the independent-answer prompt in `agent-prompts.md`
   section 7, not the general every-prompt block. Supply the review item's own text and the
   cluster agent's question and quoted passages as written, the source references and explicit
   human constraints; add no wording of your own. Exclude your answer,
   cluster recommendations, other agents' conclusions, worksheet and comparisons. The agent
   follows `/try-answer-design-question`, reads the sources itself, and writes
   `<RUN>/answer-<ref>.md`. Never let it read other files in the run directory. A failed or
   missing result is retried once with the same neutral prompt in a fresh agent; if still
   missing, the question goes to the individual flow.
3. Compare each pair as its answer arrives. Agreement means the same substantive decision,
   scope, conditions and necessary additions, not matching wording, confidence or a bare yes/no.
   An addition only one answer makes is dropped from the proposal, unless leaving it out changes
   the meaning; then, as on any disagreement, missing facts or an answer that defers the choice,
   the question is **individual**.
4. Read the relevant current ruling chains again. A recorded ruling overrides lagging corpus
   text. Check the proposed meaning, not just the agents' `Contradicts` field. An agreement that
   conflicts with an earlier **human** ruling is **individual**, however confident: record which
   ruling, its quoted passage and why the proposal would contradict it. Legacy rulings
   (`Automated: unspecified`) count as human, and so does the human successor of an automated
   ruling. An agreement that changes an **automated** ruling from an earlier pass is a
   proposal that supersedes it; note the id and what it said. One that changes an automated
   ruling recorded in this pass is **individual**. Repeat this check when the batch is built. If the evidence changed materially since
   the answers, the question is **individual**.
5. Save both answer paths, the comparison, the conflict check (with any conflicting human
   ruling) and the route in the worksheet: **proposed** (full agreement, no human conflict) or
   **individual**. Already settled questions reference the existing ruling rather than
   generating duplicates.

On resume, reuse completed answer pairs and recorded rulings. Never reconstruct an allegedly
independent first answer after reading the second. Never open an `answer-<ref>.md` whose
`<RUN>-hidden/orchestrator-<ref>.md` (or its `-rN`) is missing: mark it `discarded` in the worksheet and answer the question
again from scratch, writing `orchestrator-<ref>-r2.md` and `answer-<ref>-r2.md` (the next `rN`
if those exist too). Do not rerun completed pairs after each owner answer.

Tell the owner the counts so far: settled, dropped, proposed, individual. Step 5 shows the
batches as soon as five proposals are ready, while later waves still run.

### 5. Confirm, then ask

**The open-section check comes first**, every time this step starts, whatever follows. Read the log's open section,
the last section's heading and the last `Review file (open):` line, two lines and nothing more:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && grep -nE '^## [0-9]+\. ' docs/decision-log.md | tail -1; grep -n '^Review file (open):' docs/decision-log.md | tail -1)
```

When the second line comes after the first (a higher line number) and reads
`Review file (open): <argument>`, the log's open section already belongs to this review: an
earlier session ran part of its cycle. Continue in that section: N is the number of the first
line, `new-section` is skipped, and `just decisions list --section N` shows the entries it
already holds; copy the section as it stands, its header block and those entries
(`sed -n '/^## N\. /,$p' docs/decision-log.md`: the open section is the last one, so these are its own lines), to
the top of `## Rulings as written` in the worksheet. Otherwise the section is opened before the first ruling, below.

**Batches of proposed rulings first.** As soon as five proposals are ready, show them as one
batch, numbered 1 to 5 in consequence order within the batch; the last batch may hold fewer. Each entry:

```
**1. R40 — <title>**
Context: <what the comment found, in the corpus's words>
Question: <the choice>
Proposed ruling: <the agreed ruling>
Supersedes: <id> — <what it said>      (only when it replaces an automated ruling)
```

Length follows complexity: two or three lines for an easy question, more for a hard one, never
the full write-up of an individual question. Close the batch with
`Reply with the numbers that are wrong; the rest are accepted ("ok" accepts all).`

Save the batch and the owner's exact reply in the worksheet. Numbers named as wrong go to the
individual flow, where they are asked like any other question, with both answers. A number
may also be given as the review reference (`R40`). A doubt about one proposal ("not sure about
3") sends that proposal to the individual flow. A number or reference that names nothing in the
batch, or "ok" next to a number without saying which way ("ok 2 4", "ok, 3"), makes the whole
reply unclear; "ok except 2" or "ok but 2 is wrong" is clear (2 wrong, the rest accepted): record nothing from it and show the same batch once more,
saying which part did not match; a second unclear reply sends all of its proposals to the
individual flow. Never guess. Every other proposal is accepted: the bulk accept
is the owner's approval of the ruling and of applying it (step 7). Record each accepted proposal
in batch order through `just decisions add-decision --automated`, with `--supersedes <id>` when
the entry showed one. Immediately before each write, check for a duplicate and against the
rulings recorded so far in this pass: a proposal that now contradicts one of them goes to the
individual flow instead of superseding it. Read back `just decisions show <id>`, confirm
`**Automated.** true`, and mark the worksheet entry `bulk-accepted`. The tool refuses
`--automated` with a human, legacy or section target, or an automated target a human ruling has
already superseded, and writes nothing; such a proposal goes to
the individual flow. Uncertain writes are reconciled before retrying. After each batch, report
the ids recorded. Show the next batch when five more are ready.

The owner can correct an automated ruling through a later successor, never an edit or silent
relabeling. Provenance follows what the owner contributed, in a batch reply or an individual
answer alike. A reply that only accepts or picks a presented option ("ok", "yes", "(a)") is an
acknowledgement: record it with `--automated`. A reply that states, changes or reasons the
decision in the owner's own words is a human ruling: record it the ordinary way
(`Automated: false`); it may supersede anything. When an acknowledged option would have to
supersede a human ruling, the tool refuses it; ask the owner for their own wording instead.

**Summary after the last batch.** When every wave has finished and the last batch is answered,
list the automated rulings of the pass, important ones first (scope, architecture,
security/trust, compatibility, manual user work), each with id, reference and one-line decision;
keep it in the worksheet.

**Individual questions after the summary.** Then the individual questions follow: the
disagreements, the human conflicts (naming the human ruling, quoting it and explaining why the
agreed answer would contradict it), the proposals rejected or unclear in a batch, and the failed
pairs, all in one consequence order with confirmations first.

**Current question and upcoming preview.** Use the next two unanswered prepared questions
from the worksheet's individual items, confirmations first. Explain the material disagreement,
conflict or missing evidence, both answers where relevant, and your recommendation. Proposed
additions remain proposals; never present either answer as an approved partial ruling. Start each with
`Question n of N` and the count remaining after it; label the second exactly
`Upcoming (Don't answer yet)`. Keep the same number while discussing a question, update
N when questions are added, merged or dropped, and never show only `Question n`.

For each displayed question, explain the concrete situation, relevant existing behavior,
the unresolved choice, and the practical consequences of the workable alternatives. Explain
unfamiliar terms and give a recommendation with its reason; a one-line question is not enough.
For the current question, include concise quoted evidence with file and heading; retain
confirmation references (`C1`…) as source ids. The preview needs meaningful context too,
but does not request an answer yet. Wait
for the current answer only. Preserve the prepared list between answers, rather than
rechecking the whole review. The orchestrator records the answer below before advancing.

The orchestrator saves the presented question and exact answer in the worksheet, then interprets
and cleans up only the definite decision into a ruling (`decision-log-section.md`: in the corpus's
own words, a link for every reference). Preserve ambiguities in the worksheet for subsequent
review/validation rather than asking an immediate follow-up or inventing approval. If no definite
decision can be extracted, leave it pending for that later pass and proceed to the next question. Before the first ruling, when the open-section check found
no open section for this review, open it through the tool; it prints N:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions new-section --title "Review: <slug>" --description "<description from step 3>" --review-file <argument>)
```

Its header line reads `Review file (open): <argument>` until step 9's `close-section` turns it into the `Review file:`
contract line, so no commit before the close makes the review look decided. Copy the new section's header block to
the top of `## Rulings as written` in the worksheet. Then, for this and every later ruling, record it; the tool
prints `N.k`:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions add-decision --title "<title>" --context "<what the comment or finding said and which passage it concerns>" --decision "<the ruling>" --affected "<docs-relative path>#<heading text>" … --source "reviews/<argument's file name>#<the item's heading text>" --answers "<the finding or question numbers it answers; for a free-form file a short quoted phrase per comment; iteration findings as 01.3>")
```

The context is the comment or finding in one or two sentences, the decision is the ruling as cleaned up; every
reference in either is a link (`docs/LINKS.md`). `--affected` holds the passages the question quoted, one link
argument each (`design/02-repos-and-config.md#2.6 Trust`, or the file alone for a whole document);
`/apply-decision` replaces them with the real set. Omit `--affected` when it would be empty. `--source` is
docs-relative: the item's heading in the review file (`## R4. …` gives `reviews/<file>.md#R4. …`), never the file
alone; for an iteration finding it is the iteration file's path with that finding's heading,
`reviews/iterations/<…>-iteration-NN.md#<n>. <title>` (step 8). The tool refuses an unknown file or heading and
writes nothing; fix the reference. Append the output of `just decisions show N.k` to
`## Rulings as written`, write the id into the question's entry under `## Questions`, and mark the
answer recorded; keep any unresolved parts pending. Do not claim recording succeeded without
readback, or retry an uncertain write without checking the section for an existing entry.

The `--answers` text follows `decision-log-section.md`: finding or question numbers where the
file has them; for a free-form file a short quoted phrase per comment, so the log reads on its
own; iteration findings as `01.3`. A worksheet reference like `¶12` never appears in the log.
Promote the preview to current and show the next unanswered preview.

### 6. Verify

Confirm every definite answer and every bulk-accepted proposal has been recorded and no write
failure is unresolved before verification, application or closing. For automated rulings also
confirm both independent answer artifacts, the comparison and current-history check, the batch
and reply that accepted them, and structured provenance.
Supply pending uncertainties from the worksheet as
`<pending uncertainties>` below; an answered question can still have an unresolved part.

Dispatch one verify-review agent: the every-prompt block of `agent-prompts.md` section 1
followed by the verify-review body of section 6. `<review file path>` is the argument file
(the iteration file when this step runs on iteration findings at step 8), `<unit>` the unit of
step 3, `<OUTPUT PATH>` `<RUN>/verify-<nn>.md` with `nn` the two-digit count of verify passes
in this cycle from `01`. `<section>` is built from the worksheet, not the log: the header
block and every ruling under `## Rulings as written`, then a draft
`### N.<k> Settled by earlier rulings` entry from the settled list, one line per comment with
its reference and the ruling number that settles it, then a draft `### N.<k+1> Declared minor`
entry listing every unit marked `dismissed` and every unit on the dropped list with its reason.
Wait; a missing output is redispatched once.

Read `<RUN>/verify-<nn>.md`. Material units marked `not answered` become the next prepared
question pass through step 4's independent-answer sequence, then step 5's batches and
individual questions. The owner rules on remaining disagreements, recorded as in step 5; or
the owner dismisses the unit, and its entry under `## Questions` in the worksheet is marked
`dismissed`, with file and heading and a one-line gist, for the declared-minor entry of step 9.
Dispatch verify-review again, with the next `nn`, until every unit is `answered by`; a unit
covered by the draft declared-minor entry counts as answered.

### 7. Apply

Check application authority before dispatching any protected-document edit, including carry
steps here and in step 8. A bulk accept in step 5 and an individual answer are the owner's
explicit approval of the nature of the change: apply those rulings with no further prompt. An
`Automated: true` ruling recorded any other way is not applied without the owner's approval;
summarize the proposed change and ask.

The log, with the recorded entries waiting to be applied, and the iteration files of this cycle are uncommitted
through this step; `/apply-decision`'s gate allows exactly those two to be dirty and stops on anything else. Nothing
is committed before the first `/apply-decision`.

For each ruling recorded in this cycle and not yet applied (`just decisions list --section N` shows the status), in
id order, run `/apply-decision <id>` (the skill in `.claude/skills/apply-decision/SKILL.md`; invoke the Skill tool
with `skill: apply-decision` and `args: <id>`): it needs a tree clean but for the log and `docs/reviews/iterations/`,
edits the corpus documents the ruling reaches, records the real affected set
and commits the ruling with its documents (the log goes in whole, so the entries recorded in this pass travel with
the first application). One ruling, one commit.

Each settled-but-lagging comment of step 4 names an earlier ruling and a lagging document; it has no new decision to
apply. After the new rulings, dispatch one carry-document agent per lagging document, all in one message, never
editing a document in this session: the prompt is the every-prompt block of `agent-prompts.md` section 1 with its
first line replaced as section 5 says, then the section 5 body; `<document>` the lagging document's absolute path,
`<rulings>` the output of `just decisions show <earlier id>` for the ruling of each lagging comment that names this
document, `<OUTPUT PATH>` `<RUN>/carry-<doc>.md`. Wait for every agent; a missing output is redispatched once. Read
each `<RUN>/carry-<doc>.md` (its passages and its doubts; a doubt is one question to the owner per turn), then
commit the carried documents in one commit `Carried: <earlier ids> into <documents>` with the attribution line:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just links-check && git add <lagging documents> && git commit -m "Carried: <earlier ids> into <documents>

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- <lagging documents> && git show --stat --format= HEAD)
```

Record under each question's entry in `## Questions` the commit that applied it. A doubt that arises while applying
is one question to the owner per turn; an answer that rules something is recorded per step 5 and applied the same
way.

### 8. Validate

State in the conversation, each on its own line, `Run directory: <RUN>` and `Section: N`,
where N is the number `new-section` printed at step 5, or the open section step 5 continued;
when the section has not been opened yet, state `Section: none` instead. Then invoke the Skill tool with
`skill: validate-design` and `args: <argument>`. It runs
inline, writes the next iteration file
`docs/reviews/iterations/<argument's name without .md>-iteration-NN.md` into the
working tree, leaves it unstaged, and ends with the status line of `triage.md` section 3,
without the `carried` mark.

Read the iteration file (it is a file of this cycle). Record every finding under
`## Questions` in the worksheet: a split or re-raise of an earlier entry gets its bucket for
iteration NN added to that entry; a new finding gets a new entry with its reference `NN.n`,
its passages and its bucket.

Carry the `Already ruled, not carried` bucket through carry-document agents as step 7 says for a
settled-but-lagging comment: each finding's block names the ruling and the lagging passage; one
agent per lagging document, `<rulings>` from `just decisions show <ruling id>`, output
`<RUN>/carry-<doc>.md`, never an edit by this session; commit the carried documents in one
`Carried:` commit. Then re-emit the status line with the
`carried` mark on the second bucket, and append it under `## Status lines`.

Show the owner the status line and its recommendation, then ask one question:
`Rule on the <n> open findings, declare them minor and stop, or stop?` where `<n>` is the
`Needs a ruling` count. The owner may also name a finding of another bucket to move into the
open ones (`triage.md` section 1); do so before acting on the choice.

- Rule: step 4's independent-answer sequence, then steps 5 to 7 on the open findings, in the iteration file's order, references as
  `NN.n` (`01.3`). In step 5's `add-decision`, `--answers` is `NN.n` and `--source` is the
  iteration file's docs-relative path with the finding's heading text,
  `--source "reviews/iterations/<YYYY-MM-DD>-<slug>-iteration-NN.md#<n>. <title>"` (the file
  is in the working tree, so the heading resolves; it is committed at step 10). Step 6 runs
  verify-review on the iteration file, whose unit is a numbered finding under
  `## Needs a ruling`; the other two sections are not units. Then back to the start of this
  step for the next pass.
- Declare minor: add the open findings to the declared-minor list in the worksheet, each with
  reference, file and heading, one-line gist. Go to step 9.
- Stop: go to step 9.

### 9. Close the section

The number of validation passes run is the highest `NN` of this cycle. Should no ruling have been
recorded in the cycle, the section has not been opened either; run the open-section check of
step 5, and open it now with the `new-section` command of step 5 unless that check finds it open
for the argument. Then set `Iterations:` to the count and the header's `refined` date to today;
the tool edits that header and nothing else:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions close-section --section N --iterations <count>)
```

Then add the two closing notes, `k` continuing the ruling numbers. Omit a note whose list is
empty; when the settled note is omitted, the declared-minor note takes its number.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions add-note --title "Settled by earlier rulings" --text "<one line per comment of the settled list: its reference, the ruling number that settles it, whether a document had to be carried; lines joined with ' · '>" && just decisions add-note --title "Declared minor" --text "The owner closed this review on iteration NN with the following open and declared them minor, no ruling made: <one entry each, from the entries marked dismissed at step 6 and the declared-minor list of step 8: reference, file and heading of the passage, one-line gist; joined with ' · '>")
```

Append the output of `just decisions show` for the notes to `## Rulings as written`.

**Links.** `ROOT=$(git rev-parse --show-toplevel); rm -f "$ROOT/.cache/reconcile-links/changed.txt"; (cd "$ROOT" && just links-check)`
must print `OK`. Otherwise run `/reconcile-links` (it edits only Markdown in `docs/` and lists the files it changed in
`.cache/reconcile-links/changed.txt`), and commit the files it changed with this skill's own: the commit command below
adds `$(cat "$ROOT/.cache/reconcile-links/changed.txt" 2>/dev/null)`. The rule is `docs/LINKS.md`.

### 10. Commit

Stage exactly `docs/decision-log.md` (the closed header and the notes; the entries and the
documents were committed per ruling in step 7) and every iteration file of this cycle; the paths
after `--` limit the commit to them. The stat must list the log, the iteration files not committed
at step 7, and the files /reconcile-links changed (`.cache/reconcile-links/changed.txt`), and no other.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git add docs/decision-log.md docs/reviews/iterations/<YYYY-MM-DD>-<slug>-iteration-*.md $(cat "$ROOT/.cache/reconcile-links/changed.txt" 2>/dev/null) && git commit -m "Review decided: docs/reviews/<YYYY-MM-DD>-<slug>.md (§N)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- docs/decision-log.md docs/reviews/iterations/<YYYY-MM-DD>-<slug>-iteration-*.md $(cat "$ROOT/.cache/reconcile-links/changed.txt" 2>/dev/null) && git show --stat --format= HEAD)
```

Then `rm -rf <RUN> <RUN>-hidden`. Report the section number, the commit and the summary of step 5. Finished.

## Without an argument

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT"
# paste the function block of review-files.md section 3 here
review_undecided)
```

The list is oldest first. When it is empty, say `No undecided review files.` and stop. For
each file in order, ask one question with three options: `Review <file> now, declare it minor,
or skip it?`

- Review now: run `## With an argument` on that file from step 1 through step 10, then
  continue with the next file. When step 1 prints `REJECT`, report the reason and continue
  with the next file instead of stopping.
- Declare minor: run `review_gate` on the file. On `REJECT`, report the reason and continue
  with the next file. On `UNCOMMITTED`, ask the step 1 commit question first. Then read the
  file and write the two or three sentences of step 3. Run the open-section check of step 5:
  when the log's open section already names the file, N is that section and `new-section` is
  skipped; otherwise open the section with the tool, which prints N. Then write its one note,
  close it (`close-section` writes the `Review file:` contract line) and commit the decision log alone. In a
  continued section that already holds rulings, the note's text is `The owner declared the rest of the review minor,
  no further ruling made.`, and `--iterations` keeps the count the earlier sessions reached: the section's
  `Iterations:` line when it has one, else the highest `NN` of `docs/reviews/iterations/<file's name without
  .md>-iteration-NN.md`, else 0. Only a section opened here takes `--iterations 0`.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions new-section --title "Review: <slug>" --description "<description>" --review-file <file>)
```

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions add-note --title "Declared minor" --text "The owner declared the whole review minor, no ruling made." && just decisions close-section --section N --iterations <0, or the continued section's count> && git add docs/decision-log.md && git commit -m "Review declared minor: <slug> (§N)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- docs/decision-log.md && git show --stat --format= HEAD)
```

  Continue with the next file.
- Skip: leave it undecided, continue with the next file.

After the last file, say that the list is done and stop.

## Never

- Never edit a corpus document in the orchestrator; use authorized application or carry steps.
- Never expose the first answer, conversation history or other answer artifacts to the independent
  agent, or present a revised first answer as independent after reading the second.
- Never present both displayed questions as active, or treat a preview as an answer or approval.
- Never record a ruling the owner has not seen in a batch or answered individually; never put
  a disagreement or a conflict with a human ruling into a batch; never let an automated ruling
  supersede anything but an automated ruling. Label the preview exactly `Upcoming (Don't answer yet)`; only the current question asks for an answer.
- Never delegate answer recording, fabricate missing policy, or treat an unverified write as recorded.
- Never paste an answer as a ruling; interpret and clean it up.
- Never commit outside step 1 (the review file), steps 7 and 8 (one commit per ruling by
  `/apply-decision`, one `Carried:` commit per pass for the documents the carry-document agents
  edited) and step 10;
  never commit the log or an iteration file on this skill's own account before step 10.
- Never write into `docs/decision-log.md` by any means but `just decisions`.
- Never write anything from the run directory into the repository; the worksheet and the agent
  outputs stay under `/tmp`.
- Never reach into `docs/reviews/` beyond the argument file and its iteration files
  in `docs/reviews/iterations/`, and the listing of the no-argument mode.
- Never pass a `model` parameter, and never use a `subagent_type` other than
  `general-purpose`.
- Never delete, move or trash a file; the run directory and its `-hidden` folder under `/tmp`
  at step 10 are the one exception.
