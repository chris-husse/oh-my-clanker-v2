import 'package:path/path.dart' as p;

import 'history.dart';
import 'references.dart';
import 'scan.dart';
import 'scope.dart';
import 'text.dart';
import 'vault.dart';

class Problem implements Comparable<Problem> {
  Problem(this.file, this.line, this.kind, this.detail);
  final String file;
  final int line;
  final String kind, detail;

  @override
  String toString() => 'PROBLEM: $file:$line: $kind: $detail';

  @override
  int compareTo(Problem o) => file != o.file
      ? file.compareTo(o.file)
      : line != o.line
          ? line.compareTo(o.line)
          : kind.compareTo(o.kind);
}

final _schemeRe = RegExp(r'^[a-zA-Z][a-zA-Z0-9+.-]*:');
final _externalRe = RegExp(r'^(https?|mailto):', caseSensitive: false);
final _wikiRe = RegExp(r'\[\[[^\]\n]+\]\]');
final _refUseRe = RegExp(r'\[[^\[\]\n]+\]\[[^\[\]\n]*\]');
final _refDefRe = RegExp(r'^ {0,3}\[[^\]\n]+\]:[ \t]*\S', multiLine: true);

int lineOfIn(String raw, int off) => raw.substring(0, off).split('\n').length;

/// Every link problem of the files [scope] checks (Scope.isChecked), sorted by file and line; their targets resolve
/// against the whole vault. With [git], a link of the review files is checked as pinned history: a pinned link at its
/// commit on main; an unpinned one resolves now like any link, and one whose target is gone is `unpinned`.
List<Problem> checkVault(Vault v, Scope scope, {String label = 'docs', GitHistory? git}) {
  final ix = Index.of(v, scope);
  final problems = <Problem>[];
  for (final f in v.markdown.where(scope.isChecked)) {
    final raw = v.text(f);
    final masked = mask(raw);
    final starts = [0, for (var i = 0; i < raw.length; i++) if (raw.codeUnitAt(i) == 10) i + 1];
    int lineOf(int off) {
      var lo = 0, hi = starts.length - 1;
      while (lo < hi) {
        final mid = (lo + hi + 1) >> 1;
        if (starts[mid] <= off) {
          lo = mid;
        } else {
          hi = mid - 1;
        }
      }
      return lo + 1;
    }

    void add(int off, String kind, String detail) => problems.add(Problem('$label/$f', lineOf(off), kind, detail));

    /// The check against today's vault of a link that resolves now: the link's text names the reference it links to.
    void checkToday(MdLink l, String target, String? heading) {
      if (!l.image && !scope.isReview(target)) { // a link into a review file names that file's item, never a story
        final token = raw.substring(l.textStart, l.textEnd).replaceAll('`', '').trim();
        final want = ix.lookup(token);
        if (want != null && (want.file != target || (want.heading != null && want.heading != heading))) {
          add(l.start, 'wrong-target',
              '"$token" links to ${linkTo(f, Target(target, heading))}; it is ${linkTo(f, want)}');
        }
      }
    }

    for (final m in _wikiRe.allMatches(masked)) {
      add(m.start, 'form', 'wikilink ${m[0]}; write a relative Markdown link');
    }
    for (final m in _refUseRe.allMatches(masked)) {
      add(m.start, 'form', 'reference-style link ${m[0]}; write an inline link');
    }
    for (final m in _refDefRe.allMatches(masked)) {
      add(m.start, 'form', 'reference definition; write inline links');
    }
    for (final l in scanLinks(masked)) {
      final dest = l.dest;
      if (l.angle) {
        add(l.start, 'form', 'angle-bracket destination <$dest>; write each space as %20');
        continue;
      }
      if (_schemeRe.hasMatch(dest)) {
        if (!_externalRe.hasMatch(dest)) add(l.start, 'form', 'scheme not allowed: $dest');
        continue;
      }
      if (dest.startsWith('/')) {
        add(l.start, 'form', 'absolute path: $dest');
        continue;
      }
      final hash = dest.indexOf('#');
      final path = hash < 0 ? dest : dest.substring(0, hash);
      final frag = hash < 0 ? null : dest.substring(hash + 1);
      final target = path.isEmpty ? f : p.posix.normalize(p.posix.join(p.posix.dirname(f), decodePercent(path)));
      if (target == '..' || target.startsWith('../')) {
        add(l.start, 'escape', 'link leaves $label/: $dest');
        continue;
      }
      if (git != null && scope.isReview(f) && path.isNotEmpty) {
        final pin = l.pin;
        if (pin == null) {
          final heading = frag == null || frag.isEmpty || !target.endsWith('.md') ? null : decodePercent(frag);
          final resolves = v.isFile(target) &&
              (heading == null || v.headings(target).any((h) => h.text == heading) || v.slugs(target).containsKey(frag));
          if (!resolves) {
            add(l.start, 'unpinned', '$dest: no longer resolves; run just pin-links');
            continue;
          }
        } else {
          // pinned: checked at its commit, not in the working tree; whether the target exists today does not matter
          final heading = frag == null || frag.isEmpty || !target.endsWith('.md') ? null : decodePercent(frag);
          if (!git.onMain(pin)) {
            add(l.start, 'pin', 'git:$pin is not a commit on main: $dest');
          } else if (!git.existedAt(pin, target, null)) {
            add(l.start, 'dead-pin', 'no such file at git:$pin: $dest');
          } else if (heading != null && !git.existedAt(pin, target, heading)) {
            add(l.start, 'dead-pin', 'no heading "$heading" in $target at git:$pin');
          } else if (heading != null && frag != encodeAnchor(heading)) {
            add(l.start, 'form', 'anchor not as Obsidian writes it: #$frag; write #${encodeAnchor(heading)}');
          }
          if (!v.isFile(target) || (heading != null && !v.headings(target).any((h) => h.text == heading))) {
            continue; // gone today: nothing else to check against the working tree
          }
          checkToday(l, target, heading);
          continue;
        }
      }
      if (!v.isFile(target)) {
        add(l.start, 'dead-file', v.isDir(target) ? 'a folder, not a file: $dest' : 'no such file: $dest');
        continue;
      }
      String? heading;
      if (frag != null && frag.isNotEmpty && target.endsWith('.md')) {
        final texts = [for (final h in v.headings(target)) h.text];
        final asText = decodePercent(frag);
        if (texts.contains(asText)) {
          heading = asText;
          if (frag != encodeAnchor(asText)) {
            add(l.start, 'form', 'anchor not as Obsidian writes it: #$frag; write #${encodeAnchor(asText)}');
          }
        } else {
          final slug = v.slugs(target)[frag];
          if (slug != null) {
            add(l.start, 'form', 'GitHub slug #$frag; write #${encodeAnchor(slug)}');
          } else {
            add(l.start, 'dead-heading', 'no heading "$asText" in $target');
          }
          continue;
        }
      }
      checkToday(l, target, heading);
    }
    for (final m in mentionsIn(v, ix, f)) {
      add(m.start, 'unlinked', '${m.token}: link it to ${linkTo(f, m.target)}');
    }
  }
  problems.sort();
  return problems;
}
