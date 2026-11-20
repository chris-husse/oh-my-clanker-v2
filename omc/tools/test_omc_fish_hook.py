"""Tests of omc/tools/omc-title.fish, the fish title hook, in a real fish: restricted PATH, a stub helper, scrubbed
iTerm2 env. omc 0.1.54's `tests/unit/test_fish_hook.py`, rewritten to
unittest: the stub `omc` on PATH becomes the stub helper the hook's `__omc_title_helper` names (the conf.d copy is the
installed form, fish_integration.installed_hook, with the stub as its helper), the cases of omc's `command -s omc`
fallback become the empty helper's, and the hint names `just omc shell-integration fish disable`; every other case
and byte kept. `HOME`, `OMC_HOME` and the XDG directories are temporary; skipped where `fish` is not on PATH. Run
from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_fish_hook.py"""
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from fish_integration import installed_hook  # noqa: E402
from omc_fishpty import drive_fish  # noqa: E402
from omc_stubs import host_bin  # noqa: E402

HOOK = Path(HERE) / "omc-title.fish"
SESSION = "w0t1p0:38B11221-B7E1-4F36-8A3B-50D549172632"
UUID = "38B11221-B7E1-4F36-8A3B-50D549172632"
# Scrubbed so a test run inside iTerm2 never sees the developer's tab (spec §7).
SCRUB = (
    "ITERM_SESSION_ID", "TERM_PROGRAM", "LC_TERMINAL", "TMUX", "STY",
    "OMC_FISH_TITLE_DISABLE", "OMC_HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME",
    "HOME",
)  # fmt: skip
HINT_NO_HELPER = (
    "omc: fish title hook has no helper (__omc_title_helper is empty); "
    "`just omc shell-integration fish disable` removes the hook"
)
# Stubs run on a PATH holding only the stub dir: builtins and redirections only.
STUB_OMC = """#!/bin/sh
printf '%s\\n' "$*" >> "$OMC_TEST_LOG"
if [ "$1" = title ] && [ "$2" = apply ] && [ -r "$3" ]; then
  IFS= read -r line < "$3"
  printf 'request: %s\\n' "$line" >> "$OMC_TEST_LOG"
fi
exit 0
"""
STUB_HELPER = """#!/bin/sh
printf 'via-helper %s\\n' "$*" >> "$OMC_TEST_LOG"
exit 0
"""
# In-fish bounded wait: the helper is disowned and the pipe session ends with `exit`.
# `{sleep}` is the real sleep's resolved path: PATH holds only the stubs.
WAIT_FN = """function __wait_log --argument-names pattern count
    set -l tries 0
    while test $tries -lt 200
        if test -e "$OMC_TEST_LOG"
            if test (count (string match -r -- $pattern <$OMC_TEST_LOG)) -ge $count
                return 0
            end
        end
        set tries (math $tries + 1)
        {sleep} 0.05
    end
    echo "__wait_log: $pattern x$count not reached" >&2
    return 1
end
"""


def _tool(name, hint):
    found = shutil.which(name)
    if found is None:
        raise AssertionError(f"{name} is required for fish hook tests: {hint}")
    return found


def _init_repo(path, branch):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", branch, str(path)], check=True)
    git = ["git", "-C", str(path)]
    for key, value in (
        ("user.name", "Test"),
        ("user.email", "test@example.com"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run([*git, "config", key, value], check=True)
    (path / "file").write_text("initial\n")
    subprocess.run([*git, "add", "file"], check=True)
    subprocess.run([*git, "commit", "-qm", "initial"], check=True)
    return path


class HookShell:
    def __init__(self, tmp_path, *, helper=True):
        self.fish = _tool("fish", "brew install fish (macOS) or sudo apt-get install fish (Ubuntu)")
        git = _tool("git", "install git")
        self.tmp = tmp_path
        self.repo = _init_repo(tmp_path / "repo's space", "feature/first")
        self.stubs = tmp_path / "stubs"
        self.stubs.mkdir()
        self.omc = self.stubs / "omc"
        self.omc.write_text(STUB_OMC)
        self.omc.chmod(0o755)
        (self.stubs / "git").symlink_to(git)  # the hook runs `command git`
        (self.stubs / "mkdir").symlink_to(host_bin("mkdir"))  # and `command mkdir`
        self.config = tmp_path / "config"
        confd = self.config / "fish" / "conf.d"
        confd.mkdir(parents=True)
        self.hook = confd / "omc-title.fish"
        # The installed copy, its helper the stub; without one, the packaged hook's bytes (an empty helper).
        self.hook.write_bytes(installed_hook([str(self.omc)]) if helper else HOOK.read_bytes())
        self.user_config = self.config / "fish" / "config.fish"
        self.user_config.write_text(
            'echo USER_CONFIG >> "$OMC_TEST_LOG"\nfunction fish_title; echo USER_TITLE; end\n'
        )
        self.helpers = tmp_path / "helpers.fish"
        self.sleep = host_bin("sleep")
        self.helpers.write_text(WAIT_FN.format(sleep=self.sleep))
        self.omc_home = tmp_path / "omc home"
        self.log = tmp_path / "omc.log"
        (tmp_path / "home").mkdir()
        # fish's own interactive init runs a bare `mkdir -p …/fish/generated_completions`
        # (fish 4: $XDG_CACHE_HOME, fish 3.7: $XDG_DATA_HOME) unless it already exists; on the
        # restricted PATH that is "fish: Unknown command: mkdir" on stderr. Pre-create both.
        for base in ("cache", "data"):
            (tmp_path / base / "fish" / "generated_completions").mkdir(parents=True)
        # The same for the host's system config: NixOS's /etc/fish/config.fish runs `fenv`, whose bash ends in a bare
        # `env -0` ("env: command not found" on stderr). A silent `env` keeps it quiet and imports nothing, so the
        # PATH stays the stub dir; the hook never runs `env`.
        (self.stubs / "env").write_text("#!/bin/sh\nexit 0\n")
        (self.stubs / "env").chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if k not in SCRUB}
        self.env.update(
            HOME=str(tmp_path / "home"),
            PATH=str(self.stubs),
            XDG_CONFIG_HOME=str(self.config),
            XDG_DATA_HOME=str(tmp_path / "data"),
            XDG_CACHE_HOME=str(tmp_path / "cache"),
            OMC_HOME=str(self.omc_home),
            OMC_TEST_LOG=str(self.log),
            ITERM_SESSION_ID=SESSION,
            TERM_PROGRAM="iTerm.app",
        )

    def run(self, script, *, env=None, cwd=None, timeout=25):
        merged = {**self.env, **(env or {})}
        merged = {k: v for k, v in merged.items() if v is not None}
        body = f"source {shlex.quote(str(self.helpers))}; {script}; exit"
        return subprocess.run(
            [self.fish, "-i", "-C", body],
            cwd=cwd or self.repo,
            env=merged,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def lines(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def requests(self):
        return [line.removeprefix("request: ") for line in self.lines() if line.startswith("request: ")]

    def applies(self):
        return [line for line in self.lines() if line.startswith("title apply ")]


@unittest.skipUnless(shutil.which("fish"), "fish is not on PATH")
class FishHookTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)

    def shell(self, name="sh", **kwargs):
        path = self.tmp_path / name
        path.mkdir()
        return HookShell(path, **kwargs)

    def test_branch_detached_outside_branch_yields_set_nothing_release_set(self):
        sh = self.shell()
        proc = sh.run(
            "emit fish_prompt; __wait_log '^request:' 1; "
            "git switch --detach -q; emit fish_prompt; "
            "cd /; emit fish_prompt; __wait_log '^request:' 2; "
            f"cd {shlex.quote(str(sh.repo))}; emit fish_prompt; __wait_log '^request:' 3"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(sh.lines()[0], "USER_CONFIG")
        self.assertEqual(sh.requests(), ["set feature/first", "release", "set feature/first"])
        self.assertEqual(len(sh.applies()), 3)
        files = list((sh.omc_home / "title-request").iterdir())
        self.assertTrue(len(files) == 1 and files[0].name.startswith(f"{UUID}-"), files)
        self.assertEqual(files[0].read_text(), "set feature/first\n")

    def test_detached_start_without_known_branch_releases_then_pins(self):
        sh = self.shell()
        subprocess.run(["git", "-C", str(sh.repo), "switch", "--detach", "-q"], check=True)
        proc = sh.run(
            "emit fish_prompt; __wait_log '^request:' 1; "
            "git switch -q feature/first; emit fish_prompt; __wait_log '^request:' 2"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(sh.requests(), ["release", "set feature/first"])

    def test_rapid_branch_changes_keep_one_request_file_holding_the_latest(self):
        sh = self.shell()
        proc = sh.run(
            "emit fish_prompt; git switch -qc feature/second; emit fish_prompt; "
            "git switch -qc feature/third; emit fish_prompt; __wait_log 'title apply' 3"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        applies = sh.applies()
        self.assertEqual(len(applies), 3)
        paths = {line.split(" ", 2)[2] for line in applies}
        self.assertEqual(len(paths), 1)  # the same <uuid>-<pid> file every time
        request = Path(paths.pop())
        self.assertEqual(request.parent, sh.omc_home / "title-request")
        self.assertTrue(request.name.startswith(f"{UUID}-"))
        self.assertEqual(request.read_text(), "set feature/third\n")

    def test_special_characters_stay_literal(self):
        sh = self.shell()
        proc = sh.run("git switch -qc 'feature/cost$USD(parent)'; emit fish_prompt; __wait_log '^request:' 1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(sh.requests(), ["set feature/cost$USD(parent)"])

    def test_directory_change_to_another_repository_pins_its_branch(self):
        sh = self.shell()
        other = _init_repo(sh.tmp / "other repo", "feature/elsewhere")
        proc = sh.run(
            "emit fish_prompt; __wait_log '^request:' 1; "
            f"cd {shlex.quote(str(other))}; __wait_log '^request:' 2"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(sh.requests(), ["set feature/first", "set feature/elsewhere"])

    def test_worktree_change_with_unchanged_branch_name_still_remembers_the_new_key(self):
        # repoA/main -> repoB/main dispatches nothing (same title), yet B's key must be recorded:
        # detaching in B then pins `main` instead of releasing.
        sh = self.shell()
        repo_a = _init_repo(sh.tmp / "repo a", "main")
        repo_b = _init_repo(sh.tmp / "repo b", "main")
        proc = sh.run(
            "emit fish_prompt; __wait_log '^request:' 1; "
            f"cd {shlex.quote(str(repo_b))}; emit fish_prompt; "
            "git switch --detach -q; emit fish_prompt; "
            "git switch -qc other; emit fish_prompt; __wait_log '^request: set other' 1",
            cwd=repo_a,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(sh.requests(), ["set main", "set other"])
        self.assertEqual(len(sh.applies()), 2)

    def test_user_fish_title_and_config_untouched_one_handler_after_resourcing(self):
        sh = self.shell()
        before = sh.user_config.read_bytes()
        hook = shlex.quote(str(sh.hook))
        proc = sh.run(
            f"source {hook}; source {hook}; emit fish_prompt; __wait_log '^request:' 1; "
            "emit fish_prompt; fish_title; functions --handlers"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(sh.requests(), ["set feature/first"])  # one dispatch despite three sourcings
        self.assertIn("USER_TITLE", proc.stdout)
        self.assertEqual(sh.user_config.read_bytes(), before)
        for handler in (
            "fish_prompt __omc_title_prompt",
            "fish_preexec __omc_title_preexec",
            "PWD __omc_title_pwd",
        ):
            self.assertEqual(proc.stdout.count(handler), 1, proc.stdout)
        self.assertNotIn("fish_title", HOOK.read_text())  # the hook never defines or replaces fish_title

    def test_inert_shells_record_nothing(self):
        for name, env in (
            ("not-iterm", {"TERM_PROGRAM": None, "LC_TERMINAL": None}),
            ("tmux", {"TMUX": "/tmp/tmux-501/default,1,0"}),
            ("screen", {"STY": "1234.pts-0.host"}),
            ("bad-session", {"ITERM_SESSION_ID": "not-a-session"}),
            ("bad-prefix", {"ITERM_SESSION_ID": f"unrelated:{UUID}"}),
            ("disabled", {"OMC_FISH_TITLE_DISABLE": "1"}),
        ):
            with self.subTest(name):
                sh = self.shell(name)
                proc = sh.run(
                    "emit fish_prompt; git switch -qc feature/second; emit fish_prompt; "
                    f"cd /; emit fish_prompt; {sh.sleep} 0.3; functions --handlers",
                    env=env,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stderr, "")
                self.assertEqual(sh.lines(), ["USER_CONFIG"])
                registered = "__omc_title_prompt" in proc.stdout
                self.assertEqual(registered, env.get("OMC_FISH_TITLE_DISABLE") == "1")  # disabled: armed but silent

    def test_lc_terminal_alone_activates(self):
        sh = self.shell()
        proc = sh.run("emit fish_prompt; __wait_log '^request:' 1", env={"TERM_PROGRAM": None, "LC_TERMINAL": "iTerm2"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(sh.requests(), ["set feature/first"])

    def test_failure_marker_hints_once_and_retries_once_per_failure(self):
        sh = self.shell()
        marker = sh.omc_home / "title-failed" / UUID
        marker.parent.mkdir(parents=True)
        first = "omc: iTerm2 tab title update failed: worker exit 1 (retry: omc title set -- <branch>)"
        marker.write_text(f"{first}\nat earlier\n")
        old = time.time() - 120  # `path mtime` is whole seconds: make the rewrite below strictly newer
        os.utime(marker, (old, old))
        second = "omc: iTerm2 tab title update failed: timed out after 5s (retry: omc title set -- <branch>)"
        proc = sh.run(
            "emit fish_prompt; __wait_log '^request:' 1; emit fish_prompt; emit fish_prompt; "
            f"echo {shlex.quote(second)} > {shlex.quote(str(marker))}; "
            f"emit fish_prompt; __wait_log '^request:' 2; emit fish_prompt; {sh.sleep} 0.3"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr.splitlines(), [first, second])
        self.assertEqual(sh.requests(), ["set feature/first", "set feature/first"])

    def test_empty_helper_hints_once_and_records_nothing(self):
        sh = self.shell(helper=False)
        proc = sh.run("emit fish_prompt; emit fish_prompt; git switch -qc feature/second; emit fish_prompt")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr.splitlines(), [HINT_NO_HELPER])
        self.assertEqual(sh.lines(), ["USER_CONFIG"])

    def test_helper_set_later_is_picked_up(self):
        sh = self.shell(helper=False)
        proc = sh.run(
            f"emit fish_prompt; set -g __omc_title_helper {shlex.quote(str(sh.omc))}; "
            "emit fish_prompt; __wait_log '^request:' 1"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr.splitlines(), [HINT_NO_HELPER])
        self.assertEqual(sh.requests(), ["set feature/first"])

    def test_missing_git_changes_nothing(self):
        sh = self.shell()
        (sh.stubs / "git").unlink()
        proc = sh.run(f"emit fish_prompt; emit fish_prompt; {sh.sleep} 0.2")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(sh.lines(), ["USER_CONFIG"])

    def test_request_dir_is_made_with_the_mkdir_on_path(self):
        # Like git and omc, mkdir resolves through PATH: hosts such as NixOS have no /bin/mkdir.
        sh = self.shell()
        made = sh.tmp / "mkdir.calls"
        (sh.stubs / "mkdir").unlink()
        (sh.stubs / "mkdir").write_text(
            f'#!/bin/sh\nprintf "%s\\n" "$*" >> {shlex.quote(str(made))}\n'
            f'exec {shlex.quote(host_bin("mkdir"))} "$@"\n'
        )
        (sh.stubs / "mkdir").chmod(0o755)
        proc = sh.run("emit fish_prompt; __wait_log '^request:' 1")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(made.read_text(), f"-p {sh.omc_home / 'title-request'}\n")
        self.assertEqual(sh.requests(), ["set feature/first"])

    def test_missing_mkdir_changes_nothing(self):
        sh = self.shell()
        (sh.stubs / "mkdir").unlink()
        proc = sh.run(f"emit fish_prompt; emit fish_prompt; {sh.sleep} 0.2")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(sh.lines(), ["USER_CONFIG"])

    def test_preset_helper_variable_wins_over_the_installed_one(self):
        sh = self.shell()
        helper = sh.tmp / "helper dir" / "python"
        helper.parent.mkdir()
        helper.write_text(STUB_HELPER)
        helper.chmod(0o755)
        proc = sh.run(
            f"set -g __omc_title_helper {shlex.quote(str(helper))} -m omc; "
            f"source {shlex.quote(str(HOOK))}; emit fish_prompt; __wait_log via-helper 1"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = sh.lines()
        self.assertTrue(len(lines) == 2 and lines[1].startswith("via-helper -m omc title apply "), lines)
        self.assertEqual(sh.applies(), [])  # the conf.d copy's helper was never used

    def test_pipestatus_survives_a_prompt_handler_that_dispatches(self):
        sh = self.shell()
        prompt_log = sh.tmp / "prompts"
        sh.user_config.write_text(
            "set -g fish_greeting\n"
            'function fish_prompt; echo "P:$pipestatus" >> "$OMC_PROMPT_LOG"; printf "READY> "; end\n'
        )
        env = {**sh.env, "OMC_PROMPT_LOG": str(prompt_log), "TERM": "dumb"}
        drive_fish(
            sh.fish,
            env,
            [
                # Wait for the first request: the hook rewrites the file before a slow stub reads it.
                f"source {shlex.quote(str(sh.helpers))}; __wait_log '^request:' 1",
                "git switch -qc feature/second; true | false | true",
                "__wait_log '^request:' 2",
            ],
            prompt_log,
            cwd=sh.repo,
        )
        prompts = prompt_log.read_text().splitlines()
        self.assertEqual(prompts[2], "P:0 1 0", prompts)  # the prompt right after the pipeline
        self.assertEqual(sh.requests(), ["set feature/first", "set feature/second"])


if __name__ == "__main__":
    unittest.main()
