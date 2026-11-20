import 'dart:convert';

import 'package:crypto/crypto.dart';

import 'check.dart';
import 'scope.dart';
import 'vault.dart';

final _rulesLineRe = RegExp(r'^\*\*Rules\.\*\* (.*)$', multiLine: true);
final _refRe = RegExp(r'^(T\d+(?:\.\d+)*)@([0-9a-f]{4})$');
final _subthemeRe = RegExp(r'^(T\d+(?:\.\d+)*) ');

/// The hash a story's rule reference carries: the first 4 hex characters of the SHA-256 of the subtheme heading's
/// text (UTF-8, the text after `### `).
String ruleHash(String headingText) => sha256.convert(utf8.encode(headingText)).toString().substring(0, 4);

/// Every problem of the stories' (Scope.isStory) `**Rules.**` lines: each reference names a subtheme heading of a
/// theme file (Scope.isTheme) and carries the hash of that heading's text.
List<Problem> checkRuleRefs(Vault v, Scope scope, {String label = 'docs'}) {
  final heads = <String, String>{
    for (final f in v.markdown.where(scope.isTheme))
      for (final h in v.headings(f))
        if (h.level >= 3 && _subthemeRe.hasMatch(h.text)) _subthemeRe.firstMatch(h.text)![1]!: h.text,
  };
  final out = <Problem>[];
  for (final f in v.markdown.where(scope.isStory)) {
    final raw = v.text(f);
    for (final m in _rulesLineRe.allMatches(raw)) {
      final line = lineOfIn(raw, m.start);
      for (final tok in m[1]!.split(',').map((t) => t.trim()).where((t) => t.isNotEmpty)) {
        final r = _refRe.firstMatch(tok);
        if (r == null) {
          out.add(Problem('$label/$f', line, 'form', 'rule reference "$tok"; write T<n>.<m>@<4 hex>'));
          continue;
        }
        final heading = heads[r[1]];
        if (heading == null) {
          out.add(Problem('$label/$f', line, 'orphan-rule', '${r[1]}: no such subtheme heading'));
          continue;
        }
        final hash = ruleHash(heading);
        if (hash != r[2]) {
          out.add(Problem('$label/$f', line, 'stale-rule',
              '${r[1]} is now "$heading" ($hash); re-read the story, then write ${r[1]}@$hash'));
        }
      }
    }
  }
  return out..sort();
}
