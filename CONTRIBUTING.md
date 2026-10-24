# Contributing a recipe

1. Fork this repository and add your recipe as `recipes/<your GitHub name>/<kind>/<name>/` (`kind` is `nixos` or
   `macos`; names use lowercase letters, digits and `-`).
2. Write `recipe.toml` and `default.nix` (below), test it in omaflake (below).
3. Run `python3 tools/catalog.py` and commit the updated `catalog.json` with your recipe.
4. Open a pull request – one recipe (or one recipe for both guest kinds) per pull request – and fill in the checklist.

The core team reviews every recipe against REVIEW.md: is it safe, does it work, does it add something the catalog
does not have yet. Changes to a merged recipe go the same way; only its author or the core team change it.

## `recipe.toml`

```toml
"$schema" = "https://omaflake.dev/schema/recipe/v1.json"   # the version of this format – required
systems = ["aarch64-linux"]      # what it can be built for – required (below)
author = "your-github-name"      # the folder's author – required
license = "MIT"                  # SPDX identifier, one of source.toml's licenses – required
description = "Rust development: rustup, rust-analyzer and neovim with the Rust LSP."   # English – required
description_de = "Rust-Entwicklung: rustup, rust-analyzer und neovim mit Rust-LSP."     # optional, any language code
tags = ["rust", "neovim"]        # from tags.toml (add new ones there) – required
homepage = "https://…"           # optional: where to read more or report problems
requires = ["omaflake/nixos/neovim-minimal"]   # optional: recipes of the same kind this one imports

# How a VM from it runs (defaults for new VMs; the user can change them)
cpus = 4
memory_gb = 8
disk_gb = 40
network = "shared"               # shared | isolated (NixOS only) | none
share = true                     # share a Mac folder: /mnt/share (NixOS), ~/Share (macOS)
ephemeral = false                # discard changes at power-off
display = "gpu"                  # none (headless) | window | gpu (window with 3D, NixOS)
audio = true                     # optional: audio, microphone, clipboard, camera (camera: NixOS)
lab = false                      # optional: true = development recipe, shown only in omaflake's developer mode
```

`systems` names the architectures the recipe is built and tested for, as Nix names them: `aarch64-linux` (NixOS on
a Mac with Apple silicon) and `x86_64-linux` for kind `nixos`, `aarch64-darwin` for kind `macos`. List only what you
have tested – omaflake shows a recipe only where it runs, and builds it only for a system it lists.

## `default.nix`

A NixOS module (kind `nixos`) or a nix-darwin module (kind `macos`). omaflake adds its guest modules around it – guest
hardware, the omaflake agent, the user, SSH keys, locale and keyboard – so a recipe only says what makes it different.
Its module arguments:

| Argument | |
|---|---|
| `pkgs`, `lib`, `config` | as usual; `pkgs` is omaflake's pinned nixpkgs (nixos-unstable) |
| `settings` | the user's values from omaflake: `user`, `fullName`, `email`, `timeZone`, `locale`, `keyboard`, `macUser` (macOS) |
| `nix-homebrew` | (macOS) the nix-homebrew flake, for recipes that want Homebrew |

NixOS recipes have home-manager: `home-manager.users.${settings.user} = { … };`. A NixOS recipe picks its editor
line with `omaflake.editor = "neovim";` (Neovim, preconfigured, with Zellij – the default) or `"emacs"` (Emacs,
preconfigured); the desktop, WezTerm and the terminal tools are the same in both. Name recipes after their line, e.g.
`neovim-research`, `emacs-research`. To build on another recipe, list it
in `requires` and import it relatively: `imports = [ ../neovim-minimal ];` (same author and kind) – omaflake keeps the
`<author>/<kind>/<name>` layout when it downloads recipes, so the path stays valid.

**Variants per architecture.** A file `<system>.nix` next to `default.nix` – e.g. `x86_64-linux.nix` – is added to
the recipe when it is built for that system (it must be one of `systems`). Put what differs there, such as a package
that exists for one architecture only; for a small difference `lib.mkIf pkgs.stdenv.hostPlatform.isx86_64 { … }` in
`default.nix` works as well. A variant belongs to its own recipe: a recipe that imports another (`requires`) gets that
one's `default.nix` only – import its variant yourself if you need it.

What a recipe must not do:

- bring its own flake, flake inputs or `flake.lock` – it uses omaflake's pinned inputs;
- fetch anything without a hash, or download and run code at run time (`curl … | sh`, unpinned installers);
- contain secrets, keys, personal data (names, e-mail addresses, host names, paths like `/Users/…`), telemetry or
  tracking;
- read anything from the Mac it is evaluated on (`builtins.getEnv`, absolute paths);
- switch off or change omaflake's guest agent or guest modules.

Files: at most 1 MiB each and 5 MiB per recipe, no symbolic links.

## Testing your recipe

Add your fork's checkout as a local source – in omaflake's Settings → Recipe Sources ("Folder …"), or
`omaf sources add <path to your checkout>` – and build the recipe from the Recipes tab or with
`omaf build <author>/<kind>/<name>`. A local folder is used as it is: change a file, build again. Put the folder first
in the list (`--first`, or the arrow in Settings) while it has a recipe of the same name as another source. Recipes
it `requires` from this repository are in your fork already.
