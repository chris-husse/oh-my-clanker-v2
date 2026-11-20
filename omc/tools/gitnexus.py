"""GitNexus for the omc/ pipeline, behind `just omc gitnexus <verb>`: the fork's checkout, its build and its embedding runtime under `~/.omc/tools/gitnexus`, outside every
checkout and shared by them, at the commit `gitnexus` of omc/config.yaml pins. The mechanisms are the old CLI's
(oh-my-clanker 2ce00cd, src/omc/gitnexus.py: `ensure_gitnexus`, `_clone_if_missing`, `_build`, `ensure_embeddings`,
`_embeddings_ready`; src/omc/toolctx.py: `gitnexus_env`); its omc-specific plumbing is not kept. `refresh` keeps the
primary checkout's index (its `.gitnexus/`, never a worktree's) at the base's tip, after the old `refresh_knowledge`,
`_run_analyze`, `_backfill_embeddings`, `_destroy_and_rebuild` and `_store_heartbeat`; the read verbs ask that index,
scoped to the base, from any checkout (the old src/omc/internal.py). The standard library only;
every path is expanded at call time, so `HOME` moves the install (the tests' only lever)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import repo  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

HOME = '~/.omc/tools/gitnexus'
CXX_STD = '-std=c++20'  # Node 26 headers need C++20; the fork's tree-sitter hardcodes c++17 (the old _native_build_env)
RUNTIME_PACKAGES = ('@huggingface/transformers', 'onnxruntime-node')  # one alone is an interrupted install

Paths = namedtuple('Paths', 'home checkout cli runtime hf')

STORE = '.gitnexus'
META_NAMES = ('gitnexus.json', 'meta.json')  # upstream's new name first, the fork's legacy one after (read_index_meta)
NODE_CAP = 50_000  # GitNexus's default embedding cap: analyze skips embedding over it, `embeddings sync` does not
POLL = 1.0  # seconds between two looks at a long step's child
BEAT = 60.0  # seconds between two liveness lines of a long step; the child is never killed
NOT_INSTALLED = 'GitNexus not installed: just omc gitnexus install'
READS = ('query', 'context', 'impact', 'cypher')


class Failed(Exception):
    """A GitNexus step that did not finish; its message is the `[failed] <why>` reason."""


def paths():
    """The install's places under `HOME`: the fork's checkout, its built CLI, the embedding runtime and the model
    cache, the last two beside the checkout so a forced checkout of a moved pin never touches them."""
    home = os.path.expanduser(HOME)
    checkout = os.path.join(home, 'gitnexus')
    return Paths(home, checkout, os.path.join(checkout, 'gitnexus', 'dist', 'cli', 'index.js'),
                 os.path.join(home, 'embeddings', 'runtime'), os.path.join(home, 'embeddings', 'hf'))


def env(write):
    """The environment of every GitNexus child, os.environ under it: the local store, the runtime and the model
    cache; the LadybugDB extension install on the write paths only (analyze, `embeddings sync`)."""
    p = paths()
    merged = dict(os.environ, GITNEXUS_SHARED_STORE='off', GITNEXUS_EMBEDDING_RUNTIME_DIR=p.runtime, HF_HOME=p.hf)
    if write:
        merged['GITNEXUS_LBUG_EXTENSION_INSTALL'] = 'auto'
    else:
        merged.pop('GITNEXUS_LBUG_EXTENSION_INSTALL', None)
    return merged


def argv(*args):
    """The command line of the built CLI with [args]."""
    return ['node', paths().cli, *args]


def say_to_stderr(line):
    print(line, file=sys.stderr, flush=True)


def git(*args, check=True):
    r = subprocess.run(('git', *args), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise Failed(f'git {" ".join(args)}: {(r.stderr or r.stdout).strip()[:400]}')
    return r


def head(checkout):
    """The checkout's HEAD sha, or None when there is no checkout."""
    if not os.path.isdir(os.path.join(checkout, '.git')):
        return None
    r = git('-C', checkout, 'rev-parse', '--verify', '-q', 'HEAD^{commit}', check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def runtime_ready():
    """Both runtime packages are in the runtime's node_modules (the old _embeddings_ready)."""
    modules = os.path.join(paths().runtime, 'node_modules')
    return all(os.path.isfile(os.path.join(modules, p, 'package.json')) for p in RUNTIME_PACKAGES)


def installed(cfg):
    """The checkout is at the pin, built, and its embedding runtime ready."""
    p = paths()
    return head(p.checkout) == cfg.gitnexus_commit and os.path.isfile(p.cli) and runtime_ready()


def captured(command, cwd, environment, **kw):
    """[command] in [cwd], its output captured, whatever its exit code; raises Failed when it cannot start."""
    try:
        return subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, **kw)
    except FileNotFoundError:
        raise Failed(f'{command[0]} not on PATH') from None


def run(command, cwd, environment, shown):
    """[command] in [cwd]; raises Failed, saying [shown] and its output's tail, when it does not exit 0."""
    r = captured(command, cwd, environment)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip()[-800:]
        raise Failed(f'{shown} failed' + (f':\n{tail}' if tail else ''))


def clone_or_fetch(cfg, say):
    """The checkout of the pinned commit: cloned when absent; an existing clone of another origin is refused, never
    re-pointed (the old _clone_if_missing); the pin fetched when the clone lacks it."""
    checkout = paths().checkout
    if not os.path.isdir(os.path.join(checkout, '.git')):
        say(f'→ GitNexus: cloning {cfg.gitnexus_origin}')
        os.makedirs(os.path.dirname(checkout), exist_ok=True)
        git('clone', '-q', cfg.gitnexus_origin, checkout)
    else:
        origin = git('-C', checkout, 'remote', 'get-url', 'origin', check=False).stdout.strip()
        if origin != cfg.gitnexus_origin:
            raise Failed(f'{checkout} is a clone of {origin or "nothing"}, not of {cfg.gitnexus_origin}: '
                         'remove it to install again')
    pin = cfg.gitnexus_commit
    if git('-C', checkout, 'cat-file', '-e', f'{pin}^{{commit}}', check=False).returncode != 0:
        say(f'→ GitNexus: fetching {pin[:7]}')
        git('-C', checkout, 'fetch', '-q', 'origin')
        if git('-C', checkout, 'cat-file', '-e', f'{pin}^{{commit}}', check=False).returncode != 0:
            git('-C', checkout, 'fetch', '-q', 'origin', pin)
    git('-C', checkout, 'checkout', '-q', '-f', '--detach', pin)


def build(say):
    """The old _build, in its order: gitnexus-shared's install, then gitnexus's `ci` and `build`, each with
    `-std=c++20` appended to CXXFLAGS (the old _native_build_env)."""
    p = paths()
    environment = env(False)
    environment['CXXFLAGS'] = f'{environment.get("CXXFLAGS", "").strip()} {CXX_STD}'.strip()
    say('→ GitNexus: building')
    for command, package in ((['npm', 'install', '--no-audit', '--no-fund'], 'gitnexus-shared'),
                             (['npm', 'ci'], 'gitnexus'), (['npm', 'run', 'build'], 'gitnexus')):
        run(command, os.path.join(p.checkout, package), environment, f'{" ".join(command)} in {package}/')
    if not os.path.isfile(p.cli):
        raise Failed('the build exited 0 but left no gitnexus/dist/cli/index.js')


def install(cfg, say=say_to_stderr):
    """`just omc gitnexus install`: nothing to do when installed(cfg); else clone or fetch, a forced checkout of the
    pin when HEAD is another sha, the build when the CLI is missing or HEAD moved, then `embeddings install` when the
    runtime is not ready or the build ran (a rebuilt checkout may pin another runtime stack). The sha; raises Failed."""
    pin = cfg.gitnexus_commit
    done = f'GitNexus {pin[:7]} installed [ok]'
    if installed(cfg):
        say(done)
        return pin
    for tool in ('node', 'npm'):
        if shutil.which(tool) is None:
            raise Failed(f'{tool} not on PATH')
    p = paths()
    moved = head(p.checkout) != pin
    if moved:
        clone_or_fetch(cfg, say)
    built = False
    if moved or not os.path.isfile(p.cli):
        build(say)
        built = True
    if built or not runtime_ready():
        say('→ GitNexus: installing the embedding runtime')
        run(argv('embeddings', 'install'), p.home, env(False), 'gitnexus embeddings install')
        if not runtime_ready():
            raise Failed(f'embeddings install exited 0 but the runtime lacks one of {", ".join(RUNTIME_PACKAGES)}')
    say(done)
    return pin


# ─── refresh ───────────────────────────────────────────────────────────────


def primary_root(cwd):
    """The primary checkout: the parent of the git common dir, the same from it and from any of its worktrees."""
    r = repo.git(cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if r.returncode != 0 or not r.stdout.strip():
        raise Refused('not inside a git repository')
    return os.path.dirname(r.stdout.strip().rstrip('/'))


def index_meta(primary):
    """The index's metadata, `gitnexus.json` first, else `meta.json`; an unreadable one counts as missing (the old
    read_index_meta). None when there is no index."""
    for name in META_NAMES:
        path = os.path.join(primary, STORE, name)
        if os.path.isfile(path):
            try:
                with open(path, encoding='utf-8') as f:
                    data = json.load(f)
            except (OSError, ValueError):
                return None
            return data if isinstance(data, dict) else None
    return None


def indexed_at(primary):
    """The commit the primary's index records (`lastCommit`), or None."""
    last = (index_meta(primary) or {}).get('lastCommit')
    return last if isinstance(last, str) and last else None


def stat(meta, key):
    """`stats.<key>` of [meta] as an int; absent or not an int: 0."""
    value = (meta or {}).get('stats', {}).get(key) if isinstance((meta or {}).get('stats'), dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def stale(primary, base, head):
    """Why the primary's index is not the base's tip [head], as words (the old snapshot_freshness): `missing`,
    `owner` (the store is stamped with another branch: analyzes land in a sub-slot nothing reads), `foreign` (built
    for another checkout), `dirty` (an analyze did not finish), `behind`. Empty: current."""
    meta = index_meta(primary)
    if meta is None:
        return ['missing']
    reasons = []
    owner = meta.get('branch')
    if isinstance(owner, str) and owner and owner != base:
        reasons.append('owner')
    recorded = meta.get('repoPath')
    if isinstance(recorded, str) and recorded and os.path.realpath(recorded) != os.path.realpath(primary):
        reasons.append('foreign')
    if meta.get('incrementalInProgress'):
        reasons.append('dirty')
    if meta.get('lastCommit') != head:
        reasons.append('behind')
    return reasons


def clock(seconds):
    """An elapsed time as the step lines show it: `41s`, `2m14s`."""
    seconds = int(seconds)
    return f'{seconds // 60}m{seconds % 60:02d}s' if seconds >= 60 else f'{seconds}s'


def fingerprint(path):
    """The tree under [path] as (files, newest mtime, total size); None while it is absent (the old _dir_heartbeat)."""
    if not os.path.isdir(path):
        return None
    count = newest = size = 0
    for where, _dirs, files in os.walk(path):
        for name in files:
            try:
                st = os.stat(os.path.join(where, name))
            except OSError:
                continue  # renamed away mid-walk; the next look sees it
            count, newest, size = count + 1, max(newest, st.st_mtime_ns), size + st.st_size
    return count, newest, size


def watched(command, primary, what, say):
    """[command] in [primary] on the write environment, for a step that prints nothing off a TTY for minutes (the
    embedding analyze, `embeddings sync`): liveness is the store's growth (the old _store_heartbeat), said with the
    elapsed time once a minute, and the child is never killed. (exit code, its output's tail)."""
    with tempfile.TemporaryFile('w+', encoding='utf-8', errors='replace') as out:
        try:
            child = subprocess.Popen(command, cwd=primary, env=env(True), stdin=subprocess.DEVNULL, stdout=out,
                                     stderr=subprocess.STDOUT, text=True)
        except FileNotFoundError:
            raise Failed(f'{command[0]} not on PATH') from None
        start = next_beat = time.monotonic()
        next_beat += BEAT
        last = fingerprint(os.path.join(primary, STORE))
        while True:
            try:
                code = child.wait(timeout=POLL)
                break
            except subprocess.TimeoutExpired:
                pass
            now = time.monotonic()
            if now >= next_beat:
                beat = fingerprint(os.path.join(primary, STORE))
                say(f'· {what}: {clock(now - start)}, the store {"growing" if beat != last else "unchanged"}')
                last, next_beat = beat, now + BEAT
        out.seek(0)
        return code, out.read().strip()[-800:]


def analyze(primary, base, embed, say):
    """One analyze of the primary, with `--embeddings` when [embed]; an embedding analyze that fails is said and
    retried once keyword-only, so a model download dying offline never costs the index (the old _run_analyze).
    Whether embedding failed this run; a keyword-only analyze that fails is said only: the verdict after it decides."""
    command = argv('analyze', '--skip-agents-md', '--skip-skills', '--branch', base)
    if embed:
        code, tail = watched([*command, '--embeddings'], primary, 'analyze with embeddings', say)
        if code == 0:
            return False
        say(f'· analyze with embeddings failed (exit {code}): {tail[-400:]}; retrying keyword-only')
    r = captured(command, primary, env(True), stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        say(f'· analyze failed (exit {r.returncode}): {(r.stderr or r.stdout).strip()[-400:]}')
    return embed


def rebuild(primary, base, embed, say):
    """The store cleared and indexed from scratch (the old _destroy_and_rebuild): `clean --force`, judged by its
    post-condition (it exits 0 when the deletion fails), the store's remains removed, then one analyze. Whether
    embedding failed; raises Failed when the store cannot be cleared or node cannot start."""
    captured(argv('clean', '--force'), primary, env(True), stdin=subprocess.DEVNULL)
    store = os.path.join(primary, STORE)
    shutil.rmtree(store, ignore_errors=True)
    if os.path.exists(store):
        raise Failed(f'cannot clear {store}')
    return analyze(primary, base, embed, say)


def backfill(primary, say):
    """The one-time `embeddings sync` of an index with no vectors (the old _backfill_embeddings): analyze says
    "Already up to date" whatever its flags, so an index built keyword-only would gain vectors one commit at a time.
    Its failure is said only."""
    say('→ GitNexus: embedding the existing index (one-time)')
    code, tail = watched(argv('embeddings', 'sync', primary), primary, 'embeddings sync', say)
    if code != 0:
        say(f'· embeddings sync failed (exit {code}): {tail[-400:]}')
    elif stat(index_meta(primary), 'embeddings') == 0:
        say('· embeddings sync exited 0 but the index still has no vectors')


def refresh(primary, base, say=say_to_stderr):
    """`just omc gitnexus refresh`: the primary's index at its HEAD on [base]. Current: `index current [ok]` and
    `'current'`. Else the cheapest step first: an incremental analyze (with embeddings when the runtime is ready),
    escalated once to a cleared store and a full analyze when the index is still stale after it; a store owned by
    another branch is cleared at once. Then the backfill when the index has nodes but no vectors (not over the node
    cap, not after an embedding failure of this run). `'embeddings'` or `'keyword-only'`, said on the last line.
    Raises Refused for a primary off [base] (nothing written), Failed for no build or an index still stale."""
    if not os.path.isfile(paths().cli):
        raise Failed(NOT_INSTALLED)
    branch = repo.git(primary, 'symbolic-ref', '--short', '-q', 'HEAD').stdout.strip()
    if branch != base:
        raise Refused(f'the primary checkout is on {branch or "a detached HEAD"}, not {base}: the index is '
                      f'refreshed on {base} only')
    head = repo.output(primary, 'rev-parse', 'HEAD').strip()
    embed = runtime_ready()
    failed = False
    reasons = stale(primary, base, head)
    if reasons:
        if 'owner' in reasons:
            say(f'→ GitNexus: the index is owned by {index_meta(primary).get("branch")!r}, not {base!r}: rebuilding')
            failed = rebuild(primary, base, embed, say)
        else:
            say(f'→ GitNexus: analyzing {head[:7]} ({", ".join(reasons)})')
            failed = analyze(primary, base, embed, say)
            again = stale(primary, base, head)
            if again:
                say(f'→ GitNexus: still stale after the analyze ({", ".join(again)}): rebuilding')
                failed = rebuild(primary, base, embed and not failed, say) or failed
        again = stale(primary, base, head)
        if again:
            raise Failed(f'the index is still stale after a rebuild ({", ".join(again)})')
    meta = index_meta(primary)
    nodes = stat(meta, 'nodes')
    backfilled = embed and not failed and nodes and stat(meta, 'embeddings') == 0
    if backfilled and nodes > NODE_CAP:
        say(f'· the index is over GitNexus\'s {NODE_CAP}-node embedding cap: it stays keyword-only')
        backfilled = False
    elif backfilled:
        backfill(primary, say)
    if not reasons and not backfilled:
        say('index current [ok]')
        return 'current'
    how = 'embeddings' if stat(index_meta(primary), 'embeddings') > 0 else 'keyword-only'
    say(f'index at {head[:7]} ({how}) [ok]')
    return how


# ─── the read verbs ────────────────────────────────────────────────────────


def read(verb, args, cwd='.'):
    """`just omc gitnexus query|context|impact|cypher <args>`: the primary's graph scoped to the base (`--repo
    <primary> --branch <base>` on every call), from any checkout, on the read environment. One first line on stdout,
    `index at <sha>, base at <sha of origin/<base> in the primary>`, how far the graph lags; then GitNexus's answer
    as it gives it, and its exit code. Refused with no build or no index in the primary."""
    if verb not in READS:
        raise Refused(f'{verb} is not a read verb: one of {", ".join(READS)}')
    if not os.path.isfile(paths().cli):
        raise Refused(NOT_INSTALLED)
    primary = primary_root(cwd)
    base = config.load(repo.root(cwd)).base
    indexed = indexed_at(primary)
    if indexed is None:
        raise Refused(f'no GitNexus index in {primary}: just design refreshes it')
    r = repo.git(primary, 'rev-parse', '--verify', '-q', f'refs/remotes/origin/{base}^{{commit}}')
    tip = r.stdout.strip()[:7] if r.returncode == 0 and r.stdout.strip() else f'unknown (no origin/{base})'
    print(f'index at {indexed[:7]}, base at {tip}', flush=True)
    try:
        return subprocess.run(argv(verb, *args, '--repo', primary, '--branch', base), cwd=primary,
                              env=env(False)).returncode
    except FileNotFoundError:
        raise Refused('node not on PATH') from None
