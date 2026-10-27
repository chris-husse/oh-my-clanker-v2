# Design Folder Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give this repository the design-management layout, decision log, review conventions, link rules and freshness chain, as one Python package plus nine skills, and convert the existing design and decision log into it.

**Architecture:** One uv-managed Python package `tools/design/` holds a shared Markdown parser (`folder.py`), the log parser and writer (`log.py`), and four command modules (`decisions.py`, `links.py`, `pins.py`, `freshness.py`), each a console script behind a justfile recipe. The high-level design moves from `design/` to `docs/design/`; `tools/corpus.yaml` declares what `docs/` contains. The skills under `.claude/skills/` are copies of the source skills with every product word and reference kind removed. The old question log becomes one open review section with three applied rulings, and its open questions stay in the review file.

**Tech Stack:** Python 3.12, uv, pyyaml, dvc 3.67.1, pytest, git, just, bash.

**Spec:** `docs/superpowers/specs/2026-10-27-design-folder-design.md`. **Reference:** `docs/superpowers/plans/2026-10-27-design-folder-reference.md` (the source tools described function by function; read the section your task names before writing code). **Source repository:** `/home/openclaw/Projects/apuntalo.co` at commit `467e9e9`, read-only.

## Global Constraints

- Python 3.12; dependencies: `pyyaml`, `dvc==3.67.1`; dev: `pytest`. Nothing else. No Dart anywhere in this repository.
- No product word of the source anywhere in this repository: not `apuntalo`, `creditosya`, nor any of the source's actors or domain words (`worker`, `intake`, `payout`, `supervisor`, `collector`, `client`, `loan`, `credit`, `lending`, `route`, `shift`), nor `story`, `stories`, `scene`, `screen`, `mock`, `Confluence`, `Flutter`, `Dart`, `fvm`, `Obsidian`, `vault`. Task 15 greps for them; a hit fails the task. (`client` in the sense of an MCP client is allowed only inside `docs/design/`, which is existing text.)
- A reference is a link; the tools know one id shape, the log's `N.k` and `§N`. No regex for any other reference kind.
- The log is append-only and the tool is its only writer; the tests prove it.
- Every commit message ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Commands run from the repository root unless a step says otherwise. The repository is `/home/openclaw/Projects/oh-my-clanker-v2`, branch `feature/design-folder`.
- Tests: `uv run --project tools pytest tools/design/tests -q`. Every task ends green.
- Problem lines are `PROBLEM: <file>:<line>: <kind>: <detail>` and warnings `WARNING: …`; the summary is `OK` or `<n> problems`. Skills grep these.

---

### Task 1: The package skeleton, justfile and uv project

**Files:**
- Create: `tools/pyproject.toml`, `tools/design/__init__.py`, `tools/design/tests/__init__.py`, `tools/design/tests/conftest.py`, `tools/corpus.yaml`, `tools/stages.yaml`, `justfile`, `.gitignore`, `.dvc/config`, `.dvcignore`
- Test: `tools/design/tests/test_skeleton.py`

**Interfaces:**
- Produces: the fixture `repo(tmp_path)` in `conftest.py` returning a `pathlib.Path` of a fresh git repository with user config set, an initial empty commit on `main`, and a `docs/` folder; `corpus_yaml(path, **overrides)` writing a `tools/corpus.yaml` with the defaults of the spec. Every later test module uses them.

- [x] **Step 1: Write the failing test**

```python
# tools/design/tests/test_skeleton.py
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
```

- [x] **Step 2: Create the project**

```toml
# tools/pyproject.toml
[project]
name = "design"
version = "0.1.0"
description = "The design folder's tools: decision log, links, pins, freshness"
requires-python = ">=3.12"
dependencies = ["pyyaml>=6.0", "dvc==3.67.1"]

[project.scripts]
design-decisions = "design.decisions:main"
design-links-check = "design.links:main"
design-pin-links = "design.pins:main"
design-ensure-up-to-date = "design.freshness:check_main"
design-mark-up-to-date = "design.freshness:mark_main"
design-recorded-at = "design.freshness:recorded_at_main"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["design"]

[tool.pytest.ini_options]
testpaths = ["design/tests"]
```

`tools/design/__init__.py` is empty. `tools/design/tests/conftest.py`:

```python
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
```

`tools/corpus.yaml` exactly as the spec's section 4 (`root: docs`, `log: decision-log.md`, `corpus: [design/**/*.md, e2e-tests/**/*.md]`, `history: [reviews/**]`, `generated: []`, `exclude: [superpowers/**]`). `tools/stages.yaml`:

```yaml
# The chain of generated files: what each stage reads, what it writes, which skill regenerates it.
# `just ensure-up-to-date` generates dvc.yaml from this file; edit this, never dvc.yaml.
dvc: 3.67.1
stages: {}
```

`.dvc/config` holds `[core]\n    analytics = false\n`; `.dvcignore` holds `cache\nconfig\ntmp\n`. `.gitignore`: `.cache/`, `tools/.venv/`, `__pycache__/`, `.dvc/cache/`, `.dvc/tmp/`.

`justfile`:

```make
# The decision log's tool: show, list, search, history, check, new-section, add-decision, add-note, apply-decision, close-section
decisions *ARGS:
    uv run --project tools design-decisions {{ARGS}}

# Check every link of docs/ (no LLM): escapes, dead files and headings, link form, unlinked rulings, wrong targets, stray files, pins of the log and the reviews
links-check *ARGS:
    uv run --project tools design-links-check {{ARGS}}

# Pin every link of the decision log and the reviews whose line comes from main to a commit on main where its target existed (docs/LINKS.md)
pin-links:
    uv run --project tools design-pin-links

# Is every generated file current with its inputs (DVC, tools/stages.yaml)? OK, or the stale stages and "run /ensure-up-to-date" (--full, --target <path>, --warnings-as-errors, --root <dir>)
ensure-up-to-date *ARGS:
    uv run --project tools design-ensure-up-to-date {{ARGS}}

# Record stages as regenerated and current; the last step of each regenerating skill
mark-up-to-date +STAGES:
    uv run --project tools design-mark-up-to-date {{STAGES}}

# The commit that last recorded a stage (exit 1: never)
recorded-at STAGE:
    uv run --project tools design-recorded-at {{STAGE}}

# The tools' tests, the log's integrity, every link, every generated file
build:
    uv run --project tools pytest tools/design/tests -q
    just decisions check
    just links-check
    just ensure-up-to-date

# Once per clone: every push runs the freshness check and refuses unpinned links from main (.githooks/pre-push)
install-hooks:
    git config core.hooksPath .githooks
```

- [x] **Step 3: Run `uv sync --project tools` and the test**

Run: `uv sync --project tools && uv run --project tools pytest tools/design/tests -q`
Expected: 3 passed. (`uv run --project tools dvc --version` prints `3.67.1`.)

- [x] **Step 4: Commit**

```bash
git add tools justfile .gitignore .dvc/config .dvcignore
git commit -m "tools: the design package skeleton, uv project, justfile" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `folder.py`: the Markdown parser and the docs folder

**Files:**
- Create: `tools/design/folder.py`
- Test: `tools/design/tests/test_folder.py`

**Reference:** sections A (lines 52-180 of the source), B.1 to B.5.

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class Heading: line: int; level: int; text: str
@dataclass
class Link:
    start: int; end: int; text_start: int; text_end: int; dest: str
    image: bool = False; angle: bool = False; title: str | None = None
    @property
    def pin(self) -> str | None            # PIN_RE group 1 of the title
    @property
    def path_and_fragment(self) -> tuple[str, str | None]   # dest split at the first '#'
def mask(text: str) -> str                 # code, fences, comments blanked; length kept
def headings_of(text: str) -> list[Heading]
def scan_links(masked: str) -> list[Link]
def unlink(text: str) -> str
def encode_anchor(heading: str) -> str
def decode_percent(s: str) -> str
def github_slug(heading: str) -> str
@dataclass(frozen=True)
class Target: file: str; heading: str | None
def link_to(from_rel: str, target: Target) -> str
def resolve(from_rel: str, dest: str) -> tuple[str, str | None]   # (normalized target rel, fragment); '' path means from_rel itself
def escapes(target_rel: str) -> bool       # '..' or starts with '../'
@dataclass
class Corpus:
    root: str; log: str; corpus: list[str]; history: list[str]; generated: list[str]; exclude: list[str]
    @staticmethod
    def load(repo_root: Path) -> 'Corpus'   # reads <repo_root>/tools/corpus.yaml
    def matches(self, patterns, rel) -> bool
    def is_history(self, rel) -> bool; def is_generated(self, rel) -> bool; def is_excluded(self, rel) -> bool; def is_corpus(self, rel) -> bool
def glob_to_regex(pattern: str) -> re.Pattern   # ** across folders, * within one, ?, [..], {a,b}; anchored
class Folder:
    root: Path; files: list[str]            # posix, relative, sorted
    @staticmethod
    def git(root) -> 'Folder'               # git ls-files --cached --others --exclude-standard -z, existing on disk
    @staticmethod
    def dir(root) -> 'Folder'
    @property
    def markdown(self) -> list[str]
    def text(self, rel) -> str; def headings(self, rel) -> list[Heading]; def slugs(self, rel) -> dict[str, str]
    def is_file(self, rel) -> bool; def is_dir(self, rel) -> bool
    def has_heading(self, rel, heading) -> bool
def repo_root(start: Path | None = None) -> Path   # first ancestor with .git
```

- [x] **Step 1: Write the failing tests** (port B.12 unlink_test and the parser cases of A's test list; these are the minimum)

```python
# tools/design/tests/test_folder.py
from design.folder import *

def test_mask_keeps_length_and_newlines():
    t = "a `x` b\n```\ncode\n```\n<!-- c\nd -->e"
    m = mask(t)
    assert len(m) == len(t) and m.count('\n') == t.count('\n') and m.endswith('e') and 'code' not in m and 'x' not in m

def test_headings_keep_raw_text_and_skip_fences():
    t = "# A\n```\n# not\n```\n## W16 — A `x` phone\n"
    assert [(h.line, h.level, h.text) for h in headings_of(t)] == [(1, 1, 'A'), (5, 2, 'W16 — A `x` phone')]

def test_anchor_encoding_and_decoding():
    assert encode_anchor('2.4 The cache (`~/.omc2/`)') == '2.4%20The%20cache%20(%60~/.omc2/%60)'
    assert decode_percent('bad%zz%C3%20end') == 'bad%zz%C3 end'
    assert decode_percent('phon%65') == 'phone'

def test_scan_links_parentheses_titles_pins_images():
    t = 'see [a](x.md#Receive%20(QR):%20ok "git:0123456789ab") ![i](p.png) [[wiki]] [e](<a b.md>)'
    ls = scan_links(mask(t))
    assert [(l.dest, l.title, l.pin, l.image, l.angle) for l in ls] == [
        ('x.md#Receive%20(QR):%20ok', 'git:0123456789ab', '0123456789ab', False, False),
        ('p.png', None, None, True, False), ('a b.md', None, None, False, True)]
    assert t[ls[0].text_start:ls[0].text_end] == 'a'

def test_unlink_keeps_images_and_code():
    t = '[a](x.md "git:0123456789ab") ![i](p.png) `[c](d)`'
    assert unlink(t) == 'a ![i](p.png) `[c](d)`'

def test_resolve_and_link_to():
    assert resolve('reviews/r.md', '../design/01-x.md#1.1%20A') == ('design/01-x.md', '1.1%20A')
    assert resolve('decision-log.md', '#1.1%20A') == ('decision-log.md', '1.1%20A')
    assert escapes(resolve('design/a.md', '../../out.md')[0])
    assert link_to('reviews/r.md', Target('design/01-x.md', '1.1 A')) == '../design/01-x.md#1.1%20A'
    assert link_to('decision-log.md', Target('decision-log.md', '1.1 A')) == '#1.1%20A'

def test_glob_to_regex():
    assert glob_to_regex('design/**/*.md').match('design/a/b.md') and glob_to_regex('design/**/*.md').match('design/b.md')
    assert not glob_to_regex('design/*.md').match('design/a/b.md')
    assert glob_to_regex('reviews/**').match('reviews/iterations/x.md')
    assert glob_to_regex('{a,b}/*.md').match('b/c.md')

def test_folder_git_lists_tracked_and_untracked_existing_files(repo):
    (repo / 'docs' / 'a.md').write_text('# A\n')
    (repo / 'docs' / 'b.md').write_text('# B\n')
    from design.tests.conftest import commit_all
    commit_all(repo, 'a')
    (repo / 'docs' / 'b.md').unlink()
    (repo / 'docs' / 'c.md').write_text('# C\n')
    f = Folder.git(repo / 'docs')
    assert f.files == ['a.md', 'c.md'] and f.markdown == ['a.md', 'c.md']
    assert f.has_heading('a.md', 'A') and not f.has_heading('a.md', 'B')

def test_corpus_load_and_matching(repo):
    c = Corpus.load(repo)
    assert c.is_history('reviews/x.md') and c.is_corpus('design/01-a.md') and c.is_excluded('superpowers/specs/s.md')
    assert not c.is_generated('design/01-a.md')
```

- [x] **Step 2: Run them to see them fail**

Run: `uv run --project tools pytest tools/design/tests/test_folder.py -q`
Expected: ImportError.

- [x] **Step 3: Implement `folder.py`** following reference B.2 to B.5 exactly (masking, fences, code spans with the `](` exception, `destinationAt` with both forms, `_title`, percent decoding byte by byte, anchors, slugs) and A's `scan_links`/`unlink`. `Folder.git` runs `git -C <root> ls-files --cached --others --exclude-standard -z .`. `Corpus.load` reads `tools/corpus.yaml` with `yaml.safe_load` and compiles each glob with `glob_to_regex`. `resolve` uses `posixpath.normpath(posixpath.join(posixpath.dirname(from_rel), decode_percent(path)))`.

- [x] **Step 4: Run the tests**

Run: `uv run --project tools pytest tools/design/tests -q`
Expected: all pass.

- [x] **Step 5: Commit**

```bash
git add tools/design/folder.py tools/design/tests/test_folder.py
git commit -m "tools: folder.py, the Markdown parser and the docs folder" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: `log.py`: the decision log's parser and writer

**Files:**
- Create: `tools/design/log.py`
- Test: `tools/design/tests/test_log.py`

**Reference:** section A (source lines 299-447, 620-660), the regexes block, the entry example.

**Interfaces:**
- Consumes: `folder.scan_links`, `folder.mask`, `folder.unlink`, `folder.headings_of`.
- Produces:

```python
FIELDS = ['Context', 'Decision', 'Affected', 'Supersedes', 'Source', 'Status']
SECTION_RE, ENTRY_RE, FIELD_RE, ANSWERS_RE, STATUS_RE, RULING_ID_RE, LOG_SECTION_ID_RE   # as the reference
@dataclass
class Entry:
    id: str; section: int; number: int; title: str; line: int; end: int   # line 1-based heading line; end exclusive, trailing blanks trimmed
    fields: dict[str, str]; answers: str | None; lines: list[str]        # lines: heading through end
    def kind(self) -> str          # 'note' | 'decision' | 'malformed'
    def status(self) -> str        # 'note' | 'recorded' | 'applied' | 'malformed'
    def date(self) -> str | None   # the recorded date
    def text(self) -> str          # the entry's lines joined
    def links(self) -> list[Link]  # every link in the entry text
    def link_free(self) -> str     # unlink(text())
    def affected(self) -> list[Target]     # the Affected field's links as (file rel to docs, decoded heading)
    def supersedes(self) -> list[str]      # ids ('1.1') and sections ('§1')
@dataclass
class Section:
    n: int; title: str; dates: str; line: int; review_file: str | None; review_open: bool; iterations: int | None; entries: list[Entry]
@dataclass
class Log:
    lines: list[str]; sections: list[Section]; entries: dict[str, Entry]
    @property
    def open_section(self) -> Section | None
def parse_log(text: str) -> Log
def render_entry(entry_id: str, title: str, fields: dict[str, str], answers: str | None = None) -> list[str]   # heading, blank, fields in FIELDS order (empty skipped), Answers line, blank
def write_log(path: Path, lines: list[str]) -> None     # joins with '\n', trailing newline
def header_lines() -> list[str]   # ['# Decision Log', '', '*Append-only. Every ruling and its reasoning, dated.*', '']
def entry_link(entry_id: str, title: str) -> str   # '#1.2%20Title'
```

- [x] **Step 1: Write the failing tests**

```python
# tools/design/tests/test_log.py
from design.log import *

LOG = """# Decision Log

*Append-only. Every ruling and its reasoning, dated.*

## 1. Review: first (2026-10-27)

A description.
Review file (open): docs/reviews/2026-10-16-first.md

### 1.1 First ruling

**Context.** Because of [2.1](design/02-x.md#2.1%20Title).
**Decision.** Do it.
**Affected.** [2.1](design/02-x.md#2.1%20Title)
**Source.** [R1. A](reviews/2026-10-16-first.md#R1.%20A)
**Status.** recorded 2026-10-27 · applied 2026-10-27
Answers: R1

### 1.2 Second

**Context.** c
**Decision.** d
**Supersedes.** [1.1](#1.1%20First%20ruling), [§1](#1.%20Review:%20first%20(2026-10-27))
**Status.** recorded 2026-10-27

### 1.3 Parked

note text
**Status.** note

"""

def test_sections_and_entries():
    log = parse_log(LOG)
    s = log.sections[0]
    assert (s.n, s.title, s.review_file, s.review_open, s.iterations) == (1, 'Review: first', 'docs/reviews/2026-10-16-first.md', True, None)
    assert list(log.entries) == ['1.1', '1.2', '1.3'] and log.open_section is s

def test_kind_status_date_affected_supersedes():
    log = parse_log(LOG)
    e = log.entries['1.1']
    assert (e.kind(), e.status(), e.date(), e.answers) == ('decision', 'applied', '2026-10-27', 'R1')
    assert e.affected() == [Target('design/02-x.md', '2.1 Title')]
    assert log.entries['1.2'].supersedes() == ['1.1', '§1'] and log.entries['1.2'].status() == 'recorded'
    assert log.entries['1.3'].kind() == 'note'

def test_body_excludes_the_next_heading_and_trailing_blanks():
    log = parse_log(LOG)
    assert log.entries['1.2'].lines[-1] == '**Status.** recorded 2026-10-27'

def test_malformed_status_and_missing_fields():
    text = LOG.replace('**Status.** recorded 2026-10-27\n', '**Status.** legacy\n')
    assert parse_log(text).entries['1.2'].status() == 'malformed'
    text = LOG.replace('**Decision.** d\n', '')
    assert parse_log(text).entries['1.2'].kind() == 'malformed'

def test_render_entry_skips_empty_fields_and_keeps_order():
    lines = render_entry('1.4', 'T', {'Decision': 'd', 'Context': 'c', 'Affected': '', 'Status': 'recorded 2026-10-27'}, 'R2')
    assert lines == ['### 1.4 T', '', '**Context.** c', '**Decision.** d', '**Status.** recorded 2026-10-27', 'Answers: R2', '']

def test_link_free_text_drops_links_not_words():
    assert parse_log(LOG).entries['1.1'].link_free().splitlines()[2] == '**Context.** Because of 2.1.'
```

- [x] **Step 2: Run them to see them fail**. Expected: ImportError.

- [x] **Step 3: Implement `log.py`** porting source lines 299-447 and 620-640 with one Affected field, no legacy kind, the four status forms. `parse_log` walks lines, tracks fences (FENCE_RE) so a `###` inside a fence is not an entry, opens a `Section` on SECTION_RE, an `Entry` on ENTRY_RE, collects fields with FIELD_RE and the Answers line, and reads `Review file (open):`, `Review file:` and `Iterations:` lines of a section. An entry is `malformed` when it has a Status that fails STATUS_RE, or is a decision (has Context or Decision) lacking either, or has no Status line at all.

- [x] **Step 4: Run the tests**: all pass.

- [x] **Step 5: Commit**

```bash
git add tools/design/log.py tools/design/tests/test_log.py
git commit -m "tools: log.py, the decision log's parser and writer" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `decisions.py`: the log's commands

**Files:**
- Create: `tools/design/decisions.py`
- Test: `tools/design/tests/test_decisions.py`

**Reference:** section A (source lines 448-810); the surviving test list; spec sections 6.2 and 6.3.

**Interfaces:**
- Consumes: `log.*`, `folder.Folder`, `folder.Corpus`, `folder.resolve`, `folder.encode_anchor`, `folder.decode_percent`, `folder.repo_root`.
- Produces:

```python
class RefError(Exception): ...
def load(docs: Path) -> tuple[Folder, Log]
def resolve_link_arg(folder: Folder, log: Log, arg: str) -> tuple[Target, str]   # 'design/02-x.md#2.1 Title' -> (Target, markdown link relative to the log); '1.1' and '§1' resolve against the log; raises RefError
def search(folder, log, affected=None, source=None, supersedes=None, status=None, section=None, since=None, text=None) -> list[Entry]
def history(folder, log, ref: str) -> list[tuple[Entry, list[str]]]   # entries hitting the target, each with its direct later ids
def format_oneline(e) -> str          # '1.2  recorded 2026-10-27  Second'
def check(folder, log, head_text: str | None) -> list[str]   # 'PROBLEM: decision-log.md:<line>: <kind>: <detail>'
def new_section(folder, log, title, description=None, review_file=None, today=None) -> int
def add_decision(folder, log, title, context, decision, affected=(), supersedes=(), source=None, answers=None, today=None) -> str
def add_note(folder, log, title, text) -> str
def apply_decision(folder, log, entry_id, affected=None, no_change=False, today=None) -> None
def close_section(folder, log, n, iterations, today=None) -> None
def head_log_text(docs: Path) -> str | None     # git show HEAD:<prefix>decision-log.md
def main(argv=None) -> int
```

CLI (argparse, `prog='design-decisions'`, global `--docs <dir>` defaulting to `<repo_root>/docs`): `show <id>...`; `list [--section N]`; `search [--affected P] [--source P] [--supersedes ID] [--status S] [--section N] [--since DATE] [--text REGEX] [--oneline | --ids]`; `history <ref>`; `check`; `new-section --title T [--description D] [--review-file F]`; `add-decision --title T --context C --decision D [--affected L ...] [--supersedes ID ...] [--source L] [--answers A]` (prints the new id); `add-note --title T --text X` (prints the id); `apply-decision --id ID (--affected L ... | --no-change)`; `close-section --section N --iterations K`. Writing commands exit 1 with the RefError message on stderr and leave the file untouched. `check` prints its lines and exits 1 when any.

The check kinds: `duplicate-id`, `out-of-order`, `wrong-section`, `malformed-entry` (a decision without Context or Decision, an unknown field, a note with fields other than Status), `malformed-status`, `dead-link` (a link of a recorded entry whose target file or heading does not exist; pinned links skipped), `edited` (an applied or note entry in `head_text` whose link-free text differs), `removed` (an entry in `head_text` missing now), `unresolved-section` (a `Review file (open):` naming a file that does not exist).

- [x] **Step 1: Write the failing tests**: port every name in reference A's surviving list into pytest functions over a fixture that writes `design/02-x.md` (`## 2.1 Title`, `## 2.2 Other`), `reviews/2026-10-16-first.md` (`## R1. A`, `## R2. B`) and the LOG of Task 3 into `repo/docs`, commits it, then exercises the functions and the CLI (`main([...])` with `--docs`). The essential assertions:

```python
def test_add_decision_writes_links_and_refuses_unresolvable(repo, docs):
    folder, log = load(docs)
    eid = add_decision(folder, log, 'T', 'c', 'd', affected=['design/02-x.md#2.2 Other'], source='reviews/2026-10-16-first.md#R2. B', answers='R2', today='2026-10-27')
    assert eid == '1.4'
    text = (docs / 'decision-log.md').read_text()
    assert '**Affected.** [2.2](design/02-x.md#2.2%20Other)' in text and '**Source.** [R2. B](reviews/2026-10-16-first.md#R2.%20B)' in text
    before = text
    with pytest.raises(RefError):
        add_decision(*load(docs), 'T', 'c', 'd', affected=['design/02-x.md#2.9 Nope'])
    assert (docs / 'decision-log.md').read_text() == before

def test_apply_replaces_the_affected_set_and_marks_applied(repo, docs):
    apply_decision(*load(docs), '1.2', affected=['design/02-x.md#2.1 Title'], today='2026-10-28')
    e = load(docs)[1].entries['1.2']
    assert e.status() == 'applied' and e.fields['Status'] == 'recorded 2026-10-27 · applied 2026-10-28'
    assert e.affected() == [Target('design/02-x.md', '2.1 Title')]

def test_apply_refuses_an_applied_entry_and_a_note(repo, docs):
    for eid in ('1.1', '1.3'):
        with pytest.raises(RefError): apply_decision(*load(docs), eid, no_change=True)

def test_history_follows_supersession(repo, docs):
    h = history(*load(docs), 'design/02-x.md#2.1 Title')
    assert [e.id for e, _ in h] == ['1.1'] and h[0][1] == ['1.2']

def test_search_by_affected_source_status(repo, docs):
    folder, log = load(docs)
    assert [e.id for e in search(folder, log, affected='design/02-x.md')] == ['1.1']
    assert [e.id for e in search(folder, log, source='reviews/')] == ['1.1']
    assert [e.id for e in search(folder, log, status='recorded')] == ['1.2']

def test_check_immutability_against_head(repo, docs):
    folder, log = load(docs)
    head = head_log_text(docs)
    assert check(folder, log, head) == []
    p = docs / 'decision-log.md'
    p.write_text(p.read_text().replace('**Decision.** Do it.', '**Decision.** Do not.'))
    assert any(': edited: 1.1' in line for line in check(*load(docs), head))

def test_close_section_and_new_section(repo, docs):
    close_section(*load(docs), 1, 2, today='2026-10-28')
    text = (docs / 'decision-log.md').read_text()
    assert 'Review file: docs/reviews/2026-10-16-first.md\nIterations: 2' in text and '## 1. Review: first (2026-10-27, refined 2026-10-28)' in text
    assert new_section(*load(docs), 'Second', today='2026-10-28') == 2

def test_cli_add_decision_prints_the_id_and_check_exit_code(repo, docs, capsys):
    assert main(['--docs', str(docs), 'add-decision', '--title', 'T', '--context', 'c', '--decision', 'd']) == 0
    assert capsys.readouterr().out.strip() == '1.4'
    assert main(['--docs', str(docs), 'check']) == 0
```

- [x] **Step 2: Run them to see them fail**. Expected: ImportError.

- [x] **Step 3: Implement `decisions.py`** porting the source's functions (lines 448-810) onto `log.py`: `resolve_link_arg` splits at the first `#`, checks the file exists under docs and the heading exists (decoded, verbatim), and for `N.k` / `§N` arguments resolves against the log's entries and sections; `_links` renders `[<text>](<link>)` where the text is the heading's leading id token when it has one (`2.1`), else the heading text, else the file stem; the Source link's text is the whole heading. `add_decision` appends to the open section (RefError without one), `apply_decision` replaces the Affected field and Status in place, `close_section` rewrites the section header and its contract line. `write_log` writes the whole file.

- [x] **Step 4: Run the tests**: all pass.

- [x] **Step 5: Commit**

```bash
git add tools/design/decisions.py tools/design/tests/test_decisions.py
git commit -m "tools: decisions.py, the decision log's commands" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `links.py`: the link checker

**Files:**
- Create: `tools/design/links.py`
- Test: `tools/design/tests/test_links.py`

**Reference:** B.6 (the kept parts), B.7, B.8, B.11, B.12 (check_test without git); spec section 5.

**Interfaces:**
- Consumes: `folder.*`, `log.parse_log`.
- Produces:

```python
@dataclass(order=True)
class Problem:
    warning: bool; file: str; line: int; kind: str; detail: str
    def __str__(self): return f"{'WARNING' if self.warning else 'PROBLEM'}: {self.file}:{self.line}: {self.kind}: {self.detail}"
def ruling_index(folder, corpus) -> dict[str, Target]          # 'N.k' -> Target(log, heading), from the log's level-3 headings
def log_entry_status(folder, corpus) -> dict[str, tuple[str, str]]   # heading text -> (id, status)
def mentions_in(folder, corpus, rel, rulings) -> list[tuple[int, str, Target, bool]]   # (offset, token, target, certain)
def check_folder(folder: Folder, corpus: Corpus, git=None, label='docs') -> list[Problem]
def main(argv=None) -> int      # [root]; prints problems; 'OK' or '<n> problems'
```

`git` is the `GitHistory` of Task 6; in this task pass `None` and leave the history branch as a call into `git` guarded by `if git is not None`.

- [x] **Step 1: Write the failing tests**: port B.12's no-git cases onto a fixture `folder_with(repo, extra: dict[str, str])` that writes the LOG of Task 3 (plus a `### 1.4 Three digits` entry with status applied and a `## 14. Big (2026-10-27)` section with `### 14.104 Big one` applied) and `design/02-x.md` with `## 2.1 Title`, `images/a.png` and `design/page.md` embedding `../images/a.png`, then runs `check_folder(Folder.dir(docs), Corpus.load(repo))` and compares `kinds = [f"{'W' if p.warning else 'P'} {p.kind} {p.file}:{p.line}" for p in problems]`. Required cases, each a test function: base clean · escape · dead-file and a folder · dead-heading · form seven ways · unlinked certain after "decision log" · parenthesis grouping certain, bare warning · plain stays plain (heading, code span, fence, comment, link text, URL, version `1.14.4`, own heading number) · wrong-target (`[2.2](design/02-x.md#2.1%20Title)` from `design/y.md`) · review link exempt · Answers lines skipped in the log, not elsewhere · stray and unembedded image · three-digit and `§` rulings · backtick heading `%60` clean, raw backtick is form · decoding cases · unapplied-target for recorded, note, section heading; file alone fine; same-file section link inside the log fine · a dead link in a generated file (corpus with `generated: ['product/**']`) is a warning · `main` prints `OK` / `1 problems` and exit codes.

- [x] **Step 2: Run them to see them fail**. Expected: ImportError.

- [x] **Step 3: Implement `links.py`** following B.8 in check order, with: `history` files from `corpus.is_history`, `generated` from `corpus.is_generated`, the `unapplied-target` check reading `log_entry_status`, the `wrong-target` rule of the spec (id token `\d+(?:\.\d+)*` in the text must equal the target heading's leading id token; otherwise the text must contain the heading text, or the file's first heading or stem), `stray` for every non-`.md` file not embedded, `mentions_in` for rulings only (B.6), the keyed regex also accepting `ruling 1.2` and `rulings 1.2 and 1.3`.

- [x] **Step 4: Run the tests**: all pass.

- [x] **Step 5: Commit**

```bash
git add tools/design/links.py tools/design/tests/test_links.py
git commit -m "tools: links.py, the link checker" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: `pins.py`: git history and pinning

**Files:**
- Create: `tools/design/pins.py`
- Modify: `tools/design/links.py` (the history branch, B.8 step 4)
- Test: `tools/design/tests/test_pins.py`

**Reference:** B.9, B.10, B.11, B.12 (pinned group and pin_test).

**Interfaces:**
- Produces:

```python
class GitHistory:
    @staticmethod
    def of(folder_root: Path) -> 'GitHistory | None'    # rev-parse --show-toplevel --show-prefix
    repo_root: Path; prefix: str
    def main(self) -> str | None                          # refs/remotes/origin/main, then refs/heads/main
    def on_main(self, sha) -> bool
    def commit_of(self, rel, line) -> str | None          # blame --porcelain; None for uncommitted
    def existed_at(self, commit, rel, heading=None) -> bool
    def latest_on_main_with(self, rel, heading=None) -> str | None
@dataclass
class PinReport: pinned: int; unpinnable: list[str]
def pin_links(folder, corpus, git, label='docs') -> PinReport
def main(argv=None) -> int
```

- [x] **Step 1: Write the failing tests**: a fixture building a real repo: commit `one` on `main` with `docs/design/01-a.md` (`## 1.1 Keep`, `## 1.2 Gone soon`) and the log linking both from an applied entry; commit `two` dropping `## 1.2 Gone soon`; branch `feature` from `two`. Tests: unpinned link on a line from main is `unpinned`, gone today or not, a review file too · pinned links resolve at their commit though gone today · `pin` for a branch commit, `dead-pin` for a missing heading and a missing file, `form` for a mis-encoded anchor, `pin` for `0123456789ab` · a branch line resolves now, same-file and external exempt · main is origin/main when present (`git update-ref refs/remotes/origin/main one`) · `on_main` with a 12-char prefix · `commit_of` follows a rename · `existed_at`, `latest_on_main_with` · `pin_links` pins main lines to their commit, else the newest with the target, lists the rest, a second run pins 0 · a branch line whose target is gone pins to the last main commit with it · `main` exit 2 without a main branch.

- [x] **Step 2: Run them to see them fail**. Expected: ImportError.

- [x] **Step 3: Implement `pins.py`** per B.9 and B.10, and wire the history branch into `links.check_folder` per B.8 step 4 (`unpinned`, `pin`, `dead-pin`, `form` for a pinned anchor, gone-today is fine). `links.main` passes `GitHistory.of(root)`.

- [x] **Step 4: Run the tests**: all pass (`test_links.py` too).

- [x] **Step 5: Commit**

```bash
git add tools/design/pins.py tools/design/links.py tools/design/tests/test_pins.py
git commit -m "tools: pins.py, git history and link pinning" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: `freshness.py`: the freshness chain with DVC

**Files:**
- Create: `tools/design/freshness.py`
- Test: `tools/design/tests/test_freshness.py`

**Reference:** section C entirely; spec section 9.

**Interfaces:**
- Consumes: `folder.glob_to_regex`, `folder.repo_root`, `links.check_folder`, `pins.GitHistory`, `folder.Corpus`.
- Produces:

```python
STAGES_PATH = 'tools/stages.yaml'
@dataclass
class StageDecl: name: str; skill: str; inputs: list[str]; outputs: list[str]; each: str | None; root: str | None; exclude: list[str]
@dataclass
class Declaration: dvc: str; stages: list[StageDecl]
def declaration_at(root: Path) -> Declaration            # raises FormatError(message) with C.1's texts
@dataclass
class DvcStage: name: str; decl: str; cmd: str; deps: list[str]; outs: list[str]
def git_files(root: Path) -> list[str]
def expand_all(decl: Declaration, files: list[str]) -> list[DvcStage]
def render_dvc_yaml(stages: list[DvcStage]) -> str
def stage_decl_of(name: str) -> str
def dvc_problem(wanted: str) -> str | None
def dvc_status(root: Path) -> dict[str, list[str]]
def check(root: Path, full=False, target=None, warnings_as_errors=False) -> tuple[str, bool]
def mark(root: Path, names: list[str]) -> int           # writes dvc.yaml, records through the DVC API; returns an exit code, prints the messages
def recorded_at(root: Path, stage: str) -> str | None
def check_main(argv=None) -> int; def mark_main(argv=None) -> int; def recorded_at_main(argv=None) -> int
```

- [x] **Step 1: Write the failing tests**: port C.7's generate_test (pure) and check_test (a repo with `dvc init -q --no-scm`? no: `dvc init -q` inside the git repo fixture, `.dvc/config` analytics off, a `tools/stages.yaml` with `screen` over `defs/*.md` to `out/{id}.md` and `docs` over `defs/*.md` to `out/page.md`) and the `--target` link cases (a `docs/` folder with a problem). Every C.7 line is one test. The zero-stage case is added: `stages: {}` renders `stages: {}`, `check` prints `OK`, `mark --generate-only` prints `0 stage(s)`.

- [x] **Step 2: Run them to see them fail**. Expected: ImportError.

- [x] **Step 3: Implement `freshness.py`** per C.1 to C.6; `mark` records in-process with the snippet of C.5. The header line is `# Generated by `just ensure-up-to-date` from tools/stages.yaml. Do not edit.`; the install hint is `uv sync --project tools`.

- [x] **Step 4: Run the tests**: all pass. Then at the repository root: `uv run --project tools design-mark-up-to-date --generate-only` writes `dvc.yaml`; `uv run --project tools design-ensure-up-to-date` prints `OK`.

- [x] **Step 5: Commit**

```bash
git add tools/design/freshness.py tools/design/tests/test_freshness.py dvc.yaml
git commit -m "tools: freshness.py, the generated-files chain on DVC" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: The pre-push hook

**Files:**
- Create: `.githooks/pre-push`
- Test: `tools/design/tests/test_hook.py`

**Reference:** the source hook (quoted in full in the plan's discussion; see `/home/openclaw/Projects/apuntalo.co/.githooks/pre-push`) and C.7 hook_test; spec section 10.

- [x] **Step 1: Write the failing tests** (a work repo cloned from a bare remote, `core.hooksPath` set to a copy of `.githooks`, `tools/` symlinked from this repository so the hook finds the package): a stale tip is refused with `run /ensure-up-to-date` · a tip without `tools/stages.yaml` is refused with the predates line · a current tip is accepted · an uncommitted edit changes nothing · an unpinned log link from main is refused with `unpinned links from main: run just pin-links, commit, push again`, accepted once pinned · a push from a linked worktree gets the right verdict and leaves the clone's origin config untouched.

- [x] **Step 2: Run them to see them fail**. Expected: the hook file does not exist.

- [x] **Step 3: Write the hook**: the source hook with `TOOL`/`LINKS` replaced by `cd "$ROOT" && uv run --project tools design-ensure-up-to-date --root "$tmp/tree"` and `uv run --project tools design-links-check "$tmp/tree/docs"`; same `unset`, same temporary-worktree loop, same traps, same messages. `chmod +x`.

- [x] **Step 4: Run the tests**: all pass.

- [x] **Step 5: Commit**

```bash
git add .githooks/pre-push tools/design/tests/test_hook.py
git commit -m "hooks: pre-push refuses a stale tip or unpinned links from main" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Move the design into `docs/design/` and write the folder's rules

**Files:**
- Move: `design/*` to `docs/design/*` (`git mv`)
- Create: `docs/LINKS.md`, `docs/index.md`, `docs/reviews/README.md`, `docs/reviews/iterations/.gitkeep`, `docs/reviews/raw-feedback/.gitkeep`
- Modify: `AGENTS.md`, `docs/design/README.md`, `docs/design/13-testing.md`, `docs/design/02-repos-and-config.md` (the one line naming `docs/design/` as the per-feature location, if present), `docs/reviews/2026-10-16-adversarial-design-review.md`

**Reference:** spec sections 3, 5, 11; the source's `docs/LINKS.md`, `docs/index.md`, `docs/reviews/README.md` for wording (rewrite them, do not copy product words).

- [x] **Step 1: Move**: `git mv design docs/design`. Then `grep -rn 'design/' docs AGENTS.md README.md` and rewrite every path that meant the root folder: `design/` becomes `docs/design/` in prose; relative links between the design documents are unchanged (same folder). In `docs/design/13-testing.md` §13.1 and `AGENTS.md`, the per-feature design location `docs/design/` becomes `docs/features/`.

- [x] **Step 2: Make every reference a link.** In `docs/design/*.md` and the review file, a mention of another document's section such as `02-repos-and-config.md §2.6` or `14 §14.2` or `(09-run-jobs.md)` becomes `[02 §2.6](02-repos-and-config.md#2.6%20Trust)` (from the review file: `../design/…`). Write a throwaway script under `/tmp/` that, for each `NN-name.md §x.y` and `NN §x.y` pattern, looks up the heading starting with `x.y ` in that file and rewrites the mention; run it, then handle the rest by hand until `just links-check` reports no `dead-*`, `form`, `escape` or `wrong-target` problem under `docs/design/` or the review file. Keep the `Where:` lines' wording; only wrap them. `README.md` at the repository root stays as is apart from paths.

- [x] **Step 3: Write `docs/LINKS.md`** with spec section 5 in full (form, a reference is a link, link text names its target, rulings are the one id shape, links into the log, pinning, generated files, links are invisible to programs), `docs/index.md` (the map: design is corpus, the log is rulings, reviews are history, `superpowers/` is this repository's own specs and plans and is never corpus), and `docs/reviews/README.md` (naming `YYYY-MM-DD-<slug>.md` with the slug rule, `iterations/`, `raw-feedback/` reserved for a future harvester, "nothing in a subfolder is ever reviewed directly", "agents never read this folder except the file under review and its iterations").

- [x] **Step 4: `AGENTS.md`** per spec section 11: the protected folders are `docs/design/` and `docs/e2e-tests/`; test code in `tests/e2e/`; per-feature designs in `docs/features/`; the new paragraph on rulings as the explicit approval and `/apply-decision` and the carry step as the only agent edits. Add one line: the generated-files rule (`just ensure-up-to-date`, `/ensure-up-to-date`, `just install-hooks` once per clone) and the decision-log rule (`docs/decision-log.md` is written only through `just decisions`; `/record-decision`, `/apply-decision`, `/how-we-got-here`; never by hand).

- [x] **Step 5: Verify**: `just links-check` lists only problems in `decision-log.md` (the old log, replaced in Task 11) and `stray` for `.gitkeep` files, which you avoid by not adding `.gitkeep` but creating the folders in Task 11 when the first file lands; so drop the two `.gitkeep` files and expect only the old log's problems.

- [x] **Step 6: Commit**

```bash
git add -A docs AGENTS.md README.md
git commit -m "docs: the design moves into docs/design; LINKS, index, reviews README, AGENTS rules" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: Append the eight log-only questions to the review file

**Files:**
- Modify: `docs/reviews/2026-10-16-adversarial-design-review.md`

**Reference:** spec section 12 step 1; the old `docs/decision-log.md` questions Q22, Q23, Q24, Q97, Q98, Q99, Q100, Q101.

- [x] **Step 1: Append**, before `## Dropped findings`, eight items in the file's own form (`## <id>. [<severity>] <title>`, blank, `**Where:**`, `**Problem:**`, `**Question:**`, the options, `**Recommendation:**`, `**Cost if wrong:**`), copying the text of the old log's questions: `E1` from Q22, `E2` from Q23, `E3` from Q24 (severity `high`), `R94` from Q97 (`blocker`), `R95` from Q98 (`blocker`), `R96` from Q99 (`high`), `R97` from Q100 (`high`), `R98` from Q101 (`blocker`). Drop the Status and Answer paragraphs; the answers go into the log in Task 11. R94's title is `How sub-designs are made`; R98's is `The other user-only gates: reset-rounds, configure, and unauthenticated MCP`. Make the `Where:` references links as in Task 9.

- [x] **Step 2: Verify**: `grep -c '^## [ER][0-9]*\. ' docs/reviews/2026-10-16-adversarial-design-review.md` prints 101; `just links-check` reports nothing new for the review file.

- [x] **Step 3: Commit**

```bash
git add docs/reviews/2026-10-16-adversarial-design-review.md
git commit -m "reviews: the eight questions that lived only in the log join the review file" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: Write the new log through the tool

**Files:**
- Replace: `docs/decision-log.md`

**Reference:** spec section 12 steps 3 to 5; the old log's Q1, Q2, Q97, Q98, Q99.

- [x] **Step 1: Save the old log** to `/tmp/old-decision-log.md` and write the new header into `docs/decision-log.md` (`# Decision Log`, blank, `*Append-only. Every ruling and its reasoning, dated.*`, blank).

- [x] **Step 2: Run the commands**, with `--today 2026-10-27` where the CLI accepts it (add a hidden `--today` option to `new-section`, `add-decision` and `apply-decision` in `decisions.py` if Task 4 did not; it is for migrations and tests):
  1. `just decisions new-section --title "Review: adversarial-design-review" --description "<the old log's header sentence about its sources, reworded without 'Q' numbers>" --review-file docs/reviews/2026-10-16-adversarial-design-review.md`
  2. `just decisions add-decision --title "MVP scope of multi-repo work" --context "<Q1 Problem + Question>" --decision "<Q1 Answer, then the amendment paragraph>" --affected "design/14-cross-repo-features.md" --affected "design/01-principles.md#1.1 What v2 is" --source "reviews/2026-10-16-adversarial-design-review.md#R1. [blocker] MVP scope of multi-repo work" --answers R1` (every section the Context names, such as `§1.1`, `13.2`, `4.3`, is written as a link argument-style mention inside the text: `[1.1](design/01-principles.md#1.1%20What%20v2%20is)`; the tool verifies them)
  3. `add-decision` for the trust half of Q2: title `Trust: index-only by default, trusted repos and mirrors, user-only trust commands`, Context from Q2's Problem and Question, Decision from `Answer (trust)` plus one sentence that the other gates are item R98, affected `design/02-repos-and-config.md#2.6 Trust`, `design/01-principles.md#1.2 Cross-cutting rules`, `design/04-mcp-and-cli.md#4.6 …`, `design/05-skill-rendering.md#5.2 Provider stubs`, source R2's heading, answers `R2`
  4. `add-decision` for Q97: title `How sub-designs are made`, affected from its `Recorded in` line, source R94's heading, answers `R94`
  5. `just decisions add-note --title "Parked" --text "R95 and R96 are parked with [14.2](design/14-cross-repo-features.md#14.2%20…) and are not MVP."`
  6. `apply-decision --id 1.1 --affected …`, `--id 1.2 --affected …`, `--id 1.3 --affected …` with the same affected sets, today `2026-10-27`.
  Copy the exact wording from `/tmp/old-decision-log.md`; do not paraphrase the owner's answers.

- [x] **Step 3: Verify**: `just decisions check` prints nothing and exits 0; `just decisions list` shows 1.1 to 1.4; `just decisions search --status recorded --oneline` is empty; `just decisions history "design/02-repos-and-config.md#2.6 Trust"` lists 1.2; `just links-check` prints `OK`; `just ensure-up-to-date` prints `OK`.

- [x] **Step 4: Commit**

```bash
git add docs/decision-log.md
git commit -m "decision log: converted to the tool's format; three applied rulings, one parked note" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: Skills: `decision-log`, `record-decision`, `apply-decision`, `how-we-got-here`

**Files:**
- Create: `.claude/skills/decision-log/SKILL.md`, `.claude/skills/decision-log/format.md`, `.claude/skills/record-decision/SKILL.md`, `.claude/skills/apply-decision/SKILL.md`, `.claude/skills/how-we-got-here/SKILL.md`

**Reference:** the source skills of the same names; spec section 8 (the table's Keeps and Loses columns are the edit list); section 6 for `format.md`.

- [x] **Step 1: Copy** each source `SKILL.md` (and `format.md`) and edit: every `python3 -I … decisions.py` and `just decisions` call keeps the `just decisions` form; `--affected-stories|screens|documents` become `--affected <link>`; `search --story|--screen|--document` become `search --affected <path-prefix>`; the "find what it affects" step reads `docs/design/README.md` and greps `^##` over the corpus files listed in `tools/corpus.yaml`; the vocabulary step is removed; the screen-definition and mock steps, the `references` fence and the "Next: /update-mocks, then /generate-docs" lines are removed; the `/apply-decision` commit command imports `design.log` for the link-free body (`uv run --project tools python -c 'from design.decisions import entry_body; …'`; add `entry_body(docs, id) -> str` to `decisions.py` if missing); the attribution line is the Global Constraints one. `format.md` is spec section 6 rewritten as the contract.

- [x] **Step 2: Grep** the four folders for every Global Constraints word; zero hits.

- [x] **Step 3: Dry run**: `just decisions show 1.1` from the skill's own command line works; read each skill top to bottom once and fix any step that names a file or command this repository does not have.

- [x] **Step 4: Commit**

```bash
git add .claude/skills/decision-log .claude/skills/record-decision .claude/skills/apply-decision .claude/skills/how-we-got-here
git commit -m "skills: decision-log, record-decision, apply-decision, how-we-got-here" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 13: Skills: `review-design`, `validate-design`, `design-review-conventions`

**Files:**
- Create: `.claude/skills/review-design/SKILL.md`, `.claude/skills/validate-design/SKILL.md`, `.claude/skills/design-review-conventions/{SKILL.md,review-files.md,decision-log-section.md,findings-format.md,agent-prompts.md,triage.md,worksheet.md}`

**Reference:** the source skills; spec section 8; the Explore report of the review conventions (in the conversation that produced this plan; its content is the source files themselves).

- [x] **Step 1: Copy and edit**: the worksheet prefix `/tmp/design-review-<ts>`; the agent prompts' shared block names "this repository's design folder", the do-not-read list from `tools/corpus.yaml` (`history`, `exclude`, and everything outside `docs/`), and "the corpus: every file matching the `corpus` globs of `tools/corpus.yaml`, listed with `git ls-files docs/design docs/e2e-tests`"; the slug warning keeps the rule and loses the word list; `validate-design` inventories the corpus from the same globs; the `--affected-*` flags become `--affected`; the `--source` and `--answers` conventions stay; the closing "Next:" lines are removed. **Add** to `review-design` step 5: before `new-section`, run `just decisions list --section` on the open section; if the log's open section's `Review file (open):` line names the argument file, continue in that section and skip `new-section`.

- [x] **Step 2: Grep** for the Global Constraints words; zero hits.

- [x] **Step 3: Gate dry run**: paste the `review_gate` function from `review-files.md` into a shell and run it on `docs/reviews/2026-10-16-adversarial-design-review.md`; expected `OK`. Run `review_undecided`; expected that file.

- [x] **Step 4: Commit**

```bash
git add .claude/skills/review-design .claude/skills/validate-design .claude/skills/design-review-conventions
git commit -m "skills: review-design, validate-design, design-review-conventions" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 14: Skills: `reconcile-links`, `ensure-up-to-date`

**Files:**
- Create: `.claude/skills/reconcile-links/SKILL.md`, `.claude/skills/ensure-up-to-date/SKILL.md`

- [x] **Step 1: Copy and edit**: `reconcile-links` keeps every fix kind of spec section 5 (its kinds list drops `unlinked` for anything but rulings) and the `changed.txt` contract at `.cache/reconcile-links/changed.txt`; `ensure-up-to-date` keeps the loop (`just ensure-up-to-date`, run the stale stage's skill, `just mark-up-to-date`, repeat) and says that with no stages declared the check prints `OK` and the skill stops; the stage list is "the stages of `tools/stages.yaml`, in file order".

- [x] **Step 2: Grep** for the Global Constraints words; zero hits.

- [x] **Step 3: Commit**

```bash
git add .claude/skills/reconcile-links .claude/skills/ensure-up-to-date
git commit -m "skills: reconcile-links, ensure-up-to-date" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 15: Final verification

- [x] **Step 1: `just build`** green: pytest, `decisions check`, `links-check` `OK`, `ensure-up-to-date` `OK`.

- [x] **Step 2: The word grep** over the whole repository except `.git` and `docs/superpowers/`:

```bash
grep -rniE 'apuntalo|creditosya|confluence|flutter|\bdart\b|\bfvm\b|obsidian|\bvault\b|\bmock|\bscreen|\bscene|\bstor(y|ies)\b|\blending\b|\bloan|\bpayout|\bintake\b' --exclude-dir=.git --exclude-dir=superpowers --exclude-dir=.venv . ; echo "exit $?"
```
Expected: no output but `exit 1`, except hits inside `docs/design/` that are the existing design's own words (none of these words occur there today; check with the same grep restricted to `docs/design`).

- [x] **Step 3: Hand checks** of spec section 13: `just decisions show 1.1 1.2 1.3`; `just decisions history "design/02-repos-and-config.md#2.6 Trust"` lists 1.2; `just decisions search --status recorded --oneline` is empty; `just install-hooks` then `git push --dry-run origin feature/design-folder` runs the hook and passes (unpinned lines are on this branch, so allowed).

- [x] **Step 4: Write `docs/superpowers/plans/2026-10-27-design-folder.md`'s checkboxes** as done and commit nothing else; report.

## Dependencies and parallelism

Task 1 first. Tasks 2 to 4 are sequential (folder, log, decisions). Tasks 5 and 6 are sequential after 2 and 3. Task 7 after 2, 5 and 6. Task 8 after 7. Tasks 9 to 11 after 4, 5, 6 and 7, sequential. Tasks 12 to 14 need only Task 4's CLI and can run in parallel with 9 to 11 in separate worktrees, at most three agents at once; merge with `git rebase`. Task 15 last.
