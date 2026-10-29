# Worksheet

## 1. Run directory

Each cycle of `/review-design`, and each standalone run of `/validate-design`, has one
directory `/tmp/design-review-<timestamp>/`, created with `mkdir -p`:

```bash
RUN=/tmp/design-review-$(date +%Y%m%d-%H%M%S); mkdir -p "$RUN"
```

Nothing in it enters the repo. It is deleted at the end of the cycle or of the standalone run.
It is kept when a merge fails, so the run can be redone from the files on disk without
redispatching the agents.

## 2. worksheet.md

`<run>/worksheet.md` is written by the session and updated through the cycle. It has four
sections:

- `## Units`: the units of the review file, in file order, each with its reference.
- `## Questions`: one entry per finding or merged question, whatever its bucket, with the
  comment references it merges, its bucket in each iteration, its class (confirmation, real
  question), both independent answer paths, independence (the first answer saved before its wave
  was dispatched; `discarded` pairs), evidence version, comparison of choice/scope/conditions,
  current-history conflict check (naming any conflicting human ruling), confidence, the
  automated ruling it would supersede, route (`proposed` or `individual`), the batch and number
  it was shown as with the owner's exact reply (`bulk-accepted` or moved to individual), or its
  question number/order and total, current/upcoming role, exact presented question and owner
  answer, pending uncertainties, confirmed ruling id and Automated field, and the commit that
  applied it.
- `## Status lines`: every status line shown, in order, and the ids recorded after each batch.
- `## Rulings as written`: each ruling as entered in the decision log.

A run that has nothing for a section leaves it empty.

Whenever the session needs the list of units, questions or rulings, it re-reads the worksheet
rather than its own history. Context compaction then cannot lose the list.

## 3. Agent outputs

Agent outputs sit beside the worksheet, one file per agent:

- `cluster-<k>.md`: check-cluster; `k` is the cluster number.
- `validate-<doc>.md`: validate-document; `doc` is the document's path below `docs/` without
  `.md`, every `/` as `-` (`docs/design/02-repos-and-config.md` gives
  `design-02-repos-and-config`), so two folders' files of one name stay apart.
- `carry-<doc>.md`: carry-document, the same `doc`; used by `/review-design` for
  settled-but-lagging comments; new rulings of a review are applied by `/apply-decision`, which
  writes no such file.
- `orchestrator-<ref>.md`: the orchestrator's hidden answer, saved before its wave is dispatched,
  in `<run>-hidden/` beside the run directory, never named in a prompt; `-r2` and later
  suffixes for re-answered pairs, also on `answer-<ref>.md`.
- `answer-<ref>.md`: the fresh try-answer agent's independent answer, one per unresolved prepared
  question; `ref` is the question's first reference. The agent may not read other run files.
- `verify-<nn>.md`: verify-review; `nn` is the two-digit count of verify passes in the cycle,
  from `01`.

## 4. Question progress

The orchestrator handles presentation, recording and progress directly; there is no background
recorder or separate answer queue. Show the current question and the next unanswered preview,
labeled exactly `Upcoming (Don't answer yet)`, each with `Question n of N` and the count
remaining after it. Only the current question requests an answer.

Save the exact question and answer before recording the definite ruling with `just decisions`.
Save the confirmed id and readback under `## Rulings as written`; keep uncertainties separately
for subsequent review/validation, without immediate follow-ups. Then promote the preview and
refill from the existing question list. Displaying a question never answers it.

On resume, use the worksheet and reconcile any uncertain write against the section through
`just decisions list/show` before retrying, so a successful write is not duplicated. Never
advance verification, application or closing past an unresolved recording failure.

Batches of proposed rulings come before the individual questions: save each batch as shown and
the owner's exact reply, then record the accepted proposals and their readback before showing the
next batch. Preserve both independent answers and their comparison before proposing anything. If
the first answer or independence evidence is missing, do not reconstruct it after reading the
second or claim agreement; answer the question again from scratch. After the last batch, the
summary lists the automated rulings of the pass with the important ones first (scope,
architecture, security/trust, compatibility, manual user work).
