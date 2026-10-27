"""The docs folder and its Markdown: masking, headings, anchors, inline links, and the corpus configuration.

Every later module builds on this one. Paths inside the folder are posix and relative to its root."""
from __future__ import annotations

import functools
import os
import posixpath
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

HEADING_RE = re.compile(r'^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$')
FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
PIN_RE = re.compile(r'^git:([0-9a-f]{7,40})$')
COMMENT_RE = re.compile(r'<!--[\s\S]*?-->')
PCT_RUN_RE = re.compile(r'(?:%[0-9A-Fa-f]{2})+')
SLUG_DROP_RE = re.compile(r'[^\w\s-]', re.UNICODE)


@dataclass(frozen=True)
class Heading:
    line: int  # 1-based
    level: int
    text: str  # raw, as written


@dataclass
class Link:
    """One inline link or image; offsets index the text it was scanned from."""
    start: int  # the whole link, with the `!` of an image
    end: int
    text_start: int  # the link text between the brackets
    text_end: int
    dest: str  # as written, without angle brackets
    image: bool = False
    angle: bool = False
    title: str | None = None  # without its quotes

    @property
    def pin(self) -> str | None:
        """The commit of a `git:<sha>` title, or None."""
        m = PIN_RE.match(self.title) if self.title is not None else None
        return m.group(1) if m else None

    @property
    def path_and_fragment(self) -> tuple[str, str | None]:
        """The destination split at its first `#`; the fragment is None when there is no `#`."""
        path, hash_, frag = self.dest.partition('#')
        return path, frag if hash_ else None


def _blank(s: str) -> str:
    """Every character of s but newlines as a space, so offsets and line numbers stay."""
    return re.sub(r'[^\n]', ' ', s)


def closes_fence(line: str, run: str, fence: str) -> bool:
    return run[0] == fence[0] and len(run) >= len(fence) and line.strip() == run


def mask(text: str) -> str:
    """text with fenced code, HTML comments and inline code spans blanked; length and newlines kept."""
    lines = text.split('\n')
    fence = None
    for i, line in enumerate(lines):
        m = FENCE_RE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                lines[i] = _blank(line)
        else:
            if m and closes_fence(line, m.group(1), fence):
                fence = None
            lines[i] = _blank(line)
    s = '\n'.join(lines)
    s = COMMENT_RE.sub(lambda m: _blank(m.group(0)), s)
    return _mask_code_spans(s)


def _mask_code_spans(s: str) -> str:
    """s with inline code spans blanked, left to right; a link destination after `](` is passed over whole, so a
    backtick inside it never opens a span."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '`':
            k = i
            while k < len(s) and s[k] == '`':
                k += 1
            close = re.compile('(?<!`)' + '`' * (k - i) + '(?!`)').search(s, k)
            if close is None:
                out.append(s[i:k])  # no closing run: the backticks are literal
                i = k
            else:
                out.append(_blank(s[i:close.end()]))
                i = close.end()
        elif c == ']' and i + 1 < len(s) and s[i + 1] == '(':
            d = _destination_at(s, i + 2)
            end = i + 1 if d is None else d[1]
            out.append(s[i:end])
            i = end
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def decode_percent(s: str) -> str:
    """s with each `%XX` sequence that encodes a UTF-8 character decoded; raw characters, and bytes that are not
    part of a valid character, stay as written."""
    def run(m):
        written = m.group(0)
        data = bytes(int(written[i + 1:i + 3], 16) for i in range(0, len(written), 3))
        out, i = [], 0
        while i < len(data):
            lead = data[i]
            n = 1 if lead < 0x80 else 2 if 0xC2 <= lead < 0xE0 else 3 if 0xE0 <= lead < 0xF0 else 4 if 0xF0 <= lead < 0xF5 else 0
            if n and i + n <= len(data):
                try:
                    out.append(data[i:i + n].decode('utf-8'))
                    i += n
                    continue
                except UnicodeDecodeError:
                    pass  # not a valid character: keep its first byte as written
            out.append(written[3 * i:3 * i + 3])
            i += 1
        return ''.join(out)
    return PCT_RUN_RE.sub(run, s)


def headings_of(text: str) -> list[Heading]:
    """The ATX headings outside fenced code, in order."""
    out, fence = [], None
    for i, line in enumerate(text.split('\n')):
        f = FENCE_RE.match(line)
        if fence is not None:
            if f and closes_fence(line, f.group(1), fence):
                fence = None
            continue
        if f:
            fence = f.group(1)
            continue
        m = HEADING_RE.match(line)
        if m and m.group(2):
            out.append(Heading(i + 1, len(m.group(1)), m.group(2)))
    return out


def encode_anchor(heading: str) -> str:
    """The anchor of a heading: every space %20, every backtick %60, everything else raw."""
    return heading.replace(' ', '%20').replace('`', '%60')


def github_slug(heading: str) -> str:
    """The anchor GitHub gives a heading: lowercase, punctuation dropped, each space a dash (not collapsed)."""
    return SLUG_DROP_RE.sub('', heading.lower()).strip().replace(' ', '-')


def _title(between: str) -> str | None:
    """The title between a destination and its closing parenthesis, without its quotes; None when there is none."""
    t = between.strip()
    if len(t) >= 2 and ((t[0] == '"' and t[-1] == '"') or (t[0] == "'" and t[-1] == "'")):
        return t[1:-1]
    return t or None


def _destination_at(s: str, k: int) -> tuple[str, int, bool, str | None] | None:
    """The inline link destination starting at k (just after `](`): (dest, end past `)`, angle, title), or None."""
    if k < len(s) and s[k] == '<':
        gt = s.find('>', k)
        if gt < 0 or '\n' in s[k:gt]:
            return None
        end = s.find(')', gt)
        if end < 0:
            return None
        return s[k + 1:gt], end + 1, True, _title(s[gt + 1:end])
    depth, m = 0, k
    while m < len(s):
        c = s[m]
        if c in '\n \t':
            break
        if c == '(':
            depth += 1
        elif c == ')':
            if depth == 0:
                break
            depth -= 1
        m += 1
    if m >= len(s) or s[m] == '\n':
        return None
    dest = s[k:m]
    if s[m] == ')':
        return dest, m + 1, False, None
    end = s.find(')', m)  # a title after the destination
    if end < 0 or '\n' in s[m:end]:
        return None
    return dest, end + 1, False, _title(s[m:end])


def scan_links(masked: str) -> list[Link]:
    """The inline links and images of masked (code and comments already blanked by mask), in order."""
    s, out, i = masked, [], 0
    while True:
        open_ = s.find('[', i)
        if open_ < 0:
            return out
        i = open_ + 1
        if open_ > 0 and s[open_ - 1] == '\\':
            continue
        if open_ + 1 < len(s) and s[open_ + 1] == '[':
            i = open_ + 2  # a wikilink, not an inline link
            continue
        depth, close = 0, -1
        for j in range(open_, len(s)):
            c = s[j]
            if c == '\n':
                break
            if c == '[':
                depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0:
                    close = j
                    break
        if close < 0 or close + 1 >= len(s) or s[close + 1] != '(':
            continue
        d = _destination_at(s, close + 2)
        if d is None:
            continue
        dest, end, angle, title = d
        image = open_ > 0 and s[open_ - 1] == '!'
        out.append(Link(open_ - 1 if image else open_, end, open_ + 1, close, dest, image, angle, title))
        i = end


def unlink(text: str) -> str:
    """text with every inline link (not image) replaced by the raw text between its brackets; links in code stay."""
    out, at = [], 0
    for link in scan_links(mask(text)):
        if link.image:
            continue
        out.append(text[at:link.start])
        out.append(text[link.text_start:link.text_end])
        at = link.end
    out.append(text[at:])
    return ''.join(out)


@dataclass(frozen=True)
class Target:
    file: str  # posix, relative to the folder
    heading: str | None  # the heading's text as written; None for the file itself


def link_to(from_rel: str, target: Target) -> str:
    """The relative destination from from_rel to target, its anchor encoded."""
    if target.file == from_rel and target.heading is not None:
        return '#' + encode_anchor(target.heading)
    rel = posixpath.relpath(target.file, posixpath.dirname(from_rel) or '.')
    return rel if target.heading is None else f'{rel}#{encode_anchor(target.heading)}'


def resolve(from_rel: str, dest: str) -> tuple[str, str | None]:
    """The normalized target of a destination written in from_rel, and its fragment as written (None without `#`)."""
    path, hash_, frag = dest.partition('#')
    target = from_rel if path == '' else posixpath.normpath(posixpath.join(posixpath.dirname(from_rel), decode_percent(path)))
    return target, frag if hash_ else None


def escapes(target_rel: str) -> bool:
    """Whether a resolved target leaves the folder."""
    return target_rel == '..' or target_rel.startswith('../')


@functools.lru_cache(maxsize=None)
def glob_to_regex(pattern: str) -> re.Pattern:
    """An anchored regex for a glob: `**` across folders, `*` and `?` within one, `[..]` classes, `{a,b}`."""
    out, i, n, braces = [], 0, len(pattern), 0
    while i < n:
        c = pattern[i]
        if c == '*':
            if pattern.startswith('**', i):
                if pattern.startswith('**/', i):
                    out.append('(?:.*/)?')  # zero or more folders
                    i += 3
                else:
                    out.append('.*')
                    i += 2
                continue
            out.append('[^/]*')
        elif c == '?':
            out.append('[^/]')
        elif c == '[':
            j = pattern.find(']', i + 2 if pattern[i + 1:i + 2] in ('!', '^') else i + 1)
            if j < 0:
                out.append(re.escape(c))
            else:
                body = pattern[i + 1:j]
                if body[:1] in ('!', '^'):
                    body = '^' + body[1:]
                out.append('[' + body.replace('\\', '\\\\') + ']')
                i = j
        elif c == '{':
            braces += 1
            out.append('(?:')
        elif c == ',' and braces:
            out.append('|')
        elif c == '}' and braces:
            braces -= 1
            out.append(')')
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile(''.join(out) + r'\Z')


@dataclass
class Corpus:
    """tools/corpus.yaml: the folder, its log, and which of its files are corpus, history, generated or excluded."""
    root: str
    log: str
    corpus: list[str]
    history: list[str]
    generated: list[str]
    exclude: list[str]

    @staticmethod
    def load(repo_root: Path) -> Corpus:
        data = yaml.safe_load((Path(repo_root) / 'tools' / 'corpus.yaml').read_text(encoding='utf-8')) or {}
        c = Corpus(root=data['root'], log=data['log'], corpus=list(data.get('corpus') or []),
                   history=list(data.get('history') or []), generated=list(data.get('generated') or []),
                   exclude=list(data.get('exclude') or []))
        for p in c.corpus + c.history + c.generated + c.exclude:
            try:
                glob_to_regex(p)  # compile once; a bad glob fails here
            except re.error as e:
                raise ValueError(f'tools/corpus.yaml: bad glob {p!r}: {e}') from None
        return c

    def matches(self, patterns, rel) -> bool:
        return any(glob_to_regex(p).match(rel) for p in patterns)

    def is_history(self, rel) -> bool:
        return self.matches(self.history, rel)

    def is_generated(self, rel) -> bool:
        return self.matches(self.generated, rel)

    def is_excluded(self, rel) -> bool:
        return self.matches(self.exclude, rel)

    def is_corpus(self, rel) -> bool:
        return self.matches(self.corpus, rel)


class Folder:
    """The files of the docs folder, each read once."""

    def __init__(self, root: Path, files: list[str]):
        self.root = root
        self.files = files  # posix, relative to root, sorted
        self._texts: dict[str, str] = {}
        self._headings: dict[str, list[Heading]] = {}
        self._slugs: dict[str, dict[str, str]] = {}

    @staticmethod
    def git(root) -> Folder:
        """The files git tracks or would track under root that exist on disk."""
        root = Path(os.path.abspath(root))
        r = subprocess.run(['git', '-C', str(root), 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '.'],
                           capture_output=True, text=True, encoding='utf-8')
        if r.returncode != 0:
            raise RuntimeError(f'git ls-files in {root}: {r.stderr.strip()}')
        files = sorted(f for f in r.stdout.split('\0') if f and (root / f).exists())
        return Folder(root, files)

    @staticmethod
    def dir(root) -> Folder:
        """Every file under root (for tests)."""
        root = Path(os.path.abspath(root))
        files = sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file())
        return Folder(root, files)

    @property
    def markdown(self) -> list[str]:
        return [f for f in self.files if f.endswith('.md')]

    def text(self, rel) -> str:
        if rel not in self._texts:
            self._texts[rel] = (self.root / rel).read_text(encoding='utf-8').replace('\r\n', '\n')
        return self._texts[rel]

    def headings(self, rel) -> list[Heading]:
        if rel not in self._headings:
            self._headings[rel] = headings_of(self.text(rel))
        return self._headings[rel]

    def slugs(self, rel) -> dict[str, str]:
        """GitHub slugs of rel's headings (duplicates numbered -1, -2, first wins) to the heading's text."""
        if rel not in self._slugs:
            seen: dict[str, int] = {}
            out: dict[str, str] = {}
            for h in self.headings(rel):
                base = github_slug(h.text)
                n = seen.get(base, 0)
                seen[base] = n + 1
                out.setdefault(base if n == 0 else f'{base}-{n}', h.text)
            self._slugs[rel] = out
        return self._slugs[rel]

    def is_file(self, rel) -> bool:
        return (self.root / rel).is_file()

    def is_dir(self, rel) -> bool:
        return (self.root / rel).is_dir()

    def has_heading(self, rel, heading) -> bool:
        return self.is_file(rel) and any(h.text == heading for h in self.headings(rel))


def repo_root(start: Path | None = None) -> Path:
    """The first directory from start (default: the working directory) up that holds `.git`, a folder or a file."""
    here = Path(os.path.abspath(start if start is not None else Path.cwd()))
    for d in (here, *here.parents):
        if (d / '.git').exists():
            return d
    raise RuntimeError(f'no .git above {here}')
