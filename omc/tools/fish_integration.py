"""The fish title hook, omc/tools/omc-title.fish, and its omc-owned copy in the user's fish conf.d: `just omc shell-integration fish enable|disable|status|reconcile`. Ported from omc 0.1.54's
`src/omc/fish_integration.py`: the same behavior and bytes (the conf.d path, the ownership marker, the symlink and
foreign-file refusal, the atomic write, the opt-out file), but for the installed copy, which is the hook's bytes with
`set -g __omc_title_helper just --justfile <checkout>/justfile omc` below the ownership line (`installed_hook`; omc
installed the packaged bytes unchanged and its hook fell back to an `omc` on PATH, which the project has not). The
checkout is the one this file is in. The standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Literal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from toolctx import Ctx as ToolContext  # noqa: E402
from toolctx import OmcError, Refusal  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
HOOK_PREFIX = "# omc-managed fish title integration"
Action = Literal["enable", "disable", "status", "reconcile"]


def fish_hook_path() -> Path:
    return Path(HERE) / "omc-title.fish"


def title_helper() -> list[str]:
    """The hook's `__omc_title_helper`: `just omc` of this checkout, a form that runs from any directory."""
    return ["just", "--justfile", os.path.join(ROOT, "justfile"), "omc"]


def fish_quote(word: str) -> str:
    """`word` as one fish word: bare when it is plain, else single-quoted (fish escapes `\\` and `'` there)."""
    if re.fullmatch(r"[A-Za-z0-9_./=:@+-]+", word):
        return word
    return "'" + word.replace("\\", "\\\\").replace("'", "\\'") + "'"


def installed_hook(helper: list[str] | None = None) -> bytes:
    """The conf.d copy's bytes: the hook's, with `set -g __omc_title_helper <helper>` below the ownership line."""
    marker, rest = fish_hook_path().read_bytes().split(b"\n", 1)
    line = "set -g __omc_title_helper " + " ".join(fish_quote(word) for word in helper or title_helper())
    return marker + b"\n" + line.encode() + b"\n" + rest


def managed_fish_path(ctx: ToolContext) -> Path:
    xdg = ctx.env.get("XDG_CONFIG_HOME", "")
    if xdg and Path(xdg).is_absolute():
        base = Path(xdg)
    else:
        home = ctx.env.get("HOME")
        base = (Path(home) if home else Path.home()) / ".config"
    return base / "fish" / "conf.d" / "omc-title.fish"


def _disabled_path(ctx: ToolContext) -> Path:
    return ctx.home / "integrations" / "fish-title.disabled"


def is_owned(path: Path) -> bool:
    """A regular file whose first line starts with HOOK_PREFIX, any version suffix."""
    if path.is_symlink() or not path.is_file():
        return False
    try:
        with path.open("rb") as fh:
            first = fh.readline()
    except OSError:
        return False
    return first.startswith(HOOK_PREFIX.encode())


def _refuse_unless_manageable(target: Path) -> None:
    # Only the target itself is judged: a symlinked parent (~/.config/fish -> a dotfiles
    # checkout under stow/chezmoi/yadm) is written through, as those setups expect.
    if target.is_symlink():
        raise Refusal(f"fish integration: {target} is a symlink; leaving it alone")
    if target.exists() and not is_owned(target):
        raise Refusal(
            f"fish integration: {target} exists and is not omc-owned; move it aside first"
        )


def _install(ctx: ToolContext) -> None:
    target = managed_fish_path(ctx)
    _refuse_unless_manageable(target)
    content = installed_hook()
    if not content.startswith(HOOK_PREFIX.encode()):
        raise OmcError("packaged fish hook has no ownership header (broken install?)")
    target.parent.mkdir(parents=True, exist_ok=True)
    _refuse_unless_manageable(target)  # re-check: the path may have changed during mkdir
    if target.exists() and target.read_bytes() == content:
        return
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".omc-title.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _foreign_note(target: Path) -> str | None:
    """Why `target` is not omc's to remove, or None when it is absent or owned."""
    if not target.exists() and not target.is_symlink():
        return None
    if target.is_symlink():
        return f"left {target} in place: a symlink"
    if not is_owned(target):
        return f"left {target} in place: not an omc-owned file"
    return None


def _remove_owned(ctx: ToolContext) -> None:
    """Opt-out removal: an owned file goes (an OSError is an error); anything else stays."""
    target = managed_fish_path(ctx)
    note = _foreign_note(target)
    if note is not None:
        print(f"· fish integration: {note}", file=sys.stderr)
        return
    try:
        target.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise OmcError(f"fish integration removal failed: {exc}") from exc


def remove_owned_hook(ctx: ToolContext) -> str | None:
    """Uninstall's removal: delete only an owned file; otherwise return why it stays."""
    target = managed_fish_path(ctx)
    note = _foreign_note(target)
    if note is not None or not is_owned(target):
        return note
    try:
        target.unlink()
    except OSError as exc:
        return f"could not remove {target}: {exc}"
    return None


def run_fish_integration(ctx: ToolContext, action: Action) -> int:
    target = managed_fish_path(ctx)
    disabled = _disabled_path(ctx)
    if action == "status":
        print(
            json.dumps(
                {
                    "enabled": not disabled.exists(),
                    "installed": target.exists() or target.is_symlink(),
                    "path": str(target),
                    "owned": is_owned(target),
                }
            )
        )
        return 0
    if action == "disable":
        # The opt-out is recorded FIRST and unconditionally: disable is never a dead end.
        try:
            disabled.parent.mkdir(parents=True, exist_ok=True)
            disabled.touch()
        except OSError as exc:
            raise OmcError(f"could not persist fish disable: {exc}") from exc
        _remove_owned(ctx)
        return 0
    if action == "reconcile" and disabled.exists():
        if _foreign_note(target) is None:
            _remove_owned(ctx)  # opted out: an owned hook goes; a foreign file is not ours
        return 0
    if action in ("enable", "reconcile"):
        try:
            _install(ctx)
        except OSError as exc:
            raise OmcError(f"fish integration setup failed: {exc}") from exc
        if action == "enable":
            try:
                disabled.unlink(missing_ok=True)
            except OSError as exc:
                raise OmcError(f"could not clear fish disable: {exc}") from exc
        return 0
    raise ValueError(f"unknown fish integration action: {action}")
