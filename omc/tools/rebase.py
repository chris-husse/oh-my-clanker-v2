"""`just omc rebase [--squash]` and `just omc impact [--done]` :
squash the branch when asked, rebase it onto `origin/<base>`, and keep the old merge-base in the mark
`.cache/omc/impact` until its impact reading is done. The mark is written before `git rebase` starts and never
overwritten, so a session that ends at a paused rebase, or a second rebase before the reading, keeps the oldest
merge-base. A paused rebase is never aborted here; continuing it is the rebase terminal's job. The standard library
only; every git call goes through repo.git."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import repo  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

MARK = os.path.join('.cache', 'omc', 'impact')
# The git state of an operation in progress, each a `git rev-parse --git-path` name
PAUSED = (('rebase-merge', 'a rebase'), ('rebase-apply', 'a rebase'), ('MERGE_HEAD', 'a merge'),
          ('CHERRY_PICK_HEAD', 'a cherry-pick'), ('REVERT_HEAD', 'a revert'))


def _in_progress(root, names=PAUSED):
    """The operation git has in progress (`a rebase`, `a merge`, …), or None."""
    for name, what in names:
        path = repo.output(root, 'rev-parse', '--git-path', name).strip()
        if os.path.exists(os.path.join(root, path)):
            return what
    return None


def _squash(root, old):
    """Folds the branch's commits over [old] into one `wip: squash of <branch>`; their count. Refused when there is
    none; a failed commit puts the commits back as found (`git reset --soft <old tip>`), then is refused."""
    k = int(repo.output(root, 'rev-list', '--count', f'{old}..HEAD'))
    if k == 0:
        raise Refused(f'nothing to squash: the branch has no commit over the merge-base {old}')
    if k > 1:
        tip = repo.output(root, 'rev-parse', 'HEAD').strip()
        branch = repo.git(root, 'symbolic-ref', '-q', '--short', 'HEAD').stdout.strip() or 'HEAD'
        repo.output(root, 'reset', '-q', '--soft', old)
        commit = repo.git(root, 'commit', '-q', '-m', f'wip: squash of {branch}')
        if commit.returncode != 0:
            why = repo.why(commit, commit.stdout.strip() or None)
            back = repo.git(root, 'reset', '-q', '--soft', tip)
            if back.returncode != 0:
                raise Refused(f'the squash commit failed ({why}) and the commits could not be put back '
                              f'({repo.why(back)}): HEAD is at the merge-base {old}; restore with '
                              f'`git reset --soft {tip}`')
            raise Refused(f'the squash commit failed, the commits are back as found: {why}')
    return k


def rebase(root, squash):
    """(exit code, the JSON verdict): 0 `rebased` true or false, 3 a stop on conflicts (the rebase left paused);
    `old_base` is the mark's value, the oldest merge-base whose impact is pending (a kept older mark wins).
    Raises Refused (2) for an operation in progress, unmerged paths, a dirty tree, a failed fetch, `squash` with
    nothing over the merge-base, or a rebase git refused before it started (the mark this call wrote removed)."""
    what = _in_progress(root)
    if what:
        raise Refused(f'{what} is in progress: finish it (`--continue`) or back out (`--abort`) first')
    if repo.output(root, 'ls-files', '-u').strip():
        raise Refused('the index has unmerged paths: resolve them first')
    dirty = repo.dirty_paths(root)
    if dirty:  # never folded in: the orchestrator settles a dirty tree first
        raise Refused('the tree has uncommitted changes: ' + ', '.join(line[3:] for line in dirty))
    base = config.load(root).base
    ref = f'origin/{base}'
    repo.output(root, 'fetch', '-q', 'origin', base)
    old = repo.merge_base(root)
    squashed = _squash(root, old) if squash else None
    tip = repo.output(root, 'rev-parse', ref).strip()
    if old == tip:
        return 0, {'ok': True, 'rebased': False, 'squashed': squashed}
    wrote = impact(root) is None
    if wrote:
        _write_mark(root, old)
    pending = impact(root)  # the oldest merge-base whose impact is not read yet: this one or a kept older one
    r = repo.git(root, 'rebase', ref)
    if r.returncode == 0:
        return 0, {'ok': True, 'rebased': True, 'old_base': pending, 'new_base': tip, 'squashed': squashed}
    if _in_progress(root, PAUSED[:2]):
        conflicts = repo.output(root, 'diff', '--name-only', '--diff-filter=U').splitlines()
        return 3, {'ok': False, 'conflicts': conflicts, 'old_base': pending}
    if wrote:  # git refused before it started: nothing moved, nothing to read
        impact_done(root)
    raise Refused(f'git rebase {ref}: {repo.why(r)}')


def _write_mark(root, old):
    path = os.path.join(root, MARK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(old + '\n')


def impact(root):
    """The old merge-base the mark holds, or None when no impact is pending."""
    try:
        with open(os.path.join(root, MARK), encoding='utf-8') as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def impact_done(root):
    """Removes the mark; absent is fine."""
    try:
        os.remove(os.path.join(root, MARK))
    except FileNotFoundError:
        pass
