"""Tests of omc/tools/fish_integration.py, `just omc shell-integration fish enable|disable|status|reconcile`: the managed fish hook's lifecycle, owned by prefix, refusing foreign files, sparing
config.fish. omc 0.1.54's `tests/unit/test_fish_integration.py`, every case and expected byte kept, rewritten to
unittest; the installed copy's expected bytes are the packaged hook's with the `set -g __omc_title_helper …` line below
the ownership marker (`installed_hook()`), and the packaged hook lives in omc/tools, not in omc's `assets`. `HOME`,
`OMC_HOME` and `XDG_CONFIG_HOME` are temporary directories. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_fish_integration.py"""
import contextlib
import io
import json
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from fish_integration import (  # noqa: E402
    HOOK_PREFIX,
    fish_hook_path,
    installed_hook,
    is_owned,
    managed_fish_path,
    remove_owned_hook,
    run_fish_integration,
)
from omc import main as omc_main  # noqa: E402
from toolctx import Ctx, Refusal  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))


def _ctx(tmp_path, **extra):
    return Ctx.from_env({"HOME": str(tmp_path), "OMC_HOME": str(tmp_path / "omc"), **extra})


class FishIntegrationTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)
        self._out, self._err = io.StringIO(), io.StringIO()

    def capture(self):
        stack = contextlib.ExitStack()
        stack.enter_context(contextlib.redirect_stdout(self._out))
        stack.enter_context(contextlib.redirect_stderr(self._err))
        return stack

    def readouterr(self):
        captured = (self._out.getvalue(), self._err.getvalue())
        self._out, self._err = io.StringIO(), io.StringIO()
        return captured

    def test_packaged_asset_is_the_hook_and_carries_the_prefix(self):
        asset = fish_hook_path()
        self.assertTrue(asset.name == "omc-title.fish" and asset.parent == Path(HERE), asset)
        self.assertTrue(asset.read_text().splitlines()[0].startswith(HOOK_PREFIX + " v"))

    def test_installed_copy_is_the_packaged_hook_with_the_helper_below_the_marker(self):
        packaged = fish_hook_path().read_bytes()
        marker, rest = packaged.split(b"\n", 1)
        helper = f"set -g __omc_title_helper just --justfile {shlex.quote(os.path.join(ROOT, 'justfile'))} omc\n"
        self.assertEqual(installed_hook(), marker + b"\n" + helper.encode() + rest)

    def test_managed_hook_lifecycle(self):
        ctx = _ctx(self.tmp_path)
        target = managed_fish_path(ctx)
        self.assertEqual(target, self.tmp_path / ".config" / "fish" / "conf.d" / "omc-title.fish")
        config = target.parent.parent / "config.fish"
        config.parent.mkdir(parents=True)
        config.write_bytes(b"# my fish settings\n")
        with self.capture():
            self.assertEqual(run_fish_integration(ctx, "enable"), 0)
            first = target.read_bytes()
            self.assertEqual(first, installed_hook())
            self.assertEqual(run_fish_integration(ctx, "reconcile"), 0)
            self.assertEqual(target.read_bytes(), first)  # byte-idempotent
            self.assertEqual(config.read_bytes(), b"# my fish settings\n")
            self.assertEqual(run_fish_integration(ctx, "status"), 0)
        status = json.loads(self.readouterr()[0])
        self.assertEqual(status, {"enabled": True, "installed": True, "path": str(target), "owned": True})
        with self.capture():
            self.assertEqual(run_fish_integration(ctx, "disable"), 0)
            self.assertFalse(target.exists())
            self.assertTrue((ctx.home / "integrations" / "fish-title.disabled").exists())
            self.assertEqual(run_fish_integration(ctx, "reconcile"), 0)
            self.assertFalse(target.exists())  # reconcile honors the opt-out
            self.assertEqual(run_fish_integration(ctx, "status"), 0)
        self.assertIs(json.loads(self.readouterr()[0])["enabled"], False)
        with self.capture():
            self.assertEqual(run_fish_integration(ctx, "enable"), 0)
        self.assertEqual(target.read_bytes(), first)
        self.assertFalse((ctx.home / "integrations" / "fish-title.disabled").exists())

    def test_header_bump_never_orphans_an_earlier_copy(self):
        ctx = _ctx(self.tmp_path)
        target = managed_fish_path(ctx)
        target.parent.mkdir(parents=True)
        target.write_bytes(b"# omc-managed fish title integration v1\nfunction old; end\n")
        self.assertTrue(is_owned(target))
        self.assertEqual(run_fish_integration(ctx, "reconcile"), 0)
        self.assertEqual(target.read_bytes(), installed_hook())

    def test_xdg_config_home_absolute_only(self):
        tmp_path = self.tmp_path
        self.assertEqual(
            managed_fish_path(_ctx(tmp_path, XDG_CONFIG_HOME=str(tmp_path / "my config"))),
            tmp_path / "my config" / "fish" / "conf.d" / "omc-title.fish",
        )
        self.assertEqual(
            managed_fish_path(_ctx(tmp_path, XDG_CONFIG_HOME="relative/config")),
            tmp_path / ".config" / "fish" / "conf.d" / "omc-title.fish",
        )
        no_home = Ctx.from_env({"OMC_HOME": str(tmp_path / "omc")})
        self.assertEqual(managed_fish_path(no_home), Path.home() / ".config" / "fish" / "conf.d" / "omc-title.fish")

    def test_unowned_file_and_symlink_are_refused_untouched(self):
        for action in ("enable", "reconcile"):
            with self.subTest(action=action):
                ctx = _ctx(self.tmp_path / action, XDG_CONFIG_HOME=str(self.tmp_path / action / "my config"))
                target = managed_fish_path(ctx)
                target.parent.mkdir(parents=True)
                target.write_bytes(b"my hook\n")
                with self.assertRaisesRegex(Refusal, str(target)):
                    run_fish_integration(ctx, action)
                self.assertEqual(target.read_bytes(), b"my hook\n")
                target.unlink()
                target.symlink_to(self.tmp_path / "absent")
                with self.assertRaisesRegex(Refusal, "symlink"):
                    run_fish_integration(ctx, action)
                self.assertTrue(target.is_symlink())
                self.assertFalse(is_owned(target))

    @staticmethod
    def _symlinked_fish_dir(tmp_path):
        """~/.config/fish -> a dotfiles checkout, as stow/chezmoi/yadm setups lay it out."""
        fish_dir = tmp_path / ".config" / "fish"
        fish_dir.parent.mkdir(parents=True)
        real = tmp_path / "dotfiles" / "fish"
        real.mkdir(parents=True)
        fish_dir.symlink_to(real)
        return real

    def test_symlinked_parent_is_written_through(self):
        for action in ("enable", "reconcile"):
            with self.subTest(action=action):
                tmp_path = self.tmp_path / action
                ctx = _ctx(tmp_path)
                real = self._symlinked_fish_dir(tmp_path)
                self.assertEqual(run_fish_integration(ctx, action), 0)
                landed = real / "conf.d" / "omc-title.fish"
                self.assertEqual(landed.read_bytes(), installed_hook())
                self.assertTrue(not landed.is_symlink() and is_owned(managed_fish_path(ctx)))

    def test_disable_under_symlinked_parent_records_opt_out(self):
        ctx = _ctx(self.tmp_path)
        real = self._symlinked_fish_dir(self.tmp_path)
        with self.capture():
            self.assertEqual(run_fish_integration(ctx, "enable"), 0)
            self.assertEqual(run_fish_integration(ctx, "disable"), 0)
        self.assertFalse((real / "conf.d" / "omc-title.fish").exists())
        self.assertTrue((ctx.home / "integrations" / "fish-title.disabled").exists())
        self.assertEqual(self.readouterr(), ("", ""))

    def test_disable_over_a_foreign_target_records_opt_out_with_one_note(self):
        for kind in ("unowned", "symlink"):
            with self.subTest(kind=kind):
                tmp_path = self.tmp_path / kind
                ctx = _ctx(tmp_path)
                target = managed_fish_path(ctx)
                target.parent.mkdir(parents=True)
                if kind == "unowned":
                    target.write_bytes(b"my hook\n")
                else:
                    target.symlink_to(tmp_path / "absent")
                with self.capture():
                    self.assertEqual(run_fish_integration(ctx, "disable"), 0)
                self.assertTrue((ctx.home / "integrations" / "fish-title.disabled").exists())
                if kind == "unowned":
                    self.assertEqual(target.read_bytes(), b"my hook\n")
                else:
                    self.assertTrue(target.is_symlink())
                out, err = self.readouterr()
                self.assertEqual(out, "")
                self.assertTrue(err.count("\n") == 1 and str(target) in err, err)

    def test_reconcile_while_opted_out_leaves_a_foreign_file(self):
        ctx = _ctx(self.tmp_path)
        with self.capture():
            self.assertEqual(run_fish_integration(ctx, "disable"), 0)
            target = managed_fish_path(ctx)
            target.parent.mkdir(parents=True)
            target.write_bytes(b"my hook\n")
            self.assertEqual(run_fish_integration(ctx, "reconcile"), 0)
        self.assertEqual(target.read_bytes(), b"my hook\n")
        self.assertLessEqual(self.readouterr()[1].count("\n"), 1)
        target.unlink()
        target.symlink_to(self.tmp_path / "absent")
        self.assertEqual(run_fish_integration(ctx, "reconcile"), 0)
        self.assertTrue(target.is_symlink())

    def test_status_never_refuses(self):
        ctx = _ctx(self.tmp_path)
        target = managed_fish_path(ctx)
        target.parent.mkdir(parents=True)
        target.write_bytes(b"my hook\n")
        with self.capture():
            self.assertEqual(run_fish_integration(ctx, "status"), 0)
        status = json.loads(self.readouterr()[0])
        self.assertTrue(status["installed"] is True and status["owned"] is False)

    def test_remove_owned_hook_is_non_blocking(self):
        ctx = _ctx(self.tmp_path)
        target = managed_fish_path(ctx)
        self.assertIsNone(remove_owned_hook(ctx))  # absent
        self.assertEqual(run_fish_integration(ctx, "enable"), 0)
        self.assertIsNone(remove_owned_hook(ctx))
        self.assertFalse(target.exists())
        target.write_bytes(b"my hook\n")
        note = remove_owned_hook(ctx)
        self.assertTrue(note is not None and str(target) in note and "not an omc-owned file" in note, note)
        self.assertEqual(target.read_bytes(), b"my hook\n")
        target.unlink()
        target.symlink_to(self.tmp_path / "absent")
        self.assertIsNotNone(remove_owned_hook(ctx))
        self.assertTrue(target.is_symlink())

    def _entry_env(self, ctx):
        env = {k: v for k, v in os.environ.items() if k != "XDG_CONFIG_HOME"}
        env.update(HOME=str(self.tmp_path), OMC_HOME=str(ctx.home))
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_owned_hook_removal_permission_error_is_an_error(self):
        ctx = _ctx(self.tmp_path)
        self.assertEqual(run_fish_integration(ctx, "enable"), 0)
        target = managed_fish_path(ctx)
        original = target.read_bytes()
        real_unlink = Path.unlink

        def deny_target(path, *args, **kwargs):
            if path == target:
                raise PermissionError("simulated read-only fish directory")
            return real_unlink(path, *args, **kwargs)

        self._entry_env(ctx)
        with mock.patch.object(Path, "unlink", deny_target):
            with self.capture():
                self.assertEqual(omc_main(["shell-integration", "fish", "disable"]), 1)
            self.assertEqual(target.read_bytes(), original)
            self.assertIn("fish integration removal failed", self.readouterr()[1])
            self.assertIsNotNone(remove_owned_hook(ctx))  # uninstall path: a note, not an exception

    def test_enable_flag_removal_permission_error_is_reported(self):
        ctx = _ctx(self.tmp_path)
        self.assertEqual(run_fish_integration(ctx, "disable"), 0)
        flag = ctx.home / "integrations" / "fish-title.disabled"
        real_unlink = Path.unlink

        def deny_flag(path, *args, **kwargs):
            if path == flag:
                raise PermissionError("simulated read-only omc integrations directory")
            return real_unlink(path, *args, **kwargs)

        self._entry_env(ctx)
        with mock.patch.object(Path, "unlink", deny_flag):
            with self.capture():
                self.assertEqual(omc_main(["shell-integration", "fish", "enable"]), 1)
        self.assertTrue(managed_fish_path(ctx).exists())
        self.assertTrue(flag.exists())
        self.assertIn("could not clear fish disable", self.readouterr()[1])


if __name__ == "__main__":
    unittest.main()
