import 'dart:io';

import 'package:path/path.dart' as p;

import 'text.dart';

/// The files of the docs vault, read once.
class Vault {
  Vault._(this.root, this.files);

  /// The files git tracks or would track under [root] (Obsidian's own files are ignored by .gitignore).
  factory Vault.git(String root) {
    final r = Process.runSync('git', ['-C', root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z', '.']);
    if (r.exitCode != 0) throw StateError('git ls-files in $root: ${r.stderr}');
    final files = (r.stdout as String).split('\u0000').where((f) => f.isNotEmpty && File(p.join(root, f)).existsSync()).toList()
      ..sort();
    return Vault._(p.normalize(Directory(root).absolute.path), files);
  }

  /// Every file under [root] (for tests).
  factory Vault.dir(String root) {
    final abs = p.normalize(Directory(root).absolute.path);
    final files = [
      for (final f in Directory(abs).listSync(recursive: true).whereType<File>()) p.posix.joinAll(p.split(p.relative(f.path, from: abs))),
    ]..sort();
    return Vault._(abs, files);
  }

  final String root;
  final List<String> files; // posix paths relative to root
  final _texts = <String, String>{};
  final _headings = <String, List<Heading>>{};
  final _slugs = <String, Map<String, String>>{};

  Iterable<String> get markdown => files.where((f) => f.endsWith('.md'));
  String text(String rel) => _texts.putIfAbsent(rel, () => File(p.join(root, rel)).readAsStringSync().replaceAll('\r\n', '\n'));
  List<Heading> headings(String rel) => _headings.putIfAbsent(rel, () => headingsOf(text(rel)));

  /// GitHub slugs of [rel]'s headings (duplicates numbered -1, -2) to the heading's text.
  Map<String, String> slugs(String rel) => _slugs.putIfAbsent(rel, () {
        final seen = <String, int>{};
        final out = <String, String>{};
        for (final h in headings(rel)) {
          final base = githubSlug(h.text);
          final n = seen[base] ?? 0;
          seen[base] = n + 1;
          out.putIfAbsent(n == 0 ? base : '$base-$n', () => h.text);
        }
        return out;
      });

  bool isFile(String rel) => File(p.join(root, rel)).existsSync();
  bool isDir(String rel) => Directory(p.join(root, rel)).existsSync();
}
