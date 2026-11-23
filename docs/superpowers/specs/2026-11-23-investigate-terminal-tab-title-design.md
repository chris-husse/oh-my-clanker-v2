# `/investigate` in v2, and `just investigate`

Date: 2026-11-23. Branch: `feature/investigate-terminal-tab-title`. Brief: `.cache/omc/brief.md` (the owner's
sentence: when `/investigate` runs, the terminal tab heading becomes a slug of the investigation topic; failing that, a
`just investigate` that defaults to prod and sets the shell up as `just design` does).

## Intent and the why

The owner wants the terminal tab of an investigation named after what is being investigated (the brief). The primer
found that v2 has no
`/investigate` at all: the one in use is the v1 omc plugin's `omc:investigate`
(`~/.claude/plugins/cache/oh-my-clanker/omc/0.1.54/skills/investigate/`), installed beside v2. The owner ruled that v2
owns it: the skill is ported here, and launched by a `just investigate` that sets the shell up properly.

## Goals

- `omc/skills/investigate/` — v1's `SKILL.md` and `worker-mission.md` ported to v2, so every v2 project gets
  `/investigate <env> <prompt>` through the install's existing skill links (`install/install.py` › `skill_links`).
- `just investigate <text…>` — always prod; pulls the primary checkout's main; derives the slug from the text; names
  the terminal tab and the herdr tab after it; launches Claude in the primary checkout seeded with
  `/investigate prod <text>`.
- Every file an investigation creates lives in `../investigations/<slug>-<YYYYMMDD-HHMMSS>/` beside the repository's
  primary checkout (`~/Projects/investigations/…` for a project at `~/Projects/<name>`).
- The WHERE of each environment comes from the project's own
  `omc/hook/investigation/investigation-context.<env>.md`, which install never ships nor touches.

## Non-goals

- No worktree, no branch, no lock of its own: an investigation is not a piece of work.
- No environment on the command line of `just investigate`: it is prod, always. Other environments (`uat`, `local`,
  whatever hook files the project defines) are reached by typing `/investigate <env> <prompt>` in a session.
- No change to the v1 plugin; it stays installed and its `/omc:investigate` stays callable, untouched.
- v2 ships no investigation-context of its own, and no example one.

## Anti-goals

- An investigation that modifies the project's code or files. Prohibited in this flow; see "Read-only".
- Files written anywhere but the investigation's folder (`/tmp`, the checkout, the home directory).
- A folder pre-filled with files the owner did not ask for.

## Constraints

- A Bash call from Claude has no tty (checked: "not a tty"), so a title escape printed from inside a skill never
  reaches the terminal. Only the launcher, before Claude starts, can set the title in every terminal; this is why the
  title belongs to `just investigate`.
- Claude Code overwrites the terminal title unless `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`
  (`omc/tools/design.py` › `launch_env`).
- Install ships every path under `omc/` except `omc/VERSION` and `omc/bin/` (`install/install.py:86`).

## Approaches

The launcher, three ways considered:

- **(a) Picked:** a new `omc/tools/investigate.py`, with the launch pieces it shares with `design.py` moved into one
  module both call. One code path for titles, herdr tabs and shells; `design.py` gets shorter. Cost: a refactor of
  `design.py`, whose tests (`test_omc_design.py`) must stay green unchanged in behaviour.
- (b) `investigate.py` copying what it needs from `design.py`: less risk now, two copies of the title and shell logic
  to keep in step.
- (c) A bash-only recipe: loses the iTerm2 title pinning, the fish hook's `__omc_desired_title`, and `SLUG_FORM`'s
  check, so the tab title — the point of the brief — works worse outside herdr.

The owner picked (a).

## The design

### 1. `just investigate <text…>`

A recipe in `omc/omc.just`, shaped like `design`: from any checkout, it resolves the primary checkout, does the same
shell pull `design` does (fetch and fast-forward of `origin/<base>` when the primary is on `<base>` with no tracked
changes; any failure left to the Python), and runs the primary's pulled justfile's `_investigate-start`, which runs
`omc/tools/investigate.py` with the text. Refused with no text. Steps, one line each on stderr as `just design` prints
them:

0. **Hook:** the primary checkout (as the recipe's shell pull left it) has
   `omc/hook/investigation/investigation-context.prod.md`, else refused at once — before the locked pull, the slug,
   the GitNexus refresh and the folder — naming the file to create and the
   `investigation-context.*.md` files that do exist.
1. **Primary checkout:** on the base branch (`base` of `omc/config.yaml`), no tracked changes, not diverged from
   `origin/<base>` — else refused (prod runs main; investigating a feature checkout would mislead). On macOS the fish
   title hook's conf.d copy is reconciled first, as `just design` does before its lock (`reconcile_fish`, a failure a
   `[warn]`). Then pulled:
   `git fetch origin <base>` and a fast-forward, under `just design`'s start lock (`design.py` › `lock`, held only
   around the pull, so an investigation and a design start never pull the primary at the same moment). Same as
   `design.py`'s `check_primary`, `lock` and `pull`.
2. **Slug:** from the text, through `design.py`'s `ask_slug` (one `claude -p` call, checked against `SLUG_FORM`).
3. **GitNexus:** the same index refresh `just design` runs (`gitnexus_steps`), never stopping the start, so `/explain`
   answers against the pulled main.
4. **Folder:** `<parent of the primary checkout>/investigations/<slug>-<YYYYMMDD-HHMMSS>/`, local time, created empty
   (`investigations/` created when missing).
5. **Environment of the session:** `launch_env` (Claude's own title off, `OMC_SLUG`, `OMC_PROVIDER`), plus
   `OMC_INVESTIGATION=<absolute folder>`.
6. **Tabs:** herdr tab renamed to the slug (`herdr.name_tab`); terminal title the slug (`exec_interactive`'s `title`,
   `title_seq` and `title_argv`, in the fixed-title mode of section 2).
7. **Session:** the user's interactive shell, in the primary checkout, running
   `claude -n <slug> [--model <orchestrator-model>] --add-dir <folder> --settings '<deny rules>' '/investigate prod <text>'`
   (under `direnv exec .` when `design.py` would). The deny rules are in "Read-only".

No worktree, no lock of its own, no `.cache/omc/brief.md`, no notification wiring (`notify.wire_worktree` writes into the
checkout).

### 2. The shared launch module

`omc/tools/launch.py` (name the builder's call) takes from `design.py` what both launchers run: `check_primary`,
`pull`, `lock`, `ask_claude`, `ask_slug`, `has_direnv`, `launch_env`, `gitnexus_steps`, `reconcile_fish`, the `step`
printer, and the tail that names the herdr tab and execs the shell. `design.py` calls it and behaves exactly as today.
`shells.startup_argv` gains a keyword for extra arguments before the seed (`--add-dir`, `--settings`).

**A fixed title.** Today only fish's launch makes the title follow the git branch: with a title command (`title_argv`,
which `design.py` always passes), its inline `__omc_refresh_title` (`omc/tools/shells.py` › `FishShell.build_invocation`)
sets `__omc_desired_title` to `git branch --show-current` at startup, before every command, on every prompt and on
every `cd`, and in iTerm2 the sourced `omc/tools/omc-title.fish` pins the tab to the branch instead. zsh and bash
already keep the title they are given (the `title_seq` printed again at every prompt, the title command run once);
sh sets it once and has no prompt hook. For `just design` the branch is the wanted title; for an investigation in the
primary checkout fish would read `main`. So `exec_interactive` gains a fixed-title mode, used by `just investigate`
and by nothing else: the title is the given text for the life of that shell, including after `claude` exits and after
a `cd`, never replaced by the branch. The work is in fish: the inline path without the branch lookup, and in iTerm2
the hook leaving that tab alone (through whatever marker or `just omc title` state fits it best: the hook already has
one switch, `OMC_FISH_TITLE_DISABLE=1`, which its `__omc_title_refresh` and `shells.py`'s `_ITERM2_HOOK_PREDICATE` both
honour; when the hook itself changes, `omc-title.fish`'s version marker and tests follow); zsh, bash and sh keep what
they do today, the given text being the slug. `just design`'s branch-following title is unchanged.

### 3. The skill, `omc/skills/investigate/`

v1's `SKILL.md` and `worker-mission.md`, ported with these changes and otherwise kept (the env lock, the echo, intake,
pre-flight, the loop, the confidence rules, halting, red flags):

- **Arguments:** `<environment> <prompt>`, as v1.
- **The gate:** `omc/hook/investigation/investigation-context.<env>.md` in the repository root (and the primary
  checkout's, when the session is in a worktree). Missing for the named environment → refuse: query nothing, list the
  `investigation-context.*.md` files that exist (the environments the project defines), and describe what the file
  must answer (v1's "env briefing" checklist). Present → it is the env briefing. v1's `.omc/skills/investigation-context`
  router is gone; environment names are the file names, no aliases.
- **`/omc:explain`** becomes v2's `/explain`.
- **Workers:** each on the `model` of the JSON `just omc models medium` prints.
- **The folder:** `$OMC_INVESTIGATION` when set. Unset (the skill typed in a session):
  `../investigations/<slug>-<YYYYMMDD-HHMMSS>/` beside the primary checkout, the slug made by the skill from the
  prompt, created the first time anything is written.
  Subfolders are created only when needed:
  - `downloads/` — files fetched from a system (logs, exports, case files);
  - `tmp/` — scratch space, in place of `/tmp`;
  - `src/` — scripts and code the agent writes to analyse data;
  - `report/` — output for the owner: written only when the owner asks for a report.

  The folder may hold anything else related to the investigation; nothing related to it goes elsewhere.
- **Reporting:** chat by default, as v1; a report when the owner asks, in `report/` (v1's
  `/tmp/omc-investigations/` and the briefing's report-location override are gone).
- **Read-only discipline:** v1's (no mutation of any environment) plus: no change to code or any file of the project;
  every write goes to the folder.

### 4. Read-only

Two layers:

- **The skill's rule** (above), the only layer when the skill is typed in an ordinary session.
- **The harness, under `just investigate`:** `--settings` with `permissions.deny` for `Edit`, `Write` and
  `NotebookEdit` on the primary checkout (`Edit(//<absolute primary>/**)` and the same for the other two), so the
  harness refuses a file-tool write there. Bash is not policed by rules; the skill forbids writing through it outside
  the folder.

### 5. `omc/hook/` and install

`install/install.py` treats `omc/hook/` exactly as `omc/bin/`: never shipped, never merged, never removed; wholly the
project's. v2 commits nothing under it. `install/test_install.py` gains the cases `omc/bin/` has (v2's `omc/hook/`
file not copied, as `test_fresh_does_not_copy_bin_or_version_from_v2`; a project's `omc/hook/` file left alone on
update, as `test_update_leaves_bin`). `RealV2.test_version_never_shipped`, which asserted that v2 tracks no `omc/bin/` file, is corrected to assert what install guarantees: v2 tracks its own gates in `omc/bin/` (since c329492) and a real install leaves `omc/bin/` out of the project.

### 6. Docs shipped to projects

`omc/skills/oh-my-clanker/agents-section.md` gains `just investigate <text>` and `/investigate <env> <prompt>`, and
where a project puts its `omc/hook/investigation/investigation-context.<env>.md`: its `omc/tools/` line names
`just investigate` beside `just design`, and its layout block gains an `omc/hook/` line beside `omc/bin/` (the
project's own, never shipped). In `omc/omc.just` the recipe and its `_investigate-start` take the `design` recipe's
one-line comment style; the comment above `omc` lists the verbs of `just omc`, which `investigate` is not, and stays as
it is.

### 7. The decision log is opt-in

Ruled by the owner in `/audit` (2026-11-24), after `just decisions renumber` refused in the rebase step with
`error: no such log: docs/decision-log.md`: "`just decisions renumber` should just be silent if the file is not
configured and it shouldn't be in this repo and it should not be configured for ANY repo through install, unless it is
explicitly enabled for a project."

- **Absent means off.** `paths.decision_log` has no default (`omc/tools/config.py` › `Paths.decision_log` becomes
  `None`): a project without the key has no decision log. Only a project that writes the key into its own
  `omc/config.yaml` has one.
- **v2 and install configure none.** `omc/config.yaml` (v2's own, and what install ships) drops the
  `decision_log:` line; a commented line in its place says how a project enables one. The test fixtures that need a
  log (`omc_fixtures.py`, `decisions/decision_log_fixtures.py`) set the key themselves. No project in use has a log file
  (checked: every `omc/config.yaml` under `~/Projects` names `docs/decision-log.md`, none has the file), so an update's
  three-way merge dropping the line from a project loses nothing.
- **Silent when off.** With no log configured, every `just decisions` verb that only reads or maintains the log
  (`renumber`, `trim`, `check`, `resolve`, `guard`, `list`, `show`, `pending`) prints nothing and exits 0, and
  `just design-integrity-check` is idle (nothing printed, exit 0), unless `paths.protected` names pages, which need a
  log: then it refuses, `paths.protected is set but no decision log is configured (paths.decision_log)`. A verb that
  writes an entry (`add-decision`, `apply-decision`, `defer`, `undefer`, `confirm`, `overrule`, `update`, `remove`)
  refuses, exit 2, `no decision log configured: set paths.decision_log in omc/config.yaml to enable one`. A log that is
  configured but whose file does not exist yet behaves as today.
- **The other readers.** `todos.py` › `deferred` returns no items with no log configured; `design.py` refuses
  `--deferred` with the same "no decision log configured" message; the vault of `decisions.configured` and of
  `links-check` (the top folder of the log) is not required when no log is configured.
- **The skills** that run `just decisions` or `/record-decision` need no change for the silent verbs. Where a skill
  would record a ruling and the log is off, `/record-decision` says the ruling is not recorded because no log is
  configured, and the flow goes on (the ruling stays in the conversation and in the record).

## Decided by the owner

Port into v2 (not a v2 launcher over the v1 plugin); `just investigate` always prod, no environment argument; it pulls
main; no worktree; the folder `../investigations/<slug>-<timestamp>/`, empty until something is written, with
`downloads/`, `tmp/`, `src/`, `report/` and anything else related; reports only on request; no code or project file
changes; the WHERE in `omc/hook/investigation/investigation-context.<env>.md`; install treats `omc/hook/` like
`omc/bin/`; the session in the primary checkout with the folder added; the skill's rule plus harness deny rules; the
launcher as a new tool over a shared module; the decision log opt-in, silent when not configured, configured by neither v2 nor install (section 7).

## Calls made in this design (the owner may overrule)

- Refuse when the primary checkout is not on main, clean and undiverged (as `just design`).
- Slug alone for the tab, the herdr tab and `claude -n`; timestamp `YYYYMMDD-HHMMSS`, local time.
- GitNexus refreshed at launch; no notification wiring.
- Workers on the `medium` role.
- The skill typed directly makes its own folder, without harness deny rules.
- A missing prod hook file refuses `just investigate` right after the recipe's shell pull, before every other step.
- The pull runs under `just design`'s start lock.
- The tab keeps the slug for the life of the investigation's shell, through a new fixed-title mode in `shells.py`
  and the fish hook; `just design`'s branch-following title stays as it is.

## Left to the builder

The shared module's name and the exact split; the wording of the ported skill; tests for `investigate.py` in the
style of `test_omc_design.py` (the folder name, the argv, the environment, the refusals).
