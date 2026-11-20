# omc/tools/decisions/test_decisions.py
"""Tests of omc/tools/decisions/decisions.py. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --project omc --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/decisions/test_decisions.py
Every check takes texts: the tests pass the logs and the pages in, no git, but for GitInputsTest."""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import decisions  # noqa: E402
from decision_log_fixtures import (FIXTURE, LOG_HEAD, STORY, T05, APPLIED, RECORDED, write_vault, entry,  # noqa: E402
                                   log_text, parse, config, config_text, PATHS)
import omc_fixtures  # noqa: E402  (decision_log_fixtures put omc/tools on the path)

OLD_HEAD = ('# Design decision log: screen reviews\n\n*Append-only. One section per screen review (`/review-design`), each '
            'entry a decided change and its reasoning.\nWritten only through `just decisions --log reviews/design-decision-log.md`.*\n')
W2_LINK = '[W2](../stories/worker.md#W2%20—%20Begin%20the%20shift)'
SCENE_LINK = '[shift.preparing](../screens/definitions/shift.preparing.md)'
INCIDENTS_LINK = '[Incidents](../architecture/operations.md#Incidents)'


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = write_vault(self.tmp.name)
        self.vault = decisions.Vault(self.docs)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        with open(os.path.join(self.docs, rel), 'w', encoding='utf-8') as f:
            f.write(text)

    def log_now(self):
        return decisions.parse_log(self.vault.text(decisions.LOG))


class LinksTest(unittest.TestCase):
    def test_scan_links_handles_parentheses_and_titles(self):
        text = 'see [W3](stories/worker.md#W3%20—%20Check%20in%20(QR)) and ![s](x.png) and [x](y.md "git:0f1211d1") end'
        links = decisions.scan_links(text)
        self.assertEqual([(l.text, l.dest, l.title) for l in links],
                         [('W3', 'stories/worker.md#W3%20—%20Check%20in%20(QR)', None), ('x', 'y.md', 'git:0f1211d1')])
        self.assertEqual(decisions.unlink(text), 'see W3 and ![s](x.png) and x end')

    def test_anchor_encoding(self):
        self.assertEqual(decisions.encode_anchor('9.17 `lookback` applies'), '9.17%20%60lookback%60%20applies')
        self.assertEqual(decisions.decode_anchor('W3%20—%20Check%20in%20(QR)'), 'W3 — Check in (QR)')

    def test_mask_code_keeps_length(self):
        s = 'a `W2` b [W2](x)'
        self.assertEqual(len(decisions.mask_code(s)), len(s))
        self.assertNotIn('`W2`', decisions.mask_code(s))


class NormalizeTest(unittest.TestCase):
    def same(self, path, before, after):
        return decisions.normalize(path, before) == decisions.normalize(path, after)

    def test_a_link_only_edit_normalizes_equal(self):
        self.assertTrue(self.same('design/T05-the-shift.md', T05, T05.replace('Begin%20the%20shift', 'Begin%20the%20day')))
        self.assertTrue(self.same('design/T05-the-shift.md', T05, T05.replace('without signal', 'without [signal](../x.md)')))

    def test_an_e2e_only_edit_normalizes_equal(self):
        self.assertTrue(self.same('design/T05-the-shift.md', T05, T05.replace('[E2E: E5.2.1-1]', '[E2E: E5.2.1-1, E5.2.1-2]')))
        self.assertTrue(self.same('design/T05-the-shift.md', T05, T05.replace('  [E2E: E5.2.1-1]\n', '')))

    def test_a_story_hash_only_edit_normalizes_equal(self):
        self.assertTrue(self.same('stories/worker.md', STORY, STORY.replace('@454f', '@0a1b')))
        self.assertFalse(self.same('stories/worker.md', STORY, STORY.replace('T5.2.1@454f', 'T5.2.2@454f')))

    def test_a_word_edit_does_not(self):
        self.assertFalse(self.same('design/T05-the-shift.md', T05, T05.replace('without signal', 'without a signal')))

    def test_port_yaml_compares_raw(self):
        self.assertEqual(decisions.normalize('architecture/objects/port.yaml', 'a: [x](y)\n'), 'a: [x](y)\n')
        self.assertIsNone(decisions.normalize('stories/worker.md', None))

    def test_a_references_block_edit_does_not_normalize_away(self):
        page = '# s\n\n```references\n- {ref: R5.2.1-1, says: "A shift cannot begin."}\n```\n'
        self.assertFalse(self.same('screens/definitions/s.md', page, page.replace('cannot begin', 'may begin')))


class ResolveTest(VaultCase):
    def resolved(self, name, gone=frozenset()):
        r = self.vault.resolve(name, gone)
        return r.file, r.written

    def test_rules_and_subthemes_reach_their_theme_file(self):
        self.assertEqual(self.resolved('R5.2.1-1'), ('design/T05-the-shift.md', 'R5.2.1-1'))
        self.assertEqual(self.resolved('T5.2.1'), ('design/T05-the-shift.md', 'T5.2.1'))
        self.assertEqual(self.resolved('T5'), ('design/T05-the-shift.md', 'T5'))

    def test_a_story_and_a_scene_are_written_as_links(self):
        self.assertEqual(self.resolved('W2'), ('stories/worker.md', W2_LINK))
        self.assertEqual(self.resolved('shift.preparing'), ('screens/definitions/shift.preparing.md', SCENE_LINK))

    def test_views_components_and_vault_paths_are_written_plain(self):
        self.assertEqual(self.resolved('views/shift_view'), ('screens/views/shift_view.md', 'views/shift_view'))
        self.assertEqual(self.resolved('incident_row'), ('screens/components/incident_row.md', 'incident_row'))
        self.assertEqual(self.resolved('screens/FORMAT.md'), ('screens/FORMAT.md', 'screens/FORMAT.md'))
        self.assertEqual(self.resolved('docs/architecture/objects/port.yaml'), ('architecture/objects/port.yaml', 'architecture/objects/port.yaml'))

    def test_a_heading_of_a_guarded_page_is_written_as_its_link(self):
        self.assertEqual(self.resolved('architecture/operations.md#Incidents'), ('architecture/operations.md', INCIDENTS_LINK))

    def test_a_name_that_reaches_nothing_is_refused(self):
        for name in ('R9.9-9', 'nothing.here', 'stories/none.md', 'architecture/operations.md#Nope', 'reviews/2026-11-12-x-1.md', 'W99'):
            with self.assertRaises(decisions.RefError, msg=name):
                self.vault.resolve(name)

    def test_a_deleted_scene_resolves_when_gone(self):
        gone = frozenset({'screens/definitions/shift.gone.md'})
        self.assertEqual(self.resolved('shift.gone', gone), ('screens/definitions/shift.gone.md', 'shift.gone'))
        with self.assertRaises(decisions.RefError):
            self.vault.resolve('shift.gone')


class WriteTest(VaultCase):
    def add(self, title='Incidents need a photo', context='W2 counts without proof.', decision='Every incident carries a photo.', **kw):
        return decisions.add_decision(self.vault, self.log_now(), title, context, decision, today='2026-11-12', **kw)

    def test_add_decision_appends_the_entry_and_advances_next(self):
        n = self.add(affected=['R5.2.1-1', 'W2', 'shift.preparing', 'architecture/operations.md#Incidents'],
                     source='reviews/2026-11-12-x-1.md#Q1 A question')
        self.assertEqual(n, 1)
        self.assertEqual(self.vault.text(decisions.LOG), log_text(2, '\n'.join([
            '### 1 Incidents need a photo', '',
            f'**Context.** {W2_LINK} counts without proof.',
            '**Decision.** Every incident carries a photo.',
            '**Automated.** false',
            f'**Affected.** R5.2.1-1, {W2_LINK}, {SCENE_LINK}, {INCIDENTS_LINK}',
            '**Source.** [Q1](2026-11-12-x-1.md#Q1%20A%20question)',
            '**Status.** recorded 2026-11-12']) + '\n'))
        self.assertEqual(self.add('Second'), 2)
        log = self.log_now()
        self.assertEqual((log.next, list(log.entries)), (3, [1, 2]))
        self.assertNotIn('Affected', log.entries[2].fields)

    def test_automated_writes_true(self):
        self.add(automated=True)
        self.assertEqual(self.log_now().entries[1].fields['Automated'], 'true')

    def test_an_unknown_affected_name_writes_nothing(self):
        with self.assertRaisesRegex(decisions.RefError, 'nothing.here'):
            self.add(affected=['W2', 'nothing.here'])
        self.assertEqual(self.vault.text(decisions.LOG), LOG_HEAD)

    def test_a_missing_title_context_or_decision_is_refused(self):
        for kw in ({'title': ''}, {'context': ' '}, {'decision': None}):
            with self.assertRaises(decisions.RefError, msg=kw):
                self.add(**kw)
        self.assertEqual(self.vault.text(decisions.LOG), LOG_HEAD)

    def test_the_old_header_is_refused(self):
        self.write(decisions.LOG, OLD_HEAD)
        with self.assertRaisesRegex(decisions.RefError, 'Next'):
            self.add()


class ApplyTest(VaultCase):
    def setUp(self):
        super().setUp()
        decisions.add_decision(self.vault, self.log_now(), 'Incidents need a photo', 'C.', 'D.', affected=['W2'], today='2026-11-12')

    def test_apply_sets_the_status_and_replaces_affected(self):
        decisions.apply_decision(self.vault, self.log_now(), 1, ['screens/FORMAT.md', 'R5.2.1-1'], today='2026-11-13')
        e = self.log_now().entries[1]
        self.assertEqual((e.status, e.fields['Status']), (decisions.Status.APPLIED, 'recorded 2026-11-12 · applied 2026-11-13'))
        self.assertEqual(e.fields['Affected'], 'screens/FORMAT.md, R5.2.1-1')
        self.assertEqual([l.split('.**')[0] for l in e.body if l], ['**Context', '**Decision', '**Automated', '**Affected', '**Status'])

    def test_an_empty_affected_drops_the_field(self):
        decisions.apply_decision(self.vault, self.log_now(), 1, [], today='2026-11-13')
        self.assertNotIn('Affected', self.log_now().entries[1].fields)

    def test_a_second_application_is_refused(self):
        decisions.apply_decision(self.vault, self.log_now(), 1, [])
        with self.assertRaisesRegex(decisions.RefError, 'already applied'):
            decisions.apply_decision(self.vault, self.log_now(), 1, ['W2'])

    def test_an_unknown_id_is_refused(self):
        with self.assertRaisesRegex(decisions.RefError, 'no such entry'):
            decisions.apply_decision(self.vault, self.log_now(), 7, [])


class UpdateRemoveTest(VaultCase):
    """update and remove: only an entry no commit ever held (heads, committed_heads) changes."""

    def setUp(self):
        super().setUp()
        for title in ('Incidents need a photo', 'Stock is counted twice', 'A third'):
            decisions.add_decision(self.vault, self.log_now(), title, 'C.', 'D.', affected=['W2'],
                                   source='reviews/2026-11-12-x-1.md#Q1 A question', today='2026-11-12')

    def test_update_rewrites_only_the_fields_given(self):
        decisions.update_decision(self.vault, self.log_now(), 2, set(), title='Stock is counted once', decision='W2 counts once.',
                                  affected=[], automated=True)
        e = self.log_now().entries[2]
        self.assertEqual((e.title, e.fields['Context'], e.fields['Decision'], e.fields['Automated'], e.fields['Status']),
                         ('Stock is counted once', 'C.', f'{W2_LINK} counts once.', 'true', RECORDED))
        self.assertNotIn('Affected', e.fields)
        self.assertEqual(e.fields['Source'], '[Q1](2026-11-12-x-1.md#Q1%20A%20question)')
        self.assertEqual(list(self.log_now().entries), [1, 2, 3])

    def test_update_refuses_an_entry_ever_committed_by_id_or_by_title(self):
        before = self.vault.text(decisions.LOG)
        for heads in ({(2, 'Something else')}, {(7, 'Stock is counted twice')}):
            with self.assertRaisesRegex(decisions.RefError, 'has been committed', msg=heads):
                decisions.update_decision(self.vault, self.log_now(), 2, heads, decision='Other.')
        with self.assertRaisesRegex(decisions.RefError, 'nothing.here'):
            decisions.update_decision(self.vault, self.log_now(), 2, set(), affected=['nothing.here'])
        with self.assertRaisesRegex(decisions.RefError, 'no such entry'):
            decisions.update_decision(self.vault, self.log_now(), 9, set(), decision='Other.')
        self.assertEqual(self.vault.text(decisions.LOG), before)

    def test_remove_drops_the_entry_and_lowers_next(self):
        decisions.remove_decision(self.vault, self.log_now(), 3, set())
        self.assertEqual(self.vault.text(decisions.LOG).count('### '), 2)
        self.assertEqual(self.log_now().next, 3)
        decisions.remove_decision(self.vault, self.log_now(), 1, set())
        log = self.log_now()
        self.assertEqual((list(log.entries), log.next), ([2], 3))
        self.assertNotIn('\n\n\n', self.vault.text(decisions.LOG))

    def test_remove_never_lowers_next_below_heads_next(self):
        decisions.remove_decision(self.vault, self.log_now(), 3, set(), head_next=4)
        self.assertEqual(self.log_now().next, 4)

    def test_remove_refuses_a_committed_entry_and_one_still_named(self):
        before = self.vault.text(decisions.LOG)
        with self.assertRaisesRegex(decisions.RefError, 'has been committed'):
            decisions.remove_decision(self.vault, self.log_now(), 2, {(2, 'Stock is counted twice')})
        with self.assertRaisesRegex(decisions.RefError, r'still named in docs/reviews/2026-11-12-x-1\.md:3'):
            decisions.remove_decision(self.vault, self.log_now(), 2, set(), [('docs/reviews/2026-11-12-x-1.md', 3, 2)])
        self.assertEqual(self.vault.text(decisions.LOG), before)


class GuardTest(VaultCase):
    EDITED = T05.replace('without signal', 'without a signal')

    def guard(self, changes, now, base=None):
        return decisions.guard(self.vault, changes, now, base if base is not None else decisions.parse_log(LOG_HEAD))

    def test_an_edited_page_without_an_entry_is_unbacked(self):
        out = self.guard({'design/T05-the-shift.md': (T05, self.EDITED)}, parse(1))
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith('UNBACKED: docs/design/T05-the-shift.md: changed since the merge-base'), out[0])
        self.assertIn('(no entry names it)', out[0])
        self.assertIn('/review-decisions', out[0])
        self.assertIn('the owner', out[0])
        self.assertNotIn('undo the edit', out[0])

    def test_link_e2e_and_hash_only_edits_are_not_changes(self):
        changes = {'design/T05-the-shift.md': (T05, T05.replace('Begin%20the%20shift', 'Begin%20the%20day').replace(
                       '[E2E: E5.2.1-1]', '[E2E: E5.2.1-1, E5.2.1-2]')),
                   'stories/worker.md': (STORY, STORY.replace('@454f', '@0a1b'))}
        self.assertEqual(self.guard(changes, parse(1)), [])

    def test_an_entry_applied_on_the_branch_backs_the_page(self):
        changes = {'architecture/operations.md': ('# Operations\n\n## Incidents\n\nText.\n', '# Operations\n\n## Incidents\n\nMore.\n')}
        self.assertEqual(self.guard(changes, parse(2, entry(1, APPLIED, INCIDENTS_LINK))), [])

    def test_an_entry_naming_a_rule_backs_its_theme_file(self):
        self.assertEqual(self.guard({'design/T05-the-shift.md': (T05, self.EDITED)}, parse(2, entry(1, APPLIED, 'R5.2.1-1'))), [])

    def test_an_entry_applied_at_the_merge_base_does_not_count(self):
        log = parse(2, entry(1, APPLIED, 'R5.2.1-1'))
        out = self.guard({'design/T05-the-shift.md': (T05, self.EDITED)}, log, log)
        self.assertEqual(len(out), 1)
        self.assertIn('(1 applied on main)', out[0])

    def test_a_recorded_entry_does_not_back(self):
        out = self.guard({'design/T05-the-shift.md': (T05, self.EDITED)}, parse(2, entry(1, RECORDED, 'R5.2.1-1')))
        self.assertEqual(len(out), 1)
        self.assertIn('(1 recorded)', out[0])

    def test_an_added_and_a_deleted_page_each_need_their_entry(self):
        self.write('screens/definitions/shift.new.md', '# shift.new\n')
        self.vault = decisions.Vault(self.docs)
        changes = {'screens/definitions/shift.new.md': (None, '# shift.new\n'), 'screens/definitions/shift.gone.md': ('# shift.gone\n', None)}
        out = self.guard(changes, parse(1))
        self.assertEqual([l.split(': ')[1] for l in out], ['docs/screens/definitions/shift.gone.md', 'docs/screens/definitions/shift.new.md'])
        backed = parse(2, entry(1, APPLIED, '[shift.new](../screens/definitions/shift.new.md), shift.gone'))
        self.assertEqual(self.guard(changes, backed), [])
        self.assertEqual(len(self.guard(changes, parse(2, entry(1, APPLIED, 'shift.gone')))), 1)

    def test_a_page_outside_the_guard_is_never_reported(self):
        self.assertEqual(self.guard({'reviews/x.md': ('a', 'b'), 'tools/x.md': ('a', 'b'), 'screens/shots/a.png': ('a', 'b')}, parse(1)), [])


class PendingTest(unittest.TestCase):
    QUESTIONS = FIXTURE['reviews/2026-11-12-x-1.md']

    def test_a_recorded_entry_is_pending(self):
        log = parse(3, entry(1, RECORDED, title='One'), entry(2, APPLIED, title='Two'))
        self.assertEqual(decisions.pending(log, {}), ['PENDING: decision 1 recorded, not applied: One'])

    def test_an_open_question_of_a_question_file_is_pending(self):
        self.assertEqual(decisions.pending(parse(1), {'reviews/2026-11-12-x-1.md': self.QUESTIONS}),
                         ['PENDING: docs/reviews/2026-11-12-x-1.md:3: Q1 A question is open'])

    def test_questions_alone_reports_an_open_question_not_a_recorded_entry(self):
        log = parse(3, entry(1, RECORDED, title='One'))
        self.assertEqual(decisions.open_questions({'reviews/2026-11-12-x-1.md': self.QUESTIONS}),
                         ['PENDING: docs/reviews/2026-11-12-x-1.md:3: Q1 A question is open'])
        self.assertEqual(decisions.unapplied(log), [f'PENDING: decision {1} recorded, not applied: One'])

    def test_a_review_file_is_not_a_question_file(self):
        rulings = 'reviews/2026-11-11-server-gate-rulings.md'
        self.assertEqual(decisions.pending(parse(1), {rulings: FIXTURE[rulings]}), [])

    def test_answered_and_decided_questions_are_not_pending(self):
        for status in ('answered', 'decision 3'):
            files = {'reviews/2026-11-12-x-1.md': self.QUESTIONS.replace('**Status.** open', f'**Status.** {status}')}
            self.assertEqual(decisions.pending(parse(1), files), [], status)


class TrimTest(unittest.TestCase):
    def test_trim_drops_the_entries_applied_at_the_merge_base(self):
        now = parse(5, entry(1, APPLIED, title='On main'), entry(2, RECORDED, title='Pending'), entry(3, APPLIED, title='Branch'),
                    entry(4, APPLIED, title='Also on main'))
        base = parse(5, entry(1, APPLIED, title='On main'), entry(3, RECORDED, title='Branch'), entry(4, APPLIED, title='Also on main'))
        lines, k = decisions.trim(now, base)
        self.assertEqual(k, 2)
        self.assertEqual('\n'.join(lines).rstrip('\n') + '\n',
                         log_text(5, entry(2, RECORDED, title='Pending'), entry(3, APPLIED, title='Branch')))
        self.assertEqual(decisions.trim(now, decisions.parse_log(OLD_HEAD)), (now.lines, 0))


class TwoBranchesTest(VaultCase):
    """Branches A and B start from the same main and both record entry 2; A merges first, B rebases."""
    A_FILE, B_FILE = 'reviews/2026-11-11-a-1.md', 'reviews/2026-11-12-b-1.md'
    A_QUESTIONS = '# Questions: feature/a run 1\n\n### Q1 Count the stock twice\n\n**Status.** decision 2\n'
    B_QUESTIONS = '# Questions: feature/b run 1\n\n### Q1 A worker\'s incident\n\n**Status.** decision 2\n'
    B_SOURCE = '[Q1](2026-11-12-b-1.md#Q1%20A%20worker\'s%20incident)'

    def setUp(self):
        super().setUp()
        self.write(self.A_FILE, self.A_QUESTIONS)
        self.write(self.B_FILE, self.B_QUESTIONS)
        self.vault = decisions.Vault(self.docs)
        self.one = entry(1, APPLIED, title='One', context='One.')
        self.a2 = entry(2, APPLIED, 'R5.2.1-1', title='Stock is counted twice', context='A count was wrong.')
        self.main = parse(3, self.one, self.a2)  # the merge-base after A merged

    def b(self, n):
        return entry(n, APPLIED, 'R5.2.1-1', title='Incidents need a photo', context='Workers record incidents without proof.').replace(
            '**Status.**', f'**Source.** {self.B_SOURCE}\n**Status.**')

    def kinds(self, log):
        return [p.split(': ')[2] for p in decisions.check(self.vault, log, None, self.main)]

    def test_b_keeping_its_own_2_is_reported_never_trimmed(self):
        now = parse(3, self.one, self.b(2))
        self.assertEqual([e.title for e in decisions.applied_on_branch(now, self.main)], ['Incidents need a photo'])
        lines, k = decisions.trim(now, self.main)
        self.assertEqual((k, '\n'.join(lines).rstrip('\n') + '\n'), (1, log_text(3, self.b(2))))
        problems = decisions.check(self.vault, now, None, self.main)
        self.assertEqual([p.split(': ')[2] for p in problems], ['id-on-main'])
        self.assertIn('just decisions renumber', problems[0])

    def test_both_2s_kept_are_reported(self):
        self.assertEqual(self.kinds(parse(3, self.one, self.a2, self.b(2))), ['duplicate-id', 'id-on-main'])

    def test_renumber_moves_b_s_entries_after_main_s(self):
        lines, files, moved, dropped = decisions.renumber(parse(3, self.one, self.a2, self.b(2)), self.main,
                                                          {self.B_FILE: (self.B_QUESTIONS, None)})
        text = '\n'.join(lines).rstrip('\n') + '\n'
        self.assertEqual(text, log_text(4, self.one, self.a2, self.b(3)))
        self.assertEqual((moved, dropped), ([(2, 3)], []))
        self.assertEqual(files, {self.B_FILE: self.B_QUESTIONS.replace('decision 2', 'decision 3')})
        now = decisions.parse_log(text)
        self.assertEqual([e.n for e in decisions.applied_on_branch(now, self.main)], [3])
        self.assertEqual(decisions.trim(now, self.main)[1], 2)
        self.assertEqual(self.kinds(now), [])
        self.assertEqual(decisions.renumber(now, self.main, {self.B_FILE: (files[self.B_FILE], None)})[1:], ({}, [], []))

    def test_renumber_after_b_kept_only_its_own(self):
        lines, _, moved, _ = decisions.renumber(parse(3, self.one, self.b(2)), self.main, {})
        self.assertEqual(('\n'.join(lines).rstrip('\n') + '\n', moved), (log_text(4, self.one, self.b(3)), [(2, 3)]))

    def test_renumber_refuses_conflict_markers_and_a_base_with_entries_without_next(self):
        with self.assertRaisesRegex(decisions.RefError, 'conflict'):
            decisions.renumber(decisions.parse_log(log_text(3, self.one) + '<<<<<<< HEAD\n' + self.a2 + '=======\n'
                                                   + self.b(2) + '>>>>>>> b\n'), self.main, {})
        with self.assertRaisesRegex(decisions.RefError, 'Next'):
            decisions.renumber(parse(3, self.b(2)), decisions.parse_log(log_text(3, self.one).replace(' Next: 3', '')), {})

    def test_renumber_rewrites_the_branch_s_references_and_only_those(self):
        b3 = entry(3, APPLIED, title='Photos are kept', context='Replaces decision 2; decision 1 stands.')
        spec = 'Per decision 2.\nMain\'s decision 2.\nDecisions 1, 2 and 3.\n'
        lines, files, moved, _ = decisions.renumber(parse(4, self.one, self.a2, self.b(2), b3), self.main,
                                                    {'docs/s.md': (spec, {0, 2})})
        self.assertEqual(moved, [(2, 3), (3, 4)])
        self.assertIn('**Context.** Replaces decision 3; decision 1 stands.', lines)
        self.assertEqual(files, {'docs/s.md': 'Per decision 3.\nMain\'s decision 2.\nDecisions 1, 3 and 4.\n'})

    def test_check_reports_a_reference_to_a_decision_no_log_held(self):
        now = parse(3, self.one, self.a2)
        self.assertEqual(decisions.check(self.vault, now, None, self.main, refs=[('docs/q.md', 5, 2)]), [])
        problems = decisions.check(self.vault, now, None, self.main, refs=[('docs/q.md', 5, 147)])
        self.assertEqual(problems, ["PROBLEM: docs/q.md:5: dangling-decision: decision 147, which neither the log nor "
                                    "main's log ever held"])

    def test_check_after_renumber_does_not_judge_ids_head_held_twice(self):
        b3 = entry(3, APPLIED, title='Photos are kept', context='Replaces decision 2.')
        head = parse(3, self.one, self.a2, self.b(2), b3.replace('### 3 ', '### 2 '))
        lines, _, _, _ = decisions.renumber(parse(3, self.one, self.a2, self.b(2), b3), self.main, {})
        self.assertEqual(decisions.check(self.vault, decisions.parse_log('\n'.join(lines)), head, self.main), [])

    def test_a_number_after_a_reference_is_no_decision(self):
        refs = lambda text: [n for _, n in decisions.decision_refs(text)]
        self.assertEqual(refs('decision 20, 4 shards'), [20])
        self.assertEqual(refs('decision 21 and 2026-11-12'), [21])
        self.assertEqual(refs('decision 2026-11-12'), [])
        self.assertEqual(refs('decisions 12 and 35; Decisions 1, 2 and 3; decisions 12, 24, and 30'), [12, 35, 1, 2, 3, 12, 24, 30])
        self.assertEqual(decisions.rewrite_refs('decision 2, 2 rows and decision 2 and 2026', {2: 9}),
                         'decision 9, 2 rows and decision 9 and 2026')

    def test_a_link_to_an_entry_follows_the_configured_log(self):
        decisions.configure(config.Paths(decision_log='docs/decision-log.md'))
        try:
            refs = lambda text: [n for _, n in decisions.decision_refs(text)]
            link = 'see [41](../decision-log.md#41%20Photos%20are%20kept)'
            self.assertEqual(refs(link), [41])
            self.assertEqual(refs('see [41](reviews/design-decision-log.md#41%20Photos)'), [])
            self.assertEqual(decisions.rewrite_refs(link, {41: 45}), link.replace('#41%20', '#45%20'))
            masked = decisions.masked_refs(parse(2, entry(1, context='Per `decision-log.md#41 x`.')).entries[1])
            self.assertIn('decision-log.md## x', masked)
        finally:
            decisions.configure(PATHS)
        self.assertEqual(refs('see [41](design-decision-log.md#41%20Photos)'), [41])

    def test_a_plural_reference_s_comma_list_is_every_id_of_it(self):
        refs = lambda text: [n for _, n in decisions.decision_refs(text)]
        self.assertEqual(refs('decisions 150, 47; Decisions 38, 41, 42 (R5.6-5)'), [150, 47, 38, 41, 42])
        self.assertEqual(refs('decisions 12, 2026-11-12'), [12])
        self.assertEqual(decisions.rewrite_refs('(decisions 38, 41, 42) and decision 41, 4 rows', {38: 142, 41: 145, 42: 146}),
                         '(decisions 142, 145, 146) and decision 145, 4 rows')

    def test_check_follows_entries_renumber_moved_in_a_chain(self):
        """main recorded 2; the branch's 2 and 3 (3 replacing 2) move to 3 and 4: HEAD's 3 is now another entry."""
        b3 = entry(3, APPLIED, title='Photos are kept', context='Replaces decision 2.')
        head = parse(4, self.one, self.a2, self.b(2), b3)
        lines, _, _, _ = decisions.renumber(parse(4, self.one, self.a2, self.b(2), b3), self.main, {})
        now = decisions.parse_log('\n'.join(lines))
        self.assertEqual(decisions.check(self.vault, now, head, self.main), [])
        edited = decisions.parse_log('\n'.join(lines).replace('Replaces decision 3.', 'Replaces nothing.'))
        self.assertEqual([p.split(': ')[2] for p in decisions.check(self.vault, edited, head, self.main)], ['edited'])

    def test_renumber_refuses_a_dirty_base_and_a_dangling_reference(self):
        with self.assertRaisesRegex(decisions.RefError, 'docs/q.md:3: decision 9'):
            decisions.renumber(parse(3, self.one, self.a2, self.b(2)), self.main, {}, [('docs/q.md', 3, 9)])
        with self.assertRaisesRegex(decisions.RefError, 'docs/s.md:1: decision 9'):
            decisions.renumber(parse(3, self.one, self.a2, self.b(2)), self.main, {'docs/s.md': ('See decision 9.', None)})
        with self.assertRaisesRegex(decisions.RefError, 'id 2 twice'):
            decisions.renumber(parse(3, self.b(2)), parse(3, self.one, self.a2, self.a2), {})

    def test_an_entry_main_trimmed_is_main_s_never_the_branch_s(self):
        """B forked when main's log held entry 1 and recorded b2; A recorded a2, trimmed 1 and merged. At the rebase
        stop B's side still holds 1: renumber drops it, the guard and trim never count it as B's."""
        fork = log_text(2, entry(1, APPLIED, 'R5.2.1-1', title='One', context='One.'))
        main = decisions.main_log(log_text(3, self.a2), [log_text(3, self.a2), fork])
        one = entry(1, APPLIED, 'R5.2.1-1', title='One', context='One.')
        now = parse(3, self.a2, one, self.b(2))
        self.assertEqual([e.title for e in decisions.applied_on_branch(now, main)], ['Incidents need a photo'])
        self.assertEqual([e.n for e in decisions.applied_on_branch(now, decisions.parse_log(log_text(3, self.a2)))], [1, 2])
        lines, files, moved, dropped = decisions.renumber(now, main, {self.B_FILE: (self.B_QUESTIONS, None)})
        self.assertEqual('\n'.join(lines).rstrip('\n') + '\n', log_text(4, self.a2, self.b(3)))
        self.assertEqual((moved, dropped), ([(2, 3)], [1]))
        self.assertEqual(files, {self.B_FILE: self.B_QUESTIONS.replace('decision 2', 'decision 3')})
        self.assertEqual(decisions.trim(parse(3, one, self.b(2)), main)[1], 1)
        problems = decisions.check(self.vault, parse(4, one, self.a2, self.b(3)), None, main)
        self.assertEqual([p.split(': ')[2] for p in problems], ['trimmed-on-main'])
        self.assertIn('just decisions trim', problems[0])
        edited = T05.replace('without signal', 'without a signal')
        out = decisions.guard(self.vault, {'design/T05-the-shift.md': (T05, edited)}, parse(3, self.a2, one), main)
        self.assertEqual(len(out), 1)
        self.assertIn('(2 applied on main, 1 applied on main)', out[0])

    def test_a_branch_entry_under_an_id_main_trimmed_is_the_branch_s(self):
        """main allotted 2 to a2 after B forked and trimmed it since: B's own 2 is another decision, kept, and moved."""
        main = decisions.main_log(log_text(3), [log_text(3, self.a2), log_text(2)])
        now = parse(3, self.b(2))
        self.assertEqual([e.n for e in decisions.applied_on_branch(now, main)], [2])
        self.assertEqual(decisions.trim(now, main)[1], 0)
        self.assertEqual([p.split(': ')[2] for p in decisions.check(self.vault, now, None, main)], ['id-on-main'])
        lines, _, moved, dropped = decisions.renumber(now, main, {})
        self.assertEqual(('\n'.join(lines).rstrip('\n') + '\n', moved, dropped), (log_text(4, self.b(3)), [(2, 3)], []))

    def test_main_s_old_header_holds_no_entries_so_ids_start_at_1(self):
        lines, _, moved, _ = decisions.renumber(parse(3, self.b(2)), decisions.parse_log(OLD_HEAD), {})
        self.assertEqual(('\n'.join(lines).rstrip('\n') + '\n', moved), (log_text(2, self.b(1)), [(2, 1)]))
        self.assertEqual(decisions.renumber(parse(2, self.b(1)), decisions.parse_log(OLD_HEAD), {})[2], [])


class ResolveLogTest(unittest.TestCase):
    """A rebase's conflict of the log, settled entry by entry: base the common ancestor, ours main's side, theirs the
    commit being replayed."""
    one = entry(1, APPLIED, title='One', context='One.')
    a2 = entry(2, APPLIED, title='Stock is counted twice', context='A.')
    b2 = entry(2, RECORDED, title='Incidents need a photo', context='B.')

    def heads(self, text):
        return [(e.n, e.title, e.status.value) for e in decisions.parse_log(text).order]

    def test_an_untrimmed_branch_side_is_never_copied_twice(self):
        text, said = decisions.resolve_log(log_text(2, self.one), log_text(3, self.one, self.a2), log_text(3, self.one, self.b2))
        self.assertEqual(self.heads(text), [(1, 'One', 'applied'), (2, 'Stock is counted twice', 'applied'),
                                            (2, 'Incidents need a photo', 'recorded')])
        self.assertEqual(said, {'main': 2, 'branch': [2], 'dropped': []})

    def test_the_commit_s_apply_of_an_entry_main_holds_unchanged_wins(self):
        base, ours = log_text(3, self.one, self.b2), log_text(3, self.one, self.b2, entry(3, APPLIED, title='M', context='M.'))
        theirs = log_text(3, self.one, self.b2.replace(RECORDED, APPLIED))
        self.assertEqual(self.heads(decisions.resolve_log(base, ours, theirs)[0]),
                         [(1, 'One', 'applied'), (2, 'Incidents need a photo', 'applied'), (3, 'M', 'applied')])

    def test_a_trim_on_either_side_stays(self):
        # main trimmed 1, the branch side still holds it as it was
        text, said = decisions.resolve_log(log_text(2, self.one), log_text(3, self.a2), log_text(3, self.one, self.b2))
        self.assertEqual((self.heads(text), said['dropped']), ([(2, 'Stock is counted twice', 'applied'), (2, 'Incidents need a photo', 'recorded')], [1]))
        # the commit trimmed 1, main left it as it was
        text, said = decisions.resolve_log(log_text(2, self.one), log_text(3, self.one, self.a2), log_text(3, self.b2))
        self.assertEqual((self.heads(text), said['dropped']), ([(2, 'Stock is counted twice', 'applied'), (2, 'Incidents need a photo', 'recorded')], [1]))

    def test_an_entry_both_sides_changed_differently_is_refused(self):
        base = log_text(2, entry(1, RECORDED, title='One', context='One.'))
        with self.assertRaisesRegex(decisions.RefError, 'both changed it'):
            decisions.resolve_log(base, log_text(2, entry(1, APPLIED, title='One', context='One.')),
                                  log_text(2, entry(1, 'recorded 2026-11-13', title='One', context='One.')))

    def test_a_side_with_conflict_markers_is_refused(self):
        with self.assertRaisesRegex(decisions.RefError, 'conflict markers'):
            decisions.resolve_log(LOG_HEAD, LOG_HEAD + '<<<<<<< HEAD\n', LOG_HEAD)


class CheckTest(VaultCase):
    def kinds(self, now, head=None, base=None):
        problems = decisions.check(self.vault, now if not isinstance(now, str) else decisions.parse_log(now),
                                   decisions.parse_log(head) if head is not None else None,
                                   decisions.parse_log(base) if base is not None else None)
        return [p.split(': ')[2] for p in problems]

    def test_a_clean_log(self):
        text = log_text(3, entry(1, APPLIED, f'R5.2.1-1, {W2_LINK}'), entry(2, RECORDED, 'screens/FORMAT.md'))
        self.assertEqual(self.kinds(text, text, LOG_HEAD), [])
        self.assertEqual(self.kinds(LOG_HEAD), [])

    def test_a_header_without_next(self):
        self.assertEqual(self.kinds(LOG_HEAD.replace(' Next: 1', '')), ['header'])

    def test_ids_unique_ascending_and_below_next(self):
        self.assertIn('duplicate-id', self.kinds(log_text(3, entry(1), entry(1))))
        self.assertIn('out-of-order', self.kinds(log_text(4, entry(2), entry(1))))
        self.assertEqual(self.kinds(log_text(3, entry(3))), ['id-not-below-next'])

    def test_malformed_entries_and_statuses(self):
        self.assertEqual(self.kinds(log_text(2, entry(1, automated='maybe'))), ['malformed-entry'])
        self.assertEqual(self.kinds(log_text(2, entry(1).replace('**Context.** Workers record incidents without proof.\n', ''))),
                         ['malformed-entry'])
        self.assertEqual(self.kinds(log_text(2, entry(1).replace('**Automated.** false', '**Automated.** false\n**Automated.** true'))),
                         ['malformed-entry'])
        self.assertEqual(self.kinds(log_text(2, entry(1, 'applied yesterday'))), ['malformed-status'])

    def test_an_edited_applied_entry(self):
        head = log_text(2, entry(1, APPLIED))
        self.assertEqual(self.kinds(head.replace('carries a photo', 'carries two photos'), head), ['edited'])
        self.assertEqual(self.kinds(head.replace('**Status.**', '**Affected.** W2\n**Status.**'), head), ['edited'])

    def test_an_edited_recorded_entry(self):
        head = log_text(2, entry(1, RECORDED))
        self.assertEqual(self.kinds(head.replace('without proof', 'with no proof'), head), ['edited'])
        self.assertEqual(self.kinds(head.replace('**Status.**', '**Affected.** W2\n**Status.**'), head), [])  # applying sets these
        self.assertEqual(self.kinds(head.replace(RECORDED, APPLIED), head), [])

    def test_removed_unless_applied_at_the_merge_base(self):
        head = log_text(3, entry(1, APPLIED), entry(2))
        self.assertEqual(self.kinds(log_text(3, entry(2)), head, LOG_HEAD), ['removed'])
        self.assertEqual(self.kinds(log_text(3, entry(2)), head, log_text(2, entry(1, APPLIED))), [])  # a trim

    def test_names_and_links_of_new_and_recorded_entries_resolve(self):
        self.assertEqual(self.kinds(log_text(2, entry(1, RECORDED, 'R5.2.1-1, nothing.here'))), ['unknown-name'])
        self.assertEqual(self.kinds(log_text(2, entry(1, RECORDED, '[W2](../stories/worker.md#W2%20—%20Gone)'))), ['dead-link'])
        head = log_text(2, entry(1, APPLIED, 'nothing.here'))
        self.assertEqual(self.kinds(head, head), [])  # applied in HEAD: compared with HEAD only

    def test_a_deleted_page_named_on_the_branch_resolves_through_gone(self):
        log = decisions.parse_log(log_text(2, entry(1, RECORDED, 'shift.gone')))
        self.assertEqual(decisions.check(self.vault, log, None, None, gone=frozenset({'screens/definitions/shift.gone.md'})), [])

    def test_a_link_recorded_to_a_page_deleted_on_the_branch_is_not_dead(self):
        link = '[shift.gone](../screens/definitions/shift.gone.md)'  # linked at recording, while the page existed
        log = decisions.parse_log(log_text(2, entry(1, APPLIED, 'shift.gone', context=f'{link} is unused.')))
        self.assertEqual(decisions.check(self.vault, log, None, None, gone=frozenset({'screens/definitions/shift.gone.md'})), [])
        self.assertEqual([p.split(': ')[2] for p in decisions.check(self.vault, log, None, None)], ['dead-link', 'unknown-name'])

    def test_the_old_header_is_a_base_log_with_no_entries(self):
        old = decisions.parse_log(OLD_HEAD)
        self.assertEqual((old.next, old.entries), (None, {}))
        self.assertEqual(decisions.parse_log(''), decisions.Log([''], None, {}))
        self.assertEqual(self.kinds(LOG_HEAD, OLD_HEAD, OLD_HEAD), [])


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = write_vault(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *args, expect=0):
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'decisions.py'), '--docs', self.docs, *args],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, expect, r.stderr + r.stdout)
        return r.stdout + r.stderr  # errors go to stderr

    def test_record_show_list_apply_and_pending(self):
        self.assertEqual(self.run_tool('add-decision', '--title', 'Incidents need a photo', '--context', 'C.', '--decision', 'D.',
                                       '--affected', 'W2, R5.2.1-1'), '1\n')
        self.assertEqual(self.run_tool('add-decision', '--title', 'Second', '--context', 'C.', '--decision', 'D.', '--automated'), '2\n')
        self.assertTrue(self.run_tool('show', '1').startswith('### 1 Incidents need a photo\n\n**Context.** C.\n'))
        self.assertEqual(len(self.run_tool('list').splitlines()), 2)
        self.assertIn('no such entry', self.run_tool('show', '9', expect=2))
        out = self.run_tool('pending', expect=1)
        self.assertEqual(out.splitlines(), ['PENDING: decision 1 recorded, not applied: Incidents need a photo',
                                            'PENDING: decision 2 recorded, not applied: Second',
                                            'PENDING: docs/reviews/2026-11-12-x-1.md:3: Q1 A question is open'])
        self.run_tool('apply-decision', '--id', '1', '--affected', 'screens/FORMAT.md')
        self.run_tool('apply-decision', '--id', '2', '--affected', '')
        self.assertIn('already applied', self.run_tool('apply-decision', '--id', '1', '--affected', '', expect=2))
        path = os.path.join(self.docs, 'reviews/2026-11-12-x-1.md')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text.replace('**Status.** open', '**Status.** answered'))
        self.assertEqual(self.run_tool('pending'), 'OK\n')

    def test_pending_questions_reports_only_the_open_questions(self):
        self.run_tool('add-decision', '--title', 'Incidents need a photo', '--context', 'C.', '--decision', 'D.', '--affected', 'W2, R5.2.1-1')
        self.assertEqual(self.run_tool('pending', '--questions', expect=1).splitlines(),
                         ['PENDING: docs/reviews/2026-11-12-x-1.md:3: Q1 A question is open'])
        path = os.path.join(self.docs, 'reviews/2026-11-12-x-1.md')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text.replace('**Status.** open', '**Status.** answered'))
        self.assertEqual(self.run_tool('pending', '--questions'), 'OK\n')
        self.assertIn('Incidents need a photo', self.run_tool('pending', expect=1))

    def test_an_unknown_name_is_an_error(self):
        self.assertIn('error: no such page: nothing.here',
                      self.run_tool('add-decision', '--title', 'T', '--context', 'C.', '--decision', 'D.', '--affected', 'nothing.here', expect=2))

    def test_a_story_defined_twice_is_an_error_not_a_traceback(self):
        with open(os.path.join(self.docs, 'stories/other.md'), 'w', encoding='utf-8') as f:
            f.write('# Other\n\n### W2 — Another\n')
        out = self.run_tool('list', expect=2)
        self.assertTrue(out.startswith('error: "W2" is defined twice'), out)
        self.assertNotIn('Traceback', out)

    def test_log_is_refused(self):
        self.run_tool('--log', 'reviews/design-decision-log.md', 'list', expect=2)


class GitInputsTest(unittest.TestCase):
    """git_inputs, the one place the tool reads git, over a small repository whose origin/main is its first commit."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.docs = write_vault(self.root)
        self.git('init', '-q', '-b', 'main')
        self.commit('main')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', self.root, '-c', 'user.email=t@t', '-c', 'user.name=t', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *args],
                              check=True, capture_output=True, text=True).stdout

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', message)

    def put(self, rel, text):
        path = os.path.join(self.docs, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)

    def test_the_merge_base_the_logs_and_the_changed_guarded_pages(self):
        committed_log = log_text(2, entry(1))
        self.put('reviews/design-decision-log.md', committed_log)
        self.put('stories/worker.md', STORY.replace('Count.', 'Count it.'))
        self.commit('branch')
        self.put('design/T05-the-shift.md', T05.replace('without signal', 'without a signal'))
        self.put('screens/definitions/shift.new — ñ.md', '# new\n')
        os.remove(os.path.join(self.docs, 'screens/components/incident_row.md'))
        self.put('reviews/y.md', 'not guarded\n')
        self.put('screens/shots/a.png', 'not guarded\n')
        inputs = decisions.git_inputs(self.root, 'docs')
        self.assertEqual(inputs.base, self.git('rev-parse', 'origin/main').strip())
        self.assertEqual((inputs.head_log, inputs.base_log), (committed_log, LOG_HEAD))
        self.assertEqual(inputs.changes, {
            'design/T05-the-shift.md': (T05, T05.replace('without signal', 'without a signal')),
            'stories/worker.md': (STORY, STORY.replace('Count.', 'Count it.')),
            'screens/definitions/shift.new — ñ.md': (None, '# new\n'),
            'screens/components/incident_row.md': ('# incident_row\n', None),
        })
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'decisions.py'), '--docs', self.docs, 'guard'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(len(r.stdout.splitlines()), 4, r.stdout)

    def test_renumber_after_a_rebase(self):
        one, a2 = entry(1, APPLIED, title='One', context='One.'), entry(2, APPLIED, title='Stock is counted twice', context='A.')
        b2 = entry(2, RECORDED, title='Incidents need a photo', context='B.')
        self.put('reviews/design-decision-log.md', log_text(3, one, a2))
        self.commit('main, after branch A merged')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.put('reviews/design-decision-log.md', log_text(3, one, a2, b2))  # the conflict resolved: main's, then B's
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'decisions.py'), '--docs', self.docs, 'renumber'],
                           capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, 'decision 2 is now 3\n1 entries renumbered\n'), r.stderr)
        with open(os.path.join(self.docs, 'reviews/design-decision-log.md'), encoding='utf-8') as f:
            self.assertEqual(f.read(), log_text(4, one, a2, b2.replace('### 2 ', '### 3 ')))

    def test_update_and_remove_refuse_what_a_commit_ever_held(self):
        def tool(*args):
            return subprocess.run([sys.executable, '-I', os.path.join(HERE, 'decisions.py'), '--docs', self.docs, *args],
                                  capture_output=True, text=True)
        self.put('reviews/design-decision-log.md', log_text(2, entry(1)))
        self.commit('entry 1 committed')
        self.put('reviews/design-decision-log.md', log_text(4, entry(1), entry(2, title='Two'), entry(3, title='Three')))
        r = tool('update', '1', '--decision', 'Other.')
        self.assertEqual(r.returncode, 2)
        self.assertIn('has been committed', r.stderr)
        self.assertEqual(tool('update', '2', '--decision', 'Other.').returncode, 0)
        self.put('reviews/y.md', 'See decision 3.\n')
        r = tool('remove', '3')
        self.assertEqual(r.returncode, 2)
        self.assertIn('still named in docs/reviews/y.md:1', r.stderr)
        os.remove(os.path.join(self.docs, 'reviews/y.md'))
        self.assertEqual(tool('remove', '3').returncode, 0)
        self.assertEqual(tool('remove', '2').returncode, 0)
        with open(os.path.join(self.docs, 'reviews/design-decision-log.md'), encoding='utf-8') as f:
            self.assertEqual(f.read(), log_text(2, entry(1)))  # Next back to HEAD's
        self.assertEqual(tool('remove', '1').returncode, 2)

    def renumber_cli(self):
        return subprocess.run([sys.executable, '-I', os.path.join(HERE, 'decisions.py'), '--docs', self.docs, 'renumber'],
                              capture_output=True, text=True)

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding='utf-8') as f:
            return f.read()

    def test_renumber_waits_for_the_rebase_then_drops_what_main_trimmed_and_rewrites_every_reference(self):
        """B forked when main held entry 1 and recorded 2 and 3, 3 replacing 2, and a record citing both; main recorded
        its own 2, cited it in a page, and trimmed 1. Renumber refuses at the rebase's stop; after it, it drops 1,
        moves 2 and 3, and rewrites B's references and only B's: main's line citing its own 2 stays."""
        one = entry(1, APPLIED, title='One', context='One.')
        a2, b2 = entry(2, APPLIED, title='Stock is counted twice', context='A.'), entry(2, RECORDED, title='Incidents need a photo', context='B.')
        b3 = entry(3, RECORDED, title='Photos are kept', context='Replaces decision 2.')
        self.put('reviews/design-decision-log.md', log_text(2, one))
        self.put('superpowers/specs/x.md', '# X\n\nIntro.\n')
        self.commit('main, the fork point')
        fork = self.git('rev-parse', 'HEAD').strip()
        self.put('reviews/design-decision-log.md', log_text(3, a2))
        self.put('superpowers/specs/x.md', '# X\n\nIntro, per decision 2.\n')
        self.commit('main, after branch A merged (it trimmed 1)')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.git('checkout', '-q', '-b', 'b', fork)
        self.put('reviews/design-decision-log.md', log_text(4, one, b2, b3))
        self.put('superpowers/specs/b.md', '# B\n\nDecisions 2 and 3 hold; see [3](../../reviews/design-decision-log.md#3%20Photos%20are%20kept).\n')
        self.commit('branch B records 2 and 3')
        r = subprocess.run(['git', '-C', self.root, '-c', 'user.email=t@t', '-c', 'user.name=t', '-c', 'core.hooksPath=/dev/null',
                            'rebase', 'origin/main'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0, 'the log conflicts')
        self.assertEqual(decisions.git_inputs(self.root, 'docs').main_logs, [log_text(3, a2), log_text(2, one), LOG_HEAD])
        self.put('reviews/design-decision-log.md', log_text(3, a2, one, b2, b3))
        r = self.renumber_cli()
        self.assertEqual(r.returncode, 2)
        self.assertIn('a rebase is in progress', r.stderr)
        self.git('add', '-A')
        self.git('-c', 'core.editor=true', 'rebase', '--continue')
        r = self.renumber_cli()
        self.assertEqual((r.returncode, r.stdout), (0, 'decision 1 dropped: applied on main and trimmed there\n'
                                                       'decision 2 is now 3\ndecision 3 is now 4\n2 entries renumbered\n'), r.stderr)
        self.assertEqual(self.read('docs/reviews/design-decision-log.md'),
                         log_text(5, a2, b2.replace('### 2 ', '### 3 '), b3.replace('### 3 ', '### 4 ').replace('decision 2', 'decision 3')))
        self.assertEqual(self.read('docs/superpowers/specs/b.md'),
                         '# B\n\nDecisions 3 and 4 hold; see [3](../../reviews/design-decision-log.md#4%20Photos%20are%20kept).\n')
        self.assertEqual(self.read('docs/superpowers/specs/x.md'), '# X\n\nIntro, per decision 2.\n')

    def test_renumber_refuses_a_base_that_does_not_validate_until_the_branch_fixes_it(self):
        a2, b2 = entry(2, APPLIED, title='Stock is counted twice', context='A.'), entry(2, RECORDED, title='Incidents need a photo', context='B.')
        self.put('reviews/design-decision-log.md', log_text(3, entry(1, APPLIED, title='One', context='One.'), a2))
        self.put('reviews/q.md', '# Questions: x\n\n### Q1 Q\n\n**Status.** decision 147\n')
        self.commit('main, citing a decision its log never held')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        before = log_text(3, entry(1, APPLIED, title='One', context='One.'), a2, b2)
        self.put('reviews/design-decision-log.md', before)
        r = self.renumber_cli()
        self.assertEqual(r.returncode, 2)
        self.assertIn('docs/reviews/q.md:5: decision 147', r.stderr)
        self.assertEqual(self.read('docs/reviews/design-decision-log.md'), before)
        self.put('reviews/q.md', '# Questions: x\n\n### Q1 Q\n\n**Status.** pending entry 147 of feature/y\n')  # fixed on the branch
        r = self.renumber_cli()
        self.assertEqual((r.returncode, r.stdout), (0, 'decision 2 is now 3\n1 entries renumbered\n'), r.stderr)

    def test_a_rebase_with_two_stops_resolved_then_renumbered(self):
        """B forked when main held 1 and never trimmed; it recorded 2, then applied it; main recorded its own 2. Each
        replayed commit conflicts on the log: resolve at each stop, continue, then renumber; check is clean."""
        one = entry(1, APPLIED, title='One', context='One.')
        a2 = entry(2, APPLIED, title='Stock is counted twice', context='A.')
        b2 = entry(2, RECORDED, title='Incidents need a photo', context='B.')
        self.put('reviews/design-decision-log.md', log_text(2, one))
        self.commit('main, the fork point')
        fork = self.git('rev-parse', 'HEAD').strip()
        self.put('reviews/design-decision-log.md', log_text(3, one, a2))
        self.commit('main records its 2')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.git('checkout', '-q', '-b', 'b', fork)
        self.put('reviews/design-decision-log.md', log_text(3, one, b2))
        self.put('superpowers/specs/b.md', '# B\n\nPer decision 2.\n')
        self.commit('B records 2')
        self.put('reviews/design-decision-log.md', log_text(3, one, b2.replace(RECORDED, APPLIED)))
        self.commit('B applies 2')
        rebase = ['git', '-C', self.root, '-c', 'user.email=t@t', '-c', 'user.name=t', '-c', 'core.hooksPath=/dev/null',
                  '-c', 'core.editor=true']
        resolve = [sys.executable, '-I', os.path.join(HERE, 'decisions.py'), '--docs', self.docs, 'resolve']
        r = subprocess.run(rebase + ['rebase', 'origin/main'], capture_output=True, text=True)
        stops = 0
        while r.returncode != 0:
            stops += 1
            self.assertLess(stops, 4, r.stdout + r.stderr)
            out = subprocess.run(resolve, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            r = subprocess.run(rebase + ['rebase', '--continue'], capture_output=True, text=True)
        self.assertGreaterEqual(stops, 1)
        r = self.renumber_cli()
        self.assertEqual((r.returncode, r.stdout), (0, 'decision 2 is now 3\n1 entries renumbered\n'), r.stderr)
        self.assertEqual(self.read('docs/reviews/design-decision-log.md'),
                         log_text(4, one, a2, b2.replace(RECORDED, APPLIED).replace('### 2 ', '### 3 ')))
        self.assertEqual(self.read('docs/superpowers/specs/b.md'), '# B\n\nPer decision 3.\n')

    def test_resolve_refuses_outside_a_rebase(self):
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'decisions.py'), '--docs', self.docs, 'resolve'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('no rebase is in progress', r.stderr)

    def test_no_origin_main_is_an_error(self):
        self.git('update-ref', '-d', 'refs/remotes/origin/main')
        with self.assertRaisesRegex(decisions.RefError, 'no origin/main'):
            decisions.git_inputs(self.root, 'docs')

    def test_the_merge_base_is_with_the_configs_base(self):
        path = os.path.join(self.root, 'omc', 'config.yaml')
        with open(path, encoding='utf-8') as f:
            text = f.read()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text.replace('base: main\n', 'base: develop\n'))
        self.commit('develop is the base')
        self.git('update-ref', 'refs/remotes/origin/develop', 'HEAD')
        self.commit('branch')
        inputs = decisions.git_inputs(self.root, 'docs')
        self.assertEqual(inputs.base, self.git('rev-parse', 'origin/develop').strip())
        self.git('update-ref', '-d', 'refs/remotes/origin/develop')
        with self.assertRaisesRegex(decisions.RefError, 'no origin/develop'):
            decisions.git_inputs(self.root, 'docs')


class ConfigTest(unittest.TestCase):
    """The log and the guarded pages from omc/config.yaml's paths, over omc_fixtures.Repo (origin/main its first
    commit, `protected: []`, the log docs/decision-log.md, which it does not hold), the tool run as `just decisions`
    runs it: from the repository's root, no --docs."""

    def setUp(self):
        self.repo = omc_fixtures.Repo.make_repo()

    def tearDown(self):
        self.repo.cleanup()

    def run_tool(self, *args):
        return subprocess.run([sys.executable, '-I', os.path.join(HERE, 'decisions.py'), *args], cwd=self.repo.work,
                              env=self.repo.env, capture_output=True, text=True)

    def configure(self, **paths):
        self.repo.commit('omc/config.yaml', config_text(config.Paths(**paths)), 'config')
        self.repo.git('update-ref', 'refs/remotes/origin/main', 'HEAD')

    def test_no_log_no_protected_check_passes(self):
        for gone in (False, True):  # with origin/main, then without: an idle tool reads no git
            if gone:
                self.repo.git('update-ref', '-d', 'refs/remotes/origin/main')
            for verb in (['check'], ['guard'], ['pending'], ['pending', '--questions'], ['list']):
                r = self.run_tool(*verb)
                self.assertEqual((r.returncode, r.stdout, r.stderr), (0, '', ''), (verb, gone))

    def test_no_log_with_protected_is_refused(self):
        self.configure(protected=('docs/design/**/*.md',))
        r = self.run_tool('check')
        self.assertEqual((r.returncode, r.stderr), (2, 'error: no such log: docs/decision-log.md\n'), r.stdout)

    def test_guarded_from_config(self):
        self.configure(protected=('spec/**/*.md',), decision_log='decision-log.md')
        self.repo.commit('decision-log.md', LOG_HEAD, 'the log')
        self.repo.commit('spec/a.md', '# A\n', 'a guarded page')
        self.repo.commit('docs/design/T05-the-shift.md', T05, 'a page the config does not guard')
        self.repo.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.repo.write('spec/a.md', '# A, edited\n')
        self.repo.write('docs/design/T05-the-shift.md', T05.replace('without signal', 'without a signal'))
        r = self.run_tool('guard')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(len(r.stdout.splitlines()), 1, r.stdout)
        self.assertTrue(r.stdout.startswith('UNBACKED: spec/a.md: changed since the merge-base'), r.stdout)
        decisions.configure(config.Paths(protected=('spec/**/*.md',), decision_log='decision-log.md'))
        try:
            self.assertEqual((decisions.VAULT, decisions.LOG), ('', 'decision-log.md'))
            self.assertTrue(decisions.guarded('spec/a.md') and decisions.guarded('spec/x/b.md'))
            self.assertFalse(decisions.guarded('docs/design/T05-the-shift.md') or decisions.guarded('spec/a.yaml'))
        finally:
            decisions.configure(PATHS)

    def test_protected_outside_vault_refused(self):
        self.configure(protected=('docs/design/**/*.md', 'spec/**'))
        for verb in (['check'], ['list'], ['add-decision', '--title', 'T', '--context', 'C.', '--decision', 'D.']):
            r = self.run_tool(*verb)
            self.assertEqual((r.returncode, r.stdout, r.stderr),
                             (2, '', "error: paths.protected 'spec/**' lies outside the vault docs/ (the folder of "
                                     'paths.decision_log)\n'), verb)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'integrity.py')], cwd=self.repo.work,
                           env=self.repo.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("paths.protected 'spec/**' lies outside the vault docs/", r.stderr)

    def test_questions_outside_vault_refused(self):
        self.configure(decision_log='notes/log.md')  # questions stays docs/reviews/
        r = self.run_tool('check')
        self.assertEqual((r.returncode, r.stderr), (2, "error: paths.questions 'docs/reviews/' lies outside the vault "
                                                       'notes/ (the folder of paths.decision_log)\n'), r.stdout)

    def test_themes_from_config(self):
        self.configure(protected=('docs/**/*.md',), themes=('docs/rules/*.md',))
        self.repo.commit('docs/decision-log.md', LOG_HEAD, 'the log')
        self.repo.write('docs/rules/shift.md', T05)  # not design/T<nn>-*.md: a theme file only through paths.themes
        self.repo.write('docs/design/T05-the-shift.md', T05.replace('R5.2.1-1', 'R5.2.1-2'))  # no theme file here
        r = self.run_tool('add-decision', '--title', 'T', '--context', 'C.', '--decision', 'D.', '--affected', 'R5.2.1-1')
        self.assertEqual((r.returncode, r.stdout), (0, '1\n'), r.stderr)
        r = self.run_tool('add-decision', '--title', 'U', '--context', 'C.', '--decision', 'D.', '--affected', 'R5.2.1-2')
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn('no such page: R5.2.1-2', r.stderr)

    def test_log_path_from_config(self):
        self.configure(protected=('notes/pages/*.md',), decision_log='notes/log.md', questions='notes/')
        self.repo.commit('notes/log.md', LOG_HEAD, 'the log')
        self.repo.write('notes/q.md', FIXTURE['reviews/2026-11-12-x-1.md'])
        r = self.run_tool('add-decision', '--title', 'T', '--context', 'C.', '--decision', 'D.')
        self.assertEqual((r.returncode, r.stdout), (0, '1\n'), r.stderr)
        with open(os.path.join(self.repo.work, 'notes', 'log.md'), encoding='utf-8') as f:
            self.assertIn('### 1 T\n', f.read())
        r = self.run_tool('pending')
        self.assertEqual(r.stdout.splitlines(), ['PENDING: decision 1 recorded, not applied: T',
                                                 'PENDING: notes/q.md:3: Q1 A question is open'], r.stderr)
        r = self.run_tool('check')
        self.assertEqual((r.returncode, r.stdout), (0, 'OK\n'), r.stderr)


if __name__ == '__main__':
    unittest.main()
