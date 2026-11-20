import 'dart:convert';
import 'dart:io';

import 'layout.dart';
import 'text.dart';

/// What git remembers: the commit that introduced each line of a file, the commits on main (the base branch, `base`
/// of omc/config.yaml), and a file's text at a commit. Every answer is cached: the log has thousands of links.
class GitHistory {
  GitHistory(this.repoRoot, this.prefix, {this.base = defaultBase});
  final String repoRoot;
  final String prefix; // the vault's path inside the repository, with a trailing slash ('docs/'), or ''
  final String base; // the base branch's name

  final _blame = <String, List<String?>>{};
  final _shows = <String, String?>{};
  final _headings = <String, Set<String>>{};
  final _onMain = <String, bool>{};
  Set<String>? _mainCommits;
  String? _main;

  /// For a vault inside a git repository, its base branch the repository's [baseOf]; null when it is in none.
  static GitHistory? of(String vaultRoot) {
    final top = Process.runSync('git', ['-C', vaultRoot, 'rev-parse', '--show-toplevel', '--show-prefix']);
    if (top.exitCode != 0) return null;
    final parts = (top.stdout as String).split('\n');
    final root = parts[0].trim();
    return GitHistory(root, parts.length > 1 ? parts[1].trim() : '', base: baseOf(root));
  }

  ProcessResult _git(List<String> args) => Process.runSync('git', ['-C', repoRoot, ...args], stdoutEncoding: utf8);

  /// The base branch: `origin/<base>`, or the local `<base>` when there is no origin's; null when neither exists.
  String? get main {
    if (_main != null) return _main!.isEmpty ? null : _main;
    for (final ref in ['refs/remotes/origin/$base', 'refs/heads/$base']) {
      if (_git(['rev-parse', '--verify', '-q', '$ref^{commit}']).exitCode == 0) return _main = ref;
    }
    _main = '';
    return null;
  }

  Set<String> get _commitsOnMain => _mainCommits ??= main == null
      ? <String>{}
      : {for (final l in (_git(['rev-list', main!]).stdout as String).split('\n')) if (l.trim().isNotEmpty) l.trim()};

  /// Whether [sha] (full or abbreviated) is a commit on main: an ancestor of it, or its tip.
  bool onMain(String sha) => _onMain.putIfAbsent(sha, () {
        final all = _commitsOnMain;
        return sha.length == 40 ? all.contains(sha) : all.any((c) => c.startsWith(sha));
      });

  /// The commit that introduced each line of the vault file [vaultRel] in the working tree (index 0 is line 1); null
  /// for an uncommitted line. One `git blame` per file.
  List<String?> lineCommits(String vaultRel) => _blame.putIfAbsent(vaultRel, () {
        final r = _git(['blame', '--porcelain', '--', '$prefix$vaultRel']);
        if (r.exitCode != 0) return const [];
        final out = <String?>[];
        final header = RegExp(r'^([0-9a-f]{40}) \d+ (\d+)');
        for (final l in (r.stdout as String).split('\n')) {
          final m = header.firstMatch(l);
          if (m == null) continue;
          final line = int.parse(m[2]!);
          while (out.length < line) {
            out.add(null);
          }
          out[line - 1] = m[1]!.startsWith('0000000000') ? null : m[1];
        }
        return out;
      });

  /// The commit that introduced line [line] (1-based) of the vault file [vaultRel]; null when the line is uncommitted.
  String? commitOf(String vaultRel, int line) {
    final all = lineCommits(vaultRel);
    return line >= 1 && line <= all.length ? all[line - 1] : null;
  }

  /// The text of the repository path [repoPath] at [commit]; null when it does not exist there.
  String? show(String commit, String repoPath) => _shows.putIfAbsent('$commit:$repoPath', () {
        final r = _git(['show', '$commit:$repoPath']);
        return r.exitCode != 0 ? null : (r.stdout as String).replaceAll('\r\n', '\n');
      });

  /// Whether [vaultRel] existed at [commit], with [heading] among its headings when one is given. A path that does
  /// not exist at the commit is tried at its old locations too (locationsOf).
  bool existedAt(String commit, String vaultRel, String? heading) {
    for (final path in locationsOf(vaultRel)) {
      final key = '$commit:$prefix$path';
      final text = show(commit, '$prefix$path');
      if (text == null) continue;
      if (heading == null) return true;
      return _headings.putIfAbsent(key, () => {for (final h in headingsOf(text)) h.text}).contains(heading);
    }
    return false;
  }

  /// The newest commit on main at which [vaultRel] (with [heading] when one is given) existed, at its path or an old
  /// location; null when there is none.
  String? latestOnMainWith(String vaultRel, String? heading) {
    if (main == null) return null;
    final r = _git(['log', '--format=%H', main!, '--', for (final l in locationsOf(vaultRel)) '$prefix$l']);
    if (r.exitCode != 0) return null;
    for (final c in (r.stdout as String).split('\n')) {
      if (c.trim().isNotEmpty && existedAt(c.trim(), vaultRel, heading)) return c.trim();
    }
    return null;
  }

  /// [vaultRel] and the locations it had before, in the order to try them: none in this repository yet.
  static List<String> locationsOf(String vaultRel) => [vaultRel];
}
