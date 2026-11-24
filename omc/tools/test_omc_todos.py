"""Tests of omc/tools/todos.py, `just omc todos [--json]`: each source of its table parsed from fixtures (the
project's own `omc/bin/todos` a script the case writes), and the start command of each. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_todos.py
Each case gets its own temporary repository from omc_fixtures' `Repo` (a bare origin.git and a work clone on main);
the log's deferred entries are read from origin/main, so a case pushes the log it means main to hold."""
import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import omc  # noqa: E402
import todos  # noqa: E402
from omc_fixtures import Repo  # noqa: E402

LOG = 'docs/decision-log.md'  # omc_fixtures' paths.decision_log
LOG_TEXT = '''# Design decision log

*Scratch space. Next: 58*

### 41 Incidents need a photo

**Context.** Incidents are reported without proof.
**Decision.** Every incident carries a photo.
**Automated.** false
**Affected.** R9.3-2, T9.3
**Status.** recorded 2026-11-12 · deferred 2026-11-13

### 42 The header shows the call

**Context.** The owner asked.
**Decision.** The call sits under the picture.
**Automated.** false
**Status.** recorded 2026-11-12

### 57 A deferred one applied later

**Context.** Old.
**Decision.** Done.
**Automated.** false
**Status.** recorded 2026-11-12 · deferred 2026-11-13 · applied 2026-11-14
'''
QUESTIONS = '''# Questions: feature/x run 1

### Q1 An incident without a photo
**Question.** May an incident be reported without a photo?
**Status.** open

### Q2 Settled already
**Question.** Is it?
**Status.** decision 41

### Q3 The "quoted" $name
**Question.** A title to quote.
**Status.** open
'''
HOOK = """#!/bin/sh
cat <<'END'
[{"source": "open-item", "path": "notes/open.md#Q1", "title": "The replica", "theme": "T18.1"},
 {"source": "e2e", "path": "test/OPEN.md#O1", "title": "A close before the pull", "start": "just design x"}]
END
"""
CODE = '''import os
# TODO: read the rows by id
x = 1  # FIXME handle the empty list
y = "a TODO in a string is no comment"
'''
DART = '''// TODO(mara): drop the fallback
void main() {}
'''


class TodosTest(unittest.TestCase):

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        env = mock.patch.dict(os.environ, self.repo.env, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def files(self, files, push=False):
        for path, text in files.items():
            self.repo.write(path, text)
            self.repo.git('add', '--', path)
        self.repo.git('commit', '-q', '-m', 'fixtures')
        if push:
            self.repo.git('push', '-q', 'origin', 'main')

    def of(self, source):
        return [{k: v for k, v in item.items()} for item in todos.gather(self.repo.work) if item['source'] == source]

    def omc(self, *args):
        out, err, here = io.StringIO(), io.StringIO(), os.getcwd()
        os.chdir(self.repo.work)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = omc.main(list(args))
        finally:
            os.chdir(here)
        return subprocess.CompletedProcess(args, code, out.getvalue(), err.getvalue())


class Sources(TodosTest):

    def test_tasks(self):
        self.files({'tasks/README.md': '# Open work\n', 'tasks/location-tracker.md': '# Location tracker\n\nT4.6 work.\n',
                    'tasks/no-heading.md': 'just text\n'})
        self.assertEqual(self.of('tasks'), [
            {'source': 'tasks', 'path': 'tasks/location-tracker.md', 'title': 'Location tracker', 'theme': 'T4.6',
             'start': 'just design tasks/location-tracker.md'},
            {'source': 'tasks', 'path': 'tasks/no-heading.md', 'title': 'no-heading', 'theme': None,
             'start': 'just design tasks/no-heading.md'}])

    def test_deferred_entries_of_origin_main(self):
        self.files({LOG: LOG_TEXT}, push=True)
        self.repo.write(LOG, LOG_TEXT.replace('deferred 2026-11-13\n\n### 42', 'deferred 2026-11-13 · applied 2026-11-20'
                                              '\n\n### 42'))  # the working tree's log is not main's
        self.assertEqual(self.of('deferred'), [
            {'source': 'deferred', 'path': f'{LOG}#41', 'title': 'Incidents need a photo', 'theme': 'T9.3',
             'start': 'just design --deferred 41'}])

    def test_no_log_on_main_is_none(self):
        self.assertEqual(self.of('deferred'), [])

    def test_no_log_configured_is_none(self):
        """Absent means off: main's file at the old default path is no log when the config names none."""
        path = os.path.join(self.repo.work, 'omc', 'config.yaml')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        self.files({'omc/config.yaml': text.replace(f'  decision_log: {LOG}\n', ''), LOG: LOG_TEXT}, push=True)
        self.assertEqual(self.of('deferred'), [])

    def test_open_questions_of_question_files(self):
        self.files({'docs/reviews/2026-11-20-x-1.md': QUESTIONS,
                    'docs/reviews/review-notes.md': '# Review\n\n### Q1 Not a question file\n**Status.** open\n',
                    'docs/reviews/screens/2026-11-20-x-screens-1.md': QUESTIONS})  # a subfolder is not read
        self.assertEqual([(i['path'], i['title']) for i in self.of('question')], [
            ('docs/reviews/2026-11-20-x-1.md#Q1', 'An incident without a photo'),
            ('docs/reviews/2026-11-20-x-1.md#Q3', 'The "quoted" $name')])

    def hook(self, text, mode=0o755):
        path = os.path.join(self.repo.work, 'omc', 'bin', 'todos')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        os.chmod(path, mode)

    def test_the_projects_own_sources(self):
        self.hook(HOOK)
        self.assertEqual([i for i in todos.gather(self.repo.work) if i['source'] in ('open-item', 'e2e')], [
            {'source': 'open-item', 'path': 'notes/open.md#Q1', 'title': 'The replica', 'theme': 'T18.1',
             'start': 'just design "The replica (notes/open.md#Q1)"'},
            {'source': 'e2e', 'path': 'test/OPEN.md#O1', 'title': 'A close before the pull', 'theme': None,
             'start': 'just design x'}])

    def test_no_hook_or_not_executable_is_dormant(self):
        self.assertEqual(todos.project(self.repo.work), [])
        self.hook(HOOK, mode=0o644)
        self.assertEqual(todos.project(self.repo.work), [])

    def test_a_failing_or_malformed_hook_is_refused(self):
        for text, said in (('#!/bin/sh\necho broken >&2\nexit 3\n', 'exited 3: broken'),
                           ('#!/bin/sh\necho not json\n', 'printed no JSON list'),
                           ('#!/bin/sh\necho \'{"a": 1}\'\n', 'printed no JSON list'),
                           ('#!/bin/sh\necho \'[{"source": "x", "path": "p"}]\'\n', 'without a source, a path and a title')):
            self.hook(text)
            with self.assertRaises(todos.Refused) as e:
                todos.project(self.repo.work)
            self.assertIn(said, str(e.exception))

    def test_none_without_todos_or_product(self):
        self.files({'src/tools/x/a.py': CODE})
        self.assertEqual(self.of('todo'), [])
        self.repo.set_config('  themes: []\n', '  themes: []\n  product: [src/app/**]\n')
        self.files({'src/app/lib/b.dart': DART})
        self.assertEqual([i['path'] for i in self.of('todo')], ['src/app/lib/b.dart:1'])

    def test_todo_and_fixme_comments_of_paths_todos(self):
        self.repo.set_config('  themes: []\n', '  themes: []\n  todos: [src/**]\n  product: [src/app/**]\n')
        self.files({'src/tools/x/a.py': CODE, 'src/app/lib/b.dart': DART, 'docs/c.md': '# TODO: not under src\n'})
        self.assertEqual([(i['path'], i['title']) for i in self.of('todo')], [
            ('src/app/lib/b.dart:1', 'TODO(mara): drop the fallback'),
            ('src/tools/x/a.py:2', 'TODO: read the rows by id'),
            ('src/tools/x/a.py:3', 'FIXME handle the empty list')])


class Start(TodosTest):

    def test_commands(self):
        self.repo.set_config('  themes: []\n', '  themes: []\n  todos: [src/**]\n')
        self.files({'tasks/location-tracker.md': '# Location tracker\n', LOG: LOG_TEXT,
                    'docs/reviews/2026-11-20-x-1.md': QUESTIONS, 'src/tools/x/a.py': CODE}, push=True)
        starts = {i['path']: i['start'] for i in todos.gather(self.repo.work)}
        self.assertEqual(starts['tasks/location-tracker.md'], 'just design tasks/location-tracker.md')
        self.assertEqual(starts[f'{LOG}#41'], 'just design --deferred 41')
        self.assertEqual(starts['docs/reviews/2026-11-20-x-1.md#Q1'],
                         'just design "An incident without a photo (docs/reviews/2026-11-20-x-1.md#Q1)"')
        self.assertEqual(starts['docs/reviews/2026-11-20-x-1.md#Q3'],
                         'just design "The \\"quoted\\" \\$name (docs/reviews/2026-11-20-x-1.md#Q3)"')
        self.assertEqual(starts['src/tools/x/a.py:2'], 'just design "TODO: read the rows by id (src/tools/x/a.py:2)"')
        # the shell reads the quoted text back as the one argument it was
        out = subprocess.run(('sh', '-c', 'printf %s ' + starts['docs/reviews/2026-11-20-x-1.md#Q3'][len('just design '):]),
                             capture_output=True, text=True).stdout
        self.assertEqual(out, 'The "quoted" $name (docs/reviews/2026-11-20-x-1.md#Q3)')


class Cli(TodosTest):

    def test_text_json_and_none(self):
        r = self.omc('todos')
        self.assertEqual((r.returncode, r.stdout), (1, 'no open work found\n'), r.stderr)
        self.files({'tasks/location-tracker.md': '# Location tracker\n'})
        r = self.omc('todos')
        self.assertEqual((r.returncode, r.stdout), (0, 'tasks\t-\tLocation tracker\ttasks/location-tracker.md\t'
                                                       'just design tasks/location-tracker.md\n'), r.stderr)
        r = self.omc('todos', '--json')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), todos.gather(self.repo.work))


if __name__ == '__main__':
    unittest.main()
