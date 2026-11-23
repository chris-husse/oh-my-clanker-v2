"""Tests of omc/tools/launch.py, the launch pieces `just design` and `just investigate` share. Run from the repository
root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_launch.py
Each case that needs a primary checkout gets its own temporary repository from omc_fixtures' `Repo` (a bare origin.git
and a work clone on main, the caller's GIT_ variables removed and a private GIT_CONFIG_GLOBAL). No case reaches the
network, starts a session or calls a model."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import launch  # noqa: E402
from omc_fixtures import Repo  # noqa: E402


class CheckPrimary(unittest.TestCase):
    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        self.saved = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.saved)))
        os.environ.clear()
        os.environ.update(self.repo.env)  # launch's git calls inherit the fixture's private git config

    def test_check_primary_names_the_caller(self):
        self.repo.git('switch', '-q', '-c', 'feature/x')
        with self.assertRaises(launch.Refused) as e:
            launch.check_primary(self.repo.work, 'main', why='just investigate reads {base}')
        self.assertIn('just investigate reads main', str(e.exception))
        self.assertIn('the primary checkout is on feature/x, not main', str(e.exception))

    def test_check_primary_defaults_to_design(self):
        self.repo.git('switch', '-q', '-c', 'feature/x')
        with self.assertRaises(launch.Refused) as e:
            launch.check_primary(self.repo.work, 'main')
        self.assertIn('just design cuts its worktrees from main', str(e.exception))

    def test_check_primary_passes_on_base(self):
        launch.check_primary(self.repo.work, 'main')


class LaunchEnv(unittest.TestCase):
    def test_launch_env_merges_extra(self):
        env = launch.launch_env({'PATH': '/x'}, 's', {'OMC_INVESTIGATION': '/f'})
        self.assertEqual(env['OMC_INVESTIGATION'], '/f')
        self.assertEqual(env['OMC_SLUG'], 's')
        self.assertEqual(env['CLAUDE_CODE_DISABLE_TERMINAL_TITLE'], '1')
        self.assertEqual(env['PATH'], '/x')

    def test_launch_env_without_extra(self):
        env = launch.launch_env({'PATH': '/v/bin:/x', 'VIRTUAL_ENV': '/v'}, 's')
        self.assertEqual(env, {'PATH': '/x', 'CLAUDE_CODE_DISABLE_TERMINAL_TITLE': '1', 'OMC_SLUG': 's',
                               'OMC_PROVIDER': 'claude'})


if __name__ == '__main__':
    unittest.main()
