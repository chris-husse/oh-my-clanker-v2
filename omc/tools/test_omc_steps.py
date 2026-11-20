"""Tests of omc/tools/steps.py and of `just omc gate run` with a step file `omc/bin/<gate>.steps.yaml`: only the stale
steps run, `--full` runs all and records a pass, a `derive` command's lines are inputs, a failing one is red and names
its step, a red step stays stale, a stage fed by a stale step's outs runs too, and with no DVC in the project the step
file is refused. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_steps.py
Each case gets its own temporary repository from omc_fixtures' `Repo`, a DVC repository without git integration
(`dvc init --no-scm`) committed in it, the generated DVC files git-ignored. DVC is the one on the test's PATH, run as
`uv run --frozen dvc` in the repository (no project there, so uv runs it from the PATH); without it every case that
needs it is skipped, with that message. The verbs run through `omc.main` in this process."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import concurrency  # noqa: E402
import config  # noqa: E402
import done  # noqa: E402
import omc  # noqa: E402
import steps  # noqa: E402
from omc_fixtures import Repo  # noqa: E402

IGNORE = '.cache/\n/dvc.yaml\n/dvc.lock\n/dvc-params.json\n/.dvc/tmp/\n/.dvc/cache/\n'


def _dvc_found():
    """Whether `uv run --frozen dvc` starts DVC in an empty folder, as the cases run it."""
    with tempfile.TemporaryDirectory() as d:
        try:
            r = subprocess.run((*steps.DVC, '--version'), cwd=d, capture_output=True, text=True)
        except OSError:
            return False
        return r.returncode == 0


DVC_FOUND = _dvc_found()
NO_DVC = 'no DVC: `uv run --frozen dvc` does not start DVC here (the step selection cases need it)'


class StepsTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        self.repo.git('checkout', '-q', '-b', 'feature/x')
        registry = tempfile.TemporaryDirectory()
        self.addCleanup(registry.cleanup)
        env = mock.patch.dict(os.environ, {**self.repo.env, concurrency.REGISTRY_ENV: registry.name}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.root = self.repo.work

    def dvc_repo(self):
        """`dvc init --no-scm` in the work clone, its files and the ignores committed; skipped without DVC."""
        if not DVC_FOUND:
            self.skipTest(NO_DVC)
        r = subprocess.run((*steps.DVC, 'init', '--no-scm', '-q'), cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.repo.write('.gitignore', IGNORE)
        self.repo.git('add', '--', '.gitignore', '.dvc/config', '.dvcignore')
        self.repo.git('commit', '-q', '-m', 'dvc')

    def step_file(self, text, gate='check', files=()):
        """Commits `omc/bin/<gate>.steps.yaml` of [text] and every (path, text) of [files]."""
        for path, body in files:
            self.repo.write(path, body)
        path = os.path.join('omc', 'bin', f'{gate}.steps.yaml')
        self.repo.write(path, text)
        self.repo.git('add', '--', path, *(p for p, _ in files))
        self.repo.git('commit', '-q', '-m', 'steps')

    def omc(self, *args):
        out, err, here = io.StringIO(), io.StringIO(), os.getcwd()
        os.chdir(self.root)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = omc.main(list(args))
        finally:
            os.chdir(here)
        return subprocess.CompletedProcess(args, code, out.getvalue(), err.getvalue())

    def ran(self):
        """The steps that ran, from the marks each stub step leaves in `.cache/ran`, in order; the marks cleared."""
        path = os.path.join(self.root, '.cache', 'ran')
        try:
            with open(path, encoding='utf-8') as f:
                names = f.read().split()
        except FileNotFoundError:
            return []
        os.remove(path)
        return names

    def passes(self):
        return sorted(f for _, _, fs in os.walk(os.path.join(self.root, '.cache', 'omc', 'passes')) for f in fs)

    def mark(self, name, then=''):
        return f'mkdir -p .cache && echo {name} >> .cache/ran{then}'

    def two_steps(self):
        self.step_file(
            'steps:\n'
            f'  - name: alpha\n    run: {self.mark("alpha")}\n    inputs: [src/a/**]\n'
            f'  - name: beta\n    run: {self.mark("beta")}\n    inputs: [src/b.txt]\n',
            files=(('src/a/x.txt', 'a\n'), ('src/b.txt', 'b\n')))

    # ----------------------------------------------------------------------------------------------- load
    def test_load_reads_the_step_file(self):
        self.assertIsNone(steps.load(self.root, 'check'))
        self.step_file('steps:\n  - name: one\n    run: echo 1\n    inputs: [src/**]\n    derive: echo x\n'
                       '    lock: sub/dvc.yaml:one\n    outs: [out]\n  - name: two\n    run: echo 2\n')
        self.assertEqual(steps.load(self.root, 'check'), [
            steps.Step('one', 'echo 1', ('src/**',), 'echo x', 'sub/dvc.yaml:one', ('out',)),
            steps.Step('two', 'echo 2', (), None, None, ())])

    def test_load_refuses_a_bad_step_file(self):
        for text, why in (('steps: 1\n', 'a list'), ('steps:\n  - run: x\n', 'name'),
                          ('steps:\n  - name: a\n', 'run'), ('steps:\n  - {name: a, run: x, inputs: x}\n', 'inputs'),
                          ('steps:\n  - {name: a, run: x}\n  - {name: a, run: y}\n', 'twice'),
                          ('steps:\n  - {name: a, run: x, lock: nostage}\n', 'lock'),
                          ('steps:\n  - {name: a, run: x, other: 1}\n', 'other')):
            with self.subTest(text=text):
                self.step_file(text)
                with self.assertRaises(config.Refused) as e:
                    steps.load(self.root, 'check')
                self.assertIn(why, str(e.exception))

    # ------------------------------------------------------------------------------------------ gate run
    def test_no_step_file_runs_whole(self):
        path = os.path.join('omc', 'bin', 'check')
        self.repo.write(path, '#!/bin/sh\necho whole\n')
        os.chmod(os.path.join(self.root, path), 0o755)
        self.repo.git('add', '--', path)
        self.repo.git('commit', '-q', '-m', 'bin')
        r = self.omc('gate', 'run', 'check')
        self.assertEqual((r.returncode, r.stdout), (0, 'whole\n'), r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.root, 'dvc.yaml')))
        self.assertEqual(len(self.passes()), 1)

    def test_only_stale_steps_run(self):
        self.dvc_repo()
        self.two_steps()
        r = self.omc('gate', 'run', 'check')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.ran(), ['alpha', 'beta'])
        r = self.omc('gate', 'run', 'check')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.ran(), [])
        self.assertIn('fresh: alpha, beta', r.stdout)
        self.repo.commit('src/a/x.txt', 'changed\n', 'a')
        self.assertEqual(self.omc('gate', 'run', 'check').returncode, 0)
        self.assertEqual(self.ran(), ['alpha'])
        self.repo.commit('src/a/new.txt', 'new\n', 'a new file the glob matches')
        self.assertEqual(self.omc('gate', 'run', 'check').returncode, 0)
        self.assertEqual(self.ran(), ['alpha'])

    def test_a_changed_command_is_stale(self):
        self.dvc_repo()
        self.two_steps()
        self.omc('gate', 'run', 'check')
        self.ran()
        self.step_file('steps:\n'
                       f'  - name: alpha\n    run: {self.mark("alpha")}\n    inputs: [src/a/**]\n'
                       f'  - name: beta\n    run: {self.mark("beta", "; true")}\n    inputs: [src/b.txt]\n')
        self.omc('gate', 'run', 'check')
        self.assertEqual(self.ran(), ['beta'])

    def test_a_step_without_inputs_always_runs(self):
        self.dvc_repo()
        self.step_file(f'steps:\n  - name: always\n    run: {self.mark("always")}\n')
        for _ in range(2):
            self.assertEqual(self.omc('gate', 'run', 'check').returncode, 0)
            self.assertEqual(self.ran(), ['always'])

    def test_full_runs_all_and_records_pass(self):
        self.dvc_repo()
        self.two_steps()
        self.omc('gate', 'run', 'check')
        self.ran()
        for f in os.listdir(os.path.join(self.root, '.cache', 'omc', 'passes', 'check')):
            os.remove(os.path.join(self.root, '.cache', 'omc', 'passes', 'check', f))
        r = self.omc('gate', 'run', 'check', '--full')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.ran(), ['alpha', 'beta'])
        head = self.repo.git('rev-parse', 'HEAD').strip()
        self.assertEqual(self.passes(), [f'{head}.json'])
        self.assertIn('passed: run at', self.omc('gate', 'passed', 'check').stdout)

    def test_other_arguments_are_refused(self):
        self.dvc_repo()
        self.two_steps()
        r = self.omc('gate', 'run', 'check', '--only', 'alpha')
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn('--full', r.stderr)

    def test_derived_inputs(self):
        self.dvc_repo()
        self.step_file(f'steps:\n  - name: gamma\n    run: {self.mark("gamma")}\n    derive: cat deps.txt\n',
                       files=(('deps.txt', 'src/c.txt\n\nsrc/d\n'), ('src/c.txt', 'c\n'), ('src/d/e.txt', 'e\n'),
                              ('src/other.txt', 'o\n')))
        self.omc('gate', 'run', 'check')
        self.assertEqual(self.ran(), ['gamma'])
        self.repo.commit('src/other.txt', 'changed\n', 'not an input')
        self.omc('gate', 'run', 'check')
        self.assertEqual(self.ran(), [])
        self.repo.commit('src/d/e.txt', 'changed\n', 'an input inside a derived folder')
        self.omc('gate', 'run', 'check')
        self.assertEqual(self.ran(), ['gamma'])

    def test_derived_inputs_failure_is_red(self):
        self.dvc_repo()
        self.step_file('steps:\n'
                       f'  - name: alpha\n    run: {self.mark("alpha")}\n'
                       f'  - name: gamma\n    run: {self.mark("gamma")}\n    derive: echo boom >&2; exit 3\n')
        r = self.omc('gate', 'run', 'check')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('step gamma: its derive command failed (exit 3): boom', r.stdout)
        self.assertEqual(self.ran(), [])  # never read as "no inputs": nothing runs
        self.assertEqual(self.passes(), [])
        with self.assertRaises(steps.StepFailed) as e:
            steps.stale(self.root, steps.load(self.root, 'check'))
        self.assertIn('gamma', str(e.exception))

    def test_red_step_not_recorded(self):
        self.dvc_repo()
        self.step_file('steps:\n'
                       f'  - name: alpha\n    run: {self.mark("alpha", "; test -f src/ok")}\n    inputs: [src/a.txt]\n'
                       f'  - name: beta\n    run: {self.mark("beta")}\n    inputs: [src/b.txt]\n',
                       files=(('src/a.txt', 'a\n'), ('src/b.txt', 'b\n')))
        r = self.omc('gate', 'run', 'check')
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('red: alpha', r.stdout)
        self.assertEqual(self.ran(), ['alpha', 'beta'])  # a red step does not stop the others
        self.assertEqual(self.passes(), [])
        self.assertEqual(steps.stale(self.root, steps.load(self.root, 'check')), ['alpha'])
        self.omc('gate', 'run', 'check')
        self.assertEqual(self.ran(), ['alpha'])

    def test_an_input_changed_while_it_ran_is_not_recorded(self):
        self.dvc_repo()
        self.step_file(f'steps:\n  - name: alpha\n    run: {self.mark("alpha", "; echo x >> src/a.txt")}\n'
                       '    inputs: [src/a.txt]\n', files=(('src/a.txt', 'a\n'),))
        r = self.omc('gate', 'run', 'check')
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('alpha: an input changed while it ran: not recorded', r.stdout)
        self.assertEqual(steps.stale(self.root, steps.load(self.root, 'check')), ['alpha'])

    def test_a_step_fed_by_a_stale_step_s_outs_runs(self):
        self.dvc_repo()
        self.step_file('steps:\n'
                       f'  - name: make\n    run: {self.mark("make", "; cp src/in.txt build.out")}\n'
                       '    inputs: [src/in.txt]\n    outs: [build.out]\n'
                       f'  - name: use\n    run: {self.mark("use")}\n    inputs: [build.out]\n',
                       files=(('src/in.txt', '1\n'),))
        self.repo.write('.gitignore', IGNORE + '/build.out\n')
        self.repo.git('commit', '-q', '-am', 'ignore the out')
        self.assertEqual(self.omc('gate', 'run', 'check').returncode, 0)
        self.assertEqual(self.ran(), ['make', 'use'])
        self.repo.commit('src/in.txt', '2\n', 'in')
        self.omc('gate', 'run', 'check')
        self.assertEqual(self.ran(), ['make', 'use'])
        os.remove(os.path.join(self.root, 'build.out'))
        self.omc('gate', 'run', 'check')
        self.assertEqual(self.ran(), ['make', 'use'])  # a deleted out is stale

    def test_a_committed_stage_with_its_own_lock(self):
        self.dvc_repo()
        stage = '{"stages": {"model": {"cmd": "x", "deps": ["m.txt"]}}}\n'
        self.step_file(f'steps:\n  - name: model check\n    run: {self.mark("model")}\n    lock: sub/dvc.yaml:model\n',
                       files=(('sub/dvc.yaml', stage), ('sub/m.txt', 'm\n')))
        self.assertEqual(self.omc('gate', 'run', 'check').returncode, 0)
        self.assertEqual(self.ran(), ['model'])
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'sub', 'dvc.lock')))  # the committed stage's lock
        self.repo.git('add', '--', 'sub/dvc.lock')
        self.repo.git('commit', '-q', '-m', 'lock')
        self.omc('gate', 'run', 'check', '--full')
        self.assertEqual(self.ran(), [])  # --full leaves a committed stage to its lock
        self.repo.commit('sub/m.txt', 'n\n', 'model')
        self.omc('gate', 'run', 'check')
        self.assertEqual(self.ran(), ['model'])

    def test_no_dvc_refused(self):
        self.step_file(f'steps:\n  - name: alpha\n    run: {self.mark("alpha")}\n    inputs: [src/a.txt]\n',
                       files=(('src/a.txt', 'a\n'),))
        uv = shutil.which('uv')
        if uv is None:
            self.skipTest('no uv on the PATH')
        bare = tempfile.TemporaryDirectory()
        self.addCleanup(bare.cleanup)
        os.symlink(uv, os.path.join(bare.name, 'uv'))
        for name in ('git', 'bash', 'sh', 'mkdir'):
            if found := shutil.which(name):
                os.symlink(found, os.path.join(bare.name, name))
        env = {k: v for k, v in os.environ.items() if k not in ('UV_PROJECT_ENVIRONMENT', 'VIRTUAL_ENV')}
        # no environment of the caller's either: a project's .cache/venv may hold DVC (its own pin)
        with mock.patch.dict(os.environ, {**env, 'PATH': bare.name}, clear=True):
            r = self.omc('gate', 'run', 'check')
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn('step selection needs DVC in the project (uv run --frozen dvc)', r.stderr)
        self.assertEqual(self.ran(), [])

    def test_no_dvc_repository_refused(self):
        if not DVC_FOUND:
            self.skipTest(NO_DVC)
        self.step_file(f'steps:\n  - name: alpha\n    run: {self.mark("alpha")}\n    inputs: [src/a.txt]\n',
                       files=(('src/a.txt', 'a\n'),))
        r = self.omc('gate', 'run', 'check')
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn('dvc init --no-scm', r.stderr)

    def test_a_silent_step_is_killed(self):
        self.dvc_repo()
        path = os.path.join(self.root, 'omc', 'config.yaml')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        self.repo.commit('omc/config.yaml', text + 'silence:\n  check: 1\n', 'silence')
        self.step_file('steps:\n  - name: hang\n    run: sleep 30\n  - name: after\n    run: echo after\n')
        with mock.patch.object(done, 'GRACE', 0.5):
            r = self.omc('gate', 'run', 'check')
        self.assertEqual(r.returncode, 124, r.stdout)
        self.assertTrue(r.stdout.endswith('no output for 1 s: killed\n'), r.stdout)
        self.assertNotIn('after\n', r.stdout)


if __name__ == '__main__':
    unittest.main()
