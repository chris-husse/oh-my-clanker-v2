"""Tests of omc/tools/lint.py, `just omc lint` (lint checks names, not the flow). Run from
the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_lint.py
Each case writes a temporary root: a justfile with `check` that imports omc/omc.just with `decisions` and `omc`, `.claude/skills/record-decision`,
one pipeline skill `design` (steps `fresh` and `done`) and its link, one terminal `rebase`, one gate terminal `check`
and its link; no git is needed. The last case lints the real tree (in v2, a scratch
layout of its working tree's omc/)."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import lint  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
DESIGN = 'omc/pipeline/design/SKILL.md'
REBASE = 'omc/terminals/rebase/SKILL.md'
CHECK = 'omc/terminals/check/SKILL.md'


INSTALL_HELPERS = ('skill_links', 'shipped', 'link_skills', 'import_omc_just')


def v2_installer(repo):
    """v2's install/install.py, loaded by its path, when [repo] is v2: no omc/VERSION (every installed project has
    one) and an install/install.py with install's helpers; else None, and a project's own script is never loaded."""
    path = os.path.join(repo, 'install', 'install.py')
    if os.path.exists(os.path.join(repo, 'omc', 'VERSION')) or not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location('omc_v2_install', path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module if all(hasattr(module, name) for name in INSTALL_HELPERS) else None

JUSTFILE = '''# The project's own recipes, and omc's from the file it imports
import 'omc/omc.just'

# The fast gate
check *ARGS:
    omc/bin/check "$@"
'''

OMC_JUST = '''omc_py := "uv run"

[positional-arguments]
decisions *ARGS:
    {{omc_py}} omc/tools/decisions/decisions.py "$@"

[positional-arguments]
omc *ARGS:
    {{omc_py}} omc/tools/omc.py "$@"
'''

DESIGN_SKILL = '''---
name: design
description: "The design phase. /design <step-id> enters at that step."
disable-model-invocation: true
---

# /design

## `fresh` — bring the branch onto main

▣ `rebase` with `squash: no`; ✓ `just omc git rebased-on`, then `just omc enter design` and `just omc models high`.
A ruling is recorded through `/record-decision`; then on to `done`.

```sh
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just omc gate passed check)
```

## `done` — the end

`just decisions check` and `just check --detach`; a red one → back to `fresh`. `/design done` enters here.
'''

REBASE_SKILL = '''---
name: rebase
description: Rebase the branch onto main and say what moved.
---

# rebase

Run `just omc rebase --squash`; report the files of a conflict.

`OUTCOME {"outcome": "rebased", "old_base": "<sha>", "new_base": "<sha>"}`
'''

CHECK_SKILL = '''---
name: check
description: "Run the fast gate, `just check`, fix and rerun until green."
---

# check

Run `just check`; fix what is red and run it again.

`OUTCOME {"outcome": "passed"}`
'''

FILES = {'justfile': JUSTFILE, 'omc/omc.just': OMC_JUST, DESIGN: DESIGN_SKILL, REBASE: REBASE_SKILL, CHECK: CHECK_SKILL,
         '.claude/skills/record-decision/SKILL.md': '---\nname: record-decision\ndescription: Record a ruling.\n---\n'}


class LintTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = os.path.realpath(tmp.name)
        for path, text in FILES.items():
            self.write(path, text)
        os.symlink('../../omc/pipeline/design', self.path('.claude/skills/design'))
        os.symlink('../../omc/terminals/check', self.path('.claude/skills/check'))

    def path(self, rel):
        return os.path.join(self.root, rel)

    def write(self, rel, text):
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with open(self.path(rel), 'w', encoding='utf-8') as f:
            f.write(text)

    def read(self, rel):
        with open(self.path(rel), encoding='utf-8') as f:
            return f.read()

    def append(self, rel, text):
        """Append [text] to [rel]; the line number of its first line."""
        before = self.read(rel)
        self.write(rel, before + text)
        return before.count('\n') + 1

    def replace(self, rel, old, new):
        text = self.read(rel)
        self.assertIn(old, text)
        self.write(rel, text.replace(old, new, 1))

    def problems(self):
        """(path, line, kind) of each PROBLEM line of lint.lint."""
        found = []
        for p in lint.lint(self.root):
            self.assertTrue(p.startswith('PROBLEM: '), p)
            path, line, kind, _ = p[len('PROBLEM: '):].split(':', 3)
            found.append((path, int(line), kind.strip()))
        return found

    def omc(self, *args):
        return subprocess.run((sys.executable, '-I', os.path.join(HERE, 'omc.py'), *args), capture_output=True,
                              text=True)

    def test_a_sound_tree_is_green(self):
        self.assertEqual(lint.lint(self.root), [])
        r = self.omc('lint', '--root', self.root)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, 'OK\n', ''))

    def test_the_command_line_lists_the_problems(self):
        at = self.append(DESIGN, '`just frobnicate`\n')
        r = self.omc('lint', '--root', self.root)
        self.assertEqual(r.returncode, 1, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 2, r.stdout)
        self.assertTrue(lines[0].startswith(f'PROBLEM: {DESIGN}:{at}: recipe: '), lines[0])
        self.assertEqual(lines[1], '1 problems')

    def test_a_root_without_omc_is_refused(self):
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        r = self.omc('lint', '--root', empty.name)
        self.assertEqual((r.returncode, r.stdout), (2, ''))
        self.assertTrue(r.stderr.startswith('error: '), r.stderr)

    def test_a_missing_terminal_is_red(self):
        at = self.append(DESIGN, '▣ harden over the record, then ▣ `rebase` again.\n')
        self.assertEqual(self.problems(), [(DESIGN, at, 'terminal')])

    def test_a_mark_ending_a_sentence_is_read(self):
        self.append(DESIGN, 'Then ▣ rebase. Again ▣ `rebase`: ▣ rebase/again.\n')
        self.assertEqual(self.problems(), [])
        at = self.append(DESIGN, 'Then ▣ harden. And ▣ verify: on it.\n')
        self.assertEqual(self.problems(), [(DESIGN, at, 'terminal'), (DESIGN, at, 'terminal')])

    def test_a_command_ending_a_sentence_is_read(self):
        self.append(DESIGN, '```\nRun just check. Then just omc gate passed: done.\n```\n')
        self.assertEqual(self.problems(), [])
        at = self.append(DESIGN, '```\nRun just frobnicate. Then just omc gate pass.\n```\n')
        self.assertEqual(self.problems(), [(DESIGN, at + 1, 'recipe'), (DESIGN, at + 1, 'verb')])

    def test_an_unknown_verb_is_red(self):
        at = self.append(DESIGN, 'Then `just omc frobnicate --now`.\n')
        self.assertEqual(self.problems(), [(DESIGN, at, 'verb')])

    def test_an_unknown_sub_verb_is_red(self):
        at = self.append(DESIGN, 'Then `just omc gate pass check`; `just omc gate passed <check|verify>`.\n')
        self.assertEqual(self.problems(), [(DESIGN, at, 'verb')])

    def test_an_unknown_recipe_is_red(self):
        at = self.append(DESIGN, '```sh\njust check\njust frobnicate --now\n```\n')
        self.assertEqual(self.problems(), [(DESIGN, at + 2, 'recipe')])

    def test_lint_reads_imported_recipes(self):
        """A recipe counts when the root justfile defines it or a file it imports does, `import` or `import?`, each path
        relative to the importing file, imports of imports too; a missing optional import and a file nobody imports
        add nothing."""
        self.write('justfile', JUSTFILE + "import? 'local.just'\n")
        self.write('omc/omc.just', OMC_JUST + 'import "more/deep.just"\n')
        self.write('omc/more/deep.just', '@deep:\n    true\n')
        self.write('stray.just', 'stray:\n    true\n')
        self.append(DESIGN, '`just decisions check`, `just omc lint` and `just deep`.\n')
        self.assertEqual(self.problems(), [])
        at = self.append(DESIGN, '`just stray` and `just local`.\n')
        self.assertEqual(self.problems(), [(DESIGN, at, 'recipe'), (DESIGN, at, 'recipe')])
        self.write('local.just', 'local:\n    true\n')
        self.assertEqual(self.problems(), [(DESIGN, at, 'recipe')])

    def test_an_unknown_skill_is_red(self):
        at = self.append(DESIGN, 'Carry it through `/frobnicate` and `/record-decision`.\n')
        self.assertEqual(self.problems(), [(DESIGN, at, 'skill')])

    def test_an_unknown_step_is_red(self):
        at = self.append(DESIGN, 'Else back to `nowhere`; or `/design elsewhere`; on to `fresh`.\n')
        self.assertEqual(self.problems(), [(DESIGN, at, 'step'), (DESIGN, at, 'step')])

    def test_a_repeated_step_is_red(self):
        at = self.append(DESIGN, '\n## `fresh` — again\n')
        self.assertEqual(self.problems(), [(DESIGN, at + 1, 'step')])

    def test_a_missing_link_is_red(self):
        os.remove(self.path('.claude/skills/design'))
        self.assertEqual(self.problems(), [(DESIGN, 1, 'link')])

    def test_a_link_elsewhere_is_red(self):
        os.remove(self.path('.claude/skills/design'))
        os.symlink('../../omc/terminals/rebase', self.path('.claude/skills/design'))
        self.assertEqual(self.problems(), [(DESIGN, 1, 'link')])

    def test_a_gate_without_its_link_is_red(self):
        os.remove(self.path('.claude/skills/check'))
        self.assertEqual(self.problems(), [(CHECK, 1, 'link')])
        self.assertIn('.claude/skills/check is not a symbolic link to omc/terminals/check', lint.lint(self.root)[0])

    def test_a_gate_linked_elsewhere_is_red(self):
        os.remove(self.path('.claude/skills/check'))
        os.symlink('../../omc/terminals/rebase', self.path('.claude/skills/check'))
        self.assertEqual(self.problems(), [(CHECK, 1, 'link')])

    def test_a_terminal_asking_the_owner_is_red(self):
        at = self.append(REBASE, 'On a conflict, Ask The Owner which side wins.\n')
        self.assertEqual(self.problems(), [(REBASE, at, 'owner')])

    def test_a_terminal_running_an_orchestrator_is_red(self):
        at = self.append(REBASE, 'Then run `/record-decision` over the ruling.\n')
        self.assertEqual(self.problems(), [(REBASE, at, 'runs')])

    def test_a_terminal_without_its_outcome_is_red(self):
        self.replace(REBASE, '`OUTCOME {"outcome": "rebased", "old_base": "<sha>", "new_base": "<sha>"}`\n', '')
        self.assertEqual(self.problems(), [(REBASE, 1, 'outcome')])

    def test_a_bad_frontmatter_is_red(self):
        self.replace(REBASE, 'name: rebase', 'name: rebasing')
        self.assertEqual(self.problems(), [(REBASE, 2, 'frontmatter')])
        self.write(REBASE, REBASE_SKILL.replace('description: Rebase the branch onto main and say what moved.\n',
                                                'description:\n'))
        self.assertEqual(self.problems(), [(REBASE, 3, 'frontmatter')])
        self.write(REBASE, REBASE_SKILL[len('---\n'):])
        self.assertEqual(self.problems(), [(REBASE, 1, 'frontmatter')])

    def test_paths_namespaced_skills_and_prose_are_not_names(self):
        self.append(DESIGN, 'The marks: ▣ (a terminal) and ✓ (a tool check). Scratch in `/tmp/omc-gates`; '
                            'brainstorm with `superpowers:brainstorming` (`/superpowers:brainstorming`); it just '
                            'works. Seeded as `/design .cache/omc/brief.md`.\n')
        self.assertEqual(self.problems(), [])

    def test_a_project_with_its_own_install_script_lints_its_own_tree(self):
        marker = self.path('imported')
        self.write('omc/VERSION', '0' * 40 + '\n')
        self.write('install/install.py', f'open({marker!r}, "w").close()\n')
        self.assertIsNone(v2_installer(self.root))
        self.assertFalse(os.path.exists(marker))

    def test_an_install_script_without_omcs_helpers_is_not_v2s(self):
        self.write('install/install.py', 'def main():\n    pass\n')
        self.assertIsNone(v2_installer(self.root))

    def test_the_real_tree_is_green(self):
        """A project's own tree; in v2, whose tree holds no skill links and no justfile importing omc/omc.just, the
        working tree's omc/ laid out in a scratch root as install lays it out."""
        install = v2_installer(REPO)
        if install is None:
            self.assertEqual(lint.lint(REPO), [])
            return
        with tempfile.TemporaryDirectory() as root:
            shutil.copytree(os.path.join(REPO, 'omc'), os.path.join(root, 'omc'),
                            ignore=shutil.ignore_patterns('__pycache__'))
            files = [os.path.relpath(os.path.join(d, f), root).replace(os.sep, '/')
                     for d, _, names in os.walk(os.path.join(root, 'omc')) for f in names]
            links = install.skill_links([p for p in files if install.shipped(p)])
            install.link_skills(root, links, {}, links, lambda line: None)
            install.import_omc_just(root)
            self.assertEqual(lint.lint(root), [])


if __name__ == '__main__':
    unittest.main()
