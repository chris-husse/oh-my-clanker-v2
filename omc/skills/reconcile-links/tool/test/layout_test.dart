import 'dart:io';

import 'package:docs_links/docs_links.dart';
import 'package:path/path.dart' as p;
import 'package:test/test.dart';

void main() {
  late Directory tmp;
  String repo() => '${tmp.path}/repo';
  String git(List<String> a) {
    final r = Process.runSync('git', ['-C', repo(), '-c', 'user.email=t@t', '-c', 'user.name=t', ...a]);
    if (r.exitCode != 0) fail('git $a: ${r.stderr}');
    return (r.stdout as String).trim();
  }

  void put(String rel, String text) => File('${repo()}/$rel')
    ..parent.createSync(recursive: true)
    ..writeAsStringSync(text);

  setUp(() {
    tmp = Directory.systemTemp.createTempSync('layout-');
    Directory(repo()).createSync();
    git(['init', '-q', '-b', 'main']);
  });
  tearDown(() => tmp.deleteSync(recursive: true));

  group('layoutOf', () {
    test('without omc/config.yaml: the vault docs/, the log decision-log.md in it', () {
      final l = layoutOf(repo());
      expect(l.vault, p.join(repo(), 'docs'));
      expect(l.label, 'docs');
      expect(l.log, 'decision-log.md');
    });

    test('paths.decision_log of omc/config.yaml: the vault its top folder, the log relative to it', () {
      put('omc/config.yaml',
          'base: main\npaths:\n  protected: []\n  decision_log: notes/log/decisions.md  # the log\n  questions: notes/q/\n');
      final l = layoutOf(repo());
      expect(l.vault, p.join(repo(), 'notes'));
      expect(l.label, 'notes');
      expect(l.log, 'log/decisions.md');
    });

    test('a log at the root: the vault is the repository', () {
      put('omc/config.yaml', 'paths:\n  decision_log: decisions.md\n');
      final l = layoutOf(repo());
      expect(l.vault, repo());
      expect(l.label, '.');
      expect(l.log, 'decisions.md');
    });

    test('paths.links: the files links-check checks, in place of the protected ones and the question files', () {
      put('omc/config.yaml',
          'paths:\n  protected: [docs/architecture/**, docs/design/**]\n  decision_log: docs/reviews/log.md\n'
          '  questions: docs/reviews/\n  links: [docs/design/**, docs/stories/**, docs/reviews/**]\n');
      final s = layoutOf(repo()).scope;
      expect(s.isChecked('reviews/sub/x.md'), isTrue);
      expect(s.isChecked('architecture/a.md'), isFalse);
      expect(s.isChecked('design/T01.md'), isTrue);
      expect(s.isChecked('reviews/log.md'), isTrue);
      expect(s.isProtected('architecture/a.md'), isTrue); // the guarded set is unchanged
      put('omc/config.yaml', 'paths:\n  links: [elsewhere/**]\n');
      expect(() => layoutOf(repo()), throwsStateError);
    });

    test('without paths.links: the protected files, the question files and the log, as before', () {
      put('omc/config.yaml',
          'paths:\n  protected: [docs/architecture/**, docs/design/**]\n  decision_log: docs/reviews/log.md\n'
          '  questions: docs/reviews/\n');
      final s = layoutOf(repo()).scope;
      expect(s.links, isNull);
      expect(s.isChecked('architecture/a.md'), isTrue);
      expect(s.isChecked('reviews/q.md'), isTrue);
      expect(s.isChecked('reviews/sub/x.md'), isFalse);
      expect(s.isChecked('stories/s.md'), isFalse);
    });

    test('a config without paths, or without decision_log: the default', () {
      put('omc/config.yaml', 'base: main\n');
      expect(layoutOf(repo()).log, 'decision-log.md');
      put('omc/config.yaml', 'paths:\n  briefs: tasks/\n');
      expect(layoutOf(repo()).vault, p.join(repo(), 'docs'));
    });
  });

  test("the base branch is `base` of omc/config.yaml: origin/<base>, else the local <base>", () {
    put('omc/config.yaml', 'base: develop\nbranch_prefix: feature/\n');
    put('docs/a.md', '# a\n');
    git(['add', '-A']);
    git(['commit', '-q', '-m', 'one']);
    final one = git(['rev-parse', 'HEAD']);
    git(['branch', 'develop']);
    git(['update-ref', 'refs/remotes/origin/main', one]);
    expect(GitHistory.of('${repo()}/docs')!.main, 'refs/heads/develop');
    git(['update-ref', 'refs/remotes/origin/develop', one]);
    final h = GitHistory.of('${repo()}/docs')!;
    expect(h.main, 'refs/remotes/origin/develop');
    expect(h.onMain(one), isTrue);
    put('omc/config.yaml', 'branch_prefix: feature/\n');
    expect(GitHistory.of('${repo()}/docs')!.main, 'refs/remotes/origin/main'); // no base: main, as config.py has it
    put('omc/config.yaml', 'base: [develop]\n');
    expect(() => GitHistory.of('${repo()}/docs'), throwsStateError);
  });

  test('links-check over a repository with no docs/ prints OK and exits 0', () {
    put('README.md', '# A project\n');
    git(['add', '-A']);
    git(['commit', '-q', '-m', 'one']);
    final out = StringBuffer();
    expect(linksCheck(repo(), out), 0);
    expect(out.toString(), 'OK\n');
  });

  test('pin-links over a repository with no docs/ pins nothing and exits 0', () {
    put('README.md', '# A project\n');
    git(['add', '-A']);
    git(['commit', '-q', '-m', 'one']);
    final out = StringBuffer(), err = StringBuffer();
    expect(pinLinksIn(repo(), out, err), 0);
    expect(out.toString(), 'pinned 0 links\n');
    expect(err.toString(), isEmpty);
  });

  test('the configured log is history: its link to a heading gone is unpinned, and pin-links pins it', () {
    put('omc/config.yaml', 'paths:\n  decision_log: notes/the-log.md\n  questions: notes/reviews/\n');
    put('notes/stories/worker.md', '# Stories\n\n### W2 — Begin the shift\n\nText.\n\n### W3 — Gone soon\n\nText.\n');
    put('notes/the-log.md', '# Decision Log\n\n### 1 A ruling\n\nAbout [W3](stories/worker.md#W3%20—%20Gone%20soon).\n');
    git(['add', '-A']);
    git(['commit', '-q', '-m', 'one']);
    final one = git(['rev-parse', 'HEAD']).substring(0, 12);
    put('notes/stories/worker.md', '# Stories\n\n### W2 — Begin the shift\n\nText.\n');
    git(['commit', '-q', '-am', 'two']);
    final out = StringBuffer();
    expect(linksCheck(repo(), out), 1);
    expect(out.toString(), contains('PROBLEM: notes/the-log.md:5: unpinned: '));
    final pinned = StringBuffer();
    expect(pinLinksIn(repo(), pinned, StringBuffer()), 0);
    expect(pinned.toString(), 'pinned 1 links\n');
    expect(File('${repo()}/notes/the-log.md').readAsStringSync(), contains('Gone%20soon "git:$one")'));
    final again = StringBuffer();
    expect(linksCheck(repo(), again), 0);
    expect(again.toString(), 'OK\n');
  });
  test('a glob or the questions folder outside the vault is refused, as the decisions tool refuses it', () {
    put('omc/config.yaml', 'paths:\n  decision_log: notes/log.md\n');
    expect(() => layoutOf(repo()), throwsStateError); // the default questions, docs/reviews/
    put('omc/config.yaml', 'paths:\n  decision_log: notes/log.md\n  questions: notes/q/\n  protected: [docs/**]\n');
    expect(() => layoutOf(repo()), throwsStateError);
  });

  group('the files checked, from paths', () {
    void commit() {
      git(['add', '-A']);
      git(['commit', '-q', '-m', 'c']);
    }

    List<String> problems() {
      final out = StringBuffer();
      linksCheck(repo(), out);
      return [
        for (final l in out.toString().split('\n'))
          if (l.startsWith('PROBLEM: ')) l.substring('PROBLEM: '.length).split(': ').take(2).join(' ')
      ];
    }

    test('with the defaults only the log is checked: docs/design/ is no folder of its own', () {
      put('docs/decision-log.md', '# Log\n\n[gone](nothere.md)\n');
      put('docs/design/x.md', '# X\n\n[gone](nothere.md)\n');
      put('docs/stories/y.md', '# Y\n\n[gone](nothere.md)\n');
      commit();
      expect(problems(), ['docs/decision-log.md:3 unpinned']); // the log is history
    });

    test('the question files: every *.md directly under paths.questions, checked and pinned', () {
      put('omc/config.yaml', 'paths:\n  questions: docs/questions/\n');
      put('docs/x.md', '# X\n\n## Gone soon\n\nText.\n');
      put('docs/questions/q1.md', '# Q1\n\n[x](../x.md#Gone%20soon) and [dead](nothere.md)\n');
      put('docs/questions/deeper/q2.md', '# Q2\n\n[dead](nothere.md)\n');
      put('docs/reviews/r.md', '# R\n\n[dead](nothere.md)\n');
      commit();
      final one = git(['rev-parse', 'HEAD']).substring(0, 12);
      put('docs/x.md', '# X\n');
      commit();
      expect(problems(), ['docs/questions/q1.md:3 unpinned', 'docs/questions/q1.md:3 unpinned']);
      final out = StringBuffer();
      expect(pinLinksIn(repo(), out, StringBuffer()), 1); // nothere.md never existed: not pinnable
      expect(out.toString(), startsWith('pinned 1 links\n'));
      expect(File('${repo()}/docs/questions/q1.md').readAsStringSync(), contains('Gone%20soon "git:$one")'));
    });

    test('a protected glob: a broken link there is reported, one in an unprotected page is not', () {
      put('omc/config.yaml', 'paths:\n  protected: [docs/spec/**/*.md]\n');
      put('docs/spec/a.md', '# A\n\n[gone](nothere.md)\n');
      put('docs/spec/deep/b.md', '# B\n\n[gone](../nothere.md)\n');
      put('docs/spec/c.txt', '[gone](nothere.md)\n');
      put('docs/other.md', '# O\n\n[gone](nothere.md)\n');
      commit();
      expect(problems(), ['docs/spec/a.md:3 dead-file', 'docs/spec/deep/b.md:3 dead-file']);
    });

    test('the theme files: paths.themes globs, checked, and the source of the stories\' rule references', () {
      put('omc/config.yaml', 'paths:\n  protected: [docs/stories/*.md]\n  themes: [docs/themes/T*.md]\n');
      put('docs/themes/T01-tenant.md', '# T1\n\n### T1.1 Tenant scope\n\n[gone](nothere.md)\n');
      put('docs/themes/README.md', '# Themes\n\n[gone](nothere.md)\n');
      put('docs/design/T02-flags.md', '# T2\n\n### T2.1 Flags\n');
      put('docs/stories/worker.md',
          '# S\n\n### W2 — Begin\n\n**Rules.** T1.1@${ruleHash('T1.1 Tenant scope')}, T2.1@${ruleHash('T2.1 Flags')}\n');
      commit();
      expect(problems(), ['docs/stories/worker.md:5 orphan-rule', 'docs/themes/T01-tenant.md:5 dead-file']);
    });
  });

  test('globRegExp has config.matches\' semantics', () {
    bool m(String g, String f) => globRegExp(g).hasMatch(f);
    expect(m('docs/**/*.md', 'docs/a.md'), isTrue);
    expect(m('docs/**/*.md', 'docs/x/y/a.md'), isTrue);
    expect(m('docs/*.md', 'docs/x/a.md'), isFalse);
    expect(m('docs/**', 'docs/x/a.png'), isTrue);
    expect(m('docs/T?.md', 'docs/T1.md'), isTrue);
    expect(m('docs/T[0-9]-*.md', 'docs/T5-x.md'), isTrue);
    expect(m('docs/T[!0-9]*.md', 'docs/T5.md'), isFalse);
    expect(m('docs/a.b.md', 'docs/aXb.md'), isFalse);
    expect(m('docs/.hidden/*', 'docs/.hidden/x'), isTrue);
  });
}
