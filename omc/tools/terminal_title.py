"""Reusable title command for shell integrations: `python3 -I <root>/omc/tools/terminal_title.py <title>`,
which replaces omc's `python -m omc.terminal_title`. A title with a Unicode `Cc` character is refused
(`omc: invalid title: control characters are not allowed`, exit 1); otherwise `detect_terminal(env).set_title`, exit 0
when the title was pinned or written, 1 on the iTerm2 fallback. Ported from omc 0.1.54's `src/omc/terminal_title.py`,
its argv rewritten. The standard library only."""
from __future__ import annotations

import argparse
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from terminals import detect_terminal  # noqa: E402
from toolctx import Ctx  # noqa: E402


def terminal_title_argv() -> list[str]:
    return ["python3", "-I", os.path.join(HERE, "terminal_title.py")]


def validate_title(title: str) -> str | None:
    """None when `title` may be sent to a terminal, else why not (C0/C1 control characters)."""
    if any(unicodedata.category(char) == "Cc" for char in title):
        return "control characters are not allowed"
    return None


def run_title(ctx: Ctx, title: str) -> int:
    reason = validate_title(title)
    if reason is not None:
        print(f"omc: invalid title: {reason}", file=sys.stderr)
        return 1
    return 0 if detect_terminal(ctx.env).set_title(ctx, title) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Set the current terminal tab title")
    parser.add_argument("title")
    args = parser.parse_args(argv)
    return run_title(Ctx.from_env(), args.title)


if __name__ == "__main__":
    raise SystemExit(main())
