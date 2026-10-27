# Findings format

One file per agent in the run directory, findings numbered, one block per finding:

```
## n. <title>
**Group:** conflict | gap | wording
**This document says:** <quoted passage, file and heading>
**Conflicts with:** <quoted passage, file and heading, or "nothing; undefined">
**Why it matters:** <one or two sentences>
**Question for the owner:** <one question>
```

Groups are kinds, not severities:

- Conflict: two passages disagree.
- Gap: a document relies on something no other document and no ruling defines.
- Wording: one thing under two names.

Rules:

- Quote both passages where two exist.
- Number findings from 1 within a file.
- An agent with nothing to report writes a file saying `No findings.`
- A missing file means the agent failed; the skill redispatches it.
