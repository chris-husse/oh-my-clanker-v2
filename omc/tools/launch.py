"""The launch pieces `just design` (design.py) and `just investigate` (investigate.py) share: the step lines on stderr
(`→ <what> … [ok]`, `[warn] <why>` or `[failed] <why>`), the primary checkout's check and pull, the start's lock
(`.cache/omc/design.lock` of the primary, which both commands wait in line on), the slug asked of `claude -p`, the
GitNexus install and refresh under their own lock, the launch environment, the macOS fish hook's reconcile, and the
tail of a start: the herdr tab named, the `→ session: …` line, then the process becomes the interactive shell of
`$SHELL`'s basename (`shells.py`) in the given directory, titled as asked. The standard library and pyyaml
(config.py); every refusal is `Refused` (exit 2, `error: <why>`, the caller's)."""
import fcntl
import os
import re
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import fish_integration  # noqa: E402
import gitnexus  # noqa: E402
import herdr  # noqa: E402
import repo  # noqa: E402
import shells  # noqa: E402
from terminal_title import terminal_title_argv  # noqa: E402
from terminals import detect_terminal  # noqa: E402
from toolctx import Ctx, OmcError  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

LOCK = os.path.join('.cache', 'omc', 'design.lock')
GITNEXUS_LOCK = os.path.join('.cache', 'omc', 'gitnexus.lock')  # the refresh's, outside the start's
PROVIDER = 'claude'
TITLE_OFF = {'CLAUDE_CODE_DISABLE_TERMINAL_TITLE': '1'}  # omc's claude provider's `title_env`
SLUG_FORM = re.compile(r'^[a-z0-9]+(-[a-z0-9]+){2,5}$')  # three to six words
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


def ask_slug(text, ask):
    """The slug [ask] (a callable of the prompt) gives for [text], asked once more when its form is wrong, then
    refused."""
    answers = []
    for _ in range(2):
        answer = ask(PROMPT.format(text=text.strip())).strip()
        if SLUG_FORM.match(answer):
            return answer
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


def check_primary(primary, base, why='just design cuts its worktrees from {base}'):
    """Refused unless the primary checkout is on [base], with no tracked changes (untracked files are none) and not
    diverged from `origin/<base>` (behind only is pulled, ahead only is not diverged). [why], formatted with `base`,
    ends the refusal of a primary off [base]: what the caller needs [base] for."""
    branch = repo.git(primary, 'symbolic-ref', '--short', '-q', 'HEAD').stdout.strip()
    if branch != base:
        raise Refused(f'the primary checkout is on {branch or "a detached HEAD"}, not {base}: '
                      f'{why.format(base=base)} ({primary})')
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
    """The install, then the refresh of the primary's index at its HEAD, after the start's lock is released and under
    the primary's own `.cache/omc/gitnexus.lock`, taken without waiting: held by another start, which refreshes the
    same index, both are left to it (`→ GitNexus: another start is refreshing the index [ok]`). Neither refuses the
    start: a failure is its step's `[failed] <why>` and the line `GitNexus is stale: /explain answers from <sha or "no
    index">` (a failed install skips the refresh)."""
    path = os.path.join(primary, GITNEXUS_LOCK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a') as held:
        try:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            say('→ GitNexus: another start is refreshing the index [ok]')
            return
        _gitnexus_steps(cfg, primary)


def _gitnexus_steps(cfg, primary):
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


def has_direnv(env):
    """Whether `direnv version` runs (exit 0, 5 s) on [env]'s PATH: omc's `probe.has_direnv`."""
    try:
        r = subprocess.run(('direnv', 'version'), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
                           env=env)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def launch_env(env, slug, extra=None):
    """[env] for the launch shell (omc's `session.py:74-77`): the `uv` venv taken out (`VIRTUAL_ENV`, and its `bin`
    off `PATH`), `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`, `OMC_SLUG` and `OMC_PROVIDER` set, then [extra] (a mapping of
    the caller's own variables) merged last."""
    env = dict(env)
    venv = env.pop('VIRTUAL_ENV', '')
    if venv and 'PATH' in env:
        drop = os.path.normpath(os.path.join(venv, 'bin'))
        env['PATH'] = os.pathsep.join(d for d in env['PATH'].split(os.pathsep) if os.path.normpath(d) != drop)
    env.update(TITLE_OFF, OMC_SLUG=slug, OMC_PROVIDER=PROVIDER)
    env.update(extra or {})
    return env


def reconcile_fish():
    """macOS only: `just omc shell-integration fish reconcile`, as omc's install ran it; never refuses the start."""
    with step('fish title hook: reconciling', quick=True) as s:
        try:
            fish_integration.run_fish_integration(Ctx.from_env(), 'reconcile')
        except (OmcError, OSError) as e:
            s.warn(str(e).splitlines()[0] if str(e) else type(e).__name__)


def launch(env, *, cwd, slug, title, argv, origin, fixed_title=False):
    """The tail of a start: inside herdr its tab named [slug] (`herdr.name_tab`, a failure a `[warn]`), the line
    `→ session: starting <shell> on claude "<seed>"` (the seed the last word of [argv]), `os.environ` replaced by
    [env], then the process becomes the interactive shell of [env]'s `$SHELL` in [cwd], titled [title], running
    [argv], its herdr exit report [origin]. [fixed_title]: the title stays [title] for the shell's life (fish never
    turns it into the branch). Returns only by raising Refused, when the shell cannot be run."""
    named = herdr.name_tab(Ctx.from_env(env), slug)  # the tab beside the title; None outside herdr
    if named is not None:
        say(f'→ herdr tab: {slug} ' + ('[ok]' if named else '[warn] herdr tab rename failed'))
    shell = shells.detect_shell(env)
    say(f'→ session: starting {shell.name} on claude "{argv[-1]}"')
    os.environ.clear()
    os.environ.update(env)
    try:
        shell.exec_interactive(cwd=cwd, title=title, startup_argv=argv,
                               title_seq=detect_terminal(env).title_sequence(title),
                               title_argv=terminal_title_argv(), origin_cwd=origin, fixed_title=fixed_title)
    except OSError as e:
        raise Refused(f'cannot run {shell.name}: {e.strerror}') from None
