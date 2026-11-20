import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:yaml/yaml.dart';

import 'scope.dart';

/// Where the vault is and which of its files the tool reads, from `paths` of the repository's `omc/config.yaml`
/// (each key's default when the file or the key is missing, as omc/tools/config.py has them): the vault is the top
/// folder of `paths.decision_log` (the repository itself for a log at its root); the log, `paths.protected`,
/// `paths.themes`, `paths.questions` and `paths.links` become the vault-relative [Scope].
class Layout {
  Layout(this.vault, this.label, this.scope);

  /// The vault's absolute path.
  final String vault;

  /// The vault as the problems name it, relative to the repository (`docs`, or `.` for the repository itself).
  final String label;

  /// The files the tool reads, relative to the vault.
  final Scope scope;

  /// The decision log, a posix path relative to the vault.
  String get log => scope.log!;
}

const defaultLog = 'docs/decision-log.md';
const defaultBase = 'main';
const defaultQuestions = 'docs/reviews/';

/// The [Layout] of the repository at [repo]; StateError on a config that is no YAML mapping, a key of the wrong
/// type, a log path that leaves the repository, or a glob or the questions folder outside the vault (the tool reads
/// only the vault, as the decisions tool refuses them).
Layout layoutOf(String repo) {
  final config = File(p.join(repo, 'omc', 'config.yaml'));
  Map paths = const {};
  final raw = _configOf(config)['paths'];
  if (raw != null && raw is! Map) throw StateError('${config.path}: paths is not a mapping');
  if (raw is Map) paths = raw;
  String str(String key, String fallback) {
    final v = paths[key];
    if (v == null) return fallback;
    if (v is! String || v.isEmpty) throw StateError('${config.path}: paths.$key is not a path');
    return v;
  }

  List<String> globs(String key) {
    final v = paths[key];
    if (v == null) return const [];
    if (v is! List || v.any((g) => g is! String || g.isEmpty)) {
      throw StateError('${config.path}: paths.$key is not a list of globs');
    }
    return [for (final g in v) g as String];
  }

  final logPath = str('decision_log', defaultLog);
  final norm = p.posix.normalize(logPath);
  if (p.posix.isAbsolute(norm) || norm == '..' || norm.startsWith('../')) {
    throw StateError('paths.decision_log $logPath leaves the repository');
  }
  final slash = norm.indexOf('/');
  final label = slash < 0 ? '.' : norm.substring(0, slash);
  final prefix = slash < 0 ? '' : '$label/';
  String inVault(String key, String path) {
    if (!path.startsWith(prefix)) {
      throw StateError("paths.$key '$path' lies outside the vault ${prefix.isEmpty ? './' : prefix} (the folder of "
          'paths.decision_log)');
    }
    return path.substring(prefix.length);
  }

  final scope = Scope(
    protected: [for (final g in globs('protected')) inVault('protected', g)],
    themes: [for (final g in globs('themes')) inVault('themes', g)],
    questions: inVault('questions', str('questions', defaultQuestions)),
    links: paths['links'] == null ? null : [for (final g in globs('links')) inVault('links', g)],
    log: slash < 0 ? norm : norm.substring(slash + 1),
  );
  return Layout(slash < 0 ? p.normalize(repo) : p.join(p.normalize(repo), label), label, scope);
}

/// The base branch of the repository at [repo]: `base` of its `omc/config.yaml` (`main` when the file or the key is
/// missing); StateError on a config that is no YAML mapping or a `base` that is no branch name.
String baseOf(String repo) {
  final config = File(p.join(repo, 'omc', 'config.yaml'));
  final v = _configOf(config)['base'];
  if (v == null) return defaultBase;
  if (v is! String || v.isEmpty) throw StateError('${config.path}: base is not a branch name');
  return v;
}

/// The YAML mapping of [config] (empty when the file is missing); StateError when it is no YAML mapping.
Map _configOf(File config) {
  if (!config.existsSync()) return const {};
  final Object? doc;
  try {
    doc = loadYaml(config.readAsStringSync());
  } on YamlException catch (e) {
    throw StateError('${config.path}: ${e.message}');
  }
  if (doc != null && doc is! Map) throw StateError('${config.path}: not a mapping');
  return doc is Map ? doc : const {};
}
