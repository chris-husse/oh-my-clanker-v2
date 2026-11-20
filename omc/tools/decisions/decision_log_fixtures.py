# omc/tools/decisions/decision_log_fixtures.py
"""The fixtures test_decisions.py and test_integrity.py share: the vault FIXTURE, the omc/config.yaml whose paths
place it (PATHS, CONFIG; the tool is configured with them on import) and the log's entries as the tool writes them.
Imported by both, after they put this directory on the path; not a test of its own."""
import json
import os
import sys

import decisions

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # omc/tools: config, omc_fixtures
import config  # noqa: E402
import omc_fixtures  # noqa: E402

# The paths of the vault FIXTURE: the log in docs/reviews/, the question files beside it, the guarded pages every *.md
# of four folders and one data file, the theme files design/T<nn>-*.md
PATHS = config.Paths(protected=('docs/architecture/**/*.md', 'docs/design/**/*.md', 'docs/screens/**/*.md',
                                'docs/stories/**/*.md', 'docs/architecture/objects/port.yaml'),
                     decision_log='docs/reviews/design-decision-log.md', questions='docs/reviews/',
                     themes=('docs/design/T[0-9][0-9]-*.md',))


def config_text(paths):
    """omc_fixtures.CONFIG, the shipped tiers and pin, with its `paths` block holding [paths] (a config.Paths;
    the globs as JSON strings, which YAML reads as they are)."""
    head = omc_fixtures.CONFIG[:omc_fixtures.CONFIG.index('paths:\n')]
    lines = [f'  {k}: [{", ".join(json.dumps(g) for g in v)}]' if isinstance(v, tuple) else f'  {k}: {v}'
             for k, v in vars(paths).items() if v is not None]  # an unset key (paths.links) stays absent
    return head + 'paths:\n' + '\n'.join(lines) + '\n'


CONFIG = config_text(PATHS)
decisions.configure(PATHS)

LOG_HEAD = ('# Design decision log\n\n*Scratch space: decisions recorded and not yet carried through, trimmed once '
            'applied on main. Written only through `just decisions`. Next: 1*\n')
T05 = ('## T5 The shift\n\n### T5.2.1 Preconditions\n\n'
       '- [R5.2.1-1] A shift cannot begin without signal.\n'
       '  (worker.md › [W2](../stories/worker.md#W2%20—%20Begin%20the%20shift); 13.24)\n'
       '  [E2E: E5.2.1-1]\n')
STORY = '# Worker\n\n### W2 — Begin the shift\n\nCount.\n\n**Rules.** T5.2.1@454f\n'
FIXTURE = {
    'design/T05-the-shift.md': T05,
    'stories/worker.md': STORY,
    'screens/definitions/shift.preparing.md': '# shift.preparing\n\nText.\n',
    'screens/views/shift_view.md': '# shift_view\n',
    'screens/components/incident_row.md': '# incident_row\n',
    'screens/FORMAT.md': '# Format\n\n## References\n\nText.\n',
    'architecture/operations.md': '# Operations\n\n## Incidents\n\nText.\n',
    'architecture/objects/port.yaml': 'a: 1\n',
    'reviews/2026-11-12-x-1.md': '# Questions: feature/x run 1\n\n### Q1 A question\n\n**Status.** open\n',
    'reviews/2026-11-11-server-gate-rulings.md': '# Rulings\n\n### Q1 Not a question file\n\n**Status.** open\n',
    'reviews/design-decision-log.md': LOG_HEAD,
}
APPLIED = 'recorded 2026-11-12 · applied 2026-11-12'
RECORDED = 'recorded 2026-11-12'


def write_vault(root, files=FIXTURE):
    """The vault [files] under <root>/docs and <root>/omc/config.yaml (CONFIG); the vault's path."""
    os.makedirs(os.path.join(root, 'omc'), exist_ok=True)
    with open(os.path.join(root, 'omc', 'config.yaml'), 'w', encoding='utf-8') as f:
        f.write(CONFIG)
    docs = os.path.join(root, 'docs')
    for rel, text in files.items():
        path = os.path.join(docs, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    return docs


def entry(n, status=RECORDED, affected='', title='Incidents need a photo', context='Workers record incidents without proof.',
          decision='Every incident carries a photo.', automated='false'):
    """An entry's text as the tool writes it."""
    lines = [f'### {n} {title}', '', f'**Context.** {context}', f'**Decision.** {decision}', f'**Automated.** {automated}']
    if affected:
        lines.append(f'**Affected.** {affected}')
    return '\n'.join(lines + [f'**Status.** {status}']) + '\n'


def log_text(next_n, *entries):
    return LOG_HEAD.replace('Next: 1*', f'Next: {next_n}*') + ''.join('\n' + e for e in entries)


def parse(next_n, *entries):
    return decisions.parse_log(log_text(next_n, *entries))
