"""Tests of omc/tools/omc.py, the entry of `just omc`. Run from the
repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_cli.py
The tool runs as a subprocess in one temporary repository, omc_fixtures' `Repo` (a bare origin.git and a work clone on
main, the caller's GIT_ variables removed and a private GIT_CONFIG_GLOBAL) with a copy of omc/ committed and pushed;
each case starts without the marker."""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from omc_fixtures import Repo  # noqa: E402

OMC = os.path.dirname(HERE)
MARKER = os.path.join('.cache', 'omc', 'current')
RESUME = ('you are in /audit (omc/pipeline/audit/SKILL.md): read it again and start it at its first step; the steps '
          'that are done skip themselves\n')


class CliTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo = Repo.make_repo()
        cls.work, cls.env = cls.repo.work, cls.repo.env
        shutil.copytree(OMC, os.path.join(cls.work, 'omc'), ignore=shutil.ignore_patterns('__pycache__'),
                        dirs_exist_ok=True)
        cls.repo.git('add', '-A')
        cls.repo.git('commit', '-q', '-m', 'omc')
        cls.repo.git('push', '-q', 'origin', 'main')
        cls.outside = os.path.join(cls.repo.root, 'outside')
        os.makedirs(cls.outside)

    @classmethod
    def tearDownClass(cls):
        cls.repo.cleanup()

    def setUp(self):
        shutil.rmtree(os.path.join(self.work, '.cache'), ignore_errors=True)

    def omc(self, *args, cwd=None):
        tool = os.path.join(self.work, 'omc', 'tools', 'omc.py')
        return subprocess.run((sys.executable, '-I', tool, *args), cwd=cwd or self.work, env=self.env,
                              capture_output=True, text=True)

    def marker(self):
        return os.path.join(self.work, MARKER)

    def test_enter_writes_and_done_removes_the_marker(self):
        r = self.omc('enter', 'implement')
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, '', ''))
        with open(self.marker(), encoding='utf-8') as f:
            self.assertEqual(f.read().strip(), 'implement')
        r = self.omc('enter', '--done')
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, '', ''))
        self.assertFalse(os.path.exists(self.marker()))
        r = self.omc('enter', '--done')     # absent is fine
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_enter_refuses_another_word(self):
        for args in (('enter', 'finish'), ('enter',), ('enter', 'audit', '--done')):
            with self.subTest(args=args):
                r = self.omc(*args)
                self.assertEqual(r.returncode, 2)
                self.assertTrue(r.stderr.startswith('error: '), r.stderr)
                self.assertFalse(os.path.exists(self.marker()))

    def test_resume_prints_the_line_only_with_a_marker(self):
        r = self.omc('enter', '--resume')
        self.assertEqual((r.returncode, r.stdout), (0, ''), r.stderr)
        self.assertEqual(self.omc('enter', 'audit').returncode, 0)
        r = self.omc('enter', '--resume')
        self.assertEqual((r.returncode, r.stdout), (0, RESUME), r.stderr)
        r = self.omc('enter', '--resume', cwd=self.outside)
        self.assertEqual((r.returncode, r.stdout), (0, ''), r.stderr)

    def test_an_unknown_verb_is_refused(self):
        for args in (('finish',), ()):
            with self.subTest(args=args):
                r = self.omc(*args)
                self.assertEqual(r.returncode, 2)
                self.assertTrue(r.stderr.startswith('error: '), r.stderr)

    def test_models_through_the_entry(self):
        for role, model in (('orchestrator', 'opus'), ('harden', 'fable'), ('simple', 'sonnet'), ('medium', 'opus'),
                            ('high', 'opus')):
            with self.subTest(role=role):
                r = self.omc('models', role)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.count('\n'), 1)
                self.assertEqual(json.loads(r.stdout), {'role': role, 'model': model, 'effort': ''})
        for role in ('design', 'plan', 'review', 'cheap'):
            with self.subTest(role=role):
                r = self.omc('models', role)
                self.assertEqual((r.returncode, r.stdout), (2, ''))
                self.assertTrue(r.stderr.startswith('error: '), r.stderr)

    def test_handoff_answers_from_the_yaml(self):
        r = self.omc('handoff')
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, 'continue\n', ''))
        path = os.path.join(self.work, 'omc', 'config.yaml')
        with open(path, encoding='utf-8') as f:
            text = f.read()

        def restore():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
        self.addCleanup(restore)
        for line, code, out in (('ask_for_provider_handoff: true', 0, 'ask\n'),
                                ('ask_for_provider_handoff: maybe', 2, '')):
            with self.subTest(line=line):
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(re.sub(r'^ask_for_provider_handoff: .*$', line, text, flags=re.M))
                r = self.omc('handoff')
                self.assertEqual((r.returncode, r.stdout), (code, out), r.stderr)
                if code:
                    self.assertTrue(r.stderr.startswith('error: '), r.stderr)

    def test_enter_brainstorm_and_its_resume(self):
        self.assertEqual(self.omc('enter', 'brainstorm').returncode, 0)
        with open(self.marker(), encoding='utf-8') as f:
            self.assertEqual(f.read().strip(), 'brainstorm')
        r = self.omc('enter', '--resume')
        self.assertEqual((r.returncode, r.stdout), (0, RESUME.replace('audit', 'brainstorm')), r.stderr)

    def ported_env(self):
        """The ported verbs' environment: HOME, OMC_HOME and XDG_CONFIG_HOME under the temporary repository's root, no
        iTerm2 session."""
        home = os.path.join(self.repo.root, 'home')
        env = {k: v for k, v in self.env.items() if k not in ('ITERM_SESSION_ID', 'TERM_PROGRAM', 'LC_TERMINAL')}
        env.update(HOME=home, OMC_HOME=os.path.join(home, '.omc'), XDG_CONFIG_HOME=os.path.join(home, '.config'))
        return home, env

    def ported(self, *args, env):
        tool = os.path.join(self.work, 'omc', 'tools', 'omc.py')
        return subprocess.run((sys.executable, '-I', tool, *args), cwd=self.outside, env=env, capture_output=True,
                              text=True)

    def test_title_parses_and_reaches_its_module(self):
        _, env = self.ported_env()
        for args in (('title', 'set', '--', 'feature/x'), ('title', 'release'), ('title', 'apply', 'nope')):
            with self.subTest(args=args):
                r = self.ported(*args, env=env)
                self.assertEqual((r.returncode, r.stdout), (2, ''))
                self.assertTrue(r.stderr.startswith('error: omc title: ITERM_SESSION_ID is missing or malformed'),
                                r.stderr)
        for args in (('title',), ('title', 'pin', 'x'), ('title', 'set')):
            with self.subTest(args=args):
                r = self.ported(*args, env=env)
                self.assertEqual(r.returncode, 2)
                self.assertTrue(r.stderr.startswith('error: '), r.stderr)

    def test_shell_integration_parses_and_reaches_its_module(self):
        home, env = self.ported_env()
        r = self.ported('shell-integration', 'fish', 'status', env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        path = os.path.join(home, '.config', 'fish', 'conf.d', 'omc-title.fish')
        self.assertEqual(json.loads(r.stdout), {'enabled': True, 'installed': False, 'path': path, 'owned': False})
        for args in (('shell-integration',), ('shell-integration', 'zsh', 'status'),
                     ('shell-integration', 'fish', 'install')):
            with self.subTest(args=args):
                r = self.ported(*args, env=env)
                self.assertEqual(r.returncode, 2)
                self.assertTrue(r.stderr.startswith('error: '), r.stderr)

    def test_record_without_one_is_exit_1(self):
        r = self.omc('record')
        self.assertEqual((r.returncode, r.stdout), (1, 'no record committed on this branch\n'), r.stderr)

if __name__ == '__main__':
    unittest.main()
