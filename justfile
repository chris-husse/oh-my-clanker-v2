# The decision log's tool: show, list, search, history, check, new-section, add-decision, add-note, apply-decision, close-section
[positional-arguments]
decisions *ARGS:
    uv run --project tools design-decisions "$@"

# Check every link of docs/ (no LLM): escapes, dead files and headings, link form, unlinked rulings, wrong targets, stray files, pins of the log and the reviews
[positional-arguments]
links-check *ARGS:
    uv run --project tools design-links-check "$@"

# Pin every link of the decision log and the reviews whose line comes from main to a commit on main where its target existed (docs/LINKS.md)
pin-links:
    uv run --project tools design-pin-links

# Is every generated file current with its inputs (DVC, tools/stages.yaml)? OK, or the stale stages and "run /ensure-up-to-date" (--full, --target <path>, --warnings-as-errors, --root <dir>)
[positional-arguments]
ensure-up-to-date *ARGS:
    uv run --project tools design-ensure-up-to-date "$@"

# Record stages as regenerated and current; the last step of each regenerating skill
[positional-arguments]
mark-up-to-date +STAGES:
    uv run --project tools design-mark-up-to-date "$@"

# The commit that last recorded a stage (exit 1: never)
[positional-arguments]
recorded-at STAGE:
    uv run --project tools design-recorded-at "$@"

# The tools' tests, the log's integrity, every link, every generated file
build:
    uv run --project tools pytest tools/design/tests -q
    just decisions check
    just links-check
    just ensure-up-to-date

# Once per clone: every push runs the freshness check and refuses unpinned links from main (.githooks/pre-push)
install-hooks:
    git config core.hooksPath .githooks
