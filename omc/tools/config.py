"""The omc/ pipeline's config, omc/config.yaml: the base branch, the branch prefix, the
orchestrator's model, the hand-off flag `ask_for_provider_handoff` (absent: false), the tiers of `models`, the
`complexity` mapping of a plan task's `Complexity:` line to a tier or the orchestrator, Claude's models only,
the `gitnexus` pin, the fork's origin and full commit sha, the gates' `concurrency` (runs of a gate at once on the
machine, absent: 1) and `silence` (seconds without output before a gate run is killed, absent: none), and
`paths`, every path of the project the tools read (`Paths`; absent: the defaults, every glob list empty; `links`,
the files links-check reads, absent: the protected ones; `product`, what the project ships, absent: a plan's
`Gate: build` is the plan writer's reading alone).
Read with `yaml.safe_load`, so through the justfile's `uv run --frozen python -I` (pyyaml is pinned); the names every
verb of `just omc` and `just design` share live here: `VERBS`, `PIPELINE`, `GATES`, `ROLES`."""
import glob
import os
import re
from dataclasses import dataclass, fields

import yaml

# Every verb of `just omc` and the words it takes after it (omc/tools/omc.py)
VERBS = {'enter': (), 'record': (), 'plan': (), 'git': ('rebased-on', 'one-commit', 'clean'), 'rebase': (),
         'impact': (), 'gate': ('run', 'passed', 'skip'), 'reviewed': (), 'settled': (), 'models': (), 'handoff': (),
         'lint': (), 'gitnexus': ('install', 'refresh', 'query', 'context', 'impact', 'cypher'),
         'title': ('set', 'release', 'apply'), 'shell-integration': ('fish',), 'pass': ('harden', 'consistency'),
         'shots': ('pairs', 'accepted', 'path'), 'todos': ()}
# The four skills of omc/pipeline/, the words `just omc enter` takes
PIPELINE = ('brainstorm', 'design', 'implement', 'audit')
# The three gate terminals of omc/terminals/ that are also skills, /check, /build, /verify
GATES = ('check', 'build', 'verify')
# The roles of `just omc models`: the orchestrator, ▣ harden's first pass (the `max` tier), every later pass of ▣ harden
# (`harden-repeat`, the `medium` tier: `just omc pass harden`), then a coding task's `Complexity:`
ROLES = ('orchestrator', 'harden', 'harden-repeat', 'simple', 'medium', 'high')
COMPLEXITIES = ('simple', 'medium', 'high')
HARDEN_TIER = 'max'
HARDEN_REPEAT_TIER = 'medium'
ORCHESTRATOR = 'orchestrator'  # the `complexity` value naming `orchestrator-model`
# The cheap/fast tier: a model whose name holds one of these is refused
CHEAP = ('haiku', 'mini', 'nano', 'flash')


class Refused(Exception):
    """The one refusal of every verb of `just omc` (exit 2, `error: <why>`): the config cannot be used, a question
    about it or about the repository has no answer; its message says why. omc.Refused and repo.Refused are this."""


@dataclass(frozen=True)
class Paths:
    """`paths` of omc/config.yaml, relative to the repository's root: the glob lists (`matches`) are empty by default,
    so the steps that read them find nothing and pass; a folder ends with `/`."""
    protected: tuple[str, ...] = ()  # the documents that change only through an applied decision
    screenshots: tuple[str, ...] = ()  # the committed screenshots
    baselines: tuple[str, ...] = ()  # the files a gate regenerates and commits
    briefs: str = 'tasks/'
    specs: str = 'docs/superpowers/specs/'
    plans: str = 'docs/superpowers/plans/'
    decision_log: str = 'docs/decision-log.md'
    questions: str = 'docs/reviews/'
    themes: tuple[str, ...] = ()  # the theme files (rule ids)
    product: tuple[str, ...] = ()  # what the project ships: a branch changing none of it is gated by build (`Gate:`)
    links: tuple[str, ...] | None = None  # the files links-check reads (links_scope); absent: the protected ones
    todos: tuple[str, ...] | None = None  # the files whose TODO/FIXME comments are open work; absent: product

    @property
    def verdicts(self):
        """The folder of the shots' verdicts, one `<slug>.yaml` per branch (▣ screens-assess): `<questions>shots/`."""
        return f'{self.questions}shots/'

    @property
    def screen_reviews(self):
        """The folder of the owner's screenshot reviews, one file per round: `<questions>screens/`."""
        return f'{self.questions}screens/'


FOLDERS = ('briefs', 'specs', 'plans', 'questions')  # the `Paths` strings that name a folder


def matches(path, globs):
    """Whether [path] (relative, `/`-separated) matches one of [globs]: `*` and `?` stay within one folder, `**`
    spans any number of them, `docs/design/**/*.md` matches `docs/design/a.md` as well."""
    return any(re.fullmatch(glob.translate(g, recursive=True, include_hidden=True, seps='/'), path) for g in globs)


def links_scope(cfg):
    """The globs of the files links-check reads, of the config mapping [cfg]: `paths.links`, else `paths.protected`
    (the links tool adds the question files then), else none."""
    paths = cfg.get('paths') if isinstance(cfg.get('paths'), dict) else {}
    links = paths.get('links')
    return list(paths.get('protected') or ()) if links is None else list(links)


def _paths(path, data):
    """The `Paths` of the `paths` mapping [data] (None: every default); raises Refused for an unknown key, a glob
    list that is not a list of non-empty strings, or a path that is not a non-empty string."""
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise Refused(f'{path}: `paths` is not a mapping')
    known = {f.name: f for f in fields(Paths)}
    values = {}
    for key, value in data.items():
        if key not in known:
            raise Refused(f'{path}: paths.{key} is no path omc reads ({", ".join(known)})')
        if isinstance(known[key].default, str):
            if not isinstance(value, str) or not value:
                raise Refused(f'{path}: paths.{key} is not a non-empty string')
            values[key] = value if key not in FOLDERS or value.endswith('/') else value + '/'
        else:
            if not isinstance(value, list) or not all(isinstance(g, str) and g for g in value):
                raise Refused(f'{path}: paths.{key} is not a list of globs')
            values[key] = tuple(value)
    return Paths(**values)


@dataclass(frozen=True)
class Config:
    base: str
    branch_prefix: str
    orchestrator_model: str  # `orchestrator-model`
    ask_for_provider_handoff: bool  # absent: False
    tiers: dict  # `models`: tier -> model
    complexity: dict  # `complexity`: simple | medium | high -> a tier or `orchestrator`
    gitnexus_origin: str  # the fork's URL, `gitnexus.origin`
    gitnexus_commit: str  # the 40-hex sha `just omc gitnexus install` builds, `gitnexus.commit`
    paths: Paths  # `paths`, absent: the defaults


def _model(path, where, model):
    """[model] when it is a non-empty string outside the cheap/fast tier; else Refused."""
    if not isinstance(model, str) or not model:
        raise Refused(f'{path}: {where} is missing or not a string')
    cheap = [w for w in CHEAP if w in model.lower()]
    if cheap:
        raise Refused(f'{path}: {where} names `{model}`, the cheap/fast tier ({cheap[0]}), which the pipeline never '
                      'uses')
    return model


def raw(root):
    """The mapping of <root>/omc/config.yaml as YAML reads it, nothing checked but that it is one; raises Refused
    when the file is missing, unreadable, not YAML or not a mapping."""
    path = os.path.join(root, 'omc', 'config.yaml')
    try:
        with open(path, encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except OSError as e:
        raise Refused(f'cannot read {path}: {e.strerror}') from None
    except yaml.YAMLError as e:
        raise Refused(f'{path} is not YAML: {e}') from None
    if not isinstance(data, dict):
        raise Refused(f'{path} is not a mapping')
    return data


def _per_gate(cfg, key, gate):
    """The positive integer [cfg]'s mapping [key] gives [gate], None when the key or the gate is absent; raises
    Refused for a mapping that is none, names no gate of GATES, or a value that is no integer of at least 1."""
    table = cfg.get(key)
    if table is None:
        return None
    if not isinstance(table, dict):
        raise Refused(f'`{key}` is not a mapping of the gates ({", ".join(GATES)})')
    for name, value in table.items():
        if name not in GATES:
            raise Refused(f'{key} names `{name}`, no gate ({", ".join(GATES)})')
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise Refused(f'{key} `{name}` is `{value}`, not a whole number of at least 1')
    return table.get(gate)


def concurrency(cfg, gate):
    """How many runs of [gate] may run at once on this machine, of the config mapping [cfg] (`concurrency`): 1 when
    absent; Refused for a value below 1 (`_per_gate`)."""
    value = _per_gate(cfg, 'concurrency', gate)
    return 1 if value is None else value


def silence(cfg, gate):
    """The seconds without a byte of output after which a run of [gate] is killed, of the config mapping [cfg]
    (`silence`): None (never) when absent; Refused for a value below 1 (`_per_gate`)."""
    return _per_gate(cfg, 'silence', gate)


def load(root):
    """The config of the repository at [root], <root>/omc/config.yaml; raises Refused when it is missing, unreadable
    or not YAML, lacks a key, a tier or a complexity, names a cheap model, maps a complexity to no tier, holds a
    hand-off flag that is not a boolean, pins GitNexus to anything but a full sha, holds a `concurrency` or `silence`
    `_per_gate` refuses, or a `paths` entry `_paths` refuses."""
    path = os.path.join(root, 'omc', 'config.yaml')
    data = raw(root)
    for key in ('concurrency', 'silence'):
        try:
            _per_gate(data, key, GATES[0])
        except Refused as e:
            raise Refused(f'{path}: {e}') from None
    for key in ('base', 'branch_prefix'):
        if not isinstance(data.get(key), str) or not data[key]:
            raise Refused(f'{path}: `{key}` is missing or not a string')
    orchestrator = _model(path, '`orchestrator-model`', data.get('orchestrator-model'))
    handoff = data.get('ask_for_provider_handoff', False)
    if not isinstance(handoff, bool):
        raise Refused(f'{path}: `ask_for_provider_handoff` is not true or false')
    table = data.get('models')
    if not isinstance(table, dict) or not table:
        raise Refused(f'{path}: no `models` mapping of the tiers')
    tiers = {str(tier): _model(path, f'models `{tier}`', model) for tier, model in table.items()}
    for tier, what in ((HARDEN_TIER, '▣ harden'), (HARDEN_REPEAT_TIER, "▣ harden's later passes")):
        if tier not in tiers:
            raise Refused(f'{path}: models has no tier `{tier}` ({what})')
    mapping = data.get('complexity')
    if not isinstance(mapping, dict):
        raise Refused(f'{path}: no `complexity` mapping')
    complexity = {}
    for name in COMPLEXITIES:
        value = mapping.get(name)
        if value is None:
            raise Refused(f'{path}: complexity has no `{name}`')
        if not isinstance(value, str) or (value != ORCHESTRATOR and value not in tiers):
            raise Refused(f'{path}: complexity `{name}` is `{value}`, neither a tier of models '
                          f'({", ".join(tiers)}) nor `{ORCHESTRATOR}`')
        complexity[name] = value
    pin = data.get('gitnexus')
    if not isinstance(pin, dict):
        raise Refused(f'{path}: no gitnexus mapping')
    origin, commit = pin.get('origin'), pin.get('commit')
    if not isinstance(origin, str) or not origin:
        raise Refused(f'{path}: gitnexus origin is missing or not a string')
    if not isinstance(commit, str) or not re.fullmatch('[0-9a-f]{40}', commit):
        raise Refused(f'{path}: gitnexus commit is not a full sha')
    return Config(data['base'], data['branch_prefix'], orchestrator, handoff, tiers, complexity, origin, commit,
                  _paths(path, data.get('paths')))


def models(cfg, role):
    """The answer of `just omc models <role>`: {'role', 'model', 'effort'}, `effort` always '' (the harness's
    default); a complexity resolves through its tier, `orchestrator` through `orchestrator-model`; raises Refused for
    an unknown role."""
    if role not in ROLES:
        raise Refused(f'no role `{role}`; the roles are {", ".join(ROLES)}')
    if role == 'orchestrator':
        model = cfg.orchestrator_model
    elif role == 'harden':
        model = cfg.tiers[HARDEN_TIER]
    elif role == 'harden-repeat':
        model = cfg.tiers[HARDEN_REPEAT_TIER]
    else:
        tier = cfg.complexity[role]
        model = cfg.orchestrator_model if tier == ORCHESTRATOR else cfg.tiers[tier]
    return {'role': role, 'model': model, 'effort': ''}
