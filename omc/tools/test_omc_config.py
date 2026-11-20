"""Tests of omc/tools/config.py, the pipeline's config. Run from the repository root:
UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -X pycache_prefix=.cache/pycache omc/tools/test_omc_config.py
The real omc/config.yaml is read in place; the refusals read a temporary root's omc/config.yaml."""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))

GOOD = '''base: main
branch_prefix: feature/
orchestrator-model: opus
ask_for_provider_handoff: false
models:
  max: fable
  medium: opus
  low: sonnet
complexity:
  simple: low
  medium: medium
  high: orchestrator
gitnexus:
  origin: https://example.invalid/GitNexus.git
  commit: 0123456789abcdef0123456789abcdef01234567
'''


class ConfigTest(unittest.TestCase):

    def load_text(self, text):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, 'omc'))
            with open(os.path.join(root, 'omc', 'config.yaml'), 'w', encoding='utf-8') as f:
                f.write(text)
            return config.load(root)

    def assertRefused(self, text, *words):
        with self.assertRaises(config.Refused) as caught:
            self.load_text(text)
        for word in words:
            self.assertIn(word, str(caught.exception))

    def test_the_real_config_loads(self):
        cfg = config.load(REPO)
        self.assertEqual((cfg.base, cfg.branch_prefix), ('main', 'feature/'))
        self.assertEqual(cfg.orchestrator_model, 'opus')
        self.assertIs(cfg.ask_for_provider_handoff, False)
        self.assertEqual(cfg.tiers, {'max': 'fable', 'medium': 'opus', 'low': 'sonnet'})
        self.assertEqual(cfg.complexity, {'simple': 'low', 'medium': 'medium', 'high': 'orchestrator'})

    def test_the_roles(self):
        self.assertEqual(config.ROLES, ('orchestrator', 'harden', 'harden-repeat', 'simple', 'medium', 'high'))
        cfg = config.load(REPO)
        self.assertEqual({role: config.models(cfg, role)['model'] for role in config.ROLES},
                         {'orchestrator': 'opus', 'harden': 'fable', 'harden-repeat': 'opus', 'simple': 'sonnet',
                          'medium': 'opus', 'high': 'opus'})

    def test_a_complexity_resolves_through_its_tier(self):
        cfg = self.load_text(GOOD.replace('orchestrator-model: opus', 'orchestrator-model: big')
                             .replace('  medium: opus', '  medium: mid'))
        self.assertEqual(config.models(cfg, 'high'), {'role': 'high', 'model': 'big', 'effort': ''})
        self.assertEqual(config.models(cfg, 'medium'), {'role': 'medium', 'model': 'mid', 'effort': ''})
        self.assertEqual(config.models(cfg, 'simple'), {'role': 'simple', 'model': 'sonnet', 'effort': ''})
        self.assertEqual(config.models(cfg, 'orchestrator'), {'role': 'orchestrator', 'model': 'big', 'effort': ''})
        self.assertEqual(config.models(cfg, 'harden'), {'role': 'harden', 'model': 'fable', 'effort': ''})
        # every later pass of ▣ harden on the `medium` tier, whatever the complexity `medium` maps to
        cfg = self.load_text(GOOD.replace('  medium: opus', '  medium: mid').replace('  medium: medium', '  medium: low'))
        self.assertEqual(config.models(cfg, 'harden-repeat'), {'role': 'harden-repeat', 'model': 'mid', 'effort': ''})

    def test_a_cheap_model_is_refused(self):
        self.assertEqual(self.load_text(GOOD).tiers['low'], 'sonnet')
        for word in ('haiku', 'mini', 'nano', 'flash'):
            for name, text in (('tier', GOOD.replace('  low: sonnet', f'  low: claude-{word}')),
                               ('orchestrator', GOOD.replace('orchestrator-model: opus',
                                                             f'orchestrator-model: {word}-1'))):
                with self.subTest(word=word, row=name):
                    self.assertRefused(text, word, 'cheap')

    def test_a_complexity_that_is_no_tier_is_refused(self):
        self.assertRefused(GOOD.replace('  simple: low', '  simple: tiny'), 'simple', 'tiny')
        self.assertRefused(GOOD.replace('  high: orchestrator', '  high: opus'), 'high', 'opus')

    def test_a_missing_complexity_or_tier_is_refused(self):
        self.assertRefused(GOOD.replace('  high: orchestrator\n', ''), 'high')
        self.assertRefused(GOOD.replace('  max: fable\n', ''), 'max')
        self.assertRefused(GOOD.replace('  medium: opus\n', '').replace('  medium: medium', '  medium: low'), 'medium')
        self.assertRefused(GOOD.replace('orchestrator-model: opus\n', ''), 'orchestrator-model')
        self.assertRefused(GOOD.replace('base: main\n', ''), 'base')

    def test_the_handoff_flag(self):
        self.assertIs(self.load_text(GOOD.replace('ask_for_provider_handoff: false\n', '')).ask_for_provider_handoff,
                      False)
        self.assertIs(self.load_text(GOOD.replace('handoff: false', 'handoff: true')).ask_for_provider_handoff,
                      True)
        for value in ('yes please', '1', '"true"'):
            with self.subTest(value=value):
                self.assertRefused(GOOD.replace('handoff: false', f'handoff: {value}'), 'ask_for_provider_handoff')

    def test_a_missing_or_bad_file_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(config.Refused) as caught:
                config.load(root)
            self.assertIn('config.yaml', str(caught.exception))
        self.assertRefused('base: [main\n', 'YAML')
        self.assertRefused('- a list\n', 'mapping')

    def test_the_gitnexus_pin_is_read(self):
        cfg = self.load_text(GOOD)
        self.assertEqual((cfg.gitnexus_origin, cfg.gitnexus_commit),
                         ('https://example.invalid/GitNexus.git', '0123456789abcdef0123456789abcdef01234567'))
        real = config.load(REPO)
        self.assertEqual(real.gitnexus_origin, 'https://github.com/chris-husse/GitNexus.git')
        self.assertRegex(real.gitnexus_commit, '^[0-9a-f]{40}$')

    def test_a_short_or_missing_pin_is_refused(self):
        pin = '  commit: 0123456789abcdef0123456789abcdef01234567\n'
        for name, text in (('short', GOOD.replace(pin, '  commit: "0123456"\n')),
                           ('upper', GOOD.replace(pin, pin.upper().replace('COMMIT', 'commit'))),
                           ('missing', GOOD.replace(pin, ''))):
            with self.subTest(name=name):
                self.assertRefused(text, 'gitnexus commit is not a full sha')
        self.assertRefused(GOOD.replace('  origin: https://example.invalid/GitNexus.git\n', ''), 'gitnexus origin')
        self.assertRefused(GOOD.split('gitnexus:')[0], 'no gitnexus mapping')

    def test_models_refuses_another_role(self):
        cfg = config.load(REPO)
        for role in ('design', 'design-repeat', 'plan', 'review', 'cheap', 'max'):
            with self.subTest(role=role):
                with self.assertRaises(config.Refused):
                    config.models(cfg, role)

    def test_paths_default_empty(self):
        defaults = config.Paths(protected=(), screenshots=(), baselines=(), briefs='tasks/',
                                specs='docs/superpowers/specs/', plans='docs/superpowers/plans/',
                                decision_log='docs/decision-log.md', questions='docs/reviews/', themes=())
        self.assertEqual(self.load_text(GOOD).paths, defaults)
        if not os.path.exists(os.path.join(REPO, 'omc', 'VERSION')):  # the generic file v2 ships; an installed copy's
            self.assertEqual(config.load(REPO).paths, defaults)       # config holds the project's own paths
        cfg = self.load_text(GOOD + 'paths:\n  protected: ["docs/design/**/*.md"]\n  specs: design/\n')
        self.assertEqual((cfg.paths.protected, cfg.paths.specs, cfg.paths.plans),
                         (('docs/design/**/*.md',), 'design/', 'docs/superpowers/plans/'))

    def test_paths_product(self):
        self.assertEqual(config.Paths().product, ())  # absent: the plan's own reading of `Gate: build`
        cfg = self.load_text(GOOD + 'paths:\n  product: ["src/app/**", "src/packages/**"]\n')
        self.assertEqual(cfg.paths.product, ('src/app/**', 'src/packages/**'))
        self.assertRefused(GOOD + 'paths:\n  product: src/app\n', 'paths.product')

    def test_paths_reject_non_list(self):
        self.assertRefused(GOOD + 'paths:\n  protected: docs/x\n', 'paths.protected')
        self.assertRefused(GOOD + 'paths:\n  themes: [1]\n', 'paths.themes')
        self.assertRefused(GOOD + 'paths:\n  briefs: [tasks/]\n', 'paths.briefs')
        self.assertRefused(GOOD + 'paths:\n  specs: ""\n', 'paths.specs')
        self.assertRefused(GOOD + 'paths:\n  screenshot: []\n', 'paths.screenshot')
        self.assertRefused(GOOD + 'paths: [a]\n', '`paths`')

    def test_links_scope(self):
        self.assertEqual(config.links_scope({}), [])
        self.assertEqual(config.links_scope({'paths': {'protected': ['docs/design/**']}}), ['docs/design/**'])
        links = ['docs/design/**', 'docs/stories/**', 'docs/reviews/**']
        self.assertEqual(config.links_scope({'paths': {'protected': ['docs/**'], 'links': links}}), links)
        cfg = self.load_text(GOOD + 'paths:\n  links: [docs/reviews/**]\n')
        self.assertEqual((cfg.paths.links, config.Paths().links), (('docs/reviews/**',), None))
        self.assertRefused(GOOD + 'paths:\n  links: docs/x\n', 'paths.links')

    def test_matches(self):
        self.assertTrue(config.matches('docs/design/a/b.md', ('docs/design/**/*.md',)))
        self.assertTrue(config.matches('docs/design/b.md', ('docs/design/**/*.md',)))
        self.assertFalse(config.matches('docs/design/a/b.md', ('docs/*.md',)))
        self.assertTrue(config.matches('docs/a.md', ('src/**', 'docs/*.md')))
        self.assertTrue(config.matches('docs/screens/shots/en/x.png', ('docs/screens/shots/**',)))
        self.assertFalse(config.matches('docs/screens/x.png', ('docs/screens/shots/**',)))
        self.assertFalse(config.matches('docs/a.md', ()))


    # ------------------------------------------------------------------------------ concurrency and silence
    def test_concurrency_default_one(self):
        self.assertEqual(config.concurrency({}, 'check'), 1)
        self.assertEqual(config.concurrency({'concurrency': {'build': 2}}, 'check'), 1)

    def test_concurrency_named(self):
        self.assertEqual(config.concurrency({'concurrency': {'check': 3}}, 'check'), 3)

    def test_concurrency_refuses_zero(self):
        for bad in (0, -1, 'two', True, 1.5):
            with self.assertRaises(config.Refused, msg=repr(bad)):
                config.concurrency({'concurrency': {'check': bad}}, 'check')
        with self.assertRaises(config.Refused):
            config.concurrency({'concurrency': [1]}, 'check')
        with self.assertRaises(config.Refused) as caught:
            config.concurrency({'concurrency': {'lint': 2}}, 'check')
        self.assertIn('lint', str(caught.exception))

    def test_silence_default_none(self):
        self.assertIsNone(config.silence({}, 'verify'))
        self.assertIsNone(config.silence({'silence': {'check': 30}}, 'verify'))

    def test_silence_named(self):
        self.assertEqual(config.silence({'silence': {'verify': 60}}, 'verify'), 60)
        for bad in (0, 'a minute', False):
            with self.assertRaises(config.Refused, msg=repr(bad)):
                config.silence({'silence': {'verify': bad}}, 'verify')

    def test_load_refuses_a_bad_limit(self):
        self.assertRefused(GOOD + 'concurrency:\n  check: 0\n', 'concurrency', 'check')
        self.assertRefused(GOOD + 'silence:\n  verify: none\n', 'silence', 'verify')
        self.load_text(GOOD + 'concurrency:\n  check: 2\nsilence:\n  verify: 60\n')

    def test_raw_is_the_mapping(self):
        self.assertEqual(config.raw(REPO)['base'], 'main')

if __name__ == '__main__':
    unittest.main()
