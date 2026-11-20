---
name: reconcile-links
description: Make the docs vault's links whole again - run `just links-check`, fix every problem it reports from the context (a renamed heading, a moved or deleted file, an unlinked reference, a stale rule reference, an escaping link), check again, and ask the owner only what the documents cannot decide. Run by the owner, or as the last step of a skill that writes into the docs vault.
---

# Reconcile the vault's links

The vault is the top folder of `paths.decision_log` of `omc/config.yaml` (`docs/` by default); `just links-check` reads
the protected documents (`paths.protected`), the theme files (`paths.themes`), the question files (`paths.questions`)
and the log. The rule is the vault's `LINKS.md`, where the project keeps one; read it whole first. `just links-check` is
the judge: it prints one `PROBLEM: <file>:<line>: <kind>: <detail>` per break, then `OK` or `<n> problems`.

Every command starts from `ROOT=$(git rev-parse --show-toplevel)`. Scratch files go to `/tmp/reconcile-links/`; the
list of changed files is the worktree's own, `"$ROOT/.cache/reconcile-links/changed.txt"` (`.cache/` is gitignored).
Before the first round: `ROOT=$(git rev-parse --show-toplevel); mkdir -p
/tmp/reconcile-links "$ROOT/.cache/reconcile-links" && rm -f "$ROOT/.cache/reconcile-links/changed.txt"`.

## Each round

The protected documents (the files `paths.protected` matches) change only through the log. There this skill changes only
a link's target, a link's wrapper (a reference wrapped in a link, a link made plain text) and a story's `@hash`: what
the guard reads past. Anything else there (a link's text, a story's subtheme id, a moved or deleted page) needs a
decision, never written here: take it through `/answer-doubt` (it records an `Automated` entry when the docs settle it,
else writes the question to the run's question file for the owner), never `/record-decision` on your own; leave the
problem and list it in the End with the entry or the question, which `/review-decisions` carries through.

1. `ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just links-check) > /tmp/reconcile-links/check.txt`.
2. Fix every `PROBLEM` line by reading the file around the line, and the target:
   - `dead-heading`: the heading was renamed. Find it in the target file by the reference's id (`W16`, a subtheme's
     `T9.2`), else by meaning, and write its text as the anchor (every space as `%20`, every backtick as `%60`, see
     `LINKS.md`). Gone entirely: see "Ask".
   - `dead-file`: the file moved or was renamed: `git log --follow --name-status --format=%h -- <old path>` names the
     new path. Deleted: link what replaced it (the commit that deleted it says); an old ruling or design page a rule's
     source cites becomes plain text (`LINKS.md`); nothing replaced it otherwise: see "Ask". A folder: link its README
     or the file meant.
      - `form`: rewrite the link in the form `LINKS.md` gives; the detail names the exact anchor to write.
   - `unlinked`: wrap the reference in the link the detail names.
   - `wrong-target`: decide from the sentence whether the text or the target is right, and fix the other (the text,
     in a protected document: a decision, above).
      - `escape`: the target is outside the vault. Link a file in the vault that says the same, or write the path as
        text in a code span (in a protected document: a decision, above).
   - `unpinned` (a review file, a link whose target is gone): run `just pin-links`; it pins the link to the newest
     commit on `<base>` (the base branch, `base` of `omc/config.yaml`) where its target existed (`LINKS.md`). A link
     it lists as not pinnable never had its target on `<base>`: fix the link so it resolves now.
   - `pin` or `dead-pin`: the pin names no commit on `<base>`, or its target was not there at it. Remove the title
     (` "git:…"`); the edited line is this branch's, so the link must resolve now (fix it as a `dead-file` or
     `dead-heading` one when its target is gone).
      - `stale-rule` or `orphan-rule` (a story's `**Rules.**` line, `LINKS.md`): a `stale-rule` means the subtheme's
        heading changed; re-read the story against the renamed subtheme, and if it still rests on it, write the new hash
        the detail prints. An `orphan-rule` means the subtheme is gone: find where its rules went (the theme files' git
        history); naming that subtheme in the story is a decision (above). Nowhere: see "Ask".
3. Run the check again. At most three rounds; the round's fixes must reduce the count each time.

## Ask

A problem the documents cannot settle (a target gone with no successor, two readings of a sentence that both fit)
goes to the owner: one question per problem, with the file, the sentence, the old target and what each answer would
write. Wait for the answer; write it; continue the round.

## End

`just links-check` prints `OK`, or only the problems this skill leaves are left: list them for the owner: the problems
of a protected document waiting for a decision, with the entry's id. Write every file this run changed, repo-relative,
one per line, to `"$ROOT/.cache/reconcile-links/changed.txt"` (a moved file with both paths, a deleted one with its old
path); list an old or deleted path only if git tracks it (`git ls-files --error-unmatch -- <old path>` succeeds), so an
untracked stray cannot abort the commit that reads the list. When the run changed nothing, leave the file empty or
absent. Run as a step of a skill that commits: that skill commits the files changed here with its own, from that list.
Run alone: report the files changed and the problems fixed per kind, and commit only on the owner's word (`git add` of
the changed files by name; message `Links: reconciled`; the attribution line). Edit only Markdown under the vault.
