"""Tests of omc/tools/shots.py, `just omc shots pairs [--base B]` and `just omc shots accepted` (▣ screens-assess's
steps 1, 2 and 4). Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_shots.py
Each case gets its own temporary repository from omc_fixtures' `Repo` (`paths.screenshots: [docs/screens/shots/**]`,
`paths.questions: docs/reviews/`), on a branch `feature/x`. Git LFS is faked: a
base shot is committed as a pointer file and its object written into the clone's LFS store
(`.git/lfs/objects/<o[0:2]>/<o[2:4]>/<oid>`), so no case runs `git lfs`; the pictures are PNGs Pillow writes."""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import omc  # noqa: E402
import shots  # noqa: E402
from omc_fixtures import Repo  # noqa: E402

YAML = 'docs/reviews/shots/x.yaml'
SHOTS = 'docs/screens/shots/en/'


def png(color, size=(8, 8)):
    """A PNG of one [color]."""
    out = io.BytesIO()
    Image.new('RGB', size, color).save(out, format='PNG')
    return out.getvalue()


def pointer(data):
    oid = hashlib.sha256(data).hexdigest()
    return f'version https://git-lfs.github.com/spec/v1\noid sha256:{oid}\nsize {len(data)}\n'.encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ShotsTest(unittest.TestCase):

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)
        env = mock.patch.dict(os.environ, self.repo.env, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def path(self, shot):
        return os.path.join(self.repo.work, SHOTS, f'{shot}.png')

    def write_bytes(self, rel, data):
        full = os.path.join(self.repo.work, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'wb') as f:
            f.write(data)

    def base_shots(self, **pictures):
        """Commits each picture on main as an LFS pointer, its object in the store; the branch feature/x cut from
        it; the base's sha."""
        for shot, data in pictures.items():
            self.write_bytes(f'{SHOTS}{shot}.png', pointer(data))
            oid = sha(data)
            self.write_bytes(os.path.join('.git', 'lfs', 'objects', oid[:2], oid[2:4], oid), data)
            self.repo.git('add', '--', f'{SHOTS}{shot}.png')
        self.repo.git('commit', '-q', '--allow-empty', '-m', 'shots')
        self.repo.git('push', '-q', 'origin', 'main')
        self.repo.git('checkout', '-q', '-b', 'feature/x')
        return self.repo.git('rev-parse', 'HEAD').strip()

    def current(self, shot, data):
        """The working tree's shot, as `just screenshots` writes it (the picture itself)."""
        self.write_bytes(f'{SHOTS}{shot}.png', data)

    def rows(self, rows, base='abc1234'):
        self.repo.write(YAML, json.dumps({'base': base, 'shots': rows}))  # JSON is YAML

    def omc(self, *args):
        out, err, here = io.StringIO(), io.StringIO(), os.getcwd()
        os.chdir(self.repo.work)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = omc.main(list(args))
        finally:
            os.chdir(here)
        return subprocess.CompletedProcess(args, code, out.getvalue(), err.getvalue())


class Pairs(ShotsTest):

    def test_base_oid_from_pointer(self):
        red, blue = png('red'), png('blue')
        base = self.base_shots(a=red)
        self.current('a', blue)
        self.assertEqual(shots.pairs(self.repo.work, base, YAML),
                         [{'id': 'a', 'path': f'{SHOTS}a.png', 'base': sha(red), 'current': sha(blue), 'row': None}])
        self.assertEqual(shots.pointer_oid(pointer(red)), sha(red))

    def test_current_is_sha256_of_file(self):
        base = self.base_shots(a=png('red'))
        green = png('green')
        self.current('a', green)
        [pair] = shots.pairs(self.repo.work, base, YAML)
        with open(self.path('a'), 'rb') as f:
            self.assertEqual(pair['current'], hashlib.sha256(f.read()).hexdigest())
        self.assertEqual(pair['current'], sha(green))

    def test_identical_pixels_skipped(self):
        red = png('red')
        base = self.base_shots(a=red, b=red)
        self.current('a', red)  # the same bytes: the same oid
        reencoded = io.BytesIO()
        Image.new('RGB', (8, 8), (250, 5, 5)).save(reencoded, format='PNG', compress_level=0)  # under 16 off
        self.assertNotEqual(sha(reencoded.getvalue()), sha(red))
        self.current('b', reencoded.getvalue())
        self.assertEqual(shots.pairs(self.repo.work, base, YAML), [])
        self.current('b', png('red', size=(8, 9)))  # another size differs
        self.assertEqual([p['id'] for p in shots.pairs(self.repo.work, base, YAML)], ['b'])

    def test_kept_row_when_pair_equal(self):
        red, blue = png('red'), png('blue')
        base = self.base_shots(a=red)
        self.current('a', blue)
        row = {'base': sha(red), 'current': sha(blue), 'bucket': 'expected', 'verdict': 'explained',
               'reason': 'decision 42 asks for it', 'cause': 'decision 42', 'group': None, 'review': 'accepted'}
        self.rows({'a': row})
        self.assertEqual(shots.pairs(self.repo.work, base, YAML),
                         [{'id': 'a', 'path': f'{SHOTS}a.png', 'base': sha(red), 'current': sha(blue), 'row': row}])

    def test_row_dropped_when_pair_changed(self):
        red, blue = png('red'), png('blue')
        base = self.base_shots(a=red)
        self.current('a', png('green'))
        self.rows({'a': {'base': sha(red), 'current': sha(blue), 'verdict': 'broken', 'review': 'accepted'}})
        [pair] = shots.pairs(self.repo.work, base, YAML)
        self.assertIsNone(pair['row'])


class AddedAndRemoved(ShotsTest):

    def test_added_and_removed(self):
        red, blue = png('red'), png('blue')
        base = self.base_shots(gone=red)
        os.remove(self.path('gone'))
        self.current('new', blue)
        row = {'base': None, 'current': sha(blue), 'verdict': 'explained', 'review': None}
        self.rows({'new': row})
        self.assertEqual(shots.pairs(self.repo.work, base, YAML),
                         [{'id': 'gone', 'path': f'{SHOTS}gone.png', 'base': sha(red), 'current': None, 'row': None},
                          {'id': 'new', 'path': f'{SHOTS}new.png', 'base': None, 'current': sha(blue), 'row': row}])


class Configured(ShotsTest):

    def test_ids_are_file_names_over_every_glob(self):
        red, blue = png('red'), png('blue')
        base = self.base_shots(a=red)
        self.write_bytes('docs/screens/shots/es/b.png', blue)  # untracked, another folder the glob matches
        self.write_bytes('docs/other/c.png', blue)  # no glob matches it
        self.assertEqual([(p['id'], p['path']) for p in shots.pairs(self.repo.work, base, YAML)],
                         [('b', 'docs/screens/shots/es/b.png')])

    def test_two_shots_of_one_name_refused(self):
        red, blue = png('red'), png('blue')
        base = self.base_shots(a=red)
        self.write_bytes('docs/screens/shots/es/a.png', blue)
        with self.assertRaises(shots.Refused) as e:
            shots.pairs(self.repo.work, base, YAML)
        self.assertIn('two shots named a', str(e.exception))

    def test_no_screenshots_configured_no_pair(self):
        red, blue = png('red'), png('blue')
        base = self.base_shots(a=red)
        self.current('a', blue)
        self.repo.set_config('  screenshots: [docs/screens/shots/**]\n', '')
        self.assertEqual(shots.pairs(self.repo.work, base, YAML), [])
        self.assertEqual(shots.accepted(self.repo.work, base, YAML), (True, 'accepted'))

    def test_verdicts_under_the_questions_folder(self):
        self.repo.git('checkout', '-q', '-b', 'feature/new-thing')
        self.assertEqual(shots.yaml_path(self.repo.work), 'docs/reviews/shots/new-thing.yaml')
        self.repo.set_config('  questions: docs/reviews/\n', '  questions: notes/\n')
        self.assertEqual(shots.yaml_path(self.repo.work), 'notes/shots/new-thing.yaml')


class Accepted(ShotsTest):

    def setUp(self):
        super().setUp()
        self.red, self.blue, self.green = png('red'), png('blue'), png('green')
        self.base = self.base_shots(a=self.red, b=self.red)
        self.current('a', self.blue)
        self.current('b', self.green)

    def row(self, current, review):
        return {'base': sha(self.red), 'current': sha(current), 'review': review}

    def test_all_accepted(self):
        self.rows({'a': self.row(self.blue, 'accepted'), 'b': self.row(self.green, 'accepted (carried)')})
        self.assertEqual(shots.accepted(self.repo.work, self.base, YAML), (True, 'accepted'))

    def test_one_commented(self):
        self.rows({'a': self.row(self.blue, 'accepted'), 'b': self.row(self.green, 'commented (round 1)')})
        self.assertEqual(shots.accepted(self.repo.work, self.base, YAML), (False, 'not accepted: b'))
        self.rows({'a': self.row(self.blue, 'accepted')})  # b has no row
        self.assertEqual(shots.accepted(self.repo.work, self.base, YAML), (False, 'not accepted: b'))
        self.rows({'a': self.row(self.red, 'accepted'), 'b': self.row(self.green, 'accepted')})  # a's row is stale
        self.assertEqual(shots.accepted(self.repo.work, self.base, YAML), (False, 'not accepted: a'))

    def test_none_differing(self):
        self.current('a', self.red)
        self.current('b', self.red)
        self.assertEqual(shots.accepted(self.repo.work, self.base, YAML), (True, 'accepted'))


class Cli(ShotsTest):

    def test_exit_codes(self):
        red, blue = png('red'), png('blue')
        base = self.base_shots(a=red)
        self.current('a', blue)
        r = self.omc('shots', 'pairs')  # the merge-base with origin/main
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [{'id': 'a', 'path': f'{SHOTS}a.png', 'base': sha(red), 'current': sha(blue), 'row': None}])
        r = self.omc('shots', 'pairs', '--base', base)
        self.assertEqual((r.returncode, len(json.loads(r.stdout))), (0, 1), r.stderr)
        r = self.omc('shots', 'accepted')
        self.assertEqual((r.returncode, r.stdout), (1, 'not accepted: a\n'), r.stderr)
        self.rows({'a': {'base': sha(red), 'current': sha(blue), 'review': 'accepted'}})  # the branch's yaml
        r = self.omc('shots', 'accepted')
        self.assertEqual((r.returncode, r.stdout), (0, 'accepted\n'), r.stderr)
        r = self.omc('shots', 'path')
        self.assertEqual((r.returncode, r.stdout), (0, 'docs/reviews/shots/x.yaml\n'), r.stderr)
        r = self.omc('shots', 'pairs', '--base', 'nosuchref')
        self.assertEqual((r.returncode, r.stdout), (2, ''))
        self.assertTrue(r.stderr.startswith('error: '), r.stderr)
        self.repo.git('checkout', '-q', '--detach')
        r = self.omc('shots', 'accepted')
        self.assertEqual(r.returncode, 2)
        self.assertIn('detached', r.stderr)


if __name__ == '__main__':
    unittest.main()
