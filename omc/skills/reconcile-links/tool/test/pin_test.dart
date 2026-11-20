import 'dart:io';

import 'package:docs_links/docs_links.dart';
import 'package:test/test.dart';

/// The source layout: the stories and the design pages protected, the theme files design/T*.md, the reviews the
/// question files.
final _scope = Scope(protected: ['design/**', 'stories/**'], themes: ['design/T*.md'], questions: 'reviews');

void main() {
  late Directory tmp, docs;
  String git(List<String> a) {
    final r = Process.runSync('git', ['-C', '${tmp.path}/repo', '-c', 'user.email=t@t', '-c', 'user.name=t', ...a]);
    if (r.exitCode != 0) fail('git $a: ${r.stderr}');
    return (r.stdout as String).trim();
  }

  void put(String rel, String text) => File('${docs.path}/$rel')
    ..parent.createSync(recursive: true)
    ..writeAsStringSync(text);
  String read(String rel) => File('${docs.path}/$rel').readAsStringSync();
  String commit(String m) {
    git(['add', '-A', '.']);
    git(['commit', '-q', '-m', m]);
    return git(['rev-parse', 'HEAD']).substring(0, 12);
  }

  setUp(() {
    tmp = Directory.systemTemp.createTempSync('pin-links-');
    Directory('${tmp.path}/repo').createSync();
    git(['init', '-q', '-b', 'main']);
    docs = Directory('${tmp.path}/repo/docs')..createSync();
  });
  tearDown(() => tmp.deleteSync(recursive: true));

  test('pins only links whose target is gone, to the newest commit on main with it; lists the rest', () {
    const w2 = '../stories/worker.md#W2%20—%20Begin%20the%20shift';
    const w3 = '../stories/worker.md#W3%20—%20Gone%20soon';
    const head = '# Decision Log\n\n## 9. Devices\n\n### 9.1 Old\n\n';
    put('stories/worker.md', '# Stories\n\n### W2 — Begin the shift\n\nText.\n\n### W3 — Gone soon\n\nText.\n');
    put('reviews/design-decision-log.md', '$head[W2]($w2) and [W3]($w3).\n');
    put('reviews/r.md', '# R\n\n[9.1](design-decision-log.md#9.1%20Old), [same](#R) and [web](https://example.com).\n');
    final one = commit('one');
    put('stories/worker.md', '# Stories\n\n### W2 — Begin the shift\n\nText.\n');
    put('reviews/design-decision-log.md', '$head[W2]($w2) and [W3]($w3).\n\nLater [W3]($w3) and [x](nothere.md).\n');
    final two = commit('two');
    git(['checkout', '-q', '-b', 'feature']);
    put('reviews/design-decision-log.md', '${read('reviews/design-decision-log.md')}\nBranch [W2]($w2).\n');
    final before = {for (final f in ['reviews/design-decision-log.md', 'reviews/r.md']) f: read(f)};

    final r = pinLinks(Vault.git(docs.path), GitHistory.of(docs.path)!, _scope);
    expect(r.pinned, 2);
    expect(r.unpinnable, ['docs/reviews/design-decision-log.md:9: [x](nothere.md)']);
    expect(
        read('reviews/design-decision-log.md'),
        '$head[W2]($w2) and [W3]($w3 "git:$one").\n\n'
        'Later [W3]($w3 "git:$one") and [x](nothere.md).\n\nBranch [W2]($w2).\n');
    expect(read('reviews/r.md'), before['reviews/r.md']); // its link resolves: nothing to pin
    expect(two, isNot(one));
    for (final e in before.entries) {
      expect(unlink(read(e.key)), unlink(e.value)); // the link-free text is unchanged
    }
    // what is left for links-check: the link no commit on main had; a second run pins nothing
    expect([for (final p in checkVault(Vault.git(docs.path), _scope, git: GitHistory.of(docs.path))) '${p.kind} ${p.line}'],
        ['unpinned 9']);
    expect(pinLinks(Vault.git(docs.path), GitHistory.of(docs.path)!, _scope).pinned, 0);
  });

  test('pins a branch line whose target is gone from the working tree to the last commit on main with it', () {
    const old = '../stories/worker.md#W2%20—%20Begin%20the%20shift';
    const live = '../stories/worker.md#W4%20—%20End%20the%20shift';
    put('stories/worker.md', '# Stories\n\n### W2 — Begin the shift\n\nText.\n\n### W4 — End the shift\n\nText.\n');
    put('reviews/design-decision-log.md', '# Decision Log\n');
    final one = commit('one');
    git(['checkout', '-q', '-b', 'feature']);
    put('stories/worker.md', '# Stories\n\n### W2 — Start the shift\n\nText.\n\n### W4 — End the shift\n\nText.\n');
    put('reviews/design-decision-log.md', '# Decision Log\n\nBranch [W2]($old) and [W4]($live).\n');
    commit('branch');

    final r = pinLinks(Vault.git(docs.path), GitHistory.of(docs.path)!, _scope);
    expect(r.pinned, 1);
    expect(r.unpinnable, isEmpty);
    expect(read('reviews/design-decision-log.md'), '# Decision Log\n\nBranch [W2]($old "git:$one") and [W4]($live).\n');
    expect(checkVault(Vault.git(docs.path), _scope, git: GitHistory.of(docs.path)), isEmpty);
  });

  test('pins a link into a deleted decision log like any link whose target is gone', () {
    put('decision-log.md', '# Decision Log\n\n### 9.1 Old\n\nText.\n');
    final one = commit('one');
    git(['checkout', '-q', '-b', 'feature']);
    File('${docs.path}/decision-log.md').deleteSync();
    put('reviews/r.md', '# R\n\n[9.1](../decision-log.md#9.1%20Old) and [x](../decision-log.md#Never).\n');

    final report = pinLinks(Vault.git(docs.path), GitHistory.of(docs.path)!, _scope);
    expect(report.pinned, 1);
    expect(report.unpinnable, ['docs/reviews/r.md:3: [x](../decision-log.md#Never)']);
    expect(read('reviews/r.md'), '# R\n\n[9.1](../decision-log.md#9.1%20Old "git:$one") and [x](../decision-log.md#Never).\n');
    expect([for (final p in checkVault(Vault.git(docs.path), _scope, git: GitHistory.of(docs.path))) '${p.kind} ${p.line}'],
        ['unpinned 3']);
  });
}
