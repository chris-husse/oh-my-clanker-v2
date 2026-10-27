---
name: build
description: Build the world for oh-my-clanker v2: every deterministic check of the docs folder that is not a unit test. The decision log's integrity, every link, every generated file. About 5 seconds, no LLM, no tests.
---

# build

Run every command from the project root. The stage passes when every command exits 0.

1. `just decisions check`
   The decision log's integrity. Also in `check`; cheap, and build must stand on its own.
2. `just links-check`
   Every link of `docs/`: escapes, dead files and headings, link form, unlinked rulings, wrong targets, stray
   files, pins of the log and the reviews (the rules are `docs/LINKS.md`). Exit 1 lists `PROBLEM:` lines.
   Any other non-zero exit means the checker could not run: fail.
3. `just ensure-up-to-date`
   Every generated file (`dvc.yaml`, the stages of `tools/stages.yaml`) current with its inputs. Prints `OK`,
   or the stale stages and `run /ensure-up-to-date`.

This is `just build` without its first line (pytest, which is the `check` stage). There is nothing to
compile or package: the product is Markdown plus the Python tools under `tools/`.

`unpinned` problems on lines that are on `main` mean `just pin-links` has not run since those lines
landed. The fix is the rollout step of `AGENTS.md` (`just pin-links`, commit `Links: pinned`), never
editing links by hand. A stale stage is fixed by `/ensure-up-to-date`, never by `just mark-up-to-date`.

On failure, quote the first `PROBLEM:` lines or the stale stages in the summary.
