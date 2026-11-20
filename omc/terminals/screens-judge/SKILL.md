---
name: screens-judge
description: "Judge every changed screenshot, committed or regenerated, against the entry, record section or commit that explains it; commit the ones that are explained or cosmetic."
---

# screens-judge

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it looks at every
screenshot the branch changed, the committed ones and those `verify` regenerated into the tree, judges each against
the change that should explain it, commits the explained and the cosmetic ones into the branch's one commit, and ends
with one `OUTCOME` line. A changed picture is not a baseline to commit: it is evidence, either of the design change
the branch made or of a feature the branch broke. A broken or unexplained shot is a finding, and what to do about it
is the orchestrator's.

**Inputs** (in the prompt, one per line). `Root:` the worktree. `record:` the record's path, `<date>-<slug>-design.md`
in `paths.specs` of `omc/config.yaml`.

**It commits shots only.** It edits no file, changes no protected document (a file matched by `paths.protected`), writes
no entry and no question file, and runs no build, no test, no render and no gate. Its only writes are the old pictures
under `.cache/shots/`, the commit message there, and the amend of the shots it judged explained or cosmetic. Its only
`just` commands are `just omc record`, `just omc git one-commit`, `just decisions list` and `just decisions show`.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a command
printed (the merge-base, an id) is written out in the next one; so are the screenshots' globs, `paths.screenshots`:
`<shots>…` is one `':(glob)<glob>'` pathspec per glob.
`<base>` is `base` of `omc/config.yaml`, the base branch (`main` as shipped), read from the file and written out
in each command; `origin/<base>` is its remote branch.

## 1. The list

With `paths.screenshots` empty there is no screenshot to judge: say "no screenshots configured" in the report, and the
outcome is `clean` with `judged: 0`, no command run.

```bash
(cd <root> && git merge-base HEAD origin/<base> && git diff --name-only $(git merge-base HEAD origin/<base>) -- <shots>… && git status --porcelain -- <shots>…)
```

The first line is the merge-base. The diff lists the shots changed since it, committed or not; the status lists the
tree's changed (` M`), new (`??`) and deleted (` D`) shots, `verify`'s. The shots to judge are the union of both
lists, each once. Both empty: say "no changed screenshot" in the report, and the outcome is `clean` with `judged: 0`.

## 2. Each shot, every one, never a sample

Shots may be batched per screen, but each picture is opened. A shot is `<shot>`, its path; `<name>` is that path with
every `/` as `.`.

- **The old picture**, from the merge-base, into `.cache/shots/`, never /tmp, out of Git LFS (`git cat-file
  --filters`; `git show` would write the LFS pointer, not the picture):

  ```bash
  (cd <root> && mkdir -p .cache/shots && git cat-file --filters <merge-base>:<shot> > .cache/shots/<name>.base.png)
  ```

  A new shot has none at the merge-base: judge the new picture alone. A deleted shot has no new one: judge the old
  picture and the page that is gone.
- **The committed picture**, for a shot the status lists whose committed picture also differs from the merge-base's
  (`git diff --quiet <merge-base> HEAD -- <path>` exits 1): an earlier run committed it, and the tree holds
  `verify`'s picture of it again:

  ```bash
  (cd <root> && git cat-file --filters HEAD:<shot> > .cache/shots/<name>.head.png)
  ```

- **The new picture**: the file in the tree (for a shot only the commit changed, the committed one).
- **Read them all** with the Read tool, which shows a PNG.
- **Two changes for a shot with a committed picture**: the tree's change against `HEAD` (what the work since that
  commit did to it, as `verify` judged) and the branch's whole change against the merge-base. Each is judged; the shot
  takes the worse judgement. A change since `HEAD` that the branch's change does not show (a button gone, a part
  restyled) is never explained by what explained the committed picture.
- **The pages**: the protected documents that describe the screen the shot shows (those that name the shot or its
  screen), where the project has them.
- **The change that should explain it**:
  - the entries of the log that name that screen or its pages (`just decisions list`, then `just decisions show <n>`;
    the log holds the branch's entries only);
  - the record given (`just omc record` lists the branch's records);
  - the branch's commits (`git log $(git merge-base HEAD origin/<base>)..HEAD`).

## 3. The judgement

Each shot is exactly one of these, written down with what it was checked against:

- **Explained**: the visible difference is what an entry, the record or a commit says changed, and the pages that
  describe the screen (where there are any) describe the new picture. Name that entry, record section or commit.
- **Broken (Critical)**: content gone, another feature's part missing, an error screen, an unusable element, text
  overflowing, clipped or overlapping, an empty area where content was.
- **Unexplained (Important)**: something moved, restyled, appeared or vanished, and no entry, record section or commit
  accounts for it ("none names it").
- **Cosmetic drift (Minor)**: a pixel shift, antialiasing, a shade, with nothing a person would see differently.

A change that cannot be placed is unexplained, never a guess. A shot whose page no longer says what the picture shows,
while the picture is the intended change, is explained in the picture and a protected-document finding on the page:
reported as such; never fixed here.

## 4. What it does with each

- **Explained** or **cosmetic drift**, when the tree holds it changed (the status listed it): `git add` that one shot
  by its path, and amend it into the branch's one commit, its message naming each shot and its judgement. First the
  branch is one commit and nothing else is staged:

  ```bash
  (cd <root> && just omc git one-commit && git diff --cached --name-only)
  ```

  It prints `1 commits over the merge-base` and no path; more commits, or a path staged, is `failed` with that line
  or the paths. Then, all such shots at once:

  ```bash
  (cd <root> && mkdir -p .cache/shots && git add -- <shot>… && { git log -1 --format=%B; printf '%s\n' '' 'Shots:' '<shot>: explained by decision <n>' '<shot>: cosmetic drift (antialiasing)'; } > .cache/shots/message && git commit --amend -F .cache/shots/message && git show --stat --format='%h %s' HEAD)
  ```

  Each line names the shot and its judgement, for example `shots/clients/detail.png: explained by decision <n>` or
  `shots/menu.png: cosmetic drift (antialiasing)`. A shot already committed on the branch and judged so needs nothing.
- **Broken** or **unexplained**: left uncommitted, as it is, and reported as a finding with its pictures' paths
  (the old ones under `.cache/shots/`, the new one in the tree). Never restored to make it go away, never deleted:
  the orchestrator restores it once its finding has its fix or its ruling. A committed shot judged so is a finding
  too, and is left as it is.
- **Never** commit a shot only to make the tree clean, and never restore one only to make it go away.

## 5. Findings

One block per broken, unexplained or cosmetic shot, numbered, in the report:

```text
FINDING 1
severity: Critical | Important | Minor
where: <shot>
checked against: <decision <n>, the record's section, a commit, or "none names it">
what: <what differs, in one or two sentences>
fix: code | protected document | ruling
```

`fix` says whose the fix is: `code` (the screen is wrong: the task terminal's); `protected document` (a page that
describes the screen must change: never fixed by editing the page, it needs a ruling); `ruling` (the change may be
wanted, and only the owner's word says so). An explained shot is listed as `<shot>: explained by <what>`, so the report
accounts for every changed shot.

## The outcome

The report above the line is prose for the orchestrator: every shot, its judgement and what it was checked against,
the commit of the explained and cosmetic ones (its `git show --stat` line), then every `FINDING` block. No broken and
no unexplained shot is `clean` (cosmetic drift alone is clean, and listed). The last line is one of:

```text
OUTCOME {"outcome": "clean", "judged": 4}
OUTCOME {"outcome": "findings", "critical": 1, "important": 1, "minor": 2, "judged": 9}
OUTCOME {"outcome": "failed", "reason": "paths staged before the shots' commit: app/menu.py"}
```

`judged` counts the shots judged; `critical`, `important` and `minor` count the `FINDING` blocks of each severity. A
shot that needs a ruling is not a `needs_user` of this terminal: it is a `FINDING` block, and `findings` carries it to
the orchestrator.

## Never

- Never judge from a sample: every changed shot is opened, the old pictures and the new.
- Never `git add` a shot it has not looked at and judged, never commit shots in bulk, never commit a broken or
  unexplained one.
- Never restore, check out or delete a shot.
- Never edit a file: no protected document, no code, no record.
- Never write the log or an entry, never record a decision, never write a question file.
- Never build, test or render: no `/check`, `/build`, `/verify`, no `just omc gate run`, no command of `omc/bin/`, no
  gate.
- Never `git add -A`, `git add .` or `git add -f`.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
