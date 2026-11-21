"""The shots' pairs and their accepted state, the mechanical part of ▣ screens-assess (its steps 1, 2 and 4) and of
`/audit`'s `screens`: `just omc shots pairs [--base B]` and `just omc shots accepted [--base B]`.

A shot is a file `paths.screenshots` of omc/config.yaml matches (none listed: no shot, no pair, `accepted`); its id is
its file name without the extension, so two shots of one name are refused. Its pair is (base, current): the base's Git
LFS oid, the `oid sha256:` line of the pointer `git show <base>:<path>` prints (a blob that is no pointer: the sha256 of
its bytes, the oid LFS would give it), and the sha256 of the working tree's file (a file still a pointer: its oid). An
added shot has `base: None`, a removed one `current: None`. A shot whose two oids are equal is no pair; nor is one whose
two pictures are of the same size with no pixel differing (`differing`: a pixel counts when its largest channel
difference is over 16): a re-encode is not a review item. A picture is read from the bytes themselves, else from the
LFS object store (`<git common dir>/lfs/objects/<o[0:2]>/<o[2:4]>/<oid>`), else through `git lfs smudge` when
`git lfs` runs; one that cannot be read is a pair. The pair's `path` is the shot's file (the base's, for a removed
one); its `row` is the row of the branch's verdicts, `<paths.questions>shots/<slug>.yaml`
(`shots: {<id>: {base, current, bucket, verdict, reason, cause, group, review}}`), whose `base` and `current` equal the
pair, else None: a row of an earlier pair is never kept.

The standard library, pyyaml and, for the pixels only, Pillow (imported when two pictures are compared)."""
import hashlib
import io
import os
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import repo  # noqa: E402

Refused = config.Refused  # exit 2, `error: <why>`

POINTER = b'version https://git-lfs.github.com/spec/v1'
OID = b'oid sha256:'


def slug(root):
    """The branch's slug: its name without the branch prefix of omc/config.yaml; refused on a detached HEAD."""
    branch = repo.git(root, 'symbolic-ref', '--short', '-q', 'HEAD').stdout.strip()
    if not branch:
        raise Refused('HEAD is detached: no branch names the yaml')
    prefix = config.load(root).branch_prefix
    return branch[len(prefix):] if branch.startswith(prefix) else branch


def yaml_path(root):
    """`<paths.questions>shots/<slug>.yaml`, repo-relative: the branch's verdicts."""
    return f'{config.load(root).paths.verdicts}{slug(root)}.yaml'


def shot_id(path):
    """A shot's id: its file name without the extension."""
    return os.path.splitext(os.path.basename(path))[0]


def _by_id(paths):
    """{id: path} of the shots [paths]; refused when two share an id."""
    out = {}
    for path in sorted(paths):
        shot = shot_id(path)
        if shot in out:
            raise Refused(f'two shots named {shot}: {out[shot]} and {path}')
        out[shot] = path
    return out


def pointer_oid(data):
    """The sha256 oid of a Git LFS pointer's bytes, or None when [data] is no pointer."""
    if not data.startswith(POINTER):
        return None
    for line in data.splitlines():
        if line.startswith(OID):
            return line[len(OID):].strip().decode('ascii', 'replace')
    return None


def oid_of(data):
    """The LFS oid of a blob or file: a pointer's own, else the sha256 of the bytes."""
    return pointer_oid(data) or hashlib.sha256(data).hexdigest()


def _git_bytes(root, *args, stdin=None):
    try:
        r = subprocess.run(('git', *args), cwd=root, input=stdin, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def _base_files(root, base, globs):
    """{id: (path, the blob's bytes)} of the shots at [base]."""
    listing = repo.git(root, 'ls-tree', '-r', '-z', '--name-only', base)
    if listing.returncode != 0:
        raise Refused(f'git ls-tree {base}: {repo.why(listing)}')
    out = {}
    for shot, path in _by_id(p for p in listing.stdout.split('\0') if p and config.matches(p, globs)).items():
        data = _git_bytes(root, 'show', f'{base}:{path}')
        if data is None:
            raise Refused(f'git show {base}:{path} failed')
        out[shot] = (path, data)
    return out


def _current_files(root, globs):
    """{id: (path, the working tree file's bytes)} of the shots: the tracked and the untracked files git does not
    ignore."""
    listing = repo.git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
    if listing.returncode != 0:
        raise Refused(f'git ls-files: {repo.why(listing)}')
    found = {p for p in listing.stdout.split('\0')
             if p and config.matches(p, globs) and os.path.isfile(os.path.join(root, p))}
    out = {}
    for shot, path in _by_id(found).items():
        with open(os.path.join(root, path), 'rb') as f:
            out[shot] = (path, f.read())
    return out


def picture(root, data):
    """The PNG bytes of a blob or file: [data] itself when it is no pointer, else the LFS object of its oid from the
    store, else `git lfs smudge` of the pointer; None when neither has it."""
    oid = pointer_oid(data)
    if oid is None:
        return data
    common = repo.git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').stdout.strip()
    if common:
        stored = os.path.join(common, 'lfs', 'objects', oid[:2], oid[2:4], oid)
        if os.path.isfile(stored):
            with open(stored, 'rb') as f:
                return f.read()
    if _git_bytes(root, 'lfs', 'version') is None:
        return None
    smudged = _git_bytes(root, 'lfs', 'smudge', stdin=data)
    return smudged if smudged and pointer_oid(smudged) is None else None


def differing(a, b, threshold=16):
    """Whether two pictures ([a], [b]: paths or binary files) differ: of another size, or a pixel whose largest
    channel difference is over [threshold]."""
    import zlib  # noqa: F401  loads libz before Pillow, whose _imaging may find no libz.so.1 of its own
    from PIL import Image, ImageChops
    A, B = Image.open(a).convert('RGB'), Image.open(b).convert('RGB')
    if A.size != B.size:
        return True
    r, g, bl = ImageChops.difference(A, B).split()
    peak = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    return peak.point(lambda v: 255 if v > threshold else 0).histogram()[255] > 0


def same_pixels(root, before, after):
    """True when both pictures read, are of one size and no pixel differs over 16 in a channel."""
    a, b = picture(root, before), picture(root, after)
    if a is None or b is None:
        return False
    try:
        return not differing(io.BytesIO(a), io.BytesIO(b))
    except Exception:  # not a picture Pillow reads: a change to look at  # noqa: BLE001
        return False


def read_rows(root, path):
    """The `shots` mapping of the yaml at [path] (repo-relative or absolute); {} when the file is not there. Refused
    when it is not YAML or not of the form."""
    full = path if os.path.isabs(path) else os.path.join(root, path)
    try:
        with open(full, encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return {}
    except OSError as e:
        raise Refused(f'cannot read {path}: {e.strerror}') from None
    except yaml.YAMLError as e:
        raise Refused(f'{path} is not YAML: {e}') from None
    if data is None:
        return {}
    if not isinstance(data, dict) or not isinstance(data.get('shots') or {}, dict):
        raise Refused(f'{path}: not a mapping with a `shots` mapping')
    return {str(k): v for k, v in (data.get('shots') or {}).items() if isinstance(v, dict)}


def _oid(value):
    return None if value is None else str(value)


def pairs(root, base, yaml_path):
    """Every shot that differs from [base], sorted by id: {'id', 'path', 'base', 'current', 'row'} (module
    docstring)."""
    globs = config.load(root).paths.screenshots
    if not globs:
        return []
    before, after = _base_files(root, base, globs), _current_files(root, globs)
    rows = read_rows(root, yaml_path)
    out = []
    for shot in sorted(set(before) | set(after)):
        b = oid_of(before[shot][1]) if shot in before else None
        c = oid_of(after[shot][1]) if shot in after else None
        if b == c or (b and c and same_pixels(root, before[shot][1], after[shot][1])):
            continue
        row = rows.get(shot)
        kept = row if row is not None and _oid(row.get('base')) == b and _oid(row.get('current')) == c else None
        out.append({'id': shot, 'path': (after.get(shot) or before[shot])[0], 'base': b, 'current': c, 'row': kept})
    return out


def accepted(root, base, yaml_path):
    """(True, 'accepted') when every pair's row has a `review` starting `accepted` (no pair at all included), else
    (False, 'not accepted: <ids>')."""
    missing = [p['id'] for p in pairs(root, base, yaml_path)
               if not (p['row'] and str(p['row'].get('review') or '').startswith('accepted'))]
    return (False, f'not accepted: {", ".join(missing)}') if missing else (True, 'accepted')
