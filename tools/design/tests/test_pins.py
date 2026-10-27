# tools/design/tests/test_pins.py
import subprocess
from types import SimpleNamespace

import pytest

from design.folder import Corpus, Folder, unlink
from design.links import check_folder
from design.pins import GitHistory, PinReport, main, pin_links
from design.tests.conftest import commit_all, git

A_ONE = '# 01 A\n\n## 1.1 Keep\n\nText.\n\n## 1.2 Gone soon\n\nText.\n'
A_TWO = '# 01 A\n\n## 1.1 Keep\n\nText.\n'
KEEP = 'design/01-a.md#1.1%20Keep'
GONE = 'design/01-a.md#1.2%20Gone%20soon'
HEAD = '# Decision Log\n\n## 1. Review: first (2026-10-27)\n\n### 1.1 Keep both\n\n'
TAIL = '**Decision.** d\n**Status.** recorded 2026-10-27 · applied 2026-10-27\n'


def log_with(context: str, more: str = '') -> str:
    return f'{HEAD}**Context.** {context}\n{TAIL}{more}'


LOG = log_with(f'About [1.1]({KEEP}) and [1.2]({GONE}).')  # the links on line 7


def put(repo, rel, text):
    p = repo / 'docs' / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def read(repo, rel):
    return (repo / 'docs' / rel).read_text(encoding='utf-8')


def kinds(repo):
    docs = repo / 'docs'
    return [f"{'W' if p.warning else 'P'} {p.kind} {p.file}:{p.line}"
            for p in check_folder(Folder.git(docs), Corpus.load(repo), GitHistory.of(docs))]


def to_main(repo):
    git(repo, 'checkout', '-q', 'main')
    git(repo, 'merge', '-q', '--ff-only', 'feature')


@pytest.fixture
def hist(repo):
    """main: `one` has 01-a.md with 1.1 Keep and 1.2 Gone soon and the log linking both from an applied entry; `two`
    drops 1.2 Gone soon; the branch `feature` starts at `two`."""
    put(repo, 'design/01-a.md', A_ONE)
    put(repo, 'decision-log.md', LOG)
    one = commit_all(repo, 'one')
    put(repo, 'design/01-a.md', A_TWO)
    two = commit_all(repo, 'two')
    git(repo, 'checkout', '-q', '-b', 'feature')
    return SimpleNamespace(root=repo, one=one, two=two)


# The pinned links of links-check.

def test_unpinned_on_a_main_line_gone_today_or_not_a_review_too(hist):
    put(hist.root, 'reviews/r.md', f'# R\n\n[1.1](../{KEEP})\n')
    commit_all(hist.root, 'review')
    to_main(hist.root)
    assert kinds(hist.root) == ['P unpinned docs/decision-log.md:7', 'P unpinned docs/decision-log.md:7',
                                'P unpinned docs/reviews/r.md:3']
    docs = hist.root / 'docs'
    p = check_folder(Folder.git(docs), Corpus.load(hist.root), GitHistory.of(docs))[0]
    assert p.detail == f'{KEEP}: run just pin-links'


def test_links_check_main_checks_pins(hist, capsys):
    from design import links
    to_main(hist.root)
    assert links.main([str(hist.root / 'docs')]) == 1
    assert capsys.readouterr().out == (f'PROBLEM: docs/decision-log.md:7: unpinned: {KEEP}: run just pin-links\n'
                                       f'PROBLEM: docs/decision-log.md:7: unpinned: {GONE}: run just pin-links\n'
                                       '2 problems\n')


def test_pinned_links_resolve_at_their_commit_though_gone_today(hist):
    p = hist.one[:12]
    put(hist.root, 'decision-log.md', log_with(f'About [1.1]({KEEP} "git:{p}") and [1.2]({GONE} "git:{p}").'))
    put(hist.root, 'reviews/r.md', f'# R\n\n[1.1](../decision-log.md#1.1%20Keep%20both "git:{p}")\n')
    assert kinds(hist.root) == []  # uncommitted
    commit_all(hist.root, 'pin')
    assert kinds(hist.root) == []  # committed on the branch
    to_main(hist.root)
    assert kinds(hist.root) == []  # on main


def test_a_pin_is_a_commit_on_main_where_its_target_existed(hist):
    put(hist.root, 'design/01-a.md', A_TWO + '\n## 1.3 New\n\nText.\n')
    branch = commit_all(hist.root, 'new on the branch')[:12]
    p = hist.two[:12]
    put(hist.root, 'reviews/r.md', '# R\n\n'
        f'[1.3](../design/01-a.md#1.3%20New "git:{branch}")\n\n'
        f'[1.3](../design/01-a.md#1.3%20New "git:{p}")\n\n'
        f'[x](../design/never.md "git:{p}")\n\n'
        f'[1.1](../design/01-a.md#1.1%20Kee%70 "git:{p}")\n\n'
        f'[1.1](../{KEEP} "git:0123456789ab")\n')
    assert kinds(hist.root) == [
        'P unpinned docs/decision-log.md:7', 'P unpinned docs/decision-log.md:7',
        'P pin docs/reviews/r.md:3', 'P dead-pin docs/reviews/r.md:5', 'P dead-pin docs/reviews/r.md:7',
        'P form docs/reviews/r.md:9', 'P pin docs/reviews/r.md:11']
    docs = hist.root / 'docs'
    details = [x.detail for x in check_folder(Folder.git(docs), Corpus.load(hist.root), GitHistory.of(docs))[2:]]
    assert details == [
        f'git:{branch} is not a commit on main: ../design/01-a.md#1.3%20New',
        f'no heading "1.3 New" in design/01-a.md at git:{p}',
        f'no such file at git:{p}: ../design/never.md',
        'anchor not in the written form: #1.1%20Kee%70; write #1.1%20Keep',
        f'git:0123456789ab is not a commit on main: ../{KEEP}']


def test_a_branch_line_resolves_now_same_file_and_external_exempt(hist):
    put(hist.root, 'reviews/r.md', f'# R\n\n[1.1](../{KEEP}) and [1.2](../{GONE})\n')
    expected = ['P unpinned docs/decision-log.md:7', 'P unpinned docs/decision-log.md:7',
                'P dead-heading docs/reviews/r.md:3']
    assert kinds(hist.root) == expected
    commit_all(hist.root, 'branch line')
    assert kinds(hist.root) == expected
    put(hist.root, 'decision-log.md', log_with('See [1.1](#1.1%20Keep%20both) and [x](https://example.com).'))
    put(hist.root, 'reviews/r.md', '# R\n\n[R](#R)\n')
    commit_all(hist.root, 'exempt')
    to_main(hist.root)
    assert kinds(hist.root) == []


# GitHistory.

def test_main_is_origin_main_when_present_else_local_main(hist):
    h = GitHistory.of(hist.root / 'docs')
    assert (h.repo_root, h.prefix) == (hist.root.resolve(), 'docs/')
    assert h.main() == 'refs/heads/main'
    assert h.on_main(hist.two)
    git(hist.root, 'update-ref', 'refs/remotes/origin/main', hist.one)
    o = GitHistory.of(hist.root / 'docs')
    assert o.main() == 'refs/remotes/origin/main'
    assert o.on_main(hist.one[:12])
    assert not o.on_main(hist.two)
    assert not o.on_main(hist.two[:12])


def test_no_main_and_no_repository(tmp_path):
    assert GitHistory.of(tmp_path) is None
    git(tmp_path, 'init', '-q', '-b', 'other')
    assert GitHistory.of(tmp_path).main() is None


def test_commit_of_follows_a_rename(hist):
    git(hist.root, 'mv', 'docs/design/01-a.md', 'docs/design/01-b.md')
    commit_all(hist.root, 'rename')
    h = GitHistory.of(hist.root / 'docs')
    assert h.commit_of('design/01-b.md', 3) == hist.one
    assert h.commit_of('decision-log.md', 7) == hist.one
    assert h.commit_of('decision-log.md', 99) is None
    put(hist.root, 'design/01-b.md', A_TWO + 'More.\n')
    h = GitHistory.of(hist.root / 'docs')
    assert h.commit_of('design/01-b.md', 6) is None  # uncommitted
    assert h.commit_of('reviews/none.md', 1) is None


def test_existed_at(hist):
    h = GitHistory.of(hist.root / 'docs')
    assert h.existed_at(hist.one, 'design/01-a.md')
    assert h.existed_at(hist.one, 'design/01-a.md', '1.2 Gone soon')
    assert not h.existed_at(hist.two, 'design/01-a.md', '1.2 Gone soon')
    assert h.existed_at(hist.two[:12], 'design/01-a.md', '1.1 Keep')
    assert not h.existed_at(hist.one, 'design/never.md')
    assert not h.existed_at('0123456789ab', 'design/01-a.md')


def test_latest_on_main_with(hist):
    h = GitHistory.of(hist.root / 'docs')
    assert h.latest_on_main_with('design/01-a.md', '1.2 Gone soon') == hist.one
    assert h.latest_on_main_with('design/01-a.md', '1.1 Keep') == hist.two
    assert h.latest_on_main_with('design/01-a.md') == hist.two
    assert h.latest_on_main_with('design/never.md') is None
    assert h.latest_on_main_with('design/01-a.md', '9.9 Never') is None


# pin_links.

def pin(repo):
    docs = repo / 'docs'
    return pin_links(Folder.git(docs), Corpus.load(repo), GitHistory.of(docs))


def test_pin_links_pins_main_lines_else_the_newest_with_the_target_lists_the_rest(repo):
    put(repo, 'design/01-a.md', A_ONE)
    put(repo, 'decision-log.md', LOG)
    put(repo, 'reviews/r.md', '# R\n\n[1.1](../decision-log.md#1.1%20Keep%20both), [same](#R) and [web](https://example.com).\n')
    one = commit_all(repo, 'one')[:12]
    put(repo, 'design/01-a.md', A_TWO)
    put(repo, 'decision-log.md', LOG + f'\nLater [1.2]({GONE}) and [x](nothere.md).\n')
    commit_all(repo, 'two')
    git(repo, 'checkout', '-q', '-b', 'feature')
    put(repo, 'decision-log.md', read(repo, 'decision-log.md') + f'\nBranch [1.1]({KEEP}).\n')
    before = {f: read(repo, f) for f in ('decision-log.md', 'reviews/r.md')}

    r = pin(repo)
    assert r == PinReport(4, ['docs/decision-log.md:11: [x](nothere.md)'])
    assert read(repo, 'decision-log.md') == (
        log_with(f'About [1.1]({KEEP} "git:{one}") and [1.2]({GONE} "git:{one}").')
        + f'\nLater [1.2]({GONE} "git:{one}") and [x](nothere.md).\n\nBranch [1.1]({KEEP}).\n')
    assert read(repo, 'reviews/r.md') == (
        f'# R\n\n[1.1](../decision-log.md#1.1%20Keep%20both "git:{one}"), [same](#R) and [web](https://example.com).\n')
    for f, text in before.items():
        assert unlink(read(repo, f)) == unlink(text)  # the link-free text is unchanged
    # left for links-check: the link no commit on main had, now on a line of this branch
    assert kinds(repo) == ['P dead-file docs/decision-log.md:11']
    assert pin(repo).pinned == 0


def test_pin_links_pins_a_branch_line_whose_target_is_gone_to_the_last_main_commit_with_it(repo):
    put(repo, 'design/01-a.md', A_ONE)
    put(repo, 'decision-log.md', '# Decision Log\n')
    one = commit_all(repo, 'one')[:12]
    git(repo, 'checkout', '-q', '-b', 'feature')
    put(repo, 'design/01-a.md', A_ONE.replace('1.1 Keep', '1.1 Kept'))
    put(repo, 'decision-log.md', f'# Decision Log\n\nBranch [1.1]({KEEP}) and [1.2]({GONE}).\n')
    commit_all(repo, 'branch')
    r = pin(repo)
    assert r == PinReport(1, [])
    assert read(repo, 'decision-log.md') == f'# Decision Log\n\nBranch [1.1]({KEEP} "git:{one}") and [1.2]({GONE}).\n'
    assert kinds(repo) == []


def test_pin_links_walks_the_log_and_the_history_files_only(repo):
    put(repo, 'design/01-a.md', A_ONE)
    page = f'# P\n\n[1.1](01-a.md#1.1%20Keep)\n'
    put(repo, 'design/p.md', page)
    put(repo, 'decision-log.md', LOG)
    put(repo, 'superpowers/r.md', f'# S\n\n[1.1](../{KEEP})\n')
    commit_all(repo, 'one')
    corpus_history = Corpus.load(repo)
    assert not corpus_history.is_history('design/p.md')
    assert pin(repo).pinned == 2
    assert read(repo, 'design/p.md') == page
    assert read(repo, 'superpowers/r.md') == f'# S\n\n[1.1](../{KEEP})\n'


def test_pin_links_leaves_a_link_with_another_title_unpinnable(repo):
    put(repo, 'design/01-a.md', A_ONE)
    put(repo, 'decision-log.md', log_with(f'About [1.1]({KEEP} "a title").'))
    commit_all(repo, 'one')
    assert pin(repo) == PinReport(0, [f'docs/decision-log.md:7: [1.1]({KEEP} "a title")'])


# main.

def test_main_pins_and_reports(repo, capsys):
    put(repo, 'design/01-a.md', A_ONE)
    put(repo, 'decision-log.md', LOG)
    commit_all(repo, 'one')
    assert main([str(repo / 'docs')]) == 0
    assert capsys.readouterr().out == 'pinned 2 links\n'
    put(repo, 'decision-log.md', read(repo, 'decision-log.md') + '\nAlso [x](nothere.md).\n')
    commit_all(repo, 'two')
    assert main([str(repo / 'docs')]) == 1
    assert capsys.readouterr().out == ('pinned 0 links\nNOT PINNED: docs/decision-log.md:11: [x](nothere.md)\n'
                                       '1 links not pinned: no commit on main has their target\n')


def test_main_exit_2_without_a_main_branch_or_a_repository(repo, tmp_path, capsys):
    git(repo, 'branch', '-m', 'main', 'other')
    assert main([str(repo / 'docs')]) == 2
    assert capsys.readouterr().err == f'pin-links: {repo / "docs"} is not in a git repository with a main branch\n'
    plain = tmp_path / 'plain'
    plain.mkdir()
    assert main([str(plain)]) == 2
    assert capsys.readouterr().err == f'pin-links: {plain} is not in a git repository with a main branch\n'
