import 'package:path/path.dart' as p;

/// Which files of the vault the tool reads, from omc/config.yaml's `paths`, every path relative to the vault:
/// the protected documents (`paths.protected` globs), the theme files (`paths.themes` globs), the question files
/// (`*.md` directly under `paths.questions`), the decision log (`paths.decision_log`) and the files links-check
/// checks (`paths.links` globs; absent: the protected documents and the question files). Empty lists cover nothing.
class Scope {
  Scope({this.protected = const [], this.themes = const [], this.questions, this.log, this.links})
      : _protected = [for (final g in protected) globRegExp(g)],
        _themes = [for (final g in themes) globRegExp(g)],
        _links = links == null ? null : [for (final g in links) globRegExp(g)];

  final List<String> protected, themes;

  /// The globs of the files links-check checks besides the theme files and the log; null: the protected documents
  /// and the question files.
  final List<String>? links;

  final List<RegExp>? _links;

  /// The question files' folder, without its trailing `/`; null: none.
  final String? questions;

  /// The decision log; null: none.
  final String? log;

  final List<RegExp> _protected, _themes;

  bool isProtected(String f) => _protected.any((r) => r.hasMatch(f));

  bool isTheme(String f) => _themes.any((r) => r.hasMatch(f));

  /// Whether [f] is a review file, history whose links are pinned: a question file or the log.
  bool isReview(String f) =>
      f == log || (questions != null && f.endsWith('.md') && p.posix.dirname(f) == _folder(questions!));

  /// Whether links-check checks [f]: a file of [links] (absent: a protected document or a question file), the log
  /// or a theme file.
  bool isChecked(String f) =>
      (_links == null ? isProtected(f) || isReview(f) : _links.any((r) => r.hasMatch(f)) || f == log) || isTheme(f);

  /// Whether [f] is a story, whose `**Rules.**` lines and story headings the tool reads: a protected file under
  /// `stories/`.
  bool isStory(String f) => f.startsWith('stories/') && isProtected(f);

  static String _folder(String q) {
    final n = p.posix.normalize(q);
    return n.endsWith('/') ? n.substring(0, n.length - 1) : n;
  }
}

/// [glob] as an anchored RegExp with the semantics of omc/tools/config.py's `matches` (Python's `glob.translate`,
/// recursive, hidden files included): `*` and `?` stay within one folder, a `**` segment spans any number of them
/// (none too, so `a/**/*.md` matches `a/x.md`), `[…]` is a character class (`[!…]` negated).
RegExp globRegExp(String glob) {
  final segs = glob.split('/');
  final b = StringBuffer('^');
  for (var i = 0; i < segs.length; i++) {
    final s = segs[i];
    final last = i == segs.length - 1;
    if (s == '**') {
      b.write(last ? '.*' : '(?:.+/)?');
      continue;
    }
    var j = 0;
    while (j < s.length) {
      final c = s[j];
      if (c == '*') {
        b.write('[^/]*');
        while (j + 1 < s.length && s[j + 1] == '*') {
          j++;
        }
      } else if (c == '?') {
        b.write('[^/]');
      } else if (c == '[') {
        final end = s.indexOf(']', j + 2 <= s.length ? j + 2 : s.length);
        if (end < 0) {
          b.write(r'\[');
        } else {
          var body = s.substring(j + 1, end);
          final neg = body.startsWith('!');
          if (neg) body = body.substring(1);
          b.write('[${neg ? '^' : ''}${body.replaceAll(r'\', r'\\')}]');
          j = end;
        }
      } else {
        b.write(RegExp.escape(c));
      }
      j++;
    }
    if (!last) b.write('/');
  }
  b.write(r'$');
  return RegExp(b.toString());
}
