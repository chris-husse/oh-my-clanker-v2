"""Tests of omc/tools/notify.py, the notification channel the launch wires into the worktree: omc 0.1.54's `tests/unit/test_notify.py`, every case and expected byte kept, rewritten to unittest. omc's
`get_provider("claude")` is `notify.CLAUDE`; its codex provider, for the one case of a provider with no worktree file,
is `NoFile`, omc's base provider's `notification_setup` (`providers/base.py:62-64`, `{}`). Each case writes a
temporary worktree. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_notify.py"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from notify import CLAUDE, merge_claude_settings, wire_worktree  # noqa: E402

OLD = "omc internal notify --provider claude"


class NoFile:
    """omc's codex provider as the wiring sees it: the base provider's `notification_setup`, no worktree file."""

    name = "codex"

    def notification_setup(self, notifications):
        return {}


class NotifyTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)

    def wire(self, provider, enabled):
        """wire_worktree(provider, tmp_path, enabled) with stderr captured: (written, err)."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            written = wire_worktree(provider, self.tmp_path, enabled)
        return written, err.getvalue()

    def test_native_channel_written_and_repeated_wiring_is_idempotent(self):
        for enabled, channel in ((True, "auto"), (False, "notifications_disabled")):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory() as tmp:
                self.tmp_path = Path(tmp)
                self.assertEqual(self.wire(CLAUDE, enabled)[0], [".claude/settings.local.json"])
                path = self.tmp_path / ".claude/settings.local.json"
                self.assertEqual(json.loads(path.read_text()), {"preferredNotifChannel": channel})
                self.assertEqual(self.wire(CLAUDE, enabled)[0], [])

    def test_merge_removes_exact_old_hooks_and_preserves_foreign_members(self):
        existing = {
            "theme": "dark",
            "hooks": {
                "Notification": [
                    {
                        "matcher": "x",
                        "hooks": [
                            {"type": "command", "command": OLD},
                            {"type": "command", "command": OLD + " --extra"},
                            {"type": "prompt", "prompt": "keep"},
                        ],
                    }
                ],
                "Stop": [{"hooks": [{"type": "command", "command": OLD}]}],
                "PreToolUse": [{"hooks": [{"type": "command", "command": OLD}]}],
            },
        }
        ours = '{"preferredNotifChannel":"auto"}'
        merged = merge_claude_settings(json.dumps(existing), ours)
        data = json.loads(merged)
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["preferredNotifChannel"], "auto")
        self.assertEqual(
            data["hooks"]["Notification"],
            [
                {
                    "matcher": "x",
                    "hooks": [
                        {"type": "command", "command": OLD + " --extra"},
                        {"type": "prompt", "prompt": "keep"},
                    ],
                }
            ],
        )
        self.assertEqual(data["hooks"]["Stop"], [])
        self.assertEqual(data["hooks"]["PreToolUse"], existing["hooks"]["PreToolUse"])
        self.assertEqual(merge_claude_settings(merged, ours), merged)
        self.assertEqual(
            json.loads(merge_claude_settings(merged, '{"preferredNotifChannel":"notifications_disabled"}'))[
                "preferredNotifChannel"
            ],
            "notifications_disabled",
        )

    def test_bad_settings_are_preserved(self):
        for bad in ("{", "[]", '{"hooks": []}', '{"hooks":{"Stop":{}}}', '{"hooks":{"Stop":[{"hooks":{}}]}}'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp:
                self.tmp_path = Path(tmp)
                path = self.tmp_path / ".claude/settings.local.json"
                path.parent.mkdir()
                path.write_text(bad)
                written, err = self.wire(CLAUDE, True)
                self.assertEqual(written, [])
                self.assertEqual(path.read_text(), bad)
                self.assertIn("leaving it alone", err)

    def test_non_utf8_settings_are_preserved(self):
        path = self.tmp_path / ".claude/settings.local.json"
        path.parent.mkdir()
        path.write_bytes(b"\xff")
        written, err = self.wire(CLAUDE, True)
        self.assertEqual(written, [])
        self.assertEqual(path.read_bytes(), b"\xff")
        self.assertIn("could not write", err)

    def test_codex_has_no_worktree_file(self):
        self.assertEqual(self.wire(NoFile(), False)[0], [])
        self.assertEqual(list(self.tmp_path.iterdir()), [])

    def test_settings_write_failure_warns_and_does_not_break_launch(self):
        target = self.tmp_path / ".claude/settings.local.json"
        target.parent.mkdir()
        target.write_text('{"preferredNotifChannel":"notifications_disabled"}\n')
        before = target.read_bytes()
        original = Path.write_text

        def fail_target(path, content, *args, **kwargs):
            if path.parent == target.parent:
                raise OSError("read only")
            return original(path, content, *args, **kwargs)

        with mock.patch.object(Path, "write_text", fail_target):
            written, err = self.wire(CLAUDE, True)
        self.assertEqual(written, [])
        self.assertEqual(target.read_bytes(), before)
        self.assertIn("could not write", err)

    def test_partial_settings_write_preserves_original_and_cleans_temp(self):
        target = self.tmp_path / ".claude/settings.local.json"
        target.parent.mkdir()
        original = (
            b'{"permissions":{"allow":["Read"]},"preferredNotifChannel":"notifications_disabled"}\n'
        )
        target.write_bytes(original)
        real_write = Path.write_text

        def partial_write(path, content, *args, **kwargs):
            if path.parent == target.parent:
                with path.open("w") as stream:
                    stream.write(content[:10])
                raise OSError("disk full after partial write")
            return real_write(path, content, *args, **kwargs)

        with mock.patch.object(Path, "write_text", partial_write):
            written, err = self.wire(CLAUDE, True)
        self.assertEqual(written, [])
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(list(target.parent.iterdir()), [target])
        self.assertIn("could not write", err)

    def test_replace_failure_preserves_original_and_cleans_temp(self):
        target = self.tmp_path / ".claude/settings.local.json"
        target.parent.mkdir()
        original = b'{"permissions":{"allow":["Read"]}}\n'
        target.write_bytes(original)
        real_replace = Path.replace

        def fail_replace(path, destination):
            if destination == target:
                raise OSError("replace failed")
            return real_replace(path, destination)

        with mock.patch.object(Path, "replace", fail_replace):
            written, err = self.wire(CLAUDE, True)
        self.assertEqual(written, [])
        self.assertEqual(target.read_bytes(), original)
        self.assertEqual(list(target.parent.iterdir()), [target])
        self.assertIn("could not write", err)


if __name__ == "__main__":
    unittest.main()
