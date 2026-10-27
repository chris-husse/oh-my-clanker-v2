import subprocess, pathlib, pytest

def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True).stdout

@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'repo'
    root.mkdir()
    git(root, 'init', '-q', '-b', 'main')
    git(root, 'config', 'user.name', 'test')
    git(root, 'config', 'user.email', 'test@example.com')
    git(root, 'commit', '-q', '--allow-empty', '-m', 'init')
    (root / 'docs').mkdir()
    (root / 'tools').mkdir()
    corpus_yaml(root)
    return root

def corpus_yaml(root, **overrides):
    values = dict(root='docs', log='decision-log.md', corpus=['design/**/*.md', 'e2e-tests/**/*.md'],
                  history=['reviews/**'], generated=[], exclude=['superpowers/**'])
    values.update(overrides)
    import yaml
    (root / 'tools' / 'corpus.yaml').write_text(yaml.safe_dump(values, sort_keys=False))

def commit_all(root, message):
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '-m', message)
    return git(root, 'rev-parse', 'HEAD').strip()
