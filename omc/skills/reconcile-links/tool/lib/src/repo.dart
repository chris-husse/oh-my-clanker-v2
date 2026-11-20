import 'dart:io';

/// The repository's root: the nearest directory, from the working directory up, that holds `.git` (a directory in
/// the primary checkout, a file in a worktree).
String repoRoot() {
  var d = Directory.current.absolute;
  while (true) {
    if (FileSystemEntity.typeSync('${d.path}/.git') != FileSystemEntityType.notFound) return d.path;
    final parent = d.parent;
    if (parent.path == d.path) throw StateError('no .git above ${Directory.current.path}');
    d = parent;
  }
}
