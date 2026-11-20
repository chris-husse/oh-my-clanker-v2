"""The fixtures the tests of omc/tools share: `Repo`, a temporary repository (a bare origin.git and a work clone on
main holding omc/config.yaml, the caller's GIT_ variables removed and a private GIT_CONFIG_GLOBAL) with the git and
`just omc` calls the cases make in it; `FakeGitNexus`, the fake fork, a temporary `HOME` and stub `node` and `npm`
(no network, no real node). Imported by test_omc_repo.py, test_omc_rebase.py,
test_omc_done.py, test_omc_design.py, test_omc_cli.py and test_omc_gitnexus.py, after they put this directory on the
path; not a test of its own."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, 'omc.py')
# The omc/config.yaml of every `Repo`: the shipped tiers and pin, and the paths the cases rely on (a committed
# screenshot, a baseline a gate regenerates); every other path its default
CONFIG = """base: main
branch_prefix: feature/
orchestrator-model: opus
ask_for_provider_handoff: false
models:
  max: fable
  medium: opus
  low: sonnet
complexity:
  simple: low
  medium: medium
  high: orchestrator
gitnexus:
  origin: https://github.com/chris-husse/GitNexus.git
  commit: d8683be63a1f061ef88d993d4446a63144405e57
paths:
  protected: []
  screenshots: [docs/screens/shots/**]
  baselines: [test/e2e/baseline/**]
  briefs: tasks/
  specs: docs/superpowers/specs/
  plans: docs/superpowers/plans/
  decision_log: docs/decision-log.md
  questions: docs/reviews/
  themes: []
"""


class Repo:
    """A temporary bare `origin.git` and a `work` clone on `main`, one commit holding `omc/config.yaml` and a
    `.gitignore` of `.cache/`, pushed. `make_repo()` builds one; `cleanup()` removes it."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.origin = os.path.join(self.root, 'origin.git')
        self.work = os.path.join(self.root, 'work')
        self.other = os.path.join(self.root, 'other')  # the second clone advance_origin pushes from
        gitconfig = os.path.join(self.root, 'gitconfig')
        with open(gitconfig, 'w', encoding='utf-8') as f:
            f.write('[user]\n\temail = t@t\n\tname = t\n[commit]\n\tgpgsign = false\n[init]\n\tdefaultBranch = main\n')
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        # the gates' slots in a registry of its own: a gate run of the machine (the one running these tests) never
        # makes a fixture's run wait (concurrency.REGISTRY_ENV)
        self.env.update(GIT_CONFIG_GLOBAL=gitconfig, GIT_CONFIG_NOSYSTEM='1',
                        OMC_GATE_REGISTRY=os.path.join(self.root, 'gates'))

    template = None  # the first repository built, copied for every later one (a copy is cheaper than git's setup)

    @classmethod
    def make_repo(cls):
        r = cls()
        if cls.template is None:
            r.git('init', '-q', '--bare', '-b', 'main', r.origin, cwd=r.root)
            r.git('clone', '-q', r.origin, r.work, cwd=r.root)
            r.git('symbolic-ref', 'HEAD', 'refs/heads/main')
            os.makedirs(os.path.join(r.work, 'omc'))
            r.write(os.path.join('omc', 'config.yaml'), CONFIG)
            r.write('.gitignore', '.cache/\n')
            r.git('add', '--', '.gitignore', 'omc/config.yaml')
            r.git('commit', '-q', '-m', 'start')
            r.git('push', '-q', '-u', 'origin', 'main')
            cls.template = tempfile.TemporaryDirectory()
            for name in ('origin.git', 'work'):
                shutil.copytree(os.path.join(r.root, name), os.path.join(cls.template.name, name), symlinks=True)
        else:
            for name in ('origin.git', 'work'):
                shutil.copytree(os.path.join(cls.template.name, name), os.path.join(r.root, name), symlinks=True)
            r.git('remote', 'set-url', 'origin', r.origin)
        return r

    def cleanup(self):
        self.tmp.cleanup()

    def run_git(self, *args, cwd=None):
        return subprocess.run(('git', *args), cwd=cwd or self.work, env=self.env, capture_output=True, text=True)

    def git(self, *args, cwd=None):
        """git in [cwd] (the work clone by default); its stdout, the call asserted to succeed."""
        r = self.run_git(*args, cwd=cwd)
        assert r.returncode == 0, f'git {" ".join(args)}: {r.stderr}'
        return r.stdout

    def write(self, path, text, cwd=None):
        full = os.path.join(cwd or self.work, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(text)

    def commit(self, path, text, message):
        """Writes [path] in the work clone and commits it; the new HEAD's sha."""
        self.write(path, text)
        self.git('add', '--', path)
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD').strip()

    def set_config(self, old, new):
        """Replaces [old] by [new] in the work clone's omc/config.yaml (once, [old] asserted there) and commits it."""
        with open(os.path.join(self.work, 'omc', 'config.yaml'), encoding='utf-8') as f:
            text = f.read()
        assert old in text, f'{old!r} is not in omc/config.yaml'
        return self.commit(os.path.join('omc', 'config.yaml'), text.replace(old, new, 1), f'config: {new}')

    def advance_origin(self, path, text):
        """Pushes one commit writing [path] to origin.git's main from a second clone; that commit's sha. The work
        clone's origin/main is not fetched."""
        if not os.path.isdir(self.other):
            self.git('clone', '-q', self.origin, self.other, cwd=self.root)
        else:
            self.git('pull', '-q', '--ff-only', cwd=self.other)
        self.write(path, text, cwd=self.other)
        self.git('add', '--', path, cwd=self.other)
        self.git('commit', '-q', '-m', f'origin: {path}', cwd=self.other)
        self.git('push', '-q', 'origin', 'main', cwd=self.other)
        return self.git('rev-parse', 'HEAD', cwd=self.other).strip()

    def omc(self, *args):
        """`just omc <args>` in the work clone: the tool of this tree run with the clone's config."""
        return subprocess.run((sys.executable, '-I', TOOL, *args), cwd=self.work, env=self.env, capture_output=True,
                              text=True)


# The stub `npm`: logs its argv, cwd and CXXFLAGS as one JSON line; `run build` writes the CLI the build makes
NPM = """#!{python} -I
import json, os, sys
with open({log!r}, 'a', encoding='utf-8') as f:
    f.write(json.dumps({{'argv': sys.argv[1:], 'cwd': os.getcwd(), 'CXXFLAGS': os.environ.get('CXXFLAGS')}}) + '\\n')
if os.environ.get('FAKE_GITNEXUS', '') == 'npm-fails':
    sys.exit(1)
if sys.argv[1:] == ['run', 'build']:
    os.makedirs(os.path.join('dist', 'cli'), exist_ok=True)
    with open(os.path.join('dist', 'cli', 'index.js'), 'w', encoding='utf-8') as f:
        f.write('// built\\n')
"""

# The stub `node`: refuses a script that is not there, as node does; logs the CLI's arguments, the cwd and the
# GitNexus environment as one JSON line; `embeddings install` writes both runtime packages. `analyze` writes
# `.gitnexus/meta.json` in the cwd (lastCommit the cwd's HEAD, branch the `--branch`, repoPath the cwd, 40 nodes, 12
# vectors with `--embeddings`, else the vectors kept); `embeddings sync` gives the index its vectors; `clean --force`
# removes `.gitnexus/`. FAKE_GITNEXUS (comma-separated) bends them: `embed-fails` (analyze --embeddings exits 1),
# `no-vectors` (analyze --embeddings writes 0 vectors), and, on an incremental analyze (a store already there),
# `foreign-owner` (stamped branch `other`) and `still-stale` (lastCommit left as it was). A read verb (`query`,
# `context`, `impact`, `cypher`) prints `{"verb": …, "args": …}` on stdout, its args without `--repo` and `--branch`.
NODE = """#!{python} -I
import json, os, shutil, subprocess, sys
flags = set(os.environ.get('FAKE_GITNEXUS', '').split(','))
store = os.path.join(os.getcwd(), '.gitnexus')
meta_path = os.path.join(store, 'meta.json')
script, args = sys.argv[1], sys.argv[2:]
if not os.path.isfile(script):
    sys.exit(f'Error: Cannot find module {{script!r}}')
env = {{k: v for k, v in os.environ.items() if k.startswith('GITNEXUS_') or k == 'HF_HOME'}}
with open({log!r}, 'a', encoding='utf-8') as f:
    f.write(json.dumps({{'argv': args, 'cwd': os.getcwd(), 'env': env}}) + '\\n')
if args == ['embeddings', 'install']:
    for package in ('@huggingface/transformers', 'onnxruntime-node'):
        where = os.path.join(os.environ['GITNEXUS_EMBEDDING_RUNTIME_DIR'], 'node_modules', package)
        os.makedirs(where, exist_ok=True)
        with open(os.path.join(where, 'package.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps({{'name': package}}))
elif args[:1] == ['analyze']:
    embed = '--embeddings' in args
    if embed and 'embed-fails' in flags:
        sys.exit('Error: the embedding model could not be downloaded')
    existed = os.path.isfile(meta_path)
    old = json.load(open(meta_path, encoding='utf-8')) if existed else {{}}
    head = subprocess.run(('git', 'rev-parse', 'HEAD'), capture_output=True, text=True).stdout.strip()
    vectors = (0 if 'no-vectors' in flags else 12) if embed else old.get('stats', {{}}).get('embeddings', 0)
    meta = {{'lastCommit': old['lastCommit'] if existed and 'still-stale' in flags else head,
            'branch': 'other' if existed and 'foreign-owner' in flags else args[args.index('--branch') + 1],
            'repoPath': os.getcwd(), 'stats': {{'nodes': 40, 'embeddings': vectors}}}}
    os.makedirs(store, exist_ok=True)
    json.dump(meta, open(meta_path, 'w', encoding='utf-8'))
elif args[:2] == ['embeddings', 'sync']:
    meta = json.load(open(meta_path, encoding='utf-8'))
    meta['stats']['embeddings'] = 12
    json.dump(meta, open(meta_path, 'w', encoding='utf-8'))
elif args == ['clean', '--force']:
    shutil.rmtree(store, ignore_errors=True)
elif args[:1] and args[0] in ('query', 'context', 'impact', 'cypher'):
    print(json.dumps({{'verb': args[0], 'args': args[1:args.index('--repo')]}}))
"""


class FakeGitNexus:
    """The fake fork under [root]: `fork.git`, a bare repository whose `main` holds `gitnexus-shared/package.json` and
    `gitnexus/package.json` (`.sha` its tip, `.advance()` one more commit); `bin/`, the stub `npm` and `node`, which
    log to `.npm_log` and `.node_log`; `.home`, the temporary `HOME` the install goes under, `.preinstall()` an
    install's result written there at once. `.env(base_env)` is the environment a case runs the tool in;
    `.configure(repo)` points a `Repo`'s `gitnexus` pin at this fork."""

    def __init__(self, root, git_env):
        self.root = root
        self.git_env = git_env
        self.origin = os.path.join(root, 'fork.git')
        self.work = os.path.join(root, 'fork')
        self.home = os.path.join(root, 'home')
        self.bin = os.path.join(root, 'bin')
        self.npm_log = os.path.join(root, 'npm.log')
        self.node_log = os.path.join(root, 'node.log')
        os.makedirs(self.home)
        os.makedirs(self.bin)
        for name, text, log in (('npm', NPM, self.npm_log), ('node', NODE, self.node_log)):
            path = os.path.join(self.bin, name)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text.format(python=sys.executable, log=log))
            os.chmod(path, 0o755)
        self.git('init', '-q', '--bare', '-b', 'main', self.origin, cwd=root)
        self.git('clone', '-q', self.origin, self.work, cwd=root)
        self.git('symbolic-ref', 'HEAD', 'refs/heads/main')
        self.version = 0
        self.sha = self.advance()

    def git(self, *args, cwd=None):
        r = subprocess.run(('git', *args), cwd=cwd or self.work, env=self.git_env, capture_output=True, text=True)
        assert r.returncode == 0, f'git {" ".join(args)}: {r.stderr}'
        return r.stdout

    def advance(self):
        """One more commit on the fork's main, pushed; its sha, also `.sha`."""
        self.version += 1
        for package in ('gitnexus-shared', 'gitnexus'):
            path = os.path.join(self.work, package, 'package.json')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({'name': package, 'version': f'1.0.{self.version}'}) + '\n')
        self.git('add', '--', 'gitnexus-shared/package.json', 'gitnexus/package.json')
        self.git('commit', '-q', '-m', f'fork {self.version}')
        self.git('push', '-q', 'origin', 'main')
        self.sha = self.git('rev-parse', 'HEAD').strip()
        return self.sha

    def env(self, base_env, path=None):
        """[base_env] with `HOME` the temporary one, `PATH` the stubs first (or [path] when given), and no GitNexus
        variable of the caller's."""
        env = {k: v for k, v in base_env.items() if not k.startswith('GITNEXUS_') and k != 'HF_HOME'}
        env.update(HOME=self.home, PATH=path if path is not None else self.bin + os.pathsep + base_env.get('PATH', ''))
        return env

    def preinstall(self):
        """What a finished install leaves under `.home`, written without the clone and the build: the built CLI and
        both runtime packages, for the cases that start from an installed GitNexus. Not at the pin: `install` would
        build it again."""
        base = os.path.join(self.home, '.omc', 'tools', 'gitnexus')
        files = [os.path.join(base, 'gitnexus', 'gitnexus', 'dist', 'cli', 'index.js')]
        files += [os.path.join(base, 'embeddings', 'runtime', 'node_modules', p, 'package.json')
                  for p in ('@huggingface/transformers', 'onnxruntime-node')]
        for path in files:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write('{}\n')

    def configure(self, repo):
        """Rewrites [repo]'s omc/config.yaml `gitnexus` pin (its `origin:` and `commit:` lines) to this fork at `.sha`
        and commits it; the values are JSON strings, which YAML reads as they are."""
        path = os.path.join(repo.work, 'omc', 'config.yaml')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        text = re.sub(r'^(\s+)origin: .*$', lambda m: f'{m.group(1)}origin: {json.dumps(self.origin)}', text,
                      flags=re.M)
        text = re.sub(r'^(\s+)commit: .*$', lambda m: f'{m.group(1)}commit: {json.dumps(self.sha)}', text, flags=re.M)
        repo.commit('omc/config.yaml', text, 'pin the fake fork')
