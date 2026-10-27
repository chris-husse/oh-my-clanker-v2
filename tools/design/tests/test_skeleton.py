import subprocess, sys

def test_package_imports():
    import design  # noqa: F401

def test_console_scripts_are_declared():
    import tomllib, pathlib
    data = tomllib.loads((pathlib.Path(__file__).parents[2] / 'pyproject.toml').read_text())
    scripts = data['project']['scripts']
    assert set(scripts) == {'design-decisions', 'design-links-check', 'design-pin-links',
                            'design-ensure-up-to-date', 'design-mark-up-to-date', 'design-recorded-at'}

def test_repo_fixture_is_a_git_repo_on_main(repo):
    out = subprocess.run(['git', '-C', str(repo), 'branch', '--show-current'], capture_output=True, text=True)
    assert out.stdout.strip() == 'main'
    assert (repo / 'docs').is_dir()
