#!/usr/bin/env python3
"""The mechanical checks of the decisions in one command: the log is sound, every entry of the branch has its row in the
branch's record, the vault's links hold (the links tool, then the project's `omc/bin/links-check` when it has one),
every changed guarded page is named by an entry applied on the branch, and (in implementation, the default phase)
nothing recorded is left unapplied and, without --defer-questions, no question file holds an open question: the
questions wait for the push gate (verify's step and the pre-push hook pass neither flag; /design passes --phase design,
/implement's decisions step --defer-questions: from /design on, no question blocks the run); the output and the row's
form are omc/tools/decisions/FORMAT.md › The integrity check. It reads the log, the record, git and the vault's links;
no build, no test, no gate stage. Whether an entry reached the pages its row planned is the "decisions carried" review's
reading, not checked here. Every check but the record's is decisions.py's own function, called in-process; git is read
only in `branch_records` and through decisions.py (`repo_of`, `git_inputs`, `tree_refs`); every other function takes
texts. omc/config.yaml's paths place the log, the guarded pages, the question files and the records
(decisions.configured; pyyaml reads it, so it runs through uv); with no log and no protected page there is nothing to
check: it prints nothing and exits 0. Run from the repository root: `just design-integrity-check [--phase
design|implementation] [--defer-questions]` (`--help`)."""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I leaves the script's directory off the path
import decisions  # noqa: E402

CHECKS = ('decisions check', 'questions', 'record', 'links-check', 'guard', 'pending')
PHASES = ('design', 'implementation')
SECTION = 'Decisions and the pages they change'
LINKS_TOOL = 'omc/skills/reconcile-links/tool'   # repo-relative
LINKS_HOOK = 'omc/bin/links-check'   # the project's own link checks, run after the tool's when it exists
ROW_RE = re.compile(r'^\s*\|\s*`?decision (\d+)')  # a row whose first cell begins `decision <n>`


def record_rows(text):
    """The ids the rows of a record name: the first cell of every table row inside a section headed (any level)
    SECTION, outside code fences; a later cell and a row of another section never count."""
    lines = text.split('\n')
    heads = decisions.headings_of(text)
    rows = set()
    for k, h in enumerate(heads):
        if h.text != SECTION:
            continue
        end = next((g.line - 1 for g in heads[k + 1:] if g.level <= h.level), len(lines))
        fence = None
        for line in lines[h.line:end]:
            f = decisions.FENCE_RE.match(line)
            if fence is not None:
                if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence) and line.strip() == f.group(1):
                    fence = None
                continue
            if f:
                fence = f.group(1)
            elif m := ROW_RE.match(line):
                rows.add(int(m.group(1)))
    return rows


def branch_entries(log, main_log):
    """The entries of the branch: every entry of the log main's log never held as the same decision."""
    return [e for e in log.order if not decisions.on_main(e, main_log)]


def missing_rows(entries, records):
    """records: vault path -> text of the branch's records. One line per entry no record's row names; nothing when
    the branch has no record."""
    if not records:
        return []
    rows = set().union(*(record_rows(t) for t in records.values()))
    paths = ', '.join(sorted(records))
    return [f'decision {e.n} {e.title} has no row in the record\'s "{SECTION}" ({paths}): /review-decisions appends it; '
            'before implementation /design\'s harden writes it' for e in entries if e.n not in rows]


def _inner(lines):
    """lines without their leading `PROBLEM: `, to be named by their check."""
    return [l[len('PROBLEM: '):] if l.startswith('PROBLEM: ') else l for l in lines]


def integrity(phase, vault, log, head_log, main_log, changes, refs, question_files, records, links, defer_questions=False):
    """Every problem, `PROBLEM: <check>: <detail>`, in CHECKS order; `pending` in implementation only, `questions` in
    implementation without defer_questions only, phase one of PHASES (else ValueError). head_log and main_log as
    decisions.check takes them (main_log: main's log, Inputs.main()); changes as git_inputs gives them; refs as
    tree_refs; question_files as decisions.question_files; records as missing_rows; links as links_lines gives them."""
    if phase not in PHASES:
        raise ValueError(f'phase {phase!r} is not one of {", ".join(PHASES)}')
    found = {
        'decisions check': _inner(decisions.check(vault, log, head_log, main_log, decisions.deleted(changes), refs)),
        'questions': (decisions.open_questions(question_files)
                      if phase == 'implementation' and not defer_questions else []),
        'record': missing_rows(branch_entries(log, main_log), records),
        'links-check': links,
        'guard': decisions.guard(vault, changes, log, main_log),
        'pending': decisions.unapplied(log) if phase == 'implementation' else [],
    }
    return [f'PROBLEM: {check}: {detail}' for check in CHECKS for detail in found[check]]


def links_check(repo):
    """`just links-check`'s commands, run in the repository: links_lines of the links tool's run, or one `did not
    run` line when it could not start; then, when the project has its hook LINKS_HOOK (an executable file; none:
    nothing), links_lines of the hook's run at the root, its `did not run` line named `omc/bin/links-check did not
    run: …`."""
    try:
        r = subprocess.run(['dart', 'run', 'bin/links_check.dart'], cwd=os.path.join(repo, LINKS_TOOL),
                           capture_output=True, text=True)
        lines = links_lines(r.returncode, r.stdout, r.stderr)
    except OSError as e:  # no dart on the path, the tool's folder missing
        lines = [f'did not run: {e}']
    hook = os.path.join(repo, LINKS_HOOK)
    if not (os.path.isfile(hook) and os.access(hook, os.X_OK)):
        return lines
    try:
        r = subprocess.run([hook], cwd=repo, capture_output=True, text=True)
        found = links_lines(r.returncode, r.stdout, r.stderr)
    except OSError as e:
        found = [f'did not run: {e}']
    return lines + [f'{LINKS_HOOK} {line}' if line.startswith('did not run') else line for line in found]


def links_lines(returncode, stdout, stderr):
    """links-check's problems from its exit code and its output, each without its `PROBLEM: `: none on exit 0, its
    PROBLEM lines on exit 1, else one `did not run` line with the exit code and the output's last line."""
    if returncode == 0:
        return []
    problems = [l[len('PROBLEM: '):] for l in stdout.split('\n') if l.startswith('PROBLEM: ')]
    if returncode == 1 and problems:
        return problems
    last = next((l.strip() for l in reversed((stdout + '\n' + stderr).split('\n')) if l.strip()), '')
    return [f'did not run: exit {returncode}' + (f': {last}' if last else '')]


def branch_records(repo, docs, merge_base):
    """The branch's records, as vault paths, sorted: every *-design.md of `paths.specs` added since merge_base,
    tracked (`git diff --diff-filter=A` against the working tree) or untracked. docs: the vault, relative to repo."""
    prefix = '' if docs in ('', '.') else docs.rstrip('/') + '/'
    specs = decisions.SPECS
    paths = set()
    for args in (('diff', '-z', '--name-only', '--diff-filter=A', '--no-renames', merge_base), ('ls-files', '-z', '--others', '--exclude-standard')):
        r = subprocess.run(['git', '-C', repo, *args, '--', specs], capture_output=True)
        if r.returncode != 0:
            raise decisions.RefError(f'git {args[0]} failed: {r.stderr.decode().strip()}')
        paths |= {p for p in r.stdout.decode('utf-8').split('\0') if p.endswith('-design.md') and p.startswith(prefix)}
    return sorted(p[len(prefix):] for p in paths)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='design-integrity-check', description=__doc__.split('\n')[0])
    parser.add_argument('--docs', default=None, help="the vault (default: the top folder of omc/config.yaml's "
                                                     'paths.decision_log)')
    parser.add_argument('--phase', choices=PHASES, default='implementation',
                        help='design: the recorded entries and the open questions wait; implementation (the default): '
                             'nothing recorded is left unapplied, and no question is open')
    parser.add_argument('--defer-questions', action='store_true',
                        help='the open questions wait for the push gate (/implement\'s decisions step); '
                             'verify and the pre-push hook never pass it')
    args = parser.parse_args(argv)
    try:
        vault = decisions.Vault(decisions.configured(args.docs))
        if not vault.is_file(decisions.LOG):
            if not decisions.PROTECTED:
                return 0  # idle: no log, no protected page
            raise decisions.RefError(f'no such log: {decisions.VAULT}{decisions.LOG}')
        log = decisions.parse_log(vault.text(decisions.LOG))
        repo = decisions.repo_of(vault.root)
        if repo is None:
            raise decisions.RefError(f'{vault.root} is in no git repository')
        i = decisions.git_inputs(*repo)
        records = {p: vault.text(p) for p in branch_records(*repo, i.base)}
        problems = integrity(args.phase, vault, log, decisions.parse_log(i.head_log or ''), i.main(), i.changes,
                             decisions.tree_refs(repo[0]), decisions.question_files(vault), records, links_check(repo[0]),
                             defer_questions=args.defer_questions)
    except decisions.RefError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2
    for line in problems:
        print(line)
    print(f'{len(problems)} problems' if problems else 'OK')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
