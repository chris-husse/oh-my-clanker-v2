# oh-my-clanker v2's own recipes; omc/ is what projects receive.
# v2 runs its own pipeline too (`just design`, `just omc`, …): installed into itself by `just install . --no-launch`,
# its .claude/skills link the working tree's omc/ skills.
import 'omc/omc.just'

py := "UV_PROJECT_ENVIRONMENT=" + quote(justfile_directory() / ".cache/venv") + " uv run --project omc --frozen python -I -X pycache_prefix=.cache/pycache"

# Every Python test script of omc/ and install/, one after the other; all run, and it fails when any is red.
test:
    #!/usr/bin/env bash
    set -uo pipefail
    shopt -s nullglob
    for f in omc/tools/test_omc_*.py omc/tools/decisions/test_*.py install/test_*.py; do
        echo "== $f"
        {{py}} "$f" || rc=1
    done
    exit ${rc:-0}

# Install omc/ into a project (the top of a clean git work tree), or update it there by a three-way merge from the commit in its omc/VERSION, then start `claude /oh-my-clanker` in it; [--no-launch]
[positional-arguments]
install PROJECT *ARGS:
    @shift; {{py}} install/install.py {{quote(join(invocation_directory(), PROJECT))}} "$@"
