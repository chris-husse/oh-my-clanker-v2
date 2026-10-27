---
name: record-decision
description: Record one decision of the owner in docs/decision-log.md through the decision tool - make it well formed (title, context, decision, a link for every reference), find the design sections it affects and the rulings it supersedes, show the prepared `just decisions add-decision` call, run it on the owner's word. Edits no document; /apply-decision does that.
disable-model-invocation: true
---

# Record a decision

Argument: the decision in the owner's words, with whatever context they gave. The format is
`.claude/skills/decision-log/format.md`; read it first. The link rule is `docs/LINKS.md`. Every command starts from
`ROOT=$(git rev-parse --show-toplevel)`.

1. **Separate context from decision.** Context is why: what was wrong, what was asked. Decision is what now holds,
   in one to three sentences. Missing context, or a decision that could be read two ways, is one question to the
   owner, never a guess. Each field is one line. Every design section, ruling or review item either field mentions
   is a Markdown link relative to the docs root, its anchor encoded (`[2.6](design/02-repos-and-config.md#2.6%20Trust)`,
   a ruling `[1.2](#1.2%20<its title>)`); the tool checks that each resolves and infers none.
2. **Title.** One line, the decision's gist, in the style of the existing headings
   (`(cd "$ROOT" && just decisions list | tail)`).
3. **Affected.** Find what the decision changes. Read `docs/design/README.md` (the documents and what each
   covers), then the headings of the corpus:
   `(cd "$ROOT" && git ls-files -co --exclude-standard -- 'docs/design/*.md' 'docs/e2e-tests/*.md' | xargs grep -n '^##')` (the corpus is what
   `tools/corpus.yaml` lists under `corpus`). Read the candidates and keep the ones the decision really changes, each
   as a link argument `<docs-relative path>#<heading text>` (`design/02-repos-and-config.md#2.6 Trust`), or the file
   alone for a whole document. The applier replaces the set with the real one later, so a best guess is fine, an
   empty set is fine, an invented one is not.
4. **Supersedes.** For each affected target run `(cd "$ROOT" && just decisions search --affected "<path>[#<heading>]")`
   and `just decisions history "<path>[#<heading>]"`, and read the hits. A hit the new decision contradicts goes to
   `--supersedes` by its id (`1.2`). A decision that contradicts an applied decision must name it; the log never
   corrects in place.
5. **Source.** When the decision answers a review item, the item's heading in its review file:
   `--source "reviews/<file>.md#<item heading>"`, and its id in `--answers`. Otherwise no `--source`.
6. **Show the call.** Print the fields and the full command to the owner:

   ```bash
   ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just decisions add-decision --title "…" --context "…" --decision "…" --affected "design/02-repos-and-config.md#2.6 Trust" "design/04-mcp-and-cli.md" --supersedes 1.2 --source "reviews/<file>.md#<item heading>" --answers "R7")
   ```

   Wait for the owner's word. A correction is applied to the fields and shown again.
7. **Run it.** The tool prints the id, or refuses with the reason (no such file, no such heading, a note, a field
   that holds a newline or starts like log structure) and writes nothing; fix the argument and run again. Then
   `(cd "$ROOT" && just decisions show <id> && just links-check)`.
8. **Report** the id and the title, and say: `Next: /apply-decision <id>.` Commit nothing: the recorded entry is
   committed with its application.

## Never

- Edit a design document or the log by hand.
- Record a decision whose context or decision the owner did not give.
- Start `/apply-decision` or any other skill on your own.
