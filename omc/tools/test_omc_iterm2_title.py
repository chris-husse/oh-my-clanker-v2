"""Tests of omc/tools/iterm2_title.py, the short-lived iTerm2 Python API worker: omc 0.1.54's `tests/unit/test_iterm2_title.py`, every case and expected byte kept, rewritten to
unittest. The `iterm2` package is faked as omc's test faked it (a module in `sys.modules`); `worker_argv` is the port's
rewritten argv, built in terminals.py. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_iterm2_title.py"""
import asyncio
import contextlib
import io
import os
import sys
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from iterm2_title import TargetNotFound, main, release_title, set_title  # noqa: E402
from terminals import worker_argv  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))


class Iterm2TitleTest(unittest.TestCase):
    def test_worker_uses_calling_session_and_literal_title(self):
        events = []
        caller = object()
        other = object()

        class Tab:
            async def async_set_variable(self, name, value):
                events.append(("variable", name, value))

            async def async_set_title(self, expression):
                events.append(("title", expression))

        class App:
            def get_session_by_id(self, identity):
                events.append(("lookup", identity))
                return caller

            def get_window_and_tab_for_session(self, session):
                events.append(("tab lookup", session))
                return other, Tab()

        class SDK:
            async def async_get_app(self, connection):
                return App()

        asyncio.run(set_title(object(), "caller-id", "$(danger) \\()", SDK()))
        self.assertEqual(
            events,
            [
                ("lookup", "caller-id"),
                ("tab lookup", caller),
                ("variable", "user.omc_title", "$(danger) \\()"),
                ("title", r"\(user.omc_title)"),
            ],
        )

    def test_worker_rejects_missing_session_and_tab(self):
        class MissingSession:
            def get_session_by_id(self, identity):
                return None

        class MissingTab:
            def get_session_by_id(self, identity):
                return object()

            def get_window_and_tab_for_session(self, session):
                return object(), None

        class SDK:
            def __init__(self, app):
                self.app = app

            async def async_get_app(self, connection):
                return self.app

        for app in (MissingSession(), MissingTab()):
            try:
                asyncio.run(set_title(object(), "caller-id", "x", SDK(app)))
            except TargetNotFound:
                pass
            else:
                raise AssertionError("missing target accepted")

    def test_release_resets_title_to_empty_before_clearing_variable(self):
        events = []
        caller = object()

        class Tab:
            async def async_set_variable(self, name, value):
                events.append(("variable", name, value))

            async def async_set_title(self, expression):
                events.append(("title", expression))

        class App:
            def get_session_by_id(self, identity):
                events.append(("lookup", identity))
                return caller

            def get_window_and_tab_for_session(self, session):
                return object(), Tab()

        class SDK:
            async def async_get_app(self, connection):
                return App()

        asyncio.run(release_title(object(), "caller-id", SDK()))
        # "" restores the live default title (SDK docs); the variable is cleared AFTER so a
        # concurrent evaluation of \(user.omc_title) never shows an empty pin.
        self.assertEqual(
            events,
            [
                ("lookup", "caller-id"),
                ("title", ""),
                ("variable", "user.omc_title", None),
            ],
        )

    def test_worker_argv_forms(self):
        base = ["env", f"UV_PROJECT_ENVIRONMENT={ROOT}/.cache/venv", "uv", "run", "--frozen", "--project",
                os.path.join(ROOT, "omc"), "python", "-I", os.path.join(ROOT, "omc", "tools", "iterm2_title.py"),
                "--session-id", "abc"]
        self.assertEqual(worker_argv("abc", title="feature/x"), [*base, "--", "feature/x"])
        self.assertEqual(worker_argv("abc", release=True), [*base, "--release"])
        self.assertEqual(worker_argv("abc", title="-weird"), [*base, "--", "-weird"])

    def test_main_swallows_sdk_errors_with_the_fixed_stderr_line(self):
        fake = types.ModuleType("iterm2")

        class Connection:
            @staticmethod
            async def async_create():
                raise RuntimeError("cookie=SECRET-COOKIE key=SECRET-KEY")

        fake.Connection = Connection
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(sys.modules, {"iterm2": fake}), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            self.assertEqual(main(["--session-id", "38B11221-B7E1-4F36-8A3B-50D549172632", "--", "t"]), 1)
            self.assertEqual(main(["--session-id", "38B11221-B7E1-4F36-8A3B-50D549172632", "--release"]), 1)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "omc: iTerm2 title update failed\nomc: iTerm2 title update failed\n")
        self.assertNotIn("SECRET", err.getvalue())

    def test_main_requires_exactly_one_of_release_or_title(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--session-id", "abc"]), 2)
            self.assertEqual(main(["--session-id", "abc", "--release", "--", "title"]), 2)
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
