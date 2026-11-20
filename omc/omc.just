# omc's recipes, imported by the project's justfile (`import 'omc/omc.just'`); the project's own recipes stay there.
# Every Python tool runs in the uv project omc/ (omc/pyproject.toml and omc/uv.lock), its environment in the project's
# .cache/venv; `--frozen` installs exactly the lock and never resolves
omc_py := "UV_PROJECT_ENVIRONMENT=" + quote(justfile_directory() / ".cache/venv") + " uv run --project omc --frozen python -I -X pycache_prefix=.cache/pycache"

# The omc/ pipeline's tool, its config omc/config.yaml: enter, record, plan, git, rebase, impact, gate, reviewed, settled, models, handoff, lint, gitnexus, title, shell-integration, shots, todos (--help)
[no-exit-message]
[positional-arguments]
@omc *ARGS:
    {{omc_py}} omc/tools/omc.py "$@"

# Start a piece of work: a brief (under paths.briefs), a sentence, or --deferred <ids> (the brief made of those deferred entries of the origin's base log), from any checkout; first, in this shell before any Python, the primary checkout pulled (fetch and fast-forward of origin/<base>, when it is on <base> with no tracked changes; any failure left to design.py), a lone brief path made absolute, then the primary's pulled justfile runs _design-start, so the pulled recipe, uv.lock and design.py run: refused unless the primary checkout is on the base branch, clean and not diverged from its origin; the slug, then in line behind another start: the pull again (a move a [warn]), the worktree <branch prefix><slug> from the origin's base (entered again when the branch exists); out of the line, GitNexus installed and its index refreshed (left to another start refreshing it; neither stops the start); then the interactive shell in it, which runs `claude … /brainstorm`; base and branch prefix from omc/config.yaml; one line per step on stderr
[no-exit-message]
[positional-arguments]
design *ARGS:
    #!/usr/bin/env bash
    set -u
    common=$(git rev-parse --path-format=absolute --git-common-dir) || exit 2
    primary=$(dirname "$common")
    base=$(sed -n 's/^base:[[:space:]]*\([^[:space:]#]*\).*/\1/p' "$primary/omc/config.yaml" 2>/dev/null)
    if [ -n "$base" ] && [ "$(git -C "$primary" symbolic-ref --short -q HEAD)" = "$base" ] \
        && [ -z "$(git -C "$primary" status --porcelain --untracked-files=no)" ]; then
        git -C "$primary" fetch -q origin "$base" >/dev/null 2>&1 \
            && git -C "$primary" merge -q --ff-only "origin/$base" >/dev/null 2>&1
    fi
    if [ $# -eq 1 ] && [ "${1%.md}" != "$1" ] && [ -f "$1" ]; then
        set -- "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
    fi
    exec {{quote(just_executable())}} --justfile "$primary"/{{quote(file_name(justfile()))}} \
        --working-directory "$primary" _design-start {{quote("--origin=" + invocation_directory())}} "$@"

# design's second half, run from the primary's pulled justfile: design.py with the recipe's --origin= and arguments
[no-exit-message]
[positional-arguments]
@_design-start *ARGS:
    {{omc_py}} omc/tools/design.py "$@"

# The decision log's tool (omc/tools/decisions/FORMAT.md), the log at paths.decision_log: add-decision, apply-decision, defer, undefer, confirm, overrule, update, remove, show, list, pending, guard, trim, renumber, check (--help)
[positional-arguments]
decisions *ARGS:
    {{omc_py}} omc/tools/decisions/decisions.py "$@"

# The mechanical checks of the decisions in one command (omc/tools/decisions/FORMAT.md › The integrity check): the log, every entry of the branch with its row in the branch's record, the vault's links, the guard, and (implementation, the default) nothing recorded unapplied and, without --defer-questions, no open question and no entry left disagreed (both wait for the push gate); no build, no test; /audit's push and the pre-push hook pass neither flag, verify's step --defer-questions; [--phase design|implementation] [--defer-questions]
[positional-arguments]
design-integrity-check *ARGS:
    {{omc_py}} omc/tools/decisions/integrity.py "$@"

# Check the links of the docs vault, the top folder of paths.decision_log (no LLM), in the files of paths.links (absent: the paths.protected files and the question files), the paths.themes files and the log: escapes, dead files and headings, link form, unlinked references, wrong targets, the pins of the log and the question files, the stories' rule references; then the project's own checks, omc/bin/links-check, when it has one (red when either is)
links-check:
    #!/usr/bin/env bash
    set -u
    (cd omc/skills/reconcile-links/tool && dart run bin/links_check.dart)
    rc=$?
    if [ -f omc/bin/links-check ] && [ -x omc/bin/links-check ]; then
        omc/bin/links-check || { r=$?; [ "$rc" -ne 0 ] || rc=$r; }
    fi
    exit $rc

# Pin every link of the log and the question files whose target is gone to a commit on the base branch (`base` of omc/config.yaml) where its target existed; prints how many, and what it could not pin
pin-links:
    cd omc/skills/reconcile-links/tool && dart run bin/pin_links.dart
