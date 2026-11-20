---
name: explain
description: "Explain how something works in this project, from the context map and the GitNexus graph, checked against the tree, cited by path:line. `/explain <question>` typed by the owner, or run inline by an agent for where to look, the code a section cites, the callers of what a change touches."
---

# explain

`/explain <question>`: how does X work, where is Y handled, what does a change to Z reach. The owner types it, or an
agent runs it inline through the Skill tool for its own question. It reads and changes nothing: it edits no file,
starts no agent, never talks to the owner, and its only `just` commands are the read verbs of `just omc gitnexus`
(`query`, `context`, `impact`, `cypher`); never `just omc gitnexus install` or `just omc gitnexus refresh`, never a
build or a test. An empty question, typed by the owner: ask what to explain.

## 1. The context map

Where this project's truth lives. Read in this order; an earlier source wins when two disagree:

1. The theme files (`paths.themes` of `omc/config.yaml`), where the project has them: its main source of truth, one file
   per theme. Every design rule in force (`## T13`, `### T13.2`), each with a stable id (`R13.2-4`) and its sources. The
   rules win over every page below; a page that says otherwise lags them. How a rule changed is in git history (the
   theme files' log).
2. The protected documents (`paths.protected`): the project's design documents, an index or README of them first where
   they have one. The stories among them (`stories/*.md` under the top folder of `paths.decision_log`, the vault) give
   the situation, the goal and why; each story's `Rules` line names the subthemes holding its details. `LINKS.md` at the
   top of the vault, where the project keeps one, says how every document links.
3. The project's own `AGENTS.md` (or `CLAUDE.md`) and `README`: its conventions and layout.

Each entry the project leaves empty is skipped. Not part of the map: the screenshots (`paths.screenshots`), the question
files (`paths.questions`), the specs and plans (`paths.specs`, `paths.plans`).

Code: it follows the documents and never leads; `omc/` holds the pipeline and its tools, `.claude/skills/` the skills.

The map says where to look; it does not replace what the tree says.

## 2. The graph

Compose the read verbs until the question is answerable, the graph before `grep`. Each runs from any checkout,
against the primary checkout's graph at the base branch; pass only the verb and its arguments:

- `just omc gitnexus query "<concept>"`: the flows and symbols a concept takes part in.
- `just omc gitnexus context <symbol>`: a symbol's callers, callees and processes (`--file <path>` when the name is
  shared).
- `just omc gitnexus impact <symbol>`: what a change to the symbol reaches, for "what breaks if".
- `just omc gitnexus cypher "<query>"`: a Cypher query, for anything structural the others cannot say.

The first line of each is `index at <sha>, base at <sha>`: the two differ when the graph lags the base. A stderr line
of GitNexus saying the index has no embedding vectors means the results are keyword-only; the next `just design`
repairs it. Neither is fixed from here.

**No graph.** `error: GitNexus not installed: just omc gitnexus install` (exit 2), or `error: no GitNexus index in
<primary>` (exit 2): the answer says so, names the fix (`just omc gitnexus install`, or `just design` next time,
which installs and refreshes it), and comes from the map and the tree alone (`git grep`, the files), saying so.

## 3. Checked against the tree

The graph is the primary's at the base, never this branch's. Every symbol and file it cites is read in the current
checkout before it is cited: a symbol moved or gone is cited where it is now, or said to be gone; what this branch
changed (`git diff $(git merge-base HEAD origin/<base>)`, `<base>` the `base` of `omc/config.yaml`) is said as such, the graph knowing only the base. What the
graph does not show is not proof of absence.

## 4. The answer

One answer, in prose, the answer first:

- every claim cited as `path:line` (or `path:symbol`), each read in step 3;
- the flows: how the pieces connect, caller to callee;
- where the map's pages and the code disagree, both named; the rule wins over every page, and code that departs from
  a rule or a page is said to lag it;
- the index's lag, when the first line of a read verb showed one, and a keyword-only graph, when GitNexus said so;
- what could not be established, said, never guessed.
