"""A content state through this integration: what a content-<n> tag holds reads as at the user's end.

Usage:
    python3 tools/check_content.py DIR [--tag content-<n>]

DIR holds the tree of a content tag (`git archive content-<n> | tar -x -C DIR`). The integration's own
parsers read manifest.json, hacs.json, content.json and data/withdrawn.toml. When content.json names
the guard of this integration, every file the manifest names also fits the download limit, has the
sha256 and the revision its entry states, is no withdrawn revision and passes the guard. Content for
another guard is only parsed: a release takes only content built for its own guard. One line per
problem, exit 1. The standard library only: the integration's modules load without Home Assistant.
"""

from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import re
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
# The integration: the one folder under custom_components/ with a manifest.json.
(FOLDER,) = [path.parent for path in sorted((ROOT / "custom_components").glob("*/manifest.json"))]
TAG = re.compile(r"content-([1-9][0-9]*)")
# The modules without the package __init__, which imports Home Assistant: a stand-in package whose
# path is the integration's folder, so their relative imports resolve.
PACKAGE = "_xquirks_check_content"


def integration(folder: pathlib.Path = FOLDER) -> tuple[types.ModuleType, types.ModuleType, types.ModuleType]:
    if PACKAGE not in sys.modules:
        package = types.ModuleType(PACKAGE)
        package.__path__ = [str(folder)]
        sys.modules[PACKAGE] = package
    return tuple(importlib.import_module(f"{PACKAGE}.{name}") for name in ("guard", "content", "const"))


def problems(tree: pathlib.Path, tag: str = "content-1") -> tuple[list[str], str]:
    """The problems of the content in tree, and what was checked."""
    match = TAG.fullmatch(tag)
    if match is None:
        return [f"{tag}: not content-<n>"], ""
    guard, content, const = integration()

    def read(path: str, parse):
        """A metadata file as the integration fetches it: at most the download limit, then parsed."""
        try:
            data = (tree / path).read_bytes()
        except OSError as error:
            raise ValueError(f"{path}: {error}") from error
        if len(data) > const.MAX_DOWNLOAD:
            raise ValueError(f"{path}: {len(data)} bytes, the integration reads at most {const.MAX_DOWNLOAD}")
        try:
            return parse(data.decode())
        except (ValueError, AttributeError, TypeError, RecursionError) as error:
            raise ValueError(f"{path}: {error}") from error

    try:
        manifest = read("manifest.json", json.loads)
        withdrawn = read("data/withdrawn.toml", content.parse_withdrawn)
        homeassistant = read("hacs.json", content.parse_homeassistant)
        named = read("content.json", content.parse_guard)
        content.from_manifest(manifest, tag=tag, content=int(match[1]), homeassistant=homeassistant, withdrawn=withdrawn)
        shipped = content.shipped_entries(manifest)
    except ValueError as error:
        return [str(error)], ""
    shipped_guard = guard.Guard.load(FOLDER)
    if named != shipped_guard.id:
        return [], f"{len(shipped)} files listed; content for the guard {str(named)[:12]}, this integration ships {shipped_guard.id[:12]}: files not checked"
    found = []
    for path, entry in sorted((str(path), entry) for path, entry in shipped.values()):
        file = tree / path
        if file.is_symlink() or not file.is_file():
            found.append(f"{path}: no regular file")
            continue
        body = file.read_bytes()
        revision = content.effective_revision(body)
        if len(body) > const.MAX_DOWNLOAD:
            found.append(f"{path}: {len(body)} bytes, the integration reads at most {const.MAX_DOWNLOAD}")
        elif content.sha256(body) != entry["sha256"]:
            found.append(f"{path}: not the sha256 its manifest entry states")
        elif not content.generated(body):
            found.append(f"{path}: not a generated quirk file")
        elif revision != entry["revision"]:
            found.append(f"{path}: revision {revision}, its manifest entry states {entry['revision']}")
        elif (path.rpartition("/")[2], revision) in withdrawn:
            found.append(f"{path}: revision {revision} is withdrawn")
        elif refused := shipped_guard.problems(body, guard.Targets.of(entry)):
            found.append(f"{path}: {refused[0]}")
    return found, f"{len(shipped)} files read and guarded"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a content state with this integration's parsers and guard.")
    parser.add_argument("tree", type=pathlib.Path, help="the tree of a content-<n> tag")
    parser.add_argument("--tag", default="content-1", help="the tag it comes from (default content-1)")
    args = parser.parse_args(argv)
    found, checked = problems(args.tree, args.tag)
    for line in found:
        print(f"{args.tag}: {line}")
    if found:
        return 1
    print(f"{args.tag}: {checked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
