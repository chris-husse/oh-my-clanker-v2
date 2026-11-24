"""`just install <project-folder>`: puts v2's omc/ into a project, which then owns its copy (v2 is no runtime
dependency). v2 is the repository holding this script; what it ships is the committed omc/ at its HEAD (never the
working tree, never omc/VERSION, omc/bin/ or omc/hook/).

- Refused (exit 2, `error: <why>` on stderr, nothing written): the folder is not the top of a git work tree, its tree
  is dirty (untracked files count), v2's HEAD cannot be resolved, a `.claude/skills/<name>` omc links is already the
  project's own (not a link), the project's justfile (or a file it imports) defines a recipe of omc/omc.just, the
  project's .claude/settings.json is not a JSON object, (update) omc/VERSION names a commit v2 does not know, a path
  the install writes through is a symlink (omc/, a folder above one of its files, .claude, .claude/skills,
  .gitignore, .cache, .cache/omc), .claude/skills is there but no folder, or a path of v2's tree has an empty, `.`,
  `..` or `.git` component.
- Fresh (no omc/VERSION): every shipped file is copied, its executable bit kept; a file the project already had there
  with other contents is replaced and listed `REPLACED <path>`.
- Update (omc/VERSION present): per shipped path of the base (the commit in VERSION) or of v2's HEAD, a three-way
  merge of the project's file, the base's and HEAD's (`git merge-file`): a clean merge is written; a conflicted one is
  written with its markers and listed `CONFLICT <path>`; a file deleted on one side and changed on the other is left
  as the project has it and listed `KEPT <path> (<why>)`. omc/bin/ and omc/hook/ are never touched; a file only the
  project has stays.
- Then, either way: omc/VERSION is v2's HEAD; `.claude/skills/<name>` links to ../../omc/pipeline/<name> (brainstorm,
  design, implement, audit), ../../omc/terminals/<name> (check, build, verify) and ../../omc/skills/<name> (each),
  when the project has the skill's SKILL.md; an update links only a skill new since the base, so a skill or link the
  project deleted stays deleted, listed `KEPT .claude/skills/<name> (deleted here)`, and removes the link of a skill
  the base shipped and HEAD does not, when it still points where omc put it, listed `REMOVED .claude/skills/<name>
  (omc no longer ships it)` (any other link stays); the justfile imports omc/omc.just (created when missing);
  .claude/settings.json holds omc's two SessionStart hooks (added only when no hook runs the same command; a hook an
  earlier install wrote takes its new command); the root .gitignore ignores .cache/ (appended unless git ignores it
  already). Each is left alone when already so, so a second run is a no-op.
- Last, `.cache/omc/install-report` (overwritten each run) holds `mode: fresh|update`, `from: <base sha or ->`,
  `to: <v2 sha>`, `v2: <this v2's absolute path>`, one line each, then every `CONFLICT`, `KEPT`, `REMOVED` and
  `REPLACED` line printed, as printed: what `/oh-my-clanker` reads, since it cannot see this output.
- Then `claude /oh-my-clanker` in the project (replacing this process), unless `--no-launch`.
Exit 0 when done, 1 when an update left conflicts (VERSION still moves; the skill resolves them), 2 when refused.
The standard library only."""
import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile

V2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = 'omc/VERSION'
REPORT = os.path.join('.cache', 'omc', 'install-report')  # read by /oh-my-clanker, which cannot see stdout
PIPELINE = ('brainstorm', 'design', 'implement', 'audit')
TERMINALS = ('check', 'build', 'verify')
IMPORT_LINE = "import 'omc/omc.just'"
JUSTFILES = ('justfile', 'Justfile', '.justfile')
SETTINGS = os.path.join('.claude', 'settings.json')
# omc's SessionStart hooks: back into the work after a compaction, and the herdr pane title (its bytecode under the
# ignored .cache/, so the hook leaves the tree clean)
HERDR_HOOK = ('[ "${TERM_PROGRAM-}" = herdr ] && python3 -I -X pycache_prefix="$CLAUDE_PROJECT_DIR/.cache/pycache" '
              '"$CLAUDE_PROJECT_DIR/omc/tools/herdr.py" >/dev/null 2>&1 || true')
SESSION_START = [
    {'matcher': 'compact',
     'hooks': [{'type': 'command', 'command': 'cd "$CLAUDE_PROJECT_DIR" && just omc enter --resume'}]},
    {'hooks': [{'type': 'command', 'command': HERDR_HOOK, 'timeout': 5}]},
]
# A hook command an earlier install wrote -> the one that replaces it
REPLACED_HOOKS = {
    '[ "${TERM_PROGRAM-}" = herdr ] && python3 -I "$CLAUDE_PROJECT_DIR/omc/tools/herdr.py" >/dev/null 2>&1 || true':
        HERDR_HOOK,
}
# The project's paths the install writes through, besides omc/'s files: none may be a symlink
WRITE_PATHS = ('omc', '.claude', os.path.join('.claude', 'skills'), '.gitignore', '.cache',
               os.path.join('.cache', 'omc'))
# A recipe's name and a justfile's `import`/`import?`, as omc/tools/lint.py reads them
RECIPE = re.compile(r'^@?([A-Za-z_][\w-]*)(?:[ \t][^:\n]*)?:(?!=)', re.M)
IMPORT = re.compile(r'''^import\??[ \t]+(['"])(.+?)\1[ \t]*(?:#.*)?$''', re.M)
SHA = re.compile(r'^[0-9a-f]{40}$')


class Refused(Exception):
    pass


def git(cwd, *args, data=None):
    r = subprocess.run(('git', *args), cwd=cwd, input=data, capture_output=True)
    if r.returncode != 0:
        raise Refused(f'git {" ".join(args)} in {cwd}: {r.stderr.decode(errors="replace").strip()}')
    return r.stdout


def shipped(path):
    return path != VERSION and not path.startswith(('omc/bin/', 'omc/hook/'))


def tree(sha):
    """The shipped files of omc/ at v2's [sha]: path -> (mode, blob id)."""
    files = {}
    for entry in git(V2, 'ls-tree', '-r', '-z', '--full-tree', sha, '--', 'omc').split(b'\0'):
        if not entry:
            continue
        meta, path = entry.decode().split('\t', 1)
        mode, kind, oid = meta.split()
        if not shipped(path):
            continue
        if any(c in ('', '.', '..') or c.lower() == '.git' for c in path.split('/')):
            raise Refused(f'{path} at v2 {sha[:7]} has a component omc never writes (empty, ".", ".." or ".git")')
        if mode not in ('100644', '100755'):
            raise Refused(f'{path} at v2 {sha[:7]} is not a plain file (mode {mode})')
        files[path] = (mode, oid)
    return files


def blobs(oids):
    """The contents of v2's blobs [oids], read in one `git cat-file --batch`: oid -> bytes."""
    oids = sorted(set(oids))
    out = git(V2, 'cat-file', '--batch', data=''.join(o + '\n' for o in oids).encode())
    found, at = {}, 0
    for oid in oids:
        end = out.index(b'\n', at)
        size = int(out[at:end].split()[2])
        found[oid] = out[end + 1:end + 1 + size]
        at = end + 2 + size
    return found


def skill_links(files):
    """`.claude/skills/<name>` -> its link target, for the skills [files] hold."""
    def present(kind, name):
        return any(p.startswith(f'omc/{kind}/{name}/') for p in files)
    links = {n: f'../../omc/pipeline/{n}' for n in PIPELINE if present('pipeline', n)}
    links.update({n: f'../../omc/terminals/{n}' for n in TERMINALS if present('terminals', n)})
    for p in files:
        parts = p.split('/')
        if len(parts) > 3 and parts[1] == 'skills':
            links[parts[2]] = f'../../omc/skills/{parts[2]}'
    return links


def justfile_of(project):
    for name in JUSTFILES:
        if os.path.isfile(os.path.join(project, name)):
            return os.path.join(project, name)
    return None


def project_recipes(project):
    """The recipes of the project's justfile and of the files it imports, omc/omc.just left out: [name] -> file."""
    start = justfile_of(project)
    omc_just = os.path.realpath(os.path.join(project, 'omc', 'omc.just'))
    found, seen, todo = {}, set(), [start] if start else []
    while todo:
        path = todo.pop()
        real = os.path.realpath(path)
        if real in seen or real == omc_just:
            continue
        seen.add(real)
        try:
            with open(path, encoding='utf-8') as f:
                text = f.read()
        except OSError:
            continue
        for name in RECIPE.findall(text):
            found.setdefault(name, os.path.relpath(path, project))
        todo.extend(os.path.join(os.path.dirname(path), m.group(2)) for m in IMPORT.finditer(text))
    return found


def read_settings(project):
    path = os.path.join(project, SETTINGS)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            settings = json.load(f)
    except (OSError, ValueError) as e:
        raise Refused(f'{SETTINGS} cannot be read: {e}')
    hooks = settings.get('hooks', {}) if isinstance(settings, dict) else None
    if not isinstance(hooks, dict) or not isinstance(hooks.get('SessionStart', []), list):
        raise Refused(f'{SETTINGS} is not an object whose hooks.SessionStart is a list')
    return settings


def merged_settings(settings):
    """[settings] with a hook an earlier install wrote (`REPLACED_HOOKS`) given its new command, and omc's SessionStart
    hooks added where no hook runs the same command; None when nothing changes."""
    settings = copy.deepcopy(settings)
    entries = settings.setdefault('hooks', {}).setdefault('SessionStart', [])
    hooks = [h for e in entries if isinstance(e, dict) for h in e.get('hooks', []) if isinstance(h, dict)]
    replaced = False
    for h in hooks:
        if h.get('command') in REPLACED_HOOKS:
            h['command'] = REPLACED_HOOKS[h['command']]
            replaced = True
    commands = {h.get('command') for h in hooks}
    added = [copy.deepcopy(e) for e in SESSION_START if e['hooks'][0]['command'] not in commands]
    if not added and not replaced:
        return None
    entries.extend(added)
    return settings


def check_project(project):
    if not os.path.isdir(project):
        raise Refused(f'{project} is not a folder')
    r = subprocess.run(('git', '-C', project, 'rev-parse', '--show-toplevel'), capture_output=True, text=True)
    if r.returncode != 0:
        raise Refused(f'{project} is not a git work tree')
    if os.path.realpath(r.stdout.strip()) != os.path.realpath(project):
        raise Refused(f'{project} is not the top of its git work tree ({r.stdout.strip()})')
    if git(project, 'status', '--porcelain', '--untracked-files=all').strip():
        raise Refused(f'{project} is dirty; commit or stash first, so the install is one reviewable diff')


def check_write_paths(project, rels):
    """Refuses when a path the install writes through is a symlink (`WRITE_PATHS` and every existing folder above a
    file of [rels]), or `.claude/skills` is there but no folder: a write would land outside the project's tree."""
    folders = set(WRITE_PATHS)
    for rel in rels:
        parent = os.path.dirname(rel)
        while parent:
            folders.add(parent)
            parent = os.path.dirname(parent)
    for rel in sorted(folders):
        if os.path.islink(os.path.join(project, rel)):
            raise Refused(f'{rel} in the project is a symlink; the install writes there and never through a symlink')
    skills = os.path.join(project, '.claude', 'skills')
    if os.path.lexists(skills) and not os.path.isdir(skills):
        raise Refused('.claude/skills in the project is no folder; the install links the skills there')


def write_file(path, data, mode):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.islink(path):
        os.remove(path)
    with open(path, 'wb') as f:
        f.write(data)
    set_mode(path, mode)


def set_mode(path, mode):
    os.chmod(path, 0o755 if mode == '100755' else 0o644)


def remove_file(project, rel):
    os.remove(os.path.join(project, rel))
    parent = os.path.dirname(rel)
    while parent not in ('omc', ''):
        try:
            os.rmdir(os.path.join(project, parent))
        except OSError:
            break
        parent = os.path.dirname(parent)


def merge_file(ours, base, theirs, labels):
    """`git merge-file -p --diff3` of the three contents: (result, conflicted); None when git cannot merge them (a
    binary file)."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, data in (('ours', ours), ('base', base), ('theirs', theirs)):
            paths.append(os.path.join(tmp, name))
            with open(paths[-1], 'wb') as f:
                f.write(data)
        r = subprocess.run(('git', 'merge-file', '-p', '--diff3', '-L', labels[0], '-L', labels[1], '-L', labels[2],
                            *paths), capture_output=True)
    if r.returncode < 0 or r.returncode > 127:
        return None
    return r.stdout, r.returncode > 0


def update(project, base, head, B, T, content, say):
    """The three-way merge of omc/ into [project], each CONFLICT and KEPT line through [say]; the paths left in
    conflict."""
    labels = ('project', f'omc {base[:7]}', f'omc {head[:7]}')
    conflicts = []
    for rel in sorted(set(B) | set(T)):
        path = os.path.join(project, rel)
        have = os.path.isfile(path) and not os.path.islink(path)
        o = open(path, 'rb').read() if have else None
        b = content[B[rel][1]] if rel in B else None
        t = content[T[rel][1]] if rel in T else None
        if t is None:  # deleted in omc
            if o is None:
                continue
            if o == b:
                remove_file(project, rel)
            else:
                say(f'KEPT {rel} (changed here, deleted in omc)')
            continue
        mode = T[rel][0]
        if o is None:
            if b is None:
                write_file(path, t, mode)  # new in omc
            elif t != b:
                say(f'KEPT {rel} (deleted here, changed in omc)')
            continue
        if rel in B and B[rel][0] != mode:  # omc changed the executable bit: it moves; else the project's stays
            set_mode(path, mode)
        if o == t or b == t:
            continue
        if o == b:
            with open(path, 'wb') as f:
                f.write(t)
            continue
        merged = merge_file(o, b or b'', t, labels)
        if merged is None:
            say(f'CONFLICT {rel} (cannot be merged; the project\'s copy is left)')
            conflicts.append(rel)
            continue
        data, conflicted = merged
        with open(path, 'wb') as f:
            f.write(data)
        if conflicted:
            say(f'CONFLICT {rel}')
            conflicts.append(rel)
    return conflicts


def ignore_cache(project):
    """Appends `.cache/` to the project's root .gitignore (created when missing) unless git already ignores it: omc's
    gate logs, pass records and venv live there, and a tree they dirty holds no gate pass."""
    if subprocess.run(('git', 'check-ignore', '-q', '.cache/x'), cwd=project, capture_output=True).returncode == 0:
        return
    path = os.path.join(project, '.gitignore')
    text = ''
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            text = f.read()
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text + ('\n' if text and not text.endswith('\n') else '') + '.cache/\n')


def link_skills(project, links, old, new, say):
    """`.claude/skills/<name>` -> [links]' target for each skill in [new] whose SKILL.md the project has; the link to
    a skill of [old] (the base's) that [links] no longer has removed when it still points where the base's did,
    listed REMOVED through [say] (any other link, the project's own, stays); a skill of [links] not in [new] whose
    link or SKILL.md is gone listed KEPT through [say]."""
    skills_dir = os.path.join(project, '.claude', 'skills')
    os.makedirs(skills_dir, exist_ok=True)
    for name, target in sorted(old.items()):  # omc's links to skills it no longer ships
        link = os.path.join(skills_dir, name)
        if name not in links and os.path.islink(link) and os.readlink(link) == target:
            os.remove(link)
            say(f'REMOVED .claude/skills/{name} (omc no longer ships it)')
    for name, target in sorted(links.items()):
        link = os.path.join(skills_dir, name)
        there = os.path.isfile(os.path.join(project, 'omc', target[len('../../omc/'):], 'SKILL.md'))
        if name not in new:
            if not there or not os.path.lexists(link):
                say(f'KEPT .claude/skills/{name} (deleted here)')
            continue
        if not there:
            say(f'KEPT .claude/skills/{name} (deleted here)')
            continue
        if os.path.islink(link):
            if os.readlink(link) == target:
                continue
            os.remove(link)
        os.symlink(target, link)


def import_omc_just(project):
    """The project's justfile imports omc/omc.just (the justfile created when missing)."""
    justfile = justfile_of(project)
    if justfile is None:
        with open(os.path.join(project, 'justfile'), 'w', encoding='utf-8') as f:
            f.write(IMPORT_LINE + '\n')
    else:
        with open(justfile, encoding='utf-8') as f:
            text = f.read()
        if not any(m.group(2) == 'omc/omc.just' for m in IMPORT.finditer(text)):
            with open(justfile, 'w', encoding='utf-8') as f:
                f.write(text + ('' if text.endswith('\n') or not text else '\n') + IMPORT_LINE + '\n')


def install(project):
    """Installs or updates omc/ in [project]; the paths an update left in conflict. Raises Refused before writing."""
    project = os.path.abspath(project)
    check_project(project)
    try:
        head = git(V2, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    except Refused:
        raise Refused(f'v2 at {V2} has no HEAD commit')
    version_path = os.path.join(project, VERSION)
    base = None
    if os.path.exists(version_path):
        with open(version_path, encoding='utf-8') as f:
            base = f.read().strip()
        if not SHA.match(base):
            raise Refused(f'{VERSION} does not hold a full commit sha: {base!r}')
        known = subprocess.run(('git', 'cat-file', '-e', base + '^{commit}'), cwd=V2, capture_output=True)
        if known.returncode != 0:
            raise Refused(f'{VERSION} names {base}, a commit v2 at {V2} does not know')
    T = tree(head)
    B = tree(base) if base else {}
    check_write_paths(project, set(T) | set(B))
    content = blobs([oid for _, oid in T.values()] + [oid for _, oid in B.values()])

    # Every skill of T is linked on a fresh install; an update links only a skill new in T (or moved), so a skill or
    # link the project deleted stays deleted
    links = skill_links(T)
    old = skill_links(B)
    new = {n: target for n, target in links.items() if old.get(n) != target}
    skills_dir = os.path.join(project, '.claude', 'skills')
    for name in sorted(new):
        link = os.path.join(skills_dir, name)
        if os.path.lexists(link) and not os.path.islink(link):
            raise Refused(f'.claude/skills/{name} is the project\'s own; omc links its skill there')
    omc_just = content[T['omc/omc.just'][1]].decode() if 'omc/omc.just' in T else ''
    own = project_recipes(project)
    for name in RECIPE.findall(omc_just):
        if name in own:
            raise Refused(f"the project's {own[name]} defines the recipe '{name}', which omc/omc.just defines too")
    settings = merged_settings(read_settings(project))

    report = [f'mode: {"update" if base else "fresh"}', f'from: {base or "-"}', f'to: {head}', f'v2: {V2}']

    def say(line):
        print(line)
        report.append(line)

    conflicts = []
    if base is None:
        for rel, (mode, oid) in sorted(T.items()):
            path = os.path.join(project, rel)
            if os.path.lexists(path):  # an omc/ without VERSION: the project's file is replaced, and listed
                if os.path.islink(path) or not os.path.isfile(path):
                    say(f'REPLACED {rel}')
                else:
                    with open(path, 'rb') as f:
                        if f.read() != content[oid]:
                            say(f'REPLACED {rel}')
            write_file(path, content[oid], mode)
    elif base != head:
        conflicts = update(project, base, head, B, T, content, say)
    if base != head:
        with open(version_path, 'w', encoding='utf-8') as f:
            f.write(head + '\n')

    link_skills(project, links, old, new, say)
    import_omc_just(project)

    if settings is not None:
        os.makedirs(os.path.dirname(os.path.join(project, SETTINGS)), exist_ok=True)
        with open(os.path.join(project, SETTINGS), 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
            f.write('\n')

    ignore_cache(project)
    os.makedirs(os.path.join(project, os.path.dirname(REPORT)), exist_ok=True)
    with open(os.path.join(project, REPORT), 'w', encoding='utf-8') as f:
        f.write(''.join(line + '\n' for line in report))

    if base is None:
        print(f'installed omc {head[:7]} into {project}')
    elif base == head:
        print(f'omc {head[:7]} already installed in {project}')
    else:
        print(f'updated omc {base[:7]} -> {head[:7]} in {project}'
              + (f'; {len(conflicts)} file(s) in conflict' if conflicts else ''))
    return conflicts


def main(argv):
    parser = argparse.ArgumentParser(prog='just install', description='Install or update omc/ in a project.')
    parser.add_argument('project', help='the project folder, the top of its git work tree')
    parser.add_argument('--no-launch', action='store_true', help='do not start `claude /oh-my-clanker` there')
    args = parser.parse_args(argv)
    try:
        conflicts = install(args.project)
    except Refused as e:
        print(f'error: {e}', file=sys.stderr)
        return 2
    if not args.no_launch:
        sys.stdout.flush()
        os.chdir(args.project)
        try:
            os.execvp('claude', ['claude', '/oh-my-clanker'])
        except OSError as e:
            print(f'error: cannot start claude ({e}); run `claude /oh-my-clanker` in {args.project}', file=sys.stderr)
            return 2
    return 1 if conflicts else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
