"""Tests of omc/tools/concurrency.py, the machine-wide slots of a gate. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_concurrency.py
Each case gets a temporary registry (`OMC_GATE_REGISTRY`) and temporary roots; a holder in another process is a
child Python that takes the slot, prints `held` and sleeps until it is killed or its stdin closes. The poll is
shortened so a waiting taker notices a freed slot quickly."""
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import concurrency  # noqa: E402

# A holder in its own process: argv root, gate, limit; `held` on stdout once the slot is taken, then it holds the slot
# until its stdin closes (or it is killed)
HOLDER = '''import sys
sys.path.insert(0, {here!r})
import concurrency
root, gate, limit = sys.argv[1], sys.argv[2], int(sys.argv[3])
with concurrency.slot(root, gate, limit, lambda line: print(line, flush=True)):
    print('held', flush=True)
    sys.stdin.read()
'''


class ConcurrencyTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        self.registry = os.path.join(self.tmp, 'registry')
        for patch in (mock.patch.dict(os.environ, {concurrency.REGISTRY_ENV: self.registry}),
                      mock.patch.object(concurrency, 'POLL', 0.05)):
            patch.start()
            self.addCleanup(patch.stop)
        self.root = self.make_root('a')
        self.holders = []

    def make_root(self, name):
        root = os.path.join(self.tmp, name)
        os.makedirs(root)
        return root

    def holder(self, root, gate='check', limit=1):
        """A child process that holds a slot of [gate] (it has printed `held`); stopped at the end of the case."""
        p = subprocess.Popen((sys.executable, '-I', '-c', HOLDER.format(here=HERE), root, gate, str(limit)),
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                             env={**os.environ, concurrency.REGISTRY_ENV: self.registry})
        self.holders.append(p)
        self.addCleanup(self.stop, p)
        self.assertEqual(p.stdout.readline().strip(), 'held')
        return p

    def stop(self, p):
        if p.poll() is None:
            p.kill()
        p.wait()
        for f in (p.stdin, p.stdout):
            f.close()

    def taker(self, root, gate='check', limit=1):
        """A taker in a thread: (thread, events) where events['taken'] is set once it holds the slot and
        events['lines'] is what it logged; it releases the slot when events['release'] is set."""
        events = {'taken': threading.Event(), 'release': threading.Event(), 'lines': []}

        def run():
            with concurrency.slot(root, gate, limit, events['lines'].append):
                events['taken'].set()
                events['release'].wait(10)
        t = threading.Thread(target=run, daemon=True)
        t.start()

        def end():  # the holders stopped first, so a taker still waiting gets its slot and ends
            events['release'].set()
            for p in self.holders:
                self.stop(p)
            t.join(10)
            self.assertFalse(t.is_alive())
        self.addCleanup(end)
        return t, events

    def test_workspace_id_stable(self):
        first = concurrency.workspace_id(self.root)
        self.assertEqual(concurrency.workspace_id(self.root), first)
        with open(os.path.join(self.root, '.cache', 'omc', 'workspace.uuid'), encoding='utf-8') as f:
            self.assertEqual(f.read().strip(), first)
        self.assertNotEqual(concurrency.workspace_id(self.make_root('b')), first)

    def test_two_takers_one_slot(self):
        p = self.holder(self.root)
        _, ev = self.taker(self.make_root('b'))
        self.assertFalse(ev['taken'].wait(0.5))  # waits while the child holds the slot
        self.assertTrue(ev['lines'], 'no wait line logged')
        uid = concurrency.workspace_id(self.root)
        self.assertRegex(ev['lines'][0], r'^max concurrency of check reached \(1 of 1 running: ')
        self.assertIn(f'{uid} {self.root}', ev['lines'][0])
        self.assertTrue(ev['lines'][0].endswith('); waiting'), ev['lines'][0])
        self.assertEqual(len(ev['lines']), 1)  # logged again each minute, not each poll
        p.stdin.close()
        p.wait(10)
        self.assertTrue(ev['taken'].wait(5))

    def test_killed_holder_frees_slot(self):
        p = self.holder(self.root)
        os.kill(p.pid, signal.SIGKILL)
        p.wait(10)
        start = time.monotonic()
        _, ev = self.taker(self.make_root('b'))
        self.assertTrue(ev['taken'].wait(1))
        self.assertLess(time.monotonic() - start, 1)
        self.assertEqual(ev['lines'], [])

    def test_same_uuid_two_runs(self):
        twin = self.make_root('twin')  # a copy of the worktree, its .cache/ with it
        uid = concurrency.workspace_id(self.root)
        os.makedirs(os.path.join(twin, '.cache', 'omc'))
        with open(os.path.join(twin, '.cache', 'omc', 'workspace.uuid'), 'w', encoding='utf-8') as f:
            f.write(uid + '\n')
        self.assertEqual(concurrency.workspace_id(twin), uid)
        self.holder(self.root, limit=2)
        _, ev = self.taker(twin, limit=2)
        self.assertTrue(ev['taken'].wait(2))  # two slots, two runs, one uuid
        ev['release'].set()
        _, ev1 = self.taker(twin, limit=1)
        self.assertFalse(ev1['taken'].wait(0.5))  # one slot: the second waits

    def test_gates_independent(self):
        self.holder(self.root, gate='check')
        _, ev = self.taker(self.make_root('b'), gate='build')
        self.assertTrue(ev['taken'].wait(2))
        self.assertEqual(ev['lines'], [])

    def test_a_released_slot_is_free_and_says_so(self):
        with concurrency.slot(self.root, 'verify', 1, self.fail):
            with open(os.path.join(self.registry, 'verify', 'slot-0'), encoding='utf-8') as f:
                words = f.read().split()
            self.assertEqual((words[0], words[-2], words[-1]),
                             (concurrency.workspace_id(self.root), 'verify', str(os.getpid())))
        with concurrency.slot(self.root, 'verify', 1, self.fail):
            pass


if __name__ == '__main__':
    unittest.main()
