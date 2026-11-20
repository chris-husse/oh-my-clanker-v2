"""Tests of omc/tools/design.py, `just design <brief-or-text>`. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_design.py
Each case gets its own temporary repository from omc_fixtures' `Repo` (a bare origin.git and a work clone on
main, the primary checkout, the caller's GIT_ variables removed and a private GIT_CONFIG_GLOBAL), pinned to the fake
fork of omc_fixtures' `FakeGitNexus` (a temporary `HOME`, stub `node` and `npm`), so no case reaches the network; the
tool runs as a subprocess with a private PATH holding a fake `wt` (it logs its argv to wt.log, adds the worktree with
`git worktree add` and prints `{"path": …}`), a fake `claude` (for `-p` it prints the next answer of FAKE_SLUGS and
logs its title variables), fake `fish`, `zsh`, `bash` and `sh` (the launch shell: each logs its argv, cwd, the
variables of the launch, its init file and the worktree's settings.local.json to shell.log, and exits), a `direnv`
that fails (as none) unless a case puts a working one first, and the fork's stubs; `XDG_CONFIG_HOME` and `OMC_HOME`
are temporary. The recipe's cases run the real `design` recipe through `just` (skipped without one on PATH) on a
copy of the real omc/omc.just, imported by a justfile, committed and pushed in the fixture, `_design-start`'s body a
stub that writes its cwd and arguments to start.out, so they need no uv. No test starts a session or calls a model."""
import fcntl
import json
import os
import select
import shlex
import shutil
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import design  # noqa: E402
from omc_fixtures import FakeGitNexus, Repo  # noqa: E402

TOOL = os.path.join(HERE, 'design.py')
OMC_JUST = os.path.join(os.path.dirname(HERE), 'omc.just')  # the recipe tests' real recipes
SESSION = '/brainstorm .cache/omc/brief.md'
LAUNCH_VARS = ('CLAUDE_CODE_DISABLE_TERMINAL_TITLE', 'OMC_SLUG', 'OMC_PROVIDER')
# design.py run with sys.platform set first (the reconcile is macOS only): argv[1] the platform, the rest the tool's
ON_PLATFORM = ('import sys; sys.path.insert(0, {here!r}); import design; sys.platform = sys.argv[1]; '
               'sys.exit(design.main(sys.argv[2:]))')

# worktrunk's `wt switch [--create] <branch> [--base <base>] --no-cd --yes --format=json`, faked: argv to wt.log, the
# worktree added under <tmp>/trees/, its path on stdout as JSON
FAKE_WT = '''#!{python}
import json, os, subprocess, sys
args = sys.argv[1:]
with open({log!r}, 'a', encoding='utf-8') as f:
    f.write(' '.join(args) + '\\n')
words = [a for a in args if not a.startswith('--')]
branch = words[1]
base = args[args.index('--base') + 1] if '--base' in args else None
path = os.path.join({trees!r}, branch.replace('/', '-'))
if not os.path.isdir(path):
    cmd = ['git', 'worktree', 'add', '-q']
    cmd += ['-b', branch, path] + ([base] if base else []) if '--create' in args else [path, branch]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        sys.exit(1)
print(json.dumps({{'path': path}}))
'''

# Claude Code, faked: `claude -p <prompt>` prints the next answer of FAKE_SLUGS (comma-separated; a counter file
# keeps the place), logs the prompt to prompts.log and the launch's variables it got to slug-env.log; any other call
# logs its argv and cwd to claude.log
FAKE_CLAUDE = '''#!{python}
import json, os, sys
if sys.argv[1:2] == ['-p']:
    with open({prompts!r}, 'a', encoding='utf-8') as f:
        f.write(json.dumps(sys.argv[2]) + '\\n')
    with open({slug_env!r}, 'a', encoding='utf-8') as f:
        f.write(json.dumps({{k: os.environ.get(k) for k in {launch_vars!r}}}) + '\\n')
    n = int(open({counter!r}).read()) if os.path.exists({counter!r}) else 0
    open({counter!r}, 'w').write(str(n + 1))
    answers = os.environ.get('FAKE_SLUGS', '').split(',')
    print(answers[n] if n < len(answers) else '')
    sys.exit(0)
with open({log!r}, 'a', encoding='utf-8') as f:
    f.write(json.dumps({{'argv': sys.argv[1:], 'cwd': os.getcwd()}}) + '\\n')
'''


# The launch shell, faked (one script named fish, zsh, bash and sh): logs one JSON line to shell.log, the shell's
# name, its argv, its cwd, the variables of the launch, the init file it was given (zsh's $ZDOTDIR/.zshrc, bash's
# --rcfile) and the worktree's .claude/settings.local.json as the exec found them; then exits 0
FAKE_SHELL = '''#!{python}
import json, os, sys
def read(path):
    try:
        return open(path, encoding='utf-8').read()
    except (OSError, TypeError):
        return None
name, args = os.path.basename(sys.argv[0]), sys.argv[1:]
init = None
if name == 'zsh':
    init = read(os.path.join(os.environ.get('ZDOTDIR', ''), '.zshrc'))
elif name == 'bash' and '--rcfile' in args:
    init = read(args[args.index('--rcfile') + 1])
with open({log!r}, 'a', encoding='utf-8') as f:
    f.write(json.dumps({{'shell': name, 'argv': args, 'cwd': os.getcwd(), 'init': init,
                        'env': {{k: os.environ.get(k) for k in ('VIRTUAL_ENV', 'PATH', *{launch_vars!r})}},
                        'settings': read(os.path.join('.claude', 'settings.local.json'))}}) + '\\n')
'''

# `direnv version`, faked: exits [code]
FAKE_DIRENV = '''#!{python}
import sys
sys.exit({code})
'''


def write_exe(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    os.chmod(path, 0o755)


class DesignCase(unittest.TestCase):
    """The case's repository, fakes and helpers; the tests are DesignTest's and Deferred's."""

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
        self.trees = os.path.join(tmp, 'trees')
        self.bin_dir = os.path.join(tmp, 'bin')
        for name, text in (('wt', FAKE_WT.format(python=sys.executable, log=self.wt_log, trees=self.trees)),
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
        self.path = os.pathsep.join((self.bin_dir, self.fake.bin, os.environ['PATH']))
        self.env = self.fake.env(self.repo.env, path=self.path)
        for name in (*LAUNCH_VARS, 'VIRTUAL_ENV', 'TERM_PROGRAM', 'LC_TERMINAL', 'ITERM_SESSION_ID', 'HERDR_TAB_ID',
                     'HERDR_BIN_PATH'):
            self.env.pop(name, None)  # the caller's (a Claude session's, the uv venv's, the terminal's)
        self.env.update(SHELL='/usr/bin/fish', XDG_CONFIG_HOME=os.path.join(tmp, 'xdg'),
                        OMC_HOME=os.path.join(tmp, 'omc'))
        self.lock = os.path.join(self.repo.work, '.cache', 'omc', 'design.lock')
        self.model = config.load(self.repo.work).orchestrator_model

    def design(self, *args, slugs=None, flags=None, env=None, platform=None):
        """The tool run on [args]; [env] over the case's environment; [platform] set as sys.platform first."""
        env = {**self.env, **({'FAKE_SLUGS': slugs} if slugs is not None else {}), **(env or {})}
        if flags:
            env['FAKE_GITNEXUS'] = flags
        argv = (TOOL,) if platform is None else ('-c', ON_PLATFORM.format(here=HERE), platform)
        return subprocess.run((sys.executable, '-I', *argv, *args), cwd=self.repo.work, env=env, capture_output=True,
                              text=True, timeout=60)

    def read(self, path):
        try:
            with open(path, encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return None

    def tree(self, branch):
        return os.path.join(self.trees, branch.replace('/', '-'))

    def launches(self):
        """The launch shell's calls, from shell.log."""
        return [json.loads(line) for line in (self.read(self.shell_log) or '').splitlines()]

    def assertStarted(self, r, branch, brief, shell='fish'):
        """The run ended in the launch shell [shell] inside the worktree of [branch], whose brief is [brief]; the
        launch's one call, returned."""
        self.assertEqual(r.returncode, 0, r.stderr)
        tree = self.tree(branch)
        self.assertEqual(self.read(os.path.join(tree, '.cache', 'omc', 'brief.md')), brief)
        calls = self.launches()
        self.assertEqual([(c['shell'], c['cwd']) for c in calls], [(shell, tree)], r.stderr)
        self.assertIsNone(self.read(self.claude_log))  # the shell runs claude, not the tool
        self.assertEqual(self.repo.git('rev-parse', '--abbrev-ref', 'HEAD', cwd=tree).strip(), branch)
        return calls[0]

    def again(self):
        """Ready for one more run of the tool in the same case: the shell's log and the slug answers' place gone."""
        for path in (self.shell_log, self.counter):
            if os.path.exists(path):
                os.remove(path)

    def startup(self, slug, model=None, direnv=False):
        """The startup command the launch shell runs, joined."""
        argv = ['claude', '-n', slug, '--model', self.model if model is None else model, SESSION]
        return shlex.join((['direnv', 'exec', '.'] if direnv else []) + argv)

    def assertRefused(self, r, why=None):
        """Exit 2, nothing on stdout, stderr's last line `error: <why>` ([why] its start when given)."""
        self.assertEqual((r.returncode, r.stdout), (2, ''), r.stderr)
        last = r.stderr.strip().splitlines()[-1]
        self.assertTrue(last.startswith('error: ' + (why or '')), r.stderr)

    def steps(self, r):
        """stderr's step lines, `→ …`."""
        return [line for line in r.stderr.splitlines() if line.startswith('→ ')]

    def read_until(self, p, text, timeout=10):
        """What [p] wrote on stderr until [text] is in it (a step's line stays open, with no newline, while it
        waits); fails after [timeout] seconds."""
        seen, end = '', time.monotonic() + timeout
        while text not in seen:
            ready, _, _ = select.select([p.stderr], [], [], max(0.0, end - time.monotonic()))
            self.assertTrue(ready, f'no {text!r} on stderr: {seen!r}')
            chunk = os.read(p.stderr.fileno(), 4096).decode('utf-8')
            self.assertTrue(chunk, f'stderr closed before {text!r}: {seen!r}')
            seen += chunk
        return seen


class DesignTest(DesignCase):

    # ------------------------------------------------------------------------------------------------------- the slug
    def test_a_brief_gives_its_name(self):
        brief = '# Location tracker device tests\n\nRun the tracker on a device.\n'
        self.repo.write('tasks/location-tracker-device-tests.md', brief)
        r = self.design('tasks/location-tracker-device-tests.md')
        self.assertEqual(self.read(self.wt_log), 'switch --create feature/location-tracker-device-tests '
                                                 '--base origin/main --no-cd --yes --format=json\n')
        self.assertStarted(r, 'feature/location-tracker-device-tests', brief)
        self.assertIsNone(self.read(self.prompts))  # no model asked

    def test_the_recipes_origin_is_taken_off_first(self):
        brief = '# Location tracker device tests\n'
        self.repo.write('tasks/location-tracker-device-tests.md', brief)
        r = self.design(f'--origin={self.repo.work}', 'tasks/location-tracker-device-tests.md')
        self.assertStarted(r, 'feature/location-tracker-device-tests', brief)
        self.assertRefused(self.design(f'--origin={self.repo.work}'))
        self.assertIsNone(self.read(self.prompts))

    def test_free_text_asks_claude_for_the_slug(self):
        r = self.design('add', 'a', 'weekly', 'payout', 'report', slugs='add-weekly-payout-report')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        prompts = [json.loads(line) for line in self.read(self.prompts).splitlines()]
        self.assertEqual(len(prompts), 1)
        self.assertTrue(prompts[0].endswith('The work: add a weekly payout report'), prompts[0])
        self.assertIn('--create feature/add-weekly-payout-report --base origin/main', self.read(self.wt_log))

    def test_a_bad_slug_is_asked_once_more_then_refused(self):
        r = self.design('add', 'a', 'weekly', 'payout', 'report', slugs='Bad Slug,two')
        self.assertRefused(r)
        self.assertEqual(self.read(self.counter), '2')
        self.assertIsNone(self.read(self.wt_log))
        self.assertIsNone(self.read(self.shell_log))

    # --------------------------------------------------------------------------------------------------- the worktree
    def test_an_existing_branch_is_entered_again(self):
        self.repo.git('branch', 'feature/add-weekly-payout-report')
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertEqual(self.read(self.wt_log), 'switch feature/add-weekly-payout-report --no-cd --yes --format=json\n')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')

    # ------------------------------------------------------------------------------------------------------- the lock
    def hold_the_lock(self):
        """The start's lock, taken by the test (an open file; closing it releases the lock)."""
        os.makedirs(os.path.dirname(self.lock), exist_ok=True)
        held = open(self.lock, 'a')
        fcntl.flock(held, fcntl.LOCK_EX)
        return held

    def start(self, *args, slugs=None):
        env = {**self.env, **({'FAKE_SLUGS': slugs} if slugs is not None else {})}
        p = subprocess.Popen((sys.executable, '-I', TOOL, *args), cwd=self.repo.work, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.addCleanup(lambda: p.poll() is None and p.kill())
        return p

    def finish(self, p, seen=''):
        out, err = p.communicate(timeout=60)
        return subprocess.CompletedProcess(p.args, p.returncode, out.decode('utf-8'), seen + err.decode('utf-8'))

    def test_a_second_start_waits_on_the_lock(self):
        self.repo.write('tasks/location-tracker-device-tests.md', 'the brief\n')
        with self.hold_the_lock() as held:
            p = self.start('tasks/location-tracker-device-tests.md')
            seen = self.read_until(p, '→ lock: waiting for another start …')
            time.sleep(0.5)
            self.assertIsNone(self.read(self.wt_log))
            self.assertIsNone(p.poll())
            fcntl.flock(held, fcntl.LOCK_UN)
        self.assertStarted(self.finish(p, seen), 'feature/location-tracker-device-tests', 'the brief\n')

    def test_the_slug_is_made_outside_the_lock(self):
        with self.hold_the_lock() as held:
            p = self.start('add a weekly payout report', slugs='add-weekly-payout-report')
            seen = self.read_until(p, '→ lock: waiting for another start …')
            self.assertEqual(len(self.read(self.prompts).splitlines()), 1)  # asked while the lock is held
            self.assertIsNone(self.read(self.wt_log))
            self.assertIsNone(p.poll())
            fcntl.flock(held, fcntl.LOCK_UN)
        self.assertStarted(self.finish(p, seen), 'feature/add-weekly-payout-report', 'add a weekly payout report\n')

    # ------------------------------------------------------------------------------------------------- the step lines
    def test_the_step_lines(self):
        self.repo.write('tasks/location-tracker-device-tests.md', 'the brief\n')
        r = self.design('tasks/location-tracker-device-tests.md')
        self.assertStarted(r, 'feature/location-tracker-device-tests', 'the brief\n')
        lines = self.steps(r)
        starts = ['→ primary:', '→ slug:', '→ lock:', '→ primary: pulling origin/main', '→ worktree:', '→ lock: released',
                  '→ GitNexus: checking the build', '→ GitNexus: refreshing the index',  # outside the start's lock
                  '→ notifications: .claude/settings.local.json', f'→ session: starting fish on claude "{SESSION}"']
        if sys.platform == 'darwin':  # the fish title hook is reconciled on macOS only, after the slug
            starts.insert(2, '→ fish title hook: reconciling')
        self.assertEqual(len(lines), len(starts), r.stderr)
        for line, start in zip(lines, starts):
            self.assertTrue(line.startswith(start), (start, r.stderr))
        for line in lines[:-1]:
            self.assertTrue(line.endswith('[ok]'), r.stderr)
        self.assertEqual(lines[1], '→ slug: location-tracker-device-tests [ok]')
        self.assertNotIn('GitNexus is stale', r.stderr)

    def test_a_failed_gitnexus_step_does_not_stop_the_start(self):
        shutil.rmtree(self.fake.origin)  # the fork cannot be cloned
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        lines = r.stderr.splitlines()
        at = next(i for i, line in enumerate(lines) if line.startswith('→ GitNexus: checking the build'))
        self.assertRegex(lines[at], r' \[failed\] \S', r.stderr)
        self.assertEqual(lines[at + 1], 'GitNexus is stale: /explain answers from no index', r.stderr)
        self.assertFalse(any(line.startswith('→ GitNexus: refreshing') for line in lines), r.stderr)

    def test_a_refresh_under_way_in_another_start_is_left_to_it(self):
        gitnexus_lock = os.path.join(self.repo.work, '.cache', 'omc', 'gitnexus.lock')
        os.makedirs(os.path.dirname(gitnexus_lock), exist_ok=True)
        with open(gitnexus_lock, 'a') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        lines = self.steps(r)
        self.assertIn('→ GitNexus: another start is refreshing the index [ok]', lines, r.stderr)
        self.assertFalse(any(line.startswith(('→ GitNexus: checking', '→ GitNexus: refreshing')) for line in lines),
                         r.stderr)
        self.assertNotIn('GitNexus is stale', r.stderr)

    def test_a_keyword_only_refresh_warns(self):
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report', flags='embed-fails')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        refresh = [line for line in self.steps(r) if line.startswith('→ GitNexus: refreshing the index')]
        self.assertEqual(len(refresh), 1, r.stderr)
        self.assertTrue(refresh[0].endswith('[warn] keyword-only (embedding failed)'), r.stderr)

    # ---------------------------------------------------------------------------------------------------- the primary
    def assertNothingWritten(self, r, why):
        self.assertRefused(r, why)
        self.assertIsNone(self.read(self.wt_log))
        self.assertIsNone(self.read(self.shell_log))
        self.assertFalse(os.path.exists(self.lock), 'the lock file was written')

    def test_an_off_base_primary_is_refused(self):
        self.repo.git('checkout', '-q', '-b', 'feature/other')
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertNothingWritten(r, 'the primary checkout is on feature/other')

    def test_a_primary_with_changes_is_refused(self):
        self.repo.write('.gitignore', '.cache/\nbuild/\n')
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertNothingWritten(r, 'the primary checkout has changes')

    def test_a_diverged_primary_is_refused(self):
        self.repo.advance_origin('theirs.txt', 'theirs\n')
        self.repo.commit('ours.txt', 'ours\n', 'ours')
        self.repo.git('fetch', '-q', 'origin')
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertNothingWritten(r, 'the primary checkout has diverged from origin/main')

    def advance_origin_by_a_commit(self):
        """origin's main advanced by one commit; the new sha."""
        return self.repo.advance_origin('notes/pulled.txt', 'pulled\n')

    def test_a_primary_behind_origin_is_pulled_and_a_move_in_the_lock_warns(self):
        sha = self.advance_origin_by_a_commit()
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        self.assertEqual(self.repo.git('rev-parse', 'HEAD').strip(), sha)
        pull = [line for line in self.steps(r) if line.startswith('→ primary: pulling')]
        self.assertEqual(len(pull), 1, r.stderr)
        self.assertIn(sha[:7], pull[0])
        self.assertIn('moved since the start', r.stderr)  # the [warn], and the start goes on
        self.assertEqual(len(self.read(self.prompts).splitlines()), 1)  # claude -p asked once

    def test_a_current_primary_pulls_without_a_warning(self):
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        pull = [line for line in self.steps(r) if line.startswith('→ primary: pulling')]
        self.assertEqual(len(pull), 1, r.stderr)
        self.assertIn('(current)', pull[0])
        self.assertTrue(pull[0].endswith('[ok]'), r.stderr)
        self.assertNotIn('moved since the start', r.stderr)

    def test_untracked_files_are_no_changes(self):
        self.repo.write('notes.txt', 'mine\n')
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')

    # ------------------------------------------------------------------------------------------------- the launch
    def test_the_launch_execs_the_shell_of_SHELL(self):
        brief = '# Location tracker device tests\n'
        self.repo.write('tasks/location-tracker-device-tests.md', brief)
        branch, slug = 'feature/location-tracker-device-tests', 'location-tracker-device-tests'
        for shell, name in (('/usr/bin/fish', 'fish'), ('/bin/zsh', 'zsh'), ('/bin/bash', 'bash'), ('/bin/sh', 'sh'),
                            ('/usr/local/bin/tcsh', 'sh')):
            with self.subTest(shell=shell):
                self.again()
                r = self.design('tasks/location-tracker-device-tests.md', env={'SHELL': shell})
                call = self.assertStarted(r, branch, brief, shell=name)
                self.assertIn(f'→ session: starting {name} on claude "{SESSION}"', r.stderr)
                startup = self.startup(slug)
                if name == 'fish':
                    self.assertEqual(call['argv'][:2], ['-i', '-C'])
                    self.assertTrue(call['argv'][2].endswith('; ' + startup), call['argv'])
                elif name == 'zsh':
                    self.assertEqual(call['argv'], ['-i'])
                    self.assertTrue(call['init'].endswith(startup + '\n'), call['init'])
                elif name == 'bash':
                    self.assertEqual((call['argv'][0], call['argv'][2:]), ('--rcfile', ['-i']))
                    self.assertTrue(call['argv'][1].endswith('/rc.bash'), call['argv'])
                    self.assertTrue(call['init'].endswith(startup + '\n'), call['init'])
                else:
                    self.assertEqual(call['argv'][0], '-c')
                    self.assertTrue(call['argv'][1].endswith(' || :; ' + startup), call['argv'])

    def test_the_startup_runs_claude_on_brainstorm(self):
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        call = self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        self.assertTrue(call['argv'][2].endswith('; ' + self.startup('add-weekly-payout-report')), call['argv'])
        self.assertNotIn('direnv', call['argv'][2])
        self.again()
        with_direnv = os.path.join(self.repo.root, 'direnv-bin')
        write_exe(os.path.join(with_direnv, 'direnv'), FAKE_DIRENV.format(python=sys.executable, code=0))
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report',
                        env={'PATH': with_direnv + os.pathsep + self.path})
        call = self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        self.assertTrue(call['argv'][2].endswith('; ' + self.startup('add-weekly-payout-report', direnv=True)),
                        call['argv'])
        # no --model for an empty model (config.yaml refuses one; the argv is the tool's own)
        self.assertEqual(design.startup('add-weekly-payout-report', '', False),
                         ['claude', '-n', 'add-weekly-payout-report', SESSION])
        self.assertEqual(design.startup('add-weekly-payout-report', '', True),
                         ['direnv', 'exec', '.', 'claude', '-n', 'add-weekly-payout-report', SESSION])

    def test_the_title_is_the_full_branch(self):
        branch = 'feature/add-weekly-payout-report'
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        fish = self.assertStarted(r, branch, 'add a weekly payout report\n')['argv'][2]
        self.assertIn(f'set -g __omc_desired_title {branch}; ', fish)
        self.assertIn(shlex.join(design.terminal_title_argv()) + ' "$__omc_desired_title"; or true', fish)
        self.again()
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report', env={'SHELL': '/bin/sh'})
        sh = self.assertStarted(r, branch, 'add a weekly payout report\n', shell='sh')['argv'][1]
        self.assertTrue(sh.startswith(shlex.join([*design.terminal_title_argv(), branch]) + ' || :; '), sh)

    def test_inside_herdr_the_tab_is_labelled_with_the_slug(self):
        log = os.path.join(self.repo.root, 'herdr.log')
        fake = os.path.join(self.bin_dir, 'fake-herdr')
        write_exe(fake, f'#!/bin/sh\nprintf \'%s\\n\' "$*" >> {shlex.quote(log)}\n')
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report',
                        env={'TERM_PROGRAM': 'herdr', 'HERDR_TAB_ID': 'wW:t9', 'HERDR_BIN_PATH': fake})
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        self.assertEqual(self.read(log), 'tab rename wW:t9 add-weekly-payout-report\n')
        self.assertIn('→ herdr tab: add-weekly-payout-report [ok]', self.steps(r))
        self.again()
        os.remove(log)
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')  # outside herdr
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        self.assertIsNone(self.read(log))
        self.assertNotIn('herdr tab', r.stderr)

    def test_the_origin_is_the_invocation_directory(self):
        origin = os.path.join(self.repo.root, 'where I typed it')
        os.makedirs(origin)
        r = self.design(f'--origin={origin}', 'add a weekly payout report', slugs='add-weekly-payout-report')
        fish = self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')['argv'][2]
        self.assertIn(f'function __omc_herdr_exit --on-event fish_exit; __omc_herdr_report {shlex.quote(origin)}; end',
                      fish)
        self.again()
        r = self.design(f'--origin={origin}', 'add a weekly payout report', slugs='add-weekly-payout-report',
                        env={'SHELL': '/bin/zsh'})
        zshrc = self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n',
                                   shell='zsh')['init']
        self.assertIn(shlex.quote(design.shells.osc7_report(origin)), zshrc)
        self.assertIn('zshexit_functions+=(__omc_herdr_exit)', zshrc)

    def test_the_launch_env_drops_the_uv_venv(self):
        venv = os.path.join(self.repo.root, 'venv')
        os.makedirs(os.path.join(venv, 'bin'))
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report',
                        env={'VIRTUAL_ENV': venv, 'PATH': os.path.join(venv, 'bin') + os.pathsep + self.path})
        env = self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')['env']
        self.assertIsNone(env['VIRTUAL_ENV'])
        self.assertNotIn(os.path.join(venv, 'bin'), env['PATH'].split(os.pathsep))
        self.assertEqual(env['PATH'], self.path)
        self.assertEqual((env['CLAUDE_CODE_DISABLE_TERMINAL_TITLE'], env['OMC_SLUG'], env['OMC_PROVIDER']),
                         ('1', 'add-weekly-payout-report', 'claude'))

    def test_the_slug_call_disables_the_title(self):
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        calls = [json.loads(line) for line in self.read(self.slug_env).splitlines()]
        self.assertEqual(calls, [{'CLAUDE_CODE_DISABLE_TERMINAL_TITLE': '1', 'OMC_SLUG': None, 'OMC_PROVIDER': None}])

    def test_the_notification_channel_is_wired_before_the_exec(self):
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        call = self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        self.assertEqual(json.loads(call['settings']), {'preferredNotifChannel': 'auto'})
        self.assertIn('→ notifications: .claude/settings.local.json [ok]', r.stderr)
        # an invalid settings.local.json in the worktree entered again: a warning, left alone, and the launch goes on
        self.again()
        branch = 'feature/add-weekly-payout-report'
        self.repo.write(os.path.join('.claude', 'settings.local.json'), '{not json\n', cwd=self.tree(branch))
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report')
        call = self.assertStarted(r, branch, 'add a weekly payout report\n')
        self.assertEqual(call['settings'], '{not json\n')
        self.assertIn('· notifications: .claude/settings.local.json is not valid settings JSON — leaving it alone',
                      r.stderr)
        self.assertNotIn('→ notifications:', r.stderr)

    def test_the_fish_integration_is_reconciled_on_macos_only(self):
        hook = os.path.join(self.env['XDG_CONFIG_HOME'], 'fish', 'conf.d', 'omc-title.fish')
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report', platform='linux')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        self.assertFalse(os.path.exists(hook))
        self.assertNotIn('fish title hook', r.stderr)
        self.again()
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report', platform='darwin')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        with open(hook, 'rb') as f:
            self.assertEqual(f.read(), design.fish_integration.installed_hook())
        lines = self.steps(r)
        at = lines.index('→ fish title hook: reconciling [ok]')
        self.assertTrue(lines[at + 1].startswith('→ lock:'), r.stderr)  # before the lock and the worktree
        self.assertTrue(lines[at - 1].startswith('→ slug:'), r.stderr)

    def test_the_fish_opt_out_is_read_from_the_cases_omc_home(self):
        hook = os.path.join(self.env['XDG_CONFIG_HOME'], 'fish', 'conf.d', 'omc-title.fish')
        self.assertTrue(self.env['OMC_HOME'].startswith(self.repo.root), self.env['OMC_HOME'])
        marker = os.path.join(self.env['OMC_HOME'], 'integrations', 'fish-title.disabled')
        os.makedirs(os.path.dirname(marker))
        open(marker, 'w').close()
        r = self.design('add a weekly payout report', slugs='add-weekly-payout-report', platform='darwin')
        self.assertStarted(r, 'feature/add-weekly-payout-report', 'add a weekly payout report\n')
        self.assertIn('→ fish title hook: reconciling [ok]', self.steps(r))
        self.assertFalse(os.path.exists(hook))  # opted out: reconcile installs nothing

    def test_no_argument_is_refused(self):
        self.assertRefused(self.design())
        self.assertIsNone(self.read(self.wt_log))

    def test_no_argument_names_the_briefs_path(self):
        self.assertRefused(self.design(), 'nothing to start: `just design <brief-or-text>`, a brief (tasks/<name>.md)')
        self.repo.set_config('briefs: tasks/', 'briefs: briefs/')
        self.assertRefused(self.design(), 'nothing to start: `just design <brief-or-text>`, a brief (briefs/<name>.md)')

    # ----------------------------------------------------------------------------------------------------- the recipe
    def stubbed_omc_just(self, marker=None):
        """The real omc/omc.just, `_design-start`'s body replaced by a stub writing [marker] (when given), `$PWD` and its
        arguments, one per line, to <tmp>/start.out; fails loudly when the recipe's header is missing."""
        with open(OMC_JUST, encoding='utf-8') as f:
            lines = f.read().splitlines()
        at = next((i for i, line in enumerate(lines) if line.lstrip('@').startswith('_design-start *ARGS:')), None)
        self.assertIsNotNone(at, f'no `_design-start *ARGS:` recipe in {OMC_JUST}')
        end = at + 1
        while end < len(lines) and lines[end].startswith((' ', '\t')):
            end += 1
        words = (shlex.quote(marker) + ' ') if marker else ''
        stub = f'    printf \'%s\\n\' {words}"$PWD" "$@" > {shlex.quote(self.start_out)}'
        return '\n'.join(lines[:at + 1] + [stub] + lines[end:]) + '\n'

    def recipe_setup(self):
        """`just` found (else the case is skipped), a justfile importing the stubbed omc/omc.just committed in the work
        clone and pushed."""
        self.just = shutil.which('just')
        if self.just is None:
            self.skipTest('just is not on PATH')
        self.start_out = os.path.join(self.repo.root, 'start.out')
        self.repo.write('justfile', "import 'omc/omc.just'\n")
        self.repo.write('omc/omc.just', self.stubbed_omc_just())
        self.repo.git('add', '--', 'justfile', 'omc/omc.just')
        self.repo.git('commit', '-q', '-m', 'the justfile')
        self.repo.git('push', '-q', 'origin', 'main')

    def run_just(self, cwd, *args):
        """`just design <args>` in [cwd]: the machine's PATH (the case's fake shells would stand in for the recipe's
        bash), the case's git environment."""
        env = {**self.env, 'PATH': os.environ['PATH']}
        return subprocess.run((self.just, 'design', *args), cwd=cwd, env=env, capture_output=True, text=True,
                              timeout=60)

    def started(self):
        """The stub's lines: [marker,] cwd, arguments; None when it did not run."""
        out = self.read(self.start_out)
        return None if out is None else out.splitlines()

    def side_tree(self):
        tree = os.path.join(self.trees, 'side')
        self.repo.git('worktree', 'add', '-q', '-b', 'side', tree)
        return tree

    def test_the_recipe_runs_the_pulled_justfile(self):
        self.recipe_setup()
        sha = self.repo.advance_origin('omc/omc.just', self.stubbed_omc_just('pulled'))
        r = self.run_just(self.repo.work, 'add', 'a', 'weekly', 'payout', 'report')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.repo.git('rev-parse', 'HEAD').strip(), sha)
        self.assertEqual(self.started(), ['pulled', self.repo.work, f'--origin={self.repo.work}',
                                          'add', 'a', 'weekly', 'payout', 'report'])
        listed = subprocess.run((self.just, '--list'), cwd=self.repo.work, capture_output=True, text=True)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        names = [line.split()[0] for line in listed.stdout.splitlines()[1:] if line.strip()]
        self.assertIn('design', names)
        self.assertNotIn('_design-start', names)  # private

    def test_the_recipe_is_quiet(self):
        self.recipe_setup()
        r = self.run_just(self.repo.work, 'add a weekly payout report')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('#!/usr/bin/env bash', r.stderr)  # the script's body is never echoed
        self.assertNotIn('common=$(git', r.stderr + r.stdout)

    def test_the_recipe_from_a_worktree_pulls_and_runs_the_primary(self):
        self.recipe_setup()
        tree = self.side_tree()
        sha = self.repo.advance_origin('omc/omc.just', self.stubbed_omc_just('pulled'))
        r = self.run_just(tree, 'add a weekly payout report')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.repo.git('rev-parse', 'HEAD').strip(), sha)
        self.assertNotEqual(self.repo.git('rev-parse', 'HEAD', cwd=tree).strip(), sha)
        self.assertEqual(self.started(), ['pulled', self.repo.work, f'--origin={tree}', 'add a weekly payout report'])

    def test_the_recipe_makes_a_relative_brief_absolute(self):
        self.recipe_setup()
        tree = self.side_tree()
        self.repo.write('tasks/x.md', '# x\n', cwd=tree)
        r = self.run_just(tree, 'tasks/x.md')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.started(), [self.repo.work, f'--origin={tree}', os.path.join(tree, 'tasks', 'x.md')])

    def test_the_recipe_does_not_pull_a_primary_off_base(self):
        self.recipe_setup()
        self.repo.git('switch', '-q', '-c', 'parked')
        head = self.repo.git('rev-parse', 'HEAD').strip()
        self.repo.advance_origin('notes/pulled.txt', 'pulled\n')
        r = self.run_just(self.repo.work, 'add a weekly payout report')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.repo.git('rev-parse', 'HEAD').strip(), head)
        self.assertEqual(self.started(), [self.repo.work, f'--origin={self.repo.work}', 'add a weekly payout report'])

    def test_the_recipe_does_not_pull_a_dirty_primary(self):
        self.recipe_setup()
        head = self.repo.git('rev-parse', 'HEAD').strip()
        self.repo.advance_origin('notes/pulled.txt', 'pulled\n')
        self.repo.write('.gitignore', '.cache/\nbuild/\n')
        r = self.run_just(self.repo.work, 'add a weekly payout report')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.repo.git('rev-parse', 'HEAD').strip(), head)
        self.assertEqual(self.started(), [self.repo.work, f'--origin={self.repo.work}', 'add a weekly payout report'])



DEFERRED_LOG = """# Design decision log

*Scratch space. Next: 58*

### 41 Incidents need a photo

**Context.** Incidents are reported without proof.
**Decision.** Every incident carries a photo.
**Automated.** false
**Status.** recorded 2026-11-12 · deferred 2026-11-13

### 42 The header shows the call

**Context.** The owner asked.
**Decision.** The call sits under the picture.
**Automated.** false
**Status.** recorded 2026-11-12

### 43 Reports list the totals

**Context.** The totals are hidden.
**Decision.** A report lists its totals.
**Automated.** false
**Status.** recorded 2026-11-12 · deferred 2026-11-13

### 57 Applied after its deferral

**Context.** Old.
**Decision.** Done.
**Automated.** false
**Status.** recorded 2026-11-12 · deferred 2026-11-13 · applied 2026-11-14
"""
DEFERRED_BRIEF = """# Deferred rulings 41, 43

## 41. Incidents need a photo

**Context.** Incidents are reported without proof.
**Decision.** Every incident carries a photo.

## 43. Reports list the totals

**Context.** The totals are hidden.
**Decision.** A report lists its totals.
"""


class Deferred(DesignCase):
    """`just design --deferred <ids>`: the deferred entries of origin/main's log as the brief."""

    def setUp(self):
        super().setUp()
        self.repo.commit('docs/decision-log.md', DEFERRED_LOG, 'the log')  # the fixture's paths.decision_log
        self.repo.git('push', '-q', 'origin', 'main')

    def test_writes_brief_and_launches(self):
        r = self.design('--deferred', '41,43', slugs='incident-photos-and-report-totals')
        self.assertStarted(r, 'feature/incident-photos-and-report-totals', DEFERRED_BRIEF)
        prompts = [json.loads(line) for line in self.read(self.prompts).splitlines()]
        self.assertEqual(len(prompts), 1)
        self.assertTrue(prompts[0].endswith('The work: ' + DEFERRED_BRIEF.strip()), prompts[0])
        self.again()
        r = self.design(f'--origin={self.repo.work}', '--deferred=43', slugs='payout-lists-its-fees')
        self.assertStarted(r, 'feature/payout-lists-its-fees', DEFERRED_BRIEF.split('## 41')[0].replace('41, 43', '43')
                           + '## 43' + DEFERRED_BRIEF.split('## 43')[1])

    def test_refuses_unknown_or_not_deferred(self):
        for args, why in ((('--deferred', '99'), 'decision 99 is not in'),
                          (('--deferred', '41,42'), 'decision 42 is not deferred'),
                          (('--deferred', '57'), 'decision 57 is not deferred'),
                          (('--deferred', 'x'), '--deferred takes'),
                          (('--deferred',), '--deferred takes'),
                          (('--deferred', '41', 'more'), '--deferred takes')):
            r = self.design(*args, slugs='never-asked-for-this')
            self.assertRefused(r, why)
        self.assertIsNone(self.read(self.prompts))
        self.assertIsNone(self.read(self.wt_log))
        self.assertIsNone(self.read(self.shell_log))


if __name__ == '__main__':
    unittest.main()
