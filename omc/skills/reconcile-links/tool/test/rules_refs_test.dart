import 'dart:io';

import 'package:docs_links/docs_links.dart';
import 'package:test/test.dart';

/// The source layout: the stories and the design pages protected, the theme files design/T*.md, the reviews the
/// question files.
final _scope = Scope(protected: ['design/**', 'stories/**'], themes: ['design/T*.md'], questions: 'reviews');

late Directory _tmp;

/// A vault under a fresh temporary directory holding [files] (path -> content).
Vault _vault(Map<String, String> files) {
  final root = Directory('${_tmp.path}/docs')..createSync(recursive: true);
  for (final e in files.entries) {
    File('${root.path}/${e.key}')
      ..parent.createSync(recursive: true)
      ..writeAsStringSync(e.value);
  }
  return Vault.dir(root.path);
}

const _rules = '# Design decisions\n\n## T1 Tenant and the org tree\n\n### T1.1 Tenant scope\n\nText.\n';
const _right = 'fb0b'; // sha256('T1.1 Tenant scope'), first 4 hex

String _story(String refs) => '# User stories — the worker\n\n### W2 — Begin the shift\n\nCount.\n\n**Rules.** $refs\n';

List<String> _kinds(Vault v) => [for (final p in checkRuleRefs(v, _scope)) '${p.kind} ${p.file}:${p.line}'];

void main() {
  setUp(() => _tmp = Directory.systemTemp.createTempSync('rules-'));
  tearDown(() => _tmp.deleteSync(recursive: true));

  test('the hash is the first 4 hex of the SHA-256 of the heading text', () {
    expect(ruleHash('T1.1 Tenant scope'), _right);
  });

  test('a reference with the right hash is clean', () {
    expect(_kinds(_vault({'design/T01-tenant.md': _rules, 'stories/worker.md': _story('T1.1@$_right')})), isEmpty);
  });

  test('a reference to no subtheme is orphan-rule', () {
    expect(_kinds(_vault({'design/T01-tenant.md': _rules, 'stories/worker.md': _story('T1.1@$_right, T9.9@abcd')})),
        ['orphan-rule docs/stories/worker.md:7']);
  });

  test('a reference with an old hash is stale-rule, and names the right hash', () {
    final problems = checkRuleRefs(_vault({'design/T01-tenant.md': _rules, 'stories/worker.md': _story('T1.1@0000')}), _scope);
    expect([for (final p in problems) p.kind], ['stale-rule']);
    expect(problems.single.detail, contains('T1.1@$_right'));
  });

  test('a row edit leaves a story\'s heading-only hash fresh', () {
    const rows = '$_rules\n- [R1.1-1] A rule.\n  (1.1)\n';
    expect(_kinds(_vault({'design/T01-tenant.md': rows, 'stories/worker.md': _story('T1.1@$_right')})), isEmpty);
    final edited = rows.replaceFirst('A rule.', 'A rule, edited.');
    expect(_kinds(_vault({'design/T01-tenant.md': edited, 'stories/worker.md': _story('T1.1@$_right')})), isEmpty);
  });

  test('a reference without a hash is form', () {
    expect(_kinds(_vault({'design/T01-tenant.md': _rules, 'stories/worker.md': _story('T1.1')})),
        ['form docs/stories/worker.md:7']);
  });

  test('the headings come from every design/T*.md and from no other file', () {
    const t2 = '# T2 Positions\n\n### T2.1 Flags\n\nText.\n';
    const readme = '# Design\n\n### T9.9 Not a theme file\n';
    expect(
        _kinds(_vault({
          'design/T01-tenant.md': _rules,
          'design/T02-positions.md': t2,
          'design/README.md': readme,
          'stories/worker.md': _story('T1.1@$_right, T2.1@${ruleHash('T2.1 Flags')}'),
        })),
        isEmpty);
    expect(
        _kinds(_vault({
          'design/T01-tenant.md': _rules,
          'design/README.md': readme,
          'stories/worker.md': _story('T9.9@${ruleHash('T9.9 Not a theme file')}'),
        })),
        ['orphan-rule docs/stories/worker.md:7']);
  });
}
