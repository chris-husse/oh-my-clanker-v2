#!/usr/bin/env python3
"""The entry of `just omc <verb>`: one subcommand per verb of config.VERBS, the git facts
in repo.py; `enter --resume` costs no git call beyond `rev-parse`. The standard library and pyyaml (config.py reads
omc/config.yaml), run through the justfile's `uv run --frozen python -I`.
Exit codes, the same for every verb: 0 yes / done, 1 no / none (one line on stdout says why), 2 a refusal or an error
(`error: <why>` on stderr), 3 `rebase` stopped on a conflict; but `title` and `shell-integration`, which keep omc 0.1.54's
own lines and codes (`ported`).

`enter` is the marker of "Where a skill is": `.cache/omc/current` holds the name of the running pipeline skill;
`enter --resume` is the Claude `SessionStart` hook on `compact` (.claude/settings.json)."""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402
import done  # noqa: E402
import gitnexus  # noqa: E402
import lint  # noqa: E402
import passes  # noqa: E402
import rebase  # noqa: E402
import repo  # noqa: E402

MARKER = os.path.join('.cache', 'omc', 'current')
RESUME = ('you are in /{skill} (omc/pipeline/{skill}/SKILL.md): read it again and start it at its first step; the '
          'steps that are done skip themselves')


Refused = config.Refused  # the one refusal of every verb; its message follows `error: `


class Parser(argparse.ArgumentParser):
    """argparse, its usage errors in the tool's form: `error: <why>` on stderr, exit 2."""

    def error(self, message):
        print(f'error: {self.prog}: {message}', file=sys.stderr)
        sys.exit(2)


def enter(args):
    if args.resume:
        if args.skill or args.done:
            raise Refused('enter --resume takes nothing else')
        try:
            found = repo.root()
        except Refused:
            return 0
        try:
            with open(os.path.join(found, MARKER), encoding='utf-8') as f:
                skill = f.read().strip()
        except OSError:
            return 0
        if skill in config.PIPELINE:
            print(RESUME.format(skill=skill))
        return 0
    marker = os.path.join(repo.root(), MARKER)
    if args.done:
        if args.skill:
            raise Refused('enter --done takes no skill')
        try:
            os.remove(marker)
        except FileNotFoundError:
            pass
        return 0
    if args.skill not in config.PIPELINE:
        raise Refused(f'enter takes one of {", ".join(config.PIPELINE)}'
                      + (f', not `{args.skill}`' if args.skill else ''))
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, 'w', encoding='utf-8') as f:
        f.write(args.skill + '\n')
    return 0


def models(args):
    print(json.dumps(config.models(config.load(repo.root()), args.role)))
    return 0


def handoff(args):
    """`ask` when omc/config.yaml sets `ask_for_provider_handoff: true` (stop before /implement and before /audit),
    else `continue`; exit 0 for either."""
    print('ask' if config.load(repo.root()).ask_for_provider_handoff else 'continue')
    return 0


def listing(found, what):
    """One path per line, 0; none: 1."""
    print('\n'.join(found) if found else f'no {what} committed on this branch')
    return 0 if found else 1


def record(args):
    return listing(repo.records(repo.root()), 'record')


def the_plan(root):
    """The one plan the branch committed; refused when there is none or more than one."""
    found = repo.plans(root)
    if len(found) != 1:
        raise Refused('no plan committed on this branch' if not found
                      else f'{len(found)} plans committed on this branch: {", ".join(found)}')
    return found[0]


def read(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except OSError as e:
        raise Refused(f'cannot read {path}: {e.strerror}') from None


def product_gate(root, task):
    """[task] (repo.next_task) with its gate `build` made `check` when `paths.product` lists globs and a path changed
    since the merge-base (committed, in the tree or untracked: done.changed_paths) matches one, the first of them
    under `product`; else [task] as it is (no `paths.product`: the plan's `Gate:` line stands)."""
    globs = config.load(root).paths.product
    if task['gate'] != 'build' or not globs:
        return task
    hits = [p for p in done.changed_paths(root, repo.merge_base(root)) or () if config.matches(p, globs)]
    return {**task, 'gate': 'check', 'product': hits[:done.SHOWN]} if hits else task


def plan(args):
    root = repo.root()
    if not args.next and args.tick is None:
        return listing(repo.plans(root), 'plan')
    path = the_plan(root)
    full = os.path.join(root, path)
    text = read(full)
    if args.next:
        task = repo.next_task(text)
        if task is None:
            print(f'every task of {path} is ticked')
            return 1
        print(json.dumps(product_gate(root, task)))
        return 0
    try:
        ticked, count = repo.tick(text, args.tick)
    except LookupError:
        print(f'no task {args.tick} in {path}')
        return 1
    if count:
        with open(full, 'w', encoding='utf-8') as f:
            f.write(ticked)
    print(count)
    return 0


def git_fact(args):
    root = repo.root()
    if args.fact == 'rebased-on':
        yes, line = repo.rebased_on(root)
    elif args.fact == 'one-commit':
        yes, k = repo.one_commit(root)
        line = f'{k} commits over the merge-base'
    else:
        dirty = repo.dirty_paths(root)
        yes, line = not dirty, '\n'.join(dirty) or 'clean'
    print(line)
    return 0 if yes else 1


def rebase_branch(args):
    code, verdict = rebase.rebase(repo.root(), args.squash)
    print(json.dumps(verdict))
    return code


def impact(args):
    root = repo.root()
    if args.done:
        rebase.impact_done(root)
        return 0
    old = rebase.impact(root)
    print(old or 'no impact pending')
    return 0 if old else 1


def answer(yes, line):
    print(line)
    return 0 if yes else 1


def gate(args):
    root = repo.root()
    if args.ask == 'run':
        return done.gate_run(root, args.gate, args.args)
    if args.args:
        raise Refused(f'gate {args.ask} takes no arguments after the gate')
    if args.ask == 'skip':
        done.gate_skip(root, args.gate)
        return 0
    return answer(*done.gate_passed(root, args.gate))


def reviewed(args):
    root = repo.root()
    if args.record:
        done.record_review(root)
        return 0
    return answer(*done.reviewed(root))


def settled(args):
    root = repo.root()
    if args.record:
        done.record_settled(root)
        passes.clear(root)
        return 0
    return answer(*done.settled(root))


def count_pass(args):
    print(json.dumps(passes.next_pass(repo.root(), args.terminal)))
    return 0


def lint_tree(args):
    problems = lint.lint(args.root or repo.root())
    print('\n'.join([*problems, f'{len(problems)} problems' if problems else 'OK']))
    return 1 if problems else 0


def gitnexus_verb(args):
    """`just omc gitnexus <action>`: a step that does not finish is `[failed] <why>` on stderr, exit 2; `refresh`
    acts on the primary checkout's index from any checkout; a read verb asks it and exits with GitNexus's code."""
    if args.action in gitnexus.READS:
        return gitnexus.read(args.action, [args.subject, *args.rest])
    cfg = config.load(repo.root())
    try:
        if args.action == 'install':
            gitnexus.install(cfg)
        else:
            gitnexus.refresh(gitnexus.primary_root('.'), cfg.base)
    except gitnexus.Failed as e:
        print(f'[failed] {e}', file=sys.stderr)
        return 2
    return 0


def ported(args):
    """`title` and `shell-integration`, the ported helpers of omc 0.1.54 (title.py, fish_integration.py): they read no
    configuration and keep omc's own lines and codes, an expected failure `error: <why>` on stderr with its code (1, or
    2 for a refusal), as omc's one `OmcError` boundary printed it."""
    import toolctx
    ctx = toolctx.Ctx.from_env()
    try:
        if args.verb == 'title':
            import title
            return title.run_title_command(ctx, args)
        import fish_integration
        return fish_integration.run_fish_integration(ctx, args.action)
    except toolctx.OmcError as e:
        print(f'error: {e}', file=sys.stderr)
        return e.rc


def parser():
    p = Parser(prog='omc', description="The omc/ pipeline's tool.")
    verbs = p.add_subparsers(dest='verb', required=True, metavar='verb', parser_class=Parser)
    for verb in config.VERBS:
        if verb == 'enter':
            s = verbs.add_parser('enter', help='write, remove or read the marker .cache/omc/current')
            s.add_argument('skill', nargs='?', help=f'one of {", ".join(config.PIPELINE)}')
            s.add_argument('--done', action='store_true', help='remove the marker (absent is fine)')
            s.add_argument('--resume', action='store_true',
                           help="the compaction hook's line when the marker is there, else nothing; always exit 0")
            s.set_defaults(handler=enter)
        elif verb == 'models':
            s = verbs.add_parser('models', help="a role's model from omc/config.yaml, as JSON (effort always ''); "
                                                'a complexity resolves through its tier')
            s.add_argument('role', help=f'one of {", ".join(config.ROLES)}')
            s.set_defaults(handler=models)
        elif verb == 'handoff':
            s = verbs.add_parser('handoff', help='`ask` or `continue` at the hand-offs before /implement and /audit, '
                                                 'from ask_for_provider_handoff of omc/config.yaml')
            s.set_defaults(handler=handoff)
        elif verb == 'record':
            s = verbs.add_parser('record', help='the design record the branch added and committed since the merge-base')
            s.set_defaults(handler=record)
        elif verb == 'plan':
            s = verbs.add_parser('plan', help='the plan the branch added and committed since the merge-base')
            which = s.add_mutually_exclusive_group()
            which.add_argument('--next', action='store_true', help="the first task with a `- [ ]`, as JSON; its gate the plan's "
                               "`Gate:` line, `build` made `check` once the branch changes a path of "
                               "paths.product (named under `product`)")
            which.add_argument('--tick', type=int, metavar='N', help="tick every `- [ ]` of task N; prints the count")
            s.set_defaults(handler=plan)
        elif verb == 'git':
            s = verbs.add_parser('git', help='is the branch rebased on its base, one commit over it, its tree clean')
            s.add_argument('fact', choices=config.VERBS['git'])
            s.set_defaults(handler=git_fact)
        elif verb == 'rebase':
            s = verbs.add_parser('rebase', help='rebase the branch onto origin/<base>; one JSON line; 3 on a conflict')
            s.add_argument('--squash', action='store_true', help='first fold the commits over the merge-base into one')
            s.set_defaults(handler=rebase_branch)
        elif verb == 'impact':
            s = verbs.add_parser('impact', help='the old merge-base of a rebase whose impact is not read yet')
            s.add_argument('--done', action='store_true', help='remove the mark .cache/omc/impact (absent is fine)')
            s.set_defaults(handler=impact)
        elif verb == 'gate':
            s = verbs.add_parser('gate', help='run runs omc/bin/<gate> [ARGS] at the root, or with a step file '
                                              'omc/bin/<gate>.steps.yaml its stale steps (DVC deciding; --full all), '
                                              'once one of the gate\'s '
                                              'machine-wide slots is free (config `concurrency`; output teed to '
                                              '.cache/omc/gates/<gate>.log, the exit code to .cache/omc/gates/<gate>.exit '
                                              'once it ends; with config `silence`, a run silent that '
                                              'long is killed, exit 124; exit 0 of a full run started on a clean '
                                              'tree records a pass; its exit code); passed: has the gate a pass, or '
                                              'the owner\'s skip, that holds for this tree; skip writes the owner\'s '
                                              'skip')
            s.add_argument('ask', choices=config.VERBS['gate'])
            s.add_argument('gate', choices=config.GATES)
            s.add_argument('args', nargs=argparse.REMAINDER, metavar='ARGS',
                           help="run only: passed to omc/bin/<gate>, a run with ARGS recording no pass; "
                                "with a step file only --full")
            s.set_defaults(handler=gate)
        elif verb == 'reviewed':
            s = verbs.add_parser('reviewed', help='has a review that holds for this tree; --record writes one')
            s.add_argument('--record', action='store_true', help='write .cache/omc/reviewed/<HEAD sha>.json')
            s.set_defaults(handler=reviewed)
        elif verb == 'settled':
            s = verbs.add_parser('settled', help='is the design settled for this tree; --record writes it')
            s.add_argument('--record', action='store_true', help="write .cache/omc/settled/<HEAD sha>.json and "
                                                                 "remove the branch's pass counts")
            s.set_defaults(handler=settled)
        elif verb == 'pass':
            s = verbs.add_parser('pass', help='count one more pass of a design terminal; its role and tier, as JSON '
                                              '(harden: harden on max the first, harden-repeat on medium every later '
                                              'one; consistency: the orchestrator)')
            s.add_argument('terminal', choices=config.VERBS['pass'])
            s.set_defaults(handler=count_pass)
        elif verb == 'lint':
            s = verbs.add_parser('lint', help="the names the omc/ pipeline's skills use exist")
            s.add_argument('--root', metavar='DIR', help='the tree to lint (default: the repository of the cwd)')
            s.set_defaults(handler=lint_tree)
        elif verb == 'gitnexus':
            s = verbs.add_parser('gitnexus', help='GitNexus under ~/.omc/tools/gitnexus at the pin of omc/config.yaml')
            actions = s.add_subparsers(dest='action', required=True, metavar='action', parser_class=Parser)
            a = actions.add_parser('install', help='clone, build and install the embedding runtime at the pin; '
                                                   'nothing when it is there')
            a.set_defaults(handler=gitnexus_verb)
            a = actions.add_parser('refresh', help="the primary checkout's index at the base's tip: analyze, the "
                                                   'keyword-only fallback, the backfill, the rebuild of a stale store')
            a.set_defaults(handler=gitnexus_verb)
            for action, subject, what in (('query', 'concept', 'the flows a concept takes part in'),
                                          ('context', 'symbol', "a symbol's callers, callees and processes"),
                                          ('impact', 'symbol', 'what a change to a symbol reaches'),
                                          ('cypher', 'query', 'a Cypher query over the graph')):
                a = actions.add_parser(action, help=f"{what}, in the primary's graph at the base; first line: "
                                                    'the index and the base, how far it lags')
                a.add_argument('subject', metavar=subject)
                a.add_argument('rest', nargs=argparse.REMAINDER, help="GitNexus's own options, passed through")
                a.set_defaults(handler=gitnexus_verb)
        elif verb == 'title':
            s = verbs.add_parser('title', help="pin or release this iTerm2 tab's title (quiet; the fish hook's helper)")
            sub = s.add_subparsers(dest='title_command', required=True, metavar='action', parser_class=Parser)
            a = sub.add_parser('set', help="pin the caller's tab title: just omc title set -- <title>")
            a.add_argument('title')
            sub.add_parser('release', help="restore iTerm2's live default title for the caller's tab")
            a = sub.add_parser('apply', help='apply a request file the hook wrote (serialized)')
            a.add_argument('request_file')
            s.set_defaults(handler=ported)
        elif verb == 'shell-integration':
            s = verbs.add_parser('shell-integration', help="the fish tab-title hook in the user's conf.d "
                                                           '(enable|disable|status|reconcile)')
            sub = s.add_subparsers(dest='shell', required=True, metavar='shell', parser_class=Parser)
            a = sub.add_parser('fish')
            a.add_argument('action', choices=('enable', 'disable', 'status', 'reconcile'))
            s.set_defaults(handler=ported)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return args.handler(args)
    except Refused as e:
        print(f'error: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
