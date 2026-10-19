# CLAUDE.md – project rules for Claude Code

## Context

`omaflake/recipes`: the official catalog of omaflake recipes and the template for other recipe sources. omaflake
itself (app, CLI, guest modules, the recipes flake that builds images) lives in `omaflake/omaflake`, checked out next
to this one as `../omaflake`; its design for recipe sources is `../omaflake/docs/spec.md` §11.3.

## Working rules

- **Language:** everything in this repository is English. Talk to the maintainer in German.
- **Public from day one:** no personal data in tracked files (names, home paths, host names, keys).
- **The format is an interface.** `catalog.json` (schema 1), the folder layout `recipes/<author>/<kind>/<name>/` and
  the `recipe.toml` fields are what omaflake reads. Change them only together with omaflake, and raise `SCHEMA` in
  `tools/catalog.py` for changes an older omaflake would misread.
- **After every change:** `python3 tools/catalog.py` (or `nix run nixpkgs#python3 -- tools/catalog.py`) and commit
  `catalog.json` with the change; `--check` must pass.
- **Recipes:** omaflake's own recipes are under `recipes/omaflake/`. A change to them is tested by building an image
  in omaflake (CONTRIBUTING.md, "Testing your recipe").
- **Never delete (your own actions):** move files to `_to_delete/` (git-ignored) instead.
- **Verified before claimed:** mark what is not verified as `OPEN`.
