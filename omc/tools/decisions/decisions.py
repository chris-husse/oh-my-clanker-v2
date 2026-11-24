#!/usr/bin/env python3
"""The decision log's tool: the log at `paths.decision_log` of omc/config.yaml, the one log, and its only writer. The
guarded pages (every file `paths.protected` matches) change only through an entry of the log applied on the branch;
`guard` proves it against the merge-base with origin/<base> (`base` of omc/config.yaml; "main" below is that base),
comparing the pages' normalized text (what the link tools write without a decision is stripped). The vault is the top
folder of the log's path: the tool works with paths relative to it (`configure`). The log is opt-in: with no
`paths.decision_log` configured, every verb that only reads or maintains the log prints nothing and exits 0 and every
verb that writes an entry refuses (NO_LOG). With a log configured but no file yet and no protected page it is idle:
every read verb prints nothing and exits 0. The entry form, the names `Affected` takes and the rules of `check` and `trim` are
omc/tools/decisions/FORMAT.md; every link the tool writes follows docs/LINKS.md, relative to the log. git is read
only in `git_inputs`, `origin_main_log` (undefer's), renumber's reads (`operation_in_progress`, `branch_files`, `base_refs`) and `committed_heads`
(update's and remove's); every other function takes texts.
Run from the repository root: `just decisions <subcommand> ...` (`just decisions --help`)."""
import argparse
import datetime
import os
import posixpath
import re
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # omc/tools; python -I leaves it off
import config  # noqa: E402

# What omc/config.yaml's paths make of the tool, set by `configure` (on import, the default paths): the vault
# (repo-relative, '' or ending with `/`), the log relative to it, the globs of the guarded pages (repo-relative), the
# folder of the question files and the folder of the records (repo-relative, ending with `/`), the globs of the theme
# files (repo-relative)
VAULT = LOG = PROTECTED = QUESTIONS = SPECS = THEMES = None
READ_VERBS = ('check', 'guard', 'pending', 'list')  # what an idle tool (no log, no protected page) answers silently
# The verbs that write an entry: refused (NO_LOG) when no log is configured; every other verb is then silent
WRITE_VERBS = ('add-decision', 'apply-decision', 'defer', 'undefer', 'confirm', 'overrule', 'update', 'remove')
NO_LOG = 'no decision log configured: set paths.decision_log in omc/config.yaml to enable one'
FIELDS = ['Context', 'Decision', 'Automated', 'Affected', 'Source', 'Status']
ENTRY_RE = re.compile(r'^### (\d+) (.+?)\s*$')
FIELD_RE = re.compile(r'^\*\*(' + '|'.join(FIELDS) + r')\.\*\* ?(.*)$')
STATUS_RE = re.compile(r'^recorded (\d{4}-\d\d-\d\d)(?: · deferred (\d{4}-\d\d-\d\d))?(?: · applied (\d{4}-\d\d-\d\d))?$')  # the four forms
NEXT_RE = re.compile(r'Next: (\d+)(\*?)\s*$')
OVERRULED_RE = re.compile(r'^overruled by (\d+)$')  # Automated after the owner's ruling <m> replaced the entry
AUTOMATED_LINE_RE = re.compile(r'^\*\*Automated\.\*\*.*$', re.M)
E2E_LINE_RE = re.compile(r'^[ \t]+\[E2E: .*\][ \t]*$')
RULES_LINE_HASH_RE = re.compile(r'(T\d+(?:\.(?:\d+|x))*)@[0-9a-f]{4}')
RULE_ID_RE = re.compile(r'^R\d+(?:\.(?:\d+|x))*-\d+$')
SUBTHEME_ID_RE = re.compile(r'^T\d+(?:\.(?:\d+|x))*$')
STORY_ID_RE = re.compile(r'^[A-Z]{1,2}\d{1,2}(?:\.\d{1,2})?$')
SCENE_ID_RE = re.compile(r'^[a-z][a-z_]*\.[a-z][a-z0-9_]*$')
VIEW_RE = re.compile(r'^views/([a-z][a-z0-9_]*)$')
COMPONENT_RE = re.compile(r'^[a-z][a-z0-9_]*$')
QUESTION_FILE_FIRST = '# Questions: '
QUESTION_RE = re.compile(r'^### (Q\d+) (.+?)\s*$')
REF_RE = re.compile(r'\b(?P<word>[Dd]ecision(?P<pl>s)?)(?P<sp>\s+)(?P<ids>\d+(?(pl)(?:,\s+\d+(?![\d-]|\.\d))*(?:,?\s+and\s+\d+)?|(?:(?:,\s+\d+(?![\d-]|\.\d))*,?\s+and\s+\d+)?))(?![\d-]|\.\d)')  # decision 41, decisions 12 and 35, decisions 38, 41, 42 (a comma list only after the plural)
OVERRULE_REF_RE = re.compile(r'(\*\*Automated\.\*\* overruled by )(\d+)$')  # an overrule names the entry m by id
ANCHOR_RE = None  # a link to an entry's heading, `<the log's file name>#41%20…`: set by `configure`
CONFLICT_RE = re.compile(r'^(<{7}|={7}|>{7})(?: |$)')  # a line git writes into a file it could not merge

HEADING_RE = re.compile(r'^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$')
FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
STORY_HEADING_RE = re.compile(r'^([A-Z]+\d+(?:\.\d+)?) [—-] ')
RULE_LINE_RE = re.compile(r'^- \[(R\d+(?:\.(?:\d+|x))*-\d+)\] ')
SUBTHEME_HEADING_RE = re.compile(r'^(T\d+(?:\.(?:\d+|x))*) ')
PIN_RE = re.compile(r'^git:([0-9a-f]{7,40})$')  # a link title that pins the link to a commit on main (docs/LINKS.md)
TITLE_RE = re.compile(r'[ \t]+(?:"([^"\n]*)"|\'([^\'\n]*)\')[ \t]*\)')  # a link title after the destination, up to the `)`
# the mentions link_mentions links in Context and Decision: story ids and scene ids
STORY_MENTION_RE = re.compile(r'(?<![\w.§/#-])[A-Z]{1,2}\d{1,2}(?:\.\d{1,2})?(?![\w]|\.\d)')
SCENE_MENTION_RE = re.compile(r'(?<![\w/.\-])[a-z][a-z_]*\.[a-z][a-z0-9_]*(?![\w(]|\.[a-z])')


class RefError(Exception):
    """A name, a reference or an input the tool refuses; the message says why. The log is left untouched."""


# ------------------------------------------------------------------------------------------------------------- links

@dataclass(frozen=True)
class Target:
    file: str            # posix path relative to the vault
    heading: str | None  # the heading's text as written, None for the file itself


@dataclass(frozen=True)
class Link:
    text: str
    dest: str  # as written, relative to the file it stands in, without the title
    start: int = 0
    end: int = 0
    title: str | None = None  # the link title without its quotes: a pin `git:<sha>` (docs/LINKS.md), or None

    @property
    def pin(self):
        """The commit the link is pinned to (its title `git:<sha>`), or None."""
        m = PIN_RE.match(self.title or '')
        return m.group(1) if m else None

    def markdown(self):
        return f'[{self.text}]({self.dest})' if self.title is None else f'[{self.text}]({self.dest} "{self.title}")'


@dataclass
class Heading:
    line: int  # 1-based
    level: int
    text: str


def encode_anchor(heading):
    """The anchor Obsidian writes: every space %20, every backtick %60, everything else raw."""
    return heading.replace(' ', '%20').replace('`', '%60')


def decode_anchor(fragment):
    return unquote(fragment)


def scan_links(text):
    """Every inline link (not image) of text, in order; a destination may hold balanced parentheses and be followed
    by a title (`[S10](stories/supervisor.md#… "git:0f1211d1a2b3")`, a pin, docs/LINKS.md)."""
    out, i = [], 0
    while i < len(text):
        if text[i] == '[' and (i == 0 or text[i - 1] not in '!\\') and text[i + 1:i + 2] != '[':
            depth, close = 0, -1
            for j in range(i, len(text)):
                c = text[j]
                if c == '\n':
                    break
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        close = j
                        break
            if close > 0 and text[close + 1:close + 2] == '(':
                k, depth = close + 2, 0
                while k < len(text) and text[k] not in ' \t\n':
                    if text[k] == '(':
                        depth += 1
                    elif text[k] == ')':
                        if depth == 0:
                            break
                        depth -= 1
                    k += 1
                if k < len(text) and text[k] == ')':
                    out.append(Link(text[i + 1:close], text[close + 2:k], i, k + 1))
                    i = k + 1
                    continue
                t = TITLE_RE.match(text, k) if k < len(text) and k > close + 2 else None
                if t:
                    title = t.group(1) if t.group(1) is not None else t.group(2)
                    out.append(Link(text[i + 1:close], text[close + 2:k], i, t.end(), title))
                    i = t.end()
                    continue
        i += 1
    return out


def unlink(text):
    """text with every inline link replaced by its text: how the corpus reads to a program."""
    out, at = [], 0
    for l in scan_links(text):
        out.append(text[at:l.start])
        out.append(l.text)
        at = l.end
    out.append(text[at:])
    return ''.join(out)


def blank_links(text):
    """text with every inline link blanked to spaces (same length)."""
    for l in scan_links(text):
        text = text[:l.start] + ' ' * (l.end - l.start) + text[l.end:]
    return text


def mask_code(text):
    """text with every inline code span blanked to spaces (same length), so a mention inside one is not linked."""
    return re.sub(r'(`+)(?:(?!\1)[^\n])+?\1', lambda m: ' ' * len(m.group(0)), text)


def headings_of(text):
    """The ATX headings outside fenced code, in order."""
    out, fence = [], None
    for i, line in enumerate(text.split('\n')):
        f = FENCE_RE.match(line)
        if fence is not None:
            if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence) and line.strip() == f.group(1):
                fence = None
            continue
        if f:
            fence = f.group(1)
            continue
        m = HEADING_RE.match(line)
        if m and m.group(2):
            out.append(Heading(i + 1, len(m.group(1)), m.group(2)))
    return out


# ------------------------------------------------------------------------------------------------ the guarded pages

def configure(paths, vault=None):
    """Sets the tool's paths from [paths] (config.Paths): the vault is [vault] (repo-relative; --docs) or else the top
    folder of the log's path (the repository's root for a log there), the log relative to it. RefError when the log,
    a glob of `paths.protected` or `paths.themes` (its literal part, up to its first wildcard) or `paths.questions`
    lies outside the vault: the tool reads only the vault, so what lies outside would go unseen. With no log
    configured (`paths.decision_log` absent) LOG is None and no vault is required: the vault is [vault] or the
    repository's root, nothing checked against it."""
    global VAULT, LOG, PROTECTED, QUESTIONS, SPECS, THEMES, ANCHOR_RE
    PROTECTED, QUESTIONS, SPECS, THEMES = tuple(paths.protected), paths.questions, paths.specs, tuple(paths.themes)
    if paths.decision_log is None:
        vault = posixpath.normpath(vault) if vault else '.'
        VAULT, LOG, ANCHOR_RE = '' if vault == '.' else vault + '/', None, None
        return
    if vault is None:
        vault = paths.decision_log.partition('/')[0] if '/' in paths.decision_log else ''
    vault = posixpath.normpath(vault) if vault else '.'
    log = posixpath.relpath(posixpath.normpath(paths.decision_log), vault)
    if log == '..' or log.startswith('../'):
        raise RefError(f'the log {paths.decision_log} is outside the vault {vault}/')
    prefix = '' if vault == '.' else vault + '/'
    for key, value in [('protected', g) for g in paths.protected] + [('themes', g) for g in paths.themes] + \
            [('questions', paths.questions)]:
        if not re.split(r'[*?\[]', value, maxsplit=1)[0].startswith(prefix):
            raise RefError(f"paths.{key} '{value}' lies outside the vault {prefix or './'} (the folder of "
                           'paths.decision_log)')
    VAULT, LOG = prefix, log
    # the whole file name: `design-decision-log.md#2` is no link to an entry of `decision-log.md`
    ANCHOR_RE = re.compile(r'(?<![\w.-])(' + re.escape(posixpath.basename(log)) + r'#)(\d+(?=%20|\s))')


# On import, until `configured` reads the project's config: no log, as an absent `paths.decision_log` means (an
# in-process caller that needs one configures it)
configure(config.Paths())


def configured(docs=None):
    """The vault's folder, the tool configured (`configure`) from the omc/config.yaml of the repository holding the
    working directory, or with [docs] (--docs) the nearest folder above it that holds omc/config.yaml. RefError when
    there is no repository, no such config or the config is refused."""
    if docs is None:
        here = repo_of(os.getcwd())
        if here is None:
            raise RefError(f'{os.getcwd()} is in no git repository')
        root = here[0]
    else:
        root = os.path.realpath(docs)
        while not os.path.isfile(os.path.join(root, 'omc', 'config.yaml')):
            if os.path.dirname(root) == root:
                raise RefError(f'no omc/config.yaml in {docs} or above it')
            root = os.path.dirname(root)
    try:
        paths = config.load(root).paths
    except config.Refused as e:
        raise RefError(str(e)) from None
    if docs is None:
        configure(paths)
        return os.path.join(root, VAULT)
    configure(paths, os.path.relpath(os.path.realpath(docs), root).replace(os.sep, '/'))
    return docs


def guarded(path):
    """Whether a repo-relative path is one of the guarded pages: `paths.protected` matches it."""
    return config.matches(path, PROTECTED)


def is_guarded(path):
    """Whether a vault path is one of the guarded pages (guarded)."""
    return guarded(posixpath.normpath(VAULT + path))


def normalize(path, text):
    """The text the guard compares: what the link tools write without a decision stripped. A link
    becomes its text, a rule's indented [E2E: …] line goes, a story's Rules line loses its @hashes. None stays None."""
    if text is None or not path.endswith('.md'):
        return text
    lines = [l for l in unlink(text.replace('\r\n', '\n')).split('\n') if not E2E_LINE_RE.match(l)]
    if path.startswith('stories/'):
        lines = [RULES_LINE_HASH_RE.sub(r'\1', l) if l.startswith('**Rules.** ') else l for l in lines]
    return '\n'.join(lines)


# ------------------------------------------------------------------------------------------------------- the vault

@dataclass(frozen=True)
class Resolved:
    file: str     # the vault path the name reaches
    written: str  # what the entry's Affected field holds for it


class Vault:
    """The Markdown files under the vault, and the names `Affected` takes that need an index: the stories by id (from the
    level-3 and level-4 headings of stories/*.md), the rules by id and the subthemes by id (from the theme files,
    those `paths.themes` matches)."""

    def __init__(self, docs_dir):
        self.root = os.path.abspath(docs_dir)
        self.files = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d != '.obsidian')
            for fn in sorted(filenames):
                if fn.endswith('.md'):
                    self.files.append(os.path.relpath(os.path.join(dirpath, fn), self.root).replace(os.sep, '/'))
        self._text, self._headings = {}, {}
        self.stories, self.rules, self.subthemes = {}, {}, {}
        for f in self.files:
            if f.startswith('stories/'):
                for h in self.headings(f):
                    m = STORY_HEADING_RE.match(h.text)
                    if h.level in (3, 4) and m:
                        self._put(self.stories, m.group(1), Target(f, h.text))
            elif config.matches(VAULT + f, THEMES):
                for h in self.headings(f):
                    m = SUBTHEME_HEADING_RE.match(h.text)
                    if h.level >= 2 and m:
                        self._put(self.subthemes, m.group(1), Target(f, h.text))
                for line in self.text(f).split('\n'):
                    m = RULE_LINE_RE.match(line)
                    if m:
                        self._put(self.rules, m.group(1), f)

    @staticmethod
    def _put(index, token, target):
        if token in index and index[token] != target:
            raise RefError(f'"{token}" is defined twice: {index[token]} and {target}')
        index[token] = target

    def text(self, rel):
        if rel not in self._text:
            with open(os.path.join(self.root, rel), encoding='utf-8') as f:
                self._text[rel] = f.read().replace('\r\n', '\n')
        return self._text[rel]

    def headings(self, rel):
        if rel not in self._headings:
            self._headings[rel] = headings_of(self.text(rel))
        return self._headings[rel]

    def is_file(self, rel):
        return os.path.isfile(os.path.join(self.root, rel))

    def has_heading(self, rel, heading):
        return self.is_file(rel) and heading in [h.text for h in self.headings(rel)]

    @staticmethod
    def inside(path):
        """path normalised to a posix path relative to the vault, or None when it leaves the vault (absolute or ../)."""
        if os.path.isabs(path):
            return None
        norm = posixpath.normpath(path)
        return None if norm == '..' or norm.startswith('../') else norm

    def link_to(self, text, target):
        """The link to target from the log, relative to the log's own folder."""
        if target.file == LOG:
            return Link(text, '#' + encode_anchor(target.heading))
        rel = posixpath.relpath(target.file, posixpath.dirname(LOG))
        return Link(text, rel if target.heading is None else f'{rel}#{encode_anchor(target.heading)}')

    def resolve(self, name, gone=frozenset()):
        """A name of --affected as (the file it reaches, what the entry writes). gone: guarded paths deleted on the
        branch, which a name may still reach. RefError when it reaches nothing."""
        name = name.strip()

        def exists(f):
            return self.is_file(f) or f in gone
        if RULE_ID_RE.match(name):
            if name in self.rules:
                return Resolved(self.rules[name], name)
        elif SUBTHEME_ID_RE.match(name):
            if name in self.subthemes:
                return Resolved(self.subthemes[name].file, name)
        elif STORY_ID_RE.match(name):
            if name in self.stories:
                return Resolved(self.stories[name].file, self.link_to(name, self.stories[name]).markdown())
        elif SCENE_ID_RE.match(name):
            f = f'screens/definitions/{name}.md'
            if exists(f):  # a scene of a deleted page is written as text: it no longer resolves for links-check
                return Resolved(f, self.link_to(name, Target(f, None)).markdown() if self.is_file(f) else name)
        elif VIEW_RE.match(name):
            f = f'screens/{name}.md'
            if exists(f):
                return Resolved(f, name)
        elif COMPONENT_RE.match(name):
            f = f'screens/components/{name}.md'
            if exists(f):
                return Resolved(f, name)
        else:
            path, _, heading = name.partition('#')
            path = path[len(VAULT):] if VAULT and path.startswith(VAULT) else path
            if is_guarded(path) and not heading and exists(path):
                return Resolved(path, path)
            if is_guarded(path) and heading and self.has_heading(path, decode_anchor(heading)):
                h = decode_anchor(heading)
                return Resolved(path, self.link_to(h, Target(path, h)).markdown())
        raise RefError(f'no such page: {name}')

    def source(self, ref):
        """A Source reference, a vault path with a heading (a question of a question file, an item of a review file, a
        section of a record), as the link the entry writes; its text is the heading's id when it starts with one."""
        path, _, heading = ref.strip().partition('#')
        path = self.inside(path[len(VAULT):] if VAULT and path.startswith(VAULT) else path)
        if path is None:
            raise RefError(f'a link may not leave the vault {VAULT or "./"}: {ref}')
        if not self.is_file(path):
            raise RefError(f'no such file: {path}')
        if not heading:
            raise RefError(f'a source names a heading: {path}#<heading text>')
        heading = decode_anchor(heading)
        if not self.has_heading(path, heading):
            raise RefError(f'no heading "{heading}" in {path}')
        m = re.match(r'^([A-Za-z]{0,2}\d+(?:\.\d+)*)\.?(?:\s|$)', heading)
        return self.link_to(m.group(1) if m else heading, Target(path, heading)).markdown()

    def target_of(self, dest):
        """The Target a destination written in the log points to, or None when it does not exist."""
        path, _, frag = dest.partition('#')
        file = LOG if path == '' else self.inside(posixpath.join(posixpath.dirname(LOG), path))
        if file is None or not self.is_file(file):
            return None
        if not frag:
            return Target(file, None)
        heading = decode_anchor(frag)
        return Target(file, heading) if self.has_heading(file, heading) else None


def link_mentions(vault, text):
    """text with every certain story id and scene id linked; code spans and existing links are left alone, and an id
    that names nothing stays text."""
    masked = blank_links(mask_code(text))
    replacements = []
    for m in STORY_MENTION_RE.finditer(masked):
        if m.group(0) in vault.stories:
            replacements.append((m.start(), m.end(), vault.link_to(m.group(0), vault.stories[m.group(0)]).markdown()))
    for m in SCENE_MENTION_RE.finditer(masked):
        f = f'screens/definitions/{m.group(0)}.md'
        if vault.is_file(f):
            replacements.append((m.start(), m.end(), vault.link_to(m.group(0), Target(f, None)).markdown()))
    out = text
    for start, end, md in sorted(replacements, reverse=True):
        out = out[:start] + md + out[end:]
    return out


# --------------------------------------------------------------------------------------------------------- the log

class Status(Enum):
    """An entry's Status: one of STATUS_RE's forms (recorded; recorded · deferred, a ruling left for a later branch;
    applied, deferred before or not), or none."""
    RECORDED = 'recorded'
    DEFERRED = 'deferred'
    APPLIED = 'applied'
    MALFORMED = 'malformed'


@dataclass
class Entry:
    n: int
    title: str
    line: int    # 1-based heading line
    body: list   # the lines after the heading, trailing blanks dropped
    fields: dict

    @property
    def status(self):
        m = STATUS_RE.match(self.fields.get('Status', ''))
        return Status.MALFORMED if not m else Status.APPLIED if m.group(3) else Status.DEFERRED if m.group(2) \
            else Status.RECORDED

    def text(self):
        return '\n'.join([f'### {self.n} {self.title}'] + self.body)


@dataclass
class Log:
    lines: list
    next: int | None  # the header's Next: n; None in the old header
    entries: dict     # n -> Entry, in file order
    order: list = field(default_factory=list)  # every Entry in file order, an id twice included (a rebase's leftover)
    trimmed: list = field(default_factory=list)  # main's log only (main_log): the entries main held and trimmed since


def entry_headings(lines):
    """(0-based line index, n, title) of every entry heading, in file order, duplicates included."""
    return [(i, int(m.group(1)), m.group(2)) for i, line in enumerate(lines) if (m := ENTRY_RE.match(line))]


def parse_log(text):
    """The log: the header (every line above the first entry) for its Next, then the entries."""
    lines = text.split('\n')
    heads = entry_headings(lines)
    header = lines[:heads[0][0]] if heads else lines
    nexts = [m for line in header if (m := NEXT_RE.search(line))]
    log = Log(lines, int(nexts[0].group(1)) if nexts else None, {})
    for k, (i, n, title) in enumerate(heads):
        body = lines[i + 1:heads[k + 1][0] if k + 1 < len(heads) else len(lines)]
        while body and body[-1] == '':
            body.pop()
        fields = {f.group(1): f.group(2) for line in body if (f := FIELD_RE.match(line))}
        log.entries[n] = Entry(n, title, i + 1, body, fields)
        log.order.append(log.entries[n])
    return log


def main_log(base_text, older_texts):
    """main's log: the merge-base's, parsed, whose `trimmed` holds every entry an earlier commit of main's log held and
    the merge-base's no longer holds as the same decision. Only a trim removes an entry, so each was applied on main;
    the branch's old fork point is one of those commits, so an entry the branch's side kept from before it is main's."""
    base = parse_log(base_text or '')
    for text in older_texts:
        for e in parse_log(text or '').order:
            if not in_base(e, base) and not trimmed_on_main(e, base):
                base.trimmed.append(e)
    return base


def plain_names(field):
    """The names of an Affected field that are not links: the rest after the links are blanked, split on commas."""
    return [p.strip() for p in blank_links(field).split(',') if p.strip()]


def link_file(dest):
    """The vault path of the file a destination written in the log points to."""
    return posixpath.normpath(posixpath.join(posixpath.dirname(LOG), dest.partition('#')[0]))


def affected_files(vault, entry, gone=frozenset()):
    """The vault paths an entry's Affected field reaches: a link its destination's file, every other name the file it
    resolves to. A name that no longer resolves reaches nothing (the guard then names the file, never crashes)."""
    field = entry.fields.get('Affected', '')
    out = {link_file(l.dest) for l in scan_links(field)}
    for name in plain_names(field):
        try:
            out.add(vault.resolve(name, gone).file)
        except RefError:
            pass
    return out


# ----------------------------------------------------------------------------------------- the guard, pending, trim

def changed_pages(changes):
    """changes: vault path -> (base text or None, working text or None), the candidates git_inputs found. The guarded
    paths whose normalized text differs (an added or a deleted file differs)."""
    return sorted(p for p, (b, n) in changes.items() if is_guarded(p) and normalize(p, b) != normalize(p, n))


def same_decision(a, b):
    """Whether two entries are one decision: the same id, title and Context, link-free (a link's destination may be
    rewritten by /reconcile-links). Two branches that recorded the same id at once hold two decisions under it."""
    return (a.n, unlink(a.title), unlink(a.fields.get('Context', ''))) == \
        (b.n, unlink(b.title), unlink(b.fields.get('Context', '')))


def in_base(e, log_base):
    """Whether entry e is in the merge-base's log: its id there holds the same decision."""
    return e.n in log_base.entries and same_decision(e, log_base.entries[e.n])


def trimmed_on_main(e, log_base):
    """Whether main's log held entry e before the merge-base and trimmed it since (main_log)."""
    return not in_base(e, log_base) and any(same_decision(e, t) for t in log_base.trimmed)


def on_main(e, log_base):
    """Whether entry e is main's: the merge-base's log holds it, or an earlier commit of main's log did."""
    return in_base(e, log_base) or trimmed_on_main(e, log_base)


def of_branch(e, log_base):
    """Whether entry e is the branch's: main's log never held it as the same decision, or main holds it in another
    status (a deferred entry of main the branch took in and acted on). `list --branch` names these."""
    return not on_main(e, log_base) or (in_base(e, log_base) and log_base.entries[e.n].status != e.status)


def applied_on_main(e, log_base):
    """Whether entry e is applied on main: applied in the merge-base's log, or trimmed there since."""
    return (in_base(e, log_base) and log_base.entries[e.n].status == Status.APPLIED) or trimmed_on_main(e, log_base)


def applied_on_branch(log_now, log_base):
    """The branch's applied entries: applied in the working tree's log and not applied on main, as the same decision
   . An entry main held and trimmed since never counts, whichever side of a rebase kept it."""
    return [e for e in log_now.order if e.status == Status.APPLIED and not applied_on_main(e, log_base)]


def guard(vault, changes, log_now, log_base):
    """One line per changed guarded page no entry applied on the branch names (the file is the
    grain, an entry naming a rule covers its theme file)."""
    gone = deleted(changes)
    backed = set()
    for e in applied_on_branch(log_now, log_base):
        backed |= affected_files(vault, e, gone)
    out = []
    for p in changed_pages(changes):
        if p in backed:
            continue
        naming = [e for e in log_now.order if p in affected_files(vault, e, gone)]
        why = ', '.join(f'{e.n} {"applied on main" if e.status == Status.APPLIED else e.status.value}' for e in naming) or 'no entry names it'
        out.append(f'UNBACKED: {VAULT}{p}: changed since the merge-base and no entry applied on this branch names it ({why}); '
                   'an entry recorded for it is applied through /review-decisions; otherwise the owner is asked (/answer-doubt)')
    return out


def unapplied(log):
    """One line per recorded entry not applied; a deferred entry waits for a later branch and is none."""
    return [f'PENDING: decision {e.n} recorded, not applied: {e.title}' for e in log.entries.values() if e.status == Status.RECORDED]


def open_questions(question_files):
    """question_files: vault path -> text of every question file (question_files). One line per open question of a question file."""
    out = []
    for path, text in sorted(question_files.items()):
        lines = text.split('\n')
        if not lines[0].startswith(QUESTION_FILE_FIRST):
            continue
        q = None
        for i, line in enumerate(lines, 1):
            m = QUESTION_RE.match(line)
            if m:
                q = (m.group(1), m.group(2), i)
            elif q and line.strip() == '**Status.** open':
                out.append(f'PENDING: {VAULT}{path}:{q[2]}: {q[0]} {q[1]} is open')
    return out


def disagreed(log):
    """One line per entry acted on against a disagreement of /answer-doubt's two answers and not yet ruled by the owner."""
    return [f'PENDING: decision {e.n} disagreed, not ruled: {e.title}' for e in log.entries.values()
            if e.fields.get('Automated') == 'disagreed']


def pending(log, question_files):
    """The recorded entries not applied, the disagreed entries not ruled, then the open questions of the question files."""
    return unapplied(log) + disagreed(log) + open_questions(question_files)


def automated_ok(value):
    """Automated's values (FORMAT.md › The entry): true, false, disagreed, overruled by <m>."""
    return value in ('true', 'false', 'disagreed') or bool(OVERRULED_RE.match(value or ''))


def automated_moved(old, new):
    """The changes of Automated a committed entry may take, the owner's ruling after the run: none, disagreed to false
    (confirm), disagreed or true to overruled by <m> (overrule)."""
    return old == new or (old == 'disagreed' and new == 'false') or \
        (old in ('disagreed', 'true') and bool(OVERRULED_RE.match(new or '')))


def trim(log_now, log_base):
    """The working log's lines without every entry applied at the merge-base (on main), as the same decision; the
    header, Next included, stays (a deferred entry stays until it is applied on main). Returns (lines, how many
    entries went)."""
    heads = entry_headings(log_now.lines)
    keep, k = list(log_now.lines[:heads[0][0]] if heads else log_now.lines), 0
    for j, ((i, _, _), e) in enumerate(zip(heads, log_now.order)):
        end = heads[j + 1][0] if j + 1 < len(heads) else len(log_now.lines)
        if applied_on_main(e, log_base):
            k += 1
        else:
            keep += log_now.lines[i:end]
    return keep, k


def decision_refs(text):
    """(0-based line, id) of every reference to a decision in text, in order: `decision 41`, `Decisions 12 and 35`,
    `decisions 12, 24 and 30`, a link to an entry's heading in the log (`<the log's file name>#41%20…`, ANCHOR_RE), and
    an entry's `**Automated.** overruled by <m>`."""
    out = []
    for i, line in enumerate(text.split('\n')):
        found = [(m.start('ids'), [int(n) for n in re.findall(r'\d+', m.group('ids'))]) for m in REF_RE.finditer(line)]
        found += [(m.start(2), [int(m.group(2))]) for m in ANCHOR_RE.finditer(line)]
        found += [(m.start(2), [int(m.group(2))]) for m in OVERRULE_REF_RE.finditer(line)]
        out += [(i, n) for _, ns in sorted(found) for n in ns]
    return out


def rewrite_refs(line, ids):
    """line with every reference (decision_refs) to an id of ids (old id -> new id) rewritten to the new id."""
    def num(k):
        return str(ids.get(int(k.group()), k.group()))
    line = REF_RE.sub(lambda m: m.group('word') + m.group('sp') + re.sub(r'\d+', num, m.group('ids')), line)
    line = OVERRULE_REF_RE.sub(lambda m: m.group(1) + num(re.match(r'\d+', m.group(2))), line)
    return ANCHOR_RE.sub(lambda m: m.group(1) + num(re.match(r'\d+', m.group(2))), line)


def masked_refs(e):
    """An entry's text, links unlinked, without its heading's id and with every decision reference's numbers masked:
    what stays the same when renumber moves it."""
    text = unlink('\n'.join([e.title] + e.body))
    text = REF_RE.sub(lambda m: m.group('word') + m.group('sp') + re.sub(r'\d+', '#', m.group('ids')), text)
    text = re.sub(OVERRULE_REF_RE.pattern, r'\1#', text, flags=re.M)
    return ANCHOR_RE.sub(lambda m: m.group(1) + '#', text)


def known_ids(log_base):
    """Every id main's log holds or held (main_log): what a reference on main may name."""
    return set(log_base.entries) | {t.n for t in log_base.trimmed}


def validate_base(log_base, base_refs):
    """The problems of main's side, the base a renumber runs against: its log's ids unique, ascending and below its
    Next, and every reference to a decision anywhere on main (base_refs: (path, 1-based line, id), the log's own
    included) naming an id main's log holds or held. Empty when the base is clean."""
    out, seen, last = [], set(), 0
    for e in log_base.order:
        if e.n in seen:
            out.append(f'{LOG}:{e.line}: id {e.n} twice')
        elif e.n <= last:
            out.append(f'{LOG}:{e.line}: id {e.n} after {last}')
        if log_base.next is not None and e.n >= log_base.next:
            out.append(f'{LOG}:{e.line}: id {e.n} is not below Next: {log_base.next}')
        seen.add(e.n)
        last = max(last, e.n)
    known = known_ids(log_base)
    out += [f'{p}:{line}: decision {n}, which main\'s log never held' for p, line, n in base_refs if n not in known]
    return out


def entry_key(e):
    """An entry's identity across the two sides of a rebase: its title and Context, link-free; never its id, since
    two branches may hold two decisions under one id."""
    return unlink(e.title), unlink(e.fields.get('Context', ''))


def resolve_log(base_text, ours_text, theirs_text):
    """A rebase's conflict of the log, settled entry by entry (three-way, by entry_key): ours is the side the rebase
    builds on (main, with the branch's commits replayed so far), theirs the commit being replayed, base their common
    ancestor. The result holds ours' header and entries in ours' order, then the entries only theirs holds, in theirs'
    order: an entry both hold takes the side that changed it from base (theirs when the commit applied it, ours when
    main did); an entry one side removed and the other left as base had it stays removed (a trim); an entry both
    changed differently is refused. Next is the larger of the two; `renumber` gives the ids once the rebase is done.
    Returns (the log's text, {'main': n, 'branch': [ids taken from theirs], 'dropped': [ids removed]})."""
    base, ours, theirs = parse_log(base_text or ''), parse_log(ours_text), parse_log(theirs_text)
    for side, log in (('main\'s side', ours), ('the commit\'s side', theirs)):
        if any(CONFLICT_RE.match(line) for line in log.lines):
            raise RefError(f'{side} of the log holds conflict markers')
        keys = [entry_key(e) for e in log.order]
        twice = {k[0] for k in keys if keys.count(k) > 1}
        if twice:
            raise RefError(f'{side} of the log holds one entry twice: {", ".join(sorted(twice))}')
    in_base = {entry_key(e): e for e in base.order}
    in_theirs = {entry_key(e): e for e in theirs.order}
    in_ours = {entry_key(e) for e in ours.order}
    out, taken, dropped = [], [], []
    for e in ours.order:
        k, was = entry_key(e), in_base.get(entry_key(e))
        t = in_theirs.get(k)
        if t is None:
            if was is not None and was.text() == e.text():
                dropped.append(e.n)  # the commit removed it (a trim) and main left it as it was
                continue
            out.append(e)
        elif t.text() == e.text() or (was is not None and t.text() == was.text()):
            out.append(e)
        elif was is not None and e.text() == was.text():
            out.append(t)  # the commit changed it (applied it), main did not
        else:
            raise RefError(f'entry {e.n} {e.title}: main and the commit both changed it, differently')
    for t in theirs.order:
        k = entry_key(t)
        if k in in_ours:
            continue
        was = in_base.get(k)
        if was is not None and was.text() == t.text():
            dropped.append(t.n)  # main removed it (main applied it and trimmed it) and the commit left it as it was
            continue
        if was is not None:
            raise RefError(f'entry {t.n} {t.title}: main removed it and the commit changed it')
        out.append(t)
        taken.append(t.n)
    heads = entry_headings(ours.lines)
    header = with_next(ours.lines[:heads[0][0]] if heads else ours.lines, max(ours.next or 1, theirs.next or 1))
    lines = list(header)
    for e in out:
        lines += [''] + e.text().split('\n')
    return log_text(lines), {'main': len(out) - len(taken), 'branch': taken, 'dropped': dropped}


def renumber(log_now, log_base, branch_files, base_refs=()):
    """After a rebase whose log conflicts were resolved to main's entries and this branch's: the branch's own entries
    (main's log never held them as the same decision, main_log) take the ids from main's Next on, in file order, after
    main's; Next follows them. An entry main held and trimmed since goes. Every reference to an own entry is rewritten
    to its new id: in the own entries' text, and in every line the branch added (branch_files: path -> (the file's
    text, the 0-based indexes of the lines the branch added, or None when the branch added the whole file)); a line
    main holds is never touched, so a reference there keeps naming main's decision. A reference the branch added
    names an id its log held when it was written, so one naming an own entry's old id means that entry.
    Refuses (RefError, nothing written) a log with conflict markers, a base that does not validate (validate_base,
    base_refs: (path, 1-based line, id) of every reference on main), two own entries under one id, and a reference
    the branch added that names neither an id of main's nor an own entry's. After the rewrite it checks the result:
    ids unique, ascending and below Next, and every reference the branch added naming what it named before.
    Returns (the log's lines, path -> text of each file changed, [(old, new)] of the ids that moved, [the ids
    dropped])."""
    if any(CONFLICT_RE.match(line) for line in log_now.lines):
        raise RefError(f'{VAULT}{LOG} still holds conflict markers: resolve it to main\'s entries and this branch\'s first')
    if log_base.next is None and log_base.entries:
        raise RefError('the log at the merge-base holds entries and no "Next: <n>"')
    problems = validate_base(log_base, base_refs)
    if problems:
        raise RefError('the base (main) does not validate, so nothing is renumbered against it; fix main first:\n  '
                       + '\n  '.join(problems))
    start = log_base.next or 1  # the old header holds no entries
    own = [e for e in log_now.order if not on_main(e, log_base)]
    olds = [e.n for e in own]
    twice = sorted({n for n in olds if olds.count(n) > 1})
    if twice:
        raise RefError(f'this branch\'s own entries hold an id twice ({", ".join(map(str, twice))}): a reference to it '
                       'cannot be told apart')
    dropped = [e.n for e in log_now.order if trimmed_on_main(e, log_base)]
    ids = {e.n: start + k for k, e in enumerate(own)}  # old -> new, every own entry
    known = known_ids(log_base)

    def meant(n):  # what a reference the branch wrote names, after the renumber
        return ('own', ids[n]) if n in ids else ('main', n)

    # what the branch wrote: the own entries' text, every line it added; each reference names main's or an own entry
    branch = {p: (text.split('\n'), added) for p, (text, added) in branch_files.items()}
    dangling = []
    for e in own:
        dangling += [f'{LOG}:{e.line + i}: decision {n}' for i, n in decision_refs(e.text()) if n not in ids and n not in known]
    for p, (ls, added) in sorted(branch.items()):
        for i, n in decision_refs('\n'.join(ls)):
            if (added is None or i in added) and n not in ids and n not in known:
                dangling.append(f'{p}:{i + 1}: decision {n}')
    if dangling:
        raise RefError('a reference this branch wrote names no decision of main\'s and no entry of this branch\'s:\n  '
                       + '\n  '.join(dangling))

    heads = entry_headings(log_now.lines)
    lines = with_next(log_now.lines[:heads[0][0]] if heads else log_now.lines, start + len(own))
    for e in [e for e in log_now.order if in_base(e, log_base)]:
        lines += [''] + e.text().split('\n')
    for e in own:
        lines += ['', rewrite_refs(f'### {ids[e.n]} {e.title}', ids)] + [rewrite_refs(line, ids) for line in e.body]
    changed = {}
    for p, (ls, added) in branch.items():
        out = [rewrite_refs(line, ids) if added is None or i in added else line for i, line in enumerate(ls)]
        if out != ls:
            changed[p] = '\n'.join(out)

    # the result checked: the log sound, and every reference the branch wrote naming what it named before
    after = parse_log('\n'.join(lines))
    bad = validate_base(after, ())
    def after_meant(n):  # what a reference names in the result: an own entry's id is from start on, main's below
        return ('own', n) if n >= start else ('main', n)

    def words(e):  # an entry's text but its heading's id
        return '\n'.join([e.title] + e.body)
    for e_old, e_new in zip(own, after.order[len(after.order) - len(own):]):
        if e_new.n != ids[e_old.n] or e_new.title != rewrite_refs(e_old.title, ids):
            bad.append(f'{LOG}: entry {e_old.n} did not become {ids[e_old.n]}')
        if [meant(n) for _, n in decision_refs(words(e_old))] != [after_meant(n) for _, n in decision_refs(words(e_new))]:
            bad.append(f'{LOG}:{e_new.line}: the references of entry {e_new.n} changed meaning')
    for p, (ls, added) in branch.items():
        new_ls = changed.get(p, '\n'.join(ls)).split('\n')
        for i, (a, b) in enumerate(zip(ls, new_ls)):
            if added is not None and i not in added:
                if a != b:
                    bad.append(f'{p}:{i + 1}: a line main holds changed')
                continue
            was = [meant(n) for _, n in decision_refs(a)]
            now = [after_meant(n) for _, n in decision_refs(b)]
            if was != now:
                bad.append(f'{p}:{i + 1}: a reference changed meaning')
    if bad:
        raise RefError('the renumber came out wrong, nothing written:\n  ' + '\n  '.join(bad))
    moved = [(e.n, ids[e.n]) for e in own if e.n != ids[e.n]]
    return lines, changed, moved, dropped


# -------------------------------------------------------------------------------------------------------- the check

def check(vault, log, head_log, base_log, gone=frozenset(), refs=()):
    """PROBLEM lines, empty when the log is sound. head_log and base_log: the log at HEAD and at the merge-base, parsed
    (None: no such log). gone: the guarded pages deleted on the branch, which a name may still reach. refs: (path,
    1-based line, id) of every reference to a decision in the repository's files (tree_refs); each must name an id
    the log holds or main's log holds or held, else `dangling-decision`."""
    head = head_log or parse_log('')
    base = base_log or parse_log('')
    problems = []

    def add(line, kind, detail):
        problems.append(f'PROBLEM: {LOG}:{line}: {kind}: {detail}')

    if log.next is None:
        add(1, 'header', 'the header holds no "Next: <n>"')
    seen, last = set(), 0
    for i, n, _ in entry_headings(log.lines):
        if n in seen:
            add(i + 1, 'duplicate-id', f'{n} (after a rebase: keep main\'s entries and this branch\'s, then run `just decisions renumber`)')
        elif n <= last:
            add(i + 1, 'out-of-order', f'{n} after {last}')
        if log.next is not None and n >= log.next:
            add(i + 1, 'id-not-below-next', f'{n} is not below Next: {log.next}')
        seen.add(n)
        last = max(last, n)
    for e in log.order:
        mains = ([base.entries[e.n]] if e.n in base.entries else []) + [t for t in base.trimmed if t.n == e.n]
        if mains and not any(same_decision(e, b) for b in mains):
            add(e.line, 'id-on-main', f'{e.n} on main is another decision ({mains[0].title}): this branch recorded it at the '
                'same time; keep main\'s entries and this branch\'s in the log, then run `just decisions renumber`')
        if trimmed_on_main(e, base):
            add(e.line, 'trimmed-on-main', f'{e.n} was applied on main and trimmed there, and a rebase kept it from '
                'this branch\'s side; it backs no page: `just decisions renumber` at the rebase\'s stop, or '
                '`just decisions trim`, drops it')
    for e in log.order:
        missing = [f for f in ('Context', 'Decision') if f not in e.fields]
        if missing:
            add(e.line, 'malformed-entry', f'{e.n} has no {" or ".join(missing)}')
        if not automated_ok(e.fields.get('Automated')):
            add(e.line, 'malformed-entry', f'{e.n}: Automated is true, false, disagreed or overruled by <n>')
        elif (o := OVERRULED_RE.match(e.fields.get('Automated'))) and not \
                (int(o.group(1)) > e.n and (int(o.group(1)) in log.entries or int(o.group(1)) in known_ids(base))):
            add(e.line, 'dangling-overrule', f'{e.n}: overruled by {o.group(1)}, which is no later entry of the log')
        twice = [f for f in FIELDS if sum(1 for l in e.body if (m := FIELD_RE.match(l)) and m.group(1) == f) > 1]
        if twice:
            add(e.line, 'malformed-entry', f'{e.n} has {", ".join(twice)} twice')
        if e.status == Status.MALFORMED:
            add(e.line, 'malformed-status', f'{e.n}: {e.fields.get("Status", "no Status")}')
        if e.n not in head.entries or head.entries[e.n].status in (Status.RECORDED, Status.DEFERRED):
            # new or still recorded or deferred (P6): every link and every name resolves; an entry applied in HEAD is compared
            # with HEAD's text only, since a later branch may delete a page it names
            body = '\n'.join(e.body)
            for l in scan_links(body):
                # a pinned link resolves at its pin (links-check's); a link to a page deleted on the branch was written
                # while the page existed, and the entry's text never changes
                if l.pin is None and vault.target_of(l.dest) is None and link_file(l.dest) not in gone:
                    add(e.line + 1 + body.count('\n', 0, l.start), 'dead-link', f'{e.n}: {l.markdown()}')
            for name in plain_names(e.fields.get('Affected', '')):
                try:
                    vault.resolve(name, gone)
                except RefError:
                    add(e.line, 'unknown-name', f'{e.n}: {name}')
    known = set(log.entries) | known_ids(base)
    for path, line, n in refs:
        if n not in known:
            problems.append(f'PROBLEM: {path}:{line}: dangling-decision: decision {n}, which neither the log nor main\'s '
                            'log ever held')
    def moved_ok(old, new):  # automated_moved, an overrule's m followed to the id renumber gave it (by its title)
        if automated_moved(old, new):
            return True
        a, b = OVERRULED_RE.match(old or ''), OVERRULED_RE.match(new or '')
        ha, nb = a and head.entries.get(int(a.group(1))), b and log.entries.get(int(b.group(1)))
        return bool(ha and nb) and unlink(ha.title) == unlink(nb.title)

    head_ids = [e.n for e in head.order]
    for n, he in head.entries.items():
        if head_ids.count(n) > 1:
            continue  # a rebase's leftover in HEAD, main's entry and the branch's under one id: renumber settles it
        cur = log.entries.get(n)
        if cur is None or unlink(cur.title) != unlink(he.title):
            moved = [e for e in log.order if e.n != n and unlink(e.title) == unlink(he.title)
                     and not (e.n in head.entries and masked_refs(head.entries[e.n]) == masked_refs(e))]
            if moved:  # renumber moved it: the same entry under a new id, its references to moved entries rewritten
                if he.status == Status.APPLIED and masked_refs(moved[0]) != masked_refs(he):
                    add(moved[0].line, 'edited', f'{n} (now {moved[0].n}) is applied in HEAD and its text changed')
                continue
        if cur is None:
            if not applied_on_main(he, base):
                add(0, 'removed', f'{n} is in HEAD and not in the working tree, and is not applied at the merge-base (only a trim removes)')
        elif he.status == Status.APPLIED:
            # Automated apart: the owner's ruling after the run may move it (automated_moved)
            if unlink(AUTOMATED_LINE_RE.sub('', cur.text())) != unlink(AUTOMATED_LINE_RE.sub('', he.text())) or \
                    not moved_ok(he.fields.get('Automated'), cur.fields.get('Automated')):
                add(cur.line, 'edited', f'{n} is applied in HEAD and its text changed')
        elif [unlink(he.title)] + [unlink(he.fields.get(f, '')) for f in ('Context', 'Decision', 'Source')] != \
                [unlink(cur.title)] + [unlink(cur.fields.get(f, '')) for f in ('Context', 'Decision', 'Source')] or \
                not moved_ok(he.fields.get('Automated'), cur.fields.get('Automated')):
            add(cur.line, 'edited', f'{n}: its title, Context, Decision, Automated or Source changed from HEAD')
    return problems


# ------------------------------------------------------------------------------------------------------- the writes

def log_text(lines):
    """The log's text from its lines: ending with exactly one newline."""
    return '\n'.join(lines).rstrip('\n') + '\n'


def with_next(lines, n):
    """A copy of lines whose first Next (the header's, which parse_log read) is n, trailing blank lines dropped."""
    out = list(lines)
    for i, line in enumerate(out):
        m = NEXT_RE.search(line)
        if m:
            out[i] = line[:m.start()] + f'Next: {n}{m.group(2)}'
            break
    while out and out[-1] == '':
        out.pop()
    return out


def write_log(vault, lines):
    """Writes the log whole (log_text) and forgets the cached text."""
    text = log_text(lines)
    with open(os.path.join(vault.root, LOG), 'w', encoding='utf-8') as f:
        f.write(text)
    vault._text.pop(LOG, None)
    vault._headings.pop(LOG, None)


def render_entry(n, title, fields):
    """The lines of an entry: heading, blank, one line per present field in FIELDS order."""
    return [f'### {n} {title}', ''] + [f'**{label}.** {fields[label]}' for label in FIELDS if fields.get(label)]


def _today(today):
    return today or datetime.date.today().isoformat()


def _clean(value, name):
    if value is None or not value.strip():
        raise RefError(f'{name} is missing')
    return ' '.join(value.split())


def _affected(vault, names, gone):
    return ', '.join(vault.resolve(name, gone).written for name in names if name.strip())


def add_decision(vault, log, title, context, decision, affected=(), source=None, automated=False, gone=frozenset(), today=None,
                 disagreed=False):
    """Appends entry `### <Next>` with Status recorded today and advances the header's Next; returns the id. Automated:
    disagreed when disagreed, true when automated, else false. Refuses both at once, a missing title, context or
    decision, any name or source that resolves to nothing, and a header without Next."""
    if automated and disagreed:
        raise RefError('an entry is automated or disagreed, not both')
    if log.next is None:
        raise RefError(f'the header of {VAULT}{LOG} holds no "Next: <n>"')
    title, context, decision = _clean(title, 'title'), _clean(context, 'context'), _clean(decision, 'decision')
    fields = {
        'Context': link_mentions(vault, context),
        'Decision': link_mentions(vault, decision),
        'Automated': 'disagreed' if disagreed else 'true' if automated else 'false',
        'Affected': _affected(vault, affected, gone),
        'Source': vault.source(source) if source else '',
        'Status': f'recorded {_today(today)}',
    }
    n = log.next
    write_log(vault, with_next(log.lines, n + 1) + [''] + render_entry(n, title, fields))
    return n


def apply_decision(vault, log, n, affected, gone=frozenset(), today=None):
    """Marks recorded or deferred entry n applied today with the real Affected set (empty: applied with nothing to
    change, the field dropped); a deferred one keeps its history, `recorded D1 · deferred D2 · applied D3`. Refuses an
    unknown id and an entry neither recorded nor deferred (already applied, or malformed)."""
    e = log.entries.get(n)
    if e is None:
        raise RefError(f'no such entry: {n}')
    if e.status == Status.APPLIED:
        raise RefError(f'{n} is already applied')
    if e.status not in (Status.RECORDED, Status.DEFERRED):
        raise RefError(f'{n} has a malformed Status; only a recorded or deferred entry can be applied')
    fields = dict(e.fields)
    fields['Affected'] = _affected(vault, affected, gone)
    m = STATUS_RE.match(e.fields['Status'])
    deferred = f' · deferred {m.group(2)}' if m.group(2) else ''
    fields['Status'] = f'recorded {m.group(1)}{deferred} · applied {_today(today)}'
    _rewrite(vault, log, e, fields)


def _rewrite(vault, log, e, fields):
    write_log(vault, log.lines[:e.line - 1] + render_entry(e.n, e.title, fields) + log.lines[e.line + len(e.body):])


def defer_decision(vault, log, n, today=None):
    """Defers recorded entry n to main: Status `recorded D1 · deferred <today>`, the ruling left for a later branch
    (it backs no page and is not pending; apply_decision takes it there). Refuses an unknown id, an entry not recorded
    (applied, deferred or malformed) and an overruling entry, one another entry's `**Automated.** overruled by <n>`
    names: an overrule undoes work this branch did and is applied in it (FORMAT.md › "The entry": never deferred). The log is
    untouched on a refusal."""
    e = log.entries.get(n)
    if e is None:
        raise RefError(f'no such entry: {n}')
    if e.status in (Status.APPLIED, Status.DEFERRED):
        raise RefError(f'{n} is already {e.status.value}: only a recorded entry is deferred')
    if e.status != Status.RECORDED:
        raise RefError(f'{n} has a malformed Status; only a recorded entry is deferred')
    over = [o.n for o in log.order if (m := OVERRULED_RE.match(o.fields.get('Automated', ''))) and int(m.group(1)) == n]
    if over:
        raise RefError(f'{n} overrules {", ".join(map(str, over))}: an overruling entry is applied in this branch, never deferred')
    fields = dict(e.fields)
    fields['Status'] = f'{e.fields["Status"]} · deferred {_today(today)}'
    _rewrite(vault, log, e, fields)


def undefer_decision(vault, log, n, main_log):
    """Takes deferred entry n back to recorded, its recorded date kept. main_log: main's log (origin/main's, parsed;
    None: main holds none). Refuses an unknown id, an entry not deferred, and one main holds deferred (the same id and
    title): a deferral on main is main's, carried by the branch that applies it. The log is untouched on a refusal."""
    e = log.entries.get(n)
    if e is None:
        raise RefError(f'no such entry: {n}')
    if e.status != Status.DEFERRED:
        raise RefError(f'{n} is not deferred (it is {e.status.value}): only a deferred entry is undeferred')
    on = main_log.entries.get(n) if main_log is not None else None
    if on is not None and unlink(on.title) == unlink(e.title) and on.status == Status.DEFERRED:
        raise RefError(f'main holds {n} deferred: a deferral on main is undone only by applying the entry on a branch')
    fields = dict(e.fields)
    fields['Status'] = f'recorded {STATUS_RE.match(e.fields["Status"]).group(1)}'
    _rewrite(vault, log, e, fields)


def _set_automated(vault, log, e, value):
    fields = dict(e.fields)
    fields['Automated'] = value
    _rewrite(vault, log, e, fields)


def confirm_decision(vault, log, n):
    """The owner ruled disagreed entry n as it stands: Automated disagreed becomes false. Refuses an unknown id and an
    entry not disagreed, the log untouched."""
    e = log.entries.get(n)
    if e is None:
        raise RefError(f'no such entry: {n}')
    if e.fields.get('Automated') != 'disagreed':
        raise RefError(f'{n} is not disagreed: only a disagreed entry is confirmed')
    _set_automated(vault, log, e, 'false')


def overrule_decision(vault, log, n, m):
    """The owner's ruling m, a new entry recorded after n, replaced automated entry n (disagreed or true): its Automated
    becomes `overruled by <m>`. Refuses an unknown id, an entry no automated ruling, m not after n and an m that is not
    the owner's ruling (its Automated not false), the log untouched."""
    e = log.entries.get(n)
    for k in (n, m):
        if k not in log.entries:
            raise RefError(f'no such entry: {k}')
    if e.fields.get('Automated') not in ('disagreed', 'true'):
        raise RefError(f'{n} is not disagreed or true: only an automated ruling is overruled')
    if m <= n:
        raise RefError(f'{m} is not recorded after {n}: the owner\'s ruling that overrules it is a new entry')
    if log.entries[m].fields.get('Automated') != 'false':
        raise RefError(f'{m} is not the owner\'s ruling (Automated {log.entries[m].fields.get("Automated")}, not false)')
    _set_automated(vault, log, e, f'overruled by {m}')


def ever_committed(e, heads):
    """Whether entry e was ever in a commit: heads (committed_heads) holds (id, link-free title) of every entry heading
    a commit of HEAD's history added to the log; one with e's id or e's title is e (renumber may have moved it)."""
    return any(n == e.n or t == unlink(e.title) for n, t in heads)


def _uncommitted(log, n, heads):
    """Entry n, refused when unknown or ever committed: only an entry never committed is edited or removed."""
    e = log.entries.get(n)
    if e is None:
        raise RefError(f'no such entry: {n}')
    if ever_committed(e, heads):
        raise RefError(f'{n} has been committed: a committed entry never changes; record a new entry that replaces it')
    return e


def update_decision(vault, log, n, heads, title=None, context=None, decision=None, automated=None, affected=None,
                    source=None, gone=frozenset()):
    """Rewrites the given fields of entry n, never committed (heads: committed_heads), as add-decision writes them;
    the fields not given and the Status stay. affected=[] drops Affected, source='' drops Source. Refuses an entry
    ever committed, automated on an entry disagreed or overruled (confirm and overrule move it) and a name or source
    that resolves to nothing, the log untouched."""
    e = _uncommitted(log, n, heads)
    if automated is not None and (e.fields.get('Automated') == 'disagreed' or OVERRULED_RE.match(e.fields.get('Automated', ''))):
        raise RefError(f'{n} is Automated {e.fields.get("Automated")}: only confirm or overrule moves it, never update --automated')
    fields = dict(e.fields)
    if context is not None:
        fields['Context'] = link_mentions(vault, _clean(context, 'context'))
    if decision is not None:
        fields['Decision'] = link_mentions(vault, _clean(decision, 'decision'))
    if automated is not None:
        fields['Automated'] = 'true' if automated else 'false'
    if affected is not None:
        fields['Affected'] = _affected(vault, affected, gone)
    if source is not None:
        fields['Source'] = vault.source(source) if source.strip() else ''
    title = e.title if title is None else _clean(title, 'title')
    write_log(vault, log.lines[:e.line - 1] + render_entry(n, title, fields) + log.lines[e.line + len(e.body):])


def remove_decision(vault, log, n, heads, refs=(), head_next=None):
    """Drops entry n, never committed (heads: committed_heads), and lowers Next to what the remaining entries and
    HEAD's log allow (never below HEAD's Next: an id a commit holds is never used twice). refs: (path, 1-based line,
    id) of the references to decisions outside the entry itself (tree_refs); one naming n refuses, so no file is left
    naming a decision that is gone."""
    e = _uncommitted(log, n, heads)
    named = [f'{p}:{line}' for p, line, k in refs if k == n]
    if named:
        raise RefError(f'{n} is still named in {", ".join(named)}: change those references first')
    lines = log.lines[:e.line - 1] + log.lines[e.line + len(e.body):]
    if e.line >= 2 and lines[e.line - 2] == '':
        del lines[e.line - 2]  # the blank line above its heading
    floor = max([x.n + 1 for x in log.order if x is not e] + [head_next or 1])
    write_log(vault, with_next(lines, min(log.next, floor)) if log.next is not None else lines)


# ------------------------------------------------------------------------------------------------------ the git reads

@dataclass
class Inputs:
    base: str            # git merge-base HEAD origin/<base>, <base> the `base` of omc/config.yaml
    head_log: str | None
    base_log: str | None
    changes: dict        # vault path -> (base text | None, working text | None), guarded candidates only
    main_logs: list = field(default_factory=list)  # the log at each commit up to the merge-base that changed it

    def main(self):
        """main's log (main_log): the merge-base's, with what main trimmed before it."""
        return main_log(self.base_log, self.main_logs)


def git_inputs(repo, docs):
    """Every git read of the tool: the merge-base, the log at HEAD and at the merge-base, the log at every
    commit of main up to the merge-base that changed it (what main trimmed: main_log), and the guarded pages that
    differ from the merge-base (tracked: git diff against the working tree; untracked: ls-files --others), the
    globs of `paths.protected` as git's pathspecs (none: no page is guarded, git is not asked).
    repo: the repository's root; docs: the vault's path relative to it."""
    def git(*args):
        return subprocess.run(['git', '-C', repo, *args], capture_output=True)

    try:
        branch = config.load(repo).base
    except config.Refused as e:
        raise RefError(str(e)) from None
    r = git('merge-base', 'HEAD', f'origin/{branch}')
    if r.returncode != 0:
        raise RefError(f'no origin/{branch}: git fetch origin')
    base = r.stdout.decode().strip()
    prefix = '' if docs in ('', '.') else docs.rstrip('/') + '/'
    specs = [f':(glob){g}' for g in PROTECTED]
    paths = set()
    for args in (('diff', '-z', '--name-only', '--no-renames', base, '--'), ('ls-files', '-z', '--others', '--exclude-standard', '--')):
        if not specs:
            break
        r = git(*args, *specs)
        if r.returncode != 0:
            raise RefError(f'git {args[0]} failed: {r.stderr.decode().strip()}')
        paths |= {p for p in r.stdout.decode('utf-8').split('\0') if p}
    changes = {}
    for p in sorted(paths):
        rel = p[len(prefix):]
        if not p.startswith(prefix) or not is_guarded(rel):
            continue
        full = os.path.join(repo, p)
        now = None
        if os.path.isfile(full):
            with open(full, encoding='utf-8') as f:
                now = f.read().replace('\r\n', '\n')
        changes[rel] = (git_show(repo, base, p), now)
    return Inputs(base, git_show(repo, 'HEAD', prefix + LOG), git_show(repo, base, prefix + LOG), changes,
                  main_logs(repo, base, prefix + LOG))


def origin_main_log(repo, docs):
    """The log at origin/<base>'s tip (undefer's read: whether main holds an entry deferred), or None when
    origin/<base> holds no log; a missing origin/<base> is a refusal. repo: the repository's root; docs: the vault's
    path relative to it."""
    try:
        branch = config.load(repo).base
    except config.Refused as e:
        raise RefError(str(e)) from None
    if subprocess.run(['git', '-C', repo, 'rev-parse', '--verify', '-q', f'origin/{branch}^{{commit}}'],
                      capture_output=True).returncode != 0:
        raise RefError(f'no origin/{branch}: whether {branch} holds the entry deferred cannot be told')
    prefix = '' if docs in ('', '.') else docs.rstrip('/') + '/'
    return git_show(repo, f'origin/{branch}', prefix + LOG)


def unmerged(repo, path):
    """Whether path is unmerged in repo's index (a conflict git left)."""
    r = subprocess.run(['git', '-C', repo, 'ls-files', '-u', '--', path], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() != ''


def git_show(repo, rev, path):
    """The text of path at rev, or None when rev holds no such file."""
    r = subprocess.run(['git', '-C', repo, 'show', f'{rev}:{path}'], capture_output=True)
    return r.stdout.decode('utf-8').replace('\r\n', '\n') if r.returncode == 0 else None


def main_logs(repo, base, path):
    """The texts of path at every commit up to base that changed it, newest first: one rev-list, then one git show per
    commit (a commit that deleted it holds none; git_inputs' part, the one place the tool reads git)."""
    r = subprocess.run(['git', '-C', repo, 'rev-list', '--full-history', base, '--', path], capture_output=True)
    if r.returncode != 0:
        raise RefError(f'git rev-list failed: {r.stderr.decode().strip()}')
    return [t for c in r.stdout.decode().split() if (t := git_show(repo, c, path)) is not None]


def committed_heads(repo, path):
    """(id, link-free title) of every entry heading a commit of HEAD's history added to the log at path, merges'
    resolutions included: one `git log -p -m`. update and remove refuse an entry it names (ever_committed)."""
    r = subprocess.run(['git', '-C', repo, 'log', '-p', '-m', '--no-renames', '--format=', 'HEAD', '--', path],
                       capture_output=True)
    if r.returncode != 0:
        return set()  # no commit yet: nothing was ever committed
    return {(int(m.group(1)), unlink(m.group(2))) for line in r.stdout.decode('utf-8', 'replace').split('\n')
            if line.startswith('+### ') and (m := ENTRY_RE.match(line[1:]))}


def operation_in_progress(repo):
    """The git operation paused in repo (a rebase, a merge, a cherry-pick, a revert), or None."""
    for name, what in (('rebase-merge', 'a rebase'), ('rebase-apply', 'a rebase'), ('MERGE_HEAD', 'a merge'),
                       ('CHERRY_PICK_HEAD', 'a cherry-pick'), ('REVERT_HEAD', 'a revert')):
        r = subprocess.run(['git', '-C', repo, 'rev-parse', '--git-path', name], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(os.path.join(repo, r.stdout.strip())):
            return what
    return None


HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')


def own_dir(repo):
    """This tool's folder, repo-relative with a trailing slash: its tests write made-up logs, whose ids are fixtures,
    never references, so neither renumber scan reads it."""
    return os.path.relpath(os.path.dirname(os.path.realpath(__file__)), os.path.realpath(repo)).replace(os.sep, '/') + '/'


def branch_files(repo, base, skip=()):
    """What the branch wrote since base, every file of it: path (repo-relative) -> (its text in the working tree, the
    0-based indexes of the lines the branch added, or None for a file the branch added whole). Tracked files from one
    `git diff -U0` against the working tree, untracked ones whole; a deleted or a binary file is left out."""
    r = subprocess.run(['git', '-C', repo, '-c', 'core.quotePath=false', 'diff', '-U0', '--no-renames', '--no-color', '--no-ext-diff', base, '--'],
                       capture_output=True)
    if r.returncode != 0:
        raise RefError(f'git diff failed: {r.stderr.decode().strip()}')
    added, path, new_file = {}, None, False
    for raw in r.stdout.split(b'\n'):
        line = raw.decode('utf-8', 'replace')
        if line.startswith('diff --git '):
            path, new_file = None, False
        elif line.startswith('new file mode'):
            new_file = True
        elif line.startswith('+++ '):
            path = line[6:] if line.startswith('+++ b/') else None
            if path is not None:
                added[path] = None if new_file else set()
        elif path is not None and added[path] is not None and (m := HUNK_RE.match(line)):
            start, count = int(m.group(1)), int(m.group(2) or 1)
            added[path] |= set(range(start - 1, start - 1 + count))
    r = subprocess.run(['git', '-C', repo, 'ls-files', '-z', '--others', '--exclude-standard'], capture_output=True)
    for p in r.stdout.decode('utf-8').split('\0'):
        if p:
            added[p] = None
    out = {}
    for p, lines in added.items():
        full = os.path.join(repo, p)
        if p in skip or p.startswith(own_dir(repo)) or not os.path.isfile(full):
            continue
        try:
            with open(full, encoding='utf-8', newline='') as f:
                out[p] = (f.read(), lines)
        except UnicodeDecodeError:
            continue
    return out


def tree_refs(repo):
    """(path, 1-based line, id) of every reference to a decision (decision_refs) in the working tree's text files,
    tracked and untracked, but this tool's own folder (own_dir): one `git grep`."""
    return _grep_refs(repo, ['--untracked'], '')


def _grep_refs(repo, args, rev):
    log_anchor = re.sub(r'([.^$*+?()\[\]{}|\\])', r'\\\1', posixpath.basename(LOG)) + '#[0-9]'  # a link to an entry, ERE
    # submodule.recurse off: a user's `submodule.recurse=true` makes `git grep --untracked` fail outright
    r = subprocess.run(['git', '-C', repo, '-c', 'core.quotePath=false', '-c', 'submodule.recurse=false', 'grep', '-n', '-I', *args, '-E', '-e',
                        r'[Dd]ecisions?[[:space:]]+[0-9]', '-e', log_anchor, *([rev] if rev else []), '--'],
                       capture_output=True)
    if r.returncode not in (0, 1):
        raise RefError(f'git grep failed: {r.stderr.decode().strip()}')
    out, cut = [], len(rev) + 1 if rev else 0
    for raw in r.stdout.decode('utf-8', 'replace').split('\n'):
        parts = raw[cut:].split(':', 2) if raw and (not rev or raw.startswith(rev + ':')) else None
        if parts and len(parts) == 3 and parts[1].isdigit() and not parts[0].startswith(own_dir(repo)):
            out += [(parts[0], int(parts[1]), n) for _, n in decision_refs(parts[2])]
    return out


def main_lines_refs(refs, branch):
    """The references of refs (tree_refs) on main's lines as they stand on the branch: every line but those the
    branch added (branch, branch_files), so a dangling reference of main's that the branch fixed no longer counts and
    one it left still does."""
    def mains(p, line):
        if p not in branch:
            return True
        added = branch[p][1]
        return added is not None and line - 1 not in added
    return [(p, line, n) for p, line, n in refs if mains(p, line)]


def base_refs(repo, base):
    """(path, 1-based line, id) of every reference to a decision (decision_refs) in every tracked text file at base,
    but this tool's own folder (own_dir): one `git grep`."""
    return _grep_refs(repo, [], base)


def repo_of(docs):
    """(the repository's root, the vault's path relative to it), or None when the vault is in no git repository."""
    r = subprocess.run(['git', '-C', docs, 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    root = r.stdout.strip()
    return root, os.path.relpath(os.path.realpath(docs), os.path.realpath(root)).replace(os.sep, '/')


def question_files(vault):
    """vault path -> text of every question file: each *.md directly in `paths.questions` (not its subfolders), the
    log aside."""
    return {f: vault.text(f) for f in vault.files
            if f != LOG and (VAULT + f).startswith(QUESTIONS) and '/' not in (VAULT + f)[len(QUESTIONS):]}


def _split(value):
    return [v.strip() for v in value.split(',') if v.strip()]


def deleted(changes):
    """The guarded pages of changes deleted on the branch (a name may still reach them)."""
    return frozenset(p for p, (_, n) in changes.items() if n is None)


def _report(lines):
    """OK when clean, else the lines and exit 1."""
    print('\n'.join(lines) if lines else 'OK')
    return 1 if lines else 0


def main(argv=None):
    if hasattr(signal, 'SIGPIPE'):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # `just decisions list | head -3` ends quietly
    parser = argparse.ArgumentParser(prog='decisions', description=__doc__.split('\n')[0])
    parser.add_argument('--docs', default=None, help="the vault (default: the top folder of omc/config.yaml's "
                                                     'paths.decision_log)')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('add-decision', help='append an entry ### <Next> with Status recorded today; prints its id')
    p.add_argument('--title', required=True)
    p.add_argument('--context', required=True)
    p.add_argument('--decision', required=True)
    p.add_argument('--automated', action='store_true', help='a decision no owner ruling was needed for, settled by the docs')
    p.add_argument('--disagreed', action='store_true',
                   help="acted on from /design on although /answer-doubt's two answers disagreed")
    p.add_argument('--affected', default='', help='comma-separated names (FORMAT.md): R9.3-2, T9.3, W9.2, shift.incident, '
                                                  'views/shift_incident, incident_row, screens/FORMAT.md, architecture/operations.md#Incidents')
    p.add_argument('--source', help='<vault path>#<heading>: a question of a question file, an item of a review file')
    p = sub.add_parser('apply-decision', help='mark a recorded entry applied, with the real Affected set')
    p.add_argument('--id', type=int, required=True)
    p.add_argument('--affected', required=True, help='the real set, comma-separated; "" = applied with nothing to change')
    p = sub.add_parser('defer', help='defer a recorded entry to main, for a later branch: Status recorded · deferred today; '
                                     'refuses an overruling entry')
    p.add_argument('--id', type=int, required=True)
    p = sub.add_parser('undefer', help='take a deferred entry back to recorded; refused once origin/main holds it deferred')
    p.add_argument('--id', type=int, required=True)
    p = sub.add_parser('confirm', help='the owner ruled a disagreed entry as it stands: Automated false')
    p.add_argument('id', type=int)
    p = sub.add_parser('overrule', help="the owner's ruling m replaced an automated entry: Automated overruled by <m>")
    p.add_argument('id', type=int)
    p.add_argument('--by', type=int, required=True, help="the owner's ruling, an entry recorded after it")
    p = sub.add_parser('update', help='rewrite the given fields of an entry never committed; refuses one ever committed')
    p.add_argument('id', type=int)
    p.add_argument('--title')
    p.add_argument('--context')
    p.add_argument('--decision')
    p.add_argument('--automated', choices=('true', 'false'), help='refused on an entry disagreed or overruled: confirm or overrule moves it')
    p.add_argument('--affected', help='comma-separated names, as add-decision takes them; "" drops the field')
    p.add_argument('--source', help='<vault path>#<heading>; "" drops the field')
    p = sub.add_parser('remove', help='drop an entry never committed, no file naming it; refuses one ever committed')
    p.add_argument('id', type=int)
    p = sub.add_parser('show', help='entries by id, in full')
    p.add_argument('ids', nargs='+', type=int)
    p = sub.add_parser('list', help='every entry, one line each')
    p.add_argument('--branch', action='store_true',
                   help="only the branch's entries: those main's log never held as the same decision, and main's ones "
                        'the branch changed the status of (a deferred entry it took in and applied)')
    p = sub.add_parser('pending', help='the recorded entries not applied (a deferred one is none), the disagreed entries not ruled and the open questions of the question files; exit 1 when any')
    p.add_argument('--questions', action='store_true', help='the open questions of the question files alone, not the recorded entries')
    sub.add_parser('guard', help='every guarded page changed since the merge-base named by an entry applied on this branch; exit 1 when not')
    sub.add_parser('trim', help='drop every entry applied at the merge-base (on main); Next stays')
    sub.add_parser('resolve', help="at a rebase's stop where the log conflicts: settle it entry by entry from git's "
                                   "three sides (main's entries, then the commit's own) and stage it; renumber after the rebase")
    sub.add_parser('renumber', help="after a rebase whose log conflicts were resolved to main's entries and this branch's: give this "
                                    "branch's entries the ids from main's Next on and rewrite every reference to them "
                                    "the branch wrote; refuses mid-rebase and against a base that does not validate")
    sub.add_parser('check', help='the log parses, ids, fields, names and links are sound, no applied entry changed; exit 1 when not')
    args = parser.parse_args(argv)
    vault = log = None

    def inputs():
        repo = repo_of(vault.root)
        if repo is None:
            raise RefError(f'{vault.root} is in no git repository')
        return git_inputs(*repo)

    def gone():
        """The guarded pages deleted on the branch; none when the vault is in no repository (a dry run on a copy)."""
        repo = repo_of(vault.root)
        return deleted(git_inputs(*repo).changes) if repo else frozenset()
    try:
        root = configured(args.docs)
        if LOG is None:  # no log configured: the read and maintain verbs are silent, the writing ones refused
            if args.command in WRITE_VERBS:
                raise RefError(NO_LOG)
            return 0
        vault = Vault(root)  # a story, rule or subtheme defined twice is a refusal, not a crash
        if not vault.is_file(LOG):
            if not PROTECTED and args.command in READ_VERBS:
                return 0  # idle: no log, no protected page
            raise RefError(f'no such log: {VAULT}{LOG}')
        log = parse_log(vault.text(LOG))
        if args.command == 'add-decision':
            print(add_decision(vault, log, args.title, args.context, args.decision, _split(args.affected), args.source,
                               args.automated, gone(), disagreed=args.disagreed))
        elif args.command == 'defer':
            defer_decision(vault, log, args.id)
            print(args.id)
        elif args.command == 'undefer':
            repo = repo_of(vault.root)
            if repo is None:
                raise RefError(f'{vault.root} is in no git repository: whether main holds the entry deferred is git\'s')
            on_main_text = origin_main_log(*repo)
            undefer_decision(vault, log, args.id, parse_log(on_main_text) if on_main_text is not None else None)
            print(args.id)
        elif args.command == 'confirm':
            confirm_decision(vault, log, args.id)
            print(args.id)
        elif args.command == 'overrule':
            overrule_decision(vault, log, args.id, args.by)
            print(args.id)
        elif args.command == 'apply-decision':
            apply_decision(vault, log, args.id, _split(args.affected), gone())
            print(args.id)
        elif args.command in ('update', 'remove'):
            repo = repo_of(vault.root)
            if repo is None:
                raise RefError(f'{vault.root} is in no git repository: whether an entry was ever committed is git\'s')
            prefix = '' if repo[1] in ('', '.') else repo[1].rstrip('/') + '/'
            heads = committed_heads(repo[0], prefix + LOG)
            if args.command == 'update':
                update_decision(vault, log, args.id, heads, args.title, args.context, args.decision,
                                None if args.automated is None else args.automated == 'true',
                                None if args.affected is None else _split(args.affected), args.source, gone())
            else:
                e = log.entries.get(args.id)
                own = range(e.line, e.line + len(e.body) + 1) if e else range(0)
                refs = [r for r in tree_refs(repo[0]) if not (r[0] == prefix + LOG and r[1] in own)]
                head = git_show(repo[0], 'HEAD', prefix + LOG)
                remove_decision(vault, log, args.id, heads, refs, parse_log(head).next if head else None)
            print(args.id)
        elif args.command == 'show':
            for n in args.ids:
                if n not in log.entries:
                    raise RefError(f'no such entry: {n}')
            print('\n\n'.join(log.entries[n].text() for n in args.ids))
        elif args.command == 'list':
            main_entries = inputs().main() if args.branch else None
            for e in (x for x in log.entries.values() if main_entries is None or of_branch(x, main_entries)):
                print(f'{e.n}  {e.status.value}  Automated: {e.fields.get("Automated", "-")}  {e.title}')
        elif args.command == 'pending':
            return _report(open_questions(question_files(vault)) if args.questions else pending(log, question_files(vault)))
        elif args.command == 'guard':
            i = inputs()
            return _report(guard(vault, i.changes, log, i.main()))
        elif args.command == 'trim':
            i = inputs()
            lines, k = trim(log, i.main())
            if k:
                write_log(vault, lines)
            print(f'{k} entries trimmed')
        elif args.command == 'resolve':
            repo = repo_of(vault.root)
            if repo is None:
                raise RefError(f'{vault.root} is in no git repository')
            if operation_in_progress(repo[0]) != 'a rebase':
                raise RefError('no rebase is in progress: resolve settles a rebase\'s conflict of the log')
            prefix = '' if repo[1] in ('', '.') else repo[1].rstrip('/') + '/'
            path = prefix + LOG
            text, said = resolve_log(git_show(repo[0], ':1', path), git_show(repo[0], ':2', path),
                                     git_show(repo[0], ':3', path)) if unmerged(repo[0], path) else (None, None)
            if text is None:
                raise RefError(f'{VAULT}{LOG} is not in conflict: nothing to resolve')
            write_log(vault, text.rstrip('\n').split('\n'))
            r = subprocess.run(['git', '-C', repo[0], 'add', '--', path], capture_output=True, text=True)
            if r.returncode != 0:
                raise RefError(f'git add failed: {r.stderr.strip()}')
            for n in said['dropped']:
                print(f'decision {n} dropped: a trim on one side')
            print(f"resolved: main's side {said['main']} entries, the commit's own {len(said['branch'])}"
                  f"{' (' + ', '.join(map(str, said['branch'])) + ')' if said['branch'] else ''}; staged. "
                  'Go on with the rebase (git rebase --continue); once it is done, just decisions renumber')
        elif args.command == 'renumber':
            repo = repo_of(vault.root)
            if repo is None:
                raise RefError(f'{vault.root} is in no git repository')
            busy = operation_in_progress(repo[0])
            if busy:
                raise RefError(f'{busy} is in progress: finish it first (every log conflict resolved to main\'s entries '
                               'and this branch\'s), then renumber, so every commit of the branch is in what it rewrites')
            i = inputs()
            prefix = '' if repo[1] in ('', '.') else repo[1].rstrip('/') + '/'
            branch = branch_files(repo[0], i.base, {prefix + LOG})
            # main's log as main holds it (its entries' text never changes), every other file as the branch leaves it
            refs = [r for r in base_refs(repo[0], i.base) if r[0] == prefix + LOG] + \
                main_lines_refs([r for r in tree_refs(repo[0]) if r[0] != prefix + LOG], branch)
            lines, files, moved, dropped = renumber(log, i.main(), branch, refs)
            if log_text(lines) != vault.text(LOG):
                write_log(vault, lines)
            for path, text in files.items():
                with open(os.path.join(repo[0], path), 'w', encoding='utf-8', newline='') as f:
                    f.write(text)
            for n in dropped:
                print(f'decision {n} dropped: applied on main and trimmed there')
            for old, new in moved:
                print(f'decision {old} is now {new}')
            print(f'{len(moved)} entries renumbered')
        elif args.command == 'check':
            i = inputs()
            repo = repo_of(vault.root)  # inputs() refused already when there is none
            return _report(check(vault, log, parse_log(i.head_log or ''), i.main(), deleted(i.changes),
                                 tree_refs(repo[0]) if repo else ()))
    except RefError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
