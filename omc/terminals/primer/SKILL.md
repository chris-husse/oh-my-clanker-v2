---
name: primer
description: "Read the vault in its order of authority and return what the brief touches: the rules, pages and code, cited."
---

# primer

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it reads the brief, then
the vault in its order of authority, and returns what the brief touches, every item cited by file and heading, and
ends with one `OUTCOME` line. The report is what the design starts from; the scope questions in it are the
orchestrator's to put, never this terminal's.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `brief:` the brief, a path (`.cache/omc/brief.md`, a
`<name>.md` of `paths.briefs` of `omc/config.yaml`) or its text.

**It reads and changes nothing.** It edits no file, writes no entry and no question file, commits nothing, and runs
no build, no test and no gate; its only `just` commands are the read verbs of `just omc gitnexus` (`query`, `context`,
`impact`, `cypher`, through `/explain`), never `install` or `refresh`, and `just omc todos` (through
`/find-related-todos`). It reads with `/explain`, `git`, `grep` and the
files themselves.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed is written out in the next one.

## 1. The brief

Read the brief first, whole: a path is read from the root, text is taken as given. What it asks, the actors, rules,
documents and code it names, and the words it uses are what the reading below looks for. A path that does not exist, or
an empty brief, is `failed`.

## 2. Where to look

The context map of `.claude/skills/explain/SKILL.md` (its step 1) is the order of authority: read it there and
follow it; an earlier source wins when two disagree.

Start at the indexes the map names, where the project has them, to find the themes, stories and documents the brief
reaches, then read those whole; follow a story's `Rules` line and a page's links to the subthemes behind them. A page
that disagrees with a rule lags it: the report names both, and the rule stands. Each map entry the project leaves empty
in `omc/config.yaml` is skipped, and its part of the report says so.

For the code the brief reaches, run `/explain` with the brief's question (where it is handled, what calls it) and
check its citations in the tree, as its step 3 says; a cited path or symbol is read before it goes into the report.

For the known open work that fits, run `/find-related-todos` inline (through the Skill tool, as `/explain` is) with the
brief, and the subthemes and pages read above; its picks go into the report as they come, with why each fits.

## 3. The report

The report above the line is prose for the orchestrator, in these parts, every item cited by file and heading (code
by file and symbol), each with one line on what it says that matters to the brief:

- **The subthemes and rules**: each subtheme of the theme files (`paths.themes`, the file › its heading) and the rules
  of it the brief reaches, by their ids.
- **The stories**: where the vault holds stories (`stories/*.md` under the top folder of `paths.decision_log`), each
  story (its file › its heading, its id) and its `Rules` line.
- **The protected documents**: the documents of `paths.protected` the brief reaches; each page that lags a rule named
  with the rule it lags.
- **The code**: the files and symbols (and `.claude/skills/` when the brief reaches a skill) that hold what the brief
  changes, and where the code and the pages disagree.
- **The open questions**: each question of a question file (`paths.questions`, a file whose first line starts
  `# Questions: `) whose `Status` is `open` and that touches the brief, by its `### Q<k>` heading, and what its answer
  would change for it.
- **Related open work**: what `/find-related-todos` picked (briefs, deferred rulings, open questions, the project's own
  sources, `TODO` comments), each with its source path, why it fits and its start command; the seed puts them as one
  question.
- **The scope questions**: the questions whose answer changes the direction of the design (what is in and what is
  out, which rule or page it would change), each with its options and what each produces. A question whose answer
  changes nothing of the direction is not one of them.

A part with nothing in it says so in one line.

## The outcome

The last line is one of:

```text
OUTCOME {"outcome": "done"}
OUTCOME {"outcome": "failed", "reason": "the brief .cache/omc/brief.md does not exist"}
```

## Never

- Never edit a file, never write the log or an entry, never write a question file, never commit.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate; no `just` command but
  `just omc gitnexus query`, `just omc gitnexus context`, `just omc gitnexus impact`, `just omc gitnexus cypher` and
  `just omc todos`, never `install` or `refresh`.
- Never settle a scope question or an open question: both are returned in the report.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
