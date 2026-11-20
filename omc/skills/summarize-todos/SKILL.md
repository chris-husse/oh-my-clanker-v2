---
name: summarize-todos
description: "List all the known open work, deduplicated, grouped by theme and source, each with the `just design` command that starts it, and the counts per source. Typed by the owner; reads only."
---

# summarize-todos

`/summarize-todos`: every known open item and how to start it. The owner types it. It reads and changes nothing: it
edits no file, writes no entry and no question file, commits nothing, starts no agent, and runs no build or test.

## 1. The items

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc todos --json)
```

One JSON list; each item has `source`, `path`, `title`, `theme` (or null) and `start`.

## 2. Deduplicate

One gap in two sources is one item, both sources named: a brief and an open question about the same matter, a `TODO`
comment and an open test of the project's for the same behaviour. Read the sources of a doubtful pair before merging them;
two items that merely share a theme stay two. The merged item keeps one `start` command, the one of the source that
holds the most, in the order `just omc todos` gives the sources (tasks, deferred, question, the project's own, todo).

## 3. The list

Grouped by theme (`T<nn>`; an item of a subtheme, as `T9.3`, is grouped under its theme, `T9`; items without one
last, under "No theme"), then by source within a theme. Each item: its
title, its source paths, and its `start` command. A deferred entry shows its id and `just design --deferred <id>`.

It ends with the counts per source (items read, and after the merge).

## Never

- Never edit a file, write the log, an entry or a question file, or commit.
- Never start an item: the command is shown, the owner runs it.
