import pytest

from design.folder import *


def test_mask_keeps_length_and_newlines():
    t = "a `x` b\n```\ncode\n```\n<!-- c\nd -->e"
    m = mask(t)
    assert len(m) == len(t) and m.count('\n') == t.count('\n') and m.endswith('e') and 'code' not in m and 'x' not in m

def test_headings_keep_raw_text_and_skip_fences():
    t = "# A\n```\n# not\n```\n## W16 — A `x` phone\n"
    assert [(h.line, h.level, h.text) for h in headings_of(t)] == [(1, 1, 'A'), (5, 2, 'W16 — A `x` phone')]

def test_anchor_encoding_and_decoding():
    assert encode_anchor('2.4 The cache (`~/.omc2/`)') == '2.4%20The%20cache%20(%60~/.omc2/%60)'
    assert decode_percent('bad%zz%C3%20end') == 'bad%zz%C3 end'
    assert decode_percent('phon%65') == 'phone'

def test_scan_links_parentheses_titles_pins_images():
    t = 'see [a](x.md#Receive%20(QR):%20ok "git:0123456789ab") ![i](p.png) [[wiki]] [e](<a b.md>)'
    ls = scan_links(mask(t))
    assert [(l.dest, l.title, l.pin, l.image, l.angle) for l in ls] == [
        ('x.md#Receive%20(QR):%20ok', 'git:0123456789ab', '0123456789ab', False, False),
        ('p.png', None, None, True, False), ('a b.md', None, None, False, True)]
    assert t[ls[0].text_start:ls[0].text_end] == 'a'

def test_unlink_keeps_images_and_code():
    t = '[a](x.md "git:0123456789ab") ![i](p.png) `[c](d)`'
    assert unlink(t) == 'a ![i](p.png) `[c](d)`'

def test_resolve_and_link_to():
    assert resolve('reviews/r.md', '../design/01-x.md#1.1%20A') == ('design/01-x.md', '1.1%20A')
    assert resolve('decision-log.md', '#1.1%20A') == ('decision-log.md', '1.1%20A')
    assert escapes(resolve('design/a.md', '../../out.md')[0])
    assert link_to('reviews/r.md', Target('design/01-x.md', '1.1 A')) == '../design/01-x.md#1.1%20A'
    assert link_to('decision-log.md', Target('decision-log.md', '1.1 A')) == '#1.1%20A'

def test_glob_to_regex():
    assert glob_to_regex('design/**/*.md').match('design/a/b.md') and glob_to_regex('design/**/*.md').match('design/b.md')
    assert not glob_to_regex('design/*.md').match('design/a/b.md')
    assert glob_to_regex('reviews/**').match('reviews/iterations/x.md')
    assert glob_to_regex('{a,b}/*.md').match('b/c.md')

def test_folder_git_lists_tracked_and_untracked_existing_files(repo):
    (repo / 'docs' / 'a.md').write_text('# A\n')
    (repo / 'docs' / 'b.md').write_text('# B\n')
    from design.tests.conftest import commit_all
    commit_all(repo, 'a')
    (repo / 'docs' / 'b.md').unlink()
    (repo / 'docs' / 'c.md').write_text('# C\n')
    f = Folder.git(repo / 'docs')
    assert f.files == ['a.md', 'c.md'] and f.markdown == ['a.md', 'c.md']
    assert f.has_heading('a.md', 'A') and not f.has_heading('a.md', 'B')

def test_corpus_load_and_matching(repo):
    c = Corpus.load(repo)
    assert c.is_history('reviews/x.md') and c.is_corpus('design/01-a.md') and c.is_excluded('superpowers/specs/s.md')
    assert not c.is_generated('design/01-a.md')


# unlink: every non-image link becomes its text

def test_unlink_a_link_becomes_its_text():
    assert unlink('See [W16](../notes/people.md#W16%20—%20A%20replacement%20phone) now.') == 'See W16 now.'

def test_unlink_a_same_file_link():
    assert unlink('[9.18](#9.18%20Device%20kill%20is%20an%20emergency%20act)') == '9.18'

def test_unlink_balanced_parentheses_stay_inside_the_destination():
    assert unlink('[x](a.md#Receive%20Money%20(QR):%20confirm) y') == 'x y'

def test_unlink_a_pinned_link_drops_its_title():
    assert unlink('See [S10](notes/lead.md#S10%20—%20Review%20a%20request "git:0f1211d1a2b3") now.') == 'See S10 now.'

def test_unlink_images_stay():
    assert unlink('![shot](../shots/en/a.png)') == '![shot](../shots/en/a.png)'

def test_unlink_links_in_code_stay():
    s = '`[a](b.md)` and\n```\n[c](d.md)\n```\n'
    assert unlink(s) == s

def test_unlink_text_without_links_is_unchanged():
    s = '### W16 — A replacement phone\n\n**Sees.** Everything (W2, 14.26).\n'
    assert unlink(s) == s

def test_unlink_keeps_backticks_of_the_link_text():
    assert unlink('[`x` y](a.md#%60x%60%20y)') == '`x` y'

def test_unlink_a_title_runs_to_the_first_paren():
    assert unlink('[a](b.md "unclosed) c') == 'a c'  # the title runs to the first ')'
    assert unlink('[a](b.md "x"\n) c') == '[a](b.md "x"\n) c'


# mask

def test_mask_blanks_every_fenced_line_and_comments_across_lines():
    s = 'a `code` b\n```\nx\n```\n<!-- c\nd -->e'
    m = mask(s)
    assert len(m) == len(s) and m.count('\n') == s.count('\n')
    assert 'code' not in m and 'x' not in m and 'c\nd' not in m and m.endswith('e')

def test_mask_a_double_backtick_span_holds_single_backticks():
    s = 'a ``W2 `W16` x`` b'
    assert mask(s) == 'a' + ' ' * (len(s) - 3) + ' b'

def test_mask_an_unclosed_backtick_run_is_literal():
    assert mask('a ` b') == 'a ` b'

def test_mask_a_code_span_may_cross_a_newline():
    assert mask('a `b\nc` d') == 'a   \n   d'

def test_mask_a_backtick_in_a_destination_opens_no_span():
    s = '[a](x.md#`y`) and `z`'
    m = mask(s)
    assert m.startswith('[a](x.md#`y`)') and 'z' not in m

def test_mask_fence_closes_only_on_its_own_kind_and_length():
    s = '````\n```\n# a\n~~~~\n````\n# b\n'
    assert [h.text for h in headings_of(s)] == ['b']
    assert mask(s) == '    \n   \n   \n    \n    \n# b\n'

def test_mask_an_unclosed_fence_runs_to_the_end():
    s = '~~~\n# a\n[x](y)'
    assert mask(s) == '   \n   \n      '
    assert headings_of(s) == []


# headings, anchors, slugs

def test_headings_closing_hashes_stay_and_empty_or_indented_ones_are_none():
    t = '# A #\n#\n    # code\n   ### B\n#C\n'
    assert [(h.line, h.level, h.text) for h in headings_of(t)] == [(1, 1, 'A #'), (4, 3, 'B')]

def test_anchor_encoding_keeps_everything_but_space_and_backtick_raw():
    assert encode_anchor('6. Where tasks come from, in 00 §4.3 and 03 §3') == \
        '6.%20Where%20tasks%20come%20from,%20in%2000%20§4.3%20and%2003%20§3'
    assert encode_anchor('9.17 `lookback` applies') == '9.17%20%60lookback%60%20applies'

def test_decode_percent_multibyte_and_invalid():
    assert decode_percent('W3%20%E2%80%94%20x') == 'W3 — x'
    assert decode_percent('%C3%A9') == 'é'
    assert decode_percent('%C3') == '%C3'
    assert decode_percent('%FF%41') == '%FFA'
    assert decode_percent('%E2%80') == '%E2%80'
    assert decode_percent('%C3%28') == '%C3('
    assert decode_percent('raw — ok') == 'raw — ok'

def test_github_slug_keeps_accented_letters():
    assert github_slug('1.1.3 Un teléfono de reemplazo') == '113-un-teléfono-de-reemplazo'
    assert github_slug('W16 — A') == 'w16--a'


# links

def test_scan_links_title_forms():
    t = 'see [S10](notes/lead.md#S10%20—%20Review%20(a)%20request "git:0f1211d1a2b3") and [x](y.md \'t\') end'
    ls = scan_links(mask(t))
    assert [(t[l.text_start:l.text_end], l.dest, l.title, l.pin) for l in ls] == [
        ('S10', 'notes/lead.md#S10%20—%20Review%20(a)%20request', 'git:0f1211d1a2b3', '0f1211d1a2b3'),
        ('x', 'y.md', 't', None)]
    assert t[ls[0].start:ls[0].end] == t[4:t.index(' and')]

def test_scan_links_offsets_of_an_image_include_the_bang():
    t = 'a ![i](p.png) b'
    (l,) = scan_links(t)
    assert (l.start, l.end, l.image) == (2, 13, True)

def test_scan_links_skips_escapes_wikilinks_and_unfinished_ones():
    assert scan_links(r'\[a](b) [[c]] [d] [e](f') == []
    assert [l.dest for l in scan_links('[x]()')] == ['']
    assert [l.dest for l in scan_links('[a [b] c](d.md)')] == ['d.md']
    assert scan_links('[a\n](b)') == []

def test_scan_links_angle_form_with_title():
    (l,) = scan_links('[e](<a b.md> "t")')
    assert (l.dest, l.angle, l.title) == ('a b.md', True, 't')
    assert scan_links('[e](<a\nb.md>)') == []

def test_pin_needs_the_whole_title():
    assert Link(0, 0, 0, 0, 'x', title='git:0123456').pin == '0123456'
    assert Link(0, 0, 0, 0, 'x', title='git:012345').pin is None
    assert Link(0, 0, 0, 0, 'x', title='see git:0123456').pin is None
    assert Link(0, 0, 0, 0, 'x').pin is None

def test_path_and_fragment():
    assert Link(0, 0, 0, 0, 'a.md#b#c').path_and_fragment == ('a.md', 'b#c')
    assert Link(0, 0, 0, 0, 'a.md').path_and_fragment == ('a.md', None)
    assert Link(0, 0, 0, 0, '#x').path_and_fragment == ('', 'x')


# resolve, link_to, escapes

def test_no_link_leaves_the_folder():
    for dest in ['../x.md', '../x.md#x', 'reviews/../../x.md#x', '..']:
        assert escapes(resolve('a.md', dest)[0]), dest
    assert not escapes(resolve('a/b.md', '../x.md')[0])
    assert not escapes('..x.md')

def test_resolve_decodes_the_path_and_keeps_the_fragment_raw():
    assert resolve('a/b.md', 'c%20d.md') == ('a/c d.md', None)
    assert resolve('a/b.md', 'c.md#') == ('a/c.md', '')
    assert resolve('a/b.md', '') == ('a/b.md', None)

def test_link_to_relative_and_same_file():
    assert link_to('a/b.md', Target('a/b.md', None)) == 'b.md'
    assert link_to('a/b.md', Target('c.md', None)) == '../c.md'
    assert link_to('a/b.md', Target('a/b.md', 'x `y`')) == '#x%20%60y%60'
    assert link_to('r.md', Target('design/x.md', 'H')) == 'design/x.md#H'


# glob, corpus, folder

def test_glob_to_regex_anchored_classes_and_question_mark():
    assert not glob_to_regex('*.md').match('a.md.bak')
    assert not glob_to_regex('*.md').match('x/a.md')
    assert glob_to_regex('a?.md').match('ab.md') and not glob_to_regex('a?.md').match('a/.md')
    assert glob_to_regex('[ab].md').match('b.md') and not glob_to_regex('[ab].md').match('c.md')
    assert glob_to_regex('**/x.md').match('x.md') and glob_to_regex('**/x.md').match('a/b/x.md')
    assert glob_to_regex('a.md').match('a.md') and not glob_to_regex('a.md').match('aXmd')

def test_corpus_overrides(repo):
    from design.tests.conftest import corpus_yaml
    corpus_yaml(repo, generated=['product/**'])
    c = Corpus.load(repo)
    assert (c.root, c.log) == ('docs', 'decision-log.md')
    assert c.is_generated('product/en/a.md') and not c.is_history('design/a.md')
    assert c.matches(['x/*.md', 'y/**'], 'y/z/w.md')

def test_folder_dir_text_slugs_and_paths(tmp_path):
    (tmp_path / 'sub').mkdir()
    (tmp_path / 'sub' / 'a.md').write_bytes(b'# Two\r\n## Two\r\n## T\xc3\xa9 x\r\n')
    (tmp_path / 'p.png').write_bytes(b'')
    f = Folder.dir(tmp_path)
    assert f.files == ['p.png', 'sub/a.md'] and f.markdown == ['sub/a.md']
    assert f.text('sub/a.md') == '# Two\n## Two\n## Té x\n'
    assert f.slugs('sub/a.md') == {'two': 'Two', 'two-1': 'Two', 'té-x': 'Té x'}
    assert f.is_file('p.png') and not f.is_file('sub') and f.is_dir('sub') and not f.is_dir('p.png')
    assert f.root == tmp_path.resolve()

def test_folder_git_fails_outside_a_repository(tmp_path):
    with pytest.raises(RuntimeError, match='git ls-files in'):
        Folder.git(tmp_path)

def test_repo_root(repo):
    (repo / 'docs' / 'deep').mkdir()
    assert repo_root(repo / 'docs' / 'deep') == repo
    (repo / 'docs' / 'deep' / '.git').write_text('gitdir: elsewhere\n')
    assert repo_root(repo / 'docs' / 'deep') == repo / 'docs' / 'deep'
