import 'dart:io';

import 'package:path/path.dart' as p;

import 'history.dart';
import 'scan.dart';
import 'scope.dart';
import 'text.dart';
import 'vault.dart';

/// What `just pin-links` did: how many links it pinned, and the links it could not pin (`docs/x.md:12: [W3](…)`).
class PinReport {
  int pinned = 0;
  final unpinnable = <String>[];
}

final _schemeRe = RegExp(r'^[a-zA-Z][a-zA-Z0-9+.-]*:');

/// Pins every unpinned link of the review files (Scope.isReview) whose target is gone from the working tree
/// to the newest commit on main at which it existed; a link that resolves is left as it is. A link whose target never
/// existed on main is reported and left. Only the title ` "git:<sha>"` is added, so the link-free text stays as it
/// was. Writes the changed files.
PinReport pinLinks(Vault v, GitHistory git, Scope scope, {String label = 'docs'}) {
  final report = PinReport();
  for (final f in v.markdown.where(scope.isReview)) {
    final raw = v.text(f);
    final inserts = <(int, String)>[]; // offset of the closing parenthesis, the title to put before it
    var line = 1, counted = 0; // the line of offset counted; links come in order
    for (final l in scanLinks(mask(raw))) {
      for (; counted < l.start; counted++) {
        if (raw.codeUnitAt(counted) == 10) line++;
      }
      final dest = l.dest;
      if (l.pin != null || l.angle || _schemeRe.hasMatch(dest) || dest.startsWith('/')) continue;
      final hash = dest.indexOf('#');
      final path = hash < 0 ? dest : dest.substring(0, hash);
      if (path.isEmpty) continue; // the file's own headings
      final frag = hash < 0 ? null : dest.substring(hash + 1);
      final target = p.posix.normalize(p.posix.join(p.posix.dirname(f), decodePercent(path)));
      final heading = frag == null || frag.isEmpty || !target.endsWith('.md') ? null : decodePercent(frag);
      final escapes = target == '..' || target.startsWith('../');
      if (escapes || _resolves(v, target, heading, frag)) continue; // resolves now (an escape is links-check's): no pin
      final at = git.latestOnMainWith(target, heading);
      if (at == null || l.title != null) {
        report.unpinnable.add('$label/$f:$line: ${raw.substring(l.start, l.end)}');
        continue;
      }
      inserts.add((l.end - 1, ' "git:${at.substring(0, 12)}"'));
    }
    if (inserts.isEmpty) continue;
    var out = raw;
    for (final (off, title) in inserts.reversed) {
      out = '${out.substring(0, off)}$title${out.substring(off)}';
    }
    File(p.join(v.root, f)).writeAsStringSync(out);
    report.pinned += inserts.length;
  }
  return report;
}

/// Whether [target] (and [heading], or [frag] as a GitHub slug) is in the working tree.
bool _resolves(Vault v, String target, String? heading, String? frag) =>
    v.isFile(target) &&
    (heading == null || v.headings(target).any((h) => h.text == heading) || v.slugs(target).containsKey(frag));
