---
name: describe
description: "Write the PR description into the message of the branch's one commit and delete the brief it came from."
---

# describe

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it reads what the branch
changed, writes the PR description as the message of the branch's one commit, deletes the brief the branch came from in
that commit, and ends with one `OUTCOME` line. The forge fills the PR's title and text from that message, so no PR is
opened here: the owner opens it after the push, which is the orchestrator's.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `record:` the record's path, `<date>-<slug>-design.md`
in `paths.specs` of `omc/config.yaml`. `brief:` `<briefs><slug>.md`, the brief the branch came from, or `none`;
`<briefs>` is `paths.briefs` (a folder, ending with `/`), written out in each command.

**It writes the message only.** It edits no file, changes no protected document, writes no entry and no question file,
and runs no build, no test and no gate. Its only writes are the message file `.cache/omc/describe.md`, the amend of the
commit's message and, with a brief, its removal. Its only `just` commands are `just omc git one-commit`,
`just omc record`, `just omc gate passed`, `just omc reviewed`, `just omc shots accepted`, `just decisions list` and
`just decisions show`; the gates are read, never run. An amended message or a removed brief leaves the gates' passes
and the review standing (they are compared by what changed, and the briefs are a path they keep).

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed is written out in the next one.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

## 1. The commit

```bash
(cd <root> && just omc git one-commit && git diff --cached --name-only)
```

It prints `1 commits over the merge-base` and no path. More commits, or a path staged, is `failed` with that line or
the paths: the branch is squashed and its tree committed before it is described.

**The brief**, checked here, before anything is written: `brief: none` removes nothing. Any other value must be one file
`<briefs><name>.md`, not `<briefs>README.md`, with no other `/` after `<briefs>`; a directory, `<briefs>README.md` or a
path outside `<briefs>` is `failed`, nothing written. A brief that is no longer in the tree (`test -f <root>/<brief>`
fails) removes nothing.

## 2. What it reads

The real change, not only the messages:

- `git log -1 --format=%B`: the squashed commit's message (the messages of the work, the trailers).
- The changed shots and their verdicts: the branch's yaml, the path `just omc shots path` prints
  (`<paths.questions>shots/<slug>.yaml`, `<slug>` the branch without `branch_prefix` of `omc/config.yaml`), which ▣ screens-assess wrote and the owner's review completed: per shot its id, its `bucket`
  (`unexpected`, `expected`), `verdict`, `reason`, `cause` and the owner's `review`; and whether every current row is
  accepted, `just omc shots accepted`. No yaml: no shot differs from the base, and the description says nothing of
  shots. The files of the review's rounds (`<paths.questions>screens/<date>-<slug>-<n>.md`) name the owner's
  comments.
- `git diff --stat $(git merge-base HEAD origin/<base>) HEAD` for its shape, then the diff itself for whatever the
  messages do not explain.
- The record given (`just omc record` lists the branch's records): its title, its "Context and goal", its decisions.
- The decisions applied and deferred: `just decisions list` (the log holds the branch's entries and the deferred ones
  still on `<base>`), its status `applied` or `deferred`, `just decisions show <n>` where a title is not enough. The
  branch's deferred rulings are those it recorded and deferred (not on `origin/<base>`'s log:
  `git show origin/<base>:<paths.decision_log>`).
- The gates passed: `just omc gate passed check`, `just omc gate passed verify`, `just omc reviewed`, each answer as
  the tool gives it (a pass, or a skip by the owner, said as such).
- The repository's style: `git log --no-merges --format=%s -20 origin/<base>`.

## 3. The description

Written to `.cache/omc/describe.md` (`mkdir -p .cache/omc` first):

- **Line 1**: the subject, under 72 characters, in the repository's style (a sentence in the imperative that says
  what the work does, as `Sign phones in by a QR that names its server; one session per person`); it becomes the PR's
  title.
- A blank line.
- **The body**, Markdown: what changed and why (the goal, the design's main choices, what changed, by area); the
  record's path; the decisions applied, one line each, `decision <n>: <title>`, or "no decision on this branch"; the
  branch's deferred rulings, one line, `Deferred rulings: 57, 61 — <title>; <title>` (left on `<base>` unapplied, for a
  later branch), when it has any; the gates passed, as the tools answered; the changed screenshots, from the yaml, when
  there is one: the counts per bucket, then each unexpected shot and each group of expected ones with its verdict and
  reason, and the owner's review (`accepted`, or what their comment became).
- The trailers of the old message (`Co-Authored-By:` lines), kept at its end.

Scale it to the change: a few lines for a small one, a page at most for a large one. Never claim a test, a gate or a
change the diff and the tools do not show.

## 4. The amend

```bash
(cd <root> && git commit --amend -F .cache/omc/describe.md && git log -1 --format=%s)
```

When `brief` names `<briefs><slug>.md` (checked in step 1) and the file exists in the tree, it goes in the same commit,
and nothing else with it:

```bash
(cd <root> && git rm -q -- <briefs><slug>.md && git commit --amend --no-edit && git show --stat --format='%h %s' HEAD)
```

Then step 1's command again: still one commit, nothing staged.

## The outcome

The report above the line is prose for the orchestrator: the description as written, whether the brief was removed,
the `git show --stat` line. The last line is one of:

```text
OUTCOME {"outcome": "described", "subject": "Sign phones in by a QR that names its server; one session per person"}
OUTCOME {"outcome": "failed", "reason": "3 commits over the merge-base"}
```

`subject` is the commit's subject after the amend, as `git log -1 --format=%s` prints it.

## Never

- Never push, never open a PR, never call `gh`, `glab` or a forge's API.
- Never edit a file of the tree, never remove a file but the brief named, never commit a path but the brief's
  removal.
- Never write the log or an entry, never record a decision, never write a question file.
- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`; the gates are read with
  `just omc gate passed` and `just omc reviewed`, never run.
- Never claim what the diff and the tools do not show.
- Never `git add -A`, `git add .` or `git add -f`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
