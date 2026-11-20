import 'package:path/path.dart' as p;

import 'scan.dart';
import 'scope.dart';
import 'text.dart';
import 'vault.dart';

/// Where a reference points: a file, and a heading in it (null: the file itself).
class Target {
  const Target(this.file, this.heading);
  final String file;
  final String? heading;
  @override
  bool operator ==(Object o) => o is Target && o.file == file && o.heading == heading;
  @override
  int get hashCode => Object.hash(file, heading);
}

/// The relative link from [from] to [t], with its anchor as Obsidian writes it.
String linkTo(String from, Target t) {
  if (t.file == from && t.heading != null) return '#${encodeAnchor(t.heading!)}';
  final rel = p.posix.relative(t.file, from: p.posix.dirname(from));
  return t.heading == null ? rel : '$rel#${encodeAnchor(t.heading!)}';
}

final _storyHeading = RegExp(r'^([A-Z]+\d+(?:\.\d+)?) [—-] ');
final _nodeHeading = RegExp(r'^(\d+(?:\.\d+)+) ');
final _sceneFile = RegExp(r'^screens/definitions/([^/]+)\.md$'); // a screen page

/// Every reference target of the vault, by the token that names it; the stories' ids from [scope]'s stories.
class Index {
  Index.of(Vault v, Scope scope) {
    void put(Map<String, Target> m, String k, Target t) {
      final old = m[k];
      if (old != null && old != t) throw StateError('"$k" is defined twice: ${old.file} and ${t.file}');
      m[k] = t;
    }

    for (final f in v.markdown) {
      final scene = _sceneFile.firstMatch(f);
      if (scene != null && scene[1] != 'README') scenes[scene[1]!] = Target(f, null);
      for (final h in v.headings(f)) {
        if (scope.isStory(f) && (h.level == 3 || h.level == 4)) {
          final m = _storyHeading.firstMatch(h.text);
          if (m != null) put(stories, m[1]!, Target(f, h.text));
        } else if (f.startsWith('product/en/')) {
          final m = _nodeHeading.firstMatch(h.text);
          if (m != null) put(nodes, m[1]!, Target(f, h.text));
        }
      }
    }
  }

  final stories = <String, Target>{};
  final scenes = <String, Target>{};
  final nodes = <String, Target>{};

  /// The target a link text or mention names exactly (`W16`, `shift.preparing`, `docs 1.1.3`).
  Target? lookup(String token) =>
      stories[token] ??
      scenes[token] ??
      (token.startsWith('docs ') ? nodes[token.substring(5)] : null);
}

/// A reference written as plain text, and what it should link to.
class Mention {
  Mention(this.file, this.start, this.end, this.token, this.target);
  final String file;
  final int start, end; // the characters to wrap in a link
  final String token;
  final Target target;
}

final _storyRe = RegExp(r'(?<![\w.§/#-])[A-Z]{1,2}\d{1,2}(?:\.\d{1,2})?(?![\w]|\.\d)');
final _nodeRe = RegExp(r'(?<![\w])docs (\d+(?:\.\d+)+)(?![\w]|\.\d)');
final _sceneRe = RegExp(r'(?<![\w/.\-])[a-z][a-z_]*\.[a-z][a-z0-9_]*(?![\w(]|\.[a-z])');
final _urlRe = RegExp(r'\bhttps?://\S+');

/// [f]'s text as prose: code, comments, headings, links, wikilinks, reference-style links and URLs blanked.
String prose(Vault v, String f) {
  var s = mask(v.text(f));
  final lines = s.split('\n');
  for (final h in v.headings(f)) {
    lines[h.line - 1] = blank(lines[h.line - 1]);
  }
  s = lines.join('\n');
  final b = StringBuffer();
  var at = 0;
  for (final l in scanLinks(s)) {
    b
      ..write(s.substring(at, l.start))
      ..write(blank(s.substring(l.start, l.end)));
    at = l.end;
  }
  b.write(s.substring(at));
  s = b.toString();
  for (final re in [RegExp(r'\[\[[^\]\n]+\]\]'), RegExp(r'\[[^\[\]\n]+\]\[[^\[\]\n]*\]'),
      RegExp(r'^ {0,3}\[[^\]\n]+\]:.*$', multiLine: true), _urlRe]) {
    s = s.replaceAllMapped(re, (m) => blank(m[0]!));
  }
  return s;
}

/// Every reference in [f] written as plain text, in order.
List<Mention> mentionsIn(Vault v, Index ix, String f) {
  final s = prose(v, f);
  final out = <Mention>[];
  void add(int start, int end, String token, Target? t) {
    if (t != null) out.add(Mention(f, start, end, token, t));
  }

  for (final m in _storyRe.allMatches(s)) {
    add(m.start, m.end, m[0]!, ix.stories[m[0]!]);
  }
  for (final m in _nodeRe.allMatches(s)) {
    add(m.start, m.end, m[0]!, ix.nodes[m[1]!]);
  }
  for (final m in _sceneRe.allMatches(s)) {
    add(m.start, m.end, m[0]!, ix.scenes[m[0]!]);
  }

  out.sort((a, b) => a.start != b.start ? a.start.compareTo(b.start) : b.end.compareTo(a.end));
  final kept = <Mention>[];
  for (final m in out) {
    if (kept.isEmpty || m.start >= kept.last.end) kept.add(m); // a mention inside an earlier one is not a second one
  }
  return kept;
}
