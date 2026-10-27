"""Git history and link pinning: a link of a history file (the log, and every file corpus.yaml names as history) on a
line that came from main carries the title `"git:<12 hex>"` of a commit on main where its target existed.

`GitHistory` answers what git remembers, every answer cached; `pin_links` adds the titles, which leaves the
link-free text unchanged."""
from __future__ import annotations

import bisect
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from design.folder import Corpus, Folder, decode_percent, escapes, headings_of, mask, repo_root, resolve, scan_links

SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')
BLAME_HEADER_RE = re.compile(r'^([0-9a-f]{40}) \d+ (\d+)')
MAIN_REFS = ('refs/remotes/origin/main', 'refs/heads/main')


class GitHistory:
    """The repository holding a folder: the commit of each line of a file, the commits on main, a file at a commit."""

    def __init__(self, repo_root: Path, prefix: str):
        self.repo_root = Path(repo_root)
        self.prefix = prefix  # the folder's path inside the repository with a trailing slash ('docs/'), or ''
        self._main: str | None = None
        self._main_known = False
        self._main_commits: set[str] | None = None
        self._on_main: dict[str, bool] = {}
        self._blame: dict[str, list[str | None]] = {}
        self._shows: dict[str, str | None] = {}
        self._headings: dict[str, set[str]] = {}

    @staticmethod
    def of(folder_root: Path) -> GitHistory | None:
        """The history of a folder inside a git repository; None when it is not in one."""
        try:
            r = subprocess.run(['git', '-C', str(folder_root), 'rev-parse', '--show-toplevel', '--show-prefix'],
                               capture_output=True, text=True, encoding='utf-8')
        except OSError:
            return None
        if r.returncode != 0:
            return None
        parts = r.stdout.split('\n')
        return GitHistory(Path(parts[0].strip()), parts[1].strip() if len(parts) > 1 else '')

    def _git(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(['git', '-C', str(self.repo_root), *args], capture_output=True, text=True,
                              encoding='utf-8')

    def main(self) -> str | None:
        """The main branch: origin/main, else the local main; None when neither exists."""
        if not self._main_known:
            self._main_known = True
            self._main = next((ref for ref in MAIN_REFS
                               if self._git('rev-parse', '--verify', '-q', f'{ref}^{{commit}}').returncode == 0), None)
        return self._main

    def _commits_on_main(self) -> set[str]:
        if self._main_commits is None:
            main = self.main()
            out = self._git('rev-list', main).stdout if main else ''
            self._main_commits = {l.strip() for l in out.split('\n') if l.strip()}
        return self._main_commits

    def on_main(self, sha: str) -> bool:
        """Whether sha (full or abbreviated) is a commit on main: its tip or an ancestor of it."""
        if sha not in self._on_main:
            all_ = self._commits_on_main()
            self._on_main[sha] = sha in all_ if len(sha) == 40 else any(c.startswith(sha) for c in all_)
        return self._on_main[sha]

    def _line_commits(self, rel: str) -> list[str | None]:
        """The commit that introduced each line of the folder file rel in the working tree (index 0 is line 1), None
        for an uncommitted line; empty when git cannot blame it. Blame follows renames."""
        if rel not in self._blame:
            r = self._git('blame', '--porcelain', '--', self.prefix + rel)
            out: list[str | None] = []
            if r.returncode == 0:
                for l in r.stdout.split('\n'):
                    m = BLAME_HEADER_RE.match(l)
                    if m is None:
                        continue
                    line = int(m.group(2))
                    out.extend([None] * (line - len(out)))
                    out[line - 1] = None if m.group(1).startswith('0000000000') else m.group(1)
            self._blame[rel] = out
        return self._blame[rel]

    def commit_of(self, rel: str, line: int) -> str | None:
        """The commit that introduced line (1-based) of the folder file rel; None when the line is uncommitted."""
        all_ = self._line_commits(rel)
        return all_[line - 1] if 1 <= line <= len(all_) else None

    def _show(self, commit: str, repo_path: str) -> str | None:
        key = f'{commit}:{repo_path}'
        if key not in self._shows:
            r = self._git('show', key)
            self._shows[key] = r.stdout.replace('\r\n', '\n') if r.returncode == 0 else None
        return self._shows[key]

    def existed_at(self, commit: str, rel: str, heading: str | None = None) -> bool:
        """Whether the folder file rel existed at commit, with heading among its headings when one is given."""
        key = f'{commit}:{self.prefix}{rel}'
        text = self._show(commit, self.prefix + rel)
        if text is None:
            return False
        if heading is None:
            return True
        if key not in self._headings:
            self._headings[key] = {h.text for h in headings_of(text)}
        return heading in self._headings[key]

    def latest_on_main_with(self, rel: str, heading: str | None = None) -> str | None:
        """The newest commit on main at which rel (with heading when one is given) existed; None when there is none."""
        main = self.main()
        if main is None:
            return None
        r = self._git('log', '--format=%H', main, '--', self.prefix + rel)
        if r.returncode != 0:
            return None
        return next((c.strip() for c in r.stdout.split('\n') if c.strip() and self.existed_at(c.strip(), rel, heading)),
                    None)


@dataclass
class PinReport:
    pinned: int = 0
    unpinnable: list[str] = field(default_factory=list)  # `<label>/<file>:<line>: <raw link>`


def _resolves(folder: Folder, target: str, heading: str | None, frag: str | None) -> bool:
    """Whether target (and heading, or frag as a GitHub slug) is in the working tree."""
    return folder.is_file(target) and (heading is None or folder.has_heading(target, heading)
                                       or frag in folder.slugs(target))


def history_files(folder: Folder, corpus: Corpus) -> list[str]:
    """The Markdown files whose links are pinned: the log and every history file corpus.yaml does not exclude."""
    return [f for f in folder.markdown if not corpus.is_excluded(f) and (f == corpus.log or corpus.is_history(f))]


def pin_links(folder: Folder, corpus: Corpus, git: GitHistory, label: str = 'docs') -> PinReport:
    """Pin every unpinned link of a history file whose line comes from main: to the commit of its line when its
    target existed there, else to the newest commit on main where it existed. A link on a line of this branch whose
    target is gone from the working tree is pinned to the newest commit on main with it too. A link whose target no
    commit on main has, or that carries another title, is reported and left. Writes the changed files."""
    report = PinReport()
    for f in history_files(folder, corpus):
        raw = folder.text(f)
        starts = [0] + [i + 1 for i, c in enumerate(raw) if c == '\n']
        inserts: list[tuple[int, str]] = []
        for l in scan_links(mask(raw)):
            dest = l.dest
            if l.pin is not None or l.angle or SCHEME_RE.match(dest) or dest.startswith('/'):
                continue
            if dest.partition('#')[0] == '':
                continue  # the file's own headings
            target, frag = resolve(f, dest)
            heading = decode_percent(frag) if frag and target.endswith('.md') else None
            out = escapes(target)
            line = bisect.bisect_right(starts, l.start)
            commit = git.commit_of(f, line)
            from_main = commit is not None and git.on_main(commit)
            if not from_main and (out or _resolves(folder, target, heading, frag)):
                continue  # a line of this branch: it resolves now
            at = None if out else (commit if from_main and git.existed_at(commit, target, heading)
                                   else git.latest_on_main_with(target, heading))
            if at is None or l.title is not None:
                report.unpinnable.append(f'{label}/{f}:{line}: {raw[l.start:l.end]}')
                continue
            inserts.append((l.end - 1, f' "git:{at[:12]}"'))
        if not inserts:
            continue
        text = raw
        for off, title in reversed(inserts):
            text = text[:off] + title + text[off:]
        (folder.root / f).write_text(text, encoding='utf-8', newline='\n')
        folder._texts[f] = text  # the folder reads the pinned text from now on
        folder._headings.pop(f, None)
        folder._slugs.pop(f, None)
        report.pinned += len(inserts)
    return report


def main(argv=None) -> int:
    """pin-links [root]: pin the links of the history files of the docs folder (default: the corpus root of the
    repository), print `pinned <n> links` and every link left unpinned; exit 1 when any is left, 2 without a git
    repository with a main branch."""
    args = sys.argv[1:] if argv is None else list(argv)
    root = Path(args[0]) if args else None
    try:
        try:
            repo = repo_root(root)
        except RuntimeError:
            repo = None
        corpus = Corpus.load(repo) if repo is not None else None
        if root is None:
            root = repo / corpus.root if repo is not None else Path.cwd()
        git = GitHistory.of(root) if repo is not None and root.is_dir() else None
        if git is None or git.main() is None:
            print(f'pin-links: {root} is not in a git repository with a main branch', file=sys.stderr)
            return 2
        try:
            folder = Folder.git(root)
        except RuntimeError:
            folder = Folder.dir(root)
        report = pin_links(folder, corpus, git, corpus.root.rstrip('/'))
    except (RuntimeError, ValueError, OSError) as e:
        print(f'pin-links: {e}', file=sys.stderr)
        return 2
    print(f'pinned {report.pinned} links')
    for u in report.unpinnable:
        print(f'NOT PINNED: {u}')
    if report.unpinnable:
        print(f'{len(report.unpinnable)} links not pinned: no commit on main has their target')
        return 1
    return 0
