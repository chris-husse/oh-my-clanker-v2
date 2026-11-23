// Run from omc/skills/reconcile-links/tool: `dart run bin/links_check.dart` (`just links-check`).
// Prints every link problem of the files it checks in the vault (the top folder of omc/config.yaml's
// paths.decision_log; the repository itself when no log is configured): the paths.protected and paths.themes files, the question files and the log, and every problem
// of the stories' Rules references, as PROBLEM: lines, then OK, or exits 1; a repository without the vault is OK.
import 'dart:io';

import 'package:docs_links/docs_links.dart';

void main() {
  try {
    exitCode = linksCheck(repoRoot(), stdout);
  } on StateError catch (e) { // a refused omc/config.yaml, no repository
    stderr.writeln('links-check: ${e.message}');
    exitCode = 2;
  }
}
