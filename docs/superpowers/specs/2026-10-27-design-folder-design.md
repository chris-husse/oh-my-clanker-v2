# The design folder: layout, decision log, reviews and tools

Date: 2026-10-27. Status: approved in discussion, written for review.

## 1. Goal

This repository adopts the design-management framework built in the `apuntalo.co` repository, generalized so that
it fits any repository: a Markdown folder, `docs/`, holding the high-level design, an append-only decision log
written only by a tool, review files that a review cycle turns into rulings, link rules checked by a tool, and a
freshness chain for generated files. The existing high-level design moves into it, and the existing decision
log is converted into the tool's format.

This is the first instance of the general design tool that omc v2 will become. It is a migration, not the full
design of that tool. The constraints that carry forward:

- nothing in `docs/`, the tools or the skills names a product, a domain, a reference kind or an editor;
- a reference is a link, and the only check is that its target exists;
- every tool is Python; there is no Dart in this repository;
- the `apuntalo.co` repository is not touched.

The source material is the `apuntalo.co` repository at commit `467e9e9`: its skills under `.claude/skills/`, its
`docs/LINKS.md`, `docs/reviews/README.md`, `docs/index.md`, and the specs `docs/superpowers/specs/
2026-10-13-design-review-skills-design.md`, `2026-10-18-obsidian-vault-design.md` (the folder's link rules; the editor it names plays no part here),
`2026-10-19-decision-log-tool-design.md` and `2026-10-19-ensure-up-to-date-design.md`. Where this document is
silent, the behaviour of the source is the behaviour to port, minus everything section 2 removes.

## 2. What is removed from the source

- Every product word: the product name, its actors, its domain. The worksheet prefix becomes `/tmp/design-review-`.
- The reference kinds: story, scene (screen), design section. Their regexes, indexes, affected fields, search
  flags, mention auto-linking, the actor word list of the slug warning, and the vocabulary rulings a skill reads
  before writing.
- Legacy entries: the backfill tool, the `legacy` status, the prose supersession scan, the founding sections 1 to 8
  without entries. This repository starts with an empty log; the source converts its own log when it adopts this
  tool, later.
- Everything about mocks, screens, screen definitions and their `references` fence, product documentation,
  translations, Confluence publishing and comment harvesting, and the follow-ups to those skills.
- The Dart tools. The link checker, the pinning tool and the freshness tool are rewritten in Python.

## 3. Layout

```
docs/                                 the design folder: Markdown and embedded images only
  index.md                            the human map of the folder
  LINKS.md                            the link rules (section 5)
  decision-log.md                     the log (section 6)
  design/                             the high-level design: the corpus
    README.md                         the design's own index and naming (moved from design/README.md)
    NN-<slug>.md                      the numbered documents, two digits, 01 to 14 today
    open-questions.md                 open and parked questions (moved, not numbered)
  e2e-tests/                          E2E definitions, Markdown only, when they appear; corpus
  reviews/                            history, never corpus
    README.md
    YYYY-MM-DD-<slug>.md              review files, directly in the folder
    iterations/                       the review cycles' iteration files
    raw-feedback/                     raw extracts a future harvester writes; empty for now
  superpowers/                        specs and plans of this repository's own work; not corpus
tools/
  design/                             one Python package: the parser, the log, the links, the pins, the freshness
  pyproject.toml                      uv project; dependencies: dvc 3.67.1, pytest (dev)
  corpus.yaml                         what is corpus, history, generated (section 4)
  stages.yaml                         the freshness chain (section 9)
.claude/skills/                       the skills (section 8)
.githooks/pre-push                    refuses a stale or unpinned push (section 10)
justfile                              the recipes (section 7)
AGENTS.md, CLAUDE.md                  the protection rule, pointed at the new paths (section 11)
```

`design/` at the repository root ceases to exist; `git mv` keeps the history. The per-feature design artifact
location that `docs/design/` was reserved for in `13-testing.md` §13.1 and `AGENTS.md` moves to `docs/features/`
in the text of those two files; nothing else changes in the design's content.

## 4. The corpus declaration

`tools/corpus.yaml` is the one place that says what `docs/` contains, read by the tools and quoted by the skills:

```yaml
root: docs                            # the design folder, relative to the repository
log: decision-log.md                  # relative to the root
corpus: [design/**/*.md, e2e-tests/**/*.md]    # what agents validate and what rulings are applied to
history: [reviews/**]                 # read only by the review skills, only the file under review and its iterations
generated: []                         # link problems are warnings; the freshness chain enforces them instead
exclude: [superpowers/**]             # neither corpus nor history; never read by agents
```

Globs are relative to the root. The corpus list is what `validate-design` inventories and what the agent prompts
name as "the corpus". The history and exclude lists are the agents' do-not-read list. `generated` is empty today.

## 5. Links and references

`docs/LINKS.md` carries these rules inside the folder; the link checker enforces them.

- **Form.** Standard relative Markdown links. Anchors are the exact heading text with space as `%20` and backtick
  as `%60`, everything else raw. Never wikilinks, reference-style links, `<…>` destinations,
  GitHub slugs, absolute paths, or schemes other than `https`, `http` and `mailto`. No link leaves `docs/`; an
  outside path is a code span. `docs/` holds only Markdown and embedded images; anything
  else is `stray`.
- **A reference is a link.** Any mention of a design document, a section, a ruling, a review item or an E2E
  definition is written as a link to it. There are no reference kinds: the checker knows nothing about what a
  target is, only whether it exists. A link to a file resolves when the file exists; a link with an anchor
  resolves when that heading exists in that file.
- **The link text names its target** (`wrong-target`): when the text contains an id token (`\d+(\.\d+)*`,
  such as `2.6` in `02 §2.6` or `1.2` in `ruling 1.2`), that token is the leading id token of the target heading
  (`2.6` for `## 2.6 Trust`, `1.2` for `### 1.2 Title`); when it contains none, the text contains the target
  heading's text, or, for a link without an anchor, the file's first heading or its stem. Links into `reviews/`
  are exempt.
- **Rulings are the one id shape the checker knows,** because they are the log's own headings: `N.k` is a ruling,
  `§N` a section of the log. A bare `N.k` after the words "ruling", "rulings" or "decision log", or inside a
  parenthesis holding only references, is a certain `unlinked` problem; any other bare `N.k` that names an existing
  ruling is an `unlinked?` warning. No other bare token is looked at.
- **Links into the log** target only applied `### N.k` entries. A link to a recorded entry, a note or a section
  heading is `unapplied-target`.
- **Pinning.** History files are the log and everything under `reviews/`. In those files, a link on a line that
  came from `main` (by `git blame`) must carry the title `"git:<12 hex sha>"` of a commit on `main` where its
  target existed; whether it exists today does not matter. A link on a line from the current branch may be
  unpinned. `just pin-links` adds the titles, which leaves the link-free text unchanged. Self-heading and external
  links need no pin. Everywhere else nothing is pinned and every link must resolve now.
- **Generated files** (per `corpus.yaml`): problems in them are warnings.
- **Links are invisible to programs:** a link reads as its text to anything that extracts references.

Output of `just links-check`: `PROBLEM: <file>:<line>: <kind>: <detail>` lines, `WARNING: … unlinked?` lines, then
`OK` or `<n> problems`. The kinds: `escape`, `form`, `dead-file`, `dead-heading`, `wrong-target`, `unlinked`,
`unapplied-target`, `unpinned`, `pin`, `dead-pin`, `stray`.

## 6. The decision log

### 6.1 Entry format

```
## N. <title> (<date>[, refined <date>])

<optional description, 2 to 3 sentences>
Review file (open): docs/reviews/<file>.md        # a review section while its cycle runs
Review file: docs/reviews/<file>.md               # the same section once closed: the decided contract
Iterations: <n>                                   # written by close-section

### N.k <Title>

**Context.** <the problem and the question, the owner's words cleaned up; links for every reference>
**Decision.** <the ruling; links for every reference>
**Affected.** [<text>](<link>), [<text>](<link>)   # best guess at recording, replaced by the set touched at apply
**Supersedes.** [N.j](#N.j%20…), [§M](#M.%20…)    # leads, not verdicts
**Source.** [<item heading>](reviews/<file>.md#<heading>)   # a heading, never a file alone
**Status.** recorded YYYY-MM-DD[ · applied YYYY-MM-DD[, nothing to change]] | note
Answers: <ids>                                    # review item ids, iteration finding ids, or quoted phrases
```

Rules carried from the source: the log is append-only and the tool is its only writer; an entry takes `k+1` in the
open section, which is always the last `## N.`; Context and Decision never change after recording; an applied
entry's link-free text never changes; an empty field is not written; `Answers:` stays a bare line so `^Answers:`
matches; notes are never applied and never linked to; every link in a new or still-recorded entry must resolve, or
the call is rejected and the log untouched; links inside the log are `#heading` anchors, elsewhere relative to the
log, and the tool writes no pins.

What changed from the source: one `Affected` field instead of three; links are written by the caller and checked by
the tool, never inferred from the text; the status forms are four, not five (no `legacy`).

### 6.2 Commands

`just decisions <subcommand>`, each a thin wrapper over the package:

| Subcommand | Does |
|---|---|
| `show <id>…` | prints entries |
| `list [--section N]` | one line per entry |
| `search [--affected <path-prefix>] [--source <path-prefix>] [--supersedes <id>] [--status s] [--section N] [--since date] [--text regex] [--oneline\|--ids]` | filters entries; `--affected` and `--source` match a link target by docs-relative path prefix, with an optional `#heading` |
| `history <path[#heading]>` | every entry whose Affected or Supersedes links hit that target, oldest first, with transitive `later:` leads through Supersedes |
| `check` | the integrity check (6.3) |
| `new-section --title t [--description d] [--review-file f]` | opens section N+1 |
| `add-decision --title t --context c --decision d [--affected link…] [--supersedes id…] [--source link] [--answers ids]` | appends an entry, status `recorded <today>` |
| `add-note --title t --text t` | appends a note |
| `apply-decision --id N.k (--affected link… \| --no-change)` | replaces Affected with the set touched, sets `applied <today>` |
| `close-section --section N --iterations n` | turns `Review file (open):` into `Review file:`, writes `Iterations:` |

A link argument is `<docs-relative path>[#<heading text>]`; the tool encodes the anchor and verifies the target.
`--review-file` is repository-relative, because it is written verbatim as the contract line `Review file: docs/reviews/<file>.md`.
`--docs <dir>` points every subcommand at a copy of the folder for a dry run.

### 6.3 `check`

The log parses; ids are unique and ascending; each entry sits under its own section; a decision has Context and
Decision; Status is one of the four forms; every link of a recorded entry resolves (pinned links are the link
checker's); an entry that is applied or a note in `HEAD` is unchanged in link-free text and still present. Runs in
`just build`.

## 7. The tools

One package, `tools/design/`, managed by uv (`tools/pyproject.toml`), Python 3.12, standard library plus `pyyaml`
for the two YAML files and `dvc==3.67.1` for the freshness chain. Modules:

- `folder.py`: walks `docs/` (`git ls-files --cached --others --exclude-standard`), parses headings, fences and
  links, encodes and decodes anchors, resolves a link to a file and heading, reads `corpus.yaml`;
- `log.py`: the log's parser and writer (sections, entries, fields, statuses), shared by everything below;
- `decisions.py`: the subcommands of 6.2 and the check of 6.3;
- `links.py`: `links-check` (section 5);
- `pins.py`: `pin-links`, with `git blame` and `git log` against `main`;
- `freshness.py`: `ensure-up-to-date`, `mark-up-to-date`, `recorded-at` (section 9);
- `tests/`: pytest, one file per module, each test building a `docs/` folder in a temporary git repository. The cases are
  ported from `test_decisions.py` and from the Dart tests `check_test.dart` (links), the pin tests and
  `check_test.dart` (freshness) of the source, minus the removed features.

Console scripts in `pyproject.toml`: `design-decisions`, `design-links-check`, `design-pin-links`,
`design-ensure-up-to-date`, `design-mark-up-to-date`, `design-recorded-at`. The justfile recipes run them with
`uv run --project tools <script>`, so the pinned DVC is the one that runs. `just build` runs `uv run --project
tools pytest`, `just decisions check`, `just links-check` and `just ensure-up-to-date`.

When omc v2's own code exists, these modules become its `omc internal` commands; nothing here assumes otherwise.

## 8. The skills

Copied from the source into `.claude/skills/`, then edited as section 2 says. Each keeps its name, its
`user-invocable` and `disable-model-invocation` settings, its commit rules and its agent dispatch rules.

| Skill | Keeps | Loses |
|---|---|---|
| `decision-log` | the tool, `format.md` as section 6 | the three affected fields, auto-linking, the backfill, the vocabulary rulings |
| `record-decision` | split into Context and Decision, one question for ambiguity, title style from `list \| tail`, find what it affects and supersedes, show the command, wait, run, `links-check` | the per-kind grep steps (replaced by: read `docs/design/README.md`, `grep '^##'` over the corpus) and the vocabulary step |
| `apply-decision` | the clean-tree gate, `history` for every link, edit every passage the ruling reaches, record the set touched, one commit per decision with the entry as message and `Decision: <id>` trailer, `/reconcile-links` on failure | screen definitions, the `references` fence, the mock and docs follow-ups |
| `how-we-got-here` | references from grep and `search --text`, `history` with `later:` leads, `git log -S` where the log has a gap, the answer and gaps to the conversation and `/tmp/how-we-got-here/` | the vocabulary rulings |
| `review-design` | gate, worksheet, units, clusters, confirmations and questions, section, verify, apply, carry, `/validate-design` iterations, close, the two notes, the closing commit, the declare-minor path | the product prefix and the follow-ups; **adds**: when the open section already names the review file, continue it instead of `new-section` |
| `validate-design` | standalone and cycle modes, inline only, one agent per corpus document, merge, buckets, the review file shape, naming, zero-findings rule, commit | the hard-coded corpus globs (replaced by `corpus.yaml`) |
| `design-review-conventions` | `review-files.md`, `decision-log-section.md`, `findings-format.md`, `agent-prompts.md`, `triage.md`, `worksheet.md` | the product name, the four corpus file names (replaced by the corpus list), the actor word list of the slug warning (the rule stays: the slug must not name the product, an actor or the process) |
| `reconcile-links` | the fix per kind, the three rounds, the subagent split, the owner question, the `changed.txt` contract | nothing |
| `ensure-up-to-date` | the loop over stale stages | the stage list of the source; with no stages it reports `OK` and stops |

The skills reference the source specs nowhere; their own rules are complete in their files.

## 9. The freshness chain

`tools/stages.yaml` declares the generated files: for each stage its `skill`, `inputs`, `outputs`, optional `each`,
`root` and `exclude`, with the semantics of the source's `stages.yaml`. `just ensure-up-to-date` generates
`dvc.yaml` from it (never edited by hand), compares every stage's recorded inputs and outputs in `dvc.lock` with the
tree, and prints `OK` or each stale stage with what moved and the skill that regenerates it, ending with
`run /ensure-up-to-date`; `--full` lists every stale item, `--target <path>` restricts to the stages with an output
under it; `--root <dir>` checks another tree, which the hook uses. `just mark-up-to-date <stage>…` records a stage
as regenerated; `just recorded-at <stage>` prints the commit that last recorded it. `dvc.yaml` and `dvc.lock` are
committed; `.dvc/` holds DVC's config with `cache`, `config` and `tmp` in `.dvcignore`.

Today the file has no stages:

```yaml
dvc: 3.67.1
stages: {}
```

so the check prints `OK` and the pre-push hook passes on freshness. The first generated file in this repository
adds the first stage.

## 10. The pre-push hook

`.githooks/pre-push`, installed once per clone by `just install-hooks` (`git config core.hooksPath .githooks`).
For every pushed tip it adds a detached temporary worktree, runs the freshness check with `--root` on it and the
link checker on its `docs/`, and refuses the push when a stage is stale or any `unpinned` problem is reported. The
other link problems are `just build`'s. It unsets `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_PREFIX` and
`GIT_CONFIG_PARAMETERS` before running the tools, and removes the worktree whatever stopped it.

## 11. The protection rule

`AGENTS.md` keeps its rule and names the new paths: `docs/design/` and `docs/e2e-tests/` are protected, test code
derived from the definitions lives in `tests/e2e/`, per-feature designs go to `docs/features/`. One paragraph is
added: in this framework the owner's explicit approval of a change to the protected folders is a recorded ruling in
`docs/decision-log.md`, and `/apply-decision` (one commit per ruling, the entry as its message) and the review
cycle's carry step are the only ways an agent edits them. `CLAUDE.md` keeps importing `AGENTS.md`.

## 12. The migration of the existing log

The current `docs/decision-log.md` lists 101 questions in a hand-written format. 93 of them repeat the items R1 to
R93 of `docs/reviews/2026-10-16-adversarial-design-review.md` word for word; eight exist only in the log: Q22 to
Q24 (sources E1 to E3) and Q97 to Q101 (follow-ups to Q1 and Q2). Three are answered (Q1, the trust half of Q2,
Q97), two are parked (Q98, Q99), the rest are open.

Steps, in this order, each verified by the tools:

1. **Append the eight log-only questions to the review file** in its item form (`## <id>. [<severity>] <title>`,
   then Where, Problem, Question, options, Recommendation, Cost if wrong), before `## Dropped findings`: E1, E2, E3
   under those ids with the text of Q22 to Q24; Q97 to Q101 as R94 to R98. The review file's `Where` lines become
   links once the design is in `docs/` (step 2), as every other `Where` line of the file does.
2. **Move the design** (`git mv design docs/design`) and rewrite every path in the moved files, the review file, the
   README and `AGENTS.md`. Every reference under `docs/` that section 5 requires to be a link becomes one.
3. **Write the new log** through the tool, starting from an empty file with the header
   `# Decision Log` and *Append-only. Every ruling and its reasoning, dated.*:
   - `new-section --title "Review: adversarial-design-review" --review-file docs/reviews/2026-10-16-adversarial-design-review.md`
     with the description from the old log's header;
   - `add-decision` for Q1: Context from its Problem and Question, Decision from its Answer and the amendment
     paragraph, Affected from its `Recorded in` line, Source `#R1. [blocker] MVP scope of multi-repo work`,
     `--answers R1`;
   - `add-decision` for the trust half of Q2: Source R2, `--answers R2`, with the Decision stating that the other
     gates are R98;
   - `add-decision` for Q97: Source R94, `--answers R94`;
   - `add-note --title "Parked"`: Q98 and Q99 are parked with 14 §14.2, not MVP;
   - `apply-decision --id 1.1|1.2|1.3 --affected …` with the sections the old log's `Recorded in` lines name, since
     the answers were written into the design in the same turn they were given;
   - the section stays open: its cycle continues with `/review-design` on the remaining items.
   The recorded and applied dates are 2026-10-27, the dates the old log gives.
4. **The old log's open questions are not carried into the log.** Their text is in the review file. The old file
   is replaced, and git keeps it.
5. `just decisions check`, `just links-check`, `just ensure-up-to-date` print `OK`.

## 13. Testing and verification

- `uv run --project tools pytest` green, with the ported cases.
- `just build` green on the branch.
- Hand check: `just decisions show 1.1 1.2 1.3`, `just decisions history "design/02-repos-and-config.md#2.6 Trust"`
  lists 1.2, `just decisions search --status recorded --oneline` is empty.
- `/review-design docs/reviews/2026-10-16-adversarial-design-review.md` passes its gate and continues section 1
  (checked up to the first question, then stopped).

## 14. Rollout

One branch, `feature/design-folder`, ordinary commits, nothing published by this work. After the merge, once on
`main`: `just pin-links`, commit, then `just install-hooks` in each clone, in that order, because lines merged to
`main` need pins before the hook lets the next push through.

## 15. Out of scope

The omc v2 feature that will make this layout available to any repository (config, `omc internal` commands, hooks);
comment harvesting from a wiki; a CI job; any change to the `apuntalo.co` repository; converting its log.
