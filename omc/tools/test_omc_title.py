"""Tests of omc/tools/title.py, `just omc title set|release|apply`: quiet, config-free, exit codes 0/1/2, marker cooldown, serialized apply. omc 0.1.54's
`tests/unit/test_title.py`, every case and expected byte kept, rewritten to unittest: the entry is omc.py's `main`
(omc's was `omc.cli.main`), the worker's argv the port's (terminals.worker_argv), the fake worker replaces
toolctx's bounded run (omc's tests patched `ToolContext.run_bounded`), the fake clock title.py's `_clock` and `_sleep`.
`HOME` and `OMC_HOME` are temporary directories. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_title.py"""
import contextlib
import fcntl
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import title as title_mod  # noqa: E402
import toolctx  # noqa: E402
from omc import main as omc_main  # noqa: E402
from terminals import worker_argv  # noqa: E402

UUID = "38B11221-B7E1-4F36-8A3B-50D549172632"
WORKER = worker_argv(UUID, release=True)[:-1]


class Worker:
    """Fake SDK worker: records (argv, timeout); driven by `rc` / `raises`."""

    def __init__(self):
        self.calls, self.rc, self.raises = [], 0, None

    def __call__(self, env, argv, *, timeout, cwd=None, extra_env=None):
        self.calls.append((list(argv), timeout))
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(list(argv), self.rc, "", "secret-auth-value")


class Clock:
    """Fake clock + sleep for title.py: sleeping advances the clock, never the test."""

    def __init__(self):
        self.offset, self.sleeps, self.on_sleep = 0.0, [], None

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        if self.on_sleep is not None:
            self.on_sleep()
        self.offset += seconds


class TitleTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)
        self.home = self.tmp_path / "omc home"
        env = {k: v for k, v in os.environ.items() if k not in ("TERM_PROGRAM", "LC_TERMINAL")}
        env.update(OMC_HOME=str(self.home), HOME=str(self.tmp_path), ITERM_SESSION_ID=f"w0t1p0:{UUID}")
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.worker = Worker()
        self.patch(toolctx, "_run_bounded", self.worker)
        self.clock = Clock()
        real = time.time
        self.patch(title_mod, "_clock", lambda: real() + self.clock.offset)
        self.patch(title_mod, "_sleep", self.clock.sleep)
        self._out, self._err = io.StringIO(), io.StringIO()

    def patch(self, target, name, value):
        patcher = mock.patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def main(self, argv):
        with contextlib.redirect_stdout(self._out), contextlib.redirect_stderr(self._err):
            return omc_main(argv)

    def readouterr(self):
        captured = (self._out.getvalue(), self._err.getvalue())
        self._out, self._err = io.StringIO(), io.StringIO()
        return captured

    def marker(self):
        return self.home / "title-failed" / UUID

    def fresh_marker(self):
        marker = self.marker()
        marker.parent.mkdir(parents=True)
        marker.write_text("omc: iTerm2 tab title update failed: worker exit 1 (retry: ...)\nat now\n")
        return marker

    def aged_marker(self, age):
        marker = self.fresh_marker()
        then = time.time() - age
        os.utime(marker, (then, then))
        return marker

    def request(self, text):
        path = self.home / "title-request" / f"{UUID}-4242"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_set_runs_exact_worker_quietly(self):
        self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 0)
        self.assertEqual(self.worker.calls, [([*WORKER, "--", "feature/name"], 5.0)])
        self.assertEqual(self.readouterr(), ("", ""))  # no banner, no stdout, nothing on success
        self.assertFalse(self.marker().exists())

    def test_set_passes_hostile_title_literally(self):
        hostile = "feature/cost$USD(parent)\\(session.name); rm -rf"
        self.assertEqual(self.main(["title", "set", "--", hostile]), 0)
        self.assertEqual(self.worker.calls[0][0][-1], hostile)

    def test_release_runs_exact_worker_quietly(self):
        self.assertEqual(self.main(["title", "release"]), 0)
        self.assertEqual(self.worker.calls, [([*WORKER, "--release"], 5.0)])
        self.assertEqual(self.readouterr(), ("", ""))

    def test_bad_titles_are_refused_before_any_worker(self):
        for title in ("bad\007title", "bad\x9dtitle", ""):
            with self.subTest(title=title):
                self.assertEqual(self.main(["title", "set", "--", title]), 2)
                self.assertEqual(self.worker.calls, [])
                err = self.readouterr()[1]
                self.assertTrue(err.startswith("error: omc title:") and "Oh My Clanker" not in err, err)
                self.assertFalse(self.marker().exists())

    def test_missing_or_malformed_session_is_refused(self):
        for session in (None, "", "bad", f"unrelated:{UUID}"):
            with self.subTest(session=session):
                if session is None:
                    os.environ.pop("ITERM_SESSION_ID", None)
                else:
                    os.environ["ITERM_SESSION_ID"] = session
                self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 2)
                self.assertEqual(self.main(["title", "release"]), 2)
                self.assertEqual(self.worker.calls, [])
                err = self.readouterr()[1]
                self.assertTrue("ITERM_SESSION_ID" in err and "Traceback" not in err, err)

    def test_worker_failure_writes_marker_and_one_line(self):
        self.worker.rc = 3
        self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 1)
        lines = self.marker().read_text().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0], "omc: iTerm2 tab title update failed: worker exit 3 (retry: omc title set -- <branch>)"
        )
        self.assertTrue(lines[1].startswith("at 20"))  # human-readable timestamp, never parsed
        out, err = self.readouterr()
        self.assertEqual(out, "")
        self.assertEqual(err, lines[0] + "\n")
        self.assertNotIn("secret", err)  # the worker's stderr is never surfaced

    def test_worker_timeout_writes_marker(self):
        self.worker.raises = TimeoutError("command timed out after 5s")
        self.assertEqual(self.main(["title", "release"]), 1)
        self.assertIn("timed out after 5s", self.marker().read_text().splitlines()[0])
        self.assertEqual(self.readouterr()[1].count("\n"), 1)

    def test_throttled_apply_waits_out_the_cooldown_then_applies(self):
        cooldown = title_mod.COOLDOWN_SECONDS
        marker = self.aged_marker(20)
        request = self.request("set feature/name\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertEqual(len(self.clock.sleeps), 1)
        self.assertTrue(cooldown - 20 - 2 < self.clock.sleeps[0] <= cooldown - 20, self.clock.sleeps)
        self.assertEqual(self.worker.calls, [([*WORKER, "--", "feature/name"], 5.0)])
        self.assertEqual(Path(str(request) + ".applied").read_text(), "set feature/name\n")
        self.assertFalse(marker.exists())  # the retry succeeded
        self.assertEqual(self.readouterr(), ("", ""))

    def test_throttled_apply_sleep_is_bounded_by_the_cooldown(self):
        self.aged_marker(0)
        request = self.request("release\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertTrue(len(self.clock.sleeps) == 1 and 0 < self.clock.sleeps[0] <= title_mod.COOLDOWN_SECONDS)
        self.assertEqual(self.worker.calls, [([*WORKER, "--release"], 5.0)])

    def test_throttled_apply_applies_the_request_rewritten_while_it_slept(self):
        self.aged_marker(30)
        request = self.request("set first\n")
        self.clock.on_sleep = lambda: request.write_text("set second\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertEqual(self.worker.calls, [([*WORKER, "--", "second"], 5.0)])
        self.assertEqual(Path(str(request) + ".applied").read_text(), "set second\n")

    def test_throttled_apply_skips_a_request_another_helper_applied_meanwhile(self):
        self.aged_marker(30)
        request = self.request("set feature/x\n")
        applied = Path(str(request) + ".applied")
        self.clock.on_sleep = lambda: applied.write_text("set feature/x\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertTrue(len(self.clock.sleeps) == 1 and self.worker.calls == [])

    def test_throttled_apply_does_not_hold_the_lock_while_sleeping(self):
        self.aged_marker(30)
        request = self.request("set feature/x\n")
        taken = []

        def try_lock():
            with (self.home / "title-lock" / UUID).open("a+b") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)  # raises if the sleeper holds it
                taken.append(True)
                fcntl.flock(fh, fcntl.LOCK_UN)

        self.clock.on_sleep = try_lock
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertTrue(taken == [True] and len(self.worker.calls) == 1)

    def test_set_bypasses_cooldown_and_success_removes_marker(self):
        marker = self.fresh_marker()
        self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 0)
        self.assertEqual(self.worker.calls, [([*WORKER, "--", "feature/name"], 5.0)])
        self.assertEqual(self.readouterr(), ("", ""))
        self.assertFalse(marker.exists())

    def test_set_in_cooldown_still_reports_worker_failure(self):
        self.fresh_marker()
        self.worker.rc = 1
        self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 1)
        self.assertEqual(len(self.worker.calls), 1)
        self.assertIn("worker exit 1", self.readouterr()[1])

    def test_release_bypasses_cooldown(self):
        marker = self.fresh_marker()
        self.assertEqual(self.main(["title", "release"]), 0)
        self.assertEqual(self.worker.calls, [([*WORKER, "--release"], 5.0)])
        self.assertFalse(marker.exists())

    def test_stale_marker_retries_and_success_removes_it(self):
        marker = self.marker()
        marker.parent.mkdir(parents=True)
        marker.write_text("old\nat then\n")
        old = time.time() - 61
        os.utime(marker, (old, old))
        self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 0)
        self.assertEqual(len(self.worker.calls), 1)
        self.assertFalse(marker.exists())

    def test_future_marker_mtime_never_throttles(self):
        marker = self.marker()
        marker.parent.mkdir(parents=True)
        marker.write_text("skewed\nat later\n")
        future = time.time() + 3600
        os.utime(marker, (future, future))
        self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 0)
        self.assertEqual(len(self.worker.calls), 1)
        self.assertFalse(marker.exists())

    def test_unwritable_home_reports_one_line_and_exits_one(self):
        self.home.parent.mkdir(parents=True, exist_ok=True)
        self.home.write_text("a file where the omc home should be\n")
        self.worker.rc = 1
        self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 1)
        out, err = self.readouterr()
        self.assertEqual(out, "")
        self.assertEqual(err.count("\n"), 1)
        self.assertTrue("worker exit 1" in err and "marker not written" in err, err)
        self.assertNotIn("Traceback", err)

    def test_apply_performs_request_and_records_applied(self):
        request = self.request("set feature/x\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertEqual(self.worker.calls, [([*WORKER, "--", "feature/x"], 5.0)])
        self.assertEqual(Path(str(request) + ".applied").read_text(), "set feature/x\n")
        self.assertTrue((self.home / "title-lock" / UUID).exists())
        self.assertEqual(self.readouterr(), ("", ""))

    def test_apply_release_request(self):
        request = self.request("release\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertEqual(self.worker.calls, [([*WORKER, "--release"], 5.0)])

    def test_two_helpers_on_one_request_perform_one_write(self):
        request = self.request("set feature/x\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertEqual(len(self.worker.calls), 1)

    def test_request_rewritten_before_lock_is_applied_by_holder_not_newcomer(self):
        request = self.request("set first\n")
        real_flock = fcntl.flock
        rewritten = []

        def flock_then_rewrite(fh, op):
            real_flock(fh, op)
            if not rewritten:  # the holder was launched for "first"; "second" lands before it re-reads
                request.write_text("set second\n")
                rewritten.append(True)

        self.patch(title_mod.fcntl, "flock", flock_then_rewrite)
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)  # holder
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)  # newcomer launched for "second"
        self.assertEqual(self.worker.calls, [([*WORKER, "--", "second"], 5.0)])
        self.assertEqual(Path(str(request) + ".applied").read_text(), "set second\n")

    def test_lock_is_held_across_the_worker(self):
        request = self.request("set feature/x\n")
        entered = threading.Event()
        release = threading.Event()
        calls = []

        def blocking(env, argv, *, timeout, cwd=None, extra_env=None):
            calls.append(list(argv))
            entered.set()
            assert release.wait(10)
            return subprocess.CompletedProcess(list(argv), 0, "", "")

        self.patch(toolctx, "_run_bounded", blocking)
        results = {}
        holder = threading.Thread(target=lambda: results.update(holder=omc_main(["title", "apply", str(request)])))
        holder.start()
        self.assertTrue(entered.wait(10))
        newcomer = threading.Thread(
            target=lambda: results.update(newcomer=omc_main(["title", "apply", str(request)]))
        )
        newcomer.start()
        time.sleep(0.5)
        self.assertTrue(newcomer.is_alive() and len(calls) == 1)  # blocked on the lock while the worker runs
        release.set()
        holder.join(10)
        newcomer.join(10)
        self.assertEqual(results, {"holder": 0, "newcomer": 0})
        self.assertEqual(len(calls), 1)  # the newcomer found .applied == request and wrote nothing

    def test_apply_still_throttled_after_its_one_wait_gives_up_quietly(self):
        marker = self.aged_marker(30)

        def another_helper_failed_meanwhile():
            now = time.time() + self.clock.offset + self.clock.sleeps[-1]
            os.utime(marker, (now, now))

        self.clock.on_sleep = another_helper_failed_meanwhile
        request = self.request("set feature/x\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 0)
        self.assertEqual(len(self.clock.sleeps), 1)  # one wait, never a second: bounded by cooldown + deadline
        self.assertEqual(self.worker.calls, [])
        self.assertFalse(Path(str(request) + ".applied").exists())  # a later retry must re-apply
        self.assertTrue(marker.exists())  # untouched: the hook judges retries by mtime
        self.assertEqual(self.readouterr(), ("", ""))

    def test_apply_failure_does_not_record_applied(self):
        self.worker.rc = 1
        request = self.request("set feature/x\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 1)
        self.assertFalse(Path(str(request) + ".applied").exists())
        self.assertTrue(self.marker().exists())

    def test_apply_refuses_malformed_request_without_marker(self):
        for text in ("", "set \n", "set\n", "pin feature/x\n", "set bad\007\n", "\n"):
            with self.subTest(text=text):
                request = self.request(text)
                self.assertEqual(self.main(["title", "apply", str(request)]), 2)
                self.assertEqual(self.worker.calls, [])
                self.assertFalse(self.marker().exists())
                err = self.readouterr()[1]
                self.assertTrue(err.startswith("error: omc title:") and "Traceback" not in err, err)

    def test_apply_refuses_missing_request_file(self):
        self.assertEqual(self.main(["title", "apply", str(self.home / "nope")]), 2)
        self.assertEqual(self.worker.calls, [])
        self.assertIn("request file", self.readouterr()[1])

    def test_parse_request_contract(self):
        self.assertEqual(title_mod.parse_request("set feature/x\n"), ("set", "feature/x"))
        self.assertEqual(title_mod.parse_request("set a b\nignored second line\n"), ("set", "a b"))
        self.assertEqual(title_mod.parse_request("release\n"), ("release", None))
        with self.assertRaises(toolctx.Refusal):
            title_mod.parse_request("release please\n")

    def test_title_never_loads_configuration(self):
        def fail(*args, **kwargs):
            self.fail("omc title loaded configuration")

        self.patch(config, "load", fail)
        self.assertEqual(self.main(["title", "set", "--", "feature/name"]), 0)

    def test_apply_refuses_non_utf8_request(self):
        request = self.home / "title-request" / f"{UUID}-4242"
        request.parent.mkdir(parents=True)
        request.write_bytes(b"set feature/\xff\xfe\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 2)
        self.assertEqual(self.worker.calls, [])
        self.assertFalse(self.marker().exists())
        self.assertFalse(Path(str(request) + ".applied").exists())
        err = self.readouterr()[1]
        self.assertTrue(err.startswith("error: omc title:") and err.count("\n") == 1, err)

    def test_apply_keeps_carriage_return_and_refuses_it(self):
        request = self.request("")
        request.write_bytes(b"set feature/a\rb\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 2)
        self.assertEqual(self.worker.calls, [])

    def test_apply_with_unwritable_home_reports_one_error_line(self):
        request = self.tmp_path / "request"
        request.write_text("set feature/x\n")
        self.home.write_text("a file where the omc home should be\n")
        self.assertEqual(self.main(["title", "apply", str(request)]), 1)
        err = self.readouterr()[1]
        self.assertTrue(err.startswith("error: omc title:") and err.count("\n") == 1 and self.worker.calls == [],
                        err)


if __name__ == "__main__":
    unittest.main()
