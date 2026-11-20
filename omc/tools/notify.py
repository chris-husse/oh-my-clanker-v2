"""Native notification settings for omc-launched sessions. `wire_worktree(CLAUDE, <worktree>, True)`, called by the launch after the worktree is cut and before the
exec, merges `{"preferredNotifChannel": "auto"}` into the worktree's `.claude/settings.local.json` and strips the hooks
whose command is exactly `omc internal notify --provider claude` from `Notification` and `Stop`; invalid JSON is
refused with a warning, the write is atomic, the launch is never blocked. Ported from omc 0.1.54's `src/omc/notify.py`;
`CLAUDE` stands in for omc's claude provider (`providers/claude.py:160-167`, its `name` and `notification_setup`),
the one provider the pipeline launches. The standard library only."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

OLD_CLAUDE_COMMAND = "omc internal notify --provider claude"


class Claude:
    """omc's claude provider, as far as the notification wiring uses it."""

    name = "claude"

    def notification_setup(self, notifications: bool):
        # Claude Code 2.1.291: preferredNotifChannel accepts auto and
        # notifications_disabled in local settings (verified with installed CLI).
        channel = "auto" if notifications else "notifications_disabled"
        return {
            ".claude/settings.local.json": json.dumps({"preferredNotifChannel": channel}, indent=2)
            + "\n"
        }


CLAUDE = Claude()


def _warn(message: str) -> None:
    print(f"· notifications: {message}", file=sys.stderr)


def merge_claude_settings(existing_text: str, ours_text: str) -> str | None:
    """Merge the desired channel and remove exact legacy omc hooks safely."""
    try:
        existing = json.loads(existing_text)
        desired = json.loads(ours_text)
    except (ValueError, TypeError):
        return None
    if not isinstance(existing, dict) or not isinstance(desired, dict):
        return None
    hooks = existing.get("hooks", {})
    if not isinstance(hooks, dict):
        return None
    # Validate the complete structure before mutation, so malformed settings
    # remain untouched even if one event contained an old omc entry.
    for event in ("Notification", "Stop"):
        groups = hooks.get(event, [])
        if not isinstance(groups, list):
            return None
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                return None
            if not all(isinstance(member, dict) for member in group["hooks"]):
                return None
    for event in ("Notification", "Stop"):
        retained = []
        for group in hooks.get(event, []):
            members = [
                member for member in group["hooks"] if member.get("command") != OLD_CLAUDE_COMMAND
            ]
            if members:
                retained.append({**group, "hooks": members})
            elif not any(member.get("command") == OLD_CLAUDE_COMMAND for member in group["hooks"]):
                retained.append(group)
        if event in hooks:
            hooks[event] = retained
    existing.update(desired)
    return json.dumps(existing, indent=2) + "\n"


def native_description(provider, notifications: bool) -> str:
    state = "on" if notifications else "off"
    if provider.name == "claude":
        channel = "auto" if notifications else "notifications_disabled"
        detail = f"claude: preferredNotifChannel={channel} in .claude/settings.local.json"
    else:
        detail = f"codex: -c tui.notifications={str(notifications).lower()}"
    return f"native, {state}   ({detail})"


def _write_settings(target: Path, content: str) -> None:
    """Replace a settings file only after a complete same-directory write."""
    fd, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(name)
    os.close(fd)
    try:
        temporary.write_text(content)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def wire_worktree(provider, worktree: Path, notifications: bool) -> list[str]:
    """Write native settings without ever blocking session launch."""
    written = []
    try:
        files = provider.notification_setup(notifications)
    except (OSError, ValueError, TypeError) as exc:
        _warn(f"could not prepare settings: {exc}")
        return written
    for rel, content in files.items():
        target = worktree / rel
        try:
            if target.exists():
                existing = target.read_text()
                merged = merge_claude_settings(existing, content)
                if merged is None:
                    _warn(f"{rel} is not valid settings JSON — leaving it alone")
                    continue
                if merged == existing:
                    continue
                content = merged
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
            _write_settings(target, content)
            written.append(rel)
        except (OSError, ValueError, TypeError) as exc:
            _warn(f"could not write {rel}: {exc}")
    return written
