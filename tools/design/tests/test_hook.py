# tools/design/tests/test_hook.py
"""The pre-push hook against a real push: a work repository cloned from a bare remote, core.hooksPath at a copy of
.githooks, and tools/ committed into it (its pyproject.toml, uv.lock, corpus.yaml, stages.yaml and the design
package). Every work repository shares one session environment (UV_PROJECT_ENVIRONMENT), so `uv run` installs
the dependencies once and afterwards only re-points the editable design package."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from design.freshness import generated_for, mark
from design.tests.conftest import commit_all, corpus_yaml, git

HERE = Path(__file__).resolve()
TOOLS = HERE.parents[2]
HOOK = TOOLS.parent / '.githooks' / 'pre-push'
STAGES = 'dvc: 3.67.1\nstages:\n  out:\n    skill: /write-out\n    inputs: [in/*.md]\n    outputs: [out/*.md]\n'
RUN = 'run /ensure-up-to-date'
PREDATES = 'this commit predates the freshness check; merge main into it, or push with --no-verify'
UNPINNED = 'unpinned links from main: run just pin-links, commit, push again'
A = '# 01 A\n\n## 1.1 Keep\n\nText.\n'
LINK = 'design/01-a.md#1.1%20Keep'


def log_with(link: str) -> str:
    return ('# Decision Log\n\n## 1. Review: first (2026-10-27)\n\n### 1.1 Keep\n\n'
            f'**Context.** About [1.1]({link}).\n**Decision.** d\n**Status.** recorded 2026-10-27\n')


@pytest.fixture(scope='session')
def hook_env(tmp_path_factory):
    """DVC keeps its state inside the test area and sends nothing; uv installs into one shared environment; the
    environment pytest itself runs in is not passed on."""
    with pytest.MonkeyPatch.context() as m:
        m.setenv('DVC_SITE_CACHE_DIR', str(tmp_path_factory.mktemp('hook-dvc-site-cache')))
        m.setenv('DVC_NO_ANALYTICS', '1')
        m.setenv('UV_PROJECT_ENVIRONMENT', str(tmp_path_factory.mktemp('hook-venv') / 'venv'))
        m.delenv('VIRTUAL_ENV', raising=False)
        yield


def write(root, rel, text):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def push(cwd, branch='main'):
    r = subprocess.run(['git', 'push', '-q', 'origin', branch], cwd=cwd, capture_output=True, text=True,
                       env=os.environ.copy())
    return r.returncode, r.stdout + r.stderr, r.stderr


def worktrees(root):
    return git(root, 'worktree', 'list', '--porcelain').count('worktree ')


def marked(root, capsys):
    assert mark(root, ['out']) == 0
    capsys.readouterr()
    return commit_all(root, 'marked')


@pytest.fixture
def work(tmp_path, hook_env):
    remote = tmp_path / 'remote.git'
    git(tmp_path, 'init', '-q', '--bare', str(remote))
    root = tmp_path / 'work'
    root.mkdir()
    git(root, 'init', '-q', '-b', 'main')
    git(root, 'config', 'user.name', 'test')
    git(root, 'config', 'user.email', 'test@example.com')
    git(root, 'remote', 'add', 'origin', str(remote))
    (root / '.githooks').mkdir()
    shutil.copy2(HOOK, root / '.githooks' / 'pre-push')
    shutil.copytree(TOOLS / 'design', root / 'tools' / 'design',
                    ignore=shutil.ignore_patterns('tests', '__pycache__', '.venv'))
    for f in ('pyproject.toml', 'uv.lock'):
        shutil.copy2(TOOLS / f, root / 'tools' / f)
    corpus_yaml(root)
    write(root, 'tools/stages.yaml', STAGES)
    write(root, '.gitignore', '__pycache__/\n')
    write(root, 'in/a.md', 'a')
    write(root, 'out/a.md', 'A')
    subprocess.run(['dvc', 'init', '-q'], cwd=root, check=True, capture_output=True)
    write(root, '.dvc/config', '[core]\n    analytics = false\n')
    write(root, 'dvc.yaml', generated_for(root))
    git(root, 'config', 'core.hooksPath', '.githooks')
    commit_all(root, 'init')
    return root


def test_a_stale_tip_is_refused(work):
    sha = git(work, 'rev-parse', 'HEAD').strip()
    code, out, err = push(work)
    assert code != 0
    assert RUN in out
    assert f'push refused: refs/heads/main ({sha}) is not up to date' in err
    assert worktrees(work) == 1


def test_a_tip_without_stages_yaml_is_refused_with_the_predates_line(work):
    git(work, 'checkout', '-q', '--orphan', 'old')
    git(work, 'rm', '-rq', '--cached', '.')
    git(work, 'add', 'in/a.md', 'out/a.md')
    git(work, 'commit', '-q', '-m', 'before the freshness check')
    code, out, _ = push(work, 'old')
    assert code != 0
    assert PREDATES in out and RUN in out


def test_a_current_tip_is_accepted(work, capsys):
    marked(work, capsys)
    code, out, _ = push(work)
    assert code == 0, out
    assert worktrees(work) == 1


def test_an_uncommitted_edit_changes_nothing(work, capsys):
    marked(work, capsys)
    write(work, 'in/a.md', 'edited, not committed')
    code, out, _ = push(work)
    assert code == 0, out


def test_an_unpinned_log_link_from_main_is_refused_then_accepted_once_pinned(work, capsys):
    marked(work, capsys)
    write(work, 'docs/design/01-a.md', A)
    write(work, 'docs/decision-log.md', log_with(LINK))
    sha = commit_all(work, 'log')
    code, out, err = push(work)  # no origin/main yet: the local main is main
    assert code != 0
    assert f'unpinned: {LINK}: run just pin-links' in err
    assert f'push refused: refs/heads/main ({sha}) has {UNPINNED}' in err
    assert err.index(': unpinned: ') < err.index('push refused:')
    write(work, 'docs/decision-log.md', log_with(f'{LINK} "git:{sha[:12]}"'))
    commit_all(work, 'pinned')
    code, out, _ = push(work)
    assert code == 0, out


def test_a_push_from_a_linked_worktree_gets_the_right_verdict_and_leaves_origin_alone(work, tmp_path, capsys):
    origin = git(work, 'remote', 'get-url', 'origin').strip()
    wt = tmp_path / 'wt'
    git(work, 'worktree', 'add', '-q', '-b', 'side', str(wt))
    code, out, _ = push(wt, 'side')
    assert code != 0
    assert RUN in out
    assert git(wt, 'remote', 'get-url', 'origin').strip() == origin
    marked(wt, capsys)
    code, out, _ = push(wt, 'side')
    assert code == 0, out
    assert git(work, 'remote', 'get-url', 'origin').strip() == origin
    assert git(work, 'config', '--get-all', 'remote.origin.fetch').strip() == '+refs/heads/*:refs/remotes/origin/*'
    assert worktrees(work) == 2


def test_a_link_check_that_cannot_run_refuses_the_push(work, capsys):
    marked(work, capsys)
    write(work, 'docs/design/01-a.md', A)
    corpus_yaml(work, corpus=['design/{a,b.md'])  # an unbalanced brace: the corpus cannot be loaded
    sha = commit_all(work, 'bad corpus')
    code, out, err = push(work)
    assert code != 0
    assert f'push refused: refs/heads/main ({sha}): the link check could not run (exit 2)' in err
    assert 'links-check: tools/corpus.yaml: bad glob' in err
    assert worktrees(work) == 1
