---
name: rebase
description: "Rebase the branch onto origin/<base> through just omc rebase, settle the log's conflicts with the decision tool, renumber, trim and check the log, commit; never builds or tests."
---

# rebase

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it rebases the branch onto
`origin/<base>` through `just omc rebase`, settles the log's conflicts at each stop with `just decisions resolve`, brings
the log in line with `<base>` once the rebase is done, commits what that changed, and ends with one `OUTCOME` line, which
is its whole answer. The log (`paths.decision_log` of `omc/config.yaml`), the entry and the rebase step are
`omc/tools/decisions/FORMAT.md` ("Two branches at once" is the procedure this terminal follows); the tool's contract is
the docstrings of `omc/tools/rebase.py`, and its answers are below.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `squash: yes` or `squash: no`: whether the branch is
folded into one commit first (`just omc rebase --squash`), and so how the log's changes are committed. `phase: design`
or `phase: audit`: the phase that rebases; it frames the report and changes no step. `answer: <the ruled option>` or
`answer: none`: the owner's ruling on the `needs_user` an earlier run returned at a stop (step 3), one of its options
in its words; `none` on a first run.

**It builds and tests nothing, in any phase.** No `/check`, `/build`, `/verify`, no `just omc gate run` and no gate: in
/design nothing builds or tests before implementation, and in /audit the check after a rebase is the orchestrator's. The
log is written only through `just decisions`; this terminal runs `resolve`, `renumber`, `trim` and `check` and nothing
else of it.

**The old merge-base is the tool's.** `just omc rebase` writes it to `.cache/omc/impact` before `git rebase` starts
and never overwrites a mark that is there, so the mark is the oldest merge-base whose impact is still to be read, and
the JSON's `old_base` is the same value. `just omc impact` prints it; `just omc impact --done` is the orchestrator's,
once that reading is handled, never this terminal's.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed (`<old base>`, `<new base>`, a path) is written out in the next one. A commit stages its paths by
name, `git add -- <path>…`, and its message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
Every `git rebase --continue` runs as `GIT_EDITOR=true git rebase --continue`, so that it never waits in an editor.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

## 1. A rebase already paused

A session that ended at a stop leaves the rebase paused, and the tool refuses to start another. So first:

```bash
(cd <root> && { [ -e "$(git rev-parse --git-path rebase-merge)" ] || [ -e "$(git rev-parse --git-path rebase-apply)" ]; } && echo 'rebase paused' || echo 'no rebase'; git diff --name-only --diff-filter=U)
```

`no rebase`: step 2. `rebase paused` and no path after it (the stop was settled, its files staged):
`GIT_EDITOR=true git rebase --continue`, then step 3 with the paths of its next stop when it stops again, else step 4.
`rebase paused` with paths: those are the stop's conflicted files. With an `answer`, the stop is the one its
`needs_user` named: apply the ruled option to the files it named (the log only ever through `just decisions`), stage
them, `git add -- <path>…`, and go on at step 3's continue (item 2) once no path is left unmerged. Without one: step 3.

## 2. The rebase

```bash
(cd <root> && just omc rebase)
```

With `squash: yes`, `just omc rebase --squash`. It prints one JSON line and exits:

- **0**, `"rebased": false`: the branch is on `origin/<base>` already (squashed when asked). Step 4 still runs: its
  commands change nothing when nothing moved, and they settle a rebase that an earlier session finished before its
  log was brought in line. The outcome is `current`.
- **0**, `"rebased": true`: write down its `old_base` and `new_base`; step 4.
- **3**, `"ok": false`: the rebase stopped and is paused; its `conflicts` are the stop's conflicted files; step 3.
- **2**, `error: …` on stderr. Uncommitted changes or unmerged paths (the paths are listed): `needs_user` with those
  paths and the error quoted, the options being to commit them or to leave the rebase for now; this terminal neither
  commits nor discards them. Any other refusal (a failed fetch, a merge or cherry-pick in progress, nothing to squash):
  `failed`, the error line its reason.

## 3. A stop

At each stop, its conflicted files (step 1's paths, or the JSON's `conflicts`, or after a `--continue`
`git diff --name-only --diff-filter=U`):

1. **The log among them** (`paths.decision_log`): `just decisions resolve`. It settles the log entry by entry from git's
   three sides and stages it, printing `resolved: …` and `decision <n> dropped: …` per entry a trim keeps out. It
   refuses an entry both sides changed differently: that is a ruling, `needs_user` below.
2. **The log was the stop's only conflicted file**: `GIT_EDITOR=true git rebase --continue`. It stops again: this
   step again, with the new stop's files. It ends the rebase: step 4.
3. **Any other conflicted file**: the terminal merges it itself, keeping both sides. It reads each file's conflict
   (`git diff -- <path>`, the commit being replayed in `git log -1 REBASE_HEAD`, and `<base>`'s commits since the old
   base) and writes the file with `<base>`'s change and the branch's both in it, the branch's ported into the form `<base>`
   gave the file (a renamed file, a moved config, a rewritten section: the branch's addition carried into the new
   place); a lock file (`uv.lock`, `package-lock.json`, `pubspec.lock`) is taken from `<base>` and regenerated over the
   merged manifest (`uv lock`, `npm install --package-lock-only`, `dart pub get`). Then it stages the file and goes on
   (step 1). It never returns an option that drops a side, merges by hand or aborts. Only two sides whose intents
   exclude each other (`<base>` removes what the branch builds on, and no merge keeps both) are `needs_user`: that one
   contradiction, each intent with what it produces, and the one it would pick. **An entry `resolve` refused**:
   `needs_user`, the tool's message quoted. For it, the options say what each actually allows, since the log is never
   edited by hand: for example the entry put right on `<base>` first, after which the paused rebase is abandoned by the
   owner's own `git rebase --abort` and a later run starts it again. The rebase is left paused (the log staged when
   `resolve` settled it), never aborted, never skipped: the next run, given the ruled option as its `answer`, applies it
   and continues (step 1).
4. **A `--continue` git refuses without a conflict** (a commit the resolution left empty, a hook that fails): its
   message quoted, `needs_user`; never `--skip`.

## 4. The log after the rebase

The rebase is done (step 1's command prints `no rebase`). First what the tree holds now, `<tree before>`, which
matters only after a rebase this terminal continued (step 1 or step 3):

```bash
(cd <root> && git status --porcelain)
```

On the path from step 2 it prints nothing (the tool refused a dirty tree). Then the log, against `<base>`:

```bash
(cd <root> && just decisions renumber && just decisions trim && just decisions check)
```

`renumber` gives the branch's own entries the ids from `<base>`'s `Next` on and rewrites every reference to them that
the branch wrote, in any file (`decision <old> is now <new>`, `decision <n> dropped: applied on main and trimmed
there`, `<k> entries renumbered`). `trim` drops the entries applied at the merge-base (`<k> entries trimmed`), so the
log holds the branch's entries and no other. `check` is the log's own check, not the gate, and prints `OK` or one
`PROBLEM:` line per problem.

- **`renumber`, `trim` or `check` refuses** (exit 2, `error: …`; `renumber` on a base whose references do not
  validate lists every bad reference): `needs_user`, the message quoted. A bad base is fixed, never worked around,
  and this terminal fixes none of it.
- **`check` red** (`PROBLEM:` lines): `needs_user`, the lines quoted. A rebase kind (`duplicate-id`, `id-on-main`,
  `trimmed-on-main`) points at the rebase step (`resolve`, `renumber`, `trim`) and the report says so; any other kind
  is a problem of the log itself.
- Never an entry merged, dropped, moved or renumbered by hand, never the log edited to pass.

Then what they changed:

```bash
(cd <root> && git status --porcelain)
```

The log step's paths are the lines `<tree before>` did not hold (the log, and each file whose references `renumber`
rewrote), by name. None: no commit. Otherwise:

- `squash: no`: one commit, `git add -- <path>… && git commit -m "Decisions renumbered after the rebase" -m
  "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- <path>…`.
- `squash: yes`: amended into the one commit, `git add -- <path>… && git commit --amend --no-edit -- <path>…`.

A line `<tree before>` held already is not this terminal's: it stays out of the commit and is neither committed nor
discarded; after the commit, `needs_user` with those paths.

The outcome's bases. After a rebase that step 2 ran to its end, its `old_base` and `new_base`. After a rebase this
terminal continued (from step 1 or step 3), the old merge-base is the mark and the new one the merge-base now:

```bash
(cd <root> && just omc impact; git merge-base HEAD origin/<base>)
```

`just omc impact` exiting 1 (no mark: a rebase the tool did not start) leaves the old merge-base unknown. The
likely one is `git merge-base ORIG_HEAD origin/<base>` (the branch's tip before the rebase): `needs_user` once the log
step is committed, its options written with the literal shas, `old_base <sha>, new_base <sha>` (picked) and
`read no impact`, so that the orchestrator can run the impact reading on them without another rebase.

## The outcome

The report above the line is prose for the orchestrator: whether the branch was squashed, each stop and what
`resolve` printed, what `renumber` and `trim` printed, the commit (its hash and subject) or that there was none. The
last line is one of:

```text
OUTCOME {"outcome": "rebased", "old_base": "<old merge-base, full sha>", "new_base": "<new merge-base, full sha>"}
OUTCOME {"outcome": "current"}
OUTCOME {"outcome": "needs_user", "question": "…", "options": ["…", "…"], "picked": "…"}
OUTCOME {"outcome": "failed", "reason": "git fetch origin <base>: could not resolve host"}
```

## Never

- Never build or test: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate, in any phase.
- Never `git rebase --abort` or `git rebase --skip`; a stop that is not the log's is left paused.
- Never resolve the log but through `just decisions resolve`; every other conflicted file is merged here, both sides
  kept (step 3), never put to the owner as options to drop a side, to merge by hand or to abort.
- Never merge, drop, move or renumber an entry by hand, never edit the log, never record a decision, never write a
  question file: what needs a ruling is `needs_user`.
- Never edit a protected document (a file matched by `paths.protected`).
- Never `just omc impact --done`: the impact reading is not this terminal's.
- Never start an agent or a skill that starts one or that talks to the owner: the `OUTCOME` line is the whole answer.
- Never push.
- Never `git add -A`, `git add .` or `git add -f`.
