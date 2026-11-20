"""The port's stand-in for omc's `ToolContext`, `errors` and `fsutil`: the ported modules take a small stand-in for
`ToolContext` (env, home, `run_bounded`), `errors` and `fsutil`. `Ctx(env, home, run_bounded)` is omc 0.1.54's
`src/omc/toolctx.py:48-155` cut to what the ported modules use: the environment, omc's home (`$OMC_HOME`, else
`~/.omc`) and the bounded run, its child's environment the context's own (omc added the uv and GitNexus variables,
which no ported module reads). `OmcError` and `Refusal` are `errors.py`'s, `write_atomic` is `fsutil.py`'s. The
standard library only, no YAML: `herdr.py` and `terminal_title.py` import it under a bare `python3 -I`."""
from __future__ import annotations

import os
import signal
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path


class OmcError(Exception):
    """Expected failure: printed without traceback, exit code 1."""

    rc = 1


class Refusal(OmcError):
    """Deliberate refusal (bad input, unmet precondition): exit code 2."""

    rc = 2


def write_atomic(path: Path, text: str, *, parents: bool = True) -> None:
    """Write `text` to `path` through a temp sibling and os.replace, mode 0644, so no
    reader ever sees a half-written file. `parents=False` makes no directory: a missing
    one raises FileNotFoundError."""
    if parents:
        path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, 0o644)  # mkstemp creates 0600; these files are not secrets
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _run_bounded(
    env: Mapping[str, str],
    argv: Sequence[str],
    *,
    timeout: float,
    cwd: str | os.PathLike[str] | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a captured command with a hard deadline for its entire process group."""
    kwargs: dict[str, object] = {
        "env": {**env, **(extra_env or {})},
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "errors": "replace",
        "start_new_session": True,
    }
    if cwd is not None:
        kwargs["cwd"] = cwd
    proc = subprocess.Popen(list(argv), **kwargs)  # noqa: S603 - argv list, no shell
    try:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"command timed out after {timeout}s") from exc
        return subprocess.CompletedProcess(list(argv), proc.returncode, stdout, stderr)
    except BaseException:
        # A child can exit while a descendant still owns the captured pipe;
        # its process group persists after the direct child is reaped.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        proc.communicate()
        raise


@dataclass
class Ctx:
    """omc's `ToolContext`, as far as the ported modules use it: `env`, `home` and `run_bounded(argv, *, timeout,
    cwd=None, extra_env=None)`, a field a test replaces (omc's tests patched the method on the instance)."""

    env: Mapping[str, str]
    home: Path
    run_bounded: Callable[..., subprocess.CompletedProcess[str]] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self.run_bounded is None:
            self.run_bounded = lambda argv, **kwargs: _run_bounded(self.env, argv, **kwargs)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Ctx":
        env = dict(os.environ if env is None else env)
        home = Path(env.get("OMC_HOME") or (Path(env.get("HOME") or str(Path.home())) / ".omc"))
        return cls(env=env, home=home)
