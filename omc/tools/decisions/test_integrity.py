# omc/tools/decisions/test_integrity.py
"""Tests of omc/tools/decisions/integrity.py. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/decisions/test_integrity.py
Every check takes texts: the tests pass the logs, the changes, the records and the links' lines in, no git, but for
GitRepoTest."""
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
import decisions  # noqa: E402
import integrity  # noqa: E402
from decision_log_fixtures import FIXTURE, LOG_HEAD, T05, APPLIED, RECORDED, DEFERRED, write_vault, entry, log_text, parse  # noqa: E402

OMC_JUST = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'omc.just')  # the real recipes
RECORD_PATH = 'superpowers/specs/2026-01-06-x-design.md'


def record(n):
    """A record whose section holds the row of entry n."""
    return ('# R\n\n## Decisions and the pages they change\n\n'
            '| Decision | Planned pages and rules | Subthemes expected to go stale | What it means for the code |\n'
            '|---|---|---|---|\n'
            f'| `decision {n}`: Incidents need a photo | R5.2.1-1 | T5.2.1 | none |\n')


RECORD = record(1)
EDITED = T05.replace('without signal', 'without a signal')


def run(phase, log, changes={}, main_log=None, records={}, links=[], files=None, defer_questions=False):
    with tempfile.TemporaryDirectory() as tmp:
        vault = decisions.Vault(write_vault(tmp))
        return integrity.integrity(phase, vault, log, parse(1), main_log or parse(1), changes, (),
                                   files if files is not None else {}, records, links, defer_questions=defer_questions)


class IntegrityTest(unittest.TestCase):
    def test_a_clean_branch_is_ok_in_both_phases(self):
        log = parse(2, entry(1, APPLIED, 'R5.2.1-1'))
        for p in integrity.PHASES:
            self.assertEqual(run(p, log, {'design/T05-the-shift.md': (T05, EDITED)}, records={RECORD_PATH: RECORD}), [], p)

    def test_a_recorded_entry_is_a_problem_in_implementation_only(self):
        log = parse(2, entry(1, RECORDED, 'R5.2.1-1'))
        self.assertEqual(run('design', log, records={RECORD_PATH: RECORD}), [])
        self.assertEqual(run('implementation', log, records={RECORD_PATH: RECORD}),
                         [f'PROBLEM: pending: PENDING: decision {1} recorded, not applied: Incidents need a photo'])

    def test_deferred_entry_passes_implementation(self):
        # a ruling deferred to main backs no page and waits for a later branch: the push gate lets it through
        log = parse(2, entry(1, DEFERRED, 'R5.2.1-1'))
        for p in integrity.PHASES:
            self.assertEqual(run(p, log, records={RECORD_PATH: RECORD}), [], p)
        out = run('implementation', log, {'design/T05-the-shift.md': (T05, EDITED)}, records={RECORD_PATH: RECORD})
        self.assertEqual([l.split(': ')[1] for l in out], ['guard'])  # a deferred entry backs no page

    def test_a_guarded_page_changed_without_an_applied_entry_is_a_problem_in_both(self):
        for p in integrity.PHASES:
            out = run(p, parse(1), {'design/T05-the-shift.md': (T05, EDITED)})
            self.assertEqual(len(out), 1, out)
            self.assertTrue(out[0].startswith('PROBLEM: guard: UNBACKED: docs/design/T05-the-shift.md:'), out[0])

    def test_an_open_question_waits_for_the_push_gate(self):
        files = {'reviews/2026-11-12-x-1.md': FIXTURE['reviews/2026-11-12-x-1.md']}
        self.assertEqual(run('implementation', parse(1), files=files),   # the pre-push hook's and /audit's push's case
                         ['PROBLEM: questions: PENDING: docs/reviews/2026-11-12-x-1.md:3: Q1 A question is open'])
        self.assertEqual(run('design', parse(1), files=files), [])
        self.assertEqual(run('implementation', parse(1), files=files, defer_questions=True), [])
        self.assertEqual(run('design', parse(1), files=files, defer_questions=True), [])

    def test_a_disagreed_entry_is_a_problem_at_the_push_gate_only(self):
        log = parse(2, entry(1, APPLIED, 'R5.2.1-1', automated='disagreed'))
        line = 'PROBLEM: disagreed: PENDING: decision 1 disagreed, not ruled: Incidents need a photo'
        self.assertEqual(run('implementation', log, records={RECORD_PATH: RECORD}), [line])   # /audit's push, pre-push
        self.assertEqual(run('implementation', log, records={RECORD_PATH: RECORD}, defer_questions=True), [])  # /implement, verify
        self.assertEqual(run('design', log, records={RECORD_PATH: RECORD}), [])

    def test_a_confirmed_or_overruled_entry_is_no_problem(self):
        for value in ('false', 'overruled by 2'):
            log = parse(3, entry(1, APPLIED, 'R5.2.1-1', automated=value), entry(2, APPLIED, 'R5.2.1-1', title='Two'))
            self.assertEqual(run('implementation', log, records={RECORD_PATH: RECORD + record(2).split('|---|---|---|---|\n')[1]}), [], value)

    def test_an_entry_without_its_row_is_a_problem(self):
        out = run('design', parse(2, entry(1, APPLIED, 'R5.2.1-1')), records={RECORD_PATH: '# R\n'})
        self.assertEqual(out, [f'PROBLEM: record: decision {1} Incidents need a photo has no row in the record\'s "Decisions '
                               f'and the pages they change" ({RECORD_PATH}): /review-decisions appends it; before '
                               'implementation /design\'s harden writes it'])

    def test_a_branch_without_a_record_passes_the_record_check(self):
        out = run('design', parse(2, entry(1, APPLIED, 'R5.2.1-1')), records={})
        self.assertEqual([l for l in out if l.startswith('PROBLEM: record:')], [])

    def test_a_row_follows_a_renumbered_entry(self):
        n = 3
        log = parse(n + 1, entry(n, APPLIED, 'R5.2.1-1'))
        self.assertEqual(run('design', log, records={RECORD_PATH: record(n)}), [])
        out = [l for l in run('design', log, records={RECORD_PATH: record(n - 1)}) if l.startswith('PROBLEM: record:')]
        self.assertEqual(len(out), 1, out)
        self.assertTrue(out[0].startswith(f'PROBLEM: record: decision {n} Incidents need a photo has no row'), out[0])

    def test_an_entry_of_main_needs_no_row(self):
        main = parse(2, entry(1, APPLIED, 'R5.2.1-1'))
        log = parse(2, entry(1, APPLIED, 'R5.2.1-1'))  # main's entry, before a trim
        self.assertEqual(run('design', log, main_log=main, records={RECORD_PATH: '# R\n'}), [])
        self.assertEqual(len(run('design', log, records={RECORD_PATH: '# R\n'})), 1)  # the same entry, the branch's

    def test_only_the_first_cell_of_the_section_s_rows_counts(self):
        text = ('# R\n\n## Decisions and the pages they change\n\n'
                '| Decision | Planned pages and rules | Subthemes expected to go stale | What it means for the code |\n'
                '|---|---|---|---|\n'
                '| `decision 4`: Incidents need a photo | R5.2.1-1 | T5.2.1 | replaces decision 5 |\n\n'
                '```\n| `decision 6`: The record\'s example | R5.2.1-1 | T5.2.1 | none |\n```\n\n'
                '## Other\n\n| decision 7: Not the section | R5.2.1-1 | T5.2.1 | none |\n')
        self.assertEqual(integrity.record_rows(text), {4})

    def test_an_unknown_phase_is_refused(self):
        with self.assertRaises(ValueError):
            run('implementaton', parse(1))

    def test_the_log_s_own_problems_and_the_links_are_named(self):
        log = decisions.parse_log(LOG_HEAD.replace(' Next: 1', ''))
        self.assertEqual(run('design', log, links=['design/x.md:3: dead-link: y']),
                         ['PROBLEM: decisions check: reviews/design-decision-log.md:1: header: the header holds no "Next: <n>"',
                          'PROBLEM: links-check: design/x.md:3: dead-link: y'])

    def test_links_check_that_cannot_run_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = integrity.links_check(tmp)
        self.assertEqual(len(out), 1, out)
        self.assertTrue(out[0].startswith('did not run:'), out[0])

    def test_links_check_runs_dart_in_the_shipped_tool(self):
        done = subprocess.CompletedProcess([], 0, 'OK\n', '')
        with mock.patch.object(integrity.subprocess, 'run', return_value=done) as run_:
            self.assertEqual(integrity.links_check('/repo'), [])
        self.assertEqual(run_.call_args.args[0], ['dart', 'run', 'bin/links_check.dart'])
        self.assertEqual(run_.call_args.kwargs['cwd'], '/repo/omc/skills/reconcile-links/tool')

    def test_a_links_check_that_did_not_run_is_named_once(self):
        self.assertEqual(run('design', parse(1), links=['did not run: exit 255: boom']),
                         ['PROBLEM: links-check: did not run: exit 255: boom'])
        with tempfile.TemporaryDirectory() as tmp:
            did_not_run = integrity.links_check(tmp)  # the real line: the tool's folder missing
        self.assertEqual(run('design', parse(1), links=did_not_run), [f'PROBLEM: links-check: {did_not_run[0]}'])

    # ------------------------------------------------------------------------- the project's hook, omc/bin/links-check
    def hook_repo(self, hook=None):
        """A folder holding the links tool's folder, a stub `dart` (exit 0, prints OK) first on the PATH, and, with
        [hook] (a shell body), an executable `omc/bin/links-check`; the folder."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = tmp.name
        os.makedirs(os.path.join(root, integrity.LINKS_TOOL))
        stubs = os.path.join(root, 'stubs')
        os.makedirs(stubs)
        with open(os.path.join(stubs, 'dart'), 'w', encoding='utf-8') as f:
            f.write('#!/bin/sh\necho OK\n')
        os.chmod(os.path.join(stubs, 'dart'), 0o755)
        env = mock.patch.dict(os.environ, {'PATH': stubs + os.pathsep + os.environ.get('PATH', '')})
        env.start()
        self.addCleanup(env.stop)
        if hook is not None:
            path = os.path.join(root, integrity.LINKS_HOOK)
            os.makedirs(os.path.dirname(path))
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f'#!/bin/sh\n{hook}\n')
            os.chmod(path, 0o755)
        return root

    def just_links_check(self, root):
        """`just links-check` in [root], its justfile importing the real omc/omc.just; skipped without `just`."""
        just = shutil.which('just')
        if just is None:
            self.skipTest('no just on the PATH')
        os.makedirs(os.path.join(root, 'omc'), exist_ok=True)
        shutil.copy(OMC_JUST, os.path.join(root, 'omc', 'omc.just'))
        with open(os.path.join(root, 'justfile'), 'w', encoding='utf-8') as f:
            f.write("import 'omc/omc.just'\n")
        return subprocess.run((just, 'links-check'), cwd=root, capture_output=True, text=True)

    def test_integrity_links_step_runs_hook(self):
        root = self.hook_repo('echo "PROBLEM: design/x.md:3: e2e-link: gone"; exit 1')
        self.assertEqual(integrity.links_check(root), ['design/x.md:3: e2e-link: gone'])
        root = self.hook_repo('echo boom; exit 4')
        self.assertEqual(integrity.links_check(root), ['omc/bin/links-check did not run: exit 4: boom'])
        self.assertEqual(run('design', parse(1), links=integrity.links_check(root)),
                         ['PROBLEM: links-check: omc/bin/links-check did not run: exit 4: boom'])

    def test_links_check_runs_project_hook(self):
        r = self.just_links_check(self.hook_repo('echo hook ran; exit 1'))
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout, 'OK\nhook ran\n')
        r = self.just_links_check(self.hook_repo('echo hook ran'))
        self.assertEqual((r.returncode, r.stdout), (0, 'OK\nhook ran\n'), r.stderr)

    def test_no_hook_dormant(self):
        root = self.hook_repo()
        self.assertEqual(integrity.links_check(root), [])
        r = self.just_links_check(root)
        self.assertEqual((r.returncode, r.stdout), (0, 'OK\n'), r.stderr)

    def test_links_lines_takes_the_problem_lines_of_exit_1_only(self):
        self.assertEqual(integrity.links_lines(0, '0 subthemes not derived yet\nOK\n', ''), [])
        self.assertEqual(integrity.links_lines(1, 'PROBLEM: design/x.md:3: dead-link: y\n0 subthemes not derived yet\n'
                                                  '1 problems\n', ''),
                         ['design/x.md:3: dead-link: y'])
        self.assertEqual(integrity.links_lines(1, '', 'Could not find package\n'),
                         ['did not run: exit 1: Could not find package'])
        self.assertEqual(integrity.links_lines(255, 'PROBLEM: design/x.md:3: dead-link: y\n', ''),
                         ['did not run: exit 255: PROBLEM: design/x.md:3: dead-link: y'])


class GitRepoTest(unittest.TestCase):
    """The command over a small repository whose origin/main is its first commit, as test_decisions.GitInputsTest."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        answered = FIXTURE['reviews/2026-11-12-x-1.md'].replace('**Status.** open', '**Status.** answered')
        self.docs = write_vault(self.root, {**FIXTURE, 'reviews/2026-11-12-x-1.md': answered})
        self.git('init', '-q', '-b', 'main')
        self.commit('main')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', self.root, '-c', 'user.email=t@t', '-c', 'user.name=t', '-c', 'core.hooksPath=/dev/null',
                               '-c', 'commit.gpgsign=false', *args], check=True, capture_output=True, text=True).stdout

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', message)

    def put(self, rel, text):
        path = os.path.join(self.docs, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)

    def read(self, rel):
        with open(os.path.join(self.docs, rel), encoding='utf-8') as f:
            return f.read()

    def test_the_command_over_a_repository(self):
        self.put(decisions.LOG, log_text(2, entry(1, RECORDED, 'R5.2.1-1')))
        self.put(RECORD_PATH, RECORD)
        for phase, code, printed in (('design', 0, 'OK\n'),
                                     ('implementation', 1, f'PROBLEM: pending: PENDING: decision {1} recorded, not applied: '
                                                           'Incidents need a photo\n1 problems\n')):
            out = io.StringIO()
            with mock.patch.object(integrity, 'links_check', return_value=[]), contextlib.redirect_stdout(out):
                self.assertEqual(integrity.main(['--docs', self.docs, '--phase', phase]), code, out.getvalue())
            self.assertEqual(out.getvalue(), printed)

    def test_the_command_defers_an_open_question_with_its_flag_or_in_design(self):
        self.put('reviews/2026-11-12-x-1.md', FIXTURE['reviews/2026-11-12-x-1.md'])
        for args, code, printed in (([], 1, 'PROBLEM: questions: PENDING: docs/reviews/2026-11-12-x-1.md:3: Q1 A question '
                                            'is open\n1 problems\n'),
                                    (['--defer-questions'], 0, 'OK\n'),
                                    (['--phase', 'design'], 0, 'OK\n'),
                                    (['--phase', 'design', '--defer-questions'], 0, 'OK\n')):
            out = io.StringIO()
            with mock.patch.object(integrity, 'links_check', return_value=[]), contextlib.redirect_stdout(out):
                self.assertEqual(integrity.main(['--docs', self.docs, *args]), code, (args, out.getvalue()))
            self.assertEqual(out.getvalue(), printed, args)

    def test_the_command_prints_a_links_check_that_did_not_run_once(self):
        out = io.StringIO()
        with mock.patch.object(integrity, 'links_check', return_value=['did not run: exit 255: boom']), \
                contextlib.redirect_stdout(out):
            self.assertEqual(integrity.main(['--docs', self.docs, '--phase', 'design']), 1, out.getvalue())
        self.assertEqual(out.getvalue(), 'PROBLEM: links-check: did not run: exit 255: boom\n1 problems\n')

    def test_branch_records_are_the_added_design_records(self):
        self.put('superpowers/specs/2026-01-01-old-design.md', '# Old\n')
        self.commit('main holds a record')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.put('superpowers/specs/2026-01-01-old-design.md', '# Old, edited on the branch\n')
        self.put('superpowers/specs/2026-01-06-new-design.md', '# New\n')
        self.put('superpowers/specs/2026-01-06-new-plan.md', '# Plan\n')
        self.commit('the branch adds its record and its plan')
        self.put('superpowers/specs/2026-01-06-u-design.md', '# Untracked\n')
        merge_base = self.git('rev-parse', 'origin/main').strip()
        self.assertEqual(integrity.branch_records(self.root, 'docs', merge_base),
                         ['superpowers/specs/2026-01-06-new-design.md', 'superpowers/specs/2026-01-06-u-design.md'])

    def test_a_row_survives_renumber(self):
        one, a2 = entry(1, APPLIED, title='One', context='One.'), entry(2, APPLIED, title='Stock is counted twice', context='A.')
        b2 = entry(2, RECORDED, title='Incidents need a photo', context='B.')
        self.put(decisions.LOG, log_text(3, one, a2))
        self.commit('main, after branch A merged')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.put(decisions.LOG, log_text(3, one, a2, b2))  # the conflict resolved: main's, then B's
        self.put(RECORD_PATH, record(2))
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'decisions.py'), '--docs', self.docs, 'renumber'],
                           capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, 'decision 2 is now 3\n1 entries renumbered\n'), r.stderr)
        self.assertEqual(integrity.record_rows(self.read(RECORD_PATH)), {3})

    def test_no_origin_main_is_an_error(self):
        self.git('update-ref', '-d', 'refs/remotes/origin/main')
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'integrity.py'), '--docs', self.docs],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('error: no origin/main: git fetch origin', r.stderr)


class NoRepositoryTest(unittest.TestCase):
    def test_no_repository_and_no_docs_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            # no GIT_ variable of the caller; git looks for a repository no higher than tmp
            env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
            env['GIT_CEILING_DIRECTORIES'] = os.path.dirname(os.path.realpath(tmp))
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'integrity.py')], cwd=tmp, env=env,
                               capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (2, ''), r.stderr)
        self.assertTrue(r.stderr.startswith('error: ') and r.stderr.endswith(' is in no git repository\n'), r.stderr)


class DormantTest(unittest.TestCase):
    def test_integrity_dormant(self):
        """A repository with no log and `protected: []` (omc_fixtures.Repo): nothing to check, exit 0, silent."""
        import omc_fixtures  # decision_log_fixtures put omc/tools on the path
        repo = omc_fixtures.Repo.make_repo()
        try:
            for gone in (False, True):  # with origin/main, then without
                if gone:
                    repo.git('update-ref', '-d', 'refs/remotes/origin/main')
                r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'integrity.py')], cwd=repo.work,
                                   env=repo.env, capture_output=True, text=True)
                self.assertEqual((r.returncode, r.stdout, r.stderr), (0, '', ''), gone)
        finally:
            repo.cleanup()

    def test_integrity_idle_with_no_log_configured(self):
        """No paths.decision_log: idle, unless paths.protected names pages, which need a log: then refused."""
        import omc_fixtures
        import config
        from decision_log_fixtures import config_text
        repo = omc_fixtures.Repo.make_repo()
        try:
            for paths, want in (({}, (0, '', '')),
                                ({'protected': ('docs/design/**/*.md',)},
                                 (2, '', 'error: paths.protected is set but no decision log is configured '
                                         '(paths.decision_log)\n'))):
                repo.commit('omc/config.yaml', config_text(config.Paths(**paths)), 'config')
                r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'integrity.py')], cwd=repo.work,
                                   env=repo.env, capture_output=True, text=True)
                self.assertEqual((r.returncode, r.stdout, r.stderr), want, paths)
        finally:
            repo.cleanup()


if __name__ == '__main__':
    unittest.main()
