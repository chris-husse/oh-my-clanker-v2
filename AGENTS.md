# oh-my-clanker v2

- v2 is the source of `omc/`. `just install <project>` copies v2's committed `omc/` into a project (or updates it
  there by a three-way merge from the commit in its `omc/VERSION`), then starts `claude /oh-my-clanker` in it.
- Anything under `omc/` is what projects receive on update.
- Everything else in v2 (`install/`, the root `justfile`, `docs/`, this file) is never copied.
- v2 runs its own pipeline (`just design`, `just omc`): it is installed into itself (`just install . --no-launch`;
  its `.claude/skills` link the working tree's `omc/` skills, `omc/VERSION` is git-ignored). Its gate commands live
  in `omc/bin/`, which install never ships.
