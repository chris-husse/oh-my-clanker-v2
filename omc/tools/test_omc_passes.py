"""Tests of omc/tools/passes.py, `just omc pass <harden|consistency>` and the clear of `just omc settled --record`:
the count of a repeated design pass: the first pass of ▣ harden on the role `harden` (tier `max`), every later one on `harden-repeat`
(tier `medium`), every pass of ▣ consistency on the orchestrator, counted per branch, record and terminal. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_passes.py
Each case gets its own temporary repository from omc_fixtures' `Repo`, on a branch `feature/x` holding one committed
record; the verbs run through `omc.main` in this process under that environment."""
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import omc  # noqa: E402
import passes  # noqa: E402
from omc_fixtures import Repo  # noqa: E402

RECORD = 'docs/superpowers/specs/2026-01-08-x-design.md'
OTHER = 'docs/superpowers/specs/2026-01-08-y-design.md'


class PassesTest(unittest.TestCase):

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        self.repo.git('checkout', '-q', '-b', 'feature/x')
        self.repo.commit(RECORD, '# x\n', 'record x')
        env = mock.patch.dict(os.environ, self.repo.env, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def omc(self, *args):
        out, err, here = io.StringIO(), io.StringIO(), os.getcwd()
        os.chdir(self.repo.work)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = omc.main(list(args))
        finally:
            os.chdir(here)
        return subprocess.CompletedProcess(args, code, out.getvalue(), err.getvalue())

    def pass_of(self, terminal):
        """`just omc pass <terminal>`, which exits 0: its JSON."""
        r = self.omc('pass', terminal)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def counts(self):
        with open(os.path.join(self.repo.work, passes.PASSES), encoding='utf-8') as f:
            return json.load(f)

    def test_the_first_harden_is_on_max_every_later_one_on_medium_and_consistency_on_the_orchestrator(self):
        self.assertEqual(self.pass_of('harden'), {'terminal': 'harden', 'pass': 1, 'role': 'harden', 'tier': 'max'})
        self.assertEqual(self.pass_of('harden'),
                         {'terminal': 'harden', 'pass': 2, 'role': 'harden-repeat', 'tier': 'medium'})
        self.assertEqual(self.pass_of('harden'),
                         {'terminal': 'harden', 'pass': 3, 'role': 'harden-repeat', 'tier': 'medium'})
        orchestrator = {'role': 'orchestrator', 'tier': 'orchestrator'}
        self.assertEqual(self.pass_of('consistency'), {'terminal': 'consistency', 'pass': 1, **orchestrator})
        self.assertEqual(self.pass_of('consistency'), {'terminal': 'consistency', 'pass': 2, **orchestrator})
        self.assertEqual(self.counts(), {'feature/x': {RECORD: {'harden': 3, 'consistency': 2}}})

    def test_counts_are_per_branch_record_and_terminal(self):
        self.pass_of('harden')
        self.pass_of('harden')
        self.repo.git('checkout', '-q', '-b', 'feature/y', 'main')
        self.repo.commit(OTHER, '# y\n', 'record y')
        self.assertEqual(self.pass_of('harden')['pass'], 1)
        self.assertEqual(self.pass_of('consistency')['pass'], 1)
        # another record of feature/x, left by an earlier record of the branch, is not this record's count
        data = self.counts()
        data['feature/x']['docs/superpowers/specs/2026-11-01-old-design.md'] = {'harden': 5}
        with open(os.path.join(self.repo.work, passes.PASSES), 'w', encoding='utf-8') as f:
            json.dump(data, f)
        self.repo.git('checkout', '-q', 'feature/x')
        self.assertEqual(self.pass_of('harden'),
                         {'terminal': 'harden', 'pass': 3, 'role': 'harden-repeat', 'tier': 'medium'})
        self.assertEqual(self.pass_of('consistency')['pass'], 1)
        self.assertEqual(self.counts(), {
            'feature/x': {RECORD: {'harden': 3, 'consistency': 1},
                          'docs/superpowers/specs/2026-11-01-old-design.md': {'harden': 5}},
            'feature/y': {OTHER: {'harden': 1, 'consistency': 1}}})

    def test_settled_record_clears_the_branchs_counts(self):
        self.pass_of('harden')
        self.pass_of('consistency')
        self.repo.git('checkout', '-q', '-b', 'feature/y', 'main')
        self.repo.commit(OTHER, '# y\n', 'record y')
        self.pass_of('harden')
        self.repo.git('checkout', '-q', 'feature/x')
        r = self.omc('settled', '--record')
        self.assertEqual((r.returncode, r.stdout), (0, ''), r.stderr)
        self.assertEqual(self.counts(), {'feature/y': {OTHER: {'harden': 1}}})
        self.assertEqual(self.pass_of('harden')['role'], 'harden')

    def test_settled_record_without_counts_is_fine(self):
        r = self.omc('settled', '--record')
        self.assertEqual((r.returncode, r.stdout), (0, ''), r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo.work, passes.PASSES)))

    def test_no_record_is_refused(self):
        self.repo.git('checkout', '-q', '-b', 'feature/none', 'main')
        r = self.omc('pass', 'harden')
        self.assertEqual(r.returncode, 2)
        self.assertIn('no record committed on this branch', r.stderr)
        self.repo.git('checkout', '-q', 'feature/x')
        self.repo.commit(OTHER, '# y\n', 'record y')
        r = self.omc('pass', 'harden')
        self.assertEqual(r.returncode, 2)
        self.assertIn('2 records committed on this branch', r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.repo.work, passes.PASSES)))

    def test_an_unknown_terminal_is_refused(self):
        with self.assertRaises(passes.Refused) as caught:
            passes.next_pass(self.repo.work, 'integrity')
        self.assertIn('integrity', str(caught.exception))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as code:
            omc.parser().parse_args(['pass', 'integrity'])
        self.assertEqual(code.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
