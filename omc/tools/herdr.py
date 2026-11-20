"""herdr sidebar cwd reports, and the tab's label.

Builds host-less OSC 7 sequences so herdr can show folder/branch in its sidebar. `name_tab` labels the pane's tab
(`herdr tab rename $HERDR_TAB_ID <label>`, `just design` naming it after the slug where it sets the title); outside
herdr it does nothing. Run as the project's SessionStart
hook, `python3 -I -X pycache_prefix="$CLAUDE_PROJECT_DIR/.cache/pycache" "$CLAUDE_PROJECT_DIR/omc/tools/herdr.py"`
with the hook's JSON on stdin (omc's `omc internal herdr-cwd`): always silent, exit 0, but an extra argument (the
usage line, exit 2). Ported from omc 0.1.54's `src/omc/herdr.py`, its entry rewritten. The standard library only."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import TextIO

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from toolctx import Ctx  # noqa: E402

USAGE = "usage: python3 -I omc/tools/herdr.py < SessionStart-hook-JSON"

_SAFE = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/")


def percent_encode_path(path: str) -> str:
    """Percent-encode a path byte by byte (matches fish `string escape --style=url`)."""
    return "".join(chr(b) if b in _SAFE else f"%{b:02X}" for b in os.fsencode(path))


def osc7_report(path: str) -> str:
    """Return the host-less OSC 7 cwd report for `path`."""
    return "\033]7;file://" + percent_encode_path(path) + "\a"


_DEV_DIR = Path("/dev")
_MAX_ANCESTORS = 32
_TTY_NAME = re.compile(r"pts/[0-9]+|tty[A-Za-z0-9]+")


def _ancestor_tty(ctx: Ctx) -> str | None:
    """The first ancestor's terminal device name (relative to /dev), or None."""
    pid = os.getppid()
    for _ in range(_MAX_ANCESTORS):
        proc = ctx.run_bounded(["ps", "-o", "ppid=", "-o", "tty=", "-p", str(pid)], timeout=2)
        if proc.returncode != 0:
            return None
        fields = proc.stdout.split()
        if len(fields) != 2:
            return None
        ppid, tty = int(fields[0]), fields[1]
        if tty not in ("?", "??"):
            return tty if _TTY_NAME.fullmatch(tty) else None
        if ppid <= 1:
            return None
        pid = ppid
    return None


def run_herdr_cwd(ctx: Ctx, stdin: TextIO) -> int:
    """SessionStart hook (omc's spec §4.5): report the session cwd to herdr's sidebar.

    Best effort and silent: every outcome returns 0 and prints nothing.
    """
    if ctx.env.get("TERM_PROGRAM") != "herdr":
        return 0
    try:
        payload = json.loads(stdin.read())
        if not isinstance(payload, dict):
            return 0
        cwd = payload.get("cwd")
        if not isinstance(cwd, str) or not os.path.isabs(cwd):
            return 0
        report = osc7_report(cwd).encode("ascii")
        tty = _ancestor_tty(ctx)
        if tty is None:
            return 0
        fd = os.open(_DEV_DIR / tty, os.O_WRONLY | os.O_NOCTTY)
        try:
            os.write(fd, report)
        finally:
            os.close(fd)
    except (OSError, TimeoutError, ValueError):
        pass
    return 0


def name_tab(ctx: Ctx, label: str) -> bool | None:
    """Labels the pane's tab [label]: `<$HERDR_BIN_PATH or herdr> tab rename <$HERDR_TAB_ID> <label>`, 5 s at most.
    None outside herdr (`TERM_PROGRAM` not `herdr`, or no `HERDR_TAB_ID`), nothing run; else whether it exited 0,
    never raising."""
    tab = ctx.env.get("HERDR_TAB_ID")
    if ctx.env.get("TERM_PROGRAM") != "herdr" or not tab:
        return None
    try:
        proc = ctx.run_bounded([ctx.env.get("HERDR_BIN_PATH") or "herdr", "tab", "rename", tab, label], timeout=5)
    except (OSError, TimeoutError):
        return False
    return proc.returncode == 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        print(USAGE, file=sys.stderr)
        return 2
    return run_herdr_cwd(Ctx.from_env(), sys.stdin)


if __name__ == "__main__":
    raise SystemExit(main())
