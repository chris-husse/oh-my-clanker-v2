import 'dart:io';

import 'check.dart';
import 'history.dart';
import 'layout.dart';
import 'pin.dart';
import 'rules_refs.dart';
import 'vault.dart';

/// `just links-check` over the repository at [repo] (its vault and scope from layoutOf): every link problem of the
/// checked files (Scope.isChecked) and of the stories' Rules references, as PROBLEM: lines, then `<n> problems` and 1, or `OK` and 0.
/// A repository without the vault's folder has nothing to check: `OK`.
int linksCheck(String repo, StringSink out) {
  final layout = layoutOf(repo);
  final problems = <Problem>[];
  if (Directory(layout.vault).existsSync()) {
    final vault = Vault.git(layout.vault);
    problems
      ..addAll(checkVault(vault, layout.scope, label: layout.label, git: GitHistory.of(layout.vault)))
      ..addAll(checkRuleRefs(vault, layout.scope, label: layout.label))
      ..sort();
  }
  for (final p in problems) {
    out.writeln(p);
  }
  if (problems.isEmpty) {
    out.writeln('OK');
    return 0;
  }
  out.writeln('${problems.length} problems');
  return 1;
}

/// `just pin-links` over the repository at [repo]: pins the review files' links whose target is gone (pinLinks),
/// prints how many and every link it could not pin; 1 when one is left, 2 without the base branch. A repository without
/// the vault's folder has nothing to pin: `pinned 0 links`.
int pinLinksIn(String repo, StringSink out, StringSink err) {
  final layout = layoutOf(repo);
  if (!Directory(layout.vault).existsSync()) {
    out.writeln('pinned 0 links');
    return 0;
  }
  final git = GitHistory.of(layout.vault);
  if (git == null || git.main == null) {
    err.writeln('pin-links: ${layout.vault} is not in a git repository with the base branch ${baseOf(repo)} '
        '(origin/<base> or <base>, base of omc/config.yaml)');
    return 2;
  }
  final r = pinLinks(Vault.git(layout.vault), git, layout.scope, label: layout.label);
  out.writeln('pinned ${r.pinned} links');
  for (final u in r.unpinnable) {
    out.writeln('NOT PINNED: $u');
  }
  if (r.unpinnable.isNotEmpty) {
    out.writeln('${r.unpinnable.length} links not pinned: no commit on main has their target');
    return 1;
  }
  return 0;
}
