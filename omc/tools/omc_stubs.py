"""Fake executables on an isolated PATH dir for the ported tests' probe and argv cases: omc 0.1.54's
`tests/unit/_stubs.py`, as far as the ported tests use it: `host_bin`, `make_stub`, `stub_env`. `host_bin`'s
missing tool fails the case with an AssertionError where omc's called `pytest.fail`. omc's codex and plugin stubs
(`make_codex_stub`, `make_claude_stub`, the catalogs) serve tests not ported here (another provider, the plugin
install). Imported by the tests of omc/tools after they put this directory on the path; not a test of its own."""
from __future__ import annotations

import functools
import os
import shlex
import shutil
import stat
from pathlib import Path

# The developer's PATH, captured at import: tests narrow os.environ["PATH"] to a stub
# dir before writing stubs, and a stub must never be what host_bin finds or caches.
_HOST_PATH = os.environ.get("PATH", os.defpath)
# Install hint per tool host_bin is asked for; anything else gets the generic one.
_COREUTILS = "install coreutils (`sudo apt-get install coreutils`; macOS ships them)"
_INSTALL_HINTS = {
    "bash": "install bash (`brew install bash` / `sudo apt-get install bash`)",
    "git": "install git (`brew install git` / `sudo apt-get install git`)",
    **dict.fromkeys(("cat", "mkdir", "rm", "sleep", "wc"), _COREUTILS),
}


@functools.cache
def host_bin(name: str) -> str:
    """Absolute path of the real ``name`` on the developer's PATH, resolved once.

    Stubs run on a restricted PATH, so they call real tools by absolute path —
    resolved here, never a hardcoded ``/bin/…`` or ``/usr/bin/…`` literal (hosts
    such as NixOS have neither). A missing tool fails loud, naming the fix.
    """
    found = shutil.which(name, path=_HOST_PATH)
    if found is None:
        hint = _INSTALL_HINTS.get(name, f"install `{name}` and put it on PATH")
        raise AssertionError(f"`{name}` is required by the unit suite but is not on PATH: {hint}")
    return found


def make_stub(
    bindir: Path,
    name: str,
    *,
    stdout: str = "",
    stderr: str = "",
    rc: int = 0,
    argv_log: Path | None = None,
    env_log: Path | None = None,
) -> Path:
    # Quoted heredoc so stdout survives verbatim — JSON verdicts contain double quotes.
    bindir.mkdir(parents=True, exist_ok=True)
    path = bindir / name
    # Each optional block is emitted ONLY when asked, so the default script stays
    # byte-identical for every existing caller: an unconditional stderr block would
    # put a stray newline on stderr and could flip a "stderr is empty" assertion.
    # printf over echo — a dash /bin/sh expands backslash escapes in echo's args.
    log = f"printf '%s\\n' \"$*\" > {shlex.quote(str(argv_log))}\n" if argv_log else ""
    # Absolute /usr/bin/env: stub_env's PATH holds only bindir, so a bare `env`
    # would not resolve. This records what the CHILD was handed, which is the only
    # way to prove a secret reached one subprocess and not the other.
    envlog = f"/usr/bin/env > {shlex.quote(str(env_log))}\n" if env_log else ""
    cat = shlex.quote(host_bin("cat"))
    err = f"{cat} >&2 <<'OMC_STUB_ERR_EOF'\n{stderr}\nOMC_STUB_ERR_EOF\n" if stderr else ""
    path.write_text(
        f"#!/bin/sh\n{log}{envlog}{cat} <<'OMC_STUB_EOF'\n{stdout}\nOMC_STUB_EOF\n{err}exit {rc}\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def stub_env(bindir: Path, **extra: str) -> dict[str, str]:
    """A minimal env whose PATH contains ONLY the stub dir."""
    return {"HOME": str(bindir.parent), "PATH": str(bindir), **extra}
