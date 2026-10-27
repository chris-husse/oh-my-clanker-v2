# Review files

## 1. Name

A review file is `docs/reviews/YYYY-MM-DD-<slug>.md`.

The slug summarizes the single most critical finding in the file: the first finding after the
consequence sort of `triage.md`, in three to ten lowercase words joined by hyphens, shorter when
a shorter phrase still names that finding. It names a finding, not the product, an actor, or the
review process. `publish-cannot-reenter-the-design-lifecycle` is a slug. `third-validation-pass`,
`design-review`, `notes`, `review-2` are not.

Only files directly in `docs/reviews/` are review files. Two subfolders hold the rest,
and nothing in them is ever a review file:

- `docs/reviews/iterations/` holds iteration files,
  `iterations/YYYY-MM-DD-<slug>-iteration-NN.md` with the original file's date and slug and a
  two-digit counter. NN is one more than the highest counter present on disk for that slug,
  committed or not. They belong to a cycle and are never a valid argument to `/review-design`.
- `docs/reviews/raw-feedback/` holds raw feedback, the raw extracts a harvester writes and a
  review file links to; it is empty until the first one appears.

## 2. Who reads the folder

`docs/reviews/` is history (`history` in `tools/corpus.yaml`), never part of the design corpus.
Validation agents and any corpus analysis must not read it. The two skills list it and read the files of the cycle they
are running; a human reads it to learn what a decision came from.

## 3. Gate

`/review-design <file>` refuses, quoting the rule, when:

- the path is not directly in `docs/reviews/` (a file in a subfolder, raw feedback or an
  iteration, is never reviewed directly);
- the name does not match the pattern: date prefix, three to ten lowercase hyphen-joined words,
  `.md`.

The meaning rule of section 1 binds whoever creates the file, not the gate.

A review file is decided when the committed decision log carries its `Review file:` line; see
`decision-log-section.md`. The functions below do the gate, the decided check, the undecided
list and the next iteration name. The skills paste them into a subshell that starts from
`ROOT=$(git rev-parse --show-toplevel)` and runs in `ROOT`.

```bash
# All paths repo-relative, run from ROOT.
review_gate() {  # prints OK, UNCOMMITTED, or REJECT <reason>; exit 1 on REJECT
  f="$1"
  case "$f" in
    docs/reviews/*/*) echo "REJECT not directly in docs/reviews/ (raw feedback and iterations live in subfolders and are never reviewed directly)"; return 1;;
    docs/reviews/*.md) ;;
    *) echo "REJECT not directly in docs/reviews/"; return 1;;
  esac
  b=$(basename "$f" .md)
  echo "$b" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}-([a-z0-9]+-){2,9}[a-z0-9]+$' \
    || { echo "REJECT name must be YYYY-MM-DD-<slug>.md, slug three to ten lowercase hyphen-joined words"; return 1; }
  [ -f "$f" ] || { echo "REJECT file does not exist"; return 1; }
  if git ls-files --error-unmatch "$f" >/dev/null 2>&1 && git diff --quiet HEAD -- "$f"; then echo OK; else echo UNCOMMITTED; fi
}
review_decided() {  # exit 0 when the committed decision log carries the contract line
  git show HEAD:docs/decision-log.md | grep -Fxq "Review file: $1"
}
review_undecided() {  # lists every top-level review file without a committed contract line, oldest first
  for f in docs/reviews/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*.md; do
    [ -f "$f" ] || continue
    review_decided "$f" || echo "$f"
  done
}
review_next_iteration() {  # prints the path of the next iteration file (in iterations/) for a review file
  base="docs/reviews/iterations/$(basename "$1" .md)"; n=0
  for g in "$base"-iteration-[0-9][0-9].md; do [ -f "$g" ] || continue; k=${g##*-iteration-}; k=${k%.md}; k=$((10#$k)); [ $k -gt $n ] && n=$k; done
  printf '%s-iteration-%02d.md\n' "$base" $((n+1))
}
```

## 4. Slug warning

When the slug plainly names the product, an actor, or the process (review, pass, findings,
validation) instead of a finding, the skill says so, proposes a slug from the file's first
finding, and continues.

## 5. Commit question

When `review_gate` prints `UNCOMMITTED`, the file is untracked or tracked with uncommitted
changes. The skill asks once whether to commit it now with a one-line message. Yes: commit that
file alone and continue. No: stop. This is the only commit before the closing commit of the
cycle.
