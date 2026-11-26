"""Is it done: `just omc gate run | passed | skip`,
`reviewed [--record]` and `settled [--record]`. A record names the commit it was made at and holds for the tree of now
when everything changed since that commit (the working tree and the index against it, plus the untracked files) is
a path the record does not cover (`gate_keep`, `review_keep`, `settled_keep`, of omc/config.yaml's `paths`). A
settled design holds across the plan's commit and its ticks (`paths.plans` in `settled_keep`, as in `gate_keep`), so `/design` started again after its `plan`
step skips its hardening.

The records: `gate run <gate>` runs the project's own command `omc/bin/<gate>` at the root, or with a step file
`omc/bin/<gate>.steps.yaml` its stale steps (steps.py, DVC deciding; `--full` all of them), its output passed through
and teed to `.cache/omc/gates/<gate>.log`, its exit code written beside it to `.cache/omc/gates/<gate>.exit` when
it ends (removed at its start, so that a run started detached is polled by those two files); a full run (no ARGS, or a
step file's `--full`) that exits 0 and started on a clean tree (`just omc git clean`) is a pass, `.cache/omc/passes/<gate>/<HEAD sha>.json` `{"gate", "head", "at"}`;
a removed one is a gate not passed. A run first takes one of the gate's machine-wide slots (concurrency.py, `concurrency` of omc/config.yaml),
waiting in line when all are held; then the command runs in its own session, and with a `silence` limit for the gate
a run that writes no byte for that many seconds is ended as a whole process group (SIGTERM, SIGKILL 10 s later),
`no output for <s> s: killed`, exit 124 (a command that has exited while a process it left behind holds the
output keeps its own code); the time spent waiting for a slot is not counted. A SIGTERM or SIGHUP
to the run ends that group too (`_stop`), exit 128 + the signal. The owner's skip of a gate is
`.cache/omc/skips/<HEAD sha>`, one gate per line; a review `.cache/omc/reviewed/<HEAD sha>.json` and a settled design
`.cache/omc/settled/<HEAD sha>.json`, each `{"head": "<sha>", "at": "<iso time>"}`. Every
record is written to a temporary file and renamed; a file that does not parse is skipped. The standard library only;
every git call goes through repo.git."""
import codecs
import contextlib
import datetime
import glob
import json
import os
import queue
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import concurrency  # noqa: E402
import config  # noqa: E402
import repo  # noqa: E402
import steps  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

# What each record holds although it changed, of config.Paths [paths]: (folders, one `startswith` each; globs, one
# config.matches each)
GATE_NOTES = ('omc/bin/*.md',)  # the gates' notes


def gate_keep(paths):
    """The shots' verdicts and the owner's screenshot reviews (`Paths.verdicts`, `Paths.screen_reviews`) hold the
    review and the passed gate, so that `/audit`'s `screens` step amends them into the commit over both; the shots
    themselves are `paths.screenshots`, which the review holds too."""
    return ((paths.briefs, paths.plans, paths.verdicts, paths.screen_reviews),
            paths.screenshots + paths.baselines + GATE_NOTES)


def review_keep(paths):
    return (paths.briefs, paths.verdicts, paths.screen_reviews), paths.screenshots + paths.baselines


def settled_keep(paths):
    return (paths.briefs, paths.plans), ()


BIN = os.path.join('omc', 'bin')  # the project's gate commands, omc/bin/<gate>
LOGS = os.path.join('.cache', 'omc', 'gates')
PASSES = os.path.join('.cache', 'omc', 'passes')
SKIPS = os.path.join('.cache', 'omc', 'skips')
REVIEWED = os.path.join('.cache', 'omc', 'reviewed')
SETTLED = os.path.join('.cache', 'omc', 'settled')
GONE = 'the commit is gone'
SHOWN = 5  # the paths a miss names


def _names(root, *args):
    return [p for p in repo.output(root, *args).split('\0') if p]


def changed_paths(root, commit):
    """Every path that differs from [commit]: the working tree and the index against it, and the untracked files;
    sorted, unique. None when git cannot find [commit]."""
    if repo.git(root, 'cat-file', '-e', f'{commit}^{{commit}}').returncode != 0:
        return None
    return sorted(set(_names(root, 'diff', '--name-only', '-z', '--no-renames', commit, '--'))
                  | set(_names(root, 'ls-files', '-z', '--others', '--exclude-standard')))


def holds(root, commit, keep):
    """(True, []) when every path changed since [commit] starts with a folder of [keep] or matches one of its globs
    (`gate_keep`), else (False, the others); (False, ['the commit is gone']) when git cannot find [commit]."""
    changed = changed_paths(root, commit)
    if changed is None:
        return False, [GONE]
    folders, globs = keep
    others = [p for p in changed if not (p.startswith(folders) or config.matches(p, globs))]
    return not others, others


def _head(root):
    r = repo.git(root, 'rev-parse', '--verify', '-q', 'HEAD')
    if r.returncode != 0 or not r.stdout.strip():
        raise Refused('HEAD names no commit')
    return r.stdout.strip()


def _read_json(path):
    """The JSON object of [path], or None when it is gone or does not parse."""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _write_atomic(path, text):
    """[text] into [path] through `<path>.tmp-<pid>` and a rename."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f'{path}.tmp-{os.getpid()}'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


def _first_that_holds(root, candidates, keep):
    """[candidates] ((commit, what), newest first): (the first that holds, None), or (None, the why of the newest
    one, naming its first paths), or (None, None) when there is none."""
    why = None
    for commit, what in candidates:
        ok, others = holds(root, commit, keep)
        if ok:
            return (commit, what), None
        if why is None:
            why = f'{what} at {commit[:8]} does not hold: {", ".join(others[:SHOWN])}'
    return None, why


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def _passes(root, gate):
    """The pass records of [gate], newest first, as (head, 'run')."""
    found = []
    for path in glob.glob(os.path.join(root, PASSES, gate, '*.json')):
        rec = _read_json(path)
        if rec and rec.get('gate') == gate and isinstance(rec.get('head'), str) and rec['head']:
            found.append(((str(rec.get('at') or ''), _mtime(path)), rec['head']))
    found.sort(key=lambda c: c[0], reverse=True)
    return [(head, 'run') for _, head in found]


SILENT = 124  # the exit code of a run killed for its silence, as timeout(1)'s
GRACE = 10.0  # seconds between the SIGTERM of a silent run's process group and its SIGKILL


def _signal_group(proc, sig):
    try:
        os.killpg(proc.pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def _end_group(proc, chunks, out):
    """Ends [proc]'s process group: SIGTERM, then SIGKILL once [GRACE] seconds passed without the command ending and
    its output closing; what it still writes meanwhile goes to [out]."""
    _signal_group(proc, signal.SIGTERM)
    deadline = time.monotonic() + GRACE
    open_ = True
    while (proc.poll() is None or open_) and time.monotonic() < deadline:
        open_ = _drain(chunks, out, 0.1)
    _signal_group(proc, signal.SIGKILL)  # the group's other members too, a server the gate started
    proc.wait()
    if open_:
        _drain(chunks, out, 0.5)


STOPS = (signal.SIGTERM, signal.SIGHUP)  # a stop of the run itself, as a terminal stopping its background task


def _stop(signum, frame):
    """A stop of the run: further stops ignored while it ends its command, then SystemExit(128 + the signal), which
    gate_run's own handler meets so that `_end_group` ends the command's session."""
    for sig in STOPS:
        signal.signal(sig, signal.SIG_IGN)
    raise SystemExit(128 + signum)


@contextlib.contextmanager
def _stoppable():
    """SIGTERM and SIGHUP raise SystemExit (`_stop`) while inside, in the main thread; the old handlers restored."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    old = {sig: signal.signal(sig, _stop) for sig in STOPS}
    try:
        yield
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


def _drain(chunks, out, wait):
    """What [chunks] holds within [wait] seconds, to [out]; False once the reader's end (None) came."""
    end = time.monotonic() + wait
    while (left := end - time.monotonic()) > 0:
        try:
            chunk = chunks.get(timeout=left)
        except queue.Empty:
            return True
        if chunk is None:
            return False
        out(chunk)
    return True


# The cores a gate's commands leave free (the owner, 2026-11-26): core 0 stays for the desktop, the agents and the
# terminals, whatever the machine; a machine with one core keeps it.
RESERVED_CORES = frozenset({0})


def gate_cores():
    """The cores a gate's command may run on: those this process may use, but RESERVED_CORES, unless that would leave
    none; None where the platform sets no affinity (macOS), and the command runs where the system puts it."""
    if not hasattr(os, 'sched_getaffinity'):
        return None
    mine = os.sched_getaffinity(0)
    return (mine - RESERVED_CORES) or mine


def _pinned(cores):
    """The child's first act, before its exec: its affinity set to [cores], which every process it starts inherits."""
    return None if cores is None else (lambda: os.sched_setaffinity(0, cores))


def _run(argv, root, out, quiet):
    """Runs [argv] at [root] in its own session, on gate_cores() (core 0 left free), its stdout and stderr to [out] as they come; its exit code, or SILENT
    once [quiet] seconds (None: never) passed without a byte, the session ended (`_end_group`) and `no output for <s>
    s: killed` written. A command that has exited while a process it left in its group still holds the pipe keeps
    its own code: at the end of the silence that group is ended, with no kill line. A stop of ours (`_stoppable`) or an interrupt ends the session too, and is raised again.
    Refused when [argv] cannot start."""
    chunks = queue.Queue()
    try:
        proc = subprocess.Popen(argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                start_new_session=True, preexec_fn=_pinned(gate_cores()))
    except OSError as e:
        raise Refused(f'cannot run {argv[0]}: {e.strerror}') from None
    killed = False
    try:  # from the moment the command runs: a stop of ours (_stop) or an interrupt ends its session too
        def read():
            try:
                while chunk := proc.stdout.read1(65536):
                    chunks.put(chunk)
            finally:
                chunks.put(None)
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        last = time.monotonic()
        while True:
            wait = None if quiet is None else max(0.0, last + quiet - time.monotonic())
            try:
                chunk = chunks.get(timeout=wait)
            except queue.Empty:
                killed = proc.poll() is None  # else the command exited and what it left behind holds the pipe
                _end_group(proc, chunks, out)
                break
            if chunk is None:
                break
            out(chunk)
            last = time.monotonic()
        proc.wait()
    except BaseException:  # the command's own session would outlive us
        _end_group(proc, chunks, out)
        raise
    reader.join(1)  # a process outside the group may still hold the pipe: the reader is left to it
    if not reader.is_alive():
        proc.stdout.close()
    if killed:
        out(f'no output for {quiet} s: killed\n'.encode())
        return SILENT
    return proc.returncode


FULL = '--full'  # the one argument of a gate with a step file: every step runs


def _run_steps(root, gate, found, full, out, quiet):
    """The steps [found] of [gate] (steps.load): the stale ones (steps.selection), with [full] every one but a
    committed stage (`lock`), whose lock decides; each `== <name>`, then its command by bash at the root (`_run`), a
    green staged one recorded (steps.record_green) unless one of its inputs changed while it ran. A red step does not
    stop the next; a silent one ends the run (SILENT). Last, `steps: <n> ran, fresh: <names>, red: <names>`; 0 when no
    step is red, else 1 (a derive command or DVC failing: that line, nothing run)."""
    def say(text):
        out(f'{text}\n'.encode())

    try:
        names, deps = steps.selection(root, found)
    except steps.StepFailed as e:
        say(str(e))
        return 1
    chosen = {s.name for s in found if s.name in names or (full and not s.lock)}
    red, ran = [], 0
    for s in found:
        if s.name not in chosen:
            continue
        say(f'== {s.name}')
        before = steps.snapshot(root, deps[s.name]) if s.staged else None
        code = _run(('bash', '-c', s.run), root, out, quiet)
        ran += 1
        if code == SILENT:
            return SILENT
        if code != 0:
            say(f'== {s.name}: red (exit {code})')
            red.append(s.name)
        elif s.staged:
            if steps.snapshot(root, deps[s.name]) != before:
                say(f'== {s.name}: an input changed while it ran: not recorded')
                continue
            try:
                steps.record_green(root, s)
            except steps.StepFailed as e:
                say(f'== {s.name}: red, not recorded: {e}')
                red.append(s.name)
    fresh = [s.name for s in found if s.name not in chosen]
    say(f'steps: {ran} ran' + (f', fresh: {", ".join(fresh)}' if fresh else '')
        + (f', red: {", ".join(red)}' if red else ''))
    return 1 if red else 0


def gate_run(root, gate, args=()):
    """`_gate_run`, its exit code also written to `.cache/omc/gates/<gate>.exit` once it ends (the code and a
    newline: 2 for a refusal, whose `error: <why>` is the log's last line, 128 + the signal for a stop), that file removed and the log
    emptied at the start: a caller that started the run detached polls the log and that file."""
    logs = os.path.join(root, LOGS)
    log, exit_file = os.path.join(logs, f'{gate}.log'), os.path.join(logs, f'{gate}.exit')
    os.makedirs(logs, exist_ok=True)
    with contextlib.suppress(FileNotFoundError):
        os.remove(exit_file)
    open(log, 'wb').close()
    code = 1
    try:
        code = _gate_run(root, gate, args)
        return code
    except Refused as e:
        code = 2
        with open(log, 'ab') as f:
            f.write(f'error: {e}\n'.encode())
        raise
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        raise
    except KeyboardInterrupt:
        code = 128 + signal.SIGINT
        raise
    finally:
        _write_atomic(exit_file, f'{code}\n')


def _gate_run(root, gate, args=()):
    """Runs the gate [gate] at [root], its output passed to our stdout and teed into `.cache/omc/gates/<gate>.log`
    (truncated); its exit code. Without a step file it runs `omc/bin/<gate> [args]`; with one
    (`omc/bin/<gate>.steps.yaml`, steps.py) its stale steps, or with `--full` all of them (`_run_steps`), no other
    argument taken. It first takes a slot of [gate] (concurrency.slot, the limit config.concurrency), the wait line in
    the log and on stdout; each command runs in its own session (`_run`), and with config.silence a run silent that
    long is ended as a process group, `no output for <s> s: killed` written, SILENT returned; a SIGTERM or SIGHUP to us
    ends it the same way (`_stoppable`), SystemExit(128 + the signal) raised. Exit 0 of a full run (no [args], or a
    step file's `--full`) that started on a clean tree (repo.dirty_paths) writes `.cache/omc/passes/<gate>/<HEAD
    sha>.json`. Refused when there is neither a step file nor the command, the command is not executable, the step
    file or the config cannot be read or holds a bad limit, or the step file is refused (steps.load, steps.selection:
    no DVC)."""
    found = steps.load(root, gate)
    command = os.path.join(root, BIN, gate)
    if found is not None:
        if any(a != FULL for a in args):
            raise Refused(f'a gate with a step file ({BIN}/{gate}.steps.yaml) takes no argument but {FULL}')
    elif not os.path.isfile(command):
        raise Refused(f'no gate command {BIN}/{gate}')
    elif not os.access(command, os.X_OK):
        raise Refused(f'{BIN}/{gate} is not executable')
    cfg = config.raw(root)
    limit, quiet = config.concurrency(cfg, gate), config.silence(cfg, gate)
    log = os.path.join(root, LOGS, f'{gate}.log')
    os.makedirs(os.path.dirname(log), exist_ok=True)
    decode = codecs.getincrementaldecoder('utf-8')(errors='replace')
    with open(log, 'wb') as f, _stoppable():
        def out(chunk):
            f.write(chunk)
            f.flush()
            sys.stdout.write(decode.decode(chunk))
            sys.stdout.flush()

        with concurrency.slot(root, gate, limit, lambda line: out(line.encode() + b'\n')):
            head = _head(root)
            clean = not repo.dirty_paths(root)
            try:
                if found is None:
                    try:
                        code = _run((command, *args), root, out, quiet)
                    except Refused as e:
                        raise Refused(str(e).replace(command, f'{BIN}/{gate}')) from None
                else:
                    code = _run_steps(root, gate, found, FULL in args, out, quiet)
            finally:
                sys.stdout.write(decode.decode(b'', final=True))
                sys.stdout.flush()
            if code == SILENT:
                return SILENT
    full = not args if found is None else all(a == FULL for a in args)
    if code == 0 and clean and full:
        _write_atomic(os.path.join(root, PASSES, gate, f'{head}.json'),
                      json.dumps({'gate': gate, 'head': head, 'at': _now()}) + '\n')
    return code


def _skip_files(root):
    return [p for p in glob.glob(os.path.join(root, SKIPS, '*')) if '.tmp-' not in os.path.basename(p)]


def _skips(root, gate):
    """The owner's skips of [gate], newest first, as (commit, 'skip')."""
    found = []
    for path in _skip_files(root):
        try:
            with open(path, encoding='utf-8') as f:
                gates = f.read().split()
        except OSError:
            continue
        if gate in gates:
            found.append((_mtime(path), os.path.basename(path)))
    found.sort(reverse=True)
    return [(commit, 'skip') for _, commit in found]


def gate_passed(root, gate):
    """(True, 'passed: run at <head>' or 'skipped by the owner at <head>') for the newest pass of [gate], else the
    newest skip of it, that holds with gate_keep; else (False, 'not passed: <why>')."""
    keep = gate_keep(config.load(root).paths)
    hit, why = _first_that_holds(root, _passes(root, gate), keep)
    if hit:
        return True, f'passed: {hit[1]} at {hit[0][:8]}'
    skip, skip_why = _first_that_holds(root, _skips(root, gate), keep)
    if skip:
        return True, f'skipped by the owner at {skip[0][:8]}'
    return False, f'not passed: {why or skip_why or "no passed run started on a clean tree"}'


def gate_skip(root, gate):
    """Appends [gate] to `.cache/omc/skips/<HEAD sha>` (once); its path. Refused when the tree has changes the skip
    would not cover."""
    head = _head(root)
    ok, others = holds(root, head, gate_keep(config.load(root).paths))
    if not ok:
        raise Refused(f'the tree has changes a skip would not cover: {", ".join(others)}')
    path = os.path.join(root, SKIPS, head)
    try:
        with open(path, encoding='utf-8') as f:
            gates = f.read().split()
    except FileNotFoundError:
        gates = []
    if gate not in gates:
        _write_atomic(path, ''.join(f'{g}\n' for g in (*gates, gate)))
    return path


def _recorded(root, directory, keep, word, label, none):
    """(True, '<word> at <head>') for the newest record of [directory] that holds with [keep], else
    (False, 'not <word>: <why>'), the why naming the newest record as '<label> at <head>'."""
    found = []
    for path in glob.glob(os.path.join(root, directory, '*.json')):
        rec = _read_json(path)
        if rec and isinstance(rec.get('head'), str) and rec['head']:
            found.append(((str(rec.get('at') or ''), _mtime(path)), rec['head']))
    found.sort(key=lambda c: c[0], reverse=True)
    hit, why = _first_that_holds(root, [(head, label) for _, head in found], keep)
    if hit:
        return True, f'{word} at {hit[0][:8]}'
    return False, f'not {word}: {why or none}'


def _record(root, directory, keep, what):
    """Writes `<directory>/<HEAD sha>.json`; its path. Refused when the tree has changes the record would not
    cover."""
    head = _head(root)
    ok, others = holds(root, head, keep)
    if not ok:
        raise Refused(f'the tree has changes {what} would not cover: {", ".join(others)}')
    path = os.path.join(root, directory, f'{head}.json')
    _write_atomic(path, json.dumps({'head': head, 'at': _now()}) + '\n')
    return path


def reviewed(root):
    """(True, 'reviewed at <head>') when a review holds for this tree with review_keep, else (False, 'not reviewed:
    <why>')."""
    return _recorded(root, REVIEWED, review_keep(config.load(root).paths), 'reviewed', 'the review',
                     'no review recorded')


def record_review(root):
    """`.cache/omc/reviewed/<HEAD sha>.json`; refused when the tree has changes a review would not cover."""
    return _record(root, REVIEWED, review_keep(config.load(root).paths), 'a review')


def settled(root):
    """(True, 'settled at <head>') when a settled design holds for this tree with settled_keep, else (False, 'not
    settled: <why>')."""
    return _recorded(root, SETTLED, settled_keep(config.load(root).paths), 'settled', 'the settled design',
                     'nothing settled recorded')


def record_settled(root):
    """`.cache/omc/settled/<HEAD sha>.json`; refused when the tree has changes the record would not cover."""
    return _record(root, SETTLED, settled_keep(config.load(root).paths), 'a settled design')
