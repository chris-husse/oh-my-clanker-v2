"""Exercise the generated fish launch command in a real shell and repository: omc 0.1.54's `tests/unit/test_fish_title.py`, rewritten to
unittest, every case and expected line kept. Rewritten only: the hooked path's helper, omc's `sys.executable -m omc`
patched to a recorder, is `shells.title_helper` patched to a recorder that takes `title apply <file>`; the conf.d copy
is the installed form (fish_integration.installed_hook) with the stub `omc` as its helper, which must never run.
`HOME`, `OMC_HOME` and the XDG directories are temporary; skipped where `fish` is not on PATH. Run from the
repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_fish_title.py"""
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import shells  # noqa: E402
from fish_integration import installed_hook  # noqa: E402
from herdr import osc7_report  # noqa: E402
from omc_stubs import host_bin  # noqa: E402
from shells import FishShell  # noqa: E402

FISH = shutil.which("fish")
SCRUB = (
    "ITERM_SESSION_ID", "TERM_PROGRAM", "LC_TERMINAL", "TMUX", "STY", "OMC_FISH_TITLE_DISABLE",
    "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME", "HOME", "OMC_HOME",
)  # fmt: skip


def _git(*args):
    subprocess.run(["git", *args], check=True)


def _init_repo(path):
    _git("init", "-q", str(path))
    _git("-C", str(path), "config", "user.name", "Test")
    _git("-C", str(path), "config", "user.email", "test@example.com")
    _git("-C", str(path), "config", "commit.gpgsign", "false")


@unittest.skipIf(FISH is None, "fish is not on PATH")
class FishTitleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp_path = self.tmp_path = Path(self._tmp.name)
        repo = self.repo = tmp_path / "repo's space"
        repo.mkdir()
        _init_repo(repo)
        (repo / "file").write_text("initial\n")
        _git("-C", str(repo), "add", "file")
        _git("-C", str(repo), "commit", "-qm", "initial")
        _git("-C", str(repo), "switch", "-qc", "feature/first")

        recorder = self.recorder = tmp_path / "title recorder's helper"
        recorder.write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> "$OMC_TITLE_LOG"\n')
        recorder.chmod(0o755)
        config = tmp_path / "config" / "fish"
        config.mkdir(parents=True)
        (config / "config.fish").write_text('echo USER_CONFIG >> "$OMC_TITLE_LOG"\n')
        self.log = tmp_path / "titles.log"
        base = {k: v for k, v in os.environ.items() if k not in SCRUB}
        # Pre-created so fish's interactive init never runs a bare `mkdir` on a restricted PATH
        # (the double-sourcing case below runs with PATH = stub dir).
        for base_dir in ("cache", "data"):
            (tmp_path / base_dir / "fish" / "generated_completions").mkdir(parents=True)
        home = tmp_path / "home"
        home.mkdir()
        self.env = {
            **base,
            "HOME": str(home),
            "OMC_TITLE_LOG": str(self.log),
            "XDG_CONFIG_HOME": str(tmp_path / "config"),
            "XDG_CACHE_HOME": str(tmp_path / "cache"),
            "XDG_DATA_HOME": str(tmp_path / "data"),
        }

    def tearDown(self):
        self._tmp.cleanup()

    def run_fish(self, extra="", *, title_argv=None, startup=None, env_extra=None, origin_cwd=None):
        argv, files = FishShell().build_invocation(
            cwd=str(self.repo),
            title="feature/first",
            startup_argv=startup or ["/bin/sh", "-c", 'echo STARTUP >> "$OMC_TITLE_LOG"'],
            title_seq="\033]0;feature/first\007",
            title_argv=[str(self.recorder)] if title_argv is None else title_argv,
            origin_cwd=origin_cwd,
        )
        self.assertFalse(files)
        argv[0] = FISH
        argv[3] += "; " + extra + "; exit"
        proc = subprocess.run(
            argv,
            cwd=self.tmp_path,
            env={**self.env, **(env_extra or {})},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=25,
        )
        return proc, self.log.read_text().splitlines() if self.log.exists() else []

    def test_initial_title_precedes_startup_and_user_config_runs(self):
        proc, lines = self.run_fish()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP"])

    def test_branch_and_tag_with_same_name_keep_literal_branch_title(self):
        _git("-C", str(self.repo), "-c", "tag.gpgSign=false", "tag", "-am", "test", "feature/first")
        proc, lines = self.run_fish("emit fish_prompt; fish_title")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP"])
        self.assertIn("feature/first", proc.stdout)

    def test_branch_switch_and_duplicate_lifecycle_events(self):
        proc, lines = self.run_fish(
            "git switch -qc feature/second; emit fish_preexec; emit fish_prompt; emit fish_prompt; "
            "fish_title"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP", "feature/second"])
        self.assertIn("feature/second", proc.stdout)

    def test_detached_and_outside_repo_keep_last_title(self):
        proc, lines = self.run_fish(
            "git switch --detach -q; emit fish_prompt; cd /; emit fish_prompt; fish_title"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP"])
        self.assertIn("feature/first", proc.stdout)

    def test_literal_special_branch_and_directory(self):
        branch = "feature/cost$USD(parent)"
        proc, lines = self.run_fish(
            "git switch -qc 'feature/cost$USD(parent)'; emit fish_prompt; fish_title"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP", branch])
        self.assertIn(branch, proc.stdout)

    def test_directory_change_refreshes_to_other_repository_branch(self):
        other = self.repo.parent / "other repo's space"
        other.mkdir()
        _init_repo(other)
        (other / "file").write_text("other\n")
        _git("-C", str(other), "add", "file")
        _git("-C", str(other), "commit", "-qm", "other")
        _git("-C", str(other), "switch", "-qc", "feature/elsewhere")
        proc, lines = self.run_fish(f"cd {shlex.quote(str(other))}; fish_title")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP", "feature/elsewhere"])
        self.assertIn("feature/elsewhere", proc.stdout)

    def test_failed_title_operation_deduplicates_and_keeps_startup(self):
        failure = self.repo.parent / "failed helper"
        failure.write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> "$OMC_TITLE_LOG"\nexit 1\n')
        failure.chmod(0o755)
        proc, lines = self.run_fish(
            "emit fish_prompt; emit fish_preexec; git switch -qc feature/second; emit fish_prompt",
            title_argv=[str(failure)],
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP", "feature/second"])

    def test_refresh_preserves_previous_command_status(self):
        proc, lines = self.run_fish("false; __omc_refresh_title; echo STATUS:$status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("STATUS:1", proc.stdout)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP"])

    def test_generated_start_in_iterm2_dispatches_exactly_one_set_despite_double_sourcing(self):
        tmp_path = self.tmp_path
        # The builder embeds the checkout's `just omc` as the hook's helper; point it at a recorder
        # that accepts `title apply <file>` so no real title worker can run.
        fake_helper = tmp_path / "fake helper"
        fake_helper.write_text(
            "#!/bin/sh\n"
            'printf \'%s\\n\' "$*" >> "$OMC_TITLE_LOG"\n'
            'if [ "$2" = apply ] && [ -r "$3" ]; then IFS= read -r l < "$3"; '
            'printf \'request: %s\\n\' "$l" >> "$OMC_TITLE_LOG"; fi\n'
            "exit 0\n"
        )
        fake_helper.chmod(0o755)
        stubs = tmp_path / "stubs"
        stubs.mkdir()
        (stubs / "git").symlink_to(shutil.which("git"))
        (stubs / "mkdir").symlink_to(host_bin("mkdir"))  # the hook runs `command mkdir`
        (stubs / "omc").write_text(
            '#!/bin/sh\nprintf \'PATH-OMC %s\\n\' "$*" >> "$OMC_TITLE_LOG"\nexit 0\n'
        )
        (stubs / "omc").chmod(0o755)
        confd = tmp_path / "config" / "fish" / "conf.d"
        confd.mkdir(parents=True)
        # The conf.d copy, the first sourcing: the installed form, its own helper the stub `omc`.
        (confd / "omc-title.fish").write_bytes(installed_hook([str(stubs / "omc")]))
        wait = (
            "set -l t 0; while test $t -lt 200; "
            "and test (count (string match -r '^request:' <$OMC_TITLE_LOG)) -lt 1; "
            f"set t (math $t + 1); {host_bin('sleep')} 0.05; end"
        )
        with mock.patch.object(shells, "title_helper", lambda: [str(fake_helper)]):
            proc, lines = self.run_fish(
                f"emit fish_prompt; emit fish_prompt; {wait}; {host_bin('sleep')} 0.2",
                env_extra={
                    "ITERM_SESSION_ID": "w0t1p0:38B11221-B7E1-4F36-8A3B-50D549172632",
                    "TERM_PROGRAM": "iTerm.app",
                    "PATH": str(stubs),
                    "OMC_HOME": str(tmp_path / "omc-home"),
                },
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue("USER_CONFIG" in lines and "STARTUP" in lines, lines)
        self.assertEqual(len([ln for ln in lines if ln.startswith("title apply ")]), 1, lines)
        self.assertEqual([ln for ln in lines if ln.startswith("request: ")], ["request: set feature/first"])
        # the preset helper is never overridden
        self.assertFalse(any(ln.startswith("PATH-OMC") for ln in lines), lines)
        self.assertNotIn("feature/first", lines)  # the inline recorder (else branch) did not run

    def test_generated_start_with_session_disable_uses_inline_path(self):
        proc, lines = self.run_fish(
            env_extra={
                "ITERM_SESSION_ID": "w0t1p0:38B11221-B7E1-4F36-8A3B-50D549172632",
                "TERM_PROGRAM": "iTerm.app",
                "OMC_FISH_TITLE_DISABLE": "1",
            }
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(lines, ["USER_CONFIG", "feature/first", "STARTUP"])

    def test_herdr_reports_worktree_cd_and_origin_without_host(self):
        other = self.tmp_path / "other dir ü"
        other.mkdir()
        origin = self.tmp_path / "launch 100%"
        proc, _ = self.run_fish(
            f"cd {shlex.quote(str(other))}",
            origin_cwd=str(origin),
            env_extra={"TERM_PROGRAM": "herdr"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            re.findall("\x1b\\]7;file:///[^\x07]*\x07", proc.stdout),
            [osc7_report(str(self.repo)), osc7_report(str(other)), osc7_report(str(origin))],
        )

    def test_no_hostless_report_outside_herdr(self):
        for env_extra in ({}, {"TERM_PROGRAM": "tmux"}):
            with self.subTest(env_extra=env_extra):
                other = self.tmp_path / "other dir ü"
                other.mkdir(exist_ok=True)
                origin = self.tmp_path / "launch 100%"
                proc, _ = self.run_fish(
                    f"cd {shlex.quote(str(other))}", origin_cwd=str(origin), env_extra=env_extra
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertNotIn("\x1b]7;file:///", proc.stdout)


if __name__ == "__main__":
    unittest.main()
