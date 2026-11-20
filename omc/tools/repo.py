"""The git facts of the omc/ pipeline: the worktree's root, the merge-base with
`origin/<base>`, the design record and the plan the branch added and committed since it (`just omc record`, `plan`),
the plan's next task and its ticks (`plan --next`, `plan --tick`), and `just omc git rebased-on | one-commit | clean`.
The standard library only; every git call goes through `git(root, …)`, the ones whose failure is a refusal through
`output(root, …)`."""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402

Refused = config.Refused  # the one refusal of every verb: exit 2, `error: <why>`

# A plan's task: from its `### Task <n>: <title>` heading to the next `### ` or `## ` heading
TASK = re.compile(r'^### Task (\d+):[ \t]*(.*?)\s*$')
END = re.compile(r'^###? ')
BOX = re.compile(r'^(\s*- )\[ \]')
COMPLEXITY = re.compile(r'^\**Complexity:\**\s*(simple|medium|high)')
# The plan's gate after each task, a header line (before the first `### Task`): `Gate: build` or `Gate: check`
GATE = re.compile(r'^Gate:\s*(build|check)\s*$')
FENCE = re.compile(r'^\s*(```|~~~)')


def git(root, *args):
    """git in [root], text and captured; raises Refused when git cannot be started."""
    try:
        return subprocess.run(('git', *args), cwd=root, capture_output=True, text=True)
    except OSError as e:
        raise Refused(f'cannot run git: {e.strerror}') from None


def root(cwd='.'):
    """The worktree's root (`git rev-parse --show-toplevel`); raises Refused outside any repository."""
    r = git(cwd, 'rev-parse', '--show-toplevel')
    if r.returncode != 0 or not r.stdout.strip():
        raise Refused('not inside a git repository')
    return r.stdout.strip()


def base_ref(root):
    """`origin/<base>`, the base of omc/config.yaml."""
    return f'origin/{config.load(root).base}'


def why(r, default=None):
    """git's last line of stderr, the reason of a failed call; else [default], else its exit code."""
    lines = r.stderr.strip().splitlines()
    return lines[-1] if lines else default or f'git exited {r.returncode}'


def output(root, *args):
    """git's stdout of a call that must succeed; raises Refused (`git <args>: <why>`) when it fails."""
    r = git(root, *args)
    if r.returncode != 0:
        raise Refused(f'git {" ".join(args)}: {why(r)}')
    return r.stdout


def merge_base(root):
    """`git merge-base HEAD origin/<base>`; raises Refused when there is none (no such ref, no common commit)."""
    ref = base_ref(root)
    r = git(root, 'merge-base', 'HEAD', ref)
    if r.returncode != 0 or not r.stdout.strip():
        raise Refused(f'no merge-base of HEAD and {ref}: {why(r, "no common commit")}')
    return r.stdout.strip()


def _added(root, directory, suffix):
    out = output(root, 'diff', '--name-only', '-z', '--diff-filter=A', '--no-renames', merge_base(root), 'HEAD', '--',
                 directory)
    return sorted(p for p in out.split('\0') if p.endswith(suffix))


def records(root):
    """The design records (`<paths.specs>…-design.md`) the branch added and committed since the merge-base,
    sorted."""
    return _added(root, config.load(root).paths.specs, '-design.md')


def plans(root):
    """The plans (`<paths.plans>…-plan.md`) the branch added and committed since the merge-base, sorted."""
    return _added(root, config.load(root).paths.plans, '-plan.md')


def _tasks(lines):
    """Each task of a plan's lines as (n, title, the indices of its section's lines outside fenced blocks); a fenced
    block (``` or ~~~) holds no heading and no box."""
    tasks, current, fence = [], None, None
    for i, line in enumerate(lines):
        f = FENCE.match(line)
        if fence:
            if f and f.group(1) == fence:
                fence = None
            continue
        if f:
            fence = f.group(1)
            continue
        if END.match(line):
            current = None
            m = TASK.match(line)
            if m:
                current = (int(m.group(1)), m.group(2), [])
                tasks.append(current)
        elif current:
            current[2].append(i)
    return tasks


def gate(lines):
    """The plan's `Gate:` header line's value, `build` or `check`, read from the lines before the first
    `### Task <n>:` heading outside fenced blocks; no line: `check`."""
    fence = None
    for line in lines:
        f = FENCE.match(line)
        if fence:
            if f and f.group(1) == fence:
                fence = None
            continue
        if f:
            fence = f.group(1)
            continue
        if TASK.match(line):
            break
        m = GATE.match(line)
        if m:
            return m.group(1)
    return 'check'


def next_task(text):
    """{'task', 'title', 'complexity', 'gate'} of the plan's first task with a `- [ ]` in its section (its complexity
    the first `Complexity:` line, else `medium`; the gate the plan's `Gate:` header line, else `check`), or None when
    every box is ticked; raises Refused when the plan has no `### Task <n>:` heading."""
    lines = text.splitlines()
    tasks = _tasks(lines)
    if not tasks:
        raise Refused('the plan has no `### Task <n>: <title>` heading')
    for n, title, section in tasks:
        if any(BOX.match(lines[i]) for i in section):
            complexity = next((m.group(1) for m in (COMPLEXITY.match(lines[i]) for i in section) if m), 'medium')
            return {'task': n, 'title': title, 'complexity': complexity, 'gate': gate(lines)}
    return None


def tick(text, n):
    """The plan with every `- [ ]` of task [n]'s section made `- [x]`, and how many; raises LookupError when the plan
    has no task [n]."""
    lines = text.splitlines(keepends=True)
    section = next((s for m, _, s in _tasks(lines) if m == n), None)
    if section is None:
        raise LookupError(n)
    count = 0
    for i in section:
        lines[i], k = BOX.subn(r'\1[x]', lines[i])
        count += k
    return ''.join(lines), count


def rebased_on(root):
    """After `git fetch origin <base>`: (True, 'rebased on origin/<base>') when its tip is the merge-base, else
    (False, 'behind origin/<base> by <k> commits'); raises Refused when the fetch fails."""
    base = config.load(root).base
    ref = f'origin/{base}'
    output(root, 'fetch', '-q', 'origin', base)
    k = int(output(root, 'rev-list', '--count', f'{merge_base(root)}..{ref}'))
    return (True, f'rebased on {ref}') if k == 0 else (False, f'behind {ref} by {k} commits')


def one_commit(root):
    """(k == 1, k), k the branch's commits over the merge-base."""
    k = int(output(root, 'rev-list', '--count', f'{merge_base(root)}..HEAD'))
    return k == 1, k


def dirty_paths(root):
    """The lines of `git status --porcelain`, one per uncommitted path (ignored files are none); empty when clean."""
    return [line for line in output(root, 'status', '--porcelain').splitlines() if line]
