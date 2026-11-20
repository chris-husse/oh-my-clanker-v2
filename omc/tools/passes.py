"""The count of a repeated design pass, `just omc pass <harden|consistency>` (three at most, on the tiers of omc/config.yaml): the first pass of ▣
harden runs on the role `harden` (the `max` tier, Fable once), every later one on `harden-repeat` (the `medium` tier);
every pass of ▣ consistency on the orchestrator, counted all the same. The count is the tool's, not the session's, so that a restart or a
compaction cannot reset it: `.cache/omc/passes.json`, `{"<branch>": {"<record>": {"harden": n, "consistency": n}}}`,
written to a temporary file and renamed; `just omc settled --record` removes the branch's entry. The standard library
only; every git call goes through repo."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import done  # noqa: E402
import repo  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

PASSES = os.path.join('.cache', 'omc', 'passes.json')


def _branch(root):
    return repo.output(root, 'rev-parse', '--abbrev-ref', 'HEAD').strip()


def _read(root):
    """The counts; {} when the file is missing or does not parse."""
    try:
        with open(os.path.join(root, PASSES), encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(root, data):
    done._write_atomic(os.path.join(root, PASSES), json.dumps(data, indent=2, sort_keys=True) + '\n')


def role_of(terminal, n):
    """The role and tier of pass [n] of [terminal]: ▣ harden's first `harden` on the `max` tier, every later one
    `harden-repeat` on the `medium` tier; ▣ consistency always the orchestrator."""
    if terminal == 'consistency':
        return config.ORCHESTRATOR, config.ORCHESTRATOR
    return ('harden', config.HARDEN_TIER) if n == 1 else ('harden-repeat', config.HARDEN_REPEAT_TIER)


def next_pass(root, terminal):
    """Counts one more pass of [terminal] for the branch and its one record; {'terminal', 'pass', 'role', 'tier'}, as
    role_of says, the role for `just omc models <role>`. Refused for a terminal that is not counted, and
    when the branch committed no record or more than one."""
    if terminal not in config.VERBS['pass']:
        raise Refused(f'pass takes one of {", ".join(config.VERBS["pass"])}, not `{terminal}`')
    found = repo.records(root)
    if len(found) != 1:
        raise Refused('no record committed on this branch' if not found
                      else f'{len(found)} records committed on this branch: {", ".join(found)}')
    branch, record = _branch(root), found[0]
    data = _read(root)
    counts = data.setdefault(branch, {}).setdefault(record, {})
    n = int(counts.get(terminal, 0)) + 1
    counts[terminal] = n
    _write(root, data)
    role, tier = role_of(terminal, n)
    return {'terminal': terminal, 'pass': n, 'role': role, 'tier': tier}


def clear(root):
    """Removes the branch's counts; nothing when it has none."""
    data = _read(root)
    if data.pop(_branch(root), None) is not None:
        _write(root, data)
