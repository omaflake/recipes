#!/usr/bin/env python3
"""Check every recipe in this repository and write catalog.json – the one file omaflake reads to browse it.

  python3 tools/catalog.py           # check, then write catalog.json
  python3 tools/catalog.py --check   # check, and fail if catalog.json is not up to date (CI)

Needs Python 3.11 or newer (tomllib) and nothing else, so forks and own catalogs can run it anywhere. Without a
recent Python: `nix run nixpkgs#python3 -- tools/catalog.py`. Errors fail the run; warnings are for the reviewers.
The output has no timestamps or commit hashes, so it only changes when a recipe changes.
"""

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "recipes"
CATALOG = ROOT / "catalog.json"
SCHEMA = 1

KINDS = ("nixos", "macos")
NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
TAG = re.compile(r"[a-z0-9][a-z0-9+.-]*")
REF = re.compile(r"([a-z0-9][a-z0-9-]*)/(nixos|macos)/([a-z0-9][a-z0-9-]*)")

# recipe.toml: what the catalog lists about a recipe; everything else is how a VM from it runs (its defaults)
META = {"author", "license", "description", "tags", "lab", "requires", "homepage"}
REQUIRED = ("author", "license", "description", "tags", "cpus", "memory_gb", "disk_gb", "network", "share",
            "ephemeral")
CHOICES = {"network": ("shared", "isolated", "none"), "display": ("none", "window", "gpu")}
BOOLS = ("share", "ephemeral", "lab", "audio", "microphone", "clipboard", "camera")
COUNTS = ("cpus", "memory_gb", "disk_gb")

MAX_FILE = 1024 * 1024           # per file
MAX_RECIPE = 5 * 1024 * 1024     # per recipe folder
# Files a recipe never contains: its own flake (a recipe is a module on omaflake's flake), keys, secrets
FORBIDDEN = re.compile(r"(^|/)(flake\.nix|flake\.lock|\.env|id_[a-z0-9]+|.*\.(pem|key|p12))$|(^|/)local/")
# Worth a reviewer's look, not an error
LINT = [
    (re.compile(r"builtins\.(fetchTarball|fetchGit|fetchurl)\b"), "builtins fetcher – pin it with a hash"),
    (re.compile(r"builtins\.getEnv\b"), "reads the environment of the Mac it is evaluated on"),
    (re.compile(r"(curl|wget)[^\n|]*\|\s*(ba|z)?sh\b"), "downloads and runs a script"),
    (re.compile(r"omaflake-agent|clipboard-agent|camera-agent"), "touches omaflake's guest agents"),
    (re.compile(r"allowUnfree|allowInsecure"), "allows unfree or insecure packages"),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_toml(path: Path, errors: list[str]) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        errors.append(f"{path.relative_to(ROOT)}: {e}")
        return {}


def check_recipe(folder: Path, data: dict, tags: set[str], licenses: list[str], errors: list[str],
                 warnings: list[str]) -> None:
    where = folder.relative_to(ROOT)
    author, kind, name = folder.relative_to(RECIPES).parts
    if not NAME.fullmatch(author) or not NAME.fullmatch(name):
        errors.append(f"{where}: author and name use lowercase letters, digits and -")
    if kind not in KINDS:
        errors.append(f"{where}: the kind folder is nixos or macos, not {kind}")
    if data.get("author") != author:
        errors.append(f"{where}: author = \"{data.get('author')}\" in recipe.toml, but the folder says {author}")
    for key in REQUIRED:
        if key not in data:
            errors.append(f"{where}: recipe.toml needs {key}")
    for key, choices in CHOICES.items():
        if key in data and data[key] not in choices:
            errors.append(f"{where}: {key} is one of {', '.join(choices)}")
    if kind == "macos" and data.get("network") == "isolated":
        errors.append(f"{where}: network = \"isolated\" exists for NixOS only")
    for key in BOOLS:
        if key in data and not isinstance(data[key], bool):
            errors.append(f"{where}: {key} is true or false")
    for key in COUNTS:
        if key in data and (not isinstance(data[key], int) or isinstance(data[key], bool) or data[key] < 1):
            errors.append(f"{where}: {key} is a whole number of at least 1")
    if not isinstance(data.get("description", ""), str) or not data.get("description", "x").strip():
        errors.append(f"{where}: description is a sentence in English")
    if licenses and data.get("license") not in licenses:
        errors.append(f"{where}: license \"{data.get('license')}\" is not one of source.toml's licenses")
    recipe_tags = data.get("tags", [])
    if not isinstance(recipe_tags, list) or not recipe_tags:
        errors.append(f"{where}: tags is a list of at least one word")
        recipe_tags = []
    for tag in recipe_tags:
        if not isinstance(tag, str) or not TAG.fullmatch(tag):
            errors.append(f"{where}: tag {tag!r} – lowercase letters, digits and -")
        elif tag not in tags:
            errors.append(f"{where}: tag \"{tag}\" is not in tags.toml – add it there in the same pull request")
    for ref in data.get("requires", []):
        m = REF.fullmatch(ref) if isinstance(ref, str) else None
        if not m:
            errors.append(f"{where}: requires {ref!r} – write <author>/<kind>/<name>")
        elif m.group(2) != kind:
            errors.append(f"{where}: requires {ref} – a recipe can only build on one of its own kind")
        elif not (RECIPES / ref / "recipe.toml").is_file():
            errors.append(f"{where}: requires {ref}, which is not in this repository")
    if not (folder / "default.nix").is_file():
        errors.append(f"{where}: default.nix is missing")


def recipe_files(folder: Path, errors: list[str], warnings: list[str]) -> list[dict]:
    where = folder.relative_to(ROOT)
    files, total = [], 0
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder).as_posix()
        if path.is_symlink():
            errors.append(f"{where}/{rel}: no symbolic links")
            continue
        if path.is_dir() or path.name == ".DS_Store":
            continue
        if FORBIDDEN.search(rel):
            errors.append(f"{where}/{rel}: does not belong in a recipe (own flake, keys, secrets, local/)")
        data = path.read_bytes()
        total += len(data)
        if len(data) > MAX_FILE:
            errors.append(f"{where}/{rel}: {len(data)} bytes – at most {MAX_FILE} per file")
        if path.suffix in (".nix", ".sh", ".py", ".lua", ".toml", ".json"):
            text = data.decode("utf-8", errors="replace")
            for pattern, why in LINT:
                for m in pattern.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1
                    warnings.append(f"{where}/{rel}:{line}: {why}")
        files.append({"path": rel, "size": len(data), "sha256": sha256(data)})
    if total > MAX_RECIPE:
        errors.append(f"{where}: {total} bytes in all – at most {MAX_RECIPE} per recipe")
    return files


def build() -> tuple[dict, list[str], list[str]]:
    errors, warnings = [], []
    source = load_toml(ROOT / "source.toml", errors)
    for key in ("name", "description"):
        if not source.get(key):
            errors.append(f"source.toml needs {key}")
    tags = set(load_toml(ROOT / "tags.toml", errors).get("tags", {}).keys())
    licenses = source.get("licenses", [])

    recipes = []
    for toml in sorted(RECIPES.rglob("recipe.toml")):
        folder = toml.parent
        if len(folder.relative_to(RECIPES).parts) != 3:
            errors.append(f"{toml.relative_to(ROOT)}: recipes live in recipes/<author>/<kind>/<name>/")
            continue
        data = load_toml(toml, errors)
        check_recipe(folder, data, tags, licenses, errors, warnings)
        files = recipe_files(folder, errors, warnings)
        author, kind, name = folder.relative_to(RECIPES).parts
        descriptions = {k.removeprefix("description_"): v for k, v in data.items() if k.startswith("description_")}
        recipes.append({
            "id": f"{author}.{kind}.{name}",
            "author": author,
            "kind": kind,
            "name": name,
            "path": folder.relative_to(ROOT).as_posix(),
            "description": data.get("description", ""),
            "descriptions": descriptions,
            "tags": data.get("tags", []),
            "license": data.get("license", ""),
            "lab": data.get("lab", False),
            "requires": data.get("requires", []),
            "homepage": data.get("homepage", ""),
            "defaults": {k: v for k, v in data.items() if k not in META and not k.startswith("description_")},
            # Changes whenever any file of the recipe changes: how omaflake sees that an installed recipe has an update
            "version": sha256("".join(f"{f['path']}\0{f['sha256']}\n" for f in files).encode()),
            "files": files,
        })
    catalog = {
        "schema": SCHEMA,
        "source": {k: source.get(k, "") for k in ("name", "description", "homepage")},
        "recipes": recipes,
    }
    return catalog, errors, warnings


def main() -> int:
    check = "--check" in sys.argv[1:]
    catalog, errors, warnings = build()
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    if errors:
        return 1
    text = json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"
    if check:
        if not CATALOG.is_file() or CATALOG.read_text(encoding="utf-8") != text:
            print("error: catalog.json is not up to date – run python3 tools/catalog.py and commit it")
            return 1
        print(f"ok: {len(catalog['recipes'])} recipes, catalog.json up to date")
    else:
        CATALOG.write_text(text, encoding="utf-8")
        print(f"ok: {len(catalog['recipes'])} recipes written to catalog.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
