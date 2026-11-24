"""`just design <brief-or-text>`, the omc/ pipeline's one shell command: the primary, the slug, the lock, the pull,
GitNexus, the worktree, the session, one step line each on stderr (`→ <what> … [ok]`, `[warn] <why>` or
`[failed] <why>`). The primary checkout (the one `git rev-parse --git-common-dir` belongs to) must be on `<base>`, with
no tracked changes and not diverged from `origin/<base>`, or the start is refused before anything is written. The slug
is made outside the lock: a brief (an existing `*.md` file, `<name>.md` of `paths.briefs`) gives its name; free text gives one
`claude -p` call, its answer checked (kebab-case, three to six words) and asked once more, then refused. A second
start waits in line on the primary's `.cache/omc/design.lock` and never fails. The pull is the `design` recipe's, in
its shell before any Python: this process is already the pulled `design.py`, run from the primary's pulled justfile
(`_design-start`), and never re-execs. The lock covers the primary's check again, a pull (`git fetch` and
`git merge --ff-only` of `origin/<base>`) that is normally a no-op (a move it finds, a merge landed since the recipe's
pull, is one `[warn]` and the start goes on with the code it started with), and the worktree cut. After its release,
the GitNexus install and the refresh of the primary's index at the pulled tip, under their own lock taken without
waiting (held by another start: left to it), so that no start waits in line behind a refresh. Neither GitNexus step
refuses the start: a failure is
`[failed] <why>` and the line `GitNexus is stale: /explain answers from <sha>`. `feature/<slug>` is cut from
`origin/<base>` with worktrunk, or entered again when the branch exists; after the release the context goes to
`<worktree>/.cache/omc/brief.md`. Base and branch prefix come from omc/config.yaml; Claude only, no provider option.
Then the launch as omc's: on macOS the fish title hook's conf.d copy is reconciled before the lock (`fish_integration`
`reconcile`, a failure a `[warn]`); after the brief, the notification channel is wired in the worktree
(`notify.wire_worktree`, `preferredNotifChannel: auto`, never blocking); the environment takes the `uv` venv out
(`VIRTUAL_ENV` and its `bin` on `PATH`) and sets `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`, `OMC_SLUG=<slug>` and
`OMC_PROVIDER=claude` (the slug's `claude -p` gets the first only); then the process becomes the interactive shell of
`$SHELL`'s basename (fish, zsh, bash, else sh, `shells.py`) in the worktree, titled `<branch>` (inside herdr its tab
labelled `<slug>` first, `herdr.name_tab`, a failure a `[warn]`), its herdr exit report
the origin, which runs `claude -n <slug> [--model <orchestrator-model>] '/brainstorm .cache/omc/brief.md'`, under
`direnv exec .` when `direnv version` runs. A first argument `--origin=<dir>` (the `design` recipe's
`invocation_directory()`, handed on through `_design-start`; else `$PWD`) is taken off before the brief's.
`--deferred <ids>` (a later branch picking up rulings left deferred on the base, `just omc todos`) takes the
brief from the deferred entries of `origin/<base>`'s log (`# Deferred rulings <ids>`, then each entry's title, Context
and Decision; an id unknown there or not deferred, or no log configured, is refused before the lock), its slug asked of `claude -p` as for
free text; then the start goes on as with a brief. The pieces `just investigate` shares (the check, the pull, the lock,
the slug's `claude -p`, GitNexus, the environment, the launch tail) are launch.py's, imported here. The standard library
and pyyaml (config.py), through the justfile's `uv run`; exit 2 with `error: <why>` on every refusal."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import gitnexus  # noqa: E402
import launch  # noqa: E402
import notify  # noqa: E402
import repo  # noqa: E402
import shells  # noqa: E402
from launch import (  # noqa: E402,F401 (re-exported: design.<name> as before the move)
    GITNEXUS_LOCK, LOCK, PROMPT, PROVIDER, SLUG_FORM, TITLE_OFF, Refused, ask_claude, ask_slug, check_primary,
    gitnexus_steps, has_direnv, launch_env, lock, pull, reconcile_fish, say, step)

BRIEF = os.path.join('.cache', 'omc', 'brief.md')
SESSION = '/brainstorm .cache/omc/brief.md'
KEBAB = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
DEFERRED_IDS = re.compile(r'^\d+(,\d+)*$')
NOTHING = 'nothing to start: `just design <brief-or-text>`, a brief ({briefs}<name>.md) or a sentence'


def slug_of(args, ask, briefs=config.Paths().briefs):
    """(the slug, the context text) of the command's arguments: one argument naming an existing `*.md` file gives its
    base name (kebab-case, else refused) and its text; anything else is free text joined by spaces, its slug the
    answer of [ask] (a callable of the prompt), asked once more when its form is wrong, then refused; no argument is
    refused, naming [briefs], the folder of the briefs."""
    if not args:
        raise Refused(NOTHING.format(briefs=briefs))
    if len(args) == 1 and args[0].endswith('.md') and os.path.isfile(args[0]):
        name = os.path.basename(args[0])[:-len('.md')]
        if not KEBAB.match(name):
            raise Refused(f'the brief\'s name `{name}` is not kebab-case (lowercase words and numbers joined by -)')
        try:
            with open(args[0], encoding='utf-8') as f:
                return name, f.read()
        except (OSError, UnicodeDecodeError) as e:
            raise Refused(f'cannot read {args[0]}: {e}') from None
    text = ' '.join(args).strip()
    if not text:
        raise Refused('nothing to start: the text is empty')
    return ask_slug(text, ask), text + '\n'


def deferred_ids(args):
    """The ids of `--deferred <ids>` or `--deferred=<ids>` (comma-separated numbers, nothing after them), or None
    when [args] does not start with `--deferred`."""
    if not args or not (args[0] == '--deferred' or args[0].startswith('--deferred=')):
        return None
    words = [args[0][len('--deferred='):]] + args[1:] if args[0] != '--deferred' else args[1:]
    if len(words) != 1 or not DEFERRED_IDS.match(words[0]):
        raise Refused('--deferred takes one list of entry ids, comma-separated (`just design --deferred 42,57`)')
    return [int(n) for n in words[0].split(',')]


def deferred_brief(primary, base, ids, log_path):
    """The brief of the deferred entries [ids] of `origin/<base>`'s log, [log_path] (`paths.decision_log`):
    `# Deferred rulings <ids>`, then per entry `## <n>. <title>` and its Context and Decision. Refused when main's
    log is not there, or an id names no entry of it or one that is not deferred (recorded, or applied); refused with
    decisions.NO_LOG when no log is configured ([log_path] None)."""
    sys.path.append(os.path.join(HERE, 'decisions'))  # decisions
    import decisions
    if log_path is None:
        raise Refused(decisions.NO_LOG)
    r = repo.git(primary, 'show', f'origin/{base}:{log_path}')
    if r.returncode != 0:
        raise Refused(f'origin/{base} holds no {log_path}: {repo.why(r)}')
    log = decisions.parse_log(r.stdout)
    parts = [f'# Deferred rulings {", ".join(str(n) for n in ids)}']
    for n in ids:
        e = log.entries.get(n)
        if e is None:
            raise Refused(f'decision {n} is not in the log of origin/{base}')
        if e.status != decisions.Status.DEFERRED:
            raise Refused(f'decision {n} is not deferred on origin/{base}: {e.fields.get("Status", "no status")}')
        parts.append(f'## {n}. {e.title}\n\n**Context.** {e.fields.get("Context", "")}\n'
                     f'**Decision.** {e.fields.get("Decision", "")}')
    return '\n\n'.join(parts) + '\n'


def worktree(primary, branch, base):
    """`wt switch` of [branch] (`--create … --base origin/<base>` only when the branch does not exist; the pull
    fetched the base); the worktree's path, from wt's JSON."""
    ref = repo.git(primary, 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}')
    if ref.returncode not in (0, 1):
        raise Refused(f'cannot tell whether {branch} exists: {repo.why(ref)}')
    argv = ['wt', 'switch']
    if ref.returncode == 1:
        argv += ['--create', branch, '--base', f'origin/{base}']
    else:
        argv.append(branch)
    argv += ['--no-cd', '--yes', '--format=json']
    try:
        w = subprocess.run(argv, cwd=primary, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    except OSError as e:
        raise Refused(f'cannot run wt: {e.strerror}') from None
    if w.returncode != 0:
        lines = w.stderr.strip().splitlines()
        raise Refused(f'wt switch {branch} exited {w.returncode}' + (f': {lines[-1]}' if lines else ''))
    try:
        path = json.loads(w.stdout).get('path')
    except (json.JSONDecodeError, AttributeError):
        path = None
    if not isinstance(path, str) or not path:
        raise Refused(f'wt switch {branch} gave no worktree path: {w.stdout.strip()[-200:]!r}')
    return path


def startup(slug, model, direnv):
    """The launch shell's startup argv: `claude -n <slug> [--model <model>] '/brainstorm .cache/omc/brief.md'`,
    under `direnv exec .` when [direnv] (omc's `providers/claude.py:149-158`, `session.py:59-60`)."""
    return shells.startup_argv(session_name=slug, model=model, seed=SESSION, direnv=direnv)


def main(argv=None):
    """The start; it execs the launch shell on success and returns (2) only on a refusal."""
    args = sys.argv[1:] if argv is None else argv
    origin = os.environ.get('PWD') or None
    if args[:1] and args[0].startswith('--origin='):
        origin, args = args[0][len('--origin='):] or origin, args[1:]
    try:
        cfg = config.load(repo.root())
        if not args:
            raise Refused(NOTHING.format(briefs=cfg.paths.briefs))  # before the lock
        primary = gitnexus.primary_root('.')
        with step(f'primary: on {cfg.base}, clean, not diverged', quick=True):
            check_primary(primary, cfg.base)
        ids = deferred_ids(args)
        if ids is not None:
            with step(f'deferred: decisions {", ".join(str(n) for n in ids)} of origin/{cfg.base}', quick=True):
                text = deferred_brief(primary, cfg.base, ids, cfg.paths.decision_log)
        with step('slug', quick=True) as s:
            slug, text = (ask_slug(text, ask_claude), text) if ids is not None else slug_of(args, ask_claude, cfg.paths.briefs)
            s.what = f'slug: {slug}'
        branch = cfg.branch_prefix + slug
        if sys.platform == 'darwin':
            reconcile_fish()
        held = lock(primary)
        try:
            with step(f'primary: pulling origin/{cfg.base}') as s:
                check_primary(primary, cfg.base)  # another start may have moved it
                before, after = pull(primary, cfg.base)
                s.what += f' {before[:7]} → {after[:7]}' if before != after else f' {after[:7]} (current)'
                if before != after:  # the recipe's shell pulled moments ago: a merge landed since
                    s.warn(f'{cfg.base} moved since the start\'s pull: running the code it started with')
            exists = repo.git(primary, 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}').returncode == 0
            what = f'entering {branch}' if exists else f'creating {branch} from origin/{cfg.base}'
            with step(f'worktree: {what}'):
                path = worktree(primary, branch, cfg.base)
        finally:
            held.close()
        say('→ lock: released [ok]')
        gitnexus_steps(cfg, primary)
        brief = os.path.join(path, BRIEF)
        try:
            os.makedirs(os.path.dirname(brief), exist_ok=True)
            with open(brief, 'w', encoding='utf-8') as f:
                f.write(text)
        except OSError as e:
            raise Refused(f'cannot write {brief}: {e.strerror}') from None
        wired = notify.wire_worktree(notify.CLAUDE, Path(path), True)
        if wired:
            say(f'→ notifications: {", ".join(wired)} [ok]')
        env = launch_env(os.environ, slug)
        argv = startup(slug, cfg.orchestrator_model, has_direnv(env))
        launch.launch(env, cwd=path, slug=slug, title=branch, argv=argv, origin=origin)
    except Refused as e:
        print(f'error: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
