---
name: decision-log
description: "The decision log's shared tool and entry format - `just decisions` reads docs/decision-log.md, searches entries by affected link, source, supersedes, status, section, date or text, writes new decisions and notes, and marks decisions applied; `format.md` is the entry contract. Not a command; /record-decision, /apply-decision, /how-we-got-here and /review-design use it."
user-invocable: false
---

# The decision log

`docs/decision-log.md` is the one append-only record of every ruling about the design, and the tool
`tools/design/decisions.py` is its only writer. Nobody edits the log by hand.

- `format.md`: the entry, field by field, the link arguments, every subcommand and the check.
- `Automated` is structured provenance: true for a proposed ruling the owner bulk-accepted in
  `/review-design`, false for a human-recorded ruling; missing on legacy entries means unspecified,
  counted as human. Use `add-decision --automated` only from that review flow; with `--supersedes`
  it accepts only automated targets that no human ruling has superseded. Search with
  `--automated true|false|unspecified`. Application preserves provenance; automated rulings carry
  less weight and never overrule a human or legacy ruling.
- `just decisions <subcommand> …` runs the tool from the repository root; `just decisions --help` lists the
  subcommands, `just decisions <subcommand> --help` their flags. `just decisions check` runs in `just build`.
- What `docs/` holds, which files are corpus and which are history, is declared in `tools/corpus.yaml`; the link
  rules are `docs/LINKS.md`.
- `/record-decision` makes a decision well formed and records it. `/apply-decision <id>` makes the corpus say what a
  recorded decision says and marks it applied, one commit each. `/how-we-got-here <question>` answers how the design
  came to be from the decision history of a design section, an E2E definition or a ruling.
