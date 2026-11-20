"""Tests of install/install.py, `just install <project-folder>`. Run from the repository root through `just test`.
Each case builds a temporary v2 (a git repository holding a small omc/ with the real omc/omc.just, and a copy of
install/install.py, so the script's v2 is that repository) and a temporary project repository, with the caller's GIT_
variables removed and a private GIT_CONFIG_GLOBAL; the script runs with `--no-launch`. Two cases read the real v2."""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, 'install.py')

with open(os.path.join(REPO, 'omc', 'omc.just'), encoding='utf-8') as f:
    OMC_JUST = f.read()

# The omc/ of the temporary v2's first commit; omc/tools/tool.py is executable
V2_FILES = {
    'omc/omc.just': OMC_JUST,
    'omc/config.yaml': 'base: main\nbranch_prefix: feature/\n',
    'omc/pipeline/brainstorm/SKILL.md': 'brainstorm\n',
    'omc/pipeline/design/SKILL.md': 'design\n',
    'omc/pipeline/implement/SKILL.md': 'implement\n',
    'omc/pipeline/audit/SKILL.md': 'audit\n',
    'omc/terminals/check/SKILL.md': 'check\n',
    'omc/terminals/build/SKILL.md': 'build\n',
    'omc/terminals/verify/SKILL.md': 'verify\n',
    'omc/terminals/impact/SKILL.md': 'impact\n',
    'omc/skills/explain/SKILL.md': 'explain\n',
    'omc/tools/tool.py': '#!/usr/bin/env python3\nprint("tool")\n',
    'omc/tools/notes.txt': 'one\ntwo\nthree\nfour\nfive\n',
    'omc/tools/a.txt': 'a\n',
    'omc/tools/b.txt': 'b\n',
    'omc/tools/c.txt': 'c\n',
    'omc/tools/d.txt': 'd\n',
}

COMPACT = 'cd "$CLAUDE_PROJECT_DIR" && just omc enter --resume'
HERDR = ('[ "${TERM_PROGRAM-}" = herdr ] && python3 -I -X pycache_prefix="$CLAUDE_PROJECT_DIR/.cache/pycache" '
         '"$CLAUDE_PROJECT_DIR/omc/tools/herdr.py" >/dev/null 2>&1 || true')
# The herdr hook an earlier install wrote, without the pycache prefix
OLD_HERDR = ('[ "${TERM_PROGRAM-}" = herdr ] && python3 -I "$CLAUDE_PROJECT_DIR/omc/tools/herdr.py" >/dev/null 2>&1 '
             '|| true')


class Case(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = os.path.realpath(self.tmp.name)
        gitconfig = os.path.join(root, 'gitconfig')
        with open(gitconfig, 'w', encoding='utf-8') as f:
            f.write('[user]\n\temail = t@t\n\tname = t\n[commit]\n\tgpgsign = false\n[init]\n\tdefaultBranch = main\n')
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(GIT_CONFIG_GLOBAL=gitconfig, GIT_CONFIG_NOSYSTEM='1')
        self.v2 = os.path.join(root, 'v2')
        self.project = os.path.join(root, 'project')
        self.git(self.v2, 'init', '-q', self.v2, cwd=root)
        with open(SCRIPT, encoding='utf-8') as f:
            self.write(self.v2, 'install/install.py', f.read())
        for path, text in V2_FILES.items():
            self.write(self.v2, path, text)
        os.chmod(os.path.join(self.v2, 'omc/tools/tool.py'), 0o755)
        self.sha1 = self.commit(self.v2, 'v2 one')
        self.git(self.project, 'init', '-q', self.project, cwd=root)
        self.write(self.project, 'README', 'project\n')
        self.commit(self.project, 'start')

    # --- helpers

    def git(self, repo, *args, cwd=None):
        r = subprocess.run(('git', *args), cwd=cwd or repo, env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f'git {" ".join(args)}: {r.stderr}')
        return r.stdout

    def write(self, repo, path, text):
        full = os.path.join(repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(text)

    def read(self, path, repo=None):
        with open(os.path.join(repo or self.project, path), encoding='utf-8') as f:
            return f.read()

    def commit(self, repo, message):
        self.git(repo, 'add', '-A')
        self.git(repo, 'commit', '-q', '--allow-empty', '-m', message)
        return self.git(repo, 'rev-parse', 'HEAD').strip()

    def install(self, project=None, script=None):
        return subprocess.run((sys.executable, '-I', script or os.path.join(self.v2, 'install', 'install.py'),
                               project or self.project, '--no-launch'),
                              env=self.env, capture_output=True, text=True)

    def installed(self):
        """A fresh install, asserted to succeed, committed in the project."""
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.commit(self.project, 'omc installed')
        return r

    def v2_commit(self, files=None, delete=()):
        for path, text in (files or {}).items():
            self.write(self.v2, path, text)
        for path in delete:
            os.remove(os.path.join(self.v2, path))
        return self.commit(self.v2, 'v2 two')

    def status(self):
        return self.git(self.project, 'status', '--porcelain', '--untracked-files=all')

    def assertRefused(self, r, *words):
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('error:', r.stderr)
        for w in words:
            self.assertIn(w, r.stderr)


class Refusals(Case):

    def test_refuse_non_repo(self):
        plain = os.path.join(os.path.dirname(self.project), 'plain')
        os.makedirs(plain)
        r = self.install(project=plain)
        self.assertRefused(r, 'not a git work tree')
        self.assertEqual(os.listdir(plain), [])

    def test_refuse_subdirectory_of_a_repo(self):
        os.makedirs(os.path.join(self.project, 'sub'))
        r = self.install(project=os.path.join(self.project, 'sub'))
        self.assertRefused(r, 'top')
        self.assertEqual(os.listdir(os.path.join(self.project, 'sub')), [])

    def test_refuse_dirty(self):
        self.write(self.project, 'stray.txt', 'x\n')
        r = self.install()
        self.assertRefused(r, 'dirty')
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc')))
        self.assertFalse(os.path.exists(os.path.join(self.project, 'justfile')))

    def test_skill_dir_clash_refused(self):
        self.write(self.project, '.claude/skills/design/SKILL.md', 'the project\'s own design skill\n')
        self.commit(self.project, 'own skill')
        r = self.install()
        self.assertRefused(r, '.claude/skills/design')
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc')))
        self.assertEqual(self.status(), '')

    def test_recipe_clash_refused(self):
        self.write(self.project, 'justfile', '# own\ndesign:\n    echo mine\n')
        self.commit(self.project, 'own design recipe')
        r = self.install()
        self.assertRefused(r, "'design'")
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc')))
        self.assertEqual(self.status(), '')

    def test_recipe_clash_in_an_imported_file_refused(self):
        self.write(self.project, 'justfile', "import? 'more.just'\n")
        self.write(self.project, 'more.just', '@omc *ARGS:\n    echo mine\n')
        self.commit(self.project, 'own omc recipe')
        r = self.install()
        self.assertRefused(r, "'omc'")
        self.assertEqual(self.status(), '')

    def test_bad_settings_refused(self):
        self.write(self.project, '.claude/settings.json', '{not json')
        self.commit(self.project, 'broken settings')
        r = self.install()
        self.assertRefused(r, 'settings.json')
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc')))

    def test_update_refuses_unknown_base(self):
        self.installed()
        self.write(self.project, 'omc/VERSION', 'f' * 40 + '\n')
        self.commit(self.project, 'odd version')
        self.v2_commit({'omc/tools/a.txt': 'A\n'})
        r = self.install()
        self.assertRefused(r, 'f' * 40)
        self.assertEqual(self.read('omc/tools/a.txt'), 'a\n')
        self.assertEqual(self.status(), '')

    def test_claude_skills_as_a_file_refused(self):
        self.write(self.project, '.claude/skills', 'not a folder\n')
        self.commit(self.project, 'odd skills')
        r = self.install()
        self.assertRefused(r, '.claude/skills')
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc')))
        self.assertEqual(self.status(), '')

    def test_symlinks_on_a_write_path_refused(self):
        for link in ('omc', 'omc/tools', '.claude', '.claude/skills', '.gitignore', '.cache'):
            with self.subTest(link=link):
                self.git(self.project, 'reset', '-q', '--hard', self.git(self.project, 'rev-list', '--max-parents=0',
                                                                         'HEAD').strip())
                self.git(self.project, 'clean', '-q', '-fdx')
                target = os.path.join(self.project, 'elsewhere')
                os.makedirs(target)
                self.write(self.project, 'elsewhere/keep', 'x\n')
                os.makedirs(os.path.dirname(os.path.join(self.project, link)), exist_ok=True)
                os.symlink('elsewhere' if '/' not in link else '../elsewhere', os.path.join(self.project, link))
                self.commit(self.project, f'{link} a link')
                r = self.install()
                self.assertRefused(r, link, 'symlink')
                self.assertEqual(os.listdir(target), ['keep'])
                self.assertFalse(os.path.exists(os.path.join(self.project, 'omc', 'VERSION')))
                self.assertEqual(self.status(), '')

    def test_a_tree_path_with_a_dot_dot_or_dot_git_component_refused(self):
        for bad in ('..', '.git', '.GIT'):
            with self.subTest(bad=bad):
                r = subprocess.run(('git', 'hash-object', '-w', '--stdin'), cwd=self.v2, env=self.env, input='x\n',
                                   capture_output=True, text=True)
                blob = r.stdout.strip()
                inner = self.mktree(f'100644 blob {blob}\tx\n')
                bad_tree = self.mktree(f'040000 tree {inner}\t{bad}\n100644 blob {blob}\tomc.just\n')
                root = self.mktree(f'040000 tree {bad_tree}\tomc\n')
                sha = self.git(self.v2, 'commit-tree', '-m', 'bad', root).strip()
                self.git(self.v2, 'update-ref', 'HEAD', sha)
                r = self.install()
                self.assertRefused(r, f'omc/{bad}/x')
                self.assertFalse(os.path.exists(os.path.join(self.project, 'omc')))
                self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.project), 'x')))

    def mktree(self, text):
        r = subprocess.run(('git', 'mktree'), cwd=self.v2, env=self.env, input=text, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_update_refuses_dirty(self):
        self.installed()
        self.write(self.project, 'omc/tools/a.txt', 'uncommitted\n')
        self.v2_commit({'omc/tools/b.txt': 'B\n'})
        r = self.install()
        self.assertRefused(r, 'dirty')
        self.assertEqual(self.read('omc/tools/b.txt'), 'b\n')


class Fresh(Case):

    def test_fresh_copies_and_links(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        for path, text in V2_FILES.items():
            self.assertEqual(self.read(path), text, path)
        self.assertFalse(os.path.exists(os.path.join(self.project, 'install')))
        self.assertEqual(self.read('omc/VERSION'), self.sha1 + '\n')
        self.assertTrue(os.access(os.path.join(self.project, 'omc/tools/tool.py'), os.X_OK))
        self.assertFalse(os.access(os.path.join(self.project, 'omc/tools/a.txt'), os.X_OK))
        links = {'brainstorm': 'pipeline', 'design': 'pipeline', 'implement': 'pipeline', 'audit': 'pipeline',
                 'check': 'terminals', 'build': 'terminals', 'verify': 'terminals', 'explain': 'skills'}
        skills = os.path.join(self.project, '.claude', 'skills')
        self.assertEqual(sorted(os.listdir(skills)), sorted(links))
        for name, kind in links.items():
            link = os.path.join(skills, name)
            self.assertEqual(os.readlink(link), f'../../omc/{kind}/{name}')
            self.assertTrue(os.path.isfile(os.path.join(link, 'SKILL.md')), name)
        settings = json.loads(self.read('.claude/settings.json'))
        entries = settings['hooks']['SessionStart']
        self.assertEqual(entries[0], {'matcher': 'compact', 'hooks': [{'type': 'command', 'command': COMPACT}]})
        self.assertEqual(entries[1], {'hooks': [{'type': 'command', 'command': HERDR, 'timeout': 5}]})

    def test_fresh_creates_justfile_import(self):
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.read('justfile'), "import 'omc/omc.just'\n")

    def test_fresh_appends_justfile_import_once(self):
        self.write(self.project, 'justfile', '# own\nhello:\n    echo hi')
        self.commit(self.project, 'justfile')
        self.installed()
        self.assertEqual(self.read('justfile'), "# own\nhello:\n    echo hi\nimport 'omc/omc.just'\n")
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.status(), '')

    @unittest.skipUnless(shutil.which('just'), 'just is not installed')
    def test_existing_check_recipe_untouched(self):
        own = ('# The fast gate\ncheck:\n    echo own check\n\nbuild:\n    echo own build\n\n'
               'verify:\n    echo own verify\n')
        self.write(self.project, 'justfile', own)
        self.commit(self.project, 'own gates')
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.read('justfile').startswith(own))
        listed = subprocess.run(('just', '--list'), cwd=self.project, env=self.env, capture_output=True, text=True)
        self.assertEqual(listed.returncode, 0, listed.stderr)
        names = {line.split()[0] for line in listed.stdout.splitlines()[1:] if line.strip()}
        self.assertTrue({'check', 'build', 'verify', 'omc', 'design', 'decisions'} <= names, listed.stdout)
        ran = subprocess.run(('just', 'check'), cwd=self.project, env=self.env, capture_output=True, text=True)
        self.assertIn('own check', ran.stdout)

    def test_settings_merge_keeps_project(self):
        own = {'permissions': {'allow': ['Bash(ls)']},
               'hooks': {'SessionStart': [{'matcher': 'compact',
                                           'hooks': [{'type': 'command', 'command': COMPACT}]}],
                         'Stop': [{'hooks': [{'type': 'command', 'command': 'echo stop'}]}]}}
        self.write(self.project, '.claude/settings.json', json.dumps(own))
        self.commit(self.project, 'own settings')
        self.installed()
        settings = json.loads(self.read('.claude/settings.json'))
        self.assertEqual(settings['permissions'], own['permissions'])
        self.assertEqual(settings['hooks']['Stop'], own['hooks']['Stop'])
        commands = [h['command'] for e in settings['hooks']['SessionStart'] for h in e['hooks']]
        self.assertEqual(commands, [COMPACT, HERDR])

    def test_an_earlier_herdr_hook_is_replaced_not_doubled(self):
        own = {'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': OLD_HERDR, 'timeout': 5}]}]}}
        self.write(self.project, '.claude/settings.json', json.dumps(own))
        self.commit(self.project, 'an earlier install\'s hook')
        self.installed()
        commands = [h['command'] for e in json.loads(self.read('.claude/settings.json'))['hooks']['SessionStart']
                    for h in e['hooks']]
        self.assertEqual(commands, [HERDR, COMPACT])

    def test_second_install_same_head_is_noop(self):
        self.installed()
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.status(), '')

    def test_fresh_does_not_copy_bin_or_version_from_v2(self):
        # Neither is ever shipped; were either committed in v2 by mistake, the install still leaves them out
        self.write(self.v2, 'omc/bin/check', 'v2 check\n')
        self.write(self.v2, 'omc/VERSION', '0' * 40 + '\n')
        sha = self.commit(self.v2, 'mistakes')
        self.assertEqual(self.install().returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc/bin')))
        self.assertEqual(self.read('omc/VERSION'), sha + '\n')

    def test_fresh_over_an_existing_omc_lists_what_it_replaced(self):
        self.write(self.project, 'omc/config.yaml', 'base: trunk\n')
        self.write(self.project, 'omc/tools/a.txt', 'a\n')  # the same as shipped: no line
        self.write(self.project, 'omc/tools/mine.txt', 'mine\n')  # the project's only: stays, no line
        self.commit(self.project, 'an omc/ of its own')
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        printed = [line for line in r.stdout.splitlines() if line.startswith('REPLACED ')]
        self.assertEqual(printed, ['REPLACED omc/config.yaml'])
        self.assertEqual(self.read('omc/config.yaml'), V2_FILES['omc/config.yaml'])
        self.assertEqual(self.read('omc/tools/mine.txt'), 'mine\n')
        self.assertEqual(self.read('.cache/omc/install-report').splitlines(),
                         ['mode: fresh', 'from: -', f'to: {self.sha1}', f'v2: {self.v2}', 'REPLACED omc/config.yaml'])

    def test_fresh_over_a_dangling_symlink_replaces_it(self):
        os.makedirs(os.path.join(self.project, 'omc'), exist_ok=True)
        os.symlink('/nonexistent', os.path.join(self.project, 'omc/config.yaml'))
        self.commit(self.project, 'a dangling link where omc ships a file')
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('REPLACED omc/config.yaml', r.stdout.splitlines())
        self.assertFalse(os.path.islink(os.path.join(self.project, 'omc/config.yaml')))
        self.assertEqual(self.read('omc/config.yaml'), V2_FILES['omc/config.yaml'])

    def test_committed_content_not_the_working_tree(self):
        self.write(self.v2, 'omc/tools/a.txt', 'dirty in v2\n')
        self.write(self.v2, 'omc/tools/untracked.txt', 'untracked\n')
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.read('omc/tools/a.txt'), 'a\n')
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc/tools/untracked.txt')))


class Ignore(Case):
    """omc's gate logs, pass records and venv live under the project's .cache/, which the project must ignore."""

    def test_fresh_adds_cache_to_gitignore(self):
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.read('.gitignore'), '.cache/\n')

    def test_existing_cache_line_not_duplicated(self):
        self.write(self.project, '.gitignore', 'build/\n.cache/\n')
        self.commit(self.project, 'ignores')
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.read('.gitignore'), 'build/\n.cache/\n')

    def test_existing_rooted_pattern_respected(self):
        self.write(self.project, '.gitignore', '/.cache')
        self.commit(self.project, 'ignores')
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.read('.gitignore'), '/.cache')

    def test_appends_after_a_missing_trailing_newline(self):
        self.write(self.project, '.gitignore', 'build/')
        self.commit(self.project, 'ignores')
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.read('.gitignore'), 'build/\n.cache/\n')

    def test_update_adds_it_too(self):
        self.installed()
        self.write(self.project, '.gitignore', 'build/\n')
        self.commit(self.project, 'dropped .cache/')
        self.v2_commit({'omc/tools/a.txt': 'A\n'})
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.read('.gitignore'), 'build/\n.cache/\n')

    def test_fresh_writes_the_report(self):
        head = self.git(self.v2, 'rev-parse', 'HEAD').strip()
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read('.cache/omc/install-report'), f'mode: fresh\nfrom: -\nto: {head}\nv2: {self.v2}\n')
        self.assertEqual(self.status().count('install-report'), 0, self.status())

    def test_a_gate_log_leaves_the_tree_clean(self):
        self.installed()
        self.write(self.project, '.cache/omc/gates/check.log', 'passed\n')
        self.assertEqual(self.status(), '')


class Update(Case):

    def test_update_clean_merge(self):
        self.installed()
        self.write(self.project, 'omc/tools/notes.txt', 'ONE\ntwo\nthree\nfour\nfive\n')
        self.write(self.project, 'omc/config.yaml', 'base: trunk\nbranch_prefix: feature/\n')
        self.commit(self.project, 'project edits')
        sha2 = self.v2_commit({'omc/tools/notes.txt': 'one\ntwo\nthree\nfour\nFIVE\n',
                               'omc/config.yaml': 'base: main\nbranch_prefix: feature/\nnew_key: 1\n',
                               'omc/tools/new.txt': 'new\n',
                               'omc/skills/answer-doubt/SKILL.md': 'answer\n'},
                              delete=['omc/tools/a.txt', 'omc/skills/explain/SKILL.md'])
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn('CONFLICT', r.stdout)
        self.assertEqual(self.read('omc/tools/notes.txt'), 'ONE\ntwo\nthree\nfour\nFIVE\n')
        self.assertEqual(self.read('omc/config.yaml'), 'base: trunk\nbranch_prefix: feature/\nnew_key: 1\n')
        self.assertEqual(self.read('omc/tools/new.txt'), 'new\n')
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc/tools/a.txt')))
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc/skills/explain')))
        skills = os.path.join(self.project, '.claude', 'skills')
        self.assertEqual(os.readlink(os.path.join(skills, 'answer-doubt')), '../../omc/skills/answer-doubt')
        self.assertFalse(os.path.lexists(os.path.join(skills, 'explain')))
        self.assertIn('REMOVED .claude/skills/explain (omc no longer ships it)', r.stdout.splitlines())
        self.assertIn('REMOVED .claude/skills/explain (omc no longer ships it)',
                      self.read('.cache/omc/install-report').splitlines())
        self.assertEqual(self.read('omc/VERSION'), sha2 + '\n')
        self.assertEqual(self.read('justfile'), "import 'omc/omc.just'\n")
        commands = [h['command'] for e in json.loads(self.read('.claude/settings.json'))['hooks']['SessionStart']
                    for h in e['hooks']]
        self.assertEqual(commands, [COMPACT, HERDR])

    def test_update_conflict_markers(self):
        self.installed()
        self.write(self.project, 'omc/tools/notes.txt', 'one\ntwo\nPROJECT\nfour\nfive\n')
        self.commit(self.project, 'project edit')
        sha2 = self.v2_commit({'omc/tools/notes.txt': 'one\ntwo\nOMC\nfour\nfive\n',
                               'omc/tools/b.txt': 'B\n'})
        r = self.install()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('CONFLICT omc/tools/notes.txt', r.stdout.splitlines())
        text = self.read('omc/tools/notes.txt')
        self.assertIn('<<<<<<< project\nPROJECT\n', text)
        self.assertIn(f'||||||| omc {self.sha1[:7]}\nthree\n', text)
        self.assertIn(f'=======\nOMC\n>>>>>>> omc {sha2[:7]}\n', text)
        self.assertEqual(self.read('omc/tools/b.txt'), 'B\n')
        self.assertEqual(self.read('omc/VERSION'), sha2 + '\n')

    def test_update_deleted_vs_changed(self):
        self.installed()
        os.remove(os.path.join(self.project, 'omc/tools/a.txt'))  # deleted here, changed in omc
        self.write(self.project, 'omc/tools/b.txt', 'project b\n')  # changed here, deleted in omc
        os.remove(os.path.join(self.project, 'omc/tools/c.txt'))  # deleted here, unchanged in omc
        self.commit(self.project, 'project deletes and edits')
        self.v2_commit({'omc/tools/a.txt': 'A\n'}, delete=['omc/tools/b.txt'])
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = r.stdout.splitlines()
        self.assertIn('KEPT omc/tools/a.txt (deleted here, changed in omc)', lines)
        self.assertIn('KEPT omc/tools/b.txt (changed here, deleted in omc)', lines)
        self.assertFalse(any('c.txt' in line for line in lines), r.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc/tools/a.txt')))
        self.assertEqual(self.read('omc/tools/b.txt'), 'project b\n')
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc/tools/c.txt')))

    def test_update_report_holds_the_conflict_and_kept_lines_as_printed(self):
        self.installed()
        self.write(self.project, 'omc/tools/notes.txt', 'one\ntwo\nPROJECT\nfour\nfive\n')
        os.remove(os.path.join(self.project, 'omc/tools/a.txt'))
        self.commit(self.project, 'project edits')
        sha2 = self.v2_commit({'omc/tools/notes.txt': 'one\ntwo\nOMC\nfour\nfive\n', 'omc/tools/a.txt': 'A\n'})
        r = self.install()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        printed = [line for line in r.stdout.splitlines() if line.startswith(('CONFLICT ', 'KEPT '))]
        self.assertEqual(sorted(printed), ['CONFLICT omc/tools/notes.txt',
                                           'KEPT omc/tools/a.txt (deleted here, changed in omc)'])
        self.assertEqual(self.read('.cache/omc/install-report').splitlines(),
                         ['mode: update', f'from: {self.sha1}', f'to: {sha2}', f'v2: {self.v2}', *printed])

    def deleted_explain(self):
        self.installed()
        self.git(self.project, 'rm', '-q', '-r', 'omc/skills/explain', '.claude/skills/explain')
        self.commit(self.project, 'no explain')

    def test_update_deleted_skill_changed_in_omc_stays_unlinked(self):
        self.deleted_explain()
        self.v2_commit({'omc/skills/explain/SKILL.md': 'explain, better\n'})
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = r.stdout.splitlines()
        self.assertIn('KEPT omc/skills/explain/SKILL.md (deleted here, changed in omc)', lines)
        self.assertIn('KEPT .claude/skills/explain (deleted here)', lines)
        self.assertFalse(os.path.lexists(os.path.join(self.project, '.claude/skills/explain')))
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc/skills/explain')))

    def test_update_deleted_skill_untouched_in_omc_stays_unlinked(self):
        self.deleted_explain()
        self.v2_commit({'omc/tools/a.txt': 'A\n'})
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('KEPT .claude/skills/explain (deleted here)', r.stdout.splitlines())
        self.assertFalse(os.path.lexists(os.path.join(self.project, '.claude/skills/explain')))
        self.assertEqual(self.read('omc/tools/a.txt'), 'A\n')

    def test_update_links_a_skill_new_in_omc(self):
        self.installed()
        self.v2_commit({'omc/skills/pose-questions/SKILL.md': 'pose\n'})
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        link = os.path.join(self.project, '.claude/skills/pose-questions')
        self.assertEqual(os.readlink(link), '../../omc/skills/pose-questions')
        self.assertTrue(os.path.isfile(os.path.join(link, 'SKILL.md')))
        self.assertNotIn('KEPT', r.stdout)

    def own_skill(self):
        """Installed, then a skill of the project's own under omc/skills/, linked as omc links its skills."""
        self.installed()
        self.write(self.project, 'omc/skills/mine/SKILL.md', 'mine\n')
        os.symlink('../../omc/skills/mine', os.path.join(self.project, '.claude/skills/mine'))
        self.commit(self.project, 'own skill')

    def test_update_keeps_the_projects_own_skill_link(self):
        self.own_skill()
        self.v2_commit({'omc/tools/a.txt': 'A\n'})
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(os.readlink(os.path.join(self.project, '.claude/skills/mine')), '../../omc/skills/mine')
        self.assertNotIn('mine', r.stdout)

    def test_rerun_at_the_same_version_keeps_the_projects_own_skill_link(self):
        self.own_skill()
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.status(), '')

    def test_update_leaves_bin(self):
        self.installed()
        self.write(self.project, 'omc/bin/check', 'project check\n')
        self.commit(self.project, 'own bin')
        self.v2_commit({'omc/bin/check': 'v2 check\n', 'omc/bin/other': 'v2 other\n', 'omc/tools/a.txt': 'A\n'})
        r = self.install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.read('omc/bin/check'), 'project check\n')
        self.assertFalse(os.path.exists(os.path.join(self.project, 'omc/bin/other')))
        self.assertEqual(self.read('omc/tools/a.txt'), 'A\n')

    def test_update_keeps_project_additions_and_takes_new_exec_bit(self):
        self.installed()
        self.write(self.project, 'omc/tools/mine.txt', 'mine\n')
        self.commit(self.project, 'own file')
        os.chmod(os.path.join(self.v2, 'omc/tools/d.txt'), 0o755)
        self.v2_commit()
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.read('omc/tools/mine.txt'), 'mine\n')
        self.assertTrue(os.access(os.path.join(self.project, 'omc/tools/d.txt'), os.X_OK))


class RealV2(Case):

    def test_version_never_shipped(self):
        listed = self.git(REPO, 'ls-files', 'omc').splitlines()
        self.assertNotIn('omc/VERSION', listed)
        self.assertFalse([p for p in listed if p.startswith('omc/bin/')])

    def test_fresh_from_real_v2(self):
        r = self.install(script=SCRIPT)
        self.assertEqual(r.returncode, 0, r.stderr)
        head = self.git(REPO, 'rev-parse', 'HEAD').strip()
        self.assertEqual(self.read('omc/VERSION'), head + '\n')
        skills = os.path.join(self.project, '.claude', 'skills')
        expected = {'brainstorm', 'design', 'implement', 'audit', 'check', 'build', 'verify'}
        expected |= set(self.git(REPO, 'ls-tree', '--name-only', 'HEAD', 'omc/skills/').split())
        expected = {os.path.basename(p) for p in expected}
        self.assertEqual(set(os.listdir(skills)), expected)
        for name in expected:
            self.assertTrue(os.path.isfile(os.path.join(skills, name, 'SKILL.md')), name)

    def working_v2(self):
        """A temporary v2 whose one commit holds the real v2's working-tree copy of its tracked omc/, install.py and
        justfile: the install of what this tree would commit."""
        real = os.path.join(os.path.dirname(self.project), 'real-v2')
        self.git(real, 'init', '-q', real, cwd=os.path.dirname(real))
        for rel in self.git(REPO, 'ls-files', '--cached', '--others', '--exclude-standard', 'omc',
                            'install/install.py', 'justfile').splitlines():
            if os.path.isfile(os.path.join(REPO, rel)):
                os.makedirs(os.path.dirname(os.path.join(real, rel)), exist_ok=True)
                shutil.copy2(os.path.join(REPO, rel), os.path.join(real, rel))
        self.commit(real, 'the working tree')
        return real

    def test_herdr_hook_and_a_tool_run_leave_the_tree_clean(self):
        real = self.working_v2()
        r = self.install(script=os.path.join(real, 'install', 'install.py'))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.commit(self.project, 'omc installed')
        hooks = [h['command'] for e in json.loads(self.read('.claude/settings.json'))['hooks']['SessionStart']
                 for h in e['hooks'] if 'herdr' in h['command']]
        self.assertEqual(len(hooks), 1, hooks)
        env = dict(self.env, TERM_PROGRAM='herdr', CLAUDE_PROJECT_DIR=self.project)
        ran = subprocess.run(('bash', '-c', hooks[0]), cwd=self.project, env=env, capture_output=True, text=True,
                             input=json.dumps({'cwd': self.project}))
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertEqual(self.status(), '')
        # a tool run by hand, with no pycache prefix, writes omc/tools/__pycache__/, which omc/.gitignore ignores
        tool = 'import sys; sys.path.insert(0, "omc/tools"); import toolctx'
        ran = subprocess.run((sys.executable, '-I', '-c', tool),
                             cwd=self.project, env=self.env, capture_output=True, text=True)
        self.assertEqual(ran.returncode, 0, ran.stderr)
        self.assertTrue(os.path.isdir(os.path.join(self.project, 'omc', 'tools', '__pycache__')))
        self.assertEqual(self.status(), '')

    def odd_project(self):
        """A project whose path holds a space, a double quote and a `$`, installed through v2's own `just install`
        (its justfile's quoting under test too) from a temporary v2 that commits the working tree's tracked omc/, and
        committed."""
        real = self.working_v2()
        odd = os.path.join(os.path.dirname(self.project), 'pro "ject $x')
        self.git(odd, 'init', '-q', odd, cwd=os.path.dirname(odd))
        self.commit(odd, 'start')
        r = subprocess.run(('just', '--justfile', os.path.join(real, 'justfile'), '--working-directory', real,
                            'install', odd, '--no-launch'), env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(odd, 'omc', 'VERSION')))
        self.commit(odd, 'omc installed')
        return odd

    @unittest.skipUnless(shutil.which('just') and shutil.which('uv'), 'just or uv is not installed')
    def test_recipes_run_in_a_path_with_a_space_quote_and_dollar(self):
        odd = self.odd_project()
        r = subprocess.run(('just', 'omc', 'handoff'), cwd=odd, env=self.env, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, 'continue\n'), r.stderr)
        # design's --origin is the invocation directory, one word, unevaluated: as `just -n` prints the line
        r = subprocess.run(('just', '-n', 'design', 'x'), cwd=odd, env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f'--origin={odd}', shlex.split(r.stderr.strip().splitlines()[-1]))


if __name__ == '__main__':
    unittest.main()
