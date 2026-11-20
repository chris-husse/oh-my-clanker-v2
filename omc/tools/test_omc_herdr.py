"""Tests of omc/tools/herdr.py, the herdr sidebar's OSC 7 report and its SessionStart hook:
omc 0.1.54's `tests/unit/test_herdr.py`, every case and expected byte kept, rewritten to unittest; omc's
`run_internal(["herdr-cwd", …])` is the module's own `main([…])`. Each case gets a temporary `dev/pts/7` in place of
`/dev`, and a stub `ps` alone on `PATH` that logs its argv and prints the line the case gives; no real tty is
written. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_herdr.py"""
import contextlib
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import herdr  # noqa: E402
from herdr import osc7_report, percent_encode_path  # noqa: E402


class EncodingTest(unittest.TestCase):
    def test_percent_encode_matches_fish_url_escape(self):
        self.assertEqual(percent_encode_path("/home/a b/x%y/ü"), "/home/a%20b/x%25y/%C3%BC")
        self.assertEqual(percent_encode_path("/t/repo's space/A-Z_a.z~0"), "/t/repo%27s%20space/A-Z_a.z~0")
        self.assertEqual(percent_encode_path("/x/a+b,c=d@e:f!g(h)*"), "/x/a%2Bb%2Cc%3Dd%40e%3Af%21g%28h%29%2A")

    def test_percent_encode_never_raises_on_non_utf8_bytes(self):
        self.assertEqual(percent_encode_path(os.fsdecode(b"/x/\xff")), "/x/%FF")

    def test_osc7_report_is_hostless_file_uri(self):
        self.assertEqual(osc7_report("/w/a b"), "\x1b]7;file:///w/a%20b\x07")


def _ps_stub(bindir, line, rc=0):
    log = bindir / "ps.log"
    script = bindir / "ps"
    script.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> {shlex.quote(str(log))}\n"
        f"printf '%s\\n' {shlex.quote(line)}\nexit {rc}\n"
    )
    script.chmod(0o755)
    return log


class HerdrCwdTest(unittest.TestCase):
    """omc's `herdr_env` fixture: the temporary dev, the stub bin dir alone on PATH, TERM_PROGRAM=herdr."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        tmp_path = Path(tmp.name)
        self.dev = tmp_path / "dev"
        (self.dev / "pts").mkdir(parents=True)
        (self.dev / "pts" / "7").write_bytes(b"")
        self.bindir = tmp_path / "bin"
        self.bindir.mkdir()
        self.log = self.bindir / "ps.log"
        for patcher in (
            mock.patch.object(herdr, "_DEV_DIR", self.dev),
            mock.patch.dict(os.environ, {"PATH": str(self.bindir), "TERM_PROGRAM": "herdr"}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_main(self, argv, stdin):
        """herdr.main(argv) with `stdin` as sys.stdin, stdout and stderr captured: (rc, out, err)."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin)), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            rc = herdr.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_herdr_cwd_writes_encoded_report_to_first_ancestor_terminal(self):
        _ps_stub(self.bindir, "  4242 pts/7")
        rc, out, err = self.run_main([], json.dumps({"cwd": "/home/a b/x%y/ü", "hook_event_name": "SessionStart"}))
        self.assertEqual(rc, 0)
        self.assertEqual((self.dev / "pts" / "7").read_bytes(), b"\x1b]7;file:///home/a%20b/x%25y/%C3%BC\x07")
        self.assertEqual(self.log.read_text().splitlines()[0], f"-o ppid= -o tty= -p {os.getppid()}")
        self.assertTrue(out == "" and err == "")

    def test_herdr_cwd_outside_herdr_does_nothing(self):
        for term_program in (None, "tmux"):
            with self.subTest(term_program=term_program):
                if term_program is None:
                    os.environ.pop("TERM_PROGRAM", None)
                else:
                    os.environ["TERM_PROGRAM"] = term_program
                _ps_stub(self.bindir, "  4242 pts/7")
                rc, out, err = self.run_main([], json.dumps({"cwd": "/w"}))
                self.assertEqual(rc, 0)
                self.assertEqual((self.dev / "pts" / "7").read_bytes(), b"")
                self.assertFalse(self.log.exists())
                self.assertTrue(out == "" and err == "")

    def test_herdr_cwd_ends_silently(self):
        cases = {
            "no-input": ("", "4242 pts/7", 0),
            "not-json": ("not json", "4242 pts/7", 0),
            "no-cwd": ('{"session_id": "x"}', "4242 pts/7", 0),
            "relative-cwd": ('{"cwd": "relative/dir"}', "4242 pts/7", 0),
            "lone-surrogate-cwd": ('{"cwd": "/x/\\ud800"}', "4242 pts/7", 0),
            "no-ancestor-terminal": ('{"cwd": "/w"}', "    1 ?", 0),
            "ps-fails": ('{"cwd": "/w"}', "", 1),
            "never-reaches-pid-1": ('{"cwd": "/w"}', "4242 ?", 0),
            "macos-no-terminal": ('{"cwd": "/w"}', "4242 ??", 0),
            "not-a-device-name": ('{"cwd": "/w"}', "4242 pts/../pts/7", 0),
            "device-absent": ('{"cwd": "/w"}', "4242 pts/9", 0),
        }
        for name, (stdin, ps_line, ps_rc) in cases.items():
            with self.subTest(name):
                _ps_stub(self.bindir, ps_line, ps_rc)
                rc, out, err = self.run_main([], stdin)
                self.assertEqual(rc, 0)
                self.assertEqual((self.dev / "pts" / "7").read_bytes(), b"")
                self.assertTrue(out == "" and err == "")

    def test_herdr_cwd_rejects_extra_arguments(self):
        rc, _, _ = self.run_main(["x"], "")
        self.assertEqual(rc, 2)


class NameTabTest(unittest.TestCase):
    """`name_tab`: `herdr tab rename <HERDR_TAB_ID> <label>` inside herdr, through the context's bounded run (a
    recorder here); nothing outside it."""

    def ctx(self, env, rc=0, raises=None):
        calls = []

        def run(argv, **kwargs):
            calls.append((list(argv), kwargs.get("timeout")))
            if raises:
                raise raises
            return subprocess.CompletedProcess(argv, rc, "", "")
        return herdr.Ctx(env=env, home=Path("/nonexistent"), run_bounded=run), calls

    def test_inside_herdr_the_tab_is_renamed(self):
        ctx, calls = self.ctx({"TERM_PROGRAM": "herdr", "HERDR_TAB_ID": "wW:t4"})
        self.assertTrue(herdr.name_tab(ctx, "add-weekly-payout-report"))
        self.assertEqual(calls, [(["herdr", "tab", "rename", "wW:t4", "add-weekly-payout-report"], 5)])

    def test_herdrs_own_binary_is_used_when_named(self):
        ctx, calls = self.ctx({"TERM_PROGRAM": "herdr", "HERDR_TAB_ID": "wW:t4", "HERDR_BIN_PATH": "/opt/h/herdr"})
        self.assertTrue(herdr.name_tab(ctx, "x-y-z"))
        self.assertEqual(calls[0][0][0], "/opt/h/herdr")

    def test_outside_herdr_nothing_runs(self):
        for env in ({}, {"TERM_PROGRAM": "tmux", "HERDR_TAB_ID": "wW:t4"}, {"TERM_PROGRAM": "herdr"}):
            with self.subTest(env=env):
                ctx, calls = self.ctx(env)
                self.assertIsNone(herdr.name_tab(ctx, "x-y-z"))
                self.assertEqual(calls, [])

    def test_a_failed_rename_is_false_never_raised(self):
        for rc, raises in ((1, None), (0, OSError("no herdr")), (0, TimeoutError("slow"))):
            with self.subTest(rc=rc, raises=raises):
                ctx, _ = self.ctx({"TERM_PROGRAM": "herdr", "HERDR_TAB_ID": "wW:t4"}, rc=rc, raises=raises)
                self.assertFalse(herdr.name_tab(ctx, "x-y-z"))


if __name__ == "__main__":
    unittest.main()
