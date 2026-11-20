"""`just omc lint`: lint checks names, not the flow. It reads
every omc/pipeline/*/SKILL.md and omc/terminals/*/SKILL.md and reports a name that does not exist: a terminal after
a `▣`, a verb or sub-verb of `just omc`, a recipe of the justfile or of a file it imports, a skill, a step id; a pipeline skill without its
link in .claude/skills/ (Claude only), and a gate terminal (`config.GATES`) without its own; a terminal that speaks to the owner, runs an orchestrator or holds no
OUTCOME line (a search for the words, not a reading). Names are read only inside code spans and fenced blocks, but
for the `▣` marks and the step headings; paths (`/tmp/x`), namespaced names (`superpowers:brainstorming`) and prose
are not names.
The standard library only."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python -I leaves the script's directory off the path
import config  # noqa: E402

# A name, not the head of a path, a namespaced name or a file name; a `.`, `:` or `/` ending a sentence or a clause
# (before a space or the line's end) ends it
NAME = r'[A-Za-z][\w-]*(?![\w-])(?![./:]\S)'
SPAN = re.compile(r'(`+)(?!`)(.+?)(?<!`)\1(?!`)')
FENCE = re.compile(r'^\s*(`{3,}|~{3,})')
MARK = re.compile(r'▣\s*`?([A-Za-z][\w-]*)')  # whatever follows the name: a mark is never a path
HEADING = re.compile(r'^##\s+`([^`]+)`')
JUMP = re.compile(r'\b(?:back|on) to `(' + NAME + ')`')
JUST = re.compile(r'(?<![\w./-])just(?![\w-])[ \t]+(' + NAME + r')(?:[ \t]+(' + NAME + r'))?(?:[ \t]+(' + NAME + '))?')
SKILL = re.compile(r'^/(' + NAME + ')')
ENTRY = re.compile(r'^/(' + NAME + r') ([A-Za-z-]+)\s*$')
RECIPE = re.compile(r'^@?([A-Za-z_][\w-]*)(?:[ \t][^:\n]*)?:(?!=)', re.M)
IMPORT = re.compile(r'''^import\??[ \t]+(['"])(.+?)\1[ \t]*(?:#.*)?$''', re.M)
OWNER = ('ask the owner', 'asks the owner', 'tell the owner', 'tells the owner', 'show the owner', 'shows the owner',
         'askuserquestion')
# The orchestrators a terminal never runs: the pipeline's and the domain's that talk to the owner or carry decisions
RUNS = (*config.PIPELINE, 'pose-questions', 'record-decision', 'answer-doubt', 'review-decisions')
OUTCOME = 'OUTCOME {"outcome": '


class Skill:
    """One SKILL.md: its body lines after the frontmatter, the code read for names (span contents and fenced lines)
    and the spans alone, each with its line number."""

    def __init__(self, root, kind, name):
        self.kind, self.name = kind, name
        self.rel = f'omc/{kind}/{name}/SKILL.md'
        try:
            with open(os.path.join(root, self.rel), encoding='utf-8') as f:
                self.lines = f.read().split('\n')
        except OSError:
            self.lines = None
            return
        self.body = self.lines[self.frontmatter_end():]
        self.start = len(self.lines) - len(self.body)  # 0-based index of the body's first line
        self.code, self.spans, self.prose = [], [], []
        fence = None
        for i, line in enumerate(self.body, self.start + 1):
            m = FENCE.match(line)
            if fence is None and m:
                fence = m.group(1)
            elif fence is not None:
                if line.strip().startswith(fence) and not line.strip().strip(fence[0]):
                    fence = None
                else:
                    self.code.append((i, line))
            else:
                self.prose.append((i, line))
                for s in SPAN.finditer(line):
                    self.code.append((i, s.group(2)))
                    self.spans.append((i, s.group(2).strip()))

    def frontmatter_end(self):
        if self.lines and self.lines[0].strip() == '---':
            for i, line in enumerate(self.lines[1:], 1):
                if line.strip() == '---':
                    return i + 1
        return 0

    def steps(self):
        """(line, id) of each step heading."""
        return [(i, m.group(1)) for i, line in self.prose if (m := HEADING.match(line))]


def frontmatter(skill):
    """The problem of the frontmatter, (line, detail), or None."""
    end = skill.frontmatter_end()
    if not end:
        return 1, 'the file does not open with a `---` frontmatter'
    fields = {}
    for i, line in enumerate(skill.lines[1:end - 1], 2):
        key, sep, value = line.partition(':')
        if sep and not line.startswith((' ', '\t')):
            fields.setdefault(key.strip(), (i, value.strip().strip('"\'').strip()))
    line, name = fields.get('name', (1, ''))
    if name != skill.name:
        return line, f'`name:` is `{name}`, not its directory `{skill.name}`' if name else 'no `name:`'
    line, description = fields.get('description', (1, ''))
    if not description:
        return line, 'no `description:`' if line == 1 else 'an empty `description:`'
    return None


def recipes(root):
    """The recipes of the root justfile and of every file it imports (`import` or `import?`, a path relative to the
    importing file), imports of imports too; a file that cannot be read adds none."""
    found, seen, todo = set(), set(), [os.path.join(root, 'justfile')]
    while todo:
        path = todo.pop()
        if os.path.realpath(path) in seen:
            continue
        seen.add(os.path.realpath(path))
        try:
            with open(path, encoding='utf-8') as f:
                text = f.read()
        except OSError:
            continue
        found.update(RECIPE.findall(text))
        todo.extend(os.path.join(os.path.dirname(path), m.group(2)) for m in IMPORT.finditer(text))
    return found


def skills(root, kind):
    directory = os.path.join(root, 'omc', kind)
    names = sorted(n for n in os.listdir(directory) if os.path.isdir(os.path.join(directory, n))) \
        if os.path.isdir(directory) else []
    return [Skill(root, kind, n) for n in names]


def lint(root):
    """The PROBLEM lines of the tree at [root], `PROBLEM: <path>:<line>: <kind>: <detail>`; raises config.Refused when
    [root] has no omc/."""
    if not os.path.isdir(os.path.join(root, 'omc')):
        raise config.Refused(f'no omc/ in {root}')
    pipeline, terminals = skills(root, 'pipeline'), skills(root, 'terminals')
    known = recipes(root)
    present = {s.name: s for s in pipeline if s.lines is not None}
    steps = {name: {sid for _, sid in s.steps()} for name, s in present.items()}
    problems = []

    def red(skill, line, kind, detail):
        problems.append(f'PROBLEM: {skill.rel}:{line}: {kind}: {detail}')

    def linked(skill):
        """The skill's link, .claude/skills/<name> → omc/<kind>/<name>, or its problem."""
        link = os.path.join(root, '.claude', 'skills', skill.name)
        target = os.path.join(root, 'omc', skill.kind, skill.name)
        if not os.path.islink(link) or os.path.realpath(link) != os.path.realpath(target):
            red(skill, 1, 'link',
                f'.claude/skills/{skill.name} is not a symbolic link to omc/{skill.kind}/{skill.name}')

    for skill in pipeline + terminals:
        if skill.lines is None:
            red(skill, 1, 'frontmatter', 'no SKILL.md in its directory')
            continue
        bad = frontmatter(skill)
        if bad:
            red(skill, bad[0], 'frontmatter', bad[1])
        for i, line in enumerate(skill.body, skill.start + 1):
            for m in MARK.finditer(line):
                if not os.path.isfile(os.path.join(root, 'omc', 'terminals', m.group(1), 'SKILL.md')):
                    red(skill, i, 'terminal', f'▣ {m.group(1)} names no omc/terminals/{m.group(1)}/SKILL.md')
        for i, code in skill.code:
            for m in JUST.finditer(code):
                recipe, verb, sub = m.groups()
                if recipe not in known:
                    red(skill, i, 'recipe', f'`just {recipe}` names no recipe of the justfile')
                elif recipe == 'omc' and verb:
                    if verb not in config.VERBS:
                        red(skill, i, 'verb', f'`just omc {verb}` names no verb of `just omc`')
                    elif config.VERBS[verb] and sub and sub not in config.VERBS[verb]:
                        red(skill, i, 'verb', f'`just omc {verb} {sub}`: `{sub}` is not one of '
                                              f'{", ".join(config.VERBS[verb])}')
        for i, span in skill.spans:
            m = SKILL.match(span)
            if m:
                name = m.group(1)
                if not (os.path.isdir(os.path.join(root, 'omc', 'pipeline', name))
                        or os.path.isdir(os.path.join(root, '.claude', 'skills', name))):
                    red(skill, i, 'skill', f'`/{name}` names neither omc/pipeline/{name} nor .claude/skills/{name}')
                if skill.kind == 'terminals' and name in RUNS:
                    red(skill, i, 'runs', f'a terminal runs `/{name}`, an orchestrator')
            m = ENTRY.match(span)
            if m and m.group(1) in steps and m.group(2) not in steps[m.group(1)]:
                red(skill, i, 'step', f'`/{m.group(1)} {m.group(2)}`: no step `{m.group(2)}` in /{m.group(1)}')
        if skill.kind == 'terminals':
            for i, line in enumerate(skill.lines, 1):
                low = line.lower()
                for words in OWNER:
                    if words in low:
                        red(skill, i, 'owner', f'a terminal never speaks to the owner ("{words}")')
            if not any(OUTCOME in line for line in skill.lines):
                red(skill, 1, 'outcome', f'no `{OUTCOME}…}}` line')
            if skill.name in config.GATES:
                linked(skill)
            continue
        seen = set()
        for i, sid in skill.steps():
            if sid in seen:
                red(skill, i, 'step', f'the step `{sid}` again')
            seen.add(sid)
        for i, line in skill.prose:
            for m in JUMP.finditer(line):
                if m.group(1) not in seen:
                    red(skill, i, 'step', f'`{m.group(1)}` is no step of /{skill.name}')
        linked(skill)
    return problems
