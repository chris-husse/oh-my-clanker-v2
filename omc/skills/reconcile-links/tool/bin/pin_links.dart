// Run from omc/skills/reconcile-links/tool: `dart run bin/pin_links.dart` (`just pin-links`).
// Pins every link of the log and the question files whose target is gone to the newest commit on main where it existed,
// prints how many it pinned and every link it could not pin; exits 1 when one is left, 2 without the base branch
// (`base` of omc/config.yaml; "main" here is that base branch).
import 'dart:io';

import 'package:docs_links/docs_links.dart';

void main() {
  try {
    exitCode = pinLinksIn(repoRoot(), stdout, stderr);
  } on StateError catch (e) { // a refused omc/config.yaml, no repository
    stderr.writeln('pin-links: ${e.message}');
    exitCode = 2;
  }
}
