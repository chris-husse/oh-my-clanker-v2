---
name: oh-my-clanker
description: "Finish an omc install or resolve an omc update in this project, right after `just install <project>` of oh-my-clanker (which launches `claude /oh-my-clanker`): fresh, write the gates in omc/bin/, fill omc/config.yaml, add the pipeline section to AGENTS.md; update, resolve the merge's conflicts and kept files by intent and refresh that section; then verify and offer one commit. /oh-my-clanker <step-id> enters at that step."
disable-model-invocation: true
---

# oh-my-clanker

The owner's conversation that finishes what `just install <project>` of oh-my-clanker started. The installer has
already: copied `omc/` from oh-my-clanker's committed tree (a fresh install) or three-way merged it (an update, the
base the commit the old `omc/VERSION` named), written `omc/VERSION`, linked the skills into `.claude/skills/`,
appended `import 'omc/omc.just'` to the justfile, merged omc's SessionStart hooks into `.claude/settings.json` and
made git ignore `.cache/`. This skill never redoes any of that; `state` only verifies it. What is left is the
project's definition: its gates (`omc/bin/`), its values in `omc/config.yaml`, the pipeline section of its
`AGENTS.md`, and on an update the merge's conflicts and kept files.

**Where you are.** There is no run file. Started again, after a compaction or in a fresh session, the skill begins at
`state`, and every step that is done skips itself on what the repository shows, never on what the session remembers.
`/oh-my-clanker <step-id>` enters at that step. `state` decides the mode; each mode runs its steps in order:

- **fresh**: `state`, `read`, `gates`, `config`, `agents`, `gitnexus`, `verify`, `commit` (8 steps).
- **update**: `state`, `conflicts`, `kept`, `gates`, `agents`, `gitnexus`, `verify`, `commit` (8 steps); `gates`
  only fills a gate the project lacks, and `config` does not run: its values are the project's, and the merge kept
  them.

**Talking to the owner.** This is their conversation: every question is asked there, one at a time. Every message
opens with the skill, the mode and the step and its place, `/oh-my-clanker › fresh › gates (step 3 of 8)`. Every
option shows what it concretely produces (the command a gate would run, the line a file would get), with the
recommended one named; a long message that asks questions ends with every open question repeated as a numbered list,
one line each with the recommended default.

**Shell.** Variables do not survive between commands: begin every command with
`ROOT=$(git rev-parse --show-toplevel)` and run it in a subshell, `(cd "$ROOT" && …)`; a value a command printed is
written out in the next one.

**The installer's output.** On an update `just install` printed one line per file it could not settle: `CONFLICT
<path>` (written with diff3 markers, its three sides labelled `project`, `omc <base7>` and `omc <new7>`), `CONFLICT
<path> (cannot be merged; the project's copy is left)` (a binary file) and `KEPT <path> (<why>)` (a file deleted on
one side and changed on the other, left as the project has it, or a skill link the project deleted); and
`REMOVED .claude/skills/<name> (omc no longer ships it)` for each link to a skill omc dropped. On a fresh install over
an `omc/` the project already had (no `omc/VERSION`), it printed `REPLACED <path>` for each file of it that omc's copy
overwrote with other contents. This session does not see that output, so the installer also writes it to
`.cache/omc/install-report` (overwritten each run): `mode: fresh` or `mode: update`, `from: <base sha, or ->`,
`to: <the new sha>`, `v2: <the absolute path of the oh-my-clanker checkout that installed>`, one line each, then every
`CONFLICT`, `KEPT`, `REMOVED` and `REPLACED` line exactly as printed.
**The report** is that file when its `to:` is the sha `omc/VERSION` holds; it is read first, and its lines are the
conflict and kept list. Below, `<base>` is its `from:`, `<new>` its `to:` and `<v2>` its `v2:`. Only when it is
missing (or its `to:` is another sha) do `conflicts` and `kept` fall back to finding them as they say.

## `state` — tell a fresh install from an update, and verify the installer's work.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && cat .cache/omc/install-report 2>/dev/null || echo 'no install report'; cat omc/VERSION; git show HEAD:omc/VERSION 2>/dev/null || echo 'no committed omc/VERSION'; git status --short)
```

- No `omc/VERSION` at all: the installer did not run here. Tell the owner to run `just install <this-folder>` from
  their oh-my-clanker checkout, and stop.
- With the report: its `mode:` is the mode, `from:` the base and `to:` the new commit.
- Without it: **fresh** when HEAD holds no `omc/VERSION`; **update** when it does (the base is HEAD's
  `omc/VERSION`, the new commit the working tree's; the same sha in both is an update already committed, whose
  steps all skip).

Then verify, without redoing: `.claude/skills/` holds the links to `omc/pipeline/*`, `omc/terminals/*` and
`omc/skills/*` (`ls -l .claude/skills`), except a skill an update reported `KEPT .claude/skills/<name> (deleted
here)`; the justfile has the line `import 'omc/omc.just'`; `.claude/settings.json` holds the SessionStart hooks that
run `just omc enter --resume` and `omc/tools/herdr.py`; `git check-ignore -q .cache/x` exits 0. A missing piece is
the installer's failure, and this skill writes none of them. Running `just install` again is refused while the
install is uncommitted (the tree is dirty). Ask the owner, naming the missing piece: stop here and report it as an
installer bug, with the check that failed (recommended); or discard the uncommitted install and run it again: every
path `git status --short` lists, named to them first (tracked ones `git restore --staged --worktree -- <path>…`,
untracked ones `rm -r -- <path>…`; on an update that also discards the merge), then `just install <this-folder>`
from `<v2>` (or their oh-my-clanker checkout) and `/oh-my-clanker` again.

**Replaced files** (fresh only): each `REPLACED <path>` line of the report (without the report, each path
`git diff --name-only HEAD -- omc/` lists on a fresh install) is a file of the project's own `omc/` that omc's copy
overwrote. Show the owner, one file at a time, what they had and what omc put there (`git diff HEAD -- <path>`; their
whole old file is `git show HEAD:<path>`), and ask: keep omc's file (the default for a tool or a skill), or restore
theirs (`git restore --source=HEAD --worktree -- <path>`). `omc/config.yaml` is never restored whole (omc's keys and
comments are the shipped file's): its old values are carried into `config`, below, as the recommended values.

**Prerequisites.** The pipeline needs what the install does not bring; check each, `<branch>` the `base` of
`omc/config.yaml` (on a fresh install still the shipped `main` until `config` sets it; `config` checks again):

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git remote get-url origin; git rev-parse --verify -q refs/remotes/origin/<branch>; grep -A3 '^  protected:' omc/config.yaml; command -v dart || echo 'no dart')
```

- **The superpowers plugin**: this session's skills list `superpowers:brainstorming`, `superpowers:writing-plans`
  and `superpowers:test-driven-development`. Without them `/brainstorm`, the plan's writing and every build task
  fail at their first step. To get it: in Claude Code, `/plugin install superpowers@claude-plugins-official`
  (Anthropic's official marketplace; the plugin's README names its own marketplace too), then a new session.
- **An `origin` remote holding `origin/<branch>`**: `just design` cuts the work from it, `just omc record` and
  `just omc plan` exit 2 without it, every `just decisions` guard needs the merge-base with it, and `/audit` pushes
  there. To get it: `git remote add origin <url>`, then `git push -u origin <branch>` (a new remote) or
  `git fetch origin` (an existing one).
- **`dart`**, when `paths.protected` lists a glob: `just links-check` and `just pin-links` run in Dart, and
  `just design-integrity-check` reports `links-check: did not run` as a PROBLEM without it. To get it: the Dart SDK
  (dart.dev/get-dart), `dart` on `PATH`. With `paths.protected` empty nothing needs it.

A missing one never stops the install: name each to the owner, with what fails and how to get it, and go on; but
until each is there, no step and no last message advises the pipeline (`just design`, `/brainstorm`): the last
message names what is still missing instead. Then on to `read` (fresh) or to `conflicts` (update).

## `read` — read the repository.

Skip when both steps it serves are done: `gates` and `config` (their skip conditions below hold). It writes
nothing, so a skipped `read` is read again when a later step needs what it found.

Read what the repository already runs, never guessing: its languages and package managers (the manifests and lock
files), the build, test and lint commands of its justfile (other than omc's import), Makefile, package scripts,
`pyproject.toml`/`tox.ini`, CI workflows (`.github/workflows/`, `.gitlab-ci.yml`, others) and `scripts/`/`bin/`
folders; end-to-end tests and their runner when there are some; committed screenshots or golden files; its documents
(`docs/`, ADRs, specs, plans, a design folder) and its branch names (`git branch -a`). Show the owner, in one message,
what was found: per gate, the commands that would go into it; then on to `gates`.

## `gates` — write the project's gates in `omc/bin/`.

Skip when `omc/bin/check`, `omc/bin/build` and `omc/bin/verify` all exist and are executable (`test -x`).

Write each missing one (on an update, only those) as an executable shell script that wraps what the repository
already runs, nothing more:

```bash
#!/usr/bin/env bash
# The fast gate: lint and unit tests (what CI's lint and test jobs run). Pass or fail is the exit code.
set -euo pipefail
cd "$(dirname "$0")/../.."
<the repository's commands, one per line>
```

- `check`: the fast checks, lint and unit tests; it runs constantly, so nothing slow.
- `build`: the build without tests.
- `verify`: everything slow: the full tests, end-to-end tests when there are some.

A gate's script passes its arguments on (`"$@"`) when the command it wraps runs a part of itself from them (a test
path, a filter): `just omc gate run <gate> <ARGS…>` is then a partial run. A script never calls
`just omc gate run` or the skills `/check`, `/build`, `/verify`: they run it. Where the repository runs nothing for a
gate, ask the owner, one gate at a time, each option the exact lines it would write (the commands a near equivalent
runs, `exit 0` with a comment that the project has nothing for it, or the command they type), the recommended one
named. `chmod +x omc/bin/<gate>`. `omc/bin/<gate>.md` beside a gate only when the repository shows, or the owner
names, a known flaky step or a special red worth noting (what it looks like, what to do); none otherwise. Then on to
`config` (fresh) or `agents` (update).

## `config` — fill `omc/config.yaml` with the project's values.

Skip when the mode is update (the merge kept the project's values), or the working tree's `AGENTS.md` holds the
line `<!-- omc:begin -->` while HEAD's does not (`agents`, the step after this one, has run in this install; a
marker HEAD already held comes from an earlier install and does not count). On a fresh install over an `omc/` the project had
(`REPLACED omc/config.yaml` in the report), HEAD's file holds the project's old values: show them
(`git show HEAD:omc/config.yaml`), and for each key below the old value is the recommended option, put to the owner
beside the one this step would derive.

Only these keys change; every other key and comment stays as shipped:

- `base`: the default branch, `git symbolic-ref --short refs/remotes/origin/HEAD` without its `origin/`; without an
  origin's HEAD, ask the owner (the branches `git branch` lists as the options). Then check `origin/` and this value (`<branch>` there) again as
  `state` › Prerequisites does.
- `branch_prefix`: `feature/` unless the repository's branches show another convention (`feat/`, `<user>/`), which is
  then put to the owner as the recommended option.
- `paths.protected`: ask the owner whether some documents must change only through recorded decisions (their design,
  their specification). The options: none (the default: the decision process stays dormant), or the globs of the
  documents they name, each glob shown with the files it matches now. Globs there need `dart` (`state` ›
  Prerequisites): check it again once the list is not empty.
- `paths.screenshots` and `paths.baselines`: the globs of the committed screenshots and golden files `read` found;
  empty when there are none.
- `paths.themes`: empty, unless the owner uses theme files with rule ids (ask only when `read` found such files).
- `paths.product`: the globs of what the project ships (its app, its packages, its server), as `read` found them;
  a plan whose branch changes none of them is gated by the build gate and the omc tool tests after each task
  (`Gate: build`), its check gate run once at the end. Put to the owner with the files each glob matches now; the
  options: those globs, or empty (the default where the check gate tests only the product: the plan writer then gives
  `Gate: build` only to a branch that changes nothing the check gate tests).
- `paths.briefs`, `paths.specs`, `paths.plans`, `paths.questions`: as shipped, unless the repository already keeps
  briefs, specs, plans or question files in another folder; then ask, the shipped path and theirs as the options.
- `paths.decision_log`: absent as shipped (no decision log: `just decisions` is silent and a ruling is not recorded);
  written only when the owner explicitly enables a log for this project, at the path they give.
- `concurrency` and `silence` (both commented out as shipped; absent, every gate runs one at a time on the machine
  and is never killed for its silence): ask whether a gate (`check`, `build`, `verify`) may run more than once at a
  time on this machine, over its checkouts and worktrees (the options: one, the default, or the number the machine
  and the gate's resources allow: its ports, a database, the memory of a build), and whether a gate whose run writes
  nothing for some seconds is stuck and is to be ended by the gate itself (the options: never, the default, or the
  seconds, longer than the gate's slowest silent step). Each answer other than the default goes in as the key's
  mapping, `<gate>: <n>`.

**The vault rule.** With a log enabled, the vault is the top folder of `paths.decision_log` (the repository itself
for a log at its root); with none, no vault is required and the rule below does not apply. Every glob of `paths.protected` and `paths.themes` (its literal part, up to its first
wildcard) and `paths.questions` must lie inside it, or every `just decisions` command and `just links-check` exits 2
(`lies outside the vault`). Not any glob will do, so say so when asking: a document the owner names outside the vault
is put to them with the options of moving `paths.decision_log` (and `paths.questions`) to a top folder that holds it
too (recommended when one exists), or leaving that document unprotected.

Show the owner the diff of `omc/config.yaml` (`git diff -- omc/config.yaml`); then on to `agents`.

## `agents` — write or refresh the pipeline section of `AGENTS.md`.

The section is `omc/skills/oh-my-clanker/agents-section.md`, whole, from its `<!-- omc:begin -->` line to its
`<!-- omc:end -->` line.

Skip when `AGENTS.md` holds the markers and the text between them, the markers included, is the file's exactly.

- **Fresh, no markers yet.** Append the section to `AGENTS.md`, after a blank line (created when missing, with a first
  line `# <the project's name>: project rules`). Then the import: when `CLAUDE.md` is missing and nothing else imports
  `AGENTS.md`, write `CLAUDE.md` holding the line `@AGENTS.md`. When `CLAUDE.md` exists without `@AGENTS.md`, ask
  the owner: add the line `@AGENTS.md` to the top of `CLAUDE.md` (recommended: Claude Code then reads the section), or
  leave `CLAUDE.md` as it is. A section of `AGENTS.md` the project already has on the same subject (its own pipeline,
  its own gates) is shown to the owner with what the two say differently, and they say which stays; the section is
  never merged into it silently.
- **Update, markers present.** The section was written from the previous `agents-section.md`, which HEAD holds:
  `git show HEAD:omc/skills/oh-my-clanker/agents-section.md`. The text between the markers equal to that: replace it
  with the new file's. Different (the project edited inside the markers): merge by intent, as `conflicts` does, the
  base HEAD's file, one side the project's section and the other the new file; keep the project's edits and port
  omc's changes; two intents that exclude each other are asked, one at a time.
- **Update, no markers** (the project removed the section): ask the owner: put the new section back (recommended
  when they did not mean to drop it), or leave `AGENTS.md` without it.

Then on to `gitnexus`.

## `gitnexus` — install GitNexus at the pin of `omc/config.yaml`.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc gitnexus install)
```

GitNexus is always on; the command is a no-op when it is installed at the pin. A failure (`[failed] <why>`) is
reported to the owner with its line, and the skill goes on: it never stops the install. Then on to `verify`.

## `conflicts` — resolve each conflicted file by intent.

Skip when no file holds a conflict: the report's `CONFLICT` lines are none and the search below prints nothing (it
runs either way: a file resolved already holds no marker); without the report, only the search,

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && grep -rlE '^<<<<<<< project' -- omc/)
```

prints nothing, and no binary file was reported (a binary conflict has no markers: without the report it is found
as `kept` finds its files, below; with it, a binary file still listed is settled once the owner has chosen its side
in this session or the file equals one side).

For each conflicted file, each diff3 block in it: read the three sides, `project` (ours), `omc <base7>` (the
base) and `omc <new7>` (omc's new text), and what each changed against the base. Keep the project's change and port
omc's into it: the result does what both changes meant. Never drop a side silently. When the two intents exclude
each other (no text keeps both), ask the owner, one block at a time: the block, each side's intent, the text each
choice would leave, the one recommended. In `omc/config.yaml` a value is the project's: a block whose sides differ
only in a value keeps the project's, a key new in omc is taken. Remove every marker; then the file must hold none
(`grep -nE '^(<<<<<<<|\|\|\|\|\|\|\||=======|>>>>>>>)( |$)' <path>` prints nothing). A binary file in conflict: ask
the owner, keep the project's copy (the default) or take omc's (`git -C <v2> show <new>:<path> > <path>`; without the
report, `<v2>` as `kept` asks for it). Then on to `kept`.

## `kept` — settle each file the merge kept as the project has it.

Skip when there is none: the report's `KEPT` lines (each settled once the owner has chosen for it in this session,
or the tree already shows the choice), or, without the report, the computation below finds none.

Without the report (the fallback only), ask the owner once: paste the `KEPT` and `CONFLICT` lines `just install` printed
above this session (the default), or give the path of their oh-my-clanker checkout, from which the base (`<base>`,
HEAD's `omc/VERSION`) and the new commit (`<new>`, the working tree's) are read:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git -C <v2> diff --name-status <base> <new> -- omc/)
```

For each path it lists, omc/VERSION and omc/bin/ aside: deleted in `<new>` while the project's file differs from
`git -C <v2> show <base>:<path>` is `KEPT <path> (changed here, deleted in omc)`; changed in `<new>` while the
project has no such file but `<base>` had it is `KEPT <path> (deleted here, changed in omc)`; changed in `<new>`,
binary, and the project's copy differs from both `<base>`'s and `<new>`'s is a binary conflict (`conflicts`).

For each kept file, one at a time, ask the owner, showing what omc changed (`git -C <v2> diff <base> <new> -- <path>`,
`<v2>` from the report, or the path the fallback asked for; else the reason the line gives):

- `(changed here, deleted in omc)`: keep the project's file (the default when the project still uses it), or delete
  it as omc did.
- `(deleted here, changed in omc)`: keep it deleted (the default), or take omc's version
  (`git -C <v2> show <new>:<path> > <path>`, its mode as `<new>` has it).
- `.claude/skills/<name> (deleted here)`: keep the skill unlinked (the default), or link it again
  (`ln -s ../../omc/<pipeline|terminals|skills>/<name> .claude/skills/<name>`).

Then on to `gates`.

## `verify` — run the checks the install must pass.

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc lint; just decisions check; just design-integrity-check; just links-check)
```

then the fast gate, started detached from the worktree (a foreground `just omc gate run`, which writes its exit code
into `.cache/omc/gates/check.exit` when it ends):

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && rm -f .cache/omc/gates/check.exit && nohup just omc gate run check >/dev/null 2>&1 & echo $!)
```

and polled (`(cd "$ROOT" && sleep 5 && tail -n 40 .cache/omc/gates/check.log; cat .cache/omc/gates/check.exit)`)
until the exit file holds the code; never a file outside the worktree.

A red of this skill's own doing is fixed here and its check run again: a skill name, step or recipe `just omc lint`
reports in a file this skill wrote or merged, a marker left, a malformed `omc/config.yaml`, a gate script that does
not run (not executable, a wrong path, a command the repository does not have). A red of the project's own (its
tests or lint failing on code this skill did not touch, a tool missing on this machine) is not fixed: it is reported
to the owner, with the step and the lines. A missing prerequisite (`state` › Prerequisites) is not the project's red:
a `dart` missing with `paths.protected` set is that prerequisite, named again; with `paths.protected` empty,
`just links-check` failing for want of `dart` is no red at all. Then on to `commit`.

## `commit` — show the install's diff and offer one commit.

Skip when `git status --porcelain` prints nothing (committed already).

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && git status --short --untracked-files=all; git diff --stat)
```

Show the owner both, with the reds `verify` left, and offer one commit, its subject `omc: install <new7>` (fresh) or
`omc: update to <new7>` (update), `<new7>` the first seven characters of `omc/VERSION`. Commit only on their word:
the paths staged by name, `git add -- <path>…` (the paths `git status` listed: `omc/`, `.claude/skills/…`,
`.claude/settings.json`, the justfile, `.gitignore`, `AGENTS.md`, `CLAUDE.md`), never `git add -A` or `git add .`; the
message ends with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. A path the install did
not touch (the owner's own change) is not staged; it is named to them. Never a push. The last message: the commit (or
that nothing was committed), the reds left, and that `just design <brief-or-text>` starts the first piece of work;
while a prerequisite is missing (`state` › Prerequisites), instead each missing one, what fails without it and how to
get it, and that the pipeline waits for them.

## Never

- Never redo the installer's work (the copy, the merge, `omc/VERSION`, the links, the justfile import, the settings,
  `.gitignore`): `state` verifies it, and a missing piece is the installer's to write.
- Never drop a side of a conflict, or a kept file, silently: the owner decides what is not merged by intent.
- Never overwrite a value of `omc/config.yaml` or a file of `omc/bin/` the project already has.
- Never edit outside the project; never push; never commit without the owner's word.
- Never more than one question at a time.
- Never `git add -A`, `git add .` or `git add -f`.
