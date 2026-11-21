"""The open-work gatherer, `just omc todos [--json]`: the known open work read mechanically from the sources below,
the judgement left to `/find-related-todos` and `/summarize-todos`. Each item is
{'source', 'path', 'title', 'theme', 'start'}:

| source | read from | path | start |
|---|---|---|---|
| `tasks` | the briefs, `<paths.briefs>*.md` but README.md, one per file | the file | `just design <the file>` |
| `deferred` | the deferred entries of `origin/<base>`'s log (`paths.decision_log`) | `<the log>#<n>` | `just design --deferred <n>` |
| `question` | the `**Status.** open` blocks of the question files (`# Questions: …`) directly under `paths.questions` | `<file>#Q<k>` | as below |
| the project's | `omc/bin/todos`, when the project has one: its own sources | its own | its own, else as below |
| `todo` | the `TODO`/`FIXME` comments of the files git tracks that `paths.todos` matches (absent: `paths.product`) | `<file>:<line>` | as below |

"As below": `just design "<title> (<path>)"`, the text in double quotes with `\\`, `"`, `$` and the backquote escaped.
`theme` is the subtheme an item names where one can be read (`T9.3`; a rule `R14.5.1-6` gives `T14.5.1`), else None:
a brief's or an open question's first such id, a deferred entry's `Affected`. The items come in the table's order, the
`todo` ones by file then line.

`omc/bin/todos` (dormant by absence: no file, no item of its own) is the project's executable, run at the root with no
argument; it prints one JSON list of items, each with a `source`, a `path` and a `title` (strings) and optionally a
`theme` and a `start`; a missing `start` is "as below", a missing `theme` None. A run that exits non-zero, or prints
anything else, is refused. The standard library, and the log tool's parser (omc/tools/decisions/decisions.py)."""
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
sys.path.append(os.path.join(HERE, 'decisions'))  # decisions
import config  # noqa: E402
import repo  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

HOOK = os.path.join('omc', 'bin', 'todos')  # the project's own sources
HOOK_TIMEOUT = 300
QUESTION_FILE_FIRST = '# Questions: '

SUBTHEME = re.compile(r'(?<![\w.])T\d+(?:\.(?:\d+|x))*(?![\w])')
RULE = re.compile(r'(?<![\w.@])@?R(\d+(?:\.(?:\d+|x))*)-\d+')
HEADING = re.compile(r'^# (.+?)\s*$', re.M)
BLOCK = re.compile(r'^### (Q\d+) (.+?)\s*$')
COMMENT = re.compile(r'(?:#|//|/\*|<!--|^\s*\*|--)\s*((?:TODO|FIXME)\b.*?)\s*(?:\*/|-->)?\s*$')


def theme_of(text):
    """The first subtheme [text] names: a `T<n>…` id, or that of a rule's id; None."""
    found = []
    if (m := SUBTHEME.search(text or '')):
        found.append((m.start(), m.group(0)))
    if (m := RULE.search(text or '')):
        found.append((m.start(), f'T{m.group(1)}'))
    return min(found)[1] if found else None


def quoted(text):
    """[text] in double quotes for a POSIX shell."""
    return '"' + re.sub(r'([\\"$`])', r'\\\1', text) + '"'


def item(source, path, title, theme, start=None):
    return {'source': source, 'path': path, 'title': title, 'theme': theme,
            'start': start or f'just design {quoted(f"{title} ({path})")}'}


def _read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding='utf-8') as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def _rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, '/')


def tasks(root, paths):
    out = []
    for path in sorted(glob.glob(os.path.join(root, paths.briefs, '*.md'))):
        rel = _rel(root, path)
        if os.path.basename(path) == 'README.md':
            continue
        text = _read(root, rel) or ''
        m = HEADING.search(text)
        out.append(item('tasks', rel, m.group(1) if m else os.path.basename(path)[:-len('.md')], theme_of(text),
                        f'just design {rel}'))
    return out


def deferred(root, cfg):
    """The deferred entries of `origin/<base>`'s log; none when there is no such ref or log."""
    import decisions
    log_path = cfg.paths.decision_log
    r = repo.git(root, 'show', f'origin/{cfg.base}:{log_path}')
    if r.returncode != 0:
        return []
    log = decisions.parse_log(r.stdout)
    return [item('deferred', f'{log_path}#{e.n}', e.title, theme_of(e.fields.get('Affected')),
                 f'just design --deferred {e.n}')
            for e in log.entries.values() if e.status == decisions.Status.DEFERRED]


def _blocks(text):
    """(id, title, the block's lines) of every `### Q<k>` block of [text]."""
    out, current = [], None
    for line in text.split('\n'):
        m = BLOCK.match(line)
        if m:
            current = (m.group(1), m.group(2), [])
            out.append(current)
        elif line.startswith('#'):
            current = None
        elif current:
            current[2].append(line)
    return out


def questions(root, paths):
    out = []
    for path in sorted(glob.glob(os.path.join(root, paths.questions, '*.md'))):
        rel = _rel(root, path)
        text = _read(root, rel) or ''
        if not text.startswith(QUESTION_FILE_FIRST):
            continue
        for k, title, lines in _blocks(text):
            if any(line.strip() == '**Status.** open' for line in lines):
                out.append(item('question', f'{rel}#{k}', title, theme_of('\n'.join(lines))))
    return out


def project(root):
    """The items of the project's `omc/bin/todos`; none when it has none (module docstring)."""
    hook = os.path.join(root, HOOK)
    if not (os.path.isfile(hook) and os.access(hook, os.X_OK)):
        return []
    try:
        r = subprocess.run((hook,), cwd=root, capture_output=True, text=True, timeout=HOOK_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Refused(f'{HOOK} did not run: {e}') from None
    if r.returncode != 0:
        raise Refused(f'{HOOK} exited {r.returncode}: {(r.stderr or r.stdout).strip()[-400:]}')
    try:
        found = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise Refused(f'{HOOK} printed no JSON list: {e}') from None
    if not isinstance(found, list):
        raise Refused(f'{HOOK} printed no JSON list')
    out = []
    for i in found:
        if not (isinstance(i, dict) and all(isinstance(i.get(k), str) and i.get(k) for k in ('source', 'path', 'title'))
                and isinstance(i.get('theme'), (str, type(None))) and isinstance(i.get('start'), (str, type(None)))):
            raise Refused(f'{HOOK}: an item without a source, a path and a title (strings): {json.dumps(i)[:200]}')
        out.append(item(i['source'], i['path'], i['title'], i.get('theme'), i.get('start')))
    return out


def todo(root, paths):
    """One per TODO or FIXME comment of the files git tracks that `paths.todos` (absent: `paths.product`) matches, by
    file then line."""
    globs = paths.todos if paths.todos is not None else paths.product
    if not globs:
        return []
    r = repo.git(root, 'grep', '-n', '-I', '-w', '-E', 'TODO|FIXME')
    out = []
    for line in r.stdout.splitlines() if r.returncode == 0 else []:
        path, _, rest = line.partition(':')
        number, _, code = rest.partition(':')
        m = COMMENT.search(code)
        if m and number.isdigit() and config.matches(path, globs):
            out.append((path, int(number), m.group(1)))
    return [item('todo', f'{path}:{n}', text, None) for path, n, text in sorted(out)]


def gather(root):
    """Every item of open work, in the table's order (module docstring)."""
    cfg = config.load(root)
    return [*tasks(root, cfg.paths), *deferred(root, cfg), *questions(root, cfg.paths), *project(root),
            *todo(root, cfg.paths)]
