"""The launch shells: `design.py` ends in `Shell.exec_interactive`, `os.chdir` to the worktree,
then `execvp` of an interactive shell chosen by `$SHELL`'s basename (fish, zsh, bash, then sh), which runs Claude as
its startup command; when Claude exits the owner is in that shell in the worktree, and when the shell exits the herdr
exit report fires. Ported from omc 0.1.54's `src/omc/shells/{base,registry,fish,zsh,bash}.py` in one module, the same
behavior and bytes; rewritten only: the hooked fish path's helper, `just --justfile <checkout>/justfile omc`
(fish_integration.title_helper; omc had `<its python> -m omc`), and the startup argv, `startup_argv`, built as omc's
`providers/claude.py:149-158` and wrapped as `session.py:59-60`. The standard library only.
"""
from __future__ import annotations

import os
import shlex
import sys
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from fish_integration import fish_hook_path, title_helper  # noqa: E402
from herdr import osc7_report  # noqa: E402

TMPDIR_PLACEHOLDER = "{omc_tmpdir}"


def startup_argv(
    *, session_name: str, model: str, seed: str, effort: str = "", direnv: bool = False, extra: tuple[str, ...] = ()
) -> list[str]:
    """`claude -n <session> [--model <model>] [--effort <effort>] [<extra>…] <seed>`, under `direnv exec .` when
    asked."""
    argv = ["claude"]
    if session_name:
        argv += ["-n", session_name]  # resumable later via `claude --resume <name>`
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--effort", effort]
    argv += extra
    argv.append(seed)
    if direnv:
        argv = ["direnv", "exec", ".", *argv]
    return argv


class Shell(ABC):
    """An interactive shell we can hand off to inside a worktree.

    build_invocation is the pure unit-tested seam: (argv, extra_files) where
    extra_files maps a RELATIVE filename -> contents for init files; argv refers
    to them via TMPDIR_PLACEHOLDER. exec_interactive performs all side effects
    (mkdtemp, write, substitute, chdir, execvp) and is E2E-only.
    """

    name: str

    @classmethod
    @abstractmethod
    def detect(cls, env: Mapping[str, str]) -> bool: ...

    @abstractmethod
    def build_invocation(
        self,
        *,
        cwd: str,
        title: str,
        startup_argv: list[str],
        title_seq: str,
        title_argv: list[str] | None = None,
        origin_cwd: str | None = None,
        fixed_title: bool = False,
    ) -> tuple[list[str], dict[str, str]]:
        """[fixed_title]: the title stays [title] for the shell's life, never replaced by the git branch."""

    def exec_env_overrides(self, tmpdir: str | None) -> dict[str, str]:
        return {}

    def exec_interactive(
        self,
        *,
        cwd: str,
        title: str,
        startup_argv: list[str],
        title_seq: str,
        title_argv: list[str] | None = None,
        origin_cwd: str | None = None,
        fixed_title: bool = False,
    ) -> None:  # pragma: no cover - effectful exec, E2E-verified
        argv, extra_files = self.build_invocation(
            cwd=cwd,
            title=title,
            startup_argv=startup_argv,
            title_seq=title_seq,
            title_argv=title_argv,
            origin_cwd=origin_cwd,
            fixed_title=fixed_title,
        )
        tmpdir: str | None = None
        if extra_files:
            tmpdir = tempfile.mkdtemp(prefix=f"omc-{self.name}-")
            for relname, contents in extra_files.items():
                Path(tmpdir, relname).write_text(contents)
            argv = [arg.replace(TMPDIR_PLACEHOLDER, tmpdir) for arg in argv]
        os.environ.update(self.exec_env_overrides(tmpdir))
        os.chdir(cwd)
        os.execvp(argv[0], argv)  # noqa: S606 - argv is array-based, no shell


def joined_startup(startup_argv: list[str]) -> str:
    return shlex.join(startup_argv) if startup_argv else ""


def joined_title(title_argv: list[str] | None, title: str) -> str:
    """A shell command that attempts the generic title operation once."""
    return shlex.join([*title_argv, title]) if title_argv else ""


# ------------------------------------------------------------------------------------------------------------- fish
# The spec §2 activation predicate plus the per-session opt-out, evaluated by fish at
# startup. The builder itself never reads the environment (pure; --dry-run identical
# in every terminal). Keep in sync with omc-title.fish's guards.
_ITERM2_HOOK_PREDICATE = (
    "status is-interactive; and string match -rq -- "
    "'^(w[0-9]+t[0-9]+p[0-9]+:)?[0-9A-Fa-f-]{36}$' \"$ITERM_SESSION_ID\"; "
    'and begin; test "$TERM_PROGRAM" = iTerm.app; or test "$LC_TERMINAL" = iTerm2; end; '
    'and not set -q TMUX; and not set -q STY; and test "$OMC_FISH_TITLE_DISABLE" != 1'
)


def _fish_herdr_block(origin_cwd: str | None) -> str:
    """Spec 2026-11-14 §4.2: host-less OSC 7 reports for herdr's sidebar, guarded in fish.

    Reports $PWD now and on every later cd, and the origin when the shell exits.
    """
    parts = [
        'if test "$TERM_PROGRAM" = herdr',
        "function __omc_herdr_report; "
        "printf '\\e]7;file://%s\\a' (string escape --style=url -- $argv[1]); end",
        "__omc_herdr_report $PWD",
        "function __omc_herdr_pwd --on-variable PWD; __omc_herdr_report $PWD; end",
    ]
    if origin_cwd:
        parts.append(
            "function __omc_herdr_exit --on-event fish_exit; "
            f"__omc_herdr_report {shlex.quote(origin_cwd)}; end"
        )
    return "; ".join([*parts, "end"])


class FishShell(Shell):
    name = "fish"

    @classmethod
    def detect(cls, env: Mapping[str, str]) -> bool:
        return os.path.basename(env.get("SHELL", "")) == "fish"

    def build_invocation(
        self, *, cwd, title, startup_argv, title_seq, title_argv=None, origin_cwd=None, fixed_title=False
    ):
        if title_argv:
            helper = shlex.join(title_argv)
            inline = [
                f"set -g __omc_desired_title {shlex.quote(title)}",
                "set -g __omc_last_attempt ''",
                'function fish_title; printf "%s\\n" "$__omc_desired_title"; end',
                "function __omc_refresh_title",
                "set -l saved_status $status",
                *(
                    ()
                    if fixed_title
                    else (
                        "set -l branch (command git branch --show-current 2>/dev/null)",
                        'if test $status -eq 0; and test -n "$branch"; '
                        'set -g __omc_desired_title "$branch"; end',
                    )
                ),
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
                "__omc_refresh_title",  # -C startup need not emit fish_preexec.
            ]
            # In iTerm2 the packaged hook (sourced here even when conf.d never got it or
            # was disabled) owns the title; the explicit refresh is the shell's first,
            # so the cd's PWD event is ignored and the first prompt after the provider
            # exits is a no-op on an unchanged branch (spec §6).
            hooked = [
                f"set -g __omc_title_helper {shlex.join(title_helper())}",
                f"source {shlex.quote(str(fish_hook_path()))}",
                f"cd {shlex.quote(cwd)}",
                "__omc_title_refresh",
            ]
            parts = [f"if {_ITERM2_HOOK_PREDICATE}", *hooked, "else", *inline, "end"]
            if fixed_title:
                # The switch the iTerm2 hook and the predicate both honour: the hook leaves this tab alone and
                # the inline path, which keeps the given title, runs there too.
                parts.insert(0, "set -g OMC_FISH_TITLE_DISABLE 1")
        else:
            parts = [
                f"function fish_title; echo {shlex.quote(title)}; end",
                f"cd {shlex.quote(cwd)}",
                f"printf '%s' {shlex.quote(title_seq)}",
            ]
        parts.append(_fish_herdr_block(origin_cwd))
        startup = joined_startup(startup_argv)
        if startup:
            parts.append(startup)
        return ["fish", "-i", "-C", "; ".join(parts)], {}


# -------------------------------------------------------------------------------------------------------------- zsh
def _zsh_herdr_block(cwd: str, origin_cwd: str | None) -> list[str]:
    """Spec 2026-11-14 §4.2: host-less OSC 7 reports for herdr's sidebar, guarded in zsh.

    Reports the worktree now and, appended to the user's zshexit hooks, the origin on exit.
    """
    lines = [
        'if [ "${TERM_PROGRAM-}" = herdr ]; then',
        f"printf '%s' {shlex.quote(osc7_report(cwd))}",
    ]
    if origin_cwd:
        lines += [
            f"__omc_herdr_exit() {{ printf '%s' {shlex.quote(osc7_report(origin_cwd))} }}",
            "zshexit_functions+=(__omc_herdr_exit)",
        ]
    return [*lines, "fi"]


class ZshShell(Shell):
    name = "zsh"

    @classmethod
    def detect(cls, env: Mapping[str, str]) -> bool:
        return os.path.basename(env.get("SHELL", "")) == "zsh"

    def build_invocation(
        self, *, cwd, title, startup_argv, title_seq, title_argv=None, origin_cwd=None, fixed_title=False
    ):
        lines = [
            '[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc"',
            f"precmd() {{ printf '%s' {shlex.quote(title_seq)} }}",
            f"cd {shlex.quote(cwd)}",
            # precmd only fires at the first prompt — AFTER the startup session
            # exits — so emit the title once, up front, before the session runs.
            f"printf '%s' {shlex.quote(title_seq)}",
        ]
        title_command = joined_title(title_argv, title)
        if title_command:
            lines.append(f"{title_command} || :")
        lines += _zsh_herdr_block(cwd, origin_cwd)
        startup = joined_startup(startup_argv)
        if startup:
            lines.append(startup)
        return ["zsh", "-i"], {".zshrc": "\n".join(lines) + "\n"}

    def exec_env_overrides(self, tmpdir):
        return {"ZDOTDIR": tmpdir} if tmpdir else {}


# ------------------------------------------------------------------------------------------------------------- bash
_RC_NAME = "rc.bash"


def _bash_herdr_block(cwd: str, origin_cwd: str | None) -> list[str]:
    """Spec 2026-11-14 §4.2: host-less OSC 7 reports for herdr's sidebar, guarded in bash.

    Reports the worktree now and the origin from an EXIT trap that chains the user's
    own EXIT trap (word 2 of `trap -p EXIT`, re-split by eval) after the report.
    """
    lines = [
        'if [ "${TERM_PROGRAM-}" = herdr ]; then',
        f"printf '%s' {shlex.quote(osc7_report(cwd))}",
    ]
    if origin_cwd:
        lines += [
            "__omc_herdr_prev_exit=$(trap -p EXIT)",
            'eval "__omc_herdr_prev_exit=(${__omc_herdr_prev_exit})"',
            f"trap -- \"printf '%s' {shlex.quote(osc7_report(origin_cwd))}; "
            '${__omc_herdr_prev_exit[2]-}" EXIT',
        ]
    return [*lines, "fi"]


class BashShell(Shell):
    name = "bash"

    @classmethod
    def detect(cls, env: Mapping[str, str]) -> bool:
        return os.path.basename(env.get("SHELL", "")) == "bash"

    def build_invocation(
        self, *, cwd, title, startup_argv, title_seq, title_argv=None, origin_cwd=None, fixed_title=False
    ):
        rcfile = f"{TMPDIR_PLACEHOLDER}/{_RC_NAME}"
        lines = [
            '[ -f "$HOME/.bashrc" ] && source "$HOME/.bashrc"',
            f"PROMPT_COMMAND={shlex.quote(f'printf %s {shlex.quote(title_seq)}')}",
            f"cd {shlex.quote(cwd)}",
            # PROMPT_COMMAND only fires at the first prompt — AFTER the startup
            # session exits — so emit the title once, up front, before it runs.
            f"printf '%s' {shlex.quote(title_seq)}",
        ]
        title_command = joined_title(title_argv, title)
        if title_command:
            lines.append(f"{title_command} || :")
        lines += _bash_herdr_block(cwd, origin_cwd)
        startup = joined_startup(startup_argv)
        if startup:
            lines.append(startup)
        return ["bash", "--rcfile", rcfile, "-i"], {_RC_NAME: "\n".join(lines) + "\n"}


# --------------------------------------------------------------------------------------------------------------- sh
class ShShell(Shell):
    """POSIX-sh fallback: no portable prompt hook; just run the startup command."""

    name = "sh"

    @classmethod
    def detect(cls, env: Mapping[str, str]) -> bool:
        return True

    def build_invocation(
        self, *, cwd, title, startup_argv, title_seq, title_argv=None, origin_cwd=None, fixed_title=False
    ):
        # No portable exit hook in plain sh: origin_cwd is accepted and ignored (spec §4.3).
        startup = joined_startup(startup_argv)
        title_command = joined_title(title_argv, title)
        command = (
            f"{title_command} || :; {startup or 'exec sh'}"
            if title_command
            else startup or "exec sh"
        )
        return ["sh", "-c", command], {}


# --------------------------------------------------------------------------------------------------------- registry
_SHELLS: tuple[type[Shell], ...] = (FishShell, ZshShell, BashShell)


def detect_shell(env: Mapping[str, str]) -> Shell:
    for cls in _SHELLS:
        if cls.detect(env):
            return cls()
    return ShShell()
