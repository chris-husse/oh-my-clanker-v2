# Decision-log section

Each review cycle appends one section to `docs/decision-log.md`.

```
## N. Review: <slug> (YYYY-MM-DD[, refined YYYY-MM-DD])

<Two or three sentences: what the file is, where it came from, what it
mostly concerned.>
Review file (open): docs/reviews/YYYY-MM-DD-<slug>.md   (while the cycle runs; close-section makes it the contract line below)
Review file: docs/reviews/YYYY-MM-DD-<slug>.md
Iterations: <count of validation passes run, 0 when none>

### N.k entries: written by the tool, see .claude/skills/decision-log/format.md

### N.k Settled by earlier rulings
<one line per comment: its reference, the ruling number that settles it,
whether a document had to be carried>

### N.k+1 Declared minor
The owner closed this review on iteration NN with the following open and
declared them minor, no ruling made: <one line each: reference, file and
heading of the passage, one-line gist>.
```

Rules:

- N is one more than the last section in the working-tree log, unless that last section is
  still open for the same review file (its `Review file (open):` line names it): then the cycle
  continues that section and opens none.
- Entries are written only through `just decisions` (`add-decision`, `add-note`); the header through
  `new-section` and `close-section`. Nothing in this file is written by hand. `new-section` writes the header
  with `Review file (open): <path>`; `close-section` turns that line into the contract line `Review file: <path>`,
  so the line exists only once the cycle has closed.
- The header date is the day the section opened; `close-section` adds `refined <today>` when
  the cycle closes on a later day.
- The `Review file:` line is the contract. A review file is decided when the committed decision
  log contains that whole line: repo-relative path, no trailing whitespace. `review_decided` in
  `review-files.md` checks it with
  `git show HEAD:docs/decision-log.md | grep -Fx 'Review file: docs/reviews/<name>'`.
- An uncommitted section does not count for the contract. Inside a running cycle it does count
  as rulings for the agents of that cycle.
- Every review file ends with a section, including files the owner
  closes without ruling.
- Renaming a decided review file is the owner's job and includes amending the line.
- Rulings are either human answers interpreted and cleaned up, or proposed rulings the owner
  bulk-accepted: the substantive agreement of the orchestrator's hidden answer and a fresh
  independent try-answer agent, with no conflict against a human ruling. Use the corpus's own words and a link for every reference
  (`docs/LINKS.md`). The orchestrator records through `just decisions`: `--automated` writes
  `**Automated.** true`; ordinary human recording writes false. Never put attribution into the
  Decision text or relabel old entries. Unresolved ambiguities stay in the worksheet, not policy.
- Bulk-accepted rulings carry less weight than human ones: they may supersede only automated
  rulings, never a human or legacy one. The bulk accept is the owner's approval to apply them.
- The `Answers:` line names the finding numbers a ruling answers. Iteration findings are named
  by iteration and number, as `01.3`. Comments in a free-form file are named by a short quoted
  phrase each.
- The section closes with two entries. `Settled by earlier rulings` has one line per comment:
  its reference, the ruling number that settles it, whether a document had to be carried.
  `Declared minor` opens with the sentence in the template and has one line per open finding:
  reference, file and heading of the passage, one-line gist.
