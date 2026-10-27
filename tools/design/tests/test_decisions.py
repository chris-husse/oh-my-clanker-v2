# tools/design/tests/test_decisions.py
import pytest

from design.decisions import *
from design.folder import Target
from design.log import parse_log
from design.tests.conftest import commit_all, git
from design.tests.test_log import LOG

X = '# 02 X\n\n## 2.1 Title\n\nText.\n\n## 2.2 Other\n\nText.\n'
REVIEW = '# Review\n\n## R1. A\n\nOne.\n\n## R2. B\n\nTwo.\n'


def write_docs(docs, log=LOG, **extra):
    files = {'design/02-x.md': X, 'reviews/2026-10-16-first.md': REVIEW, 'decision-log.md': log, **extra}
    for rel, text in files.items():
        p = docs / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')


@pytest.fixture
def docs(repo):
    d = repo / 'docs'
    write_docs(d)
    commit_all(repo, 'docs')
    return d


def log_text(docs):
    return (docs / 'decision-log.md').read_text(encoding='utf-8')


def kinds(problems):
    return sorted(p.split(': ')[2] for p in problems)


# The brief's tests, verbatim.

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


# Ported from the source's surviving tests.

def test_target_of_a_destination(repo, docs):
    folder, log = load(docs)
    assert resolve_link_arg(folder, log, 'design/02-x.md#2.1 Title') == (Target('design/02-x.md', '2.1 Title'), '[2.1](design/02-x.md#2.1%20Title)')
    assert resolve_link_arg(folder, log, 'design/02-x.md#2.1%20Title')[0] == Target('design/02-x.md', '2.1 Title')
    assert resolve_link_arg(folder, log, 'design/02-x.md') == (Target('design/02-x.md', None), '[02-x](design/02-x.md)')
    assert resolve_link_arg(folder, log, 'reviews/2026-10-16-first.md#R1. A') == (
        Target('reviews/2026-10-16-first.md', 'R1. A'), '[R1. A](reviews/2026-10-16-first.md#R1.%20A)')
    assert resolve_link_arg(folder, log, '1.1') == (Target('decision-log.md', '1.1 First ruling'), '[1.1](#1.1%20First%20ruling)')
    assert resolve_link_arg(folder, log, 'decision-log.md#1.2 Second') == (Target('decision-log.md', '1.2 Second'), '[1.2](#1.2%20Second)')
    for bad in ['design/02-x.md#2.9 Nope', 'design/missing.md', 'design', '9.9', '§9', '1.3', '']:
        with pytest.raises(RefError):
            resolve_link_arg(folder, log, bad)

def test_no_link_leaves_the_folder(repo, docs):
    (repo / 'x.md').write_text('# x\n')  # a real file with a real heading, one level above the folder
    folder, log = load(docs)
    for ref in ['../x.md#x', 'reviews/../../x.md#x', str(repo / 'x.md') + '#x']:
        with pytest.raises(RefError, match='leaves the docs folder'):
            resolve_link_arg(folder, log, ref)

def test_kind_status_date(repo, docs):
    log = load(docs)[1]
    assert format_oneline(log.entries['1.1']) == '1.1  recorded 2026-10-27 · applied 2026-10-27  First ruling'
    assert format_oneline(log.entries['1.3']) == '1.3  note  Parked'

def test_oneline(repo, docs):
    assert format_oneline(load(docs)[1].entries['1.2']) == '1.2  recorded 2026-10-27  Second'

def test_search_by_field(repo, docs):
    folder, log = load(docs)
    ids = lambda **kw: [e.id for e in search(folder, log, **kw)]  # noqa: E731
    assert ids(affected='design/02-x.md#2.1 Title') == ['1.1']
    assert ids(affected='design/02-x.md#2.2 Other') == []
    assert ids(affected='design/') == ['1.1']
    assert ids(source='reviews/2026-10-16-first.md#R1. A') == ['1.1']
    assert ids(source='reviews/2026-10-16-first.md#R2. B') == []
    assert ids(supersedes='1.1') == ['1.2']
    assert ids(status='applied') == ['1.1'] and ids(status='note') == ['1.3']
    assert ids(section=1) == ['1.1', '1.2', '1.3'] and ids(section=2) == []
    assert ids(since='2026-10-27') == ['1.1', '1.2', '1.3'] and ids(since='2026-10-28') == []
    assert ids(text='Do it') == ['1.1'] and ids(text='^note text') == ['1.3']
    assert ids(text='Because of 2.1\\.') == ['1.1']  # the link-free text
    assert ids(affected='design/02-x.md', status='recorded') == []

def test_search_rejects_an_unknown_reference(repo, docs):
    folder, log = load(docs)
    for kw in [dict(affected='design/nope'), dict(affected='design/02-x.md#2.9 Nope'), dict(source='nowhere/'), dict(supersedes='9.9')]:
        with pytest.raises(RefError):
            search(folder, log, **kw)

def test_search_and_history_read_the_fields(repo, docs):
    # a link in the Context names a target, but only Affected and Supersedes count
    folder, log = load(docs)
    apply_decision(folder, log, '1.2', affected=['design/02-x.md#2.2 Other'], today='2026-10-28')
    folder, log = load(docs)
    assert [e.id for e in search(folder, log, affected='design/02-x.md#2.2 Other')] == ['1.2']
    assert [(e.id, later) for e, later in history(folder, log, 'design/02-x.md')] == [('1.1', ['1.2']), ('1.2', [])]
    assert [(e.id, later) for e, later in history(folder, log, 'design/02-x.md#2.2 Other')] == [('1.2', [])]

CHAIN = LOG + """### 1.4 Third

**Context.** c
**Decision.** d
**Supersedes.** [1.2](#1.2%20Second)
**Status.** recorded 2026-10-27
"""

def test_history_annotates_direct_superseders_only(repo):
    write_docs(repo / 'docs', log=CHAIN)
    folder, log = load(repo / 'docs')
    assert [(e.id, later) for e, later in history(folder, log, 'design/02-x.md#2.1 Title')] == [('1.1', ['1.2'])]
    assert later_chain(log, log.entries['1.1']) == ['1.2', '1.4']
    out = format_history(folder, log, 'design/02-x.md#2.1 Title')
    assert out.index('### 1.1 First') < out.index('later: 1.2') < out.index('### 1.2 Second') < out.index('later: 1.4') < out.index('### 1.4 Third')
    assert 'later: 1.2, 1.4' not in out and '### 1.3' not in out

def test_a_section_of_the_log_is_a_supersedes_target(repo, docs):
    folder, log = load(docs)
    assert resolve_link_arg(folder, log, '§1') == (Target('decision-log.md', '1. Review: first (2026-10-27)'), '[§1](#1.%20Review:%20first%20(2026-10-27))')
    assert [e.id for e in search(folder, log, supersedes='§1')] == ['1.2']
    assert [(e.id, later) for e, later in history(folder, log, '§1')] == [('1.2', [])]
    assert [(e.id, later) for e, later in history(folder, log, '1.1')] == [('1.1', ['1.2']), ('1.2', [])]
    assert check(folder, log, None) == []

def test_check_is_green_on_the_fixture(repo, docs):
    assert check(*load(docs), None) == []

def test_check_reports(repo, docs):
    bad = LOG.replace('**Status.** recorded 2026-10-27\n', '**Status.** recorded yesterday\n')
    bad = bad.replace('### 1.3 Parked', '### 1.1 Parked')
    bad = bad.replace('**Context.** c\n', '**Context.** c, [2.1](design/02-x.md#2.1%20Gone)\n')
    bad = bad.replace('**Affected.** [2.1](design/02-x.md#2.1%20Title)', '**Affected.** [2.1](design/02-x.md#2.1%20Gone)')  # applied: not ours
    folder, _ = load(docs)
    problems = check(folder, parse_log(bad.replace('recorded yesterday', 'recorded 2026-10-27')), None)
    assert kinds(problems) == ['dead-link', 'duplicate-id']
    line = bad.split('\n').index('**Context.** c, [2.1](design/02-x.md#2.1%20Gone)') + 1
    assert f'PROBLEM: decision-log.md:{line}: dead-link: 1.2: [2.1](design/02-x.md#2.1%20Gone) (no such heading in design/02-x.md: 2.1 Gone)' in problems
    problems = check(folder, parse_log(bad), None)
    assert kinds(problems) == ['duplicate-id', 'malformed-status']  # a malformed status is not recorded
    assert all(p.startswith('PROBLEM: decision-log.md:') for p in problems)

def test_check_reports_every_other_kind(repo, docs):
    folder, _ = load(docs)
    one = lambda text: kinds(check(folder, parse_log(text), None))  # noqa: E731
    assert one(LOG.replace('### 1.3 Parked', '### 1.0 Parked')) == ['out-of-order']
    assert one(LOG.replace('### 1.3 Parked', '### 2.3 Parked')) == ['wrong-section']
    assert one(LOG.replace('**Decision.** d\n', '')) == ['malformed-entry']
    assert one(LOG.replace('**Decision.** d\n', '**Decision.** d\n**Affected files.** x\n')) == ['malformed-entry']
    assert one(LOG.replace('note text\n', 'note text\n**Context.** c\n')) == ['malformed-entry']
    assert one(LOG.replace('**Status.** note\n', '')) == ['malformed-status']
    assert one(LOG.replace('2026-10-16-first.md\n', '2026-10-16-gone.md\n')) == ['unresolved-section']
    assert one(LOG.replace('Review file (open): docs/reviews/2026-10-16-first.md', 'Review file: docs/reviews/2026-10-16-gone.md')) == []
    assert one(LOG.replace('**Context.** c\n', '**Context.** c, see [x](design/02-x.md#nope)\n')) == ['dead-link']
    assert one(LOG.replace('**Context.** c\n', '**Context.** c, see [x](design/02-x.md#nope "git:0123abcd")\n')) == []  # pinned
    assert one(LOG.replace('**Context.** c\n', '**Context.** c, see [x](https://example.com/a#b)\n')) == []  # external
    removed = LOG[:LOG.index('### 1.3 Parked')]
    assert kinds(check(folder, parse_log(removed), LOG)) == ['removed']
    edited_note = LOG.replace('note text', 'other text')
    assert kinds(check(folder, parse_log(edited_note), LOG)) == ['edited']
    edited_recorded = LOG.replace('**Context.** c\n', '**Context.** changed\n')
    assert kinds(check(folder, parse_log(edited_recorded), LOG)) == []  # recorded in HEAD may change

def test_check_immutability_ignores_a_link_rewrite(repo, docs):
    folder, log = load(docs)
    relinked = LOG.replace('[2.1](design/02-x.md#2.1%20Title)', '[2.1](design/02-x.md#2.2%20Other)')
    assert kinds(check(folder, parse_log(relinked), LOG)) == []  # same link-free text, links resolve

def test_show_search_history_check(repo, docs, capsys):
    run = lambda *a: (main(['--docs', str(docs), *a]), capsys.readouterr())  # noqa: E731
    code, out = run('show', '1.1')
    assert code == 0 and out.out.startswith('### 1.1 First ruling\n')
    code, out = run('search', '--affected', 'design/02-x.md', '--ids')
    assert code == 0 and out.out.split() == ['1.1']
    code, out = run('search', '--status', 'recorded', '--oneline')
    assert out.out == '1.2  recorded 2026-10-27  Second\n'
    code, out = run('list')
    assert out.out.splitlines()[2] == '1.3  note  Parked'
    code, out = run('list', '--section', '2')
    assert out.out == ''
    code, out = run('history', 'design/02-x.md#2.1 Title')
    assert code == 0 and '### 1.1 First ruling' in out.out and 'later: 1.2' in out.out
    code, out = run('check')
    assert (code, out.out) == (0, 'OK\n')
    code, out = run('search', '--affected', 'nope.md')
    assert code == 1 and 'nope.md' in out.err
    code, out = run('show', '9.9')
    assert code == 1 and 'no such entry: 9.9' in out.err

def test_new_section(repo, docs):
    n = new_section(*load(docs), 'Review: second', 'Two sentences.', 'docs/reviews/2026-10-16-first.md', today='2026-10-28')
    assert n == 2
    log = load(docs)[1]
    s = log.sections[-1]
    assert (s.n, s.title, s.dates, s.review_file, s.review_open) == (2, 'Review: second', '2026-10-28', 'docs/reviews/2026-10-16-first.md', True)
    assert log_text(docs).endswith('\n\n## 2. Review: second (2026-10-28)\n\nTwo sentences.\nReview file (open): docs/reviews/2026-10-16-first.md\n')
    before = log_text(docs)
    for bad in [dict(title=''), dict(title='T', review_file='docs/reviews/nope.md'), dict(title='T', review_file='reviews/2026-10-16-first.md'),
                dict(title='a\nb'), dict(title='T', description='a\nb'), dict(title='T', today='yesterday')]:
        with pytest.raises(RefError):
            new_section(*load(docs), **bad)
    assert log_text(docs) == before

def test_add_decision(repo, docs):
    folder, log = load(docs)
    eid = add_decision(folder, log, 'Receipts', 'See [2.1](design/02-x.md#2.1%20Title).', 'A photo.',
                       affected=['design/02-x.md#2.1 Title', 'design/02-x.md'], supersedes=['1.2', '§1'],
                       source='reviews/2026-10-16-first.md#R2. B', answers='R2', today='2026-10-28')
    assert eid == '1.4'
    e = load(docs)[1].entries['1.4']
    assert e.lines == [
        '### 1.4 Receipts', '',
        '**Context.** See [2.1](design/02-x.md#2.1%20Title).',
        '**Decision.** A photo.',
        '**Affected.** [2.1](design/02-x.md#2.1%20Title), [02-x](design/02-x.md)',
        '**Supersedes.** [1.2](#1.2%20Second), [§1](#1.%20Review:%20first%20(2026-10-27))',
        '**Source.** [R2. B](reviews/2026-10-16-first.md#R2.%20B)',
        '**Status.** recorded 2026-10-28',
        'Answers: R2',
    ]
    assert log_text(docs).endswith('Answers: R2\n')
    assert check(*load(docs), head_log_text(docs)) == []

def test_add_decision_without_optional_fields(repo, docs):
    add_decision(*load(docs), 'Plain', 'Why.', 'What.', today='2026-10-28')
    assert load(docs)[1].entries['1.4'].lines == ['### 1.4 Plain', '', '**Context.** Why.', '**Decision.** What.', '**Status.** recorded 2026-10-28']

def test_add_decision_refuses_and_leaves_the_log_untouched(repo, docs):
    before = log_text(docs)
    for kw in [dict(title='', context='c', decision='d'), dict(title='t', context=' ', decision='d'), dict(title='t', context='c', decision=''),
               dict(title='t', context='c', decision='d', affected=['design/nope.md']), dict(title='t', context='c', decision='d', supersedes=['9.1']),
               dict(title='t', context='c', decision='d', supersedes=['design/02-x.md#2.1 Title']),
               dict(title='t', context='c', decision='d', source='reviews/2026-10-16-first.md#Nope'),
               dict(title='t', context='c', decision='d', source='reviews/2026-10-16-first.md'),  # a source names a heading
               dict(title='t', context='see [x](design/02-x.md#2.9%20Nope)', decision='d'),  # a dead link in the text
               dict(title='t', context='c', decision='d', today='2026-13-01')]:
        with pytest.raises(RefError):
            add_decision(*load(docs), **kw)
    assert log_text(docs) == before

def test_add_decision_refuses_a_newline_naming_the_field(repo, docs):
    before = log_text(docs)
    for kw, name in [(dict(title='a\nb'), 'title'), (dict(context='a\nb'), 'context'), (dict(decision='a\r\nb'), 'decision'), (dict(answers='R1\nR2'), 'answers')]:
        args = dict(title='t', context='c', decision='d') | kw
        with pytest.raises(RefError, match=name):
            add_decision(*load(docs), **args)
    with pytest.raises(RefError, match='text'):
        add_note(*load(docs), 'T', 'a\nb')
    assert log_text(docs) == before

def test_add_decision_refuses_without_a_section(repo):
    write_docs(repo / 'docs', log='# Decision Log\n')
    with pytest.raises(RefError):
        add_decision(*load(repo / 'docs'), 't', 'c', 'd')
    assert log_text(repo / 'docs') == '# Decision Log\n'

def test_add_note(repo, docs):
    assert add_note(*load(docs), 'Declared minor', 'The review closed with nothing open.') == '1.4'
    e = load(docs)[1].entries['1.4']
    assert (e.kind(), e.lines) == ('note', ['### 1.4 Declared minor', '', 'The review closed with nothing open.', '**Status.** note'])

def test_cli_add_decision_prints_the_id(repo, docs, capsys):
    assert main(['--docs', str(docs), 'add-decision', '--title', 'T', '--context', 'C', '--decision', 'D',
                 '--affected', 'design/02-x.md#2.1 Title', '--affected', 'design/02-x.md#2.2 Other', '--supersedes', '1.2',
                 '--source', 'reviews/2026-10-16-first.md#R2. B', '--answers', 'R2', '--today', '2026-10-29']) == 0
    assert capsys.readouterr().out.strip() == '1.4'
    e = load(docs)[1].entries['1.4']
    assert e.affected() == [Target('design/02-x.md', '2.1 Title'), Target('design/02-x.md', '2.2 Other')]
    assert e.fields['Status'] == 'recorded 2026-10-29' and e.supersedes() == ['1.2']
    before = log_text(docs)
    assert main(['--docs', str(docs), 'add-decision', '--title', 'T', '--context', 'C', '--decision', 'D', '--affected', 'design/nope.md']) == 1
    assert 'design/nope.md' in capsys.readouterr().err and log_text(docs) == before

def test_apply_keeps_everything_else_in_place(repo, docs):
    apply_decision(*load(docs), '1.2', affected=['design/02-x.md#2.1 Title', 'design/02-x.md#2.2 Other'], today='2026-10-28')
    log = load(docs)[1]
    assert log.entries['1.2'].lines == [
        '### 1.2 Second', '', '**Context.** c', '**Decision.** d',
        '**Affected.** [2.1](design/02-x.md#2.1%20Title), [2.2](design/02-x.md#2.2%20Other)',
        '**Supersedes.** [1.1](#1.1%20First%20ruling), [§1](#1.%20Review:%20first%20(2026-10-27))',
        '**Status.** recorded 2026-10-27 · applied 2026-10-28']
    old = LOG.split('\n')
    e = parse_log(LOG).entries['1.2']
    assert log_text(docs).split('\n') == old[:e.line - 1] + log.entries['1.2'].lines + old[e.end:-1]  # one final newline

def test_apply_replaces_a_recorded_affected_set(repo, docs):
    add_decision(*load(docs), 'T', 'c', 'd', affected=['design/02-x.md#2.2 Other'], today='2026-10-27')
    apply_decision(*load(docs), '1.4', affected=['design/02-x.md'], today='2026-10-28')
    e = load(docs)[1].entries['1.4']
    assert e.fields['Affected'] == '[02-x](design/02-x.md)' and e.lines.count('**Affected.** [02-x](design/02-x.md)') == 1

def test_apply_with_nothing_to_change(repo, docs):
    add_decision(*load(docs), 'T', 'c', 'd', affected=['design/02-x.md#2.2 Other'], today='2026-10-27')
    apply_decision(*load(docs), '1.4', no_change=True, today='2026-10-28')
    e = load(docs)[1].entries['1.4']
    assert e.fields['Status'] == 'recorded 2026-10-27 · applied 2026-10-28, nothing to change' and 'Affected' not in e.fields

def test_apply_refuses(repo, docs):
    before = log_text(docs)
    for args, kw in [(('1.2',), {}), (('1.2',), dict(affected=['design/02-x.md'], no_change=True)), (('9.9',), dict(no_change=True)),
                     (('1.2',), dict(affected=['design/nope.md'])), (('1.2',), dict(no_change=True, today='soon'))]:
        with pytest.raises(RefError):
            apply_decision(*load(docs), *args, **kw)
    assert log_text(docs) == before
    apply_decision(*load(docs), '1.2', no_change=True)
    with pytest.raises(RefError):
        apply_decision(*load(docs), '1.2', affected=['design/02-x.md'])  # already applied

def test_close_section(repo, docs):
    close_section(*load(docs), 1, 2, today='2026-10-27')
    s = load(docs)[1].sections[0]
    assert (s.dates, s.review_file, s.review_open, s.iterations) == ('2026-10-27', 'docs/reviews/2026-10-16-first.md', False, 2)
    close_section(*load(docs), 1, 3, today='2026-10-29')  # closing again keeps the line, counts and refines
    text = log_text(docs)
    assert 'Review file: docs/reviews/2026-10-16-first.md\nIterations: 3\n' in text and '## 1. Review: first (2026-10-27, refined 2026-10-29)' in text
    assert text.count('Iterations:') == 1 and 'Review file (open):' not in text
    close_section(*load(docs), 1, 3, today='2026-10-30')
    assert '## 1. Review: first (2026-10-27, refined 2026-10-30)' in log_text(docs)
    n = new_section(*load(docs), 'Plain', today='2026-10-30')
    before = log_text(docs)
    for args in [(n, 1), (9, 1), (1, -1)]:
        with pytest.raises(RefError):
            close_section(*load(docs), *args)  # no Review file line; no such section; a negative count
    assert log_text(docs) == before

def test_check_uses_head(repo, docs, capsys):
    assert main(['--docs', str(docs), 'check']) == 0 and capsys.readouterr().out == 'OK\n'
    p = docs / 'decision-log.md'
    p.write_text(p.read_text().replace('**Decision.** Do it.', '**Decision.** Do not.'))
    assert main(['--docs', str(docs), 'check']) == 1
    out = capsys.readouterr().out
    assert ': edited: 1.1' in out and out.endswith('\n1 problems\n')

@pytest.mark.parametrize('status, dead', [('recorded 2026-10-27 · applied 2026-10-27', False), ('recorded 2026-10-27', True)])
def test_check_leaves_aged_links_of_committed_applied_entries_to_links_check(repo, status, dead, capsys):
    docs = repo / 'docs'
    text = LOG.replace('**Status.** recorded 2026-10-27 · applied 2026-10-27', f'**Status.** {status}')
    write_docs(docs, log=text)
    commit_all(repo, 'docs')
    (docs / 'design/02-x.md').write_text(X.replace('## 2.1 Title', '## 2.1 Renamed'))  # 1.1's links aged
    code = main(['--docs', str(docs), 'check'])
    out = capsys.readouterr().out
    if not dead:
        assert (code, out) == (0, 'OK\n')
    else:
        line = text.split('\n').index('**Affected.** [2.1](design/02-x.md#2.1%20Title)') + 1
        assert code == 1 and f'PROBLEM: decision-log.md:{line}: dead-link: 1.1: [2.1](design/02-x.md#2.1%20Title) (no such heading' in out

def test_check_leaves_the_committed_log_byte_identical(repo, docs):
    before = (docs / 'decision-log.md').read_bytes()
    assert main(['--docs', str(docs), 'check']) == 0
    assert (docs / 'decision-log.md').read_bytes() == before
    assert git(repo, 'status', '--porcelain') == ''


# Added beyond the brief and the source.

def test_check_and_head_outside_git(tmp_path):
    docs = tmp_path / 'docs'
    write_docs(docs)
    assert head_log_text(docs) is None
    assert check(*load(docs), head_log_text(docs)) == []

def test_entry_body_and_cli_body(repo, docs, capsys):
    assert entry_body(docs, '1.1') == ('**Context.** Because of 2.1.\n**Decision.** Do it.\n**Affected.** 2.1\n**Source.** R1. A\n'
                                       '**Status.** recorded 2026-10-27 · applied 2026-10-27\nAnswers: R1')
    with pytest.raises(RefError):
        entry_body(docs, '9.9')
    assert main(['--docs', str(docs), 'body', '1.3']) == 0
    assert capsys.readouterr().out == 'note text\n**Status.** note\n'

def test_cli_writing_commands_take_today(repo, docs, capsys):
    d = ['--docs', str(docs)]
    assert main([*d, 'apply-decision', '--id', '1.2', '--affected', 'design/02-x.md#2.2 Other', '--today', '2026-10-28']) == 0
    assert main([*d, 'close-section', '--section', '1', '--iterations', '1', '--today', '2026-10-29']) == 0
    assert main([*d, 'new-section', '--title', 'Next', '--today', '2026-10-30']) == 0
    assert main([*d, 'add-note', '--title', 'N', '--text', 'x']) == 0
    assert capsys.readouterr().out.split() == ['1.2', '2', '2.1']
    log = load(docs)[1]
    assert log.entries['1.2'].fields['Status'] == 'recorded 2026-10-27 · applied 2026-10-28'
    assert log.sections[0].dates == '2026-10-27, refined 2026-10-29' and log.sections[1].dates == '2026-10-30'
    assert main([*d, 'apply-decision', '--id', '1.1', '--no-change']) == 1
    assert 'only a recorded decision' in capsys.readouterr().err

def test_a_duplicate_id_is_ambiguous_for_apply(repo):
    write_docs(repo / 'docs', log=LOG.replace('### 1.3 Parked\n\nnote text\n**Status.** note', '### 1.2 Again\n\n**Context.** c\n**Decision.** d\n**Status.** recorded 2026-10-27'))
    folder, log = load(repo / 'docs')
    assert kinds(check(folder, log, None)) == ['duplicate-id']
    with pytest.raises(RefError, match='more than once'):
        apply_decision(folder, log, '1.2', no_change=True)


# Review fixes.

def test_root_and_log_come_from_corpus_yaml(repo, monkeypatch, capsys):
    p = repo / 'tools' / 'corpus.yaml'
    p.write_text(p.read_text().replace('root: docs', 'root: notes').replace('log: decision-log.md', 'log: rulings.md'))
    assert 'root: notes' in p.read_text() and 'log: rulings.md' in p.read_text()
    notes = repo / 'notes'
    write_docs(notes, log=LOG.replace('docs/reviews/', 'notes/reviews/'))
    (notes / 'rulings.md').write_text((notes / 'decision-log.md').read_text())
    (notes / 'decision-log.md').unlink()
    commit_all(repo, 'notes')
    monkeypatch.chdir(repo)
    assert settings() == (repo / 'notes', 'rulings.md', 'notes')
    assert settings(notes) == (notes, 'rulings.md', 'notes')  # --docs replaces the folder only
    folder, log = load(notes)
    assert (log.file, log.root) == ('rulings.md', 'notes')
    assert resolve_link_arg(folder, log, 'rulings.md#1.1 First ruling') == (Target('rulings.md', '1.1 First ruling'), '[1.1](#1.1%20First%20ruling)')
    assert head_log_text(notes) == (notes / 'rulings.md').read_text()
    assert main(['check']) == 0 and capsys.readouterr().out == 'OK\n'
    assert main(['add-decision', '--title', 'T', '--context', 'c', '--decision', 'd', '--supersedes', '1.2']) == 0
    assert capsys.readouterr().out.strip() == '1.4' and '### 1.4 T' in (notes / 'rulings.md').read_text()
    assert main(['new-section', '--title', 'R', '--review-file', 'docs/reviews/2026-10-16-first.md']) == 1
    assert 'notes/' in capsys.readouterr().err
    assert main(['new-section', '--title', 'R', '--review-file', 'notes/reviews/2026-10-16-first.md']) == 0
    bad = (notes / 'rulings.md').read_text().replace('notes/reviews/2026-10-16-first.md', 'notes/reviews/gone.md', 1)
    assert check(folder, parse_log(bad, 'rulings.md', 'notes'), None) == [
        'PROBLEM: rulings.md:5: unresolved-section: §1 names notes/reviews/gone.md, which does not exist']

def test_settings_outside_a_repository_use_the_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert settings(tmp_path / 'copy') == (tmp_path / 'copy', 'decision-log.md', 'docs')

def test_notes_and_sections_are_never_linked_but_from_supersedes(repo, docs):
    before = log_text(docs)
    for kw in [dict(affected=['decision-log.md#1.3 Parked']), dict(context='see [1.3](#1.3%20Parked)'),
               dict(affected=['§1']), dict(affected=['decision-log.md#1. Review: first (2026-10-27)']),
               dict(context='see [§1](#1.%20Review:%20first%20(2026-10-27))'), dict(source='decision-log.md#1.3 Parked'),
               dict(context='see [log](#Decision%20Log)')]:
        args = dict(title='t', context='c', decision='d') | kw
        with pytest.raises(RefError):
            add_decision(*load(docs), **args)
    with pytest.raises(RefError, match='note'):
        add_note(*load(docs), 'N', 'see [1.3](decision-log.md#1.3%20Parked)')
    assert log_text(docs) == before
    folder, _ = load(docs)
    linked = LOG.replace('**Context.** c\n', '**Context.** c, [1.3](#1.3%20Parked), [§1](#1.%20Review:%20first%20(2026-10-27))\n')
    problems = check(folder, parse_log(linked), None)
    assert kinds(problems) == ['dead-link', 'dead-link']
    assert any('(a note; notes are never linked to)' in p for p in problems) and any('linked only from Supersedes' in p for p in problems)
    assert check(folder, parse_log(LOG), None) == []  # §1 in 1.2's Supersedes stands

@pytest.mark.parametrize('value', ['```', '~~~ x', '# heading', '### 1.9 Entry', '**Status.** note', '**Affected.** x', '**Important.** x', '  **Another label.** y',
                                   'Review file: docs/reviews/x.md', 'Review file (open): x', 'Iterations: 3', 'Answers: R1'])
def test_free_text_cannot_read_as_log_structure(repo, docs, value):
    before = log_text(docs)
    with pytest.raises(RefError):
        add_note(*load(docs), 'N', value)
    with pytest.raises(RefError):
        new_section(*load(docs), 'S', description=value)
    for field in ('title', 'context', 'decision'):
        with pytest.raises(RefError, match=field):
            add_decision(*load(docs), **(dict(title='t', context='c', decision='d') | {field: value}))
    assert log_text(docs) == before

def test_aged_links_of_applied_entries_are_not_dead_without_head(repo, docs):
    (docs / 'design/02-x.md').write_text(X.replace('## 2.1 Title', '## 2.1 Renamed'))
    assert check(*load(docs), None) == []  # 1.1 is applied; its aged links are the link checker's

def test_main_leaves_sigpipe_alone_and_cli_is_the_entry_point(repo, docs):
    import signal, tomllib, pathlib
    before = signal.getsignal(signal.SIGPIPE)
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    try:
        assert main(['--docs', str(docs), 'list']) == 0
        assert signal.getsignal(signal.SIGPIPE) == signal.SIG_IGN
    finally:
        signal.signal(signal.SIGPIPE, before)
    data = tomllib.loads((pathlib.Path(__file__).parents[2] / 'pyproject.toml').read_text())
    assert data['project']['scripts']['design-decisions'] == 'design.decisions:cli'


def test_a_run_outside_a_repository_is_an_error_without_a_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('GIT_CEILING_DIRECTORIES', str(tmp_path.parent))
    assert main(['list']) == 2
    err = capsys.readouterr().err
    assert err.startswith('error: ') and 'Traceback' not in err
