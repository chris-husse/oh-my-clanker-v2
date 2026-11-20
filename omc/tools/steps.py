"""The step selection of a gate: `omc/bin/<gate>.steps.yaml` declares the gate's steps, and `just omc gate run <gate>`
runs only the stale ones, DVC deciding (done.gate_run); without the file the gate runs `omc/bin/<gate>` whole.

The step file is `steps:`, a list of mappings: `name` (unique), `run` (a command, run by bash at the root), and
optionally `inputs` (globs, `config.matches`' semantics; a folder matched counts as all it holds), `derive` (a command
printing one input path per line, run by bash at the root), `outs` (paths the step writes, which later steps may read)
and `lock` (`<path>/dvc.yaml:<stage>`, a committed stage with its own committed lock, which decides alone). A step
with none of them always runs.

DVC only decides and records: every step with inputs or outs is one stage of the root `dvc.yaml` and its params file
`dvc-params.json` (the command, the kind of machine and the list of the inputs, so that an input gone or a glob's new
match makes it stale), JSON, both written at each run and rewritten only when their text changed; `dvc status` names
the stale stages, `dvc commit --force` records a green one into the root `dvc.lock` (every out `cache: false`,
`persist: true`); no step is ever run by DVC. A stage is stale when an input, the list of its inputs, an out, its
command or the machine changed since it last passed; a step fed by a stale step's outs is stale too. The project holds
the DVC repository: `dvc init --no-scm` (DVC with git refuses the git-ignored root dvc.yaml) and git ignores
`/dvc.yaml`, `/dvc.lock` and `/dvc-params.json`. DVC is no dependency of omc: it runs as `uv run --frozen dvc` in the
project, its own environment; without it a step file is refused. The steps of every gate share the root files: a
step's name is its stage's, so two gates' steps of one name are one stage. The standard library only, but the
step file's YAML (pyyaml, omc's own)."""
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import dataclass

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

BIN = os.path.join('omc', 'bin')
ROOT_YAML = 'dvc.yaml'
PARAMS = 'dvc-params.json'
DVC = ('uv', 'run', '--frozen', 'dvc')
NO_DVC = 'step selection needs DVC in the project (uv run --frozen dvc)'
NO_REPO = 'step selection needs a DVC repository at the root: uv run --frozen dvc init --no-scm'
OUT = {'cache': False, 'persist': True}
KEYS = ('name', 'run', 'inputs', 'derive', 'outs', 'lock')
GLOB = re.compile(r'[*?\[]')  # an input with one of these is a glob, else a plain path
LOCK = re.compile(r'^(?:[^:]+/)?dvc\.yaml:[A-Za-z0-9_-]+$')


class StepFailed(Exception):
    """A step's inputs could not be derived, or DVC failed or answered what cannot be read: the gate is red, the
    message names the step or DVC's own words."""


@dataclass(frozen=True)
class Step:
    name: str
    run: str  # bash at the root
    inputs: tuple[str, ...] = ()  # globs
    derive: str | None = None  # a command printing one input path per line
    lock: str | None = None  # `<path>/dvc.yaml:<stage>`, a committed stage with its own lock
    outs: tuple[str, ...] = ()  # paths the step writes, repo-relative

    @property
    def staged(self):
        """Whether DVC decides about this step (else it always runs)."""
        return bool(self.inputs or self.derive or self.lock or self.outs)

    @property
    def address(self):
        """What `dvc status` and `dvc commit` name its stage by: the committed `FILE:STAGE`, or the root stage."""
        return self.lock or stage_name(self.name)


def stage_name(name):
    """The DVC stage name of the step [name]: every run of other characters than [A-Za-z0-9_-] a '-', stripped."""
    return re.sub(r'[^A-Za-z0-9_-]+', '-', name).strip('-')


def path_of(root, gate):
    return os.path.join(root, BIN, f'{gate}.steps.yaml')


def _strings(where, key, value):
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise Refused(f'{where}: `{key}` is not a list of paths')
    return tuple(value)


def load(root, gate):
    """The steps of `omc/bin/<gate>.steps.yaml`, in the file's order; None when there is no such file. Refused for a
    file that is no YAML, holds no `steps` list, a step without a `name` or a `run`, a name twice (or two that make one
    stage name), a key omc does not read, a list that is none, or a `lock` that names no `dvc.yaml:<stage>`."""
    path = path_of(root, gate)
    where = os.path.relpath(path, root)
    try:
        with open(path, encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return None
    except OSError as e:
        raise Refused(f'cannot read {where}: {e.strerror}') from None
    except yaml.YAMLError as e:
        raise Refused(f'{where} is not YAML: {e}') from None
    items = data.get('steps') if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise Refused(f'{where}: `steps` is not a list of steps')
    found, names = [], set()
    for k, item in enumerate(items, 1):
        at = f'{where}: step {k}'
        if not isinstance(item, dict):
            raise Refused(f'{at} is not a mapping')
        other = [key for key in item if key not in KEYS]
        if other:
            raise Refused(f'{at}: `{other[0]}` is no key of a step ({", ".join(KEYS)})')
        name, run = item.get('name'), item.get('run')
        if not isinstance(name, str) or not stage_name(name):
            raise Refused(f'{at} has no `name`')
        if not isinstance(run, str) or not run.strip():
            raise Refused(f'{at} ({name}) has no `run` command')
        if stage_name(name) in names:
            raise Refused(f'{where}: the step {name} is named twice')
        names.add(stage_name(name))
        derive, lock = item.get('derive'), item.get('lock')
        if derive is not None and (not isinstance(derive, str) or not derive.strip()):
            raise Refused(f'{at} ({name}): `derive` is not a command')
        if lock is not None and (not isinstance(lock, str) or not LOCK.match(lock)):
            raise Refused(f'{at} ({name}): `lock` is not `<path>/dvc.yaml:<stage>`')
        found.append(Step(name, run, _strings(at, 'inputs', item.get('inputs', [])), derive, lock,
                          _strings(at, 'outs', item.get('outs', []))))
    return found


def _glob_paths(root, globs):
    """The repo-relative paths under [root] that one of [globs] matches (config.matches), outside `.git`; a folder
    matched stands for itself, its contents not listed again."""
    found = []
    for d, dirs, files in os.walk(root):
        rel = os.path.relpath(d, root)
        rel = '' if rel == '.' else rel.replace(os.sep, '/') + '/'
        dirs.sort()
        keep = []
        for name in dirs:
            if not rel and name == '.git':
                continue
            if config.matches(rel + name, globs):
                found.append(rel + name)
            else:
                keep.append(name)
        dirs[:] = keep
        found += [rel + f for f in sorted(files) if config.matches(rel + f, globs)]
    return found


def _derived(root, step):
    """The paths [step]'s `derive` command prints, one per line, normalized; StepFailed when it exits non-zero or
    prints a path outside the root."""
    r = subprocess.run(('bash', '-c', step.derive), cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        why = (r.stderr.strip() or r.stdout.strip()).split('\n')[-1]
        raise StepFailed(f'step {step.name}: its derive command failed (exit {r.returncode})'
                         + (f': {why}' if why else ''))
    found = []
    for line in r.stdout.split('\n'):
        line = line.strip()
        if not line:
            continue
        path = os.path.normpath(os.path.relpath(line, root) if os.path.isabs(line) else line).replace(os.sep, '/')
        if path == '..' or path.startswith('../'):
            raise StepFailed(f'step {step.name}: its derive command printed {line}, outside the root')
        found.append(path)
    return found


def inputs_of(root, step):
    """Every input of [step], repo-relative, sorted and unique: its plain paths (there or not: a missing one DVC calls
    deleted), its globs' matches and its derived paths."""
    literal = [os.path.normpath(g).replace(os.sep, '/') for g in step.inputs if not GLOB.search(g)]
    return tuple(sorted({*literal, *_glob_paths(root, [g for g in step.inputs if GLOB.search(g)]),
                         *(_derived(root, step) if step.derive else ())}))


def _texts(steps, deps):
    """(the root dvc.yaml's text, the params file's text): JSON, which YAML reads, of every staged step but a
    committed one."""
    stages, params = {}, {}
    for s in steps:
        if not s.staged or s.lock:
            continue
        name = stage_name(s.name)
        stage = {'cmd': f'omc gate step {name}', 'deps': list(deps[s.name]), 'params': [{PARAMS: [name]}]}
        if s.outs:
            stage['outs'] = [{o: dict(OUT)} for o in s.outs]
        stages[name] = stage
        params[name] = {'run': s.run, 'platform': platform.system(), 'inputs': list(deps[s.name])}
    dump = lambda value: json.dumps(value, indent=2) + '\n'  # noqa: E731
    return dump({'stages': stages}), dump(params)


def _write(root, steps, deps):
    for name, text in zip((ROOT_YAML, PARAMS), _texts(steps, deps)):
        path = os.path.join(root, name)
        try:
            with open(path, encoding='utf-8') as f:
                if f.read() == text:
                    continue
        except OSError:
            pass
        tmp = f'{path}.tmp-{os.getpid()}'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, path)


def _dvc(root, *args):
    """(exit code, stdout and stderr) of `uv run --frozen dvc <args>` at [root]; Refused (NO_DVC) when it cannot
    start, so when uv cannot."""
    try:
        r = subprocess.run((*DVC, *args), cwd=root, capture_output=True, text=True)
    except OSError:
        raise Refused(NO_DVC) from None
    return r.returncode, r.stdout + r.stderr


def _has_dvc(root):
    code, _ = _dvc(root, '--version')
    return code == 0


def _failed(root, what, code, out):
    """The refusal or the StepFailed of a DVC call that exited [code]: NO_DVC when DVC does not start at all."""
    if not _has_dvc(root):
        return Refused(NO_DVC)
    return StepFailed(f'{what} failed (exit {code}):\n{out.strip()}')


def _json_object(text):
    """The first JSON object of [text] (DVC may print a warning before it), or None."""
    decoder = json.JSONDecoder()
    for m in re.finditer(r'\{', text):
        try:
            value, _ = decoder.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _overlap(a, b):
    return a == b or a.startswith(b + '/') or b.startswith(a + '/')


def _downstream(steps, deps, stale):
    """[stale] and, transitively, every staged step one of whose inputs is, holds or lies inside an out of one of
    them: a step fed by a stale step's outs runs, though DVC called it fresh before they were written."""
    by = {s.name: s for s in steps}
    out, todo = set(stale), list(stale)
    while todo:
        outs = by[todo.pop()].outs
        for s in steps:
            if s.name not in out and s.staged and any(_overlap(d, o) for d in deps[s.name] for o in outs):
                out.add(s.name)
                todo.append(s.name)
    return out


def selection(root, steps):
    """(the names of the stale steps, in the steps' order, {name: its inputs}): stale is every step DVC does not
    decide (`Step.staged`), every stage `dvc status` names, and the steps their outs feed. Writes the root dvc.yaml
    and its params file. StepFailed when a derive command or DVC fails; Refused when the root holds no DVC repository
    or DVC does not start (NO_DVC)."""
    deps = {s.name: inputs_of(root, s) for s in steps}
    staged = [s for s in steps if s.staged]
    found = set()
    if staged:
        if not os.path.isdir(os.path.join(root, '.dvc')):
            raise Refused(NO_REPO if _has_dvc(root) else NO_DVC)
        _write(root, steps, deps)
        code, out = _dvc(root, 'status', '--json', *(s.address for s in staged))
        answer = _json_object(out) if code == 0 else None
        if answer is None and code == 0 and not out.strip():
            answer = {}
        if answer is None:
            raise _failed(root, 'dvc status', code, out)
        addresses = {k.removeprefix(f'{ROOT_YAML}:') for k in answer}
        found = _downstream(steps, deps, {s.name for s in staged if s.address in addresses})
    return [s.name for s in steps if not s.staged or s.name in found], deps


def stale(root, steps):
    """The names of [steps] that run, in order (`selection`)."""
    return selection(root, steps)[0]


def record_green(root, step):
    """[step] recorded as it is now (`dvc commit --force` of its stage: its inputs' and outs' hashes into its lock);
    nothing for a step DVC does not decide. StepFailed when the commit fails."""
    if not step.staged:
        return
    code, out = _dvc(root, 'commit', '--force', step.address)
    if code != 0:
        raise _failed(root, f'dvc commit {step.address}', code, out)


def _ignored_names(root):
    """The plain folder names `.dvcignore` ignores everywhere or at the root (`**/x/`, `x/`, `/x/`): the folders the
    snapshot of a step's inputs leaves out, as DVC hashes nothing under them."""
    try:
        with open(os.path.join(root, '.dvcignore'), encoding='utf-8') as f:
            lines = f.read().split('\n')
    except OSError:
        return set()
    return {m.group(1) for line in lines if (m := re.fullmatch(r'(?:\*\*/|/)?([^/*?\[!#\s][^/*?\[]*)/', line.strip()))}


def snapshot(root, paths):
    """{file: (size, mtime)} of every file at or under [paths] (repo-relative), the folders `.dvcignore` names left
    out: an input edited while its step ran changes it."""
    skip, out = _ignored_names(root), {}
    for p in paths:
        full = os.path.join(root, p)
        if os.path.isdir(full):
            for d, dirs, files in os.walk(full):
                dirs[:] = sorted(n for n in dirs if n not in skip)
                for f in files:
                    path = os.path.join(d, f)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    out[os.path.relpath(path, root)] = (st.st_size, st.st_mtime_ns)
        else:
            try:
                st = os.stat(full)
            except OSError:
                continue
            out[p] = (st.st_size, st.st_mtime_ns)
    return out
