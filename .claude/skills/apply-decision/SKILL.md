---
name: apply-decision
description: Apply one recorded decision of docs/decision-log.md to the design corpus (docs/design/, and docs/e2e-tests/ when it exists), record the real affected set with `just decisions apply-decision`, and commit the documents and the log together, the decision as the commit message. Needs a tree clean but for the log and docs/reviews/iterations/. With no argument lists the recorded decisions and stops. It commits: run it only on the owner's word, or as step 7 of /review-design, which invokes it through the Skill tool.
---

# Apply a decision

Argument: a decision id (`2.3`). The format is `.claude/skills/decision-log/format.md`; the link rule is
`docs/LINKS.md`. Every command starts from `ROOT=$(git rev-parse --show-toplevel)`.

With no argument: `(cd "$ROOT" && just decisions search --status recorded --oneline)`, print it, stop.

1. **Gate.** `(cd "$ROOT" && git status --porcelain)` may list only `docs/decision-log.md` (modified: the recorded
   entries waiting to be applied) and files under `docs/reviews/iterations/`; anything else stops with the list.
   `just decisions show <id>` must show `**Status.** recorded …`; an applied entry or a note stops with that word.
2. **History.** For every link in the entry's `Affected` and `Supersedes`, run
   `(cd "$ROOT" && just decisions history "<path>[#<heading>]")` (a superseded ruling by its id, `1.2`, a log section
   as `§N`) and read it whole. Edit from the full history of a passage, never from this one entry alone.
3. **Read the documents** the history and the entry name: the corpus files `tools/corpus.yaml` lists
   (`git ls-files -co --exclude-standard -- 'docs/design/*.md' 'docs/e2e-tests/*.md'`), starting from `docs/design/README.md`.
4. **Edit.** Make every passage the decision reaches say what the decision says, in the corpus's own words, changing
   nothing the decision does not require. A passage the decision reaches may be one the entry did not name; the
   real set is what you touched. Every reference you write is a link (`docs/LINKS.md`); a link to this decision,
   `[<id>](../decision-log.md#<id>%20<title>)` from inside `docs/design/`, is valid once the entry is applied, which
   step 5 does before the check of step 6 (links into the log target only applied decisions).
5. **Record the real set.**

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions apply-decision --id <id> --affected "design/<file>.md#<heading>" "design/<file>.md")
   ```

   A decision that changed no document: `--no-change` instead of `--affected`. The tool refuses an unknown file or
   heading and writes nothing; fix and run again.
6. **Links.** `rm -f "$ROOT/.cache/reconcile-links/changed.txt"; (cd "$ROOT" && just links-check)` must print `OK`;
   otherwise `/reconcile-links`, which lists the files it changed in `.cache/reconcile-links/changed.txt`.
7. **Commit** exactly the log and the files you changed; the log goes in whole, so other entries recorded and not
   yet applied travel with it. The subject is the entry's title; the body is the entry's text without links, from
   `just decisions body <id>`, so an anchor with parentheses survives; the trailer names the decision. Title and
   body travel in shell variables, never pasted into the command, so a backtick or a `$` in them is not read by the
   shell. The last `-m` is one paragraph: `Decision: <id>` and the attribution line with no blank line between them,
   so git reads both as trailers.

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && title=$(just decisions show <id> | sed -n '1s/^### [0-9][0-9]*\.[0-9][0-9]* //p') && body=$(just decisions body <id>) && test -n "$title" && test -n "$body" && git add docs/decision-log.md <files> $(cat "$ROOT/.cache/reconcile-links/changed.txt" 2>/dev/null) && git commit -m "$title" -m "$body" -m "Decision: <id>
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- docs/decision-log.md <files> $(cat "$ROOT/.cache/reconcile-links/changed.txt" 2>/dev/null) && git show --stat --format=%h HEAD)
   ```

8. **Report** the commit and the files. One decision per run; the owner runs the next.

## Never

- Apply with uncommitted changes in the tree other than `docs/decision-log.md` and `docs/reviews/iterations/`, or
  apply two decisions in one commit.
- Change `Context` or `Decision`; a wrong decision gets a successor through `/record-decision` with `--supersedes`.
- Edit the log by hand; `just decisions apply-decision` is the only write to it.
