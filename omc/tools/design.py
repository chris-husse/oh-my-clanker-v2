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
pull, is one `[warn]` and the start goes on with the code it started with), the GitNexus install and the refresh of
the primary's index at the pulled tip, and the worktree cut. Neither GitNexus step refuses the start: a failure is
`[failed] <why>` and the line `GitNexus is stale: /explain answers from <sha>`. `feature/<slug>` is cut from
`origin/<base>` with worktrunk, or entered again when the branch exists; after the release the context goes to
`<worktree>/.cache/omc/brief.md`. Base and branch prefix come from omc/config.yaml; Claude only, no provider option.
Then the launch as omc's: on macOS the fish title hook's conf.d copy is reconciled before the lock (`fish_integration`
`reconcile`, a failure a `[warn]`); after the brief, the notification channel is wired in the worktree
(`notify.wire_worktree`, `preferredNotifChannel: auto`, never blocking); the environment takes the `uv` venv out
(`VIRTUAL_ENV` and its `bin` on `PATH`) and sets `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`, `OMC_SLUG=<slug>` and
`OMC_PROVIDER=claude` (the slug's `claude -p` gets the first only); then the process becomes the interactive shell of
`$SHELL`'s basename (fish, zsh, bash, else sh, `shells.py`) in the worktree, titled `<branch>`, its herdr exit report
the origin, which runs `claude -n <slug> [--model <orchestrator-model>] '/brainstorm .cache/omc/brief.md'`, under
`direnv exec .` when `direnv version` runs. A first argument `--origin=<dir>` (the `design` recipe's
`invocation_directory()`, handed on through `_design-start`; else `$PWD`) is taken off before the brief's. The standard library and pyyaml (config.py), through the justfile's
`uv run`; exit 2 with `error: <why>` on every refusal."""
import fcntl
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import fish_integration  # noqa: E402
import gitnexus  # noqa: E402
import notify  # noqa: E402
import repo  # noqa: E402
import shells  # noqa: E402
from terminal_title import terminal_title_argv  # noqa: E402
from terminals import detect_terminal  # noqa: E402
from toolctx import Ctx, OmcError  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

LOCK = os.path.join('.cache', 'omc', 'design.lock')
BRIEF = os.path.join('.cache', 'omc', 'brief.md')
SESSION = '/brainstorm .cache/omc/brief.md'
PROVIDER = 'claude'
TITLE_OFF = {'CLAUDE_CODE_DISABLE_TERMINAL_TITLE': '1'}  # omc's claude provider's `title_env`
KEBAB = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
SLUG_FORM = re.compile(r'^[a-z0-9]+(-[a-z0-9]+){2,5}$')  # three to six words
NOTHING = 'nothing to start: `just design <brief-or-text>`, a brief ({briefs}<name>.md) or a sentence'
PROMPT = ('Reply with only a git branch slug for this piece of work: kebab-case, three to six lowercase ASCII words or '
          'numbers, nothing else. The work: {text}')


def ask_claude(prompt):
    """One `claude -p <prompt>` call (the owner's default model), its terminal title off; its stdout."""
    try:
        r = subprocess.run(('claude', '-p', prompt), stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           env={**os.environ, **TITLE_OFF})
    except OSError as e:
        raise Refused(f'cannot run claude: {e.strerror}') from None
    if r.returncode != 0:
        lines = r.stderr.strip().splitlines()
        raise Refused(f'claude -p exited {r.returncode}' + (f': {lines[-1]}' if lines else ''))
    return r.stdout


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
    answers = []
    for _ in range(2):
        answer = ask(PROMPT.format(text=text)).strip()
        if SLUG_FORM.match(answer):
            return answer, text + '\n'
        answers.append(answer)
    raise Refused('claude gave no slug of three to six kebab-case words, twice: '
                  + ', '.join(repr(a) for a in answers))


def say(text, end='\n'):
    sys.stderr.write(text + end)
    sys.stderr.flush()


class step:
    """One step line, a context manager: `→ <what> …` at the start, then the end word, `[ok]` unless the block
    calls `.warn(why)`; a Refused or Failed raised inside ends it `[failed] <why>` and goes on up. `.what` may be
    changed inside the block (the line is written again). `long` adds the elapsed time before the end word (from one
    second on) and keeps the line alive while it runs: refreshed in place every ten seconds on a TTY, a line
    `  · <what>: <time>` once a minute off one; off a TTY a short step writes its line at the end only. `.say` takes
    the lines of what the step runs (gitnexus's): kept, and shown under the line when it ends `[warn]`. `quick`: a
    check, whose line has no `…` (`→ slug: <slug> [ok]`)."""

    def __init__(self, what, long=False, quick=False):
        self.what, self.long, self.dots = what, long, '' if quick else ' …'
        self.tty = sys.stderr.isatty()
        self.notes, self.word = [], '[ok]'
        self.open = None  # the what of the line written without its end, while it stays so
        self.mutex, self.done = threading.Lock(), threading.Event()

    def say(self, line):
        self.notes.append(line)

    def warn(self, why):
        self.word = f'[warn] {why}'

    def elapsed(self):
        seconds = time.monotonic() - self.start
        return f' {gitnexus.clock(seconds)}' if self.long and seconds >= 1 else ''

    def beat(self):
        while not self.done.wait(10 if self.tty else 60):
            with self.mutex:
                if self.tty:
                    say(f'\r\033[K→ {self.what}{self.dots}{self.elapsed()}', end='')
                else:
                    say(('\n' if self.open else '') + f'  · {self.what}:{self.elapsed()}')
                    self.open = None

    def __enter__(self):
        self.start = time.monotonic()
        if self.tty or self.long:
            say(f'→ {self.what}{self.dots}', end='')
            self.open = self.what
        if self.long:
            self.ticker = threading.Thread(target=self.beat, daemon=True)
            self.ticker.start()
        return self

    def __exit__(self, kind, error, _tb):
        if self.long:
            self.done.set()
            self.ticker.join()
        if isinstance(error, (Refused, gitnexus.Failed)):
            self.word = f'[failed] {(str(error).splitlines() or [kind.__name__])[0]}'
        elif error is not None:
            self.word = f'[failed] {kind.__name__}'
        line = f'→ {self.what}{self.dots}{self.elapsed()} {self.word}'
        with self.mutex:
            if self.tty:
                say(f'\r\033[K{line}')
            elif self.open == self.what:
                say(f'{self.elapsed()} {self.word}')
            else:
                say(('\n' if self.open else '') + line)
            self.open = None
        if self.word.startswith('[warn]'):
            for note in self.notes:
                if not note.endswith('[ok]'):
                    say(f'  {note}')
        return False


def check_primary(primary, base):
    """Refused unless the primary checkout is on [base], with no tracked changes (untracked files are none) and not
    diverged from `origin/<base>` (behind only is pulled, ahead only is not diverged)."""
    branch = repo.git(primary, 'symbolic-ref', '--short', '-q', 'HEAD').stdout.strip()
    if branch != base:
        raise Refused(f'the primary checkout is on {branch or "a detached HEAD"}, not {base}: '
                      f'just design cuts its worktrees from {base} ({primary})')
    if repo.output(primary, 'status', '--porcelain', '--untracked-files=no').strip():
        raise Refused(f'the primary checkout has changes: commit or stash them first ({primary})')
    counts = repo.output(primary, 'rev-list', '--left-right', '--count', f'HEAD...origin/{base}').split()
    if len(counts) == 2 and counts[0] != '0' and counts[1] != '0':
        raise Refused(f'the primary checkout has diverged from origin/{base}: {counts[0]} commits ahead, '
                      f'{counts[1]} behind ({primary})')


def pull(primary, base):
    """`git fetch origin <base>` and `git merge --ff-only origin/<base>` in the primary; (the sha before, the sha
    after). A failed fetch or a refused fast-forward is Refused."""
    repo.output(primary, 'fetch', '-q', 'origin', base)
    before = repo.output(primary, 'rev-parse', 'HEAD').strip()
    repo.output(primary, 'merge', '-q', '--ff-only', f'origin/{base}')
    return before, repo.output(primary, 'rev-parse', 'HEAD').strip()


def lock(primary):
    """The start's lock, held (an open file; closing it releases the lock): taken at once when free, else when the
    other start releases it, its step line open while it waits."""
    path = os.path.join(primary, LOCK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, 'a')
    with step('lock: waiting for another start', long=True):
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fcntl.flock(f, fcntl.LOCK_EX)
    return f


def gitnexus_steps(cfg, primary):
    """The install, then the refresh of the primary's index at its HEAD; neither refuses the start: a failure is its
    step's `[failed] <why>` and the line `GitNexus is stale: /explain answers from <sha or "no index">` (a failed
    install skips the refresh)."""
    try:
        with step(f'GitNexus: checking the build at {cfg.gitnexus_commit[:7]}', long=True) as s:
            gitnexus.install(cfg, s.say)
        head = repo.output(primary, 'rev-parse', 'HEAD').strip()
        how = ' (embeddings)' if gitnexus.runtime_ready() else ''
        with step(f'GitNexus: refreshing the index at {head[:7]}{how}', long=True) as s:
            if gitnexus.refresh(primary, cfg.base, s.say) == 'keyword-only':
                capped = any('embedding cap' in note for note in s.notes)
                s.warn('keyword-only (over the embedding cap)' if capped else 'keyword-only (embedding failed)')
    except (Refused, gitnexus.Failed) as e:
        at = gitnexus.indexed_at(primary)
        say(f'GitNexus is stale: /explain answers from {at[:7] if at else "no index"}')
        for line in str(e).splitlines()[1:]:  # a build's output tail, under the line
            say(f'  {line}')


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


def has_direnv(env):
    """Whether `direnv version` runs (exit 0, 5 s) on [env]'s PATH: omc's `probe.has_direnv`."""
    try:
        r = subprocess.run(('direnv', 'version'), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
                           env=env)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def startup(slug, model, direnv):
    """The launch shell's startup argv: `claude -n <slug> [--model <model>] '/brainstorm .cache/omc/brief.md'`,
    under `direnv exec .` when [direnv] (omc's `providers/claude.py:149-158`, `session.py:59-60`)."""
    return shells.startup_argv(session_name=slug, model=model, seed=SESSION, direnv=direnv)


def launch_env(env, slug):
    """[env] for the launch shell (omc's `session.py:74-77`): the `uv` venv taken out (`VIRTUAL_ENV`, and its `bin`
    off `PATH`), `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`, `OMC_SLUG` and `OMC_PROVIDER` set."""
    env = dict(env)
    venv = env.pop('VIRTUAL_ENV', '')
    if venv and 'PATH' in env:
        drop = os.path.normpath(os.path.join(venv, 'bin'))
        env['PATH'] = os.pathsep.join(d for d in env['PATH'].split(os.pathsep) if os.path.normpath(d) != drop)
    env.update(TITLE_OFF, OMC_SLUG=slug, OMC_PROVIDER=PROVIDER)
    return env


def reconcile_fish():
    """macOS only: `just omc shell-integration fish reconcile`, as omc's install ran it; never refuses the start."""
    with step('fish title hook: reconciling', quick=True) as s:
        try:
            fish_integration.run_fish_integration(Ctx.from_env(), 'reconcile')
        except (OmcError, OSError) as e:
            s.warn(str(e).splitlines()[0] if str(e) else type(e).__name__)


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
        with step('slug', quick=True) as s:
            slug, text = slug_of(args, ask_claude, cfg.paths.briefs)
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
            gitnexus_steps(cfg, primary)
            exists = repo.git(primary, 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}').returncode == 0
            what = f'entering {branch}' if exists else f'creating {branch} from origin/{cfg.base}'
            with step(f'worktree: {what}'):
                path = worktree(primary, branch, cfg.base)
        finally:
            held.close()
        say('→ lock: released [ok]')
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
        shell = shells.detect_shell(env)
        say(f'→ session: starting {shell.name} on claude "{SESSION}"')
        os.environ.clear()
        os.environ.update(env)
        try:
            shell.exec_interactive(cwd=path, title=branch, startup_argv=argv,
                                   title_seq=detect_terminal(env).title_sequence(branch),
                                   title_argv=terminal_title_argv(), origin_cwd=origin)
        except OSError as e:
            raise Refused(f'cannot run {shell.name}: {e.strerror}') from None
    except Refused as e:
        print(f'error: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
