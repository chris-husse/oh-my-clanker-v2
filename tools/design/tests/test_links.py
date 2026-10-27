# tools/design/tests/test_links.py
from design.folder import Corpus, Folder, Target, decode_percent, unlink
from design.links import Problem, check_folder, log_entry_status, main, mentions_in, ruling_index
from design.tests.conftest import corpus_yaml
from design.tests.test_log import LOG

X = '# 02 X\n\n## 2.1 Title\n\nText.\n'
REVIEW = '# Review\n\n## R1. A\n\nOne.\n'
FIELDS = '**Context.** c\n**Decision.** d\n**Status.** recorded 2026-10-27 · applied 2026-10-27\n'
BIG_LOG = (LOG.rstrip('\n') + '\n\n### 1.4 Three digits\n\n' + FIELDS
           + '\n## 14. Big (2026-10-27)\n\n### 14.104 Big one\n\n' + FIELDS)
TO_LOG = '../decision-log.md#'


def folder_with(repo, extra: dict[str, str]):
    docs = repo / 'docs'
    files = {'decision-log.md': BIG_LOG, 'design/02-x.md': X, 'reviews/2026-10-16-first.md': REVIEW,
             'images/a.png': 'png', 'design/page.md': '# Page\n\n![a](../images/a.png)\n', **extra}
    for rel, text in files.items():
        p = docs / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    return Folder.dir(docs), Corpus.load(repo)


def problems_of(repo, extra):
    return check_folder(*folder_with(repo, extra))


def kinds_of(repo, extra):
    return [f"{'W' if p.warning else 'P'} {p.kind} {p.file}:{p.line}" for p in problems_of(repo, extra)]


def test_base_clean(repo):
    assert kinds_of(repo, {}) == []


def test_escape(repo):
    (repo / 'outside.md').write_text('# Out\n')
    assert kinds_of(repo, {'a.md': '# A\n\n[outside](../outside.md)\n'}) == ['P escape docs/a.md:3']


def test_dead_file_and_a_folder(repo):
    assert kinds_of(repo, {'a.md': '# A\n\n[x](nothere.md) [design](design/)\n'}) == [
        'P dead-file docs/a.md:3', 'P dead-file docs/a.md:3']


def test_dead_heading(repo):
    assert kinds_of(repo, {'a.md': '# A\n\n[2.9](design/02-x.md#2.9%20No%20such)\n'}) == ['P dead-heading docs/a.md:3']


def test_form_seven_ways(repo):
    extra = {
        'design/d.md': '# D\n\n## 2.5 A — B\n\nText.\n',
        'a.md': '# A\n\n[[02-x#2.1 Title]]\n\n[2.1][w]\n\n[w]: design/02-x.md\n\n'
                '[2.1](<design/02-x.md#2.1 Title>)\n\n[2.1](design/02-x.md#21-title)\n\n'
                '[2.5](design/d.md#2.5%20A%20%E2%80%94%20B)\n\n[02 X](/design/02-x.md)\n\n'
                '[file](file:///tmp/a.md)\n\n[ok](https://example.com) [ok](mailto:a@b.c)\n',
    }
    assert kinds_of(repo, extra) == [f'P form docs/a.md:{n}' for n in (3, 5, 7, 9, 11, 13, 15, 17)]


def test_unlinked_certain_after_decision_log(repo):
    assert kinds_of(repo, {'design/x.md': '# X\n\nAs decision log 1.1 says, and ruling 1.2, and rulings 1.3 and 1.4.\n'}) == [
        'P unlinked docs/design/x.md:3'] * 4


def test_parenthesis_grouping_certain_bare_warning(repo):
    assert kinds_of(repo, {'design/x.md': '# X\n\nBoth (1.1, §1.4).\n\nThen 1.1 again.\n'}) == [
        'P unlinked docs/design/x.md:3', 'P unlinked docs/design/x.md:3', 'W unlinked? docs/design/x.md:5']


def test_plain_stays_plain(repo):
    text = ('# X about 1.1\n\n## 1.4 Own heading\n\n`1.1` and\n\n```\n1.1 1.2\n```\n\n<!-- ruling 1.1 -->\n\n'
            f'[see 1.1]({TO_LOG}1.1%20First%20ruling) https://example.com/1.1 version 1.14.4 and 1.4.\n')
    assert kinds_of(repo, {'design/x.md': text}) == []


def test_wrong_target(repo):
    text = ('# Y\n\n[2.2](02-x.md#2.1%20Title)\n\n[Other](02-x.md#2.1%20Title)\n\n[the Title](02-x.md#2.1%20Title)\n\n'
            '[02 §2.1](02-x.md#2.1%20Title)\n\n[the 02 X document](02-x.md)\n\n[02-x](02-x.md)\n\n[elsewhere](02-x.md)\n\n'
            '[03](02-x.md)\n')
    problems = problems_of(repo, {'design/y.md': text})
    assert [f'{p.kind} {p.file}:{p.line}' for p in problems] == [
        'wrong-target docs/design/y.md:3', 'wrong-target docs/design/y.md:5', 'wrong-target docs/design/y.md:7',
        'wrong-target docs/design/y.md:15', 'wrong-target docs/design/y.md:17']
    assert problems[0].detail.startswith('"2.2" links to 02-x.md#2.1%20Title')


def test_review_link_exempt(repo):
    assert kinds_of(repo, {'a.md': '# A\n\n[2.6](reviews/2026-10-16-first.md#R1.%20A)\n'}) == []


def test_answers_lines_skipped_in_the_log_not_elsewhere(repo):
    log = BIG_LOG.replace('Answers: R1\n', 'Answers: R1, decision log 1.2\n\nSee decision log 1.2 in prose.\n')
    assert kinds_of(repo, {'decision-log.md': log, 'design/x.md': '# X\n\nAnswers: decision log 1.2\n'}) == [
        'P unlinked docs/decision-log.md:19', 'P unlinked docs/design/x.md:3']


def test_stray_and_unembedded_image(repo):
    problems = problems_of(repo, {'state.json': '{}', 'images/unused.png': 'png'})
    assert [str(p) for p in problems] == [
        'PROBLEM: docs/images/unused.png:0: stray: an image no page embeds',
        'PROBLEM: docs/state.json:0: stray: not Markdown; it does not belong in docs/']


def test_three_digit_rulings_keyed_grouped_bare(repo):
    assert kinds_of(repo, {'design/x.md': '# X\n\nRulings 14.104 and (1.1, 14.104).\n\n14.104 again.\n'}) == [
        'P unlinked docs/design/x.md:3'] * 3 + ['W unlinked? docs/design/x.md:5']


def test_section_sign_rulings_keyed_grouped_bare(repo):
    folder, corpus = folder_with(repo, {'design/x.md': '# X\n\nSee decision-log §1.4.\n\nBoth (§1.1, 1.2).\n\nAnd §14.104 alone.\n'})
    assert [f"{'W' if p.warning else 'P'} {p.kind} {p.file}:{p.line}" for p in check_folder(folder, corpus)] == [
        'P unlinked docs/design/x.md:3', 'P unlinked docs/design/x.md:5', 'P unlinked docs/design/x.md:5',
        'W unlinked? docs/design/x.md:7']
    rulings = ruling_index(folder, corpus)
    assert rulings['14.104'] == Target('decision-log.md', '14.104 Big one')
    text = folder.text('design/x.md')
    ms = mentions_in(folder, corpus, 'design/x.md', rulings)
    assert [(text[o:o + len(t)], t, target.heading, certain) for o, t, target, certain in ms][0] == (
        '1.4', '1.4', '1.4 Three digits', True)


def test_backtick_heading_encoded_clean_raw_is_form(repo):
    b = '# B\n\n## 3.2 `flag` applies\n\nText.\n'
    clean = '# A\n\n[3.2](design/b.md#3.2%20%60flag%60%20applies) and `code`.\n'
    folder, corpus = folder_with(repo, {'design/b.md': b, 'a.md': clean})
    assert check_folder(folder, corpus) == []
    assert unlink(folder.text('a.md')) == '# A\n\n3.2 and `code`.\n'
    problems = problems_of(repo, {'design/b.md': b, 'a.md': '# A\n\n[3.2](design/b.md#3.2%20`flag`%20applies) and `code`.\n'})
    assert [f'{p.kind} {p.file}:{p.line}' for p in problems] == ['form docs/a.md:3']
    assert 'write #3.2%20%60flag%60%20applies' in problems[0].detail


def test_decoding(repo):
    assert decode_percent('bad%zz%C3%20end') == 'bad%zz%C3 end'
    assert kinds_of(repo, {'a.md': '# A\n\n[2.1](design/02-x.md#2.1%20Titl%65)\n'}) == ['P form docs/a.md:3']


def test_unapplied_target(repo):
    text = (f'# X\n\nruling [1.1]({TO_LOG}1.1%20First%20ruling) ok, ruling [1.2]({TO_LOG}1.2%20Second) no, '
            f'ruling [1.3]({TO_LOG}1.3%20Parked) no, [the decision log](../decision-log.md) ok, '
            f'[§1]({TO_LOG}1.%20Review:%20first%20(2026-10-27)) no, [the Decision Log]({TO_LOG}Decision%20Log) no.\n')
    folder, corpus = folder_with(repo, {'design/x.md': text})
    assert [f'{p.kind} {p.file}:{p.line}' for p in check_folder(folder, corpus)] == ['unapplied-target docs/design/x.md:3'] * 4
    assert log_entry_status(folder, corpus)['1.2 Second'] == ('1.2', 'recorded')


def test_same_file_section_link_inside_the_log_fine(repo):
    assert '[§1](#1.%20Review:%20first%20(2026-10-27))' in BIG_LOG
    log = BIG_LOG + '\nSee [§14](#14.%20Big%20(2026-10-27)).\n'
    assert kinds_of(repo, {'decision-log.md': log}) == []


def test_dead_link_in_a_generated_file_is_a_warning(repo):
    corpus_yaml(repo, generated=['product/**'])
    problems = problems_of(repo, {'product/p.md': '# P\n\n[2.9](../design/02-x.md#2.9%20Gone)\n',
                                  'design/z.md': '# Z\n\n[2.9](02-x.md#2.9%20Gone)\n'})
    assert [f"{'W' if p.warning else 'P'} {p.kind} {p.file}:{p.line}" for p in problems] == [
        'P dead-heading docs/design/z.md:3', 'W dead-heading docs/product/p.md:3']
    assert problems[1].detail.endswith(' (generated)')


def test_main_prints_ok_and_problems(repo, capsys):
    folder_with(repo, {})
    assert main([str(repo / 'docs')]) == 0
    assert capsys.readouterr().out == 'OK\n'
    (repo / 'docs' / 'a.md').write_text('# A\n\n[x](nothere.md)\n')
    (repo / 'docs' / 'b.md').write_text('# B\n\nThen 1.1 again.\n')
    assert main([str(repo / 'docs')]) == 1
    assert capsys.readouterr().out == (
        'PROBLEM: docs/a.md:3: dead-file: no such file: nothere.md\n'
        'WARNING: docs/b.md:3: unlinked?: 1.1: link it to decision-log.md#1.1%20First%20ruling\n'
        '1 problems\n')



def test_main_refuses_a_root_that_is_not_a_directory(repo, capsys):
    folder_with(repo, {})
    for root in (repo / 'docs' / 'nothere', repo / 'docs' / 'design' / '02-x.md'):
        assert main([str(root)]) == 2
        out = capsys.readouterr()
        assert (out.out, out.err) == ('', f'links-check: {root} is not a directory\n')


def test_main_help_prints_usage(capsys):
    assert main(['--help']) == 0
    assert capsys.readouterr().out.startswith('usage: links-check [root]')


def test_main_reports_a_bad_corpus_glob_and_exits_2(repo, capsys):
    folder_with(repo, {})
    corpus_yaml(repo, corpus=['design/{a,b.md'])
    assert main([str(repo / 'docs')]) == 2
    assert capsys.readouterr().err.startswith("links-check: tools/corpus.yaml: bad glob 'design/{a,b.md'")


# Added beyond the brief.

def test_problem_format_and_order():
    ps = sorted([Problem(True, 'b', 1, 'unlinked?', 'w'), Problem(False, 'b', 2, 'form', 'f'), Problem(False, 'a', 9, 'stray', 's')])
    assert [str(p) for p in ps] == ['PROBLEM: a:9: stray: s', 'PROBLEM: b:2: form: f', 'WARNING: b:1: unlinked?: w']


def test_round_trip_wrapping_every_mention_leaves_only_other_problems(repo):
    folder, corpus = folder_with(repo, {'design/x.md': '# X\n\nDecision log 1.1 and §14.104. Both (1.2, 1.4). Then 1.3. [dead](nothere.md)\n'})
    before = [str(p) for p in check_folder(folder, corpus) if not p.kind.startswith('unlinked')]
    rulings = ruling_index(folder, corpus)
    from design.folder import link_to
    for rel in folder.markdown:
        text = folder.text(rel)
        for o, t, target, _ in reversed(mentions_in(folder, corpus, rel, rulings)):
            text = f'{text[:o]}[{t}]({link_to(rel, target)}){text[o + len(t):]}'
        (folder.root / rel).write_text(text, encoding='utf-8')
    assert before == ['PROBLEM: docs/design/x.md:3: dead-file: no such file: nothere.md']
    after = check_folder(Folder.dir(folder.root), corpus)
    assert [str(p) for p in after if p.kind != 'unapplied-target'] == before
    assert sorted(p.detail.split(' ')[0] for p in after if p.kind == 'unapplied-target') == ['1.2', '1.3']


def test_excluded_files_are_skipped_entirely(repo):
    extra = {'superpowers/plan.md': '# P\n\n[x](nothere.md) [[wiki]] and decision log 1.1.\n',
             'superpowers/data.json': '{}', 'superpowers/b.png': 'png'}
    assert kinds_of(repo, extra) == []


def test_wrong_target_id_token_only_against_a_heading_id_and_bounded(repo):
    extra = {'design/setup.md': '# Setup\n\nText.\n', 'design/notes.md': '# Notes\n\n## Setup\n\nText.\n',
             'design/y.md': '# Y\n\n[Python 3.12 setup](setup.md)\n\n[Python 3.12 setup](notes.md#Setup)\n\n'
                            '[Python3 notes](notes.md)\n\n[2.2](02-x.md#2.1%20Title)\n\n[the v2.1 Title](02-x.md#2.1%20Title)\n\n'
                            '[Title r2](02-x.md#2.1%20Title)\n'}
    problems = problems_of(repo, extra)
    assert [f'{p.kind} {p.file}:{p.line}' for p in problems] == [
        'wrong-target docs/design/y.md:9', 'wrong-target docs/design/y.md:13']
    assert problems[0].detail.endswith('; its id is 2.1')
    assert problems[1].detail.endswith('; the text does not name "2.1 Title"')


def test_letter_led_heading_ids_and_a_sentence_ending_period(repo):
    oq = '# Open questions\n\n## H. Cross-repo features\n\nText.\n\n## L4. Locks\n\nText.\n\n## MVP\n\nText.\n'
    links = ['[open-questions §H](open-questions.md#H.%20Cross-repo%20features)', '[H](open-questions.md#H.%20Cross-repo%20features)',
             '[§L4](open-questions.md#L4.%20Locks)', '[the locks](open-questions.md#L4.%20Locks)', '[open-questions §H](open-questions.md)',
             '[decision 2.1.](02-x.md#2.1%20Title)', '[Cross-repo features](open-questions.md#H.%20Cross-repo%20features)',
             '[open-questions §L4](open-questions.md#H.%20Cross-repo%20features)', '[§B](open-questions.md#L4.%20Locks)',
             '[decision 2.2.](02-x.md#2.1%20Title)', '[A Title note](02-x.md#2.1%20Title)']
    problems = problems_of(repo, {'design/open-questions.md': oq, 'design/y.md': '# Y\n\n' + '\n\n'.join(links) + '\n'})
    # 9: no token and not the heading's text; 15: a letter-led heading needs its id or its whole text; 23: a capital
    # word is no token against a numbered heading
    assert [(p.kind, p.line) for p in problems] == [('wrong-target', n) for n in (9, 15, 17, 19, 21, 23)]
    assert problems[0].detail.endswith('; the text does not name "L4. Locks"')
    assert problems[2].detail.endswith('; its id is H')
    assert problems[3].detail.endswith('; its id is L4')
    assert problems[4].detail.endswith('; its id is 2.1')
    assert problems[5].detail.endswith('; the text does not name "2.1 Title"')


def test_text_id_tokens():
    from design.links import TEXT_ID_RE, _leading_id
    assert TEXT_ID_RE.findall('v2.1, decision 1.2. and 3.4.5 or 6.x') == ['1.2', '3.4.5']
    assert [_leading_id(h) for h in ('H. Cross-repo', 'B1. Locks', 'L4.', 'MVP', 'OK go', 'H.x', '2.6 Trust')] == [
        'H', 'B1', 'L4', None, None, None, '2.6']
