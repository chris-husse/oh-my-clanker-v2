"""Tests of omc/tools/investigate.py, `just investigate <text…>`. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_investigate.py
On test_omc_design.py's fixture: each case gets its own temporary repository from omc_fixtures' `Repo` (its work clone
the primary checkout, its parent the folder `investigations/` goes in), pinned to the fake fork of `FakeGitNexus`; the
tool runs as a subprocess with a private PATH holding test_omc_design.py's fake `wt` (which must never run), fake
`claude` (for `-p` the next answer of FAKE_SLUGS, else its argv logged to claude.log), fake `fish`, `zsh`, `bash` and
`sh` (each logs its argv, cwd, the launch's variables and its init file to shell.log, and exits) and a failing
`direnv`. The prod hook file, `omc/hook/investigation/investigation-context.prod.md`, is written untracked in the
primary unless a case removes it. The recipe's cases run the real `investigate` recipe through `just` (skipped without
one on PATH) on a copy of the real omc/omc.just, `_investigate-start`'s body a stub writing its cwd and arguments to
start.out. No test starts a session or calls a model."""
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import investigate  # noqa: E402
from omc_fixtures import FakeGitNexus, Repo  # noqa: E402
from test_omc_design import FAKE_CLAUDE, FAKE_DIRENV, FAKE_SHELL, FAKE_WT, write_exe  # noqa: E402

TOOL = os.path.join(HERE, 'investigate.py')
OMC_JUST = os.path.join(os.path.dirname(HERE), 'omc.just')  # the recipe tests' real recipes
HOOK = os.path.join('omc', 'hook', 'investigation', 'investigation-context.prod.md')
LAUNCH_VARS = ('CLAUDE_CODE_DISABLE_TERMINAL_TITLE', 'OMC_SLUG', 'OMC_PROVIDER', 'OMC_INVESTIGATION')
SLUG = 'payout-latency-on-prod'
TEXT = 'why are payouts slow on prod'
# investigate.py run with investigate.now fixed first: argv[1] the moment (ISO), the rest the tool's
AT_NOW = ('import datetime, sys; sys.path.insert(0, {here!r}); import investigate; '
          'investigate.now = lambda: datetime.datetime.fromisoformat(sys.argv[1]); '
          'sys.exit(investigate.main(sys.argv[2:]))')
FIXED = datetime.datetime(2026, 11, 23, 14, 5, 9)


class InvestigateCase(unittest.TestCase):
    """The case's repository, fakes and helpers."""

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        tmp = self.repo.root
        self.wt_log = os.path.join(tmp, 'wt.log')
        self.claude_log = os.path.join(tmp, 'claude.log')
        self.prompts = os.path.join(tmp, 'prompts.log')
        self.counter = os.path.join(tmp, 'claude.count')
        self.slug_env = os.path.join(tmp, 'slug-env.log')
        self.shell_log = os.path.join(tmp, 'shell.log')
        self.bin_dir = os.path.join(tmp, 'bin')
        for name, text in (('wt', FAKE_WT.format(python=sys.executable, log=self.wt_log,
                                                 trees=os.path.join(tmp, 'trees'))),
                           ('claude', FAKE_CLAUDE.format(python=sys.executable, log=self.claude_log,
                                                         prompts=self.prompts, counter=self.counter,
                                                         slug_env=self.slug_env, launch_vars=LAUNCH_VARS)),
                           ('direnv', FAKE_DIRENV.format(python=sys.executable, code=127))):
            write_exe(os.path.join(self.bin_dir, name), text)
        for name in ('fish', 'zsh', 'bash', 'sh'):
            write_exe(os.path.join(self.bin_dir, name),
                      FAKE_SHELL.format(python=sys.executable, log=self.shell_log, launch_vars=LAUNCH_VARS))
        self.fake = FakeGitNexus(os.path.join(tmp, 'gitnexus'), self.repo.env)
        self.fake.configure(self.repo)
        self.repo.git('push', '-q', 'origin', 'main')
        self.repo.write(HOOK, '# prod\n')  # the project's own, untracked
        self.path = os.pathsep.join((self.bin_dir, self.fake.bin, os.environ['PATH']))
        self.env = self.fake.env(self.repo.env, path=self.path)
        for name in (*LAUNCH_VARS, 'VIRTUAL_ENV', 'TERM_PROGRAM', 'LC_TERMINAL', 'ITERM_SESSION_ID', 'HERDR_TAB_ID',
                     'HERDR_BIN_PATH'):
            self.env.pop(name, None)  # the caller's (a Claude session's, the uv venv's, the terminal's)
        self.env.update(SHELL='/usr/bin/fish', XDG_CONFIG_HOME=os.path.join(tmp, 'xdg'),
                        OMC_HOME=os.path.join(tmp, 'omc'))
        self.lock = os.path.join(self.repo.work, '.cache', 'omc', 'design.lock')
        self.model = config.load(self.repo.work).orchestrator_model
        self.investigations = os.path.join(self.repo.root, 'investigations')

    def investigate(self, *args, slugs=SLUG, env=None, at=None):
        """The tool run on [args]; [env] over the case's environment; [at] (a datetime) as investigate.now."""
        env = {**self.env, **({'FAKE_SLUGS': slugs} if slugs is not None else {}), **(env or {})}
        argv = (TOOL,) if at is None else ('-c', AT_NOW.format(here=HERE), at.isoformat())
        return subprocess.run((sys.executable, '-I', *argv, *args), cwd=self.repo.work, env=env, capture_output=True,
                              text=True, timeout=60)

    def read(self, path):
        try:
            with open(path, encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return None

    def launches(self):
        return [json.loads(line) for line in (self.read(self.shell_log) or '').splitlines()]

    def folders(self):
        return sorted(os.listdir(self.investigations)) if os.path.isdir(self.investigations) else []

    def assertStarted(self, r, shell='fish'):
        """The run ended in the launch shell [shell] in the primary checkout; the launch's one call, returned."""
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.launches()
        self.assertEqual([(c['shell'], c['cwd']) for c in calls], [(shell, self.repo.work)], r.stderr)
        self.assertIsNone(self.read(self.claude_log))  # the shell runs claude, not the tool
        return calls[0]

    def folder(self):
        """The one investigation folder made, its absolute path."""
        names = self.folders()
        self.assertEqual(len(names), 1, names)
        return os.path.join(self.investigations, names[0])

    def assertRefused(self, r, why=None):
        self.assertEqual((r.returncode, r.stdout), (2, ''), r.stderr)
        last = r.stderr.strip().splitlines()[-1]
        self.assertTrue(last.startswith('error: ' + (why or '')), r.stderr)

    def steps(self, r):
        return [line for line in r.stderr.splitlines() if line.startswith('→ ')]

    def expected_startup(self, folder, text=TEXT, primary=None):
        return ['claude', '-n', SLUG, '--model', self.model, '--add-dir', folder,
                '--settings', investigate.deny_settings(primary or self.repo.work), f'/investigate prod {text}']

    def again(self, keep_folders=False):
        """Ready for one more run in the same case: the shell's log, the slug answers' place and (unless
        [keep_folders]) the investigation folders gone."""
        for path in (self.shell_log, self.counter):
            if os.path.exists(path):
                os.remove(path)
        if not keep_folders and os.path.isdir(self.investigations):
            shutil.rmtree(self.investigations)


class InvestigateTest(InvestigateCase):

    # ---------------------------------------------------------------------------------------------------- refusals
    def test_no_text_is_refused(self):
        for args in ((), (f'--origin={self.repo.work}',), ('  ',)):
            with self.subTest(args=args):
                r = self.investigate(*args)
                self.assertRefused(r, 'nothing to investigate: just investigate <text>')
        self.assertIsNone(self.read(self.prompts))
        self.assertIsNone(self.read(self.shell_log))

    def test_a_missing_prod_hook_is_refused_first(self):
        os.remove(os.path.join(self.repo.work, HOOK))
        r = self.investigate(TEXT)
        self.assertRefused(r)
        self.assertIn('omc/hook/investigation/investigation-context.prod.md', r.stderr)
        self.assertIn('none', r.stderr.strip().splitlines()[-1])
        self.assertFalse(os.path.exists(self.lock), 'the lock file was written')
        self.assertIsNone(self.read(self.claude_log))
        self.assertIsNone(self.read(self.prompts))
        self.assertEqual(self.folders(), [])
        # the files that do exist are named
        self.repo.write(os.path.join('omc', 'hook', 'investigation', 'investigation-context.uat.md'), '# uat\n')
        r = self.investigate(TEXT)
        self.assertRefused(r)
        self.assertIn('investigation-context.uat.md', r.stderr.strip().splitlines()[-1])

    def test_an_off_base_primary_is_refused(self):
        self.repo.git('checkout', '-q', '-b', 'feature/other')
        r = self.investigate(TEXT)
        self.assertRefused(r, 'the primary checkout is on feature/other')
        self.assertIn('just investigate', r.stderr.strip().splitlines()[-1])
        self.assertIsNone(self.read(self.shell_log))
        self.assertEqual(self.folders(), [])

    # ------------------------------------------------------------------------------------------------------ the folder
    def test_the_folder_is_created_empty(self):
        self.assertFalse(os.path.exists(self.investigations))
        r = self.investigate(TEXT)
        self.assertStarted(r)
        folder = self.folder()
        self.assertRegex(os.path.basename(folder), rf'^{SLUG}-\d{{8}}-\d{{6}}$')
        self.assertEqual(os.listdir(folder), [])
        self.assertEqual(investigate.folder(self.repo.work, SLUG, FIXED),
                         os.path.join(self.investigations, f'{SLUG}-20261123-140509'))

    def test_an_existing_folder_is_refused(self):
        existing = investigate.folder(self.repo.work, SLUG, FIXED)
        os.makedirs(existing)
        r = self.investigate(TEXT, at=FIXED)
        self.assertRefused(r)
        self.assertIn(existing, r.stderr)
        self.assertIsNone(self.read(self.shell_log))
        self.assertEqual(os.listdir(existing), [])
        self.again(keep_folders=True)
        r = self.investigate(TEXT, at=FIXED + datetime.timedelta(seconds=1))
        self.assertStarted(r)

    # ------------------------------------------------------------------------------------------------------ the launch
    def test_the_startup_runs_claude_on_investigate_prod(self):
        r = self.investigate(TEXT)
        call = self.assertStarted(r)
        folder = self.folder()
        self.assertTrue(call['argv'][2].endswith('; ' + shlex.join(self.expected_startup(folder))), call['argv'])
        self.assertIn(f'→ session: starting fish on claude "/investigate prod {TEXT}"', r.stderr)
        self.assertEqual(json.loads(investigate.deny_settings(self.repo.work)),
                         {'permissions': {'deny': [f'Edit(/{self.repo.work}/**)', f'Write(/{self.repo.work}/**)',
                                                   f'NotebookEdit(/{self.repo.work}/**)']}})
        self.assertEqual(investigate.startup(SLUG, '', '/f', '/p', 'x', True),
                         ['direnv', 'exec', '.', 'claude', '-n', SLUG, '--add-dir', '/f', '--settings',
                          investigate.deny_settings('/p'), '/investigate prod x'])

    def test_the_seed_survives_quotes(self):
        text = 'why does "x" cost $5; really'
        for shell in ('/usr/bin/fish', '/bin/zsh', '/bin/bash', '/bin/sh'):
            with self.subTest(shell=shell):
                self.again()
                name = os.path.basename(shell)
                r = self.investigate(*text.split(' '), env={'SHELL': shell})
                call = self.assertStarted(r, shell=name)
                startup = shlex.join(self.expected_startup(self.folder(), text))
                script = call['init'] if name in ('zsh', 'bash') else call['argv'][-1]
                self.assertTrue(script.rstrip('\n').endswith(startup), script)
        # run by a real shell, the seed reaches claude as one argument, byte-equal
        if os.path.exists(self.claude_log):
            os.remove(self.claude_log)
        run = subprocess.run(('/bin/sh', '-c', startup), env={**self.env, 'PATH': self.bin_dir + os.pathsep
                                                               + os.environ['PATH']}, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(self.read(self.claude_log))['argv'][-1], f'/investigate prod {text}')

    def test_the_launch_env(self):
        r = self.investigate(TEXT)
        env = self.assertStarted(r)['env']
        self.assertEqual((env['CLAUDE_CODE_DISABLE_TERMINAL_TITLE'], env['OMC_SLUG'], env['OMC_PROVIDER'],
                          env['OMC_INVESTIGATION']), ('1', SLUG, 'claude', self.folder()))
        self.assertTrue(os.path.isabs(env['OMC_INVESTIGATION']))

    def test_the_title_is_the_slug_and_fixed(self):
        r = self.investigate(TEXT)
        fish = self.assertStarted(r)['argv'][2]
        self.assertIn(f'set -g __omc_desired_title {SLUG}; ', fish)
        self.assertNotIn('git branch --show-current', fish)
        self.assertIn('set -g OMC_FISH_TITLE_DISABLE 1', fish)
        self.again()
        r = self.investigate(TEXT, env={'SHELL': '/bin/sh'})
        sh = self.assertStarted(r, shell='sh')['argv'][1]
        self.assertTrue(sh.startswith(shlex.join([*investigate.launch.terminal_title_argv(), SLUG]) + ' || :; '), sh)

    def test_inside_herdr_the_tab_is_the_slug(self):
        log = os.path.join(self.repo.root, 'herdr.log')
        fake = os.path.join(self.bin_dir, 'fake-herdr')
        write_exe(fake, f'#!/bin/sh\nprintf \'%s\\n\' "$*" >> {shlex.quote(log)}\n')
        r = self.investigate(TEXT, env={'TERM_PROGRAM': 'herdr', 'HERDR_TAB_ID': 'wW:t9', 'HERDR_BIN_PATH': fake})
        self.assertStarted(r)
        self.assertEqual(self.read(log), f'tab rename wW:t9 {SLUG}\n')
        self.assertIn(f'→ herdr tab: {SLUG} [ok]', self.steps(r))

    def test_no_worktree_no_brief_no_notification(self):
        r = self.investigate(TEXT)
        call = self.assertStarted(r)
        self.assertIsNone(self.read(self.wt_log))
        self.assertFalse(os.path.exists(os.path.join(self.repo.work, '.cache', 'omc', 'brief.md')))
        self.assertIsNone(call['settings'])
        self.assertFalse(os.path.exists(os.path.join(self.repo.work, '.claude', 'settings.local.json')))
        self.assertNotIn('notifications', r.stderr)
        self.assertEqual(self.repo.git('worktree', 'list', '--porcelain').count('worktree '), 1)

    def test_the_step_lines(self):
        r = self.investigate(TEXT)
        self.assertStarted(r)
        starts = ['→ hook:', '→ lock:', '→ primary: pulling origin/main', '→ lock: released', '→ slug:',
                  '→ GitNexus: checking the build', '→ GitNexus: refreshing the index', '→ folder:',
                  '→ session: starting fish on claude']
        if sys.platform == 'darwin':
            starts.insert(1, '→ fish title hook: reconciling')
        lines = self.steps(r)
        self.assertEqual(len(lines), len(starts), r.stderr)
        for line, start in zip(lines, starts):
            self.assertTrue(line.startswith(start), (start, r.stderr))
        self.assertIn(f'→ slug: {SLUG} [ok]', lines)

    # ----------------------------------------------------------------------------------------------------- the recipe
    def stubbed_omc_just(self, marker=None):
        """The real omc/omc.just, `_investigate-start`'s body replaced by a stub writing [marker] (when given),
        `$PWD` and its arguments, one per line, to <tmp>/start.out."""
        with open(OMC_JUST, encoding='utf-8') as f:
            lines = f.read().splitlines()
        at = next((i for i, line in enumerate(lines) if line.lstrip('@').startswith('_investigate-start *ARGS:')),
                  None)
        self.assertIsNotNone(at, f'no `_investigate-start *ARGS:` recipe in {OMC_JUST}')
        end = at + 1
        while end < len(lines) and lines[end].startswith((' ', '\t')):
            end += 1
        words = (shlex.quote(marker) + ' ') if marker else ''
        stub = f'    printf \'%s\\n\' {words}"$PWD" "$@" > {shlex.quote(self.start_out)}'
        return '\n'.join(lines[:at + 1] + [stub] + lines[end:]) + '\n'

    def test_the_recipe_runs_the_pulled_justfile(self):
        just = shutil.which('just')
        if just is None:
            self.skipTest('just is not on PATH')
        self.start_out = os.path.join(self.repo.root, 'start.out')
        self.repo.write('justfile', "import 'omc/omc.just'\n")
        self.repo.write('omc/omc.just', self.stubbed_omc_just())
        self.repo.git('add', '--', 'justfile', 'omc/omc.just')
        self.repo.git('commit', '-q', '-m', 'the justfile')
        self.repo.git('push', '-q', 'origin', 'main')
        sha = self.repo.advance_origin('omc/omc.just', self.stubbed_omc_just('pulled'))
        tree = os.path.join(self.repo.root, 'trees', 'side')
        self.repo.git('worktree', 'add', '-q', '-b', 'side', tree)
        os.makedirs(os.path.join(tree, 'notes'))
        env = {**self.env, 'PATH': os.environ['PATH']}
        r = subprocess.run((just, 'investigate', 'why', 'are "payouts"', 'slow'), cwd=tree, env=env,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.repo.git('rev-parse', 'HEAD').strip(), sha)
        self.assertEqual(self.read(self.start_out).splitlines(),
                         ['pulled', self.repo.work, f'--origin={tree}', 'why', 'are "payouts"', 'slow'])
        self.assertNotIn('#!/usr/bin/env bash', r.stderr)
        listed = subprocess.run((just, '--list'), cwd=self.repo.work, capture_output=True, text=True)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        names = [line.split()[0] for line in listed.stdout.splitlines()[1:] if line.strip()]
        self.assertIn('investigate', names)
        self.assertNotIn('_investigate-start', names)  # private


class SpacedPrimary(InvestigateCase):
    """The fixture under a directory whose name holds a space."""

    def setUp(self):
        spaced = tempfile.TemporaryDirectory()
        self.addCleanup(spaced.cleanup)
        parent = os.path.join(os.path.realpath(spaced.name), 'with a space')
        os.makedirs(parent)
        saved, tempfile.tempdir = tempfile.tempdir, parent
        try:
            super().setUp()
        finally:
            tempfile.tempdir = saved

    def test_a_primary_path_with_spaces(self):
        self.assertIn(' ', self.repo.work)
        deny = json.loads(investigate.deny_settings(self.repo.work))
        self.assertEqual(deny['permissions']['deny'][0], f'Edit(/{self.repo.work}/**)')
        r = self.investigate(TEXT, env={'SHELL': '/bin/bash'})
        call = self.assertStarted(r, shell='bash')
        startup = call['init'].rstrip('\n').splitlines()[-1]
        words = shlex.split(startup)
        folder = self.folder()
        self.assertEqual(words, self.expected_startup(folder))
        self.assertEqual(words[words.index('--add-dir') + 1], folder)
        self.assertEqual(json.loads(words[words.index('--settings') + 1]), deny)


if __name__ == '__main__':
    unittest.main()
