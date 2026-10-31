"""The decision log's commands: show, list, search, history, check, new-section, add-decision, add-note, apply-decision, close-section, body.

The tool is the log's only writer. Every writing command checks everything first and writes the file whole, so an
error leaves the log untouched."""
from __future__ import annotations

import argparse
import datetime
import posixpath
import re
import signal
import subprocess
import sys
from pathlib import Path

import yaml

from design.folder import Corpus, Folder, Target, decode_percent, encode_anchor, escapes, headings_of, mask, repo_root, resolve, scan_links, unlink
from design.log import (DEFAULT_LOG, DEFAULT_ROOT, FIELD_RE, FIELDS, LOG_SECTION_ID_RE, RULING_ID_RE, Entry, Log, Section, parse_log,
                        render_entry, write_log)

DATE_RE = re.compile(r'\d{4}-\d\d-\d\d')
ID_TOKEN_RE = re.compile(r'^(\d+(?:\.\d+)*)[ .]')
SCHEME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:')
BOLD_LABEL_RE = re.compile(r'^\*\*([^*\n]+?)\.\*\*')
STRUCTURE_RE = re.compile(r'^\s*(?:#|`{3}|~{3}|\*\*[^*\n]+?\.\*\*|Review file|Iterations:|Answers:)')  # bold label: BOLD_LABEL_RE's shape


class RefError(Exception):
    """An unresolvable reference or a bad argument; a writing command leaves the log untouched."""


def settings(docs: Path | None = None) -> tuple[Path, str, str]:
    """(docs folder, log file name, docs root relative to the repository) from `tools/corpus.yaml`.

    The corpus.yaml is that of the repository holding `docs` when given, else of the repository holding the working
    directory. `docs` (the `--docs` override, for dry runs on a copy) replaces only the folder: the log name and the
    root still come from that corpus.yaml, or are `decision-log.md` and `docs` when no corpus.yaml is found."""
    for start in ([Path(docs)] if docs is not None else []) + [None]:
        try:
            root = repo_root(start)
        except RuntimeError:
            continue
        if (root / 'tools' / 'corpus.yaml').is_file():
            c = Corpus.load(root)
            if '/' in c.log:
                raise RefError(f'the log must sit at the docs root, not {c.log}')
            return (Path(docs) if docs is not None else root / c.root), c.log, c.root.rstrip('/')
    if docs is None:
        return repo_root() / DEFAULT_ROOT, DEFAULT_LOG, DEFAULT_ROOT
    return Path(docs), DEFAULT_LOG, DEFAULT_ROOT


def load(docs: Path) -> tuple[Folder, Log]:
    """The docs folder (git's files when it is in a repository) and its parsed log, named by `settings`."""
    docs, log_file, root = settings(docs)
    try:
        folder = Folder.git(docs)
    except RuntimeError:
        folder = Folder.dir(docs)
    path = folder.root / log_file
    if not path.is_file():
        raise RefError(f'no log at {path}')
    return folder, parse_log(path.read_text(encoding='utf-8').replace('\r\n', '\n'), log_file, root)


# References

def _log_heads(log: Log) -> tuple[set[str], set[str], set[str]]:
    """The log's linkable entry headings (recorded and applied decisions), its note headings, its section headings."""
    entries, notes = set(), set()
    for s in log.sections:
        for e in s.entries:
            (notes if e.status() == 'note' else entries).add(f'{e.id} {e.title}')
    return entries, notes, {_section_target(log, s).heading for s in log.sections}


def _why_not(folder: Folder, log: Log, target: Target, sections: bool, heads=None) -> str | None:
    """None when a link written in the log may point at target, else why not. Inside the log a link names a
    decision; a section only where sections is true (the Supersedes field); a note never."""
    if target.file == log.file:
        if target.heading is None:
            return None
        entries, notes, secs = heads if heads is not None else _log_heads(log)
        if target.heading in entries or (sections and target.heading in secs):
            return None
        if target.heading in notes:
            return 'a note; notes are never linked to'
        if target.heading in secs:
            return 'a log section, linked only from Supersedes'
        return f'no such heading in {target.file}: {target.heading}'
    if not folder.is_file(target.file):
        return f'no such file: {target.file}'
    if target.heading is not None and not folder.has_heading(target.file, target.heading):
        return f'no such heading in {target.file}: {target.heading}'
    return None


def _dest(log: Log, target: Target) -> str:
    """The destination of target in a link written in the log, which sits at the docs root."""
    if target.file == log.file and target.heading is not None:
        return '#' + encode_anchor(target.heading)
    path = encode_anchor(target.file)
    return path if target.heading is None else f'{path}#{encode_anchor(target.heading)}'


def _text(target: Target) -> str:
    """The text of an Affected link: the heading's leading id token, else the heading, else the file's stem."""
    if target.heading is None:
        return posixpath.splitext(posixpath.basename(target.file))[0]
    m = ID_TOKEN_RE.match(target.heading)
    return m.group(1) if m else target.heading


def _entry_target(e: Entry) -> Target:
    return Target(e.file, f'{e.id} {e.title}')


def _section_target(log: Log, s: Section) -> Target:
    return Target(log.file, f'{s.n}. {s.title} ({s.dates})')


def _resolve(folder: Folder, log: Log, arg: str, sections: bool = True) -> tuple[Target, str]:
    """(target, link text) of a link argument; a log section only when sections is true."""
    arg = _clean(arg, 'link')
    if RULING_ID_RE.match(arg):
        found = [e for s in log.sections for e in s.entries if e.id == arg]
        if not found:
            raise RefError(f'no such entry: {arg}')
        if len(found) > 1:
            raise RefError(f'{arg} is in the log more than once')
        if found[0].status() == 'note':
            raise RefError(f'{arg} is a note; notes are never linked to')
        return _entry_target(found[0]), arg
    if LOG_SECTION_ID_RE.match(arg):
        found = [s for s in log.sections if s.n == int(arg[1:])]
        if len(found) != 1:
            raise RefError(f'no such log section: {arg}' if not found else f'{arg} is in the log more than once')
        if not sections:
            raise RefError(f'{arg} is a log section, linked only from Supersedes')
        return _section_target(log, found[0]), arg
    path, hash_, heading = arg.partition('#')
    if path.startswith('/'):
        raise RefError(f'{arg} leaves the docs folder')
    path = posixpath.normpath(path) if path else ''
    if escapes(path):
        raise RefError(f'{arg} leaves the docs folder')
    if path in ('', '.'):
        raise RefError(f'no file in {arg}')
    target = Target(path, decode_percent(heading) if hash_ else None)
    why = _why_not(folder, log, target, sections)
    if why is not None:
        raise RefError(f'{arg}: {why}')
    return target, _text(target)


def resolve_link_arg(folder: Folder, log: Log, arg: str, sections: bool = True) -> tuple[Target, str]:
    """The target of a link argument and its Markdown link, relative to the log: 'design/02-x.md#2.1 Title' ->
    '[2.1](design/02-x.md#2.1%20Title)'; '1.1' and '§1' name an entry and a section of the log. Raises RefError when
    the file or heading does not exist, the argument leaves the folder, or it names a note (or a log section, unless
    sections is true: only Supersedes links a section)."""
    target, text = _resolve(folder, log, arg, sections)
    return target, f'[{text}]({_dest(log, target)})'


def _links(folder: Folder, log: Log, args, sections: bool = False) -> str:
    return ', '.join(resolve_link_arg(folder, log, a, sections)[1] for a in args or ())


def _source_link(folder: Folder, log: Log, arg: str) -> str:
    target, _ = _resolve(folder, log, arg, sections=False)
    if target.heading is None:
        raise RefError(f'a source names a heading, never a file alone: {arg}')
    return f'[{target.heading}]({_dest(log, target)})'


def _supersedes_links(folder: Folder, log: Log, args) -> str:
    for a in args or ():
        if not (RULING_ID_RE.match(a.strip()) or LOG_SECTION_ID_RE.match(a.strip())):
            raise RefError(f'a superseded ruling is an entry id (1.2) or a log section (§1): {a}')
    return _links(folder, log, args, sections=True)


def _dead_links(folder: Folder, log: Log, text: str, heads=None) -> list[tuple]:
    """(link, why) for each link of text (written in the log) that may not stand: its target does not exist, or it
    is a note, or a log section outside a Supersedes line. Pinned and external links are skipped."""
    out = []
    for link in scan_links(mask(text)):
        if link.pin is not None or SCHEME_RE.match(link.dest):
            continue
        path, frag = resolve(log.file, link.dest)
        if escapes(path):
            out.append((link, 'leaves the docs folder'))
            continue
        line = text[text.rfind('\n', 0, link.start) + 1:]
        why = _why_not(folder, log, Target(path, decode_percent(frag) if frag else None), line.startswith('**Supersedes.**'), heads)
        if why is not None:
            out.append((link, why))
    return out


# Reading

def _prefix_filter(folder: Folder, log: Log, ref: str):
    """A predicate on targets for a search prefix: 'path-prefix' or 'path#heading' (exact)."""
    path, hash_, _ = ref.partition('#')
    if hash_:
        want, _ = _resolve(folder, log, ref)
        return lambda t: t == want
    if not path or not any(f.startswith(path) for f in [*folder.files, log.file]):
        raise RefError(f'nothing in the docs folder starts with {path!r}')
    return lambda t: t.file.startswith(path)


def _date(log: Log, e: Entry) -> str | None:
    """The recorded date; for a note, its section's first date."""
    if e.date():
        return e.date()
    s = next((s for s in log.sections if e in s.entries), None)
    m = DATE_RE.search(s.dates) if s else None
    return m.group(0) if m else None


def search(folder, log, affected=None, source=None, supersedes=None, status=None, section=None, since=None, text=None, automated=None) -> list[Entry]:
    """The entries matching every given filter, in file order. --affected and --source match a link target by path
    prefix, or exactly with '#heading'; a reference that matches nothing in the folder raises RefError."""
    out = list(log.entries.values())
    for label, ref in [('Affected', affected), ('Source', source)]:
        if ref is not None:
            hit = _prefix_filter(folder, log, ref)
            out = [e for e in out if any(hit(t) for t in e.targets(label))]
    if supersedes is not None:
        want, _ = _resolve(folder, log, supersedes)
        out = [e for e in out if want in e.targets('Supersedes')]
    if status is not None:
        out = [e for e in out if e.status() == status]
    if automated is not None:
        if automated not in ('true', 'false', 'unspecified'):
            raise RefError('automated must be true, false or unspecified')
        out = [e for e in out if e.kind() == 'decision'
               and e.fields.get('Automated', 'unspecified') == automated]
    if section is not None:
        out = [e for e in out if e.section == int(section)]
    if since is not None:
        out = [e for e in out if (_date(log, e) or '') >= since]
    if text is not None:
        rx = re.compile(text, re.MULTILINE)
        out = [e for e in out if rx.search(e.link_free())]
    return out


def direct_later(log: Log, e: Entry) -> list[str]:
    """Ids of the later entries whose Supersedes names e itself, in file order."""
    target = _entry_target(e)
    return [o.id for o in log.entries.values() if o.line > e.line and target in o.targets('Supersedes')]


def _automated_supersedable(log: Log, entry_id: str, before: int | None = None) -> str | None:
    """None when an automated ruling may supersede entry_id: an automated decision that no non-automated entry
    (above line `before`, when given) supersedes, directly or through a chain; otherwise the reason. Legacy entries
    count as human."""
    e = log.entries.get(entry_id)
    if e is None:
        return None  # an unknown id is the link check's to refuse
    if e.kind() != 'decision':
        return 'is not a decision'
    provenance = e.fields.get('Automated', 'unspecified')
    if provenance == 'unspecified':
        return 'is a legacy ruling (Automated unspecified), treated as human'
    if provenance != 'true':
        return 'is a human ruling'
    if any(log.entries[i].fields.get('Automated') != 'true' and (before is None or log.entries[i].line < before)
           for i in later_chain(log, e)):
        return 'is superseded by a human ruling'
    return None


def later_chain(log: Log, e: Entry) -> list[str]:
    """Ids of the entries pointing at e through Supersedes, directly or through a chain, in file order."""
    found, queue = [], [e]
    while queue:
        for i in direct_later(log, queue.pop(0)):
            if i not in found and i != e.id:
                found.append(i)
                queue.append(log.entries[i])
    return sorted(found, key=lambda i: log.entries[i].line)


def history(folder, log, ref: str) -> list[tuple[Entry, list[str]]]:
    """The entries whose Affected or Supersedes links hit ref (a file names every heading in it; an entry id names
    the entry itself too), in file order, each with the ids of the later entries that supersede it directly."""
    target, _ = _resolve(folder, log, ref)

    def hit(t: Target) -> bool:
        return t == target or (target.heading is None and t.file == target.file)

    own = target if RULING_ID_RE.match(ref.strip()) else None
    hits = [e for e in log.entries.values()
            if (own is not None and _entry_target(e) == own) or any(hit(t) for t in e.affected() + e.targets('Supersedes'))]
    return [(e, direct_later(log, e)) for e in hits]


def format_oneline(e: Entry) -> str:
    provenance = f'  Automated: {e.fields.get("Automated", "unspecified")}' if e.kind() == 'decision' else ''
    return f'{e.id}  {e.fields.get("Status") or "(no status)"}{provenance}  {e.title}'


def format_history(folder, log, ref: str) -> str:
    """The history of ref, followed through Supersedes: the hits and every entry of their later chains, in file
    order, each with its direct `later:` leads."""
    ids = set()
    for e, _ in history(folder, log, ref):
        ids.add(e.id)
        ids.update(later_chain(log, e))
    out = [f'# How we got here: {ref}', '']
    for e in sorted((log.entries[i] for i in ids), key=lambda e: e.line):
        out.append(e.text())
        later = direct_later(log, e)
        if later:
            out.append(f'later: {", ".join(later)}')
        out.append('')
    return '\n'.join(out)


def check(folder, log, head_text: str | None) -> list[str]:
    """Problem lines, empty when the log is sound; head_text (the committed log) enables the immutability rule."""
    problems = []

    def add(line, kind, detail):
        problems.append(f'PROBLEM: {log.file}:{line}: {kind}: {detail}')

    head = parse_log(head_text, log.file, log.root) if head_text is not None else None
    heads = _log_heads(log)
    prefix = log.root + '/'
    seen, last = set(), (0, 0)
    for s in log.sections:
        if s.review_open and s.review_file is not None:
            rel = s.review_file[len(prefix):] if s.review_file.startswith(prefix) else None
            if rel is None or not folder.is_file(rel):
                add(s.line, 'unresolved-section', f'§{s.n} names {s.review_file}, which does not exist')
        for e in s.entries:
            key = (e.section, e.number)
            if e.id in seen or key <= last:
                add(e.line, 'duplicate-id' if e.id in seen else 'out-of-order', e.id)
            seen.add(e.id)
            last = max(last, key)
            if e.section != s.n:
                add(e.line, 'wrong-section', f'{e.id} under section {s.n}')
            status = e.status()
            if status == 'malformed':
                add(e.line, 'malformed-status', f'{e.id}: {e.fields.get("Status", "no Status line")}')
            elif status == 'note' and any(k != 'Status' for k in e.fields):
                add(e.line, 'malformed-entry', f'{e.id} is a note and has {", ".join(k for k in e.fields if k != "Status")}')
            elif status != 'note' and not ('Context' in e.fields and 'Decision' in e.fields):
                add(e.line, 'malformed-entry', f'{e.id} lacks Context or Decision')
            unknown = [m.group(1) for line in mask(e.text()).split('\n')
                       if (m := BOLD_LABEL_RE.match(line)) and m.group(1) not in FIELDS]
            if unknown:
                add(e.line, 'malformed-entry', f'{e.id} has the unknown field {", ".join(unknown)}')
            if len(e.automated_values) > 1 or any(v not in ('true', 'false') for v in e.automated_values):
                add(e.line, 'malformed-entry', f'{e.id}: Automated must occur once with true or false when present')
            if head is not None and e.id not in head.entries and e.kind() == 'decision' and not e.automated_values:
                add(e.line, 'malformed-entry', f'{e.id}: new decisions require Automated provenance')
            if e.fields.get('Automated') == 'true':
                by_target = {_entry_target(o): o for o in log.entries.values()}
                for t in e.targets('Supersedes'):
                    o = by_target.get(t)
                    why = _automated_supersedable(log, o.id, e.line) if o is not None else 'is a log section'
                    if why:
                        add(e.line, 'malformed-entry', f'{e.id}: automated decisions supersede only automated rulings: '
                            f'{o.id if o is not None else t.heading} {why}')
            if status == 'recorded' or (head is not None and e.id not in head.entries):
                # recorded, or new since HEAD: every link must stand; the links of applied entries and notes are the
                # link checker's business (they age as the documents move on)
                text = e.text()
                for link, why in _dead_links(folder, log, text, heads):
                    add(e.line + text.count('\n', 0, link.start), 'dead-link', f'{e.id}: {text[link.start:link.end]} ({why})')
    if head is not None:
        for hid, he in head.entries.items():
            cur = log.entries.get(hid)
            if cur is not None and cur.fields.get('Automated') != he.fields.get('Automated'):
                add(cur.line, 'edited', f'{hid}: Automated provenance changed from HEAD')
                continue
            if he.status() not in ('applied', 'note'):
                continue
            if cur is None:
                add(0, 'removed', f'{hid} is in HEAD but not in the working tree')
            elif cur.link_free() != he.link_free():
                add(cur.line, 'edited', f'{hid} is {he.status()} in HEAD and its text changed')
    return problems


# Writing

def _today(today: str | None) -> str:
    if today is None:
        return datetime.date.today().isoformat()
    try:
        if DATE_RE.fullmatch(today) and datetime.date.fromisoformat(today):
            return today
    except ValueError:
        pass
    raise RefError(f'not a date (YYYY-MM-DD): {today}')


def _clean(value: str | None, name: str) -> str:
    """value stripped; RefError naming the field when it is missing or holds a newline."""
    if value is None or not value.strip():
        raise RefError(f'{name} is missing')
    if '\n' in value or '\r' in value:
        raise RefError(f'{name} holds a newline; a field is one line')
    return value.strip()


def _free(value: str | None, name: str) -> str:
    """A free-text value (title, context, decision, note text, description), cleaned; RefError when it would read as
    log structure at the start of a line: a heading, a fence, a bold `**Label.**` (any label: check reads one as a field), a Review file, Iterations or Answers line."""
    value = _clean(value, name)
    if STRUCTURE_RE.match(value):
        raise RefError(f'{name} starts like a line of the log\'s structure (heading, fence, field, Review file, Iterations, Answers): {value[:40]}')
    return value


def _write(folder: Folder, log: Log, lines: list[str]) -> None:
    write_log(folder.root / log.file, lines)


def _append(folder: Folder, log: Log, block: list[str]) -> None:
    lines = list(log.lines)
    while lines and lines[-1] == '':
        lines.pop()
    _write(folder, log, lines + [''] + block)


def _check_text_links(folder: Folder, log: Log, value: str, name: str) -> None:
    dead = _dead_links(folder, log, value)
    if dead:
        raise RefError(f'{name}: ' + '; '.join(f'{value[l.start:l.end]} ({why})' for l, why in dead))


def new_section(folder, log, title, description=None, review_file=None, today=None) -> int:
    """Opens section N+1 at the end of the log; review_file is repository-relative (docs/reviews/<file>.md)."""
    n = (log.sections[-1].n if log.sections else 0) + 1
    block = [f'## {n}. {_free(title, "title")} ({_today(today)})', '']
    if description is not None:
        block.append(_free(description, 'description'))
    if review_file is not None:
        path = _clean(review_file, 'review file')
        prefix = log.root + '/'
        if not path.startswith(prefix) or not folder.is_file(path[len(prefix):]):
            raise RefError(f'no such file: {path} (a review file is repository-relative, {prefix}…)')
        block.append(f'Review file (open): {path}')
    _append(folder, log, block)
    return n


def _next_id(log: Log) -> str:
    s = log.open_section
    if s is None:
        raise RefError('the log has no section; run new-section first')
    return f'{s.n}.{max((e.number for e in s.entries), default=0) + 1}'


def add_decision(folder, log, title, context, decision, affected=(), supersedes=(), source=None, answers=None, today=None, automated=False) -> str:
    """Appends a recorded decision to the open section and returns its id."""
    if type(automated) is not bool:
        raise RefError('automated must be a boolean')
    if automated:
        for a in supersedes or ():
            if LOG_SECTION_ID_RE.match(a.strip()):
                raise RefError(f'automated decisions cannot supersede a log section; obtain a human decision: {a}')
            why = _automated_supersedable(log, a.strip()) if RULING_ID_RE.match(a.strip()) else None
            if why:
                raise RefError(f'automated decisions supersede only automated rulings: {a.strip()} {why}')
    title, context, decision = _free(title, 'title'), _free(context, 'context'), _free(decision, 'decision')
    _check_text_links(folder, log, context, 'context')
    _check_text_links(folder, log, decision, 'decision')
    fields = {
        'Context': context,
        'Decision': decision,
        'Automated': 'true' if automated else 'false',
        'Affected': _links(folder, log, affected),
        'Supersedes': _supersedes_links(folder, log, supersedes),
        'Source': _source_link(folder, log, source) if source is not None else '',
        'Status': f'recorded {_today(today)}',
    }
    answers = _clean(answers, 'answers') if answers is not None else None
    entry_id = _next_id(log)
    _append(folder, log, render_entry(entry_id, title, fields, answers))
    return entry_id


def add_note(folder, log, title, text) -> str:
    """Appends a note to the open section and returns its id."""
    title, text = _free(title, 'title'), _free(text, 'text')
    _check_text_links(folder, log, text, 'text')
    entry_id = _next_id(log)
    _append(folder, log, [f'### {entry_id} {title}', '', text, '**Status.** note'])
    return entry_id


def _the_entry(log: Log, entry_id: str) -> Entry:
    found = [e for s in log.sections for e in s.entries if e.id == entry_id]
    if not found:
        raise RefError(f'no such entry: {entry_id}')
    if len(found) > 1:
        raise RefError(f'{entry_id} is in the log more than once')
    return found[0]


def apply_decision(folder, log, entry_id, affected=None, no_change=False, today=None) -> None:
    """Marks a recorded decision applied: its Affected field becomes the set given (none with no_change) and its
    Status gains the applied date; every other line stays as written."""
    e = _the_entry(log, entry_id)
    if e.kind() != 'decision' or e.status() != 'recorded':
        raise RefError(f'{entry_id} is {e.status() if e.kind() != "malformed" else "malformed"}; only a recorded decision can be applied')
    if bool(affected) == bool(no_change):
        raise RefError('pass the affected set or --no-change, not both' if affected else 'no affected set given; pass the real set, or --no-change')
    links = _links(folder, log, affected)
    status = f'recorded {e.date()} · applied {_today(today)}' + (', nothing to change' if no_change else '')
    lines = []
    for line in e.lines:
        m = FIELD_RE.match(line)
        label = m.group(1) if m else None
        if label == 'Affected':
            continue
        if links and label is not None and FIELDS.index(label) > FIELDS.index('Affected'):
            lines.append(f'**Affected.** {links}')
            links = ''
        lines.append(f'**Status.** {status}' if label == 'Status' else line)
    _write(folder, log, log.lines[:e.line - 1] + lines + log.lines[e.end:])


def set_provenance(folder, log, entry_id, automated, head_text) -> None:
    """Corrects the Automated field of a decision not yet committed; a committed entry's provenance never changes.
    An entry turned automated must supersede only automated rulings."""
    if type(automated) is not bool:
        raise RefError('automated must be a boolean')
    e = _the_entry(log, entry_id)
    if e.kind() != 'decision' or e.status() != 'recorded':
        raise RefError(f'{entry_id} is {e.status()}; only a recorded decision has provenance to correct')
    if head_text is not None and entry_id in parse_log(head_text).entries:
        raise RefError(f'{entry_id} is committed; its provenance never changes')
    value = 'true' if automated else 'false'
    if e.fields.get('Automated') == value:
        raise RefError(f'{entry_id} is already Automated: {value}')
    if automated:
        by_target = {_entry_target(o): o for o in log.entries.values()}
        for t in e.targets('Supersedes'):
            o = by_target.get(t)
            why = _automated_supersedable(log, o.id, e.line) if o is not None else 'is a log section'
            if why:
                raise RefError(f'automated decisions supersede only automated rulings: {o.id if o else t.heading} {why}')
    lines = [f'**Automated.** {value}' if (m := FIELD_RE.match(line)) and m.group(1) == 'Automated' else line
             for line in e.lines]
    _write(folder, log, log.lines[:e.line - 1] + lines + log.lines[e.end:])


def close_section(folder, log, n, iterations, today=None) -> None:
    """Closes or recloses a review section: `Review file (open):` becomes `Review file:`, `Iterations:` is written,
    and the heading's dates read `(<first>, refined <today>)`."""
    found = [s for s in log.sections if s.n == n]
    if len(found) != 1:
        raise RefError(f'no section {n}' if not found else f'section {n} is in the log more than once')
    s = found[0]
    if int(iterations) < 0:
        raise RefError(f'iterations must not be negative: {iterations}')
    first = DATE_RE.search(s.dates)
    if first is None:
        raise RefError(f'section {n} has no date in its heading')
    today = _today(today)
    lines = list(log.lines)
    lines[s.line - 1] = f'## {s.n}. {s.title} ({first.group(0) if today == first.group(0) else f"{first.group(0)}, refined {today}"})'
    later = [x.line for x in log.sections if x.line > s.line]
    end = s.entries[0].line - 1 if s.entries else (later[0] - 1 if later else len(lines))
    header = range(s.line, end)  # 0-based indices of the lines after the heading, up to the first entry
    review = [i for i in header if lines[i].startswith(('Review file (open): ', 'Review file: '))]
    if not review:
        raise RefError(f'section {n} has no Review file line')
    r = review[0]
    lines[r] = 'Review file: ' + lines[r].split(': ', 1)[1]
    counts = [i for i in header if lines[i].startswith('Iterations: ')]
    if counts:
        lines[counts[0]] = f'Iterations: {int(iterations)}'
    else:
        lines.insert(r + 1, f'Iterations: {int(iterations)}')
    _write(folder, log, lines)


def head_log_text(docs: Path) -> str | None:
    """The committed log (HEAD, the log named by `settings`) when the folder is inside a git repository with a commit
    holding it, else None."""
    docs, log_file, _ = settings(docs)
    r = subprocess.run(['git', '-C', str(docs), 'rev-parse', '--show-prefix'], capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        return None
    r = subprocess.run(['git', '-C', str(docs), 'show', f'HEAD:{r.stdout.strip()}{log_file}'], capture_output=True, text=True, encoding='utf-8')
    return r.stdout if r.returncode == 0 else None


def entry_body(docs: Path, entry_id: str) -> str:
    """The entry's link-free text without its heading line: the body of a commit message."""
    e = _the_entry(load(docs)[1], entry_id)
    return unlink('\n'.join(e.lines[1:])).strip('\n')


def cli() -> int:
    """The console entry point: main with SIGPIPE at its default, so `design-decisions history … | head -3` ends quietly."""
    if hasattr(signal, 'SIGPIPE'):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    return main()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='design-decisions', description=__doc__.split('\n')[0])
    parser.add_argument('--docs', default=None, help='the docs folder, for a dry run on a copy (default: the root of tools/corpus.yaml)')
    sub = parser.add_subparsers(dest='command', required=True)

    def today_option(p):
        p.add_argument('--today', help=argparse.SUPPRESS)

    p = sub.add_parser('show', help='entries by id, in full')
    p.add_argument('ids', nargs='+')
    p = sub.add_parser('list', help='every entry, one line each')
    p.add_argument('--section', type=int)
    p = sub.add_parser('search', help='entries matching every given filter')
    p.add_argument('--automated', choices=['true', 'false', 'unspecified'], help='decision provenance; unspecified matches legacy entries without the field')
    for opt in ['--affected', '--source', '--supersedes', '--status', '--since', '--text']:
        p.add_argument(opt)
    p.add_argument('--section', type=int)
    form = p.add_mutually_exclusive_group()
    form.add_argument('--oneline', action='store_true')
    form.add_argument('--ids', action='store_true')
    p = sub.add_parser('history', help='the entries whose Affected or Supersedes links hit a target, with their later leads')
    p.add_argument('ref')
    sub.add_parser('check', help='the log parses, ids are unique and ordered, fields and links are sound, committed entries unchanged')
    p = sub.add_parser('new-section', help='open section N+1')
    p.add_argument('--title', required=True)
    p.add_argument('--description')
    p.add_argument('--review-file')
    today_option(p)
    p = sub.add_parser('add-decision', help='append a recorded decision to the open section; prints its id')
    p.add_argument('--title', required=True)
    p.add_argument('--context', required=True)
    p.add_argument('--decision', required=True)
    p.add_argument('--automated', action='store_true', help='record an owner-accepted proposed ruling; may supersede only automated rulings')
    p.add_argument('--affected', action='extend', nargs='+', default=[], metavar='LINK')
    p.add_argument('--supersedes', action='extend', nargs='+', default=[], metavar='ID')
    p.add_argument('--source', metavar='LINK')
    p.add_argument('--answers')
    today_option(p)
    p = sub.add_parser('add-note', help='append a note to the open section; prints its id')
    p.add_argument('--title', required=True)
    p.add_argument('--text', required=True)
    p = sub.add_parser('apply-decision', help='mark a recorded decision applied, with the real affected set')
    p.add_argument('--id', required=True)
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument('--affected', action='extend', nargs='+', metavar='LINK')
    which.add_argument('--no-change', action='store_true')
    today_option(p)
    p = sub.add_parser('close-section', help='turn a section\'s Review file (open) line into the contract line and write Iterations')
    p.add_argument('--section', type=int, required=True)
    p.add_argument('--iterations', type=int, required=True)
    today_option(p)
    p = sub.add_parser('set-provenance', help='correct the Automated field of a decision not yet committed')
    p.add_argument('id')
    p.add_argument('--automated', choices=['true', 'false'], required=True)
    p = sub.add_parser('body', help='an entry\'s link-free text without its heading, for a commit message')
    p.add_argument('id')
    args = parser.parse_args(argv)

    try:
        docs = settings(args.docs)[0]
        if args.command == 'body':
            print(entry_body(docs, args.id))
            return 0
        folder, log = load(docs)
        if args.command == 'show':
            for i in args.ids:
                print(_the_entry(log, i).text())
                print()
        elif args.command == 'list':
            for e in log.entries.values():
                if args.section is None or e.section == args.section:
                    print(format_oneline(e))
        elif args.command == 'search':
            hits = search(folder, log, affected=args.affected, source=args.source, supersedes=args.supersedes, status=args.status,
                          section=args.section, since=args.since, text=args.text, automated=args.automated)
            for e in hits:
                print(e.id if args.ids else format_oneline(e) if args.oneline else e.text() + '\n')
        elif args.command == 'history':
            print(format_history(folder, log, args.ref))
        elif args.command == 'check':
            problems = check(folder, log, head_log_text(docs))
            for line in problems:
                print(line)
            print(f'{len(problems)} problems' if problems else 'OK')
            return 1 if problems else 0
        elif args.command == 'new-section':
            print(new_section(folder, log, args.title, args.description, args.review_file, args.today))
        elif args.command == 'add-decision':
            print(add_decision(folder, log, args.title, args.context, args.decision, args.affected, args.supersedes,
                               args.source, args.answers, args.today, automated=args.automated))
        elif args.command == 'add-note':
            print(add_note(folder, log, args.title, args.text))
        elif args.command == 'apply-decision':
            apply_decision(folder, log, args.id, args.affected, args.no_change, args.today)
            print(args.id)
        elif args.command == 'set-provenance':
            set_provenance(folder, log, args.id, args.automated == 'true', head_log_text(docs))
            print(args.id)
        elif args.command == 'close-section':
            close_section(folder, log, args.section, args.iterations, args.today)
    except (RefError, re.error) as e:
        print(f'error: {e}', file=sys.stderr)
        return 1
    except (RuntimeError, OSError, ValueError, yaml.YAMLError) as e:  # the tool could not run: no repository, no file
        print(f'error: {e}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(cli())
