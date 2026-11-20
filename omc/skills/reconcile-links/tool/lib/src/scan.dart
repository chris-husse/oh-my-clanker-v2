/// One inline link or image.
class MdLink {
  MdLink(this.start, this.end, this.textStart, this.textEnd, this.dest,
      {required this.image, required this.angle, this.title});
  final int start, end; // the whole link (with `!` for an image), offsets in the text
  final int textStart, textEnd; // the link text between the brackets
  final String dest; // the destination as written, without angle brackets
  final bool image, angle;
  final String? title; // the link title after the destination, without its quotes (`"git:0f1211d1a2b3"`); null when none

  /// The commit a link of the log or the reviews is pinned to (its title `git:<sha>`); null when none.
  String? get pin => title == null ? null : _pinRe.firstMatch(title!)?[1];
}

final _pinRe = RegExp(r'^git:([0-9a-f]{7,40})$');

/// The inline links and images of [masked] (code and comments already blanked by `mask`), in order.
List<MdLink> scanLinks(String masked) {
  final s = masked;
  final out = <MdLink>[];
  var i = 0;
  while (true) {
    final open = s.indexOf('[', i);
    if (open < 0) break;
    i = open + 1;
    if (open > 0 && s[open - 1] == '\\') continue;
    if (open + 1 < s.length && s[open + 1] == '[') {
      i = open + 2; // a wikilink, not an inline link
      continue;
    }
    var depth = 0;
    var close = -1;
    for (var j = open; j < s.length; j++) {
      final c = s[j];
      if (c == '\n') break;
      if (c == '[') depth++;
      if (c == ']' && --depth == 0) {
        close = j;
        break;
      }
    }
    if (close < 0 || close + 1 >= s.length || s[close + 1] != '(') continue;
    final d = destinationAt(s, close + 2);
    if (d == null) continue;
    final image = open > 0 && s[open - 1] == '!';
    out.add(MdLink(image ? open - 1 : open, d.end, open + 1, close, d.dest, image: image, angle: d.angle, title: d.title));
    i = d.end;
  }
  return out;
}

/// The inline link destination of [s] starting at [k] (just after `](`): as written, without angle brackets, and the
/// offset just past its closing parenthesis, and its title without quotes when it has one; null when there is none.
({String dest, int end, bool angle, String? title})? destinationAt(String s, int k) {
  if (k < s.length && s[k] == '<') {
    final gt = s.indexOf('>', k);
    if (gt < 0 || s.substring(k, gt).contains('\n')) return null;
    final end = s.indexOf(')', gt);
    if (end < 0) return null;
    return (dest: s.substring(k + 1, gt), end: end + 1, angle: true, title: _title(s.substring(gt + 1, end)));
  }
  var depth = 0;
  var m = k;
  for (; m < s.length; m++) {
    final c = s[m];
    if (c == '\n' || c == ' ' || c == '\t') break;
    if (c == '(') depth++;
    if (c == ')') {
      if (depth == 0) break;
      depth--;
    }
  }
  if (m >= s.length || s[m] == '\n') return null;
  final dest = s.substring(k, m);
  if (s[m] == ')') return (dest: dest, end: m + 1, angle: false, title: null);
  final end = s.indexOf(')', m); // a title after the destination
  if (end < 0 || s.substring(m, end).contains('\n')) return null;
  return (dest: dest, end: end + 1, angle: false, title: _title(s.substring(m, end)));
}

/// The title between a destination and its closing parenthesis, without its quotes; null when there is none.
String? _title(String between) {
  final t = between.trim();
  if (t.length >= 2 && (t[0] == '"' && t.endsWith('"') || t[0] == "'" && t.endsWith("'"))) return t.substring(1, t.length - 1);
  return t.isEmpty ? null : t;
}
