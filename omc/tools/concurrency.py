"""The machine-wide slots of a gate: how many runs of `check`, `build` or `verify` run at once on this machine, over
every checkout and worktree (omc/config.yaml's `concurrency`, config.concurrency; absent: 1).

The registry is `~/.cache/omc/gates/<gate>/slot-<k>`, `k` in `0..limit-1` (`OMC_GATE_REGISTRY` names another folder,
for the tests). A run holds one slot file with a non-blocking `flock(LOCK_EX)` for as long as it runs; the file then
says who holds it, `<uuid> <root> <gate> <pid>`, the uuid the checkout's `.cache/omc/workspace.uuid`. A slot is a lock
of the holding process, never of the uuid: a checkout copied with its `.cache/` (a duplicate uuid) still counts as two
runs, and a holder killed even by SIGKILL frees its slot at once, as the kernel drops its locks. The lock's file
descriptor is not inherited by the gate's command. When every slot is held, the taker logs
`max concurrency of <gate> reached (<n> of <n> running: <uuid> <root>, …); waiting`, polls every 2 s and logs again
each minute. The standard library only."""
import contextlib
import fcntl
import os
import time
import uuid

REGISTRY_ENV = 'OMC_GATE_REGISTRY'
WORKSPACE_ID = os.path.join('.cache', 'omc', 'workspace.uuid')
POLL = 2.0  # seconds between two tries of the slots
EVERY = 60.0  # seconds between two wait lines


def registry(gate):
    """The folder of [gate]'s slots."""
    base = os.environ.get(REGISTRY_ENV) or os.path.join(os.path.expanduser('~'), '.cache', 'omc', 'gates')
    return os.path.join(base, gate)


def _read_id(path):
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read().strip()
        uuid.UUID(text)
        return text
    except (OSError, ValueError):
        return None


def workspace_id(root):
    """The id of the checkout at [root], `.cache/omc/workspace.uuid`: read, or written once (a `uuid4`) when missing
    or not a uuid; two first calls at once agree, the file is linked into place whole."""
    path = os.path.join(root, WORKSPACE_ID)
    found = _read_id(path)
    if found:
        return found
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = str(uuid.uuid4())
    tmp = f'{path}.tmp-{os.getpid()}-{new}'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(new + '\n')
    try:
        os.link(tmp, path)
    except FileExistsError:
        found = _read_id(path)
        if found:
            return found
        os.replace(tmp, path)  # a file there that is no uuid: ours replaces it
        return new
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(tmp)
    return new


def _holder(path):
    """`<uuid> <root>` of the slot file [path], `?` when it says nothing yet."""
    try:
        with open(path, encoding='utf-8') as f:
            words = f.read().split(' ')
    except OSError:
        return '?'
    if len(words) < 4:
        return '?'
    return ' '.join(words[:-2])


def _try(path, line):
    """The open descriptor of slot file [path], locked and holding [line]; None when another holds it."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    os.ftruncate(fd, 0)
    os.pwrite(fd, line.encode(), 0)
    return fd


@contextlib.contextmanager
def slot(root, gate, limit, log):
    """Holds one of [limit] slots of [gate] for the block, the checkout at [root] its holder; while every slot is
    held, [log] (a callable of one line) gets the wait line at once and again each minute."""
    folder = registry(gate)
    os.makedirs(folder, exist_ok=True)
    line = f'{workspace_id(root)} {root} {gate} {os.getpid()}'
    paths = [os.path.join(folder, f'slot-{k}') for k in range(limit)]
    logged = None
    while True:
        for path in paths:
            fd = _try(path, line)
            if fd is not None:
                break
        else:
            now = time.monotonic()
            if logged is None or now - logged >= EVERY:
                running = ', '.join(_holder(p) for p in paths)
                log(f'max concurrency of {gate} reached ({limit} of {limit} running: {running}); waiting')
                logged = now
            time.sleep(POLL)
            continue
        break
    try:
        yield
    finally:
        os.ftruncate(fd, 0)  # still held: nobody reads a stale holder
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
