---
name: ensure-up-to-date
description: Bring every generated file up to date with its inputs - run `just ensure-up-to-date`, then the skill of each stale stage of tools/stages.yaml in file order, checking again after each, until the check prints OK and nothing generated is left uncommitted. With no stage declared (today) the check prints OK and the skill stops. Run by the owner when the check, `just build` or the pre-push hook says "run /ensure-up-to-date".
---

# Ensure up to date

The stages are those of `tools/stages.yaml`, in file order: for each its `skill`, `inputs`, `outputs`, and optional
`each`, `root` and `exclude`. `just ensure-up-to-date` is the judge: it generates `dvc.yaml` from that file in
memory, compares each stage's recorded inputs and outputs in `dvc.lock` with the tree, and prints `OK`, or each stale
stage (`<stage>: <n> stale (<skill>)`) with what moved, ending with `run /ensure-up-to-date`. `--full` lists every
stale item where the default shows the first ones and `… and <n> more`. With no stage declared (`stages: {}`) the
check prints `OK` and this skill stops there.

The owner invoking this skill is the permission for the whole run: every stage's skill below and its agents. When
the run ends, so does the permission. Write the stale stages into the task list before starting; each skill run is a
task.

## The loop

1. `ROOT=$(git rev-parse --show-toplevel); (cd "$ROOT" && just ensure-up-to-date; git status --porcelain -- dvc.yaml dvc.lock docs)`.
   `OK` and no file listed: stop and report. `OK` with files listed: they are a stage's regenerated files left
   uncommitted; commit them with their stage's skill, or stop and report them.
2. Take the first stale stage in the order of `tools/stages.yaml` and run the skill the check names for it (its
   `skill` there), which ends by marking its stage (`just mark-up-to-date <stage>`) in its own commit.
   A line `dvc.yaml is out of step` alone (no stage listed) means files were added, removed or moved without a
   stage's skill: run the skill of the stage that owns those files. When only `tools/stages.yaml` changed and no
   stage is stale, `just mark-up-to-date --generate-only` rewrites `dvc.yaml` and marks nothing; commit `dvc.yaml`
   with the change to `tools/stages.yaml`.
   A line `out <path> deleted` means a stage's output is missing: run that stage's skill, which writes it again.
   Never mark a stage (`just mark-up-to-date <stage>`) without its skill having regenerated it, and never to quiet
   the check.
3. Go back to 1: an earlier stage usually makes later ones stale.

Stop when the check prints `OK` and step 1 lists no file, or at a question only the owner can answer, or when the
same stage is still stale after its skill ran twice (report it; something is wrong with the stage or the skill).

## Report

The stages regenerated, the commits each made, and the check's final `OK`.
