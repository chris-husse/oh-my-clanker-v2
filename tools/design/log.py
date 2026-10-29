"""The decision log: its parser and its writer.

The log is one Markdown file at the docs root: `## N. <title> (<dates>)` sections, each with optional
`Review file (open):` / `Review file:` and `Iterations:` lines, holding `### N.k <Title>` entries of bold fields."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from design.folder import FENCE_RE, Link, Target, closes_fence, decode_percent, encode_anchor, mask, resolve, scan_links, unlink

DEFAULT_LOG = 'decision-log.md'  # the log's name when no tools/corpus.yaml says otherwise; it sits at the docs root
DEFAULT_ROOT = 'docs'  # the docs folder relative to the repository, likewise
FIELDS = ['Context', 'Decision', 'Automated', 'Affected', 'Supersedes', 'Source', 'Status']

SECTION_RE = re.compile(r'^## (\d+)\. (.*?) \(([^)]*)\)\s*$')
ENTRY_RE = re.compile(r'^### (\d+)\.(\d+) (.+?)\s*$')
FIELD_RE = re.compile(r'^\*\*(' + '|'.join(FIELDS) + r')\.\*\* ?(.*)$')
ANSWERS_RE = re.compile(r'^Answers: (.*)$')
STATUS_RE = re.compile(r'^(?:note|recorded (\d{4}-\d\d-\d\d)(?: · applied (\d{4}-\d\d-\d\d)(, nothing to change)?)?)$')
RULING_ID_RE = re.compile(r'^\d{1,3}\.\d{1,3}$')
LOG_SECTION_ID_RE = re.compile(r'^§\d{1,3}$')
REVIEW_FILE_RE = re.compile(r'^Review file( \(open\))?: (.+?)\s*$')
ITERATIONS_RE = re.compile(r'^Iterations: (\d+)\s*$')


@dataclass
class Entry:
    id: str
    section: int
    number: int
    title: str
    line: int  # 1-based line of the heading
    end: int  # exclusive 0-based index past the last line, trailing blanks trimmed: log.lines[line - 1:end] == lines
    fields: dict[str, str] = field(default_factory=dict)
    automated_values: list[str] = field(default_factory=list)  # parsed occurrences, including duplicates
    answers: str | None = None
    lines: list[str] = field(default_factory=list)  # the heading through the last line
    file: str = DEFAULT_LOG  # the log's path relative to the docs folder, which its links are relative to

    def status(self) -> str:
        """'note', 'recorded', 'applied', or 'malformed' when the Status line is missing or fails STATUS_RE."""
        s = self.fields.get('Status')
        m = STATUS_RE.match(s) if s is not None else None
        if m is None:
            return 'malformed'
        if s == 'note':
            return 'note'
        return 'applied' if m.group(2) else 'recorded'

    def kind(self) -> str:
        """'note', 'decision', or 'malformed': a bad or missing Status, or a decision (recorded or applied, or any
        entry with Context or Decision) that lacks Context or Decision."""
        status = self.status()
        if status == 'malformed':
            return 'malformed'
        has = ('Context' in self.fields, 'Decision' in self.fields)
        if (status != 'note' or any(has)) and not all(has):
            return 'malformed'
        return 'note' if status == 'note' else 'decision'

    def date(self) -> str | None:
        """The recorded date, None for a note or a malformed status."""
        s = self.fields.get('Status')
        m = STATUS_RE.match(s) if s is not None else None
        return m.group(1) if m else None

    def text(self) -> str:
        return '\n'.join(self.lines)

    def links(self) -> list[Link]:
        """Every link in text(), outside code; offsets index text()."""
        return scan_links(mask(self.text()))

    def link_free(self) -> str:
        return unlink(self.text())

    def _field_links(self, label: str) -> list[tuple[Link, str]]:
        value = self.fields.get(label, '')
        return [(l, value[l.text_start:l.text_end]) for l in scan_links(mask(value)) if not l.image]

    def targets(self, label: str) -> list[Target]:
        """The links of field label: the file relative to the docs folder (the log's own file for a link inside the
        log) and the decoded heading, None for a file link."""
        out = []
        for l, _ in self._field_links(label):
            path, frag = resolve(self.file, l.dest)
            out.append(Target(path, None if frag is None else decode_percent(frag)))
        return out

    def affected(self) -> list[Target]:
        """The Affected field's links, as targets."""
        return self.targets('Affected')

    def supersedes(self) -> list[str]:
        """The link texts of the Supersedes field: entry ids ('1.1') and log sections ('§1')."""
        return [text.strip() for _, text in self._field_links('Supersedes')]


@dataclass
class Section:
    n: int
    title: str
    dates: str  # the parenthesized part of the heading, as written
    line: int  # 1-based line of the heading
    review_file: str | None = None
    review_open: bool = False
    iterations: int | None = None
    entries: list[Entry] = field(default_factory=list)


@dataclass
class Log:
    lines: list[str]
    sections: list[Section]
    entries: dict[str, Entry]
    file: str = DEFAULT_LOG  # the log's name in the docs folder
    root: str = DEFAULT_ROOT  # the docs folder relative to the repository: the prefix of a Review file line

    @property
    def open_section(self) -> Section | None:
        """The section new entries go to: always the last one."""
        return self.sections[-1] if self.sections else None


def parse_log(text: str, file: str = DEFAULT_LOG, root: str = DEFAULT_ROOT) -> Log:
    """The log in text; file is its name in the docs folder, root the folder relative to the repository (both from
    tools/corpus.yaml, through decisions.settings)."""
    lines = text.split('\n')
    log = Log(lines, [], {}, file, root)
    section: Section | None = None
    entry: Entry | None = None
    fence: str | None = None

    def close_entry(end: int):
        nonlocal entry
        if entry is None:
            return
        while end > entry.line and lines[end - 1] == '':
            end -= 1
        entry.end = end
        entry.lines = lines[entry.line - 1:end]
        entry = None

    for i, line in enumerate(lines):
        f = FENCE_RE.match(line)
        if fence is not None:
            if f and closes_fence(line, f.group(1), fence):
                fence = None
            continue
        if f:
            fence = f.group(1)
            continue
        s = SECTION_RE.match(line)
        if s:
            close_entry(i)
            section = Section(int(s.group(1)), s.group(2), s.group(3), i + 1)
            log.sections.append(section)
            continue
        e = ENTRY_RE.match(line)
        if e and section is not None:
            close_entry(i)
            entry = Entry(f'{e.group(1)}.{e.group(2)}', int(e.group(1)), int(e.group(2)), e.group(3), i + 1, i + 1, file=file)
            section.entries.append(entry)
            log.entries[entry.id] = entry
            continue
        if entry is not None:
            m = FIELD_RE.match(line)
            if m:
                entry.fields[m.group(1)] = m.group(2)
                if m.group(1) == 'Automated':
                    entry.automated_values.append(m.group(2))
            a = ANSWERS_RE.match(line)
            if a:
                entry.answers = a.group(1)
        elif section is not None:
            r = REVIEW_FILE_RE.match(line)
            if r:
                section.review_file, section.review_open = r.group(2), bool(r.group(1))
            n = ITERATIONS_RE.match(line)
            if n:
                section.iterations = int(n.group(1))
    close_entry(len(lines))
    return log


def render_entry(entry_id: str, title: str, fields: dict[str, str], answers: str | None = None) -> list[str]:
    """The lines of an entry: heading, blank, one line per non-empty field in FIELDS order, Answers, blank."""
    lines = [f'### {entry_id} {title}', '']
    for label in FIELDS:
        if fields.get(label):
            lines.append(f'**{label}.** {fields[label]}')
    if answers:
        lines.append(f'Answers: {answers}')
    lines.append('')
    return lines


def write_log(path: Path, lines: list[str]) -> None:
    """Writes the log whole, ending with exactly one newline."""
    Path(path).write_text('\n'.join(lines).rstrip('\n') + '\n', encoding='utf-8', newline='\n')


def header_lines() -> list[str]:
    return ['# Decision Log', '', '*Append-only. Every ruling and its reasoning, dated.*', '']


def entry_link(entry_id: str, title: str) -> str:
    """The in-log link destination of an entry: '#1.2%20Title'."""
    return '#' + encode_anchor(f'{entry_id} {title}')
