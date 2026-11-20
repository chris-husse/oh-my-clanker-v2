"""Tests of omc/tools/terminal_title.py, `python3 -I <root>/omc/tools/terminal_title.py <title>`:
omc 0.1.54's `tests/unit/test_terminal_title.py`, every case and expected byte kept, rewritten to unittest; the two
argvs (the title command's and the iTerm2 worker's) are the ones the port rewrites. `run_bounded` is replaced on the
context, as omc's tests patched it; no terminal and no iTerm2 is touched. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_terminal_title.py"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from terminal_title import run_title, terminal_title_argv, validate_title  # noqa: E402
from toolctx import Ctx  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
SESSION = "38B11221-B7E1-4F36-8A3B-50D549172632"


class TerminalTitleTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)

    def run_title(self, ctx, title):
        """run_title(ctx, title) with stdout and stderr captured: (rc, out, err)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = run_title(ctx, title)
        return rc, out.getvalue(), err.getvalue()

    def test_module_argv_is_this_script_under_isolated_python3(self):
        self.assertEqual(terminal_title_argv(), ["python3", "-I", os.path.join(ROOT, "omc", "tools", "terminal_title.py")])

    def test_portable_title_is_written(self):
        ctx = Ctx(home=self.home, env={})
        rc, out, _ = self.run_title(ctx, "feature/title")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "\033]0;feature/title\007")

    def test_control_characters_are_rejected_without_terminal_write(self):
        ctx = Ctx(home=self.home, env={})
        rc, out, err = self.run_title(ctx, "bad\007title")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertIn("invalid title", err)

    def test_c1_control_character_is_rejected_without_terminal_write(self):
        ctx = Ctx(home=self.home, env={})
        rc, out, _ = self.run_title(ctx, "bad\x9dtitle")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")

    def test_iterm_adapter_invokes_exact_worker_and_falls_back(self):
        ctx = Ctx(home=self.home, env={"TERM_PROGRAM": "iTerm.app", "ITERM_SESSION_ID": f"w0t1p0:{SESSION}"})
        calls = []

        def fake_run(argv, *, timeout, cwd=None, extra_env=None):
            calls.append((argv, timeout))
            return subprocess.CompletedProcess(argv, 7, "secret-stdout", "secret-auth-value")

        ctx.run_bounded = fake_run
        rc, out, err = self.run_title(ctx, "feature/name")
        self.assertEqual(rc, 1)
        self.assertEqual(
            calls,
            [
                (
                    [
                        "env",
                        f"UV_PROJECT_ENVIRONMENT={ROOT}/.cache/venv",
                        "uv",
                        "run",
                        "--frozen",
                        "--project",
                        os.path.join(ROOT, "omc"),
                        "python",
                        "-I",
                        os.path.join(ROOT, "omc", "tools", "iterm2_title.py"),
                        "--session-id",
                        SESSION,
                        "--",
                        "feature/name",
                    ],
                    5,
                )
            ],
        )
        self.assertEqual(out, "\033]0;feature/name\007")
        self.assertIn("cannot pin", err)
        self.assertNotIn("secret", err)

    def test_iterm_adapter_success_emits_no_fallback_or_warning(self):
        ctx = Ctx(home=self.home, env={"TERM_PROGRAM": "iTerm.app", "ITERM_SESSION_ID": SESSION})
        ctx.run_bounded = lambda argv, *, timeout: subprocess.CompletedProcess(argv, 0, "", "")
        rc, out, err = self.run_title(ctx, "feature/name")
        self.assertEqual(rc, 0)
        self.assertEqual((out, err), ("", ""))

    def test_malformed_session_id_never_starts_worker(self):
        ctx = Ctx(home=self.home, env={"TERM_PROGRAM": "iTerm.app", "ITERM_SESSION_ID": "bad"})
        ctx.run_bounded = lambda *a, **k: (_ for _ in ()).throw(AssertionError("worker started"))
        rc, out, _ = self.run_title(ctx, "feature/name")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "\033]0;feature/name\007")

    def test_malformed_iterm_prefix_never_starts_worker(self):
        ctx = Ctx(home=self.home, env={"TERM_PROGRAM": "iTerm.app", "ITERM_SESSION_ID": f"unrelated:{SESSION}"})
        calls = []
        ctx.run_bounded = lambda *a, **k: calls.append(a)
        rc, out, _ = self.run_title(ctx, "feature/name")
        self.assertEqual(rc, 1)
        self.assertEqual(calls, [])
        self.assertEqual(out, "\033]0;feature/name\007")

    def test_worker_timeout_falls_back(self):
        ctx = Ctx(home=self.home, env={"TERM_PROGRAM": "iTerm.app", "ITERM_SESSION_ID": SESSION})
        ctx.run_bounded = lambda *a, **k: (_ for _ in ()).throw(TimeoutError())
        rc, out, err = self.run_title(ctx, "feature/name")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "\033]0;feature/name\007")
        self.assertIn("cannot pin", err)

    def test_validate_title_names_control_characters_only(self):
        self.assertIsNone(validate_title("feature/name"))
        self.assertIsNone(validate_title(""))  # emptiness is the helper's rule, not this one's
        self.assertEqual(validate_title("bad\007title"), "control characters are not allowed")
        self.assertEqual(validate_title("bad\x9dtitle"), "control characters are not allowed")
        self.assertEqual(validate_title("tab\there"), "control characters are not allowed")


if __name__ == "__main__":
    unittest.main()
