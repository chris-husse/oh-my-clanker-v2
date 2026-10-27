---
name: design-review-conventions
description: Shared rules for /review-design and /validate-design. Review file naming and gate, the decision-log section contract, the findings format, agent prompt templates, triage, and the /tmp worksheet. Not a command; the two skills read these files by path.
user-invocable: false
---

# Design review conventions

Read the file you need; each rule lives in exactly one of them.

- `review-files.md`: where review files live (directly in `docs/reviews/`; iterations and raw feedback in its subfolders), how they are named, the gate, iteration files, the decided check, what may read `docs/reviews/`.
- `decision-log-section.md`: the section a review cycle appends, with the `Review file:` contract line.
- `findings-format.md`: the block every validation agent writes.
- `agent-prompts.md`: the four agent templates (check-cluster, validate-document, verify-review, and carry-document, which `/review-design` dispatches for a settled-but-lagging comment: each new ruling is applied through `/apply-decision`) and the lines every prompt carries.
- `triage.md`: the three buckets, the consequence sort, the status line, the stop recommendation.
- `worksheet.md`: the run directory under `/tmp` and the worksheet kept there.
