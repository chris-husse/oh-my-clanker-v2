# Design reviews

History, not corpus. Every file directly in this folder is a review file: a set of comments on the design as it
arrived, from an agent pass, a colleague's notes or the owner's own list. The decision log says what each one led
to. A review file is decided when the committed decision log carries the line `Review file: docs/reviews/<name>`.

Rules:

- Three places. Review files sit directly in `docs/reviews/`, and only those are review files. `iterations/` holds
  the validation passes of one review cycle, `iterations/YYYY-MM-DD-<slug>-iteration-NN.md`. `raw-feedback/` is
  reserved for raw feedback as a future harvester gathers it, which a review file then links to; it is empty for
  now. Each subfolder appears with its first file. Nothing in a subfolder is ever reviewed directly.
- Names are `YYYY-MM-DD-<slug>.md`. The slug names the most critical finding in the file in three to ten lowercase
  hyphen-joined words; it never names the project, a role or the review process itself.
- Nothing here is a ruling. Comments are suggestions until the owner rules through `/review-design`.
- Nothing here is design. Agents never read this folder, except the file under review and its iterations, which
  the review skills (`/review-design`, `/validate-design`) read for the cycle they run. A person reads it to learn
  what a decision came from.
- The links in these files are pinned once their lines are on `main` ([LINKS.md](../LINKS.md)).
