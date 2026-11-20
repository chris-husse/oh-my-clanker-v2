"""Terminal title adapters: iTerm2 sets an explicit API title; others use OSC 0.
Ported from omc 0.1.54's `src/omc/terminals.py`: the same behavior and bytes, the worker's argv rewritten
(`worker_argv`, here: omc built it in `iterm2_title.py`, which `title.py` and this module share; the worker itself is
`omc/tools/iterm2_title.py`, run through the project's `uv` interpreter in its own process, so a missing `iterm2`
package is one more failure that falls back to OSC 0).

OSC 0 remains the best-effort fallback when the iTerm2 API cannot pin a tab. The standard library only."""
from __future__ import annotations

import os
import re
import sys
import uuid
from abc import ABC, abstractmethod
from collections.abc import Mapping

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def worker_argv(session_id: str, *, title: str | None = None, release: bool = False) -> list[str]:
    """The iTerm2 API worker's argv: `omc/tools/iterm2_title.py` in the uv project omc/, under the checkout's venv,
    from any directory."""
    argv = ["env", f"UV_PROJECT_ENVIRONMENT={ROOT}/.cache/venv", "uv", "run", "--frozen", "--project",
            os.path.join(ROOT, "omc"), "python", "-I", os.path.join(HERE, "iterm2_title.py"), "--session-id", session_id]
    if release:
        return [*argv, "--release"]
    if title is None:
        raise ValueError("worker_argv needs a title or release=True")
    return [*argv, "--", title]


class Terminal(ABC):
    name: str

    @classmethod
    @abstractmethod
    def detect(cls, env: Mapping[str, str]) -> bool: ...

    @abstractmethod
    def title_sequence(self, title: str) -> str: ...

    @abstractmethod
    def set_title(self, ctx, title: str) -> bool: ...


class OscTerminal(Terminal):
    name = "osc"

    @classmethod
    def detect(cls, env):
        return True

    def title_sequence(self, title: str) -> str:
        return f"\033]0;{title}\007"

    def set_title(self, ctx, title: str) -> bool:
        print(self.title_sequence(title), end="", flush=True)
        return True


_SESSION_PREFIX = re.compile(r"w\d+t\d+p\d+")


def iterm2_session_id(env: Mapping[str, str]) -> str | None:
    """The bare session UUID from ITERM_SESSION_ID (`w0t1p0:<uuid>` or `<uuid>`), else None.

    UUID round trip plus the optional window/tab/pane prefix: the value names the
    caller's own tab to the API worker, so anything looser is refused.
    """
    raw = env.get("ITERM_SESSION_ID", "")
    prefix, separator, candidate = raw.partition(":")
    if not separator:
        candidate = raw
    elif _SESSION_PREFIX.fullmatch(prefix) is None:
        return None
    try:
        parsed = uuid.UUID(candidate)
    except ValueError:
        return None
    return candidate if str(parsed).lower() == candidate.lower() else None


class Iterm2Terminal(OscTerminal):
    name = "iterm2"

    @classmethod
    def detect(cls, env):
        return env.get("TERM_PROGRAM") == "iTerm.app" or env.get("LC_TERMINAL") == "iTerm2"

    def set_title(self, ctx, title: str) -> bool:
        session_id = iterm2_session_id(ctx.env)
        if session_id is not None:
            try:
                result = ctx.run_bounded(worker_argv(session_id, title=title), timeout=5)
                if result.returncode == 0:
                    return True
            except (TimeoutError, OSError):
                pass
        print(
            "omc: iTerm2 API could not pin this tab title; check Python API authorization "
            "and ITERM_SESSION_ID. Using OSC fallback (cannot pin title).",
            file=sys.stderr,
        )
        super().set_title(ctx, title)
        return False


def detect_terminal(env: Mapping[str, str]) -> Terminal:
    if Iterm2Terminal.detect(env):
        return Iterm2Terminal()
    return OscTerminal()
