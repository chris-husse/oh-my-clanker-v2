# `/investigate` in v2, and `just investigate` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Gate: check

**Goal:** Port v1's `/omc:investigate` into v2 as `/investigate`, launched by `just investigate <text…>`, which
always investigates prod, pulls main, names the tab after the slug and keeps every file in
`../investigations/<slug>-<YYYYMMDD-HHMMSS>/`.

**Architecture:** The launch pieces of `omc/tools/design.py` move into a shared `omc/tools/launch.py`. A new
`omc/tools/investigate.py` runs over that module, behind an `investigate` recipe in `omc/omc.just`. `shells.py` gains
extra Claude arguments and a fixed-title mode for fish. The skill lives in `omc/skills/investigate/`, and install
treats `omc/hook/` like `omc/bin/`.

**Tech Stack:** Python 3 (standard library and pyyaml through `uv run`), `unittest` scripts run by `just test`, just,
fish/zsh/bash/sh init snippets, Claude Code CLI flags (`--add-dir`, `--settings`).

**Spec:** `docs/superpowers/specs/2026-11-23-investigate-terminal-tab-title-design.md` (the record). Where this plan and
the record disagree, the record wins.

## Global Constraints

- `just investigate` takes no environment: always prod. The seed is exactly `/investigate prod <text>`.
- The folder is `<parent of the primary checkout>/investigations/<slug>-<YYYYMMDD-HHMMSS>/`, in local time, and is
  created empty.
- No worktree, no `.cache/omc/brief.md`, no `notify.wire_worktree`, and no lock of its own: the pull runs under
  `.cache/omc/design.lock`.
- The hook file is `omc/hook/investigation/investigation-context.<env>.md`. v2 commits nothing under `omc/hook/`.
- `just design` behaves exactly as today. Every existing case of `test_omc_design.py` and `test_omc_shells.py` stays
  green, unchanged.
- The deny rules are `Edit(//<abs primary>/**)`, `Write(//<abs primary>/**)` and `NotebookEdit(//<abs primary>/**)`.
- The session environment is `launch_env` plus `OMC_INVESTIGATION=<absolute folder>`.

## Review Focus

- **A prompt with shell metacharacters** (quotes, `$`, `;`) has to reach Claude as one seed argument, unexpanded, in
  every shell. Pinned in Task 4 (`test_the_seed_survives_quotes`).
- **A primary checkout path with spaces** has to produce deny rules and an `--add-dir` that stay one argument each.
  Pinned in Task 4 (`test_a_primary_path_with_spaces`).
- **Two investigations started in the same second with the same slug** must not share a folder. A folder that already
  exists is refused (`os.makedirs(exist_ok=False)`) and never reused. Pinned in Task 4
  (`test_an_existing_folder_is_refused`).
- **A `cd` or the return to the prompt after `claude` exits** must keep the fish title as the slug, not the branch.
  Pinned in Task 3 (`test_fixed_title_has_no_branch_lookup`).
- **A missing `investigations/` parent** is created, and the folder stays empty after launch. Pinned in Task 4
  (`test_the_folder_is_created_empty`).

---

### Task 1: `omc/hook/` is the project's, like `omc/bin/`

Complexity: simple

**Files:**
- Modify: `install/install.py:85-86` (`shipped`), plus the docstring at lines 3 and 17, which name `omc/bin/`
- Test: `install/test_install.py`

**Interfaces:**
- Produces: `shipped(path) -> bool` is False for `omc/VERSION`, for `omc/bin/…` and for `omc/hook/…`.

- [x] **Step 1: Write the failing tests** in `install/test_install.py`, beside the `omc/bin/` cases:
  - `test_fresh_does_not_copy_hook_from_v2`: v2 commits `omc/hook/investigation/investigation-context.prod.md`; after a
    fresh install the project has no `omc/hook`.
  - `test_update_leaves_hook`: the project has its own `omc/hook/investigation/investigation-context.prod.md`; after an
    update its bytes are unchanged, and nothing is listed as `KEPT` or `REMOVED` for it.

  Mirror `test_fresh_does_not_copy_bin_or_version_from_v2` and `test_update_leaves_bin`.
- [x] **Step 2:** Run `UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I install/test_install.py`. Expected:
  both new tests FAIL.
- [x] **Step 3:** In `shipped`, also exclude `path.startswith('omc/hook/')`. Name `omc/hook/` beside `omc/bin/` in the
  module docstring.
- [x] **Step 4:** Run the same command. Expected: every test passes.
- [x] **Step 5:** Commit `install/install.py` and `install/test_install.py` by name.

### Task 2: the shared launch module

Complexity: high

**Files:**
- Create: `omc/tools/launch.py`
- Modify: `omc/tools/design.py` (it imports from `launch`; its docstring keeps the design-specific story)
- Test: `omc/tools/test_omc_design.py` (unchanged, must stay green), and new `omc/tools/test_omc_launch.py`

**Interfaces:**
- Produces, in `launch.py`, moved from `design.py` with the same behaviour:
  - `Refused`, `LOCK`, `GITNEXUS_LOCK`, `PROVIDER`, `TITLE_OFF`, `SLUG_FORM`, `PROMPT`, `step` (the class),
    `say(text, end='\n')`.
  - `check_primary(primary, base, why='just design cuts its worktrees from {base}')`. The refusal text for "not on
    base" is formatted from `why`; everything else is unchanged.
  - `pull(primary, base) -> (before, after)`, `lock(primary)`, `ask_claude(prompt)`, `ask_slug(text, ask)`,
    `has_direnv(env)`, `launch_env(env, slug, extra=None)` (extra variables merged last), `gitnexus_steps(cfg,
    primary)`, `reconcile_fish()`.
  - `launch(env, *, cwd, slug, title, argv, origin, fixed_title=False) -> None`. It names the herdr tab with its step
    line, prints the `→ session: …` line, replaces `os.environ` and calls `shells.detect_shell(env).exec_interactive(…,
    fixed_title=fixed_title)`. It raises `Refused` on `OSError`. This is `design.py`'s `main` tail from
    `herdr.name_tab` on.
- `design.py` keeps `KEBAB`, `DEFERRED_IDS`, `NOTHING`, `BRIEF`, `SESSION`, `slug_of`, `deferred_ids`,
  `deferred_brief`, `worktree`, `startup` and `main`. Module-level names that tests or the recipe reach through
  `design.<name>` stay importable from `design` (re-export them).

- [x] **Step 1: Write `test_omc_launch.py`.**
  - `test_check_primary_names_the_caller`: `check_primary(primary, 'main', why='just investigate reads {base}')` on an
    off-base primary refuses with a message containing `just investigate reads main`.
  - `test_launch_env_merges_extra`: `launch_env({'PATH': '/x'}, 's', {'OMC_INVESTIGATION': '/f'})` holds
    `OMC_INVESTIGATION='/f'`, `OMC_SLUG='s'` and `CLAUDE_CODE_DISABLE_TERMINAL_TITLE='1'`.

  Use `omc_fixtures.Repo` as `test_omc_design.py` does.
- [x] **Step 2:** Run `UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache
  omc/tools/test_omc_launch.py`. Expected: FAIL, no module `launch`.
- [x] **Step 3:** Create `launch.py` by moving the code, and make `design.py` call it. Before writing the import list,
  run `/explain` on what imports `design` (`test_omc_design.py`, `omc.py`, `todos.py`, …), so that every
  `design.<name>` they use still resolves.
- [x] **Step 4:** Run `test_omc_launch.py` and `test_omc_design.py`. Expected: both pass, and `test_omc_design.py` is
  unedited.
- [x] **Step 5:** Commit `omc/tools/launch.py`, `omc/tools/design.py` and `omc/tools/test_omc_launch.py` by name.

### Task 3: extra Claude arguments and a fixed fish title

Complexity: medium

**Files:**
- Modify: `omc/tools/shells.py` (`startup_argv`, `Shell.exec_interactive`, `Shell.build_invocation` and every
  subclass's signature, `FishShell.build_invocation`)
- Test: `omc/tools/test_omc_shells.py`

**Interfaces:**
- Produces:
  - `startup_argv(*, session_name, model, seed, effort='', direnv=False, extra=()) -> list[str]`. `extra` goes after
    `--effort` and before the seed.
  - `build_invocation(…, fixed_title: bool = False)` and `exec_interactive(…, fixed_title: bool = False)` on every
    shell.
  - With `fixed_title=True`, `FishShell` drops the `git branch --show-current` lookup from the inline
    `__omc_refresh_title`, so the title stays the given text. It also sets `OMC_FISH_TITLE_DISABLE=1` in the launched
    shell before the `_ITERM2_HOOK_PREDICATE` test, so the iTerm2 hook leaves the tab alone and the inline path runs
    there too. zsh, bash and sh ignore the flag; they already keep the given title. `omc-title.fish` is not edited.

- [x] **Step 1: Write the failing tests.**
  - `test_startup_argv_puts_extra_before_the_seed`: `startup_argv(session_name='s', model='m', seed='/x',
    extra=('--add-dir', '/f'))` equals `['claude', '-n', 's', '--model', 'm', '--add-dir', '/f', '/x']`.
  - `test_fixed_title_has_no_branch_lookup`: fish's `build_invocation(…, fixed_title=True)` text has no
    `git branch --show-current`, does contain `set -g __omc_desired_title <title>`, and sets `OMC_FISH_TITLE_DISABLE`
    to 1 before the `if` of the predicate.
  - `test_default_fish_title_still_follows_the_branch`: without the flag, the text is byte-identical to today's
    (compare against a call with the old signature's arguments).
- [x] **Step 2:** Run `UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache
  omc/tools/test_omc_shells.py`. Expected: the new tests FAIL.
- [x] **Step 3:** Implement the signatures above.
- [x] **Step 4:** Run `test_omc_shells.py`, `test_omc_design.py` and `test_omc_fish_title.py`. Expected: all pass.
- [x] **Step 5:** Commit `omc/tools/shells.py` and `omc/tools/test_omc_shells.py` by name.

### Task 4: `investigate.py` and the `just investigate` recipe

Complexity: high

**Files:**
- Create: `omc/tools/investigate.py`, `omc/tools/test_omc_investigate.py`
- Modify: `omc/omc.just` (recipes `investigate` and `_investigate-start`, after `_design-start`)

**Interfaces:**
- Consumes: Task 2's `launch` module and Task 3's `startup_argv(extra=…)` and `fixed_title`.
- Produces:
  - `HOOK_DIR = 'omc/hook/investigation'`, `HOOK = 'investigation-context.{env}.md'`, `ENV = 'prod'`.
  - `folder(primary, slug, now) -> str`, which returns
    `<dirname(primary)>/investigations/<slug>-<now:%Y%m%d-%H%M%S>`.
  - `deny_settings(primary) -> str`: JSON `{"permissions": {"deny": ["Edit(//<p>/**)", "Write(//<p>/**)",
    "NotebookEdit(//<p>/**)"]}}`, where `<p>` is `primary` without its leading `/`.
  - `startup(slug, model, folder, primary, text, direnv) -> list[str]`, built from `startup_argv` with
    `extra=('--add-dir', folder, '--settings', deny_settings(primary))` and the seed `/investigate prod <text>`.
  - `main(argv=None) -> int`.
- Steps of `main`, each with its step line:
  1. Take the `--origin=` argument off.
  2. With no text, refuse: `nothing to investigate: just investigate <text>`.
  3. The hook check: refuse when `<primary>/omc/hook/investigation/investigation-context.prod.md` is missing, naming
     that path and the `investigation-context.*.md` files that exist (or `none`).
  4. `reconcile_fish` on macOS.
  5. Under `lock`: `check_primary(…, why='just investigate reads {base}, what prod runs')` and `pull`.
  6. The slug, via `ask_slug(text, ask_claude)`.
  7. `gitnexus_steps`.
  8. `os.makedirs(investigations, exist_ok=True)`, then `os.makedirs(folder)`. A folder that already exists is
     refused.
  9. `launch_env(os.environ, slug, {'OMC_INVESTIGATION': folder})`.
  10. `launch(…, cwd=primary, title=slug, fixed_title=True)`.
- Recipe `investigate *ARGS`: the `design` recipe's shell pull, verbatim, then exec of the primary's justfile
  `_investigate-start --origin=<invocation_directory()> "$@"`. It has no brief-path rewrite, and a one-line comment in
  `design`'s style.

- [x] **Step 1: Write `test_omc_investigate.py`** on `test_omc_design.py`'s fixture: fake `claude`, the fake shells,
  `Repo`, and the recipe cases on a copy of `omc.just`. The cases:
  - `test_no_text_is_refused`: exit 2 and the `nothing to investigate` line.
  - `test_a_missing_prod_hook_is_refused_first`: with no hook file there is exit 2, the error names
    `omc/hook/investigation/investigation-context.prod.md`, no lock file is created and the fake `claude` log is empty.
  - `test_the_folder_is_created_empty`: `<tmp parent>/investigations/<slug>-<14 digits with a dash>` exists and
    `os.listdir` is `[]`.
  - `test_an_existing_folder_is_refused`: `folder` is pre-created with a fixed `now` (patch `investigate.now`), so the
    run exits 2.
  - `test_the_startup_runs_claude_on_investigate_prod`: the shell log holds `claude -n <slug> --model <m> --add-dir
    <folder> --settings <json> '/investigate prod <text>'`.
  - `test_the_seed_survives_quotes`: the text `why does "x" cost $5; really` arrives as one argument, byte-equal.
  - `test_a_primary_path_with_spaces`: the fixture lives under a directory with a space, `deny_settings` parses as
    JSON, and the `--add-dir` value is one argument.
  - `test_the_launch_env`: `OMC_INVESTIGATION`, `OMC_SLUG` and `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1` are set.
  - `test_the_title_is_the_slug_and_fixed`: the fish init has the slug as its title and no branch lookup.
  - `test_inside_herdr_the_tab_is_the_slug`.
  - `test_no_worktree_no_brief_no_notification`: `wt.log` is absent, there is no `.cache/omc/brief.md`, and the
    primary's `settings.local.json` is untouched.
  - `test_an_off_base_primary_is_refused`: the message names `just investigate`.
  - `test_the_recipe_runs_the_pulled_justfile`.
- [x] **Step 2:** Run `UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache
  omc/tools/test_omc_investigate.py`. Expected: FAIL.
- [x] **Step 3:** Implement `investigate.py` and the two recipes as given in Interfaces.
- [x] **Step 4:** Run `test_omc_investigate.py` and `test_omc_design.py`. Expected: both pass.
- [x] **Step 5:** Commit `omc/tools/investigate.py`, `omc/tools/test_omc_investigate.py` and `omc/omc.just` by name.

### Task 5: the `/investigate` skill and the shipped docs

Complexity: medium

**Files:**
- Create: `omc/skills/investigate/SKILL.md` and `omc/skills/investigate/worker-mission.md`, ported from
  `~/.claude/plugins/cache/oh-my-clanker/omc/0.1.54/skills/investigate/`
- Modify: `omc/skills/oh-my-clanker/agents-section.md`
- Create: `.claude/skills/investigate`, a symlink to `../../omc/skills/investigate`, as install makes for v2 itself

**Interfaces:**
- Consumes: Task 4's `OMC_INVESTIGATION` and hook path.

- [x] **Step 1:** Port `SKILL.md` with frontmatter `name: investigate` and a description that names `/investigate
  <environment> <prompt>` and `omc/hook/investigation/investigation-context.<env>.md`. Apply the record's §3 changes,
  and keep everything else, including v1's execution-model override:
  - The gate reads `omc/hook/investigation/investigation-context.<env>.md` (and the primary checkout's, when the
    session is in a worktree). When it is missing, the skill refuses, lists the `investigation-context.*.md` files and
    gives the briefing checklist. The router and aliases are dropped.
  - `/omc:explain` becomes `/explain`.
  - Workers run on the `model` from `just omc models medium`.
  - The folder is `$OMC_INVESTIGATION`. When that is unset, the folder is
    `../investigations/<slug>-<YYYYMMDD-HHMMSS>/` beside the primary checkout, created on first write.
  - Subfolders `downloads/`, `tmp/`, `src/` and `report/` are created only when needed.
  - Reports go in `report/` only on request; `/tmp/omc-investigations/` and the report-location override are gone.
  - Read-only discipline: no change to code or project files, and every write goes in the folder, including Bash
    writes.
- [x] **Step 2:** Port `worker-mission.md`, adding to FORBIDDEN: writing any file outside the investigation folder
  (given to the worker as `<folder>`).
- [x] **Step 3:** In `agents-section.md`, name `just investigate <text>` beside `just design` on the `omc/tools/`
  line, and `/investigate <env> <prompt>` with its hook path. Add an `omc/hook/` line beside `omc/bin/` in the layout
  block (the project's own, never shipped).
- [x] **Step 4:** Run `UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I install/test_install.py` and
  `just omc lint` (when it covers skills). Expected: pass. Check that `grep -n "omc:explain\|/tmp/omc-investigations\|
  \.omc/skills/investigation-context" omc/skills/investigate/*.md` prints nothing.
- [x] **Step 5:** Commit the new skill files, `agents-section.md` and the `.claude/skills/investigate` link by name.
