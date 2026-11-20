---
name: screens-assess
description: "Give every changed screenshot one verdict per (base, current) hash pair, judged once, in the branch's verdicts' yaml (just omc shots path), sorted into unexpected and expected; restores, amends and commits nothing. Ends with its OUTCOME line."
---

# screens-assess

A terminal of the `omc/` pipeline. It runs in a fresh subagent and never speaks to the owner: it lists the shots that
differ from the base by their Git LFS hash pair, judges each pair that has no verdict yet against the branch's intent,
writes the verdicts into the branch's yaml, and ends with one `OUTCOME` line. A changed picture is evidence, of the
change the branch meant or of a feature it broke; the owner's screenshot review decides what becomes of it, not this
terminal. Its caller writes its role at each call: `orchestrator` (it reads intent, not code).

**The project's notes**, `omc/bin/screens-assess.md`, when the project has one, are read first and followed where they
say more than this file: where a shot's screen is described (the pages that tell what it shows), the files a change of
the screens reaches (a style, shared parts), how a shot's id reads, and a grouping tool of the project's own (section
3). Without them, the shots' screens are found by their id in the protected documents (`paths.protected`).

**Inputs** (in the prompt, one per line). `Root:` the worktree. `base:` the commit the shots are compared with;
without it, the merge-base with `origin/<base>` (`base` of `omc/config.yaml`). `mode: changed` or `mode: all`; without
it, `changed`. `yaml:` the path of the verdicts' file; without it, the branch's, the path `just omc shots path` prints
(`<paths.questions>shots/<slug>.yaml`, `<slug>` the branch without `branch_prefix`); a review outside the run passes a
path under `.cache/`, where everything of that review stays.

**What it writes.** The yaml, and the pictures it looks at under `.cache/shots/assess/`; nothing else. It restores no
shot, stages nothing, amends nothing and commits nothing: the caller commits the changed shots as they are together
with the yaml, so that the reviewed pair is the committed one. It edits no protected document (a file `paths.protected` matches), no code, no test, writes no entry and no question file, and
runs no build, no test, no render and no gate. Its only `just` commands are `just omc shots pairs`,
`just omc shots path`, `just omc record`, `just decisions list` and `just decisions show`; its only other command of
the project's is the grouping tool the notes name.

**Shell.** Variables do not survive between commands: run each in the root given, `(cd <root> && …)`; a value a
command printed (the base, an id, the slug) is written out in the next one.

## 1. The pairs

The base (only when no `base:` was given; `<base-branch>` is `base` of `omc/config.yaml`) and the yaml's path (only when
no `yaml:` was given):

```bash
(cd <root> && git merge-base HEAD origin/<base-branch>; just omc shots path)
```

then, `<base>` written out from the input or from that first line, the pairs:

```bash
(cd <root> && mkdir -p .cache/shots/assess && just omc shots pairs --base <base> > .cache/shots/assess/pairs.json && jq length .cache/shots/assess/pairs.json)
```

`pairs.json` is a list, one item per shot (a file `paths.screenshots` matches) that differs from the base, sorted by
id: `id` (the file name without its extension), `path` (the shot's file; the base's for a removed one), `base` (the
sha256 of the base's LFS object, `null` for an added shot), `current` (the sha256 of the working tree's file, `null`
for a removed one) and `row`. A pair whose two pictures are of one size with no pixel
differing over 16 in a channel is not in it: a re-encode is not a review item. Every shot in the working tree counts,
committed or left there by `verify`.

With `mode: all`, section 5. With `mode: changed` and an empty list: no shot differs; the yaml, when there is one, is
written with no row (section 4), and the outcome is `none`.

## 2. The lookup

A pair whose row in the yaml holds the same `base` and the same `current` is kept as it is, its verdict and the
owner's `review` field included, and is not judged again. With the default yaml, `row` is that row (`null`: no row
for this pair). With another `yaml:`, `row` was read from the default path and does not count: the terminal reads
the given yaml itself and keeps a row only when both its `base` and `current` equal the pair's, character for
character (`null` equal only to `null`). A row of an earlier pair of the same shot is never kept: its shot is judged
again. The pairs left are the ones to judge; none left: section 4, `judged: 0`.

## 3. The judgement

**The pictures**, for every pair (the kept ones too, for the grouping), out of Git LFS, into `.cache/shots/assess/`,
never /tmp:

```bash
(cd <root> && A=.cache/shots/assess && rm -rf $A/base $A/current && mkdir -p $A/base $A/current && jq -r '.[] | [.id, .path, (.base // "-"), (.current // "-")] | @tsv' $A/pairs.json | while IFS="$(printf '\t')" read -r id f b c; do if [ "$b" != - ]; then git show "<base>:$f" | git lfs smudge > "$A/base/$id.png" 2>/dev/null; fi; if [ "$c" != - ]; then git lfs smudge < "$f" > "$A/current/$id.png" 2>/dev/null; fi; for p in "$A/base/$id.png" "$A/current/$id.png"; do [ -e "$p" ] && { [ "$(head -c 4 "$p" | tail -c 3)" = PNG ] || echo "error: $p is not a picture"; }; done; done)
```

`git lfs smudge` turns a pointer into its picture and passes a picture through (without Git LFS, `git show` and the
file give the picture itself). An `error:` line (the LFS object is missing) is `failed`, with the line: a pair is never
judged without its pictures.

**The grouping**, the shared cause of several shots: the project's grouping tool, when its notes name one, run as they
say over `.cache/shots/assess/` (a shot's `group` and a group's origin from its output); else this terminal's own
reading: shots that change for one cause (one entry, one commit, one shared page or style) share a `group`, its title
naming that cause.

**What explains a change**, read once for all the pairs:

- the log's entries of the branch (`just decisions list --branch`, then `just decisions show <n>` for each that names a scene,
  its page, its view or a component its view's tree names);
- the record (`just omc record` lists the branch's records; the sections on the screens it reaches);
- the branch's commits, `git log --format='%h %s%n%b' <base>..HEAD`;
- per shot, its pages: where the project's notes say a shot's screen is described, else the protected documents that
  name its id (`git grep -l -F <id> <base> --` over `paths.protected`); the change of each since the base,
  `git diff <base> -- <page>`.

**Each pair to judge, every one, never a sample:** both pictures opened with the Read tool, which shows a PNG (an
added shot has its current picture only, a removed one its base picture only), then exactly one verdict:

| verdict | bucket | meaning |
|---|---|---|
| `explained` | expected | an entry, the record or a commit asks for exactly this change |
| `cosmetic` | expected | a shift no one asked for and no one would mind (antialiasing, a pixel of padding) |
| `unexplained` | unexpected | a visible change nothing on the branch explains |
| `broken` | unexpected | clipped, overlapping, missing, an error view, a layout that contradicts its page |

- `reason`: one or two sentences for the owner, what differs and what it was checked against.
- `cause`: what explains it, `decision <n>`, a commit's short sha or `record`; `null` when nothing does (every
  `unexplained` and most `broken`).
- `group`: the shared cause's title from the grouping when several shots change for one reason, else `null`.
- `review`: `null`; only the owner's review sets it.

A change that cannot be placed is `unexplained`, never a guess. An explained change with a defect (the intended
header, clipped) is `broken`. A picture that is the intended change while its screen page no longer says what it
shows is `explained`, its `reason` naming the page that lags.

## 4. The file

The yaml, at the path of the inputs, `base` the base's short sha:

```yaml
# docs/reviews/shots/new-settings-page.yaml
base: 4b140e5
shots:
  settings.detail:
    base: 3f9a…            # sha256 of the base LFS object, or null (added)
    current: 81c2…         # sha256 of the current file, or null (removed)
    bucket: unexpected
    verdict: broken
    reason: "the header overlaps the photo; no entry or commit explains it"
    cause: null
    group: null
    review: null           # set by the owner's review: accepted | commented (round n) | accepted (carried)
```

The rows are the kept rows and the new ones, one per pair of `pairs.json`, sorted by id, the hashes written whole.
Rows of shots that no longer differ from the base, and rows of earlier pairs, are dropped. Written atomically: the
whole file to `<yaml>.tmp` beside it (the Write tool), then `mv <yaml>.tmp <yaml>`; its directory made first
(`mkdir -p`). Then it is read back with
`(cd <root> && UV_PROJECT_ENVIRONMENT=.cache/venv uv run --frozen python -I -c "import sys, yaml; d = yaml.safe_load(open(sys.argv[1])); print(len(d['shots'] or {}))" <yaml>)`,
which prints the number of rows: the count of `pairs.json`, else `failed`.

## 5. `mode: all`

It writes no verdict and no file: every shot (`paths.screenshots`) is listed in the report, the changed
ones (those of `pairs.json`) with the verdict, bucket and reason of their row when the yaml has one for their current
pair, the others as unchanged. The counts of the outcome are those rows'; `judged` is 0, and `file` is the yaml's
path when it exists, else `null`.

## The outcome

The report above the line is prose for the caller: the base, every pair (its id, its two hashes' first 8 characters,
kept or judged, its verdict, bucket, cause and group, and for a judged one what it was checked against), the groups,
and the yaml's path. The last line is one of:

```text
OUTCOME {"outcome": "done", "unexpected": 2, "expected": 9, "judged": 4, "file": "<the yaml's path>"}
OUTCOME {"outcome": "none"}
OUTCOME {"outcome": "failed", "reason": "error: .cache/shots/assess/base/menu.png is not a picture"}
```

`unexpected` and `expected` count the yaml's rows of each bucket, kept rows included; `judged` counts the pairs judged
in this run. A shot that needs the owner's word is not a `needs_user` of this terminal: its verdict (`unexplained`,
`broken`) carries it to their review.

## Never

- Never judge from a sample: every pair without a kept row is judged, both its pictures opened.
- Never judge a pair again whose row holds its two hashes; never keep a row whose hashes differ from the pair's.
- Never restore, check out, stage, add, amend, commit or delete a shot or the yaml: the caller commits them.
- Never edit a file but the yaml: no protected document, no code, no test, no record.
- Never write the log or an entry, never record a decision, never write a question file.
- Never build, test or render: no `/check`, `/build`, `/verify`, no `just omc gate run`, no gate command of `omc/bin/`,
  no command that writes the shots, no gate.
- Never start an agent or a skill that starts one or that talks to the owner: the report and the `OUTCOME` line are
  the whole answer.
