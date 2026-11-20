"""Tests of omc/tools/terminals.py, the terminal title adapters:
omc 0.1.54's `tests/unit/test_terminals.py`, every case and expected byte kept, rewritten to unittest. Run from the
repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_terminals.py"""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import terminals  # noqa: E402
from terminals import detect_terminal, iterm2_session_id  # noqa: E402
from toolctx import Ctx  # noqa: E402


class TerminalsTest(unittest.TestCase):
    def test_osc_fallback(self):
        t = detect_terminal({})
        self.assertEqual(t.name, "osc")
        self.assertEqual(t.title_sequence("my-slug"), "\033]0;my-slug\007")

    def test_iterm2_detected_reuses_osc0(self):
        t = detect_terminal({"TERM_PROGRAM": "iTerm.app"})
        self.assertEqual(t.name, "iterm2")
        self.assertEqual(t.title_sequence("x"), "\033]0;x\007")

    def test_portable_terminal_writes_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = Ctx(home=Path(tmp), env={})
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertIs(detect_terminal(ctx.env).set_title(ctx, "feature/name"), True)
            self.assertEqual(out.getvalue(), "\033]0;feature/name\007")

    def test_worker_argv_project_is_omc(self):
        """The worker runs in the uv project omc/ of the checkout (its pyproject.toml), the venv the checkout's."""
        root = os.path.dirname(os.path.dirname(HERE))
        argv = terminals.worker_argv("S", title="t")
        self.assertEqual(argv[argv.index("--project") + 1], os.path.join(root, "omc"))
        self.assertIn(f"UV_PROJECT_ENVIRONMENT={root}/.cache/venv", argv)
        self.assertEqual(argv[-4:], ["--session-id", "S", "--", "t"])

    def test_iterm2_session_id_accepts_bare_and_prefixed_uuid(self):
        uuid = "38B11221-B7E1-4F36-8A3B-50D549172632"
        self.assertEqual(iterm2_session_id({"ITERM_SESSION_ID": uuid}), uuid)
        self.assertEqual(iterm2_session_id({"ITERM_SESSION_ID": f"w0t1p0:{uuid}"}), uuid)
        self.assertEqual(iterm2_session_id({"ITERM_SESSION_ID": uuid.lower()}), uuid.lower())

    def test_iterm2_session_id_rejects_missing_and_malformed(self):
        uuid = "38B11221-B7E1-4F36-8A3B-50D549172632"
        for env in (
            {},
            {"ITERM_SESSION_ID": ""},
            {"ITERM_SESSION_ID": "bad"},
            {"ITERM_SESSION_ID": f"unrelated:{uuid}"},
            {"ITERM_SESSION_ID": f"w0t1p0:{uuid}:extra"},
            {"ITERM_SESSION_ID": "38B11221B7E14F368A3B50D549172632"},  # no dashes: not a round trip
            {"ITERM_SESSION_ID": "w0t1p0:"},
        ):
            with self.subTest(env=env):
                self.assertIsNone(iterm2_session_id(env), env)


if __name__ == "__main__":
    unittest.main()
