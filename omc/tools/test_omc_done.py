"""Tests of omc/tools/done.py, `just omc gate passed | skip`, `reviewed [--record]` and `settled [--record]`: the
records of "Is it done"
and the comparison that says whether one holds for the tree of now. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_done.py
Each case gets its own temporary repository from omc_fixtures' `Repo` (a bare origin.git and a work clone on
main, the caller's GIT_ variables removed and a private GIT_CONFIG_GLOBAL); the verbs run through `omc.main` in this
process under that environment, and CliTest runs the entry as a subprocess. A gate's command is a stub
`omc/bin/<gate>` shell script, committed; a pass is the record `just omc gate run` writes, or one written here in its
form (`write_pass`). The gates' slots live in a temporary registry (`OMC_GATE_REGISTRY`), their poll shortened."""
import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import concurrency  # noqa: E402
import config  # noqa: E402
import done  # noqa: E402
import omc  # noqa: E402
from omc_fixtures import TOOL, Repo  # noqa: E402

CODE = 'src/a.txt'
SHOT = 'docs/screens/shots/en/x.png'
BASELINE = 'test/e2e/baseline/x.json'


def short(repo, ref='HEAD'):
    return repo.git('rev-parse', '--short=8', ref).strip()


def write_pass(root, head, gate='check', at=None):
    """A pass record `.cache/omc/passes/<gate>/<head>.json`, as `just omc gate run` writes it."""
    path = os.path.join(root, '.cache', 'omc', 'passes', gate, f'{head}.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'gate': gate, 'head': head, 'at': at or time.strftime('%Y-%m-%dT%H:%M:%S')}, f)
    return path


def write_bin(repo, gate='check', body='exit 0', mode=0o755):
    """Commits `omc/bin/<gate>`, a shell script of [body], with [mode]."""
    path = os.path.join('omc', 'bin', gate)
    repo.write(path, f'#!/bin/sh\n{body}\n')
    os.chmod(os.path.join(repo.work, path), mode)
    return repo.commit(path, f'#!/bin/sh\n{body}\n', f'bin: {gate}')


def process_gone(pid, proc='/proc'):
    """Whether [pid] has ended: from `<proc>/<pid>/stat` where [proc] exists (a zombie counts as gone), else by
    `os.kill(pid, 0)` (macOS has no /proc)."""
    if os.path.isdir(proc):
        try:
            with open(os.path.join(proc, str(pid), 'stat'), encoding='utf-8') as f:
                return f.read().split(') ')[-1].startswith('Z')
        except FileNotFoundError:
            return True
        except OSError:
            pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


class DoneTest(unittest.TestCase):
    """The verbs through `omc.main`, in this process (a Python start per call would put the file far over its time),
    in the work clone and under the fixture's environment; CliTest runs the entry itself."""

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        self.repo.git('checkout', '-q', '-b', 'feature/x')
        self.repo.commit(CODE, 'a\n', 'code')
        registry = tempfile.TemporaryDirectory()
        self.addCleanup(registry.cleanup)
        self.registry = registry.name
        env = mock.patch.dict(os.environ, {**self.repo.env, concurrency.REGISTRY_ENV: self.registry}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        poll = mock.patch.object(concurrency, 'POLL', 0.05)
        poll.start()
        self.addCleanup(poll.stop)

    def omc(self, *args):
        """`just omc <args>` in the work clone: (exit code, stdout, stderr) as a CompletedProcess."""
        out, err, here = io.StringIO(), io.StringIO(), os.getcwd()
        os.chdir(self.repo.work)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = omc.main(list(args))
        finally:
            os.chdir(here)
        return subprocess.CompletedProcess(args, code, out.getvalue(), err.getvalue())

    def ok(self, *args):
        """`just omc <args>`, which exits 0 and prints nothing."""
        r = self.omc(*args)
        self.assertEqual((r.returncode, r.stdout), (0, ''), r.stderr)

    def answer(self, code, *args):
        """The one line of `just omc <args>`, which exited [code]."""
        r = self.omc(*args)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count('\n'), 1, r.stdout)
        return r.stdout.strip()

    def assertRefused(self, *args):
        r = self.omc(*args)
        self.assertEqual((r.returncode, r.stdout), (2, ''), r.stderr)
        self.assertTrue(r.stderr.startswith('error: '), r.stderr)
        return r.stderr

    def pass_here(self, head=None, **kw):
        return write_pass(self.repo.work, head or self.repo.git('rev-parse', 'HEAD').strip(), **kw)

    def run_gate(self, gate='check', *args):
        """`just omc gate run <gate> <args>`: the CompletedProcess."""
        return self.omc('gate', 'run', gate, *args)

    def add_config(self, text):
        """Appends [text] to the work clone's omc/config.yaml, committed."""
        path = os.path.join(self.repo.work, 'omc', 'config.yaml')
        with open(path, encoding='utf-8') as f:
            old = f.read()
        self.repo.commit(os.path.join('omc', 'config.yaml'), old + text, 'config')

    def hold_slot(self, gate, seconds):
        """Another checkout holds [gate]'s one slot for [seconds], from a thread; the thread."""
        other = os.path.join(self.registry, 'other-checkout')
        os.makedirs(other, exist_ok=True)
        taken = threading.Event()

        def hold():
            with concurrency.slot(other, gate, 1, lambda line: None):
                taken.set()
                time.sleep(seconds)
        t = threading.Thread(target=hold, daemon=True)
        t.start()
        self.addCleanup(t.join, 30)
        self.assertTrue(taken.wait(5))
        return t

    def gate_log(self, gate='check'):
        with open(os.path.join(self.repo.work, '.cache', 'omc', 'gates', f'{gate}.log'), encoding='utf-8') as f:
            return f.read()

    def passes(self):
        return sorted(os.path.relpath(os.path.join(d, f), self.repo.work)
                      for d, _, fs in os.walk(os.path.join(self.repo.work, '.cache', 'omc', 'passes')) for f in fs)

    def passed(self, gate='check'):
        return self.answer(0, 'gate', 'passed', gate)

    def not_passed(self, gate='check'):
        line = self.answer(1, 'gate', 'passed', gate)
        self.assertTrue(line.startswith('not passed: '), line)
        return line

    # ------------------------------------------------------------------------------------------------- gate run
    def test_run_missing_bin_refused(self):
        self.assertIn('omc/bin/check', self.assertRefused('gate', 'run', 'check'))
        write_bin(self.repo, 'check', mode=0o644)
        self.assertIn('not executable', self.assertRefused('gate', 'run', 'check'))
        self.assertEqual(self.passes(), [])

    def test_run_records_pass_on_clean_tree(self):
        write_bin(self.repo, 'check', 'echo out; echo err >&2; pwd')
        sha = self.repo.git('rev-parse', 'HEAD').strip()
        r = self.run_gate('check')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, f'out\nerr\n{self.repo.work}\n')
        with open(os.path.join(self.repo.work, '.cache', 'omc', 'gates', 'check.log'), encoding='utf-8') as f:
            self.assertEqual(f.read(), r.stdout)
        self.assertEqual(self.passes(), [f'.cache/omc/passes/check/{sha}.json'])
        with open(os.path.join(self.repo.work, self.passes()[0]), encoding='utf-8') as f:
            rec = json.load(f)
        self.assertEqual((sorted(rec), rec['gate'], rec['head']), (['at', 'gate', 'head'], 'check', sha))
        self.assertEqual(self.passed(), f'passed: run at {sha[:8]}')
        self.not_passed('verify')

    def test_run_with_args_passes_them_and_records_nothing(self):
        write_bin(self.repo, 'check', 'echo "$@"')
        r = self.run_gate('check', 'a', '-v', '--only', 'x')
        self.assertEqual((r.returncode, r.stdout), (0, 'a -v --only x\n'), r.stderr)
        self.assertEqual(self.passes(), [])  # a partial run is not a pass
        self.assertEqual(self.not_passed(), 'not passed: no passed run started on a clean tree')

    def test_run_truncates_its_log(self):
        write_bin(self.repo, 'check', 'echo "$1"')
        self.run_gate('check', 'first')
        self.run_gate('check', 'second')
        with open(os.path.join(self.repo.work, '.cache', 'omc', 'gates', 'check.log'), encoding='utf-8') as f:
            self.assertEqual(f.read(), 'second\n')

    def test_run_dirty_start_records_nothing(self):
        write_bin(self.repo, 'check', 'rm -f src/new.txt')
        self.repo.write('src/new.txt', 'new\n')
        self.assertEqual(self.run_gate().returncode, 0)
        self.assertEqual(self.passes(), [])
        self.assertEqual(self.not_passed(), 'not passed: no passed run started on a clean tree')

    def test_run_failure_passes_code(self):
        write_bin(self.repo, 'check', 'echo red; exit 3')
        r = self.run_gate()
        self.assertEqual((r.returncode, r.stdout), (3, 'red\n'))
        self.assertEqual(self.passes(), [])
        self.not_passed()

    # ------------------------------------------------------------------------- gate run: slots and silence
    def test_gate_run_waits_for_slot(self):
        write_bin(self.repo, 'check', 'echo ran')
        self.hold_slot('check', 0.5)
        r = self.run_gate()
        self.assertEqual(r.returncode, 0, r.stderr)
        log = self.gate_log()
        self.assertRegex(log, r'^max concurrency of check reached \(1 of 1 running: .*other-checkout\); waiting\nran\n$')
        self.assertEqual(r.stdout, log)
        self.assertEqual(len(self.passes()), 1)

    def test_silence_kills_process_group(self):
        self.add_config('silence:\n  check: 2\n')
        write_bin(self.repo, 'check', 'echo start; sleep 600 & echo $! > .cache/child.pid; sleep 600')
        start = time.monotonic()
        r = self.run_gate()
        self.assertLess(time.monotonic() - start, 15)
        self.assertEqual(r.returncode, 124, r.stdout)
        self.assertTrue(self.gate_log().endswith('no output for 2 s: killed\n'), self.gate_log())
        self.assertTrue(r.stdout.endswith('no output for 2 s: killed\n'), r.stdout)
        with open(os.path.join(self.repo.work, '.cache', 'child.pid'), encoding='utf-8') as f:
            pid = int(f.read())
        self.assertProcessGone(pid)
        self.assertEqual(self.passes(), [])

    def test_a_run_deaf_to_sigterm_is_killed(self):
        self.add_config('silence:\n  check: 1\n')
        write_bin(self.repo, 'check', "trap '' TERM; sleep 600 & echo $! > .cache/child.pid; wait")
        with mock.patch.object(done, 'GRACE', 0.5):
            r = self.run_gate()
        self.assertEqual(r.returncode, 124, r.stdout)
        with open(os.path.join(self.repo.work, '.cache', 'child.pid'), encoding='utf-8') as f:
            self.assertProcessGone(int(f.read()))

    def test_no_silence_no_kill(self):
        write_bin(self.repo, 'check', 'sleep 3; echo done')
        r = self.run_gate()
        self.assertEqual((r.returncode, r.stdout), (0, 'done\n'), r.stderr)

    def test_wait_not_counted(self):
        self.add_config('silence:\n  check: 2\n')
        write_bin(self.repo, 'check', 'echo at once')
        self.hold_slot('check', 4)
        r = self.run_gate()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(r.stdout.endswith('at once\n'), r.stdout)

    def test_a_bad_limit_is_refused(self):
        write_bin(self.repo, 'check')
        self.add_config('concurrency:\n  check: 0\n')
        self.assertIn('concurrency', self.assertRefused('gate', 'run', 'check'))

    def test_a_stop_of_gate_run_ends_its_command(self):
        """SIGTERM or SIGHUP to `gate run` (the terminal stopping its background task) ends the command's own session
        too, and the run exits 128 + the signal."""
        write_bin(self.repo, 'check', 'echo start; sleep 600 & echo $! > .cache/child.pid; sleep 600')
        pid_file = os.path.join(self.repo.work, '.cache', 'child.pid')
        for sig in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(sig=sig.name):
                if os.path.exists(pid_file):
                    os.remove(pid_file)
                proc = subprocess.Popen((sys.executable, '-I', TOOL, 'gate', 'run', 'check'), cwd=self.repo.work,
                                        env=dict(os.environ), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                self.addCleanup(proc.stdout.close)
                deadline = time.monotonic() + 10
                while not os.path.exists(pid_file) or not os.path.getsize(pid_file):
                    self.assertLess(time.monotonic(), deadline, 'the stub never started')
                    time.sleep(0.05)
                with open(pid_file, encoding='utf-8') as f:
                    child = int(f.read())
                proc.send_signal(sig)
                try:
                    code = proc.wait(15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    raise
                self.assertEqual(code, 128 + sig, proc.stdout.read().decode())
                self.assertProcessGone(child)

    def test_process_gone_without_proc(self):
        """Where /proc is absent (macOS) the check polls the pid itself: a live process is not gone."""
        sleeper = subprocess.Popen(('sleep', '600'))
        self.addCleanup(sleeper.wait)
        self.addCleanup(sleeper.kill)
        self.assertFalse(process_gone(sleeper.pid, proc='/nonexistent-proc'))
        self.assertFalse(process_gone(sleeper.pid))
        sleeper.kill()
        sleeper.wait()
        self.assertTrue(process_gone(sleeper.pid, proc='/nonexistent-proc'))
        self.assertTrue(process_gone(sleeper.pid))

    def assertProcessGone(self, pid):
        """[pid] ends within 5 s (a zombie of another parent counts as gone)."""
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if process_gone(pid):
                return
            time.sleep(0.1)
        os.kill(pid, 9)
        self.fail(f'process {pid} still runs')

    def test_pass_survives_keep_paths(self):
        write_bin(self.repo, 'check')
        self.assertEqual(self.run_gate().returncode, 0)
        self.repo.commit('omc/bin/check.md', 'a known red\n', 'gate note')
        self.repo.commit('tasks/x.md', 'brief\n', 'brief')
        self.passed()

    def test_pass_voided_by_src_change(self):
        write_bin(self.repo, 'check')
        self.assertEqual(self.run_gate().returncode, 0)
        old = short(self.repo)
        self.repo.commit(CODE, 'changed\n', 'fix')
        self.assertEqual(self.not_passed(), f'not passed: run at {old} does not hold: {CODE}')

    def test_a_change_to_a_gate_command_voids_its_pass(self):
        write_bin(self.repo, 'check')
        self.assertEqual(self.run_gate().returncode, 0)
        write_bin(self.repo, 'check', 'true')
        self.assertTrue(self.not_passed().endswith('does not hold: omc/bin/check'))

    def test_build_is_a_gate(self):
        write_bin(self.repo, 'build')
        self.assertEqual(self.run_gate('build').returncode, 0)
        self.passed('build')
        self.not_passed('check')

    def test_passed_and_skip_take_no_args(self):
        self.assertRefused('gate', 'passed', 'check', 'x')
        self.assertRefused('gate', 'skip', 'check', 'x')

    # ------------------------------------------------------------------------------------------------ a pass holds
    def test_a_message_only_amend_holds_for_gate_and_review(self):
        self.pass_here()
        self.ok('reviewed', '--record')
        self.repo.git('commit', '-q', '--amend', '-m', 'described')
        self.passed()
        self.assertTrue(self.answer(0, 'reviewed').startswith('reviewed at '))

    def test_a_squash_holds(self):
        self.repo.commit('src/b.txt', 'b\n', 'second')
        self.pass_here()
        self.repo.git('reset', '-q', '--soft', 'main')
        self.repo.git('commit', '-q', '-m', 'one commit')
        self.passed()

    def test_a_changed_shot_holds_for_a_gate_not_a_review(self):
        self.pass_here()
        self.ok('reviewed', '--record')
        self.repo.commit(SHOT, 'png\n', 'judged shot')
        self.passed()
        line = self.answer(1, 'reviewed')
        self.assertTrue(line.startswith('not reviewed: ') and line.endswith(f'does not hold: {SHOT}'), line)

    def test_a_baseline_advance_holds_for_both(self):
        self.pass_here()
        self.ok('reviewed', '--record')
        self.repo.commit(BASELINE, '{}\n', 'baseline')
        self.repo.write('tasks/x.md', 'brief\n')
        self.passed()
        self.answer(0, 'reviewed')

    def test_a_code_change_holds_for_nothing(self):
        self.pass_here()
        self.ok('reviewed', '--record')
        old = short(self.repo)
        self.repo.commit(CODE, 'changed\n', 'fix')
        self.assertEqual(self.not_passed(), f'not passed: run at {old} does not hold: {CODE}')
        self.assertTrue(self.answer(1, 'reviewed').endswith(f'does not hold: {CODE}'))

    def test_an_untracked_code_file_holds_for_nothing(self):
        self.pass_here()
        self.ok('reviewed', '--record')
        self.repo.write('src/new.txt', 'new\n')
        self.assertTrue(self.not_passed().endswith('does not hold: src/new.txt'))
        self.assertTrue(self.answer(1, 'reviewed').endswith('does not hold: src/new.txt'))

    # ------------------------------------------------------------------------------------------- a pass does not
    def test_a_verify_pass_does_not_answer_for_check(self):
        self.pass_here(gate='verify')
        self.not_passed('check')
        self.passed('verify')

    def test_a_removed_pass_does_not_hold(self):
        path = self.pass_here()
        self.passed()
        os.remove(path)
        self.assertEqual(self.not_passed(), 'not passed: no passed run started on a clean tree')

    def test_a_commit_git_cannot_find_does_not_hold(self):
        self.pass_here(head='deadbeef')
        self.assertEqual(self.not_passed(), 'not passed: run at deadbeef does not hold: the commit is gone')

    def test_a_file_that_does_not_parse_is_skipped(self):
        self.pass_here()
        broken = os.path.join(self.repo.work, '.cache', 'omc', 'passes', 'check', 'x.json')
        with open(broken, 'w', encoding='utf-8') as f:
            f.write('{"gate": "check", ')
        self.assertTrue(self.passed().startswith('passed: run at '))

    def test_the_newest_pass_that_holds_answers(self):
        old = self.repo.git('rev-parse', 'HEAD').strip()
        new = self.repo.commit(SHOT, 'png\n', 'shot')
        self.pass_here(head=old, at='2026-01-07T10:00:00')
        self.pass_here(head=new, at='2026-01-07T11:00:00')
        self.assertEqual(self.passed(), f'passed: run at {new[:8]}')

    # ------------------------------------------------------------------------------------------------------ a skip
    def test_a_skip_answers_true(self):
        self.ok('gate', 'skip', 'verify')
        sha = self.repo.git('rev-parse', 'HEAD').strip()
        with open(os.path.join(self.repo.work, '.cache', 'omc', 'skips', sha), encoding='utf-8') as f:
            self.assertEqual(f.read(), 'verify\n')
        self.assertEqual(self.passed('verify'), f'skipped by the owner at {sha[:8]}')
        self.not_passed('check')
        self.repo.commit(CODE, 'changed\n', 'fix')
        self.assertTrue(self.not_passed('verify').endswith(f'does not hold: {CODE}'))

    def test_a_second_skip_appends_its_gate(self):
        self.ok('gate', 'skip', 'verify')
        self.ok('gate', 'skip', 'check')
        self.ok('gate', 'skip', 'check')
        sha = self.repo.git('rev-parse', 'HEAD').strip()
        with open(os.path.join(self.repo.work, '.cache', 'omc', 'skips', sha), encoding='utf-8') as f:
            self.assertEqual(f.read(), 'verify\ncheck\n')
        self.passed('check')

    def test_a_skip_on_a_dirty_tree_is_refused(self):
        self.repo.write(CODE, 'changed\n')
        self.assertIn(CODE, self.assertRefused('gate', 'skip', 'check'))
        self.assertFalse(os.path.exists(os.path.join(self.repo.work, '.cache', 'omc', 'skips')))

    # ------------------------------------------------------------------------------------------ reviewed, settled
    def test_reviewed_record_then_reviewed(self):
        self.assertEqual(self.answer(1, 'reviewed'), 'not reviewed: no review recorded')
        self.ok('reviewed', '--record')
        sha = self.repo.git('rev-parse', 'HEAD').strip()
        with open(os.path.join(self.repo.work, '.cache', 'omc', 'reviewed', f'{sha}.json'), encoding='utf-8') as f:
            rec = json.load(f)
        self.assertEqual(sorted(rec), ['at', 'head'])
        self.assertEqual(rec['head'], sha)
        self.assertEqual(self.answer(0, 'reviewed'), f'reviewed at {sha[:8]}')

    def test_review_record_refuses_uncovered_changes(self):
        self.repo.write(SHOT, 'png\n')
        self.assertIn(SHOT, self.assertRefused('reviewed', '--record'))
        self.assertFalse(os.path.exists(os.path.join(self.repo.work, '.cache', 'omc', 'reviewed')))
        os.remove(os.path.join(self.repo.work, SHOT))
        self.repo.write(BASELINE, '{}\n')
        self.ok('reviewed', '--record')

    def test_settled_holds_until_anything_but_tasks_and_plans_changes(self):
        self.assertEqual(self.answer(1, 'settled'), 'not settled: nothing settled recorded')
        self.ok('settled', '--record')
        self.repo.commit('tasks/x.md', 'brief\n', 'brief')
        self.assertTrue(self.answer(0, 'settled').startswith('settled at '))
        self.repo.commit('docs/superpowers/plans/x-plan.md', 'plan\n', 'Plan: x')
        self.assertTrue(self.answer(0, 'settled').startswith('settled at '))
        self.repo.write('docs/superpowers/plans/x-plan.md', 'plan, a task ticked\n')
        self.assertTrue(self.answer(0, 'settled').startswith('settled at '))
        self.repo.write(CODE, 'x\n')
        self.assertTrue(self.answer(1, 'settled').endswith(f'does not hold: {CODE}'))
        self.assertIn(CODE, self.assertRefused('settled', '--record'))

    def test_gate_keep_from_config(self):
        self.repo.set_config('screenshots: [docs/screens/shots/**]', 'screenshots: ["shots/**"]')
        self.repo.set_config('plans: docs/superpowers/plans/', 'plans: plans/')
        self.pass_here()
        self.repo.commit('shots/en/x.png', 'png\n', 'judged shot')
        self.repo.commit('plans/x-plan.md', 'plan\n', 'Plan: x')
        self.repo.write('omc/bin/check.md', 'the gate note\n')
        self.passed()
        self.repo.write('docs/superpowers/plans/x-plan.md', 'plan\n')  # the default folder, not this project's
        self.assertTrue(self.not_passed().endswith('docs/superpowers/plans/x-plan.md'))
        os.remove(os.path.join(self.repo.work, 'docs/superpowers/plans/x-plan.md'))
        self.passed()
        self.repo.write('src/b.txt', 'b\n')
        self.assertTrue(self.not_passed().endswith('src/b.txt'))


class CliTest(unittest.TestCase):
    """The entry itself, `python3 -I omc/tools/omc.py`, over one repository."""

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)

    def test_a_slot_held_on_the_machine_does_not_stop_a_fixture_run(self):
        """The fixture's runs take their slots in its own registry, never the machine's: a gate of a real checkout
        running this very test (its slot held) does not make the fixture's run wait for it."""
        home = os.path.join(self.repo.root, 'home')
        machine = os.path.join(home, '.cache', 'omc', 'gates')
        write_bin(self.repo, 'check', 'echo green')
        with mock.patch.dict(os.environ, {concurrency.REGISTRY_ENV: machine}), \
                concurrency.slot(self.repo.root, 'check', 1, lambda line: None):
            r = subprocess.run((sys.executable, '-I', TOOL, 'gate', 'run', 'check'), cwd=self.repo.work,
                               env={**self.repo.env, 'HOME': home}, capture_output=True, text=True, timeout=20)
        self.assertEqual((r.returncode, r.stdout), (0, 'green\n'), r.stderr)

    def test_the_verbs_through_the_entry(self):
        r = self.repo.omc('gate', 'passed', 'check')
        self.assertEqual((r.returncode, r.stdout), (1, 'not passed: no passed run started on a clean tree\n'))
        write_bin(self.repo, 'check', 'echo green')
        r = self.repo.omc('gate', 'run', 'check')
        self.assertEqual((r.returncode, r.stdout), (0, 'green\n'), r.stderr)
        r = self.repo.omc('gate', 'passed', 'check')
        self.assertEqual((r.returncode, r.stdout), (0, f'passed: run at {short(self.repo)}\n'))
        self.assertEqual(self.repo.omc('reviewed', '--record').returncode, 0)
        self.assertEqual(self.repo.omc('reviewed').returncode, 0)
        self.repo.write(CODE, 'x\n')
        r = self.repo.omc('settled', '--record')
        self.assertEqual((r.returncode, r.stdout), (2, ''))
        self.assertTrue(r.stderr.startswith('error: '), r.stderr)
        self.assertEqual(self.repo.omc('gate', 'passed', 'deploy').returncode, 2)


class ComparisonTest(unittest.TestCase):
    """The comparison in-process, over one repository the cases only read."""

    @classmethod
    def setUpClass(cls):
        cls.repo = Repo.make_repo()
        cls.env = mock.patch.dict(os.environ, cls.repo.env, clear=True)
        cls.env.start()
        cls.repo.git('checkout', '-q', '-b', 'feature/x')
        cls.old = cls.repo.commit(CODE, 'a\n', 'code')
        cls.repo.commit(SHOT, 'png\n', 'shot')
        cls.repo.write('tasks/x.md', 'brief\n')

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.repo.cleanup()

    def test_changed_paths_are_the_tree_and_the_untracked_files_against_the_commit(self):
        self.assertEqual(done.changed_paths(self.repo.work, self.old), [SHOT, 'tasks/x.md'])
        self.assertIsNone(done.changed_paths(self.repo.work, 'deadbeef'))

    def test_holds_names_the_paths_its_list_does_not_keep(self):
        paths = config.load(self.repo.work).paths
        self.assertEqual(done.holds(self.repo.work, self.old, done.gate_keep(paths)), (True, []))
        self.assertEqual(done.holds(self.repo.work, self.old, done.review_keep(paths)), (False, [SHOT]))
        self.assertEqual(done.holds(self.repo.work, 'deadbeef', done.gate_keep(paths)),
                         (False, ['the commit is gone']))


if __name__ == '__main__':
    unittest.main()
