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


# Added beyond the brief.

def test_a_fenced_entry_heading_is_not_an_entry():
    text = LOG.replace('note text\n', 'note text\n```\n### 1.9 Not an entry\n**Status.** recorded 2026-10-27\n```\n')
    log = parse_log(text)
    assert list(log.entries) == ['1.1', '1.2', '1.3']
    e = log.entries['1.3']
    assert e.lines[-1] == '**Status.** note' and e.status() == 'note' and e.kind() == 'note'
    assert '### 1.9 Not an entry' in e.lines


def test_several_sections():
    text = LOG + """## 2. Review: second (2026-10-27, refined 2026-10-28)

Review file: docs/reviews/2026-10-20-second.md
Iterations: 2

### 2.1 Later

**Context.** c
**Decision.** d
**Status.** recorded 2026-10-28 · applied 2026-10-28, nothing to change

## 3. Plain (2026-10-29)
"""
    log = parse_log(text)
    one, two, three = log.sections
    assert (one.review_open, [e.id for e in one.entries]) == (True, ['1.1', '1.2', '1.3'])
    assert (two.n, two.title, two.dates, two.review_file, two.review_open, two.iterations) == (
        2, 'Review: second', '2026-10-27, refined 2026-10-28', 'docs/reviews/2026-10-20-second.md', False, 2)
    assert [e.id for e in two.entries] == ['2.1'] and two.entries[0].status() == 'applied'
    assert (three.review_file, three.review_open, three.iterations, three.entries) == (None, False, None, [])
    assert log.open_section is three and list(log.entries) == ['1.1', '1.2', '1.3', '2.1']
    assert log.entries['1.3'].lines[-1] == '**Status.** note'
    e = log.entries['2.1']
    assert log.lines[e.line - 1] == '### 2.1 Later' and log.lines[e.line - 1:e.end] == e.lines


def test_no_status_is_malformed_and_a_log_without_sections_has_no_open_section():
    text = LOG.replace('note text\n**Status.** note\n', 'note text\n')
    e = parse_log(text).entries['1.3']
    assert (e.status(), e.kind(), e.date()) == ('malformed', 'malformed', None)
    assert parse_log('\n'.join(header_lines())).open_section is None


def test_write_log_and_helpers(tmp_path):
    p = tmp_path / 'decision-log.md'
    write_log(p, header_lines() + render_entry('1.1', 'T', {'Context': 'c'}))
    assert p.read_text(encoding='utf-8') == '# Decision Log\n\n*Append-only. Every ruling and its reasoning, dated.*\n\n### 1.1 T\n\n**Context.** c\n'
    assert entry_link('1.2', 'A `b` c') == '#1.2%20A%20%60b%60%20c'


def test_a_same_file_affected_link_names_the_log():
    text = LOG.replace('**Affected.** [2.1](design/02-x.md#2.1%20Title)', '**Affected.** [§1](#1.%20Review:%20first%20(2026-10-27))')
    assert parse_log(text).entries['1.1'].affected() == [Target('decision-log.md', '1. Review: first (2026-10-27)')]
