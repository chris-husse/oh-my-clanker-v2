"""Tests of omc/tools/repo.py, the git facts of `just omc record`, `plan` and `git`. Run
from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_repo.py
Each case gets its own temporary repository from omc_fixtures' `Repo` (a bare origin.git and a work clone on main
holding omc/config.yaml, the caller's GIT_ variables removed and a private GIT_CONFIG_GLOBAL); the tool runs as a
subprocess."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import repo  # noqa: E402
from omc_fixtures import Repo  # noqa: E402

SPECS = 'docs/superpowers/specs'
PLANS = 'docs/superpowers/plans'

PLAN = """# The plan

## Tasks

### Task 1: First

Complexity: simple

- [x] **Step 1:** done
- [x] **Step 2:** done

### Task 2: Second

**Complexity:** high

- [x] **Step 1:** done
- [ ] **Step 2:** open
- [ ] **Step 3:** open

### Task 3: Third

- [ ] **Step 1:** open

## After

- [ ] not a task's box
"""

FENCED = """### Task 1: Fenced

- [ ] **Step 1:** write the page:

```markdown
## Not a heading
- [ ] not a box
```

- [ ] **Step 2:** open
"""


class RepoTest(unittest.TestCase):

    def setUp(self):
        self.repo = Repo.make_repo()
        self.addCleanup(self.repo.cleanup)

    def omc(self, *args):
        return self.repo.omc(*args)

    def assertOut(self, r, code, stdout):
        self.assertEqual((r.returncode, r.stdout), (code, stdout), r.stderr)

    def assertRefused(self, r):
        self.assertEqual((r.returncode, r.stdout), (2, ''), r.stderr)
        self.assertTrue(r.stderr.startswith('error: '), r.stderr)

    # ------------------------------------------------------------------------------------------------------- record
    def test_record_none_is_exit_1(self):
        self.assertOut(self.omc('record'), 1, 'no record committed on this branch\n')

    def test_record_finds_the_committed_design_record(self):
        self.repo.commit(f'{SPECS}/2025-01-01-old-design.md', 'old\n', 'an older record, on main')
        self.repo.git('push', '-q', 'origin', 'main')
        self.repo.commit(f'{SPECS}/2026-01-01-x-design.md', 'x\n', 'Design: x')
        self.assertOut(self.omc('record'), 0, f'{SPECS}/2026-01-01-x-design.md\n')

    def test_an_untracked_record_is_not_found(self):
        self.repo.write(f'{SPECS}/2026-01-01-x-design.md', 'x\n')
        self.assertOut(self.omc('record'), 1, 'no record committed on this branch\n')
        self.repo.git('add', '--', SPECS)  # staged is not committed either
        self.assertOut(self.omc('record'), 1, 'no record committed on this branch\n')

    def test_two_records_are_both_printed(self):
        self.repo.commit(f'{SPECS}/2026-01-02-b-design.md', 'b\n', 'Design: b')
        self.repo.commit(f'{SPECS}/2026-01-01-a-design.md', 'a\n', 'Design: a')
        self.assertOut(self.omc('record'), 0, f'{SPECS}/2026-01-01-a-design.md\n{SPECS}/2026-01-02-b-design.md\n')

    def test_a_spec_not_named_design_is_ignored(self):
        self.repo.commit(f'{SPECS}/2026-01-01-x-notes.md', 'x\n', 'notes')
        self.repo.commit(f'{PLANS}/2026-01-01-x-design.md', 'x\n', 'a design name outside the specs')
        self.assertOut(self.omc('record'), 1, 'no record committed on this branch\n')

    def test_record_uses_specs_path(self):
        self.repo.set_config('specs: docs/superpowers/specs/', 'specs: design/')
        self.repo.commit(f'{SPECS}/2026-01-01-x-design.md', 'x\n', 'Design: x, under the default folder')
        self.repo.commit('design/2026-01-01-y-design.md', 'y\n', 'Design: y')
        self.assertOut(self.omc('record'), 0, 'design/2026-01-01-y-design.md\n')

    def test_no_origin_main_is_exit_2(self):
        self.repo.commit(f'{SPECS}/2026-01-01-x-design.md', 'x\n', 'Design: x')
        self.repo.git('update-ref', '-d', 'refs/remotes/origin/main')
        for args in (('record',), ('plan', '--next'), ('git', 'one-commit')):
            with self.subTest(args=args):
                self.assertRefused(self.omc(*args))

    # --------------------------------------------------------------------------------------------------------- plan
    def test_plan_finds_the_committed_plan(self):
        self.assertRefused(self.omc('plan', '--next'))  # no plan
        self.assertOut(self.omc('plan'), 1, 'no plan committed on this branch\n')
        self.repo.commit(f'{PLANS}/2026-01-01-x-plan.md', PLAN, 'Plan: x')
        self.repo.commit(f'{SPECS}/2026-01-01-x-design.md', 'x\n', 'Design: x')
        self.assertOut(self.omc('plan'), 0, f'{PLANS}/2026-01-01-x-plan.md\n')
        r = self.omc('plan', '--next')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count('\n'), 1)
        self.assertEqual(json.loads(r.stdout), {'task': 2, 'title': 'Second', 'complexity': 'high', 'gate': 'check'})

    def test_next_and_tick_with_two_plans_are_exit_2(self):
        self.repo.commit(f'{PLANS}/2026-01-01-a-plan.md', PLAN, 'Plan: a')
        self.repo.commit(f'{PLANS}/2026-01-01-b-plan.md', PLAN, 'Plan: b')
        for args in (('plan', '--next'), ('plan', '--tick', '2')):
            with self.subTest(args=args):
                r = self.omc(*args)
                self.assertRefused(r)
                self.assertIn('2026-01-01-a-plan.md', r.stderr)
                self.assertIn('2026-01-01-b-plan.md', r.stderr)

    def test_a_plan_without_a_task_heading_is_exit_2(self):
        self.repo.commit(f'{PLANS}/2026-01-01-x-plan.md', '# A plan\n\n- [ ] a box\n', 'Plan: x')
        self.assertRefused(self.omc('plan', '--next'))

    def test_next_task_is_the_first_with_an_unchecked_box(self):
        self.assertEqual(repo.next_task(PLAN), {'task': 2, 'title': 'Second', 'complexity': 'high', 'gate': 'check'})

    def test_a_task_without_complexity_is_medium(self):
        text, _ = repo.tick(PLAN, 2)
        self.assertEqual(repo.next_task(text), {'task': 3, 'title': 'Third', 'complexity': 'medium', 'gate': 'check'})

    def test_every_box_ticked_is_none(self):
        text, _ = repo.tick(repo.tick(PLAN, 2)[0], 3)
        self.assertIsNone(repo.next_task(text))  # the box under `## After` is no task's
        self.repo.commit(f'{PLANS}/2026-01-01-x-plan.md', text, 'Plan: x')
        r = self.omc('plan', '--next')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(r.stdout.count('\n'), 1)

    def test_a_gate_line_in_the_header_is_the_plans(self):
        gated = PLAN.replace('# The plan\n', '# The plan\n\nGate: build\n')
        self.assertEqual(repo.next_task(gated), {'task': 2, 'title': 'Second', 'complexity': 'high', 'gate': 'build'})
        self.assertEqual(repo.next_task(PLAN.replace('# The plan\n', '# The plan\n\nGate: check\n'))['gate'],
                         'check')
        self.repo.commit(f'{PLANS}/2026-01-01-x-plan.md', gated, 'Plan: x')
        r = self.omc('plan', '--next')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['gate'], 'build')

    def test_a_build_gate_holds_while_the_branch_changes_no_product_path(self):
        """With `paths.product`, a plan's `Gate: build` holds while nothing changed since the merge-base (committed,
        in the tree or untracked) matches one of its globs; a product path changed makes it `check`, the paths named
        under `product`."""
        self.repo.set_config('briefs: tasks/', 'briefs: tasks/\n  product: ["src/app/**"]')
        gated = PLAN.replace('# The plan\n', '# The plan\n\nGate: build\n')
        self.repo.commit(f'{PLANS}/2026-01-01-x-plan.md', gated, 'Plan: x')
        self.repo.commit('tools/lint.py', 'x\n', 'a tool, not the product')
        r = self.omc('plan', '--next')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['gate'], 'build')
        self.assertNotIn('product', json.loads(r.stdout))
        self.repo.write('src/app/main.dart', 'x\n')  # untracked
        r = self.omc('plan', '--next')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), {'task': 2, 'title': 'Second', 'complexity': 'high', 'gate': 'check',
                                                'product': ['src/app/main.dart']})

    def test_without_paths_product_the_plans_gate_line_stands(self):
        gated = PLAN.replace('# The plan\n', '# The plan\n\nGate: build\n')
        self.repo.commit(f'{PLANS}/2026-01-01-x-plan.md', gated, 'Plan: x')
        self.repo.commit('src/app/main.dart', 'x\n', 'code')
        r = self.omc('plan', '--next')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['gate'], 'build')

    def test_a_gate_line_inside_a_task_is_not_the_plans(self):
        inside = PLAN.replace('Complexity: simple\n', 'Complexity: simple\n\nGate: build\n')
        self.assertEqual(repo.next_task(inside)['gate'], 'check')
        fenced = PLAN.replace('# The plan\n', '# The plan\n\n```text\nGate: build\n```\n')
        self.assertEqual(repo.next_task(fenced)['gate'], 'check')

    def test_tick_ticks_only_that_task(self):
        text, count = repo.tick(PLAN, 2)
        self.assertEqual(count, 2)
        self.assertEqual(text, PLAN.replace('- [ ] **Step 2:** open\n- [ ] **Step 3:** open',
                                            '- [x] **Step 2:** open\n- [x] **Step 3:** open'))
        self.assertIn('### Task 3: Third\n\n- [ ] **Step 1:** open\n', text)
        self.repo.commit(f'{PLANS}/2026-01-01-x-plan.md', PLAN, 'Plan: x')
        self.assertOut(self.omc('plan', '--tick', '2'), 0, '2\n')
        with open(os.path.join(self.repo.work, PLANS, '2026-01-01-x-plan.md'), encoding='utf-8') as f:
            self.assertEqual(f.read(), text)
        self.assertOut(self.omc('plan', '--tick', '2'), 0, '0\n')  # nothing left to tick

    def test_tick_of_an_unknown_task_is_exit_1(self):
        self.repo.commit(f'{PLANS}/2026-01-01-x-plan.md', PLAN, 'Plan: x')
        r = self.omc('plan', '--tick', '9')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(r.stdout.count('\n'), 1)
        with open(os.path.join(self.repo.work, PLANS, '2026-01-01-x-plan.md'), encoding='utf-8') as f:
            self.assertEqual(f.read(), PLAN)

    def test_a_fenced_heading_or_box_is_not_the_plans(self):
        text, count = repo.tick(FENCED, 1)
        self.assertEqual(count, 2)
        self.assertIn('- [ ] not a box', text)
        self.assertIsNone(repo.next_task(text))

    # ---------------------------------------------------------------------------------------------------------- git
    def test_rebased_on_at_the_tip(self):
        self.repo.commit('a.txt', 'a\n', 'a')
        self.assertOut(self.omc('git', 'rebased-on'), 0, 'rebased on origin/main\n')

    def test_rebased_on_after_main_moved(self):
        self.repo.commit('a.txt', 'a\n', 'a')
        self.repo.advance_origin('b.txt', 'b\n')
        self.assertOut(self.omc('git', 'rebased-on'), 1, 'behind origin/main by 1 commits\n')

    def test_rebased_on_without_a_remote_is_exit_2(self):
        self.repo.git('remote', 'remove', 'origin')
        self.assertRefused(self.omc('git', 'rebased-on'))

    def test_one_commit(self):
        for k, code in ((0, 1), (1, 0), (2, 1)):
            if k:
                self.repo.commit(f'{k}.txt', f'{k}\n', f'commit {k}')
            with self.subTest(commits=k):
                self.assertOut(self.omc('git', 'one-commit'), code, f'{k} commits over the merge-base\n')

    def test_clean_lists_modified_and_untracked_paths(self):
        self.assertOut(self.omc('git', 'clean'), 0, 'clean\n')
        self.repo.write('.cache/omc/current', 'audit\n')  # ignored: never dirty
        self.assertOut(self.omc('git', 'clean'), 0, 'clean\n')
        self.repo.write('.gitignore', '.cache/\nbuild/\n')
        self.repo.write('new.txt', 'new\n')
        self.assertOut(self.omc('git', 'clean'), 1, ' M .gitignore\n?? new.txt\n')
        self.assertEqual(repo.dirty_paths(self.repo.work), [' M .gitignore', '?? new.txt'])

    def test_an_unknown_git_word_is_refused(self):
        self.assertRefused(self.omc('git', 'tidy'))


if __name__ == '__main__':
    unittest.main()
