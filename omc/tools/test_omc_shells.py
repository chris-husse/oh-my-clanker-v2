"""Tests of omc/tools/shells.py, the launch shells: omc 0.1.54's `tests/unit/test_shells.py`, rewritten to
unittest, `_inline_else` and every expected fish string kept byte for byte. Rewritten only: the hooked path's helper
is `just --justfile <checkout>/justfile omc` (fish_integration.title_helper, where omc had `<its python> -m omc`), the
title command `python3 -I <root>/omc/tools/terminal_title.py` (where omc had `python -m omc.terminal_title`), the
startup argv `claude -n <slug> --model <model> '/brainstorm .cache/omc/brief.md'` and the direnv case built by
`shells.startup_argv` (omc built them in `session_plan`, which design.py replaces). `HOME` is a temporary
directory for the real bash sessions. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_shells.py"""
import os
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
from fish_integration import fish_hook_path, title_helper  # noqa: E402
from herdr import osc7_report  # noqa: E402
from shells import TMPDIR_PLACEHOLDER, FishShell, detect_shell, startup_argv  # noqa: E402
from terminal_title import terminal_title_argv  # noqa: E402
from terminals import detect_terminal  # noqa: E402

SEED = "/brainstorm .cache/omc/brief.md"
ARGS = dict(
    cwd="/w/tree",
    title="proj-1-fix",
    startup_argv=["claude", "-n", "proj-1-fix", "--model", "opus", SEED],
    title_seq="\033]0;proj-1-fix\007",
)


def fish_herdr(origin=None):
    parts = [
        'if test "$TERM_PROGRAM" = herdr',
        "function __omc_herdr_report; "
        "printf '\\e]7;file://%s\\a' (string escape --style=url -- $argv[1]); end",
        "__omc_herdr_report $PWD",
        "function __omc_herdr_pwd --on-variable PWD; __omc_herdr_report $PWD; end",
    ]
    if origin:
        parts.append(
            f"function __omc_herdr_exit --on-event fish_exit; "
            f"__omc_herdr_report {shlex.quote(origin)}; end"
        )
    return "; ".join([*parts, "end"])


def zsh_herdr(cwd, origin=None):
    lines = [
        'if [ "${TERM_PROGRAM-}" = herdr ]; then',
        f"printf '%s' {shlex.quote(osc7_report(cwd))}",
    ]
    if origin:
        lines += [
            f"__omc_herdr_exit() {{ printf '%s' {shlex.quote(osc7_report(origin))} }}",
            "zshexit_functions+=(__omc_herdr_exit)",
        ]
    return "\n".join([*lines, "fi"])


def bash_herdr(cwd, origin=None):
    lines = [
        'if [ "${TERM_PROGRAM-}" = herdr ]; then',
        f"printf '%s' {shlex.quote(osc7_report(cwd))}",
    ]
    if origin:
        lines += [
            "__omc_herdr_prev_exit=$(trap -p EXIT)",
            'eval "__omc_herdr_prev_exit=(${__omc_herdr_prev_exit})"',
            f"trap -- \"printf '%s' {shlex.quote(osc7_report(origin))}; "
            '${__omc_herdr_prev_exit[2]-}" EXIT',
        ]
    return "\n".join([*lines, "fi"])


FISH_TITLE_ARGV = ["python3", "-I", "/r/omc/tools/terminal_title.py"]


def _inline_else(helper, title, cwd):
    """Today's inline fish title code, frozen byte for byte (spec §6)."""
    return "; ".join(
        [
            f"set -g __omc_desired_title {shlex.quote(title)}",
            "set -g __omc_last_attempt ''",
            'function fish_title; printf "%s\\n" "$__omc_desired_title"; end',
            "function __omc_refresh_title",
            "set -l saved_status $status",
            "set -l branch (command git branch --show-current 2>/dev/null)",
            'if test $status -eq 0; and test -n "$branch"; '
            'set -g __omc_desired_title "$branch"; end',
            'if test "$__omc_last_attempt" != "$__omc_desired_title"',
            'set -g __omc_last_attempt "$__omc_desired_title"',
            f'{helper} "$__omc_desired_title"; or true',
            "end",
            "return $saved_status",
            "end",
            "function __omc_title_preexec --on-event fish_preexec; __omc_refresh_title; end",
            "function __omc_title_prompt --on-event fish_prompt; __omc_refresh_title; end",
            "function __omc_title_pwd --on-variable PWD; __omc_refresh_title; end",
            f"cd {shlex.quote(cwd)}",
            "__omc_refresh_title",
        ]
    )


class _Exec:
    """os.chdir and os.execvp recorded instead of run (omc's monkeypatch of base.os)."""

    def __init__(self):
        self.seen = []

    def __enter__(self):
        self._patches = [
            mock.patch.object(shells.os, "chdir", lambda path: self.seen.append(("cd", path))),
            mock.patch.object(
                shells.os, "execvp", lambda program, argv: self.seen.append(("exec", argv))
            ),
        ]
        for patch in self._patches:
            patch.start()
        return self

    def __exit__(self, *exc):
        for patch in reversed(self._patches):
            patch.stop()

    def executed(self):
        return [argv for kind, argv in self.seen if kind == "exec"]


class StartupArgvTest(unittest.TestCase):
    """The startup command: omc's `providers/claude.py:149-158`, wrapped as `session.py:59-60`."""

    def test_the_startup_argv_with_a_model(self):
        self.assertEqual(
            startup_argv(session_name="feature/x", model="opus", seed=SEED),
            ["claude", "-n", "feature/x", "--model", "opus", "/brainstorm .cache/omc/brief.md"],
        )

    def test_the_startup_argv_under_direnv(self):
        self.assertEqual(
            startup_argv(session_name="x", model="opus", seed=SEED, direnv=True),
            ["direnv", "exec", ".", "claude", "-n", "x", "--model", "opus", SEED],
        )

    def test_an_empty_model_leaves_the_model_out(self):
        self.assertEqual(
            startup_argv(session_name="x", model="", seed=SEED), ["claude", "-n", "x", SEED]
        )
        self.assertEqual(
            startup_argv(session_name="x", model="", seed=SEED, direnv=True),
            ["direnv", "exec", ".", "claude", "-n", "x", SEED],
        )


class ShellsTest(unittest.TestCase):
    def test_detect_by_shell_env(self):
        self.assertEqual(detect_shell({"SHELL": "/usr/bin/fish"}).name, "fish")
        self.assertEqual(detect_shell({"SHELL": "/bin/zsh"}).name, "zsh")
        self.assertEqual(detect_shell({"SHELL": "/bin/bash"}).name, "bash")
        self.assertEqual(detect_shell({}).name, "sh")

    def test_direnv_launch_follows_worktree_cd(self):
        for shell_name in ("fish", "zsh", "bash", "sh"):
            with self.subTest(shell_name=shell_name):
                env = {"HOME": "/nowhere", "PATH": "/nowhere", "SHELL": shell_name}
                session_argv = startup_argv(session_name="s", model="opus", seed=SEED, direnv=True)
                title_seq = detect_terminal(env).title_sequence("t")
                title_argv = terminal_title_argv()
                if shell_name == "fish":
                    shell_argv, _ = detect_shell(env).build_invocation(
                        cwd="/w/tree",
                        title="t",
                        startup_argv=session_argv,
                        title_seq=title_seq,
                        title_argv=title_argv,
                        origin_cwd=env.get("PWD") or None,
                    )
                    self.assertEqual(shell_argv[:3], ["fish", "-i", "-C"])
                    body = shell_argv[3]
                elif shell_name == "sh":
                    with _Exec() as run:
                        detect_shell(env).exec_interactive(
                            cwd="/w/tree",
                            title="t",
                            startup_argv=session_argv,
                            title_seq=title_seq,
                            title_argv=title_argv,
                        )
                    self.assertEqual(run.seen[0], ("cd", "/w/tree"))
                    self.assertTrue(
                        run.seen[1][1][2].endswith(
                            "direnv exec . claude -n s --model opus '/brainstorm .cache/omc/brief.md'"
                        ),
                        run.seen,
                    )
                    continue
                else:
                    _, files = detect_shell(env).build_invocation(
                        cwd="/w/tree",
                        title="t",
                        startup_argv=session_argv,
                        title_seq=title_seq,
                        title_argv=title_argv,
                    )
                    body = next(iter(files.values()))
                self.assertLess(body.index("cd /w/tree"), body.index("direnv exec . claude"))

    def test_fish_invocation_inline(self):
        argv, files = detect_shell({"SHELL": "fish"}).build_invocation(**ARGS)
        self.assertEqual(argv[:3], ["fish", "-i", "-C"])
        body = argv[3]
        self.assertTrue("cd /w/tree" in body and "fish_title" in body)
        self.assertIn(shlex.join(ARGS["startup_argv"]), body)
        self.assertEqual(files, {})

    def test_zsh_invocation_writes_zshrc(self):
        shell = detect_shell({"SHELL": "zsh"})
        argv, files = shell.build_invocation(**ARGS)
        self.assertEqual(argv, ["zsh", "-i"])
        rc = files[".zshrc"]
        self.assertTrue('source "$HOME/.zshrc"' in rc and "cd /w/tree" in rc)
        self.assertIn(shlex.join(ARGS["startup_argv"]), rc)
        self.assertEqual(shell.exec_env_overrides("/tmp/x"), {"ZDOTDIR": "/tmp/x"})

    def test_bash_invocation_rcfile_placeholder(self):
        argv, files = detect_shell({"SHELL": "bash"}).build_invocation(**ARGS)
        self.assertTrue(argv[0] == "bash" and "--rcfile" in argv and "-i" in argv)
        self.assertTrue(any(TMPDIR_PLACEHOLDER in a for a in argv))
        self.assertIn("rc.bash", files)

    def test_sh_fallback_runs_startup(self):
        argv, files = detect_shell({}).build_invocation(**ARGS)
        self.assertEqual(argv[:2], ["sh", "-c"])
        self.assertIn(shlex.join(ARGS["startup_argv"]), argv[2])
        self.assertEqual(files, {})

    def test_zsh_and_bash_emit_title_before_startup(self):
        # The prompt hooks (precmd / PROMPT_COMMAND) only fire after the startup
        # session exits; the rc file must ALSO emit the title before the session.
        for shell_env in ({"SHELL": "zsh"}, {"SHELL": "bash"}):
            _, files = detect_shell(shell_env).build_invocation(**ARGS)
            rc = next(iter(files.values()))
            printf_at = rc.index("printf '%s' " + shlex.quote(ARGS["title_seq"]))
            startup_at = rc.index(shlex.join(ARGS["startup_argv"]))
            self.assertLess(printf_at, startup_at, f"title must precede startup in:\n{rc}")

    def test_title_helper_runs_before_startup_for_every_shell(self):
        for shell_name in ("fish", "bash", "zsh", "sh"):
            with self.subTest(shell_name=shell_name):
                argv, files = detect_shell({"SHELL": shell_name}).build_invocation(
                    **ARGS, title_argv=["/usr/bin/title-helper"]
                )
                body = (
                    argv[3]
                    if shell_name == "fish"
                    else argv[2]
                    if shell_name == "sh"
                    else next(iter(files.values()))
                )
                helper_call = (
                    '/usr/bin/title-helper "$__omc_desired_title"'
                    if shell_name == "fish"
                    else "/usr/bin/title-helper proj-1-fix"
                )
                self.assertLess(body.index(helper_call), body.index(shlex.join(ARGS["startup_argv"])))

    def test_exec_interactive_forwards_title_helper(self):
        shell = detect_shell({})
        with _Exec() as run:
            shell.exec_interactive(**ARGS, title_argv=["/usr/bin/title-helper"])
        executed = run.executed()
        self.assertTrue(executed and "/usr/bin/title-helper proj-1-fix" in executed[0][2])

    def test_fish_generated_command_is_one_if_else_around_the_hook(self):
        argv, files = detect_shell({"SHELL": "fish"}).build_invocation(
            **ARGS, title_argv=FISH_TITLE_ARGV
        )
        self.assertTrue(files == {} and argv[:3] == ["fish", "-i", "-C"])
        body = argv[3]
        startup = shlex.join(ARGS["startup_argv"])
        self.assertTrue(body.endswith("; end; " + fish_herdr() + "; " + startup), body)
        body = body.replace("; " + fish_herdr(), "", 1)
        self.assertEqual(body.count("; else; "), 1)
        if_branch, rest = body.split("; else; ", 1)
        else_branch, startup = rest.rsplit("; end; ", 1)
        self.assertEqual(startup, shlex.join(ARGS["startup_argv"]))
        predicate = if_branch.split("; set -g __omc_title_helper", 1)[0]
        self.assertEqual(
            predicate,
            "if status is-interactive; and string match -rq -- "
            "'^(w[0-9]+t[0-9]+p[0-9]+:)?[0-9A-Fa-f-]{36}$' \"$ITERM_SESSION_ID\"; "
            'and begin; test "$TERM_PROGRAM" = iTerm.app; or test "$LC_TERMINAL" = iTerm2; end; '
            'and not set -q TMUX; and not set -q STY; and test "$OMC_FISH_TITLE_DISABLE" != 1',
        )
        steps = [
            "set -g __omc_title_helper " + shlex.join(title_helper()),
            f"source {shlex.quote(str(fish_hook_path()))}",
            "cd /w/tree",
            "__omc_title_refresh",
        ]
        positions = [if_branch.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(if_branch.endswith("__omc_title_refresh"))
        self.assertEqual(
            else_branch, _inline_else(shlex.join(FISH_TITLE_ARGV), "proj-1-fix", "/w/tree")
        )
        self.assertIn(
            'python3 -I /r/omc/tools/terminal_title.py "$__omc_desired_title"', else_branch
        )

    def test_the_hooked_helper_is_the_checkouts_just_omc(self):
        root = os.path.dirname(os.path.dirname(HERE))
        argv, _ = detect_shell({"SHELL": "fish"}).build_invocation(**ARGS, title_argv=FISH_TITLE_ARGV)
        self.assertIn(
            "; set -g __omc_title_helper "
            + shlex.join(["just", "--justfile", os.path.join(root, "justfile"), "omc"])
            + "; ",
            argv[3],
        )

    def test_fish_without_title_argv_exact_text(self):
        argv, _ = detect_shell({"SHELL": "fish"}).build_invocation(**ARGS)
        self.assertTrue("; else; " not in argv[3] and "__omc_title_helper" not in argv[3])
        self.assertEqual(
            argv[3],
            "function fish_title; echo proj-1-fix; end; cd /w/tree; "
            f"printf '%s' {shlex.quote(ARGS['title_seq'])}; {fish_herdr()}; "
            f"{shlex.join(ARGS['startup_argv'])}",
        )

    def test_fish_dry_run_output_is_terminal_independent(self):
        # The builder never reads the environment: identical output whatever the terminal.
        shell = detect_shell({"SHELL": "fish"})
        first, _ = shell.build_invocation(**ARGS, title_argv=FISH_TITLE_ARGV)
        second, _ = shell.build_invocation(**ARGS, title_argv=FISH_TITLE_ARGV)
        self.assertEqual(first, second)

    def test_fish_herdr_block_sits_between_title_code_and_startup(self):
        for title_argv in (None, FISH_TITLE_ARGV):
            with self.subTest(title_argv=title_argv):
                argv, _ = detect_shell({"SHELL": "fish"}).build_invocation(
                    **ARGS, title_argv=title_argv, origin_cwd="/launch dir"
                )
                body = argv[3]
                block = fish_herdr("/launch dir")
                self.assertTrue(
                    body.index("cd /w/tree")
                    < body.index(block)
                    < body.index(shlex.join(ARGS["startup_argv"]))
                )
                if title_argv == FISH_TITLE_ARGV:
                    self.assertIn("; end; " + block + "; ", body)

    def test_fish_herdr_exit_handler_only_with_origin(self):
        argv, _ = detect_shell({"SHELL": "fish"}).build_invocation(**ARGS, origin_cwd=None)
        body = argv[3]
        self.assertTrue(fish_herdr() in body and "__omc_herdr_exit" not in body)

    def test_zsh_and_bash_herdr_block_after_cd_before_startup(self):
        for origin in (None, "/launch dir"):
            for shell_name in ("zsh", "bash"):
                with self.subTest(shell_name=shell_name, origin=origin):
                    _, files = detect_shell({"SHELL": shell_name}).build_invocation(
                        **ARGS, origin_cwd=origin
                    )
                    rc = next(iter(files.values()))
                    block = (zsh_herdr if shell_name == "zsh" else bash_herdr)("/w/tree", origin)
                    startup = shlex.join(ARGS["startup_argv"])
                    self.assertTrue(rc.index("cd /w/tree") < rc.index(block) < rc.index(startup))
                    if origin is None:
                        self.assertTrue("__omc_herdr_exit" not in rc and "trap -- " not in rc)

    def test_sh_ignores_origin_cwd(self):
        shell = detect_shell({})
        self.assertEqual(
            shell.build_invocation(**ARGS), shell.build_invocation(**ARGS, origin_cwd="/launch dir")
        )

    def test_exec_interactive_forwards_origin_cwd(self):
        with _Exec() as run:
            FishShell().exec_interactive(**ARGS, origin_cwd="/o")
        executed = run.executed()
        self.assertTrue(executed and "__omc_herdr_report /o; end" in executed[0][3])


class BashSessionTest(unittest.TestCase):
    """Real interactive bash sessions on the generated rcfile, `HOME` a temporary directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run_bash_session(
        self, tmp_path, *, wt, bashrc, startup_argv, origin_cwd, term_program=None
    ) -> subprocess.CompletedProcess:
        """Run an interactive bash on omc's generated rcfile for worktree ``wt`` and exit."""
        bash = shutil.which("bash")
        if bash is None:
            self.fail("bash is required: sudo apt-get install bash")
        home = tmp_path / "home"
        home.mkdir()
        (home / ".bashrc").write_text(bashrc)
        (home / ".hushlogin").touch()  # quiets Ubuntu's /etc/bash.bashrc sudo hint on stdout
        rcdir = tmp_path / "rc"
        rcdir.mkdir()
        argv, files = detect_shell({"SHELL": "bash"}).build_invocation(
            cwd=str(wt),
            title="t",
            startup_argv=startup_argv,
            title_seq="",
            origin_cwd=origin_cwd,
        )
        for name, contents in files.items():
            (rcdir / name).write_text(contents)
        rc = next(a for a in argv if TMPDIR_PLACEHOLDER in a).replace(TMPDIR_PLACEHOLDER, str(rcdir))
        env = {"HOME": str(home), "PATH": os.environ["PATH"]}
        if term_program is not None:
            env["TERM_PROGRAM"] = term_program
        return subprocess.run(
            [bash, "--rcfile", rc, "-i"],
            input="exit\n",
            env=env,
            capture_output=True,
            text=True,
            timeout=25,
        )

    def test_bash_exit_report_keeps_user_exit_trap(self):
        cases = [
            ("no-user-trap", "", ""),
            ("user-exit-trap", 'trap -- "echo USER_BYE" EXIT\n', "USER_BYE\n"),
            ("set-u-no-trap", "set -u\n", ""),
        ]
        for case_id, bashrc, user_tail in cases:
            with self.subTest(case_id), tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                wt = tmp_path / "wt dir"
                wt.mkdir()
                launch = tmp_path / "launch dir"
                launch.mkdir()
                proc = self._run_bash_session(
                    tmp_path,
                    wt=wt,
                    bashrc=bashrc,
                    startup_argv=["true"],
                    origin_cwd=str(launch),
                    term_program="herdr",
                )
                self.assertEqual(
                    proc.stdout, osc7_report(str(wt)) + osc7_report(str(launch)) + user_tail
                )
                self.assertNotIn("unbound variable", proc.stderr)

    def test_bash_herdr_guard_tolerates_set_u_without_term_program(self):
        tmp_path = self.tmp_path
        wt = tmp_path / "wt"
        wt.mkdir()
        proc = self._run_bash_session(
            tmp_path,
            wt=wt,
            bashrc="set -u\n",
            startup_argv=["printf", "STARTED\\n"],
            origin_cwd=str(tmp_path),
        )
        self.assertNotIn("unbound variable", proc.stderr)
        self.assertNotIn("\x1b]7;", proc.stdout)
        self.assertEqual(proc.stdout, "STARTED\n")


if __name__ == "__main__":
    unittest.main()
