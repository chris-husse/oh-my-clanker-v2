# Triage

## 1. Buckets

After a validation pass is merged, every finding goes into one bucket by one question: what
happens if nothing is done?

- **Needs a ruling.** Two documents can both be read as correct and they disagree, or a
  document relies on something no other document and no ruling defines. Two documents that
  disagree with the log silent are in this bucket. These need decisions.
- **Already ruled, not carried.** A ruling, including one made earlier in this cycle, settles
  it and a document still lags. Carry and list it when the ruling is a human ruling, or an
  automated ruling the owner bulk-accepted (the accept is the approval to apply). An automated
  ruling recorded any other way stays pending: report the proposed change for approval; never
  route it around the application gate through a carry agent. An automated ruling settles a
  finding like any other ruling; a later answer that would change it is a supersession
  proposal, or an individual question when it touches a human ruling.
- **Dropped.** Taste, or a repeat: a finding whose documents already match a ruling or a
  declared-minor entry. Listed with a one-line reason. Also dropped: every finding that fails the
  materiality test below, with the reason "not material".

**Materiality test.** Only actual problems reach the owner: a user would experience something
wrong or contradictory; data, security or rights could go wrong; or a builder
would have to guess between two behaviours that both look intended. Not material: wording unless
two names would show the user an actual inconsistency; technical internals left to the technical
design; rare edge cases whose sensible answer is obvious; definitions nobody would act on
differently; anything a reasonable builder would simply get right. Apply it before bucketing; when
in doubt, drop.

One finding may split: its settled part is carried when authorized and its open part asked. The review file
shows it once with both marks. The owner may move any finding into the first bucket at a
status line.

## 2. Consequence sort

The consequence sort orders the questions, the review file and the slug: conflicts first, then
gaps, then wording. Within a group, the finding whose passages are cited by the most other
findings comes first. Ties are settled by the session's judgement.

## 3. Status line

After each pass the session shows one status line: the iteration number; the count per bucket;
how many in the first bucket are new, meaning not a split or re-raise of a finding the owner
saw in an earlier iteration; and a recommendation.

```
Iteration 02. Needs a ruling: 4 (2 new). Already ruled, not carried: 3, carried. Dropped: 6.
Recommendation: continue; the first bucket fell from 9 to 4 and two findings are new.
```

The session recommends stopping when one of these holds:

- the first bucket is empty;
- everything in it is detail the corpus defers to deep dives;
- its count is not lower than the previous iteration's.

Otherwise it recommends continuing. There is no hard cap. The owner decides at every status
line.
