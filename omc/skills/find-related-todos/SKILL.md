---
name: find-related-todos
description: "From a brief, pick the known open work that fits it (briefs, deferred rulings, open questions, the project's own sources, TODO comments), each with why it fits. `/find-related-todos <brief>`, run inline by the primer; reads only."
---

# find-related-todos

`/find-related-todos <brief>`: which of the known open work fits this brief. The ▣ primer runs it inline through the
Skill tool; the owner can type it. It reads and changes nothing: it edits no file, writes no entry and no question
file, commits nothing, starts no agent, never talks to the owner, and runs no build or test. An empty brief, typed by
the owner: ask for it.

## 1. The items

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc todos --json)
```

One JSON list; each item has `source` (`tasks`, `deferred`, `question`, `todo`, and the sources of the project's own
`omc/bin/todos`), `path`, `title`, `theme` (where one can be read, else null) and `start` (the command that starts it).
The brief is a path (read from the root) or text. When the primer has read the brief's subthemes and pages, they come
with it.

## 2. The pick

An item fits when it is:

- **the same subtheme**: its `theme` is one the brief reaches (or sits under it);
- **the same page or file**: the page, screen or code file its path or title names is one the brief changes;
- **a clear extension**: finishing it is the same work as the brief, or the brief would leave it half done.

Read the item's source (the brief file, the entry's context, the question, the test) before picking it; a title
alone is not enough. An item that only shares a word with the brief does not fit. Nothing fitting is a valid answer.

## 3. The answer

A list, most fitting first. Each item: its source and path, its title, why it fits (which of the three, and the
subtheme, page or file that links it), and its `start` command. A deferred entry is named by its id. Ends with the
count picked of the count read. The primer puts it in its report as "Related open work"; the seed asks the owner which
ones the branch takes in.

## Never

- Never edit a file, write the log, an entry or a question file, or commit.
- Never pick on a title alone, and never settle what the branch takes in: that is the owner's, asked in the seed.
