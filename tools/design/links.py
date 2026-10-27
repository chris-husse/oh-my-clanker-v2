"""The link checker: every link of the docs folder in the written form, resolving, naming its target; every bare
ruling of the log linked; nothing but Markdown and embedded images in the folder.

The rules are docs/LINKS.md's. The one id shape known here is the log's own: `N.k` a ruling, `§N` a section."""
from __future__ import annotations

import bisect
import posixpath
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from design.folder import (Corpus, Folder, Target, decode_percent, encode_anchor, escapes, link_to, mask, repo_root,
                           resolve, scan_links)
from design.log import parse_log
from design.pins import GitHistory

SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')
EXTERNAL_RE = re.compile(r'^(https?|mailto):', re.IGNORECASE)
WIKI_RE = re.compile(r'\[\[[^\]\n]+\]\]')
REF_USE_RE = re.compile(r'\[[^\[\]\n]+\]\[[^\[\]\n]*\]')
REF_DEF_RE = re.compile(r'^ {0,3}\[[^\]\n]+\]:[ \t]*\S', re.MULTILINE)
REF_DEF_LINE_RE = re.compile(r'^ {0,3}\[[^\]\n]+\]:.*$', re.MULTILINE)
URL_RE = re.compile(r'\bhttps?://\S+', re.ASCII)

# a heading's leading id token: a number (`2.6 Trust`), or one or two capitals and digits before a period (`H. …`, `L4. …`)
ID_TOKEN_RE = re.compile(r'\d+(?:\.\d+)*|[A-Z]{1,2}\d*(?=\.(?:\s|$))', re.ASCII)
# an id token of link text, bounded; a sentence-ending period may follow (`decision 1.2.`), `v2.1` holds none
TEXT_ID_RE = re.compile(r'(?<![\w.])\d+(?:\.\d+)*(?!\w|\.\w)', re.ASCII)
# a letter-led id token of link text: `§H`, `H`, `L4`
TEXT_LETTER_ID_RE = re.compile(r'(?<![\w.])(§?)([A-Z]{1,2}\d*)(?!\w|\.\w)', re.ASCII)
RULING_HEADING_RE = re.compile(r'^(\d+\.\d+)[ .]', re.ASCII)
NUM_RE = re.compile(r'(?<![\w.])\d{1,3}\.\d{1,3}(?![\w]|\.\d)', re.ASCII)  # a bare ruling id
KEYED_RE = re.compile(r'(?:[Dd]ecision[ -]log|[Rr]ulings?)((?:(?:\s*,\s*|\s+and\s+|\s+)§?\d{1,3}\.\d{1,3}(?![\w]|\.\d))+)',
                      re.ASCII)
PAREN_RE = re.compile(r'\(([^()\n]*)\)')
PAREN_SPLIT_RE = re.compile(r',|;|\band\b', re.ASCII)


@dataclass(order=True)
class Problem:
    warning: bool
    file: str
    line: int
    kind: str
    detail: str

    def __str__(self):
        return f"{'WARNING' if self.warning else 'PROBLEM'}: {self.file}:{self.line}: {self.kind}: {self.detail}"


def _blank(s: str) -> str:
    return re.sub(r'[^\n]', ' ', s)


def _leading_id(text: str) -> str | None:
    m = ID_TOKEN_RE.match(text)
    return m.group(0) if m else None


def ruling_index(folder: Folder, corpus: Corpus) -> dict[str, Target]:
    """'N.k' to its entry heading in the log, from the log's level-3 headings. An id written twice raises."""
    log = corpus.log
    out: dict[str, Target] = {}
    if not folder.is_file(log):
        return out
    for h in folder.headings(log):
        m = RULING_HEADING_RE.match(h.text) if h.level == 3 else None
        if m:
            if m.group(1) in out:
                raise ValueError(f'ruling {m.group(1)} is defined twice in {log}')
            out[m.group(1)] = Target(log, h.text)
    return out


def log_entry_status(folder: Folder, corpus: Corpus) -> dict[str, tuple[str, str]]:
    """An entry's heading text, as written in the log, to (id, status)."""
    log = corpus.log
    if not folder.is_file(log):
        return {}
    by_line = {h.line: h.text for h in folder.headings(log)}
    return {by_line[e.line]: (e.id, e.status()) for e in parse_log(folder.text(log), log).entries.values()
            if e.line in by_line}


def _prose(folder: Folder, corpus: Corpus, rel: str) -> str:
    """rel's text with code, comments, headings, links, wikilinks, reference-style links and URLs blanked, and in the
    log every `Answers:` line, which names review items."""
    lines = mask(folder.text(rel)).split('\n')
    for h in folder.headings(rel):
        lines[h.line - 1] = _blank(lines[h.line - 1])
    if rel == corpus.log:
        lines = [_blank(l) if l.startswith('Answers: ') else l for l in lines]
    s = '\n'.join(lines)
    out, at = [], 0
    for l in scan_links(s):
        out += [s[at:l.start], _blank(s[l.start:l.end])]
        at = l.end
    s = ''.join(out) + s[at:]
    for r in (WIKI_RE, REF_USE_RE, REF_DEF_LINE_RE, URL_RE):
        s = r.sub(lambda m: _blank(m.group(0)), s)
    return s


def mentions_in(folder: Folder, corpus: Corpus, rel: str, rulings: dict[str, Target]) -> list[tuple[int, str, Target, bool]]:
    """Every ruling of the log written in rel as plain text: (offset, token, target, certain). Certain after
    "decision log", "ruling" or "rulings", or in a parenthesis of references only; a bare one is uncertain. Outside
    the log a number that is one of rel's own heading numbers is no mention."""
    s = _prose(folder, corpus, rel)
    keyed = set()
    for m in KEYED_RE.finditer(s):
        g = m.start(1)
        keyed.update(g + n.start() for n in NUM_RE.finditer(m.group(1)))
    grouped = set()
    for m in PAREN_RE.finditer(s):
        inner = m.group(1)
        tokens = [t.strip() for t in PAREN_SPLIT_RE.split(inner) if t.strip()]
        if tokens and all(t.removeprefix('§') in rulings for t in tokens):
            grouped.update(m.start(1) + n.start() for n in NUM_RE.finditer(inner))
    own = {_leading_id(h.text) for h in folder.headings(rel)}
    out = []
    for m in NUM_RE.finditer(s):
        t = rulings.get(m.group(0))
        if t is None:
            continue
        if m.start() in keyed:
            out.append((m.start(), m.group(0), t, True))
        elif rel != corpus.log and m.group(0) in own:
            continue
        else:
            out.append((m.start(), m.group(0), t, m.start() in grouped))
    return out


def _names_target(folder: Folder, text: str, target: str, heading: str | None) -> str | None:
    """None when the link text names its target (the spec's wrong-target rule); otherwise why not."""
    if heading is not None:
        names = [heading]
    else:
        first = folder.headings(target)[0].text if target.endswith('.md') and folder.headings(target) else None
        names = [n for n in (first, posixpath.splitext(posixpath.basename(target))[0]) if n is not None]
    leading = [i for i in (_leading_id(n) for n in names) if i is not None]
    ids = TEXT_ID_RE.findall(text)
    # a capital word counts as a token when the target's id is letter-led, or when it follows a `§`
    lettered = any(not i[0].isdigit() for i in leading)
    ids += [m.group(2) for m in TEXT_LETTER_ID_RE.finditer(text) if lettered or m.group(1)]
    if ids and leading:  # an id token is compared only with the target's own id; otherwise the text names it
        if any(i in leading for i in ids):
            return None
        return f'its id is {" or ".join(leading)}'
    if any(n.replace('`', '').casefold() in text.casefold() for n in names):
        return None
    return 'the text names neither ' + ' nor '.join(f'"{n}"' for n in names) if len(names) > 1 else f'the text does not name "{names[0]}"'


def check_folder(folder: Folder, corpus: Corpus, git=None, label: str = 'docs') -> list[Problem]:
    """Every link problem of the folder, problems first, then warnings, each sorted by file and line. With git (the
    GitHistory of the folder), a link of a history file is checked as pinned. Files corpus.yaml excludes are not
    checked at all."""
    problems: list[Problem] = []
    embedded: set[str] = set()
    log = corpus.log
    rulings = ruling_index(folder, corpus)
    entries = log_entry_status(folder, corpus)

    for f in folder.markdown:
        if corpus.is_excluded(f):
            continue
        raw = folder.text(f)
        masked = mask(raw)
        starts = [0] + [i + 1 for i, c in enumerate(raw) if c == '\n']
        generated = corpus.is_generated(f)
        history = f == log or corpus.is_history(f)

        def line_of(off):
            return bisect.bisect_right(starts, off)

        def add(off, kind, detail, warning=False):
            problems.append(Problem(warning or generated, f'{label}/{f}', line_of(off), kind,
                                    detail + ' (generated)' if generated else detail))

        def check_today(l, target, heading, frag):
            if target == log and f != log and frag:
                e = entries.get(heading)
                if e is None:
                    add(l.start, 'unapplied-target', f'links a heading of the log that is not a decision entry: #{frag}')
                elif e[1] != 'applied':
                    add(l.start, 'unapplied-target', f'{e[0]} is {e[1]}; only an applied entry may be linked')
            if not l.image and not corpus.is_history(target):  # a link into a review names its item: exempt
                token = raw[l.text_start:l.text_end].replace('`', '').strip()
                why = _names_target(folder, token, target, heading)
                if why is not None:
                    add(l.start, 'wrong-target', f'"{token}" links to {link_to(f, Target(target, heading))}; {why}')

        for m in WIKI_RE.finditer(masked):
            add(m.start(), 'form', f'wikilink {m.group(0)}; write a relative Markdown link')
        for m in REF_USE_RE.finditer(masked):
            add(m.start(), 'form', f'reference-style link {m.group(0)}; write an inline link')
        for m in REF_DEF_RE.finditer(masked):
            add(m.start(), 'form', 'reference definition; write inline links')

        for l in scan_links(masked):
            dest = l.dest
            if l.angle:
                add(l.start, 'form', f'angle-bracket destination <{dest}>; write each space as %20')
                continue
            if SCHEME_RE.match(dest):
                if not EXTERNAL_RE.match(dest):
                    add(l.start, 'form', f'scheme not allowed: {dest}')
                continue
            if dest.startswith('/'):
                add(l.start, 'form', f'absolute path: {dest}')
                continue
            path = dest.partition('#')[0]
            target, frag = resolve(f, dest)
            if escapes(target):
                add(l.start, 'escape', f'link leaves {label}/: {dest}')
                continue
            if git is not None and history and path:
                if _check_pinned(git, folder, f, l, target, frag, line_of(l.start), add, embedded, check_today):
                    continue
            if not folder.is_file(target):
                add(l.start, 'dead-file', f'a folder, not a file: {dest}' if folder.is_dir(target) else f'no such file: {dest}')
                continue
            if l.image:
                embedded.add(target)
            heading = None
            if frag and target.endswith('.md'):
                as_text = decode_percent(frag)
                if any(h.text == as_text for h in folder.headings(target)):
                    heading = as_text
                    if frag != encode_anchor(as_text):
                        add(l.start, 'form', f'anchor not in the written form: #{frag}; write #{encode_anchor(as_text)}')
                else:
                    slug = folder.slugs(target).get(frag)
                    if slug is not None:
                        add(l.start, 'form', f'GitHub slug #{frag}; write #{encode_anchor(slug)}')
                    else:
                        add(l.start, 'dead-heading', f'no heading "{as_text}" in {target}')
                    continue
            check_today(l, target, heading, frag)

        for off, token, target, certain in mentions_in(folder, corpus, f, rulings):
            add(off, 'unlinked' if certain else 'unlinked?', f'{token}: link it to {link_to(f, target)}', warning=not certain)

    for f in folder.files:
        if f.endswith('.md') or f in embedded or corpus.is_excluded(f):
            continue
        problems.append(Problem(False, f'{label}/{f}', 0, 'stray',
                                'an image no page embeds' if f.endswith('.png') else f'not Markdown; it does not belong in {label}/'))
    return sorted(problems)


def _check_pinned(git: GitHistory, folder: Folder, f, l, target, frag, line, add, embedded, check_today) -> bool:
    """A link of a history file, against git. True when it is settled here: an unpinned link on a line from main is
    `unpinned`; a pinned one is checked at its commit (`pin`, `dead-pin`, `form`), and against today's folder only
    when its target still exists. False for an unpinned link on a line of this branch: it must resolve now."""
    dest = l.dest
    pin = l.pin
    if pin is None:
        commit = git.commit_of(f, line)
        if commit is not None and git.on_main(commit):
            add(l.start, 'unpinned', f'{dest}: run just pin-links')
            return True
        return False
    heading = decode_percent(frag) if frag and target.endswith('.md') else None
    if not git.on_main(pin):
        add(l.start, 'pin', f'git:{pin} is not a commit on main: {dest}')
    elif not git.existed_at(pin, target):
        add(l.start, 'dead-pin', f'no such file at git:{pin}: {dest}')
    elif heading is not None and not git.existed_at(pin, target, heading):
        add(l.start, 'dead-pin', f'no heading "{heading}" in {target} at git:{pin}')
    elif heading is not None and frag != encode_anchor(heading):
        add(l.start, 'form', f'anchor not in the written form: #{frag}; write #{encode_anchor(heading)}')
    if not folder.is_file(target) or (heading is not None and not folder.has_heading(target, heading)):
        return True  # gone today: nothing else to check against the working tree
    if l.image:
        embedded.add(target)
    check_today(l, target, heading, frag)
    return True


def main(argv=None) -> int:
    """links-check [root]: every problem and warning of the docs folder (default: the corpus root of the repository),
    then `OK`, or `<n> problems` and exit 1. Warnings do not fail."""
    args = sys.argv[1:] if argv is None else list(argv)
    if args and args[0] in ('-h', '--help'):
        print('usage: links-check [root]\n\nEvery link problem of the docs folder at root (default: the root of '
              'tools/corpus.yaml), then OK, or <n> problems and exit 1; exit 2 when the check cannot run.')
        return 0
    if args and not Path(args[0]).is_dir():
        print(f'links-check: {args[0]} is not a directory', file=sys.stderr)
        return 2
    try:
        repo = repo_root(Path(args[0]) if args else None)
        corpus = Corpus.load(repo)
        root = Path(args[0]) if args else repo / corpus.root
        try:
            folder = Folder.git(root)
        except RuntimeError:
            folder = Folder.dir(root)
        problems = check_folder(folder, corpus, GitHistory.of(root), corpus.root.rstrip('/'))
    except (RuntimeError, ValueError, OSError) as e:
        print(f'links-check: {e}', file=sys.stderr)
        return 2
    for p in problems:
        print(p)
    failing = sum(1 for p in problems if not p.warning)
    print(f'{failing} problems' if failing else 'OK')
    return 1 if failing else 0
