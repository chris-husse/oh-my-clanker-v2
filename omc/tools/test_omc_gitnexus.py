"""Tests of omc/tools/gitnexus.py, `just omc gitnexus <verb>`. Run from the
repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_gitnexus.py
Every case runs the tool as a subprocess in a temporary repository (omc_fixtures.Repo) whose `[gitnexus]` names the
fake fork (omc_fixtures.FakeGitNexus): a temporary `HOME`, stub `node` and `npm` first on `PATH`; no network."""
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
from omc_fixtures import TOOL, FakeGitNexus, Repo  # noqa: E402

PACKAGES = ('@huggingface/transformers', 'onnxruntime-node')


class Case(unittest.TestCase):
    """A temporary repository pinned to the fake fork, its `HOME` and stubs; the stubs' logs read and cleared."""

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        self.fake = FakeGitNexus(os.path.join(self.repo.root, 'gitnexus'), self.repo.env)
        self.fake.configure(self.repo)
        self.base = os.path.join(self.fake.home, '.omc', 'tools', 'gitnexus')
        self.checkout = os.path.join(self.base, 'gitnexus')
        self.cli = os.path.join(self.checkout, 'gitnexus', 'dist', 'cli', 'index.js')
        self.runtime = os.path.join(self.base, 'embeddings', 'runtime')

    def omc(self, *args, path=None, flags=None, cwd=None):
        env = self.fake.env(self.repo.env, path)
        if flags:
            env['FAKE_GITNEXUS'] = flags
        return subprocess.run((sys.executable, '-I', TOOL, 'gitnexus', *args), cwd=cwd or self.repo.work, env=env,
                              capture_output=True, text=True)

    def install(self, path=None, flags=None):
        return self.omc('install', path=path, flags=flags)

    def calls(self, log):
        """The stub's calls since the last `clear`, one dict each."""
        if not os.path.exists(log):
            return []
        with open(log, encoding='utf-8') as f:
            return [json.loads(line) for line in f]

    def clear(self):
        for log in (self.fake.npm_log, self.fake.node_log):
            if os.path.exists(log):
                os.remove(log)

    def last_line(self, r):
        return r.stderr.strip().splitlines()[-1]

    def assert_installed(self, r, sha):
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.last_line(r), f'GitNexus {sha[:7]} installed [ok]')
        head = subprocess.run(('git', '-C', self.checkout, 'rev-parse', 'HEAD'), env=self.repo.env,
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(head, sha)


class Install(Case):

    def test_install_clones_builds_and_installs_the_runtime(self):
        r = self.install()
        self.assert_installed(r, self.fake.sha)
        npm = [(c['argv'], os.path.relpath(c['cwd'], self.checkout)) for c in self.calls(self.fake.npm_log)]
        self.assertEqual(npm, [(['install', '--no-audit', '--no-fund'], 'gitnexus-shared'), (['ci'], 'gitnexus'),
                               (['run', 'build'], 'gitnexus')])
        for c in self.calls(self.fake.npm_log):
            self.assertTrue(c['CXXFLAGS'].endswith('-std=c++20'), c)
        self.assertEqual([c['argv'] for c in self.calls(self.fake.node_log)], [['embeddings', 'install']])
        self.assertTrue(os.path.isfile(self.cli))
        for package in PACKAGES:
            self.assertTrue(os.path.isfile(os.path.join(self.runtime, 'node_modules', package, 'package.json')))

    def test_an_installed_build_is_left_alone(self):
        self.assert_installed(self.install(), self.fake.sha)
        self.clear()
        r = self.install()
        self.assert_installed(r, self.fake.sha)
        self.assertEqual(self.calls(self.fake.npm_log), [])
        self.assertEqual(self.calls(self.fake.node_log), [])

    def test_a_half_install_is_finished(self):
        self.assert_installed(self.install(), self.fake.sha)
        os.remove(self.cli)
        self.clear()
        self.assert_installed(self.install(), self.fake.sha)
        self.assertEqual([c['argv'] for c in self.calls(self.fake.npm_log)][-1], ['run', 'build'])
        self.assertTrue(os.path.isfile(self.cli))
        os.remove(os.path.join(self.runtime, 'node_modules', 'onnxruntime-node', 'package.json'))
        self.clear()
        self.assert_installed(self.install(), self.fake.sha)
        self.assertEqual(self.calls(self.fake.npm_log), [])
        self.assertEqual([c['argv'] for c in self.calls(self.fake.node_log)], [['embeddings', 'install']])
        for package in PACKAGES:
            self.assertTrue(os.path.isfile(os.path.join(self.runtime, 'node_modules', package, 'package.json')))

    def test_a_failed_build_is_failed_and_finished_next_time(self):
        r = self.install(flags='npm-fails')
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(self.last_line(r), '[failed] npm install --no-audit --no-fund in gitnexus-shared/ failed')
        self.assertTrue(os.path.isdir(os.path.join(self.checkout, '.git')))
        self.assertFalse(os.path.exists(self.cli))
        self.clear()
        self.assert_installed(self.install(), self.fake.sha)
        self.assertEqual(len(self.calls(self.fake.npm_log)), 3)

    def test_a_moved_pin_rebuilds_and_keeps_the_runtime(self):
        self.assert_installed(self.install(), self.fake.sha)
        marker = os.path.join(self.runtime, 'node_modules', 'onnxruntime-node', 'marker')
        with open(marker, 'w', encoding='utf-8') as f:
            f.write('kept\n')
        hf = os.path.join(self.base, 'embeddings', 'hf', 'model.bin')
        os.makedirs(os.path.dirname(hf))
        with open(hf, 'w', encoding='utf-8') as f:
            f.write('kept\n')
        old = self.fake.sha
        new = self.fake.advance()
        self.fake.configure(self.repo)
        stray = os.path.join(self.checkout, 'gitnexus', 'package.json')
        with open(stray, 'w', encoding='utf-8') as f:
            f.write('a stray edit\n')
        self.clear()
        self.assertNotEqual(old, new)
        self.assert_installed(self.install(), new)
        with open(stray, encoding='utf-8') as f:
            self.assertIn('1.0.2', f.read())
        self.assertEqual([c['argv'] for c in self.calls(self.fake.npm_log)],
                         [['install', '--no-audit', '--no-fund'], ['ci'], ['run', 'build']])
        for path in (marker, hf):
            with open(path, encoding='utf-8') as f:
                self.assertEqual(f.read(), 'kept\n')

    def test_the_childs_environment(self):
        self.assert_installed(self.install(), self.fake.sha)
        (call,) = [c for c in self.calls(self.fake.node_log) if c['argv'] == ['embeddings', 'install']]
        self.assertEqual(call['env'], {'GITNEXUS_SHARED_STORE': 'off', 'GITNEXUS_EMBEDDING_RUNTIME_DIR': self.runtime,
                                       'HF_HOME': os.path.join(self.base, 'embeddings', 'hf')})
        self.assertNotIn('GITNEXUS_LBUG_EXTENSION_INSTALL', call['env'])

    def test_no_node_is_failed(self):
        bare = os.path.join(self.repo.root, 'bare-bin')
        os.makedirs(bare)
        os.symlink(shutil.which('git', path=self.repo.env['PATH']), os.path.join(bare, 'git'))
        os.symlink(os.path.join(self.fake.bin, 'npm'), os.path.join(bare, 'npm'))
        r = self.install(path=bare)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(self.last_line(r), '[failed] node not on PATH')
        self.assertFalse(os.path.exists(self.checkout))


ANALYZE = ['analyze', '--skip-agents-md', '--skip-skills', '--branch', 'main']


class Refresh(Case):
    """`just omc gitnexus refresh` over an installed fake: the stub's `analyze` writes `.gitnexus/meta.json` (the
    primary's HEAD, `--branch` as its owner, a vector count), as FAKE_GITNEXUS bends it."""

    def setUp(self):
        super().setUp()
        self.fake.preinstall()
        self.store = os.path.join(self.repo.work, '.gitnexus')

    def refresh(self, flags=None, cwd=None):
        return self.omc('refresh', flags=flags, cwd=cwd)

    def head(self):
        return self.repo.git('rev-parse', 'HEAD').strip()

    def meta(self):
        with open(os.path.join(self.store, 'meta.json'), encoding='utf-8') as f:
            return json.load(f)

    def argvs(self):
        return [c['argv'] for c in self.calls(self.fake.node_log)]

    def assert_refreshed(self, r, how):
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.last_line(r), f'index at {self.head()[:7]} ({how}) [ok]')
        self.assertEqual(self.meta()['lastCommit'], self.head())
        self.assertEqual(self.meta()['branch'], 'main')

    def test_refresh_analyzes_with_embeddings(self):
        r = self.refresh()
        self.assert_refreshed(r, 'embeddings')
        (call,) = self.calls(self.fake.node_log)
        self.assertEqual(call['argv'], [*ANALYZE, '--embeddings'])
        self.assertEqual(call['cwd'], self.repo.work)
        self.assertEqual(call['env'].get('GITNEXUS_LBUG_EXTENSION_INSTALL'), 'auto')
        self.assertEqual(call['env'].get('GITNEXUS_SHARED_STORE'), 'off')

    def test_a_current_index_is_left_alone(self):
        self.assert_refreshed(self.refresh(), 'embeddings')
        self.clear()
        r = self.refresh()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.last_line(r), 'index current [ok]')
        self.assertEqual(self.calls(self.fake.node_log), [])

    def test_a_failed_embedding_falls_back_to_keyword_only(self):
        r = self.refresh(flags='embed-fails')
        self.assert_refreshed(r, 'keyword-only')
        self.assertEqual(self.argvs(), [[*ANALYZE, '--embeddings'], ANALYZE])
        self.assertEqual(self.calls(self.fake.node_log)[1]['env'].get('GITNEXUS_LBUG_EXTENSION_INSTALL'), 'auto')

    def test_an_index_without_vectors_is_backfilled(self):
        r = self.refresh(flags='no-vectors')
        self.assert_refreshed(r, 'embeddings')
        self.assertEqual(self.argvs(), [[*ANALYZE, '--embeddings'], ['embeddings', 'sync', self.repo.work]])
        self.assertEqual(self.calls(self.fake.node_log)[1]['env'].get('GITNEXUS_LBUG_EXTENSION_INSTALL'), 'auto')
        self.assertGreater(self.meta()['stats']['embeddings'], 0)

    def test_a_foreign_or_still_stale_store_is_cleared_and_rebuilt(self):
        self.assert_refreshed(self.refresh(), 'embeddings')
        for n, flags in enumerate(('foreign-owner', 'still-stale')):
            self.repo.commit(f'f{n}.txt', 'x\n', f'commit {n}')
            self.clear()
            self.assert_refreshed(self.refresh(flags=flags), 'embeddings')
            self.assertEqual(self.argvs(), [[*ANALYZE, '--embeddings'], ['clean', '--force'],
                                            [*ANALYZE, '--embeddings']], flags)
        meta = self.meta()
        meta['branch'] = 'other'  # a store owned by another branch: cleared at once, no incremental analyze first
        with open(os.path.join(self.store, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f)
        self.clear()
        self.assert_refreshed(self.refresh(), 'embeddings')
        self.assertEqual(self.argvs(), [['clean', '--force'], [*ANALYZE, '--embeddings']])

    def test_an_off_base_primary_is_refused(self):
        self.repo.git('checkout', '-q', '-b', 'other')
        r = self.refresh()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(self.last_line(r), 'error: the primary checkout is on other, not main: the index is '
                                            'refreshed on main only')
        self.assertFalse(os.path.exists(self.store))
        self.assertEqual(self.calls(self.fake.node_log), [])

    def test_refresh_from_a_worktree_writes_the_primary(self):
        tree = os.path.join(self.repo.root, 'side')
        self.repo.git('worktree', 'add', '-q', '-b', 'side', tree)
        r = self.refresh(cwd=tree)
        self.assert_refreshed(r, 'embeddings')
        self.assertFalse(os.path.exists(os.path.join(tree, '.gitnexus')))
        self.assertEqual(self.calls(self.fake.node_log)[0]['cwd'], self.repo.work)

    def test_no_build_is_failed(self):
        os.remove(self.cli)
        r = self.refresh()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(self.last_line(r), '[failed] GitNexus not installed: just omc gitnexus install')
        self.assertFalse(os.path.exists(self.store))

    def test_no_node_is_failed(self):
        bare = os.path.join(self.repo.root, 'bare-bin')
        os.makedirs(bare)
        os.symlink(shutil.which('git', path=self.repo.env['PATH']), os.path.join(bare, 'git'))
        os.remove(os.path.join(self.runtime, 'node_modules', 'onnxruntime-node', 'package.json'))  # keyword-only
        r = self.omc('refresh', path=bare)  # no index: the keyword-only analyze
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(self.last_line(r), '[failed] node not on PATH')
        os.makedirs(self.store)
        with open(os.path.join(self.store, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump({'lastCommit': self.head(), 'branch': 'other'}, f)
        r = self.omc('refresh', path=bare)  # a store owned by another branch: the clean
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(self.last_line(r), '[failed] node not on PATH')


class Read(Case):
    """The read verbs over an installed fake and an index written in the primary: the stub answers
    `{"verb": …, "args": …}` on stdout."""

    def setUp(self):
        super().setUp()
        self.fake.preinstall()
        self.store = os.path.join(self.repo.work, '.gitnexus')

    def index(self):
        """An index in the primary at its HEAD; that HEAD."""
        head = self.repo.git('rev-parse', 'HEAD').strip()
        os.makedirs(self.store)
        with open(os.path.join(self.store, 'meta.json'), 'w', encoding='utf-8') as f:
            json.dump({'lastCommit': head, 'branch': 'main', 'repoPath': self.repo.work}, f)
        return head

    def lag_line(self, head):
        base = self.repo.git('rev-parse', 'origin/main').strip()
        self.assertNotEqual(head, base)  # configure commits the pin without pushing it: the two differ
        return f'index at {head[:7]}, base at {base[:7]}'

    def test_a_read_prints_the_lag_line_then_the_answer(self):
        head = self.index()
        for verb, args in (('query', ['a concept']), ('context', ['load', '--content']), ('impact', ['load']),
                           ('cypher', ['MATCH (n) RETURN n LIMIT 1'])):
            self.clear()
            r = self.omc(verb, *args)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = r.stdout.splitlines()
            self.assertEqual(lines[0], self.lag_line(head))
            self.assertEqual(json.loads(lines[1]), {'verb': verb, 'args': args})
            (call,) = self.calls(self.fake.node_log)
            self.assertEqual(call['argv'], [verb, *args, '--repo', self.repo.work, '--branch', 'main'])
            self.assertEqual(call['cwd'], self.repo.work)
            self.assertEqual(call['env'].get('GITNEXUS_SHARED_STORE'), 'off')
            self.assertNotIn('GITNEXUS_LBUG_EXTENSION_INSTALL', call['env'])

    def test_a_read_from_a_worktree_asks_the_primary(self):
        head = self.index()
        tree = os.path.join(self.repo.root, 'side')
        self.repo.git('worktree', 'add', '-q', '-b', 'side', tree)
        r = self.omc('query', 'a concept', cwd=tree)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], self.lag_line(head))
        (call,) = self.calls(self.fake.node_log)
        self.assertEqual(call['argv'][-4:], ['--repo', self.repo.work, '--branch', 'main'])
        self.assertEqual(call['cwd'], self.repo.work)
        self.assertFalse(os.path.exists(os.path.join(tree, '.gitnexus')))

    def test_a_read_without_a_build_is_refused(self):
        self.index()
        os.remove(self.cli)
        r = self.omc('query', 'a concept')
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(r.stderr.strip(), 'error: GitNexus not installed: just omc gitnexus install')
        self.assertEqual(r.stdout, '')
        self.assertEqual(self.calls(self.fake.node_log), [])

    def test_a_read_without_an_index_is_refused(self):
        r = self.omc('impact', 'load')
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(r.stderr.strip(), f'error: no GitNexus index in {self.repo.work}: just design refreshes it')
        self.assertEqual(r.stdout, '')
        self.assertEqual(self.calls(self.fake.node_log), [])


if __name__ == '__main__':
    unittest.main()
