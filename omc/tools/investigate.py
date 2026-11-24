"""`just investigate <text…>`: a prod investigation of the text, in the primary checkout, one step line each on stderr
(`→ <what> … [ok]`, `[warn] <why>` or `[failed] <why>`). Always prod: the seed is `/investigate prod <text>`. First the
hook: the primary's `omc/hook/investigation/investigation-context.prod.md` (the project's own, never shipped), else
refused before anything else, naming it and the `investigation-context.*.md` files there are. On macOS the fish title
hook's conf.d copy is reconciled (a failure a `[warn]`). Then under `just design`'s start lock
(`.cache/omc/design.lock`), held only around it: the primary checked (on `<base>`, no tracked changes, not diverged
from `origin/<base>`, else refused) and pulled (`git fetch` and `git merge --ff-only`, normally a no-op after the
recipe's shell pull; a move is a `[warn]`). Out of the lock: the slug, one `claude -p` call checked against
`SLUG_FORM`; GitNexus installed and the primary's index refreshed (never stopping the start); the folder
`<parent of the primary>/investigations/<slug>-<YYYYMMDD-HHMMSS>` (local time), created empty, an existing one
refused. No worktree, no brief, no notification wiring. The launch: `launch_env` plus `OMC_INVESTIGATION=<folder>`, the
herdr tab and the terminal title the slug, fixed for the shell's life, and the interactive shell of `$SHELL` in the
primary running `claude -n <slug> [--model <orchestrator-model>] --add-dir <folder> --settings <deny rules>
'/investigate prod <text>'` (under `direnv exec .` when `direnv version` runs); the deny rules refuse Edit, Write and
NotebookEdit on the primary. A first argument `--origin=<dir>` (the recipe's `invocation_directory()`; else `$PWD`) is
taken off before the text. The pieces it shares with `just design` are launch.py's. The standard library and pyyaml
(config.py), through the justfile's `uv run`; exit 2 with `error: <why>` on every refusal."""
import datetime
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import gitnexus  # noqa: E402
import launch  # noqa: E402
import repo  # noqa: E402
import shells  # noqa: E402
from launch import (  # noqa: E402
    Refused, ask_claude, ask_slug, check_primary, gitnexus_steps, has_direnv, launch_env, lock, pull, reconcile_fish,
    say, step)

HOOK_DIR = 'omc/hook/investigation'
HOOK = 'investigation-context.{env}.md'
ENV = 'prod'
NOTHING = 'nothing to investigate: just investigate <text>'


def now():
    """The local time the folder is named after (a seam for the tests)."""
    return datetime.datetime.now()


def folder(primary, slug, now):
    """`<dirname(primary)>/investigations/<slug>-<YYYYMMDD-HHMMSS>` of the moment [now]."""
    return os.path.join(os.path.dirname(os.path.abspath(primary)), 'investigations',
                        f'{slug}-{now:%Y%m%d-%H%M%S}')


def deny_settings(primary):
    """The `--settings` JSON whose deny rules refuse Edit, Write and NotebookEdit anywhere in [primary]
    (`//<absolute path>/**`, the rules' absolute form)."""
    p = primary[1:] if primary.startswith('/') else primary
    return json.dumps({'permissions': {'deny': [f'{tool}(//{p}/**)' for tool in ('Edit', 'Write', 'NotebookEdit')]}})


def startup(slug, model, folder, primary, text, direnv):
    """The launch shell's startup argv: `claude -n <slug> [--model <model>] --add-dir <folder> --settings <deny
    rules> '/investigate prod <text>'`, under `direnv exec .` when [direnv]."""
    return shells.startup_argv(session_name=slug, model=model, seed=f'/investigate {ENV} {text}', direnv=direnv,
                               extra=('--add-dir', folder, '--settings', deny_settings(primary)))


def check_hook(primary):
    """Refused unless [primary] holds the prod hook file, naming it and the hook files there are (or none)."""
    path = os.path.join(primary, HOOK_DIR, HOOK.format(env=ENV))
    if os.path.isfile(path):
        return
    there = sorted(os.path.basename(p) for p in glob.glob(os.path.join(primary, HOOK_DIR, HOOK.format(env='*'))))
    raise Refused(f'no {HOOK_DIR}/{HOOK.format(env=ENV)}: create it, the WHERE of {ENV} '
                  f'(there are: {", ".join(there) if there else "none"}) ({primary})')


def main(argv=None):
    """The start; it execs the launch shell on success and returns (2) only on a refusal."""
    args = sys.argv[1:] if argv is None else argv
    origin = os.environ.get('PWD') or None
    if args[:1] and args[0].startswith('--origin='):
        origin, args = args[0][len('--origin='):] or origin, args[1:]
    try:
        text = ' '.join(args).strip()
        if not text:
            raise Refused(NOTHING)
        primary = gitnexus.primary_root('.')
        with step(f'hook: {HOOK_DIR}/{HOOK.format(env=ENV)}', quick=True):
            check_hook(primary)
        cfg = config.load(repo.root())
        if sys.platform == 'darwin':
            reconcile_fish()
        held = lock(primary)
        try:
            with step(f'primary: pulling origin/{cfg.base}') as s:
                check_primary(primary, cfg.base, why='just investigate reads {base}, what prod runs')
                before, after = pull(primary, cfg.base)
                s.what += f' {before[:7]} → {after[:7]}' if before != after else f' {after[:7]} (current)'
                if before != after:  # the recipe's shell pulled moments ago: a merge landed since
                    s.warn(f'{cfg.base} moved since the start\'s pull: running the code it started with')
        finally:
            held.close()
        say('→ lock: released [ok]')
        with step('slug', quick=True) as s:
            slug = ask_slug(text, ask_claude)
            s.what = f'slug: {slug}'
        gitnexus_steps(cfg, primary)
        path = folder(primary, slug, now())
        with step(f'folder: {path}', quick=True):
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                os.makedirs(path)
            except FileExistsError:
                raise Refused(f'{path} exists already: another investigation started this second') from None
            except OSError as e:
                raise Refused(f'cannot create {path}: {e.strerror}') from None
        env = launch_env(os.environ, slug, {'OMC_INVESTIGATION': path})
        argv = startup(slug, cfg.orchestrator_model, path, primary, text, has_direnv(env))
        launch.launch(env, cwd=primary, slug=slug, title=slug, argv=argv, origin=origin, fixed_title=True)
    except Refused as e:
        print(f'error: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
