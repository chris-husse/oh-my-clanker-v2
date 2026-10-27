---
name: reconcile-links
description: Make the links of docs/ whole again - run `just links-check`, fix every problem it reports from the context (a renamed heading, a moved or deleted file, an unlinked ruling, a wrong link text, a link to a decision not yet applied, a missing or bad pin in the log or a review file, an escaping link, a stray file), check again, and ask the owner only what the documents cannot decide. Run by the owner, or by a skill that writes into docs/ when its links check fails.
---

# Reconcile the links of docs/

The rule is `docs/LINKS.md`; read it whole first. `just links-check` is the judge: it prints one
`PROBLEM: <file>:<line>: <kind>: <detail>` per break and `WARNING: … unlinked?: …` per bare number that may be a
ruling, then `OK` or `<n> problems`.

Every command starts from `ROOT=$(git rev-parse --show-toplevel)`. Scratch files and the list of changed files are
the worktree's own, under `"$ROOT/.cache/reconcile-links/"` (`.cache/` is gitignored), so two worktrees never share
them. Write the rounds into the task list. Before the first round: `ROOT=$(git rev-parse --show-toplevel); mkdir -p
"$ROOT/.cache/reconcile-links" && rm -f "$ROOT/.cache/reconcile-links/"*.txt`.

**Text that must not change.** `docs/decision-log.md` is written only by `just decisions`, and `docs/design/` and
`docs/e2e-tests/` are protected (`AGENTS.md`). In these three places this skill changes only link destinations
(the path and the anchor) and pin titles, or wraps a bare ruling number in a link, so the link-free text, the link
texts included, never changes (`just decisions check` would report `edited` otherwise). A fix that needs any other
change there (a link text, a sentence, a code span, a moved or deleted file) is a question to the owner (see "Ask").

## Each round

1. `ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just links-check) > "$ROOT/.cache/reconcile-links/check.txt"`.
2. Fix every `PROBLEM` line by reading the file around the line, and the target:
   - `dead-heading`: the heading was renamed. Find it in the target file by the reference's id (`2.6` in
     `02 §2.6`, `1.2` in `ruling 1.2`), else by meaning, and write its text as the anchor (every space as `%20`,
     every backtick as `%60`, see `docs/LINKS.md`); the link text stays. If the link text then no longer names the
     target, fix it only outside the log, `docs/design/` and `docs/e2e-tests/`; there, ask. Gone entirely: see "Ask".
   - `dead-file`: the file moved or was renamed: `git log --follow --name-status --format=%h -- <old path>` names the
     new path. Deleted: link what replaced it per `docs/decision-log.md`; nothing did: see "Ask". A folder: link its
     README or the file meant.
   - `form`: rewrite the link in the form `docs/LINKS.md` gives; the detail names the exact anchor to write. In the
     log, `docs/design/` and `docs/e2e-tests/` only a destination may change; a rewrite that changes what the link
     reads as is a question to the owner.
   - `unlinked`: a ruling number written bare after "ruling", "rulings" or "decision log", or inside a parenthesis
     of references: wrap it in the link the detail names.
   - `wrong-target`: decide from the sentence whether the text or the target is right, and fix the other. In the
     log, `docs/design/` and `docs/e2e-tests/` only the target may change: when the text is the wrong half, ask.
   - `escape`: the target is outside `docs/`. Link a file in `docs/` that says the same, or write the path as text
     in a code span (a text change: in the log, `docs/design/` and `docs/e2e-tests/` ask instead).
   - `stray`: `docs/` holds only Markdown and the images its pages embed. Move the file out of `docs/` to where its
     readers look for it (ask where if no document says), or embed an image where a page shows it, or delete the
     file if nothing uses it (check with `git grep`). A stray under `docs/design/` or `docs/e2e-tests/`, or an
     embed that would be added there, is a question to the owner.
   - `unapplied-target`: the document links a decision that is not applied yet. Do not change the link; finish
     applying the decision (`/apply-decision <id>`), or, when the target is a note or a section heading of the log,
     link the applied decision the sentence means.
   - `unpinned` (the log or a review file, a line from main): run `just pin-links`; it pins the link to a commit on
     main where its target existed (`docs/LINKS.md`), and so a link of this branch whose target is gone. A link it
     lists as not pinnable never had its target on main: fix it as a `dead-file` or `dead-heading` one; the edited
     line is this branch's, so it then resolves now.
   - `pin` or `dead-pin`: the pin names no commit on main, or its target was not there at it. Remove the title
     (` "git:…"`); the edited line is then this branch's, so the link must resolve now (fix it as a `dead-file` or
     `dead-heading` one, changing the destination only, never the link text), or, when its target is gone today,
     `just pin-links` pins it anew to the newest commit on main that has it. `just pin-links` never touches a link
     that still carries a title.
3. For every `WARNING … unlinked?` line read the sentence: a ruling number gets its link
   (`[1.2](…/decision-log.md#1.2%20…)`); anything else (a section number, an amount, a version) stays as it is.
   When many warnings remain, split them by folder and give each folder to one subagent (`general-purpose`,
   `model: opus`, at most 20 in one message) with this brief: "Read `docs/LINKS.md`. For each line of
   `.cache/reconcile-links/<folder>.txt` (a `WARNING … unlinked?: <number>: link it to <target>` line), read the
   sentence in the file: if the number names that decision-log ruling, wrap it in the link given; otherwise leave it.
   Edit only the files listed, and only by wrapping the number. Do not run git or just."
4. Run the check again. At most three rounds; the round's fixes must reduce the count each time.

## Ask

A problem the documents cannot settle (a target gone with no successor, two readings of a sentence that both fit),
or a fix that would change text the rule "Text that must not change" keeps, goes to the owner: one question per problem, with the file, the sentence, the old target and what each answer would
write. Wait for the answer; write it; continue the round.

## End

`just links-check` prints `OK`. Write every file this run changed, repo-relative, one per line, to
`"$ROOT/.cache/reconcile-links/changed.txt"` (a moved file with both paths, a deleted one with its old path); list an
old or deleted path only if git tracks it (`git ls-files --error-unmatch -- <old path>` succeeds), so an untracked
stray cannot abort the commit that reads the list. When the run changed nothing, leave the file empty or absent.

Run as a step of a skill that commits (`/apply-decision`, `/review-design`, `/validate-design`): commit nothing;
that skill commits the files changed here with its own, from that list. Run alone: report the files changed and the problems fixed per kind, and commit only on the owner's word:

```bash
ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && L=.cache/reconcile-links/changed.txt && [ -s "$L" ] && xargs -d '\n' git add -- < "$L" && xargs -d '\n' git commit -m "Links: reconciled" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -- < "$L")
```

Edit only Markdown under `docs/` (and `.cache/reconcile-links/`), within the rule "Text that must not change";
scratch stays under `.cache/reconcile-links/`.
