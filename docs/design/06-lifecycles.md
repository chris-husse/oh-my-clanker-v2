# 6. Lifecycles, plugins and hooks

The model is Maven's: a **lifecycle** is an ordered pipeline of **plugins**; a
**hook** is a lightweight extension point a plugin calls, merging many
contributions into one result.

## 6.1 Lifecycles

- The lifecycles are `design`, `implement`, `review` and `publish`. More will be
  added later, before `design`.
- Each lifecycle is an ordered list of plugins. omc ships a default list per
  lifecycle; your omc repo's `config.yaml` or a repo's `repo.yaml` can override it,
  e.g. `design: [explain-seed, pocock-grilling-with-docs, approve-design]`.
- omc provides a sane default harness, but a lifecycle can be configured down to
  an empty shell that does nothing, if a repo wants that.
- A lifecycle takes one artifact in and produces one artifact out. For `design`,
  the input is the seed and the output is one root design document named after
  the slug, which may link to sub-documents and references it created. Only the
  root document is passed from plugin to plugin.

## 6.2 Plugins

- **Artifact in, artifact out.** Each plugin reads the previous plugin's root
  document and writes its own version.
- **Working folders live in `/tmp`,** never in a repo or omc's cache:
  `/tmp/omc2/lifecycle/<repo-key>/<branch-file>/<lifecycle>/`, mode `0700`.
  - The lifecycle input sits at the top, e.g. `design/seed.md`.
  - Plugin N writes `design/<plugin>/<slug>.md` and may create any other
    artifacts in its own folder.
  - A plugin can read every earlier plugin's folder for context. It does not
    write to them (a convention, not enforced).
  - If a session dies, you start the lifecycle over or dig out the temp folder.
  - Retention follows [03 §3.8](03-watch.md#3.8%20%60/tmp%60%20retention). The folder is deleted after the final
    artifact is committed.
- **Manifest = intent.** A plugin's manifest only declares which lifecycle(s) it
  was built for ("I made this as a design-lifecycle plugin"). omc defines each
  lifecycle's plugin contract once, and every plugin is written against it.
- **Prerequisites** are `<match>` checks in the plugin's own skill text; a missing
  one renders the plugin as only an ABORT with install instructions
  ([05-skill-rendering.md](05-skill-rendering.md)).
- **All plugins run inline in the main session,** because they are inlined skill
  text. A plugin that wants subagents starts and manages them itself.

## 6.3 Commands and the handoff between plugins

- **`omc lifecycle <lifecycle>`** prints a small orchestrator: what the lifecycle
  is for, the plugin order, the handoff rule, and what comes after.
- **`omc lifecycle <lifecycle> --<plugin>`** renders one plugin's skill with its
  hooks inlined.
- **`omc lifecycle <lifecycle> --done <plugin>`** is how every plugin ends (the
  OptMem pattern: "run it and do exactly what it prints"). Python:
  1. checks the plugin's output exists and passes the lifecycle's and the
     plugin's checks (e.g. required sections);
  2. records progress in the lifecycle temp folder;
  3. prints the next plugin's rendered skill.

  A failed check is fatal and names exactly what is missing; the model fixes it
  and runs `--done` again. This replaces v1's prose state machines, which lost
  their place across nested skills.
- **After the last plugin,** `--done` prints the lifecycle's closing statement
  instead: how to continue into the next lifecycle. Handing off to the next
  lifecycle is the orchestrator's job, never a plugin's.
- **`omc lifecycle <lifecycle> --from <plugin>`** resets progress to that plugin,
  which takes the current document as input; every later plugin reruns.

## 6.4 Hooks

- **omc defines every hook type's contract**: what a contribution receives and how
  outputs are merged. Each hook type has a fixed skill portion in omc that loops
  over the contributions and merges them. Repos can't change that. Hooks are kept
  generic and lightweight: define a contribution in your repo and it just works.
  Anything needing more control is a lifecycle plugin.
- **Plugins call hooks; lifecycles never do.** Without contributions a plugin uses
  its default instructions; with contributions it relies on their output.
- **Names are lifecycle-namespaced:** `<lifecycle>:<hook>`, e.g.
  `design:explain-context`.
- **Discovery is by name** in three layers, merged in order omc → global → repo:
  - omc: shipped default contributions;
  - global: `hooks/<lifecycle>/<hook>/` in your omc repo;
  - repo: `repos/<key>/hooks/<lifecycle>/<hook>/`.

  Nothing is registered.
- **Turning off an inherited layer:** `hooks.omc.<lifecycle>:<hook>: false` and
  `hooks.global.<lifecycle>:<hook>: false`, in `repo.yaml` or the root
  `config.yaml`. (A colon with no following space is valid inside a YAML key.)
- Contribution forms (markdown, executable) and their failure rules are in
  [05-skill-rendering.md](05-skill-rendering.md).

### Hook types defined so far

| Hook | Called by | Contract |
|---|---|---|
| `design:explain-context` | `explain-seed`, and the per-section explain step of `design-hardening` | Context only: extra context-gathering and analysis instructions (where truth lives, conventions, what else to fetch). Successor of v1's `explain-context` |
| `design:hardening` | `design-hardening` | Read-only findings ([6.5](#6.5%20Read-only%20findings%20hooks)). Default contributions: `grug`, `multi-agent-hardening` |
| `design:plan-hardening` | `write-implementation-plan` | Read-only findings ([6.5](#6.5%20Read-only%20findings%20hooks)). Default contribution: one agent per plan task |

There is no brainstorm hook for now.

## 6.5 Read-only findings hooks

Used by `design:hardening` and `design:plan-hardening`.

- **Hooks never modify anything.** Each hook reads the document folder (and any
  shared context file, e.g. `design-explained.md`) and writes one findings file.
- **Python enforces it:** it hashes the document folder before the hooks run and
  checks it after **each** hook. Any change fails the whole skill, naming the
  hook. There are no per-hook copies.
- **Each hook works from the round's input,** not from another hook's output.
- **Findings format,** validated by Python after each hook; a missing or
  malformed file fails the skill, naming the hook and line; an empty result is a
  file containing `None.`:

  ```
  ### F<n>: <title>
  - Section: <heading>
  - Severity: Important | Minor
  - Problem: …
  - Recommendation: …
  - Needs decision: yes | no
  ```
- **The plugin merges and applies:** it collects every findings file, merges them,
  applies the recommended changes, and asks you only where it is unsure
  (conflicting recommendations, findings that need a decision, waivers).
- **Rounds:** after each round the plugin shows an overview of the outcome (each
  hook's result in one line, which sections changed and by how much, the changes
  that matter in plain language, what you decided) and asks whether to run another
  round, recommending yes when the design's structure changed and no when only
  wording or local fixes did. Only an explicit answer to that question counts.

## 6.6 The final artifact

- The final artifact is a **self-contained folder**: `<slug>/<slug>.md` plus any
  files it needs. Links are relative and point only inside the folder, and the
  whole folder is committed.
- **`omc internal check-artifact <folder>`** runs inside the copy step before
  anything is committed. It rejects any occurrence of `/tmp/`, `~/.omc2` (or its
  expanded path), absolute filesystem paths, `file://` URLs, and relative links
  that escape the folder or point to a missing file. `http(s)` URLs are allowed.
  On failure nothing is copied or committed, and each offending line is listed.
- **Python copies and commits** (for `design`, after `approve-design`):
  - `design_artifact_root: omc` → a guest commit in your omc repo through watch;
  - `design_artifact_root: repository` → a commit on the feature branch under
    `design_artifact_directory`.
