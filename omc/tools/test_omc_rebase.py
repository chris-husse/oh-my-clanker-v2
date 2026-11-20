"""Tests of omc/tools/rebase.py, `just omc rebase [--squash]` and `just omc impact [--done]`. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_rebase.py
Each case gets its own temporary repository from omc_fixtures' `Repo` (a bare origin.git and a work clone on
main, the caller's GIT_ variables removed and a private GIT_CONFIG_GLOBAL); the tool runs as a subprocess."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from omc_fixtures import Repo  # noqa: E402

MARK = os.path.join('.cache', 'omc', 'impact')
BRANCH = 'feature/x'


class RebaseTest(unittest.TestCase):

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        self.repo.git('checkout', '-q', '-b', BRANCH)

    def omc(self, *args):
        return self.repo.omc(*args)

    def sha(self, ref):
        return self.repo.git('rev-parse', ref).strip()

    def mark(self):
        """The mark's text, or None when there is none."""
        try:
            with open(os.path.join(self.repo.work, MARK), encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return None

    def verdict(self, r, code):
        """The one JSON line of a run that exited [code]."""
        self.assertEqual(r.returncode, code, r.stderr)
        self.assertEqual(r.stdout.count('\n'), 1, r.stdout)
        return json.loads(r.stdout)

    def assertRefused(self, r):
        self.assertEqual((r.returncode, r.stdout), (2, ''), r.stderr)
        self.assertTrue(r.stderr.startswith('error: '), r.stderr)

    def paused(self):
        path = self.repo.git('rev-parse', '--git-path', 'rebase-merge').strip()
        return os.path.exists(os.path.join(self.repo.work, path))

    # ------------------------------------------------------------------------------------------------------- rebase
    def test_on_the_tip_nothing_moves_and_no_mark(self):
        head = self.repo.commit('a.txt', 'a\n', 'a')
        self.assertEqual(self.verdict(self.omc('rebase'), 0), {'ok': True, 'rebased': False, 'squashed': None})
        self.assertEqual(self.sha('HEAD'), head)
        self.assertIsNone(self.mark())

    def test_a_moved_main_rebases_and_marks_the_old_merge_base(self):
        self.repo.commit('a.txt', 'a\n', 'a')
        old = self.sha('origin/main')
        tip = self.repo.advance_origin('b.txt', 'b\n')
        self.assertEqual(self.verdict(self.omc('rebase'), 0),
                         {'ok': True, 'rebased': True, 'old_base': old, 'new_base': tip, 'squashed': None})
        self.assertEqual(self.mark(), old + '\n')
        self.assertEqual(self.repo.git('merge-base', 'HEAD', 'origin/main').strip(), tip)

    def test_squash_makes_one_commit_on_the_new_base(self):
        for k in (1, 2, 3):
            self.repo.commit(f'{k}.txt', f'{k}\n', f'commit {k}')
        base = self.sha('origin/main')
        changes = self.repo.git('diff', base, 'HEAD')
        tip = self.repo.advance_origin('b.txt', 'b\n')
        self.assertEqual(self.verdict(self.omc('rebase', '--squash'), 0),
                         {'ok': True, 'rebased': True, 'old_base': base, 'new_base': tip, 'squashed': 3})
        self.assertEqual(self.repo.git('rev-list', '--count', 'origin/main..HEAD').strip(), '1')
        self.assertEqual(self.sha('HEAD^'), tip)
        self.assertEqual(self.repo.git('log', '-1', '--format=%s').strip(), f'wip: squash of {BRANCH}')
        self.assertEqual(self.repo.git('diff', 'HEAD^', 'HEAD'), changes)  # the branch's changes, the same

    def test_squash_with_nothing_over_the_merge_base_is_refused(self):
        head = self.sha('HEAD')
        self.assertRefused(self.omc('rebase', '--squash'))
        self.assertEqual(self.sha('HEAD'), head)

    def test_a_failed_squash_commit_puts_the_commits_back(self):
        for k in (1, 2):
            head = self.repo.commit(f'{k}.txt', f'{k}\n', f'commit {k}')
        hook = os.path.join(self.repo.work, self.repo.git('rev-parse', '--git-path', 'hooks').strip(), 'pre-commit')
        self.repo.write(hook, '#!/bin/sh\necho refused by the hook >&2\nexit 1\n')
        os.chmod(hook, 0o755)
        r = self.omc('rebase', '--squash')
        self.assertRefused(r)
        self.assertIn('refused by the hook', r.stderr)
        self.assertEqual(self.sha('HEAD'), head)
        self.assertEqual(self.repo.git('rev-list', '--count', 'origin/main..HEAD').strip(), '2')

    def test_a_conflict_stops_with_the_files_and_the_mark_written(self):
        self.repo.commit('a.txt', 'branch\n', 'a on the branch')
        old = self.sha('origin/main')
        self.repo.advance_origin('a.txt', 'main\n')
        self.assertEqual(self.verdict(self.omc('rebase'), 3), {'ok': False, 'conflicts': ['a.txt'], 'old_base': old})
        self.assertTrue(self.paused())  # paused, never aborted
        self.assertEqual(self.mark(), old + '\n')

    def test_a_paused_rebase_is_refused(self):
        self.repo.commit('a.txt', 'branch\n', 'a on the branch')
        old = self.sha('origin/main')
        self.repo.advance_origin('a.txt', 'main\n')
        self.verdict(self.omc('rebase'), 3)
        r = self.omc('rebase')
        self.assertRefused(r)
        self.assertIn('rebase', r.stderr)
        self.assertTrue(self.paused())
        self.assertEqual(self.mark(), old + '\n')

    def test_a_dirty_tree_is_refused_and_nothing_moves(self):
        head = self.repo.commit('a.txt', 'a\n', 'a')
        self.repo.advance_origin('b.txt', 'b\n')
        self.repo.write('a.txt', 'changed\n')
        self.repo.write('new.txt', 'new\n')
        r = self.omc('rebase')
        self.assertRefused(r)
        self.assertIn('a.txt', r.stderr)
        self.assertIn('new.txt', r.stderr)
        self.assertNotIn(' M a.txt', r.stderr)  # the paths, not git status's lines
        self.assertEqual(self.sha('HEAD'), head)
        self.assertIsNone(self.mark())

    def test_an_older_mark_is_kept(self):
        self.repo.commit('a.txt', 'a\n', 'a')
        first = self.sha('origin/main')
        self.repo.advance_origin('b.txt', 'b\n')
        self.verdict(self.omc('rebase'), 0)
        second = self.repo.advance_origin('c.txt', 'c\n')
        out = self.verdict(self.omc('rebase'), 0)
        self.assertEqual(out, {'ok': True, 'rebased': True, 'old_base': first, 'new_base': second, 'squashed': None})
        self.assertEqual(self.mark(), first + '\n')

    def test_a_kept_mark_is_the_old_base_of_a_conflict(self):
        first = self.sha('origin/main')
        self.repo.write(MARK, first + '\n')
        self.repo.commit('a.txt', 'branch\n', 'a on the branch')
        self.repo.advance_origin('a.txt', 'main\n')
        self.assertEqual(self.verdict(self.omc('rebase'), 3), {'ok': False, 'conflicts': ['a.txt'], 'old_base': first})

    def test_a_rebase_refused_before_it_started_leaves_no_mark(self):
        head = self.repo.commit('a.txt', 'a\n', 'a')
        self.repo.advance_origin('b.txt', 'b\n')
        hook = os.path.join(self.repo.work, self.repo.git('rev-parse', '--git-path', 'hooks').strip(), 'pre-rebase')
        self.repo.write(hook, '#!/bin/sh\nexit 1\n')
        os.chmod(hook, 0o755)
        self.assertRefused(self.omc('rebase'))
        self.assertEqual(self.sha('HEAD'), head)
        self.assertFalse(self.paused())
        self.assertIsNone(self.mark())

    def test_a_failed_fetch_is_refused(self):
        self.repo.commit('a.txt', 'a\n', 'a')
        self.repo.git('remote', 'remove', 'origin')
        self.assertRefused(self.omc('rebase'))
        self.assertIsNone(self.mark())

    # ------------------------------------------------------------------------------------------------------- impact
    def test_impact_and_done(self):
        sha = self.sha('HEAD')
        self.repo.write(MARK, sha + '\n')
        r = self.omc('impact')
        self.assertEqual((r.returncode, r.stdout), (0, sha + '\n'), r.stderr)
        r = self.omc('impact', '--done')
        self.assertEqual((r.returncode, r.stdout), (0, ''), r.stderr)
        self.assertIsNone(self.mark())
        r = self.omc('impact')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(r.stdout.count('\n'), 1)
        r = self.omc('impact', '--done')  # absent is fine
        self.assertEqual((r.returncode, r.stdout), (0, ''), r.stderr)


if __name__ == '__main__':
    unittest.main()
