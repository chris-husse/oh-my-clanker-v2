import 'dart:io';

import 'package:docs_links/docs_links.dart';
import 'package:test/test.dart';

/// The source layout: the stories and the design pages protected, the theme files design/T*.md, the reviews the
/// question files.
final _scope = Scope(protected: ['design/**', 'stories/**'], themes: ['design/T*.md'], questions: 'reviews');

late Directory _tmp;

/// A vault under a fresh temporary directory: the base files plus [extra] (path -> content).
Vault _vault(Map<String, String> extra) {
  final root = Directory('${_tmp.path}/docs')..createSync(recursive: true);
  final files = {
    'stories/worker.md': '# User stories — the worker\n\n### W2 — Begin the shift\n\nCount.\n\n'
        '### W16 — A replacement phone\n\nSees everything.\n',
    'design/T01-tenant.md': '# T1 Tenant\n\n### T1.1 Tenant scope\n\nText.\n',
    'screens/definitions/shift.preparing.md': '# shift.preparing — Preparing shift\n\n![s](../shots/en/shift.preparing.png)\n',
    'screens/shots/en/shift.preparing.png': 'png',
    'product/en/1-collector/1.1-getting-the-phone.md': '# 1.1 Getting the phone\n\n## 1.1.3 A replacement phone\n\nText.\n',
    ...extra,
  };
  for (final e in files.entries) {
    File('${root.path}/${e.key}')
      ..parent.createSync(recursive: true)
      ..writeAsStringSync(e.value);
  }
  return Vault.dir(root.path);
}

List<String> _kinds(Vault v) => [for (final p in checkVault(v, _scope)) '${p.kind} ${p.file}:${p.line}'];

const _w16 = '../stories/worker.md#W16%20—%20A%20replacement%20phone';

/// A second stories file, with a backtick heading.
const _other = '# User stories — other\n\n### W5 — `lookback` applies to list calls\n\nText.\n';

void main() {
  setUp(() => _tmp = Directory.systemTemp.createTempSync('links-'));
  tearDown(() => _tmp.deleteSync(recursive: true));

  test('the base vault is clean', () => expect(_kinds(_vault({})), isEmpty));

  test('design/, stories/ and reviews/ are checked; the rest of the vault is not', () {
    const bad = '# X\n\n[W99](../stories/worker.md#W99%20—%20Gone) [x](nothere.md) W16 and 9.18 again.\n';
    expect(
        _kinds(_vault({
          'architecture/x.md': bad,
          'product/en/1-collector/1.2-x.md': bad,
          'superpowers/specs/x.md': bad.replaceAll('../', '../../'),
          'index.md': bad.replaceAll('../', ''),
          'state.json': '{}',
          'screens/shots/en/unused.png': 'png',
        })),
        isEmpty);
    expect(_kinds(_vault({'design/README.md': bad, 'design/T02-x.md': bad, 'stories/x.md': bad, 'reviews/x.md': bad})), [
      for (final f in ['design/README.md', 'design/T02-x.md', 'reviews/x.md', 'stories/x.md'])
        for (final k in ['dead-file', 'dead-heading', 'unlinked']) '$k docs/$f:3',
    ]);
  });

  test('every reference kind, linked, is clean', () {
    expect(
        _kinds(_vault({
          'reviews/x.md': '# X\n\n[W16]($_w16), [T1.1](../design/T01-tenant.md#T1.1%20Tenant%20scope), '
              '[shift.preparing](../screens/definitions/shift.preparing.md), '
              '[docs 1.1.3](../product/en/1-collector/1.1-getting-the-phone.md#1.1.3%20A%20replacement%20phone).\n',
        })),
        isEmpty);
  });

  test('escape: a link leaving docs/', () {
    File('${_tmp.path}/outside.md').writeAsStringSync('# Out\n');
    expect(_kinds(_vault({'design/README.md': '# A\n\n[out](../../outside.md)\n'})), ['escape docs/design/README.md:3']);
  });

  test('dead-file and a folder', () {
    expect(_kinds(_vault({'design/README.md': '# A\n\n[x](nothere.md) [y](../stories/)\n'})),
        ['dead-file docs/design/README.md:3', 'dead-file docs/design/README.md:3']);
  });

  test('dead-heading', () {
    expect(_kinds(_vault({'design/README.md': '# A\n\n[x](../stories/worker.md#No%20such)\n'})), ['dead-heading docs/design/README.md:3']);
  });

  test('form: wikilink, reference style, angle brackets, slug, encoded dash, absolute, file scheme', () {
    expect(
        _kinds(_vault({
          'design/README.md': '# A\n\n[[worker#W16 — A replacement phone]]\n\n[W2][w]\n\n[w]: ../stories/worker.md\n\n'
              '[x](<../stories/worker.md#W16 — A replacement phone>)\n\n[x](../stories/worker.md#w16--a-replacement-phone)\n\n'
              '[x](../stories/worker.md#W16%20%E2%80%94%20A%20replacement%20phone)\n\n[x](/stories/worker.md)\n\n'
              '[x](file:///tmp/a.md)\n\n[ok](https://example.com) [ok](mailto:a@b.c)\n',
        })),
        [for (final l in [3, 5, 7, 9, 11, 13, 15, 17]) 'form docs/design/README.md:$l']);
  });

  test('unlinked: every kind', () {
    expect(_kinds(_vault({'reviews/x.md': '# X\n\nW16 and shift.preparing and docs 1.1.3.\n'})),
        List.filled(3, 'unlinked docs/reviews/x.md:3'));
  });

  test('old ruling numbers, design sections and rule ids are plain text', () {
    expect(
        _kinds(_vault({
          'design/T02-x.md': '# T2\n\n### T2.1 Flags\n\nFrom ruling 9.18 and decision log §13.7 (W2, 9.18), 02 §3, 14.104; see T1.1.\n',
        })),
        ['unlinked docs/design/T02-x.md:5']);
  });

  test('plain stays plain: headings, code, comments, link text, URLs, versions, own heading numbers', () {
    expect(
        _kinds(_vault({
          'reviews/x.md': '# X about W16\n\n## 9.18 Not a ruling here\n\n`W16` and\n\n```\nW16 9.18\n```\n\n'
              '<!-- stories: W16 -->\n\n[see the phone]($_w16) https://example.com/W16 Obsidian 1.14.4.\n',
        })),
        isEmpty);
  });

  test('wrong-target: the text names one reference, the link another', () {
    expect(_kinds(_vault({'design/README.md': '# A\n\n[W16](../stories/worker.md#W2%20—%20Begin%20the%20shift)\n'})),
        ['wrong-target docs/design/README.md:3']);
  });

  test('a link into a review file names its item, not a story: no wrong-target', () {
    expect(
        _kinds(_vault({
          'reviews/2026-10-20-x-y-z.md': '# R\n\n### W2. An item\n\nText.\n',
          'design/README.md': '# A\n\n[W2](../reviews/2026-10-20-x-y-z.md#W2.%20An%20item)\n',
        })),
        isEmpty);
  });

  test('linkTo: relative, and same file', () {
    const t = Target('stories/worker.md', 'W16 — A replacement phone');
    expect(linkTo('reviews/x.md', t), _w16);
    expect(linkTo('stories/worker.md', t), '#W16%20—%20A%20replacement%20phone');
    expect(linkTo('design/README.md', const Target('screens/definitions/shift.preparing.md', null)),
        '../screens/definitions/shift.preparing.md');
  });

  test('a story id defined twice stops the check', () {
    expect(() => checkVault(_vault({'stories/other.md': '# O\n\n### W2 — Again\n'}), _scope), throwsStateError);
  });

  test('a mention: token, offsets and target pinned', () {
    final v = _vault({'reviews/x.md': '# X\n\nW16 and shift.preparing.\n'});
    final text = v.text('reviews/x.md');
    final ms = mentionsIn(v, Index.of(v, _scope), 'reviews/x.md');
    expect([for (final m in ms) (m.token, text.substring(m.start, m.end), m.start, linkTo(m.file, m.target))], [
      ('W16', 'W16', 5, _w16),
      ('shift.preparing', 'shift.preparing', 13, '../screens/definitions/shift.preparing.md'),
    ]);
  });

  test('a backtick heading: linked with each backtick as %60, clean; unlink reads the text', () {
    const dest = '../stories/other.md#W5%20—%20%60lookback%60%20applies%20to%20list%20calls';
    final v = _vault({
      'stories/other.md': _other,
      'design/README.md': '# A\n\n[W5]($dest) and `code` [x](../stories/other.md).\n',
    });
    expect(_kinds(v), isEmpty);
    expect(unlink(v.text('design/README.md')), '# A\n\nW5 and `code` x.\n');
    expect(encodeAnchor('9.17 `lookback` applies'), '9.17%20%60lookback%60%20applies');
    expect(linkTo('design/README.md', Index.of(v, _scope).stories['W5']!), dest);
  });

  test('a raw backtick in an anchor is form, and the detail names the encoded anchor', () {
    final v = _vault({
      'stories/other.md': _other,
      'design/README.md': '# A\n\n[W5](../stories/other.md#W5%20—%20`lookback`%20applies%20to%20list%20calls) and `code`.\n',
    });
    final ps = checkVault(v, _scope);
    expect([for (final p in ps) '${p.kind} ${p.file}:${p.line}'], ['form docs/design/README.md:3']);
    expect(ps.single.detail, contains('write #W5%20—%20%60lookback%60%20applies%20to%20list%20calls'));
    expect(unlink(v.text('design/README.md')), '# A\n\nW5 and `code`.\n');
  });

  test('decoding: each %XX run as UTF-8, raw characters kept', () {
    expect(decodePercent('W16%20—%20A%20phon%65'), 'W16 — A phone');
    expect(decodePercent('a%E2%80%94b ñ%20c'), 'a—b ñ c');
    expect(decodePercent('bad%zz%C3%20end'), 'bad%zz%C3 end');
    expect(_kinds(_vault({'design/README.md': '# A\n\n[x](../stories/worker.md#W16%20—%20A%20replacement%20phon%65)\n'})),
        ['form docs/design/README.md:3']);
  });

  test('a link into the log is checked by its heading like any other', () {
    const log = '# Design decision log\n\n*Scratch space. Next: 2*\n\n### 1 A decision\n\n**Context.** C.\n';
    const to = '../reviews/design-decision-log.md#';
    expect(_kinds(_vault({'reviews/design-decision-log.md': log, 'design/README.md': '# D\n\n[the entry](${to}1%20A%20decision) ok.\n'})),
        isEmpty);
    expect(_kinds(_vault({'reviews/design-decision-log.md': log, 'design/README.md': '# D\n\n[the entry](${to}2%20Gone) no.\n'})),
        ['dead-heading docs/design/README.md:3']);
  });

  group('pinned links in the reviews', () {
    late Directory docs;
    late String one, two;
    String git(List<String> a) {
      final r = Process.runSync('git', ['-C', '${_tmp.path}/repo', '-c', 'user.email=t@t', '-c', 'user.name=t', ...a]);
      if (r.exitCode != 0) fail('git $a: ${r.stderr}');
      return (r.stdout as String).trim();
    }

    void put(String rel, String text) => File('${docs.path}/$rel')
      ..parent.createSync(recursive: true)
      ..writeAsStringSync(text);
    String commit(String m) {
      git(['add', '-A', '.']);
      git(['commit', '-q', '-m', m]);
      return git(['rev-parse', 'HEAD']);
    }

    List<String> kinds() =>
        [for (final p in checkVault(Vault.git(docs.path), _scope, git: GitHistory.of(docs.path))) '${p.kind} ${p.file}:${p.line}'];
    const log = '# Decision Log\n\n## 9. Devices\n\n### 9.1 Old\n\n'
        'About [W3](../stories/worker.md#W3%20—%20Gone%20soon) and [shift.preparing](../screens/definitions/shift.preparing.md).\n';
    const oldLog = '# Decision Log\n\n## 17. Owner notes\n\n'
        '### 17.1 Applied one\n\n**Status.** recorded 2026-10-19 · applied 2026-10-19\n\n'
        '### 17.2 Recorded one\n\n**Status.** recorded 2026-10-19\n\n';

    // main: `one` holds the log, W3, shift.preparing and an old log (decision-log.md with 9.5); `two` drops W3 and
    // shift.preparing and swaps 9.5 for 9.6 in decision-log.md; the branch `feature` starts at `two`
    setUp(() {
      Directory('${_tmp.path}/repo').createSync();
      git(['init', '-q', '-b', 'main']);
      docs = Directory('${_tmp.path}/repo/docs')..createSync();
      put('stories/worker.md', '# Stories\n\n### W2 — Begin the shift\n\nText.\n\n### W3 — Gone soon\n\nText.\n');
      put('screens/definitions/shift.preparing.md', '# shift.preparing\n');
      put('reviews/design-decision-log.md', log);
      put('decision-log.md', '$oldLog### 9.5 Gone later\n\nText.\n');
      one = commit('one');
      File('${docs.path}/screens/definitions/shift.preparing.md').deleteSync();
      put('stories/worker.md', '# Stories\n\n### W2 — Begin the shift\n\nText.\n');
      put('decision-log.md', '$oldLog### 9.6 Added last\n\nText.\n');
      two = commit('two');
      git(['checkout', '-q', '-b', 'feature']);
    });

    test('an unpinned link is unpinned only when its target is gone; a fast-forward changes nothing', () {
      put('reviews/r.md', '# R\n\n[W2](../stories/worker.md#W2%20—%20Begin%20the%20shift)\n');
      final want = ['unpinned docs/reviews/design-decision-log.md:7', 'unpinned docs/reviews/design-decision-log.md:7'];
      expect(kinds(), want); // uncommitted: the review's link resolves and needs no pin
      commit('review');
      expect(kinds(), want); // on the branch
      git(['checkout', '-q', 'main']);
      git(['merge', '-q', '--ff-only', 'feature']);
      expect(kinds(), want); // fast-forwarded onto main: the same verdict
    });

    test('the theme files and the stories are not history: a link to a gone target is dead, not unpinned', () {
      put('design/README.md', '# D\n\n[W3](../stories/worker.md#W3%20—%20Gone%20soon "git:${one.substring(0, 12)}")\n');
      put('stories/x.md', '# X\n\n[W3](worker.md#W3%20—%20Gone%20soon)\n');
      expect(kinds(), containsAll(['dead-heading docs/design/README.md:3', 'dead-heading docs/stories/x.md:3']));
    });

    test('a link into a deleted file: dead outside the reviews; in a review unpinned, or checked at its pin', () {
      File('${docs.path}/decision-log.md').deleteSync();
      final p1 = one.substring(0, 12), p2 = two.substring(0, 12);
      put('design/README.md', '# D\n\n[9.6](../decision-log.md#9.6%20Added%20last)\n');
      put('stories/x.md', '# X\n\n[the log](../decision-log.md)\n');
      put('reviews/r.md', '# R\n\n[9.6](../decision-log.md#9.6%20Added%20last) '
          '[9.5](../decision-log.md#9.5%20Gone%20later "git:$p1") [17.2](../decision-log.md#17.2%20Recorded%20one "git:$p2")\n\n'
          '[9.5](../decision-log.md#9.5%20Gone%20later "git:$p2")\n');
      final want = [
        'dead-file docs/design/README.md:3',
        'unpinned docs/reviews/design-decision-log.md:7',
        'unpinned docs/reviews/design-decision-log.md:7',
        'unpinned docs/reviews/r.md:3',
        'dead-pin docs/reviews/r.md:5',
        'dead-file docs/stories/x.md:3',
      ];
      expect(kinds(), want); // deleted in the working tree
      commit('delete the log');
      expect(kinds(), want); // the deletion committed on the branch
    });

    test('pinned links resolve at their commit on main though gone today', () {
      final p = one.substring(0, 12);
      put('reviews/design-decision-log.md', '# Decision Log\n\n## 9. Devices\n\n### 9.1 Old\n\n'
          'About [W3](../stories/worker.md#W3%20—%20Gone%20soon "git:$p") and '
          '[shift.preparing](../screens/definitions/shift.preparing.md "git:$p").\n');
      put('reviews/r.md', '# R\n\n[9.1](design-decision-log.md#9.1%20Old "git:$p")\n');
      expect(kinds(), isEmpty); // uncommitted
      commit('pin');
      expect(kinds(), isEmpty); // committed on the branch
      git(['checkout', '-q', 'main']);
      git(['merge', '-q', '--ff-only', 'feature']);
      expect(kinds(), isEmpty); // on main
    });

    test('a pin must be a commit on main and its target must exist there; the form of the anchor counts', () {
      put('stories/worker.md', '# Stories\n\n### W2 — Begin the shift\n\nText.\n\n### W4 — New\n\nText.\n');
      final branch = commit('W4 on the branch').substring(0, 12);
      final p = two.substring(0, 12);
      put('reviews/design-decision-log.md', '$log\n### 9.2 New\n\n'
          '[W4](../stories/worker.md#W4%20—%20New "git:$branch")\n\n'
          '[W4](../stories/worker.md#W4%20—%20New "git:$p")\n\n'
          '[x](../screens/definitions/never.md "git:$p")\n\n'
          '[W2](../stories/worker.md#W2%20%E2%80%94%20Begin%20the%20shift "git:$p")\n\n'
          '[W2](../stories/worker.md#W2%20—%20Begin%20the%20shift "git:0123456789ab")\n');
      expect(kinds(), [
        'unpinned docs/reviews/design-decision-log.md:7',
        'unpinned docs/reviews/design-decision-log.md:7',
        'pin docs/reviews/design-decision-log.md:11',
        'dead-pin docs/reviews/design-decision-log.md:13',
        'dead-pin docs/reviews/design-decision-log.md:15',
        'form docs/reviews/design-decision-log.md:17',
        'pin docs/reviews/design-decision-log.md:19',
      ]);
    });

    test('a new unpinned link to a gone target is unpinned too; same-file and external links are exempt', () {
      final withNew = '$log\n### 9.2 New\n\n[W2](../stories/worker.md#W2%20—%20Begin%20the%20shift) and '
          '[W3](../stories/worker.md#W3%20—%20Gone%20soon)\n';
      put('reviews/design-decision-log.md', withNew);
      expect(kinds(), ['unpinned docs/reviews/design-decision-log.md:7', 'unpinned docs/reviews/design-decision-log.md:7', 'unpinned docs/reviews/design-decision-log.md:11']);
      commit('branch line');
      expect(kinds(), ['unpinned docs/reviews/design-decision-log.md:7', 'unpinned docs/reviews/design-decision-log.md:7', 'unpinned docs/reviews/design-decision-log.md:11']);
      // on main, a link to the log's own heading and an external link need no pin
      put('reviews/design-decision-log.md', '# Decision Log\n\n## 9. Devices\n\n### 9.1 Old\n\nSee [9.1](#9.1%20Old) and [x](https://example.com).\n');
      commit('exempt');
      git(['checkout', '-q', 'main']);
      git(['merge', '-q', '--ff-only', 'feature']);
      expect(kinds(), isEmpty);
    });

    test('main is origin/main when there is one; the local main otherwise', () {
      final h = GitHistory.of(docs.path)!;
      expect(h.main, 'refs/heads/main');
      expect(h.onMain(two), isTrue);
      git(['update-ref', 'refs/remotes/origin/main', one]);
      final o = GitHistory.of(docs.path)!;
      expect(o.main, 'refs/remotes/origin/main');
      expect(o.onMain(one.substring(0, 12)), isTrue);
      expect(o.onMain(two), isFalse);
      expect(o.commitOf('reviews/design-decision-log.md', 7), one);
      expect(o.existedAt(one, 'screens/definitions/shift.preparing.md', null), isTrue);
      expect(o.existedAt(one, 'reviews/design-decision-log.md', '9.1 Old'), isTrue);
      expect(o.existedAt(one, 'stories/worker.md', 'W4 — Never'), isFalse);
      expect(o.latestOnMainWith('stories/worker.md', 'W3 — Gone soon'), one);
    });
  });

  test('a link title: scanned without its quotes, the pin read from it', () {
    final ls = scanLinks('[a](x.md "git:0f1211d1a2b3") [b](y.md) [c](z.md "other")');
    expect([for (final l in ls) (l.dest, l.title, l.pin)],
        [('x.md', 'git:0f1211d1a2b3', '0f1211d1a2b3'), ('y.md', null, null), ('z.md', 'other', null)]);
  });

  test('round trip: every mention wrapped with linkTo leaves only the problems that are not mentions', () {
    final v = _vault({
      'reviews/x.md': '# X\n\nW16 and 02 §3, decision log 9.17, shift.preparing, docs 1.1.3.\n\n'
          'Both (W2, 9.18). [dead](nothere.md)\n',
      'stories/worker.md': '# User stories — the worker\n\n### W2 — Begin the shift\n\nCount 9.17.\n\n'
          '### W16 — A replacement phone\n\nSees everything, see W2.\n',
      'design/T02-x.md': '# T2\n\n### T2.1 Flags\n\nW16 and W2 on shift.preparing.\n',
    });
    bool mention(Problem p) => p.kind == 'unlinked';
    final before = [for (final p in checkVault(v, _scope)) if (!mention(p)) '$p'];
    final ix = Index.of(v, _scope);
    var wrapped = 0;
    for (final f in v.markdown) {
      final ms = mentionsIn(v, ix, f);
      var t = v.text(f);
      for (final m in ms.reversed) {
        t = '${t.substring(0, m.start)}[${m.token}](${linkTo(f, m.target)})${t.substring(m.end)}';
        wrapped++;
      }
      File('${v.root}/$f').writeAsStringSync(t);
    }
    expect(wrapped, 8);
    expect(File('${v.root}/design/T02-x.md').readAsStringSync(),
        contains('[W16](../stories/worker.md#W16%20—%20A%20replacement%20phone) and [W2]'));
    expect(before, ['PROBLEM: docs/reviews/x.md:5: dead-file: no such file: nothere.md']);
    expect([for (final p in checkVault(Vault.dir(v.root), _scope)) '$p'], before);
  });
}
