import 'dart:convert';

import 'scan.dart';

/// Every character of [s] but newlines as a space, so offsets and line numbers stay.
String blank(String s) => s.replaceAll(RegExp(r'[^\n]'), ' ');

final _fenceRe = RegExp(r'^\s*(`{3,}|~{3,})');

/// [text] with fenced code blocks, inline code spans and HTML comments blanked.
String mask(String text) {
  final lines = text.split('\n');
  String? fence;
  for (var i = 0; i < lines.length; i++) {
    final m = _fenceRe.firstMatch(lines[i]);
    if (fence == null) {
      if (m != null) {
        fence = m[1]!;
        lines[i] = blank(lines[i]);
      }
    } else {
      if (m != null && m[1]![0] == fence[0] && m[1]!.length >= fence.length && lines[i].trim() == m[1]) fence = null;
      lines[i] = blank(lines[i]);
    }
  }
  var s = lines.join('\n');
  s = s.replaceAllMapped(RegExp(r'<!--[\s\S]*?-->'), (m) => blank(m[0]!));
  return _maskCodeSpans(s);
}

/// [s] with inline code spans blanked, read left to right: a link destination (`](…)`) is passed over whole, so a
/// backtick inside it (an anchor to a heading with code) never opens a code span.
String _maskCodeSpans(String s) {
  final b = StringBuffer();
  var i = 0;
  while (i < s.length) {
    final c = s[i];
    if (c == '`') {
      var k = i;
      while (k < s.length && s[k] == '`') {
        k++;
      }
      final close = RegExp('(?<!`)${'`' * (k - i)}(?!`)').firstMatch(s.substring(k));
      if (close == null || close.start == 0) {
        b.write(s.substring(i, k)); // no closing run: the backticks are literal
        i = k;
      } else {
        final end = k + close.end;
        b.write(blank(s.substring(i, end)));
        i = end;
      }
    } else if (c == ']' && i + 1 < s.length && s[i + 1] == '(') {
      final d = destinationAt(s, i + 2);
      final end = d == null ? i + 1 : d.end;
      b.write(s.substring(i, end));
      i = end;
    } else {
      b.write(c);
      i++;
    }
  }
  return b.toString();
}

final _pctRunRe = RegExp(r'(?:%[0-9A-Fa-f]{2})+');

/// [s] with each `%XX` sequence that encodes a UTF-8 character decoded; raw characters, and bytes that are not part
/// of a valid UTF-8 character, stay as they are.
String decodePercent(String s) => s.replaceAllMapped(_pctRunRe, (m) {
      final run = m[0]!;
      final bytes = [for (var i = 0; i < run.length; i += 3) int.parse(run.substring(i + 1, i + 3), radix: 16)];
      final out = StringBuffer();
      var i = 0;
      while (i < bytes.length) {
        final lead = bytes[i];
        final n = lead < 0x80 ? 1 : lead >= 0xC2 && lead < 0xE0 ? 2 : lead >= 0xE0 && lead < 0xF0 ? 3 : lead >= 0xF0 && lead < 0xF5 ? 4 : 0;
        if (n > 0 && i + n <= bytes.length) {
          try {
            out.write(utf8.decode(bytes.sublist(i, i + n)));
            i += n;
            continue;
          } on FormatException {
            // not a valid character: keep its first byte as written
          }
        }
        out.write(run.substring(3 * i, 3 * i + 3));
        i++;
      }
      return out.toString();
    });

class Heading {
  Heading(this.line, this.level, this.text);
  final int line; // 1-based
  final int level;
  final String text; // raw, as Obsidian keys it
}

final _headingRe = RegExp(r'^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*$');

/// The ATX headings of [text] outside fenced code, in order.
List<Heading> headingsOf(String text) {
  final out = <Heading>[];
  final lines = text.split('\n');
  String? fence;
  for (var i = 0; i < lines.length; i++) {
    final f = _fenceRe.firstMatch(lines[i]);
    if (fence != null) {
      if (f != null && f[1]![0] == fence[0] && f[1]!.length >= fence.length && lines[i].trim() == f[1]) fence = null;
      continue;
    }
    if (f != null) {
      fence = f[1]!;
      continue;
    }
    final m = _headingRe.firstMatch(lines[i]);
    if (m != null && m[2]!.isNotEmpty) out.add(Heading(i + 1, m[1]!.length, m[2]!));
  }
  return out;
}

/// The anchor for [heading]: its text with every space as %20 and every backtick as %60, every other character raw.
/// Obsidian lands on it as it does on its own form; a raw backtick would open a code span under CommonMark (GitHub,
/// the Confluence renderer).
String encodeAnchor(String heading) => heading.replaceAll(' ', '%20').replaceAll('`', '%60');

/// The anchor GitHub gives [heading] (the rule the docs used before the vault).
String githubSlug(String heading) => heading
    .toLowerCase()
    .replaceAll(RegExp(r'[^\p{L}\p{N}\s_-]', unicode: true), '')
    .trim()
    .replaceAll(' ', '-');
