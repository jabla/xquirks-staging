"""Build the HACS release zip of the Home Assistant integration.

Usage:
    python tools/build_integration.py --version 1.2.0 --zip dist

The zip holds the integration folder's content at its root (as HACS expects for zip_release),
the version stamped into its manifest.json. It holds no quirk files: the integration loads their
list from the newest content-<n> tag of the repository and downloads a file when it would offer
it. It holds the guard (guard.py, fixed_code.json) every file must pass. The zip's name comes
from hacs.json ("filename"). The source tree is not changed.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def integration_folder(root: pathlib.Path = ROOT) -> pathlib.Path:
    folders = [p.parent for p in sorted((root / "custom_components").glob("*/manifest.json"))]
    if len(folders) != 1:
        sys.exit(f"expected one integration in custom_components/, found {len(folders)}")
    return folders[0]


# Home Assistant refuses to load a custom integration whose version AwesomeVersion rejects.
VERSION = re.compile(r"\d+\.\d+\.\d+")


def write_zip(folder: pathlib.Path, out: pathlib.Path, version: str | None, root: pathlib.Path = ROOT) -> pathlib.Path:
    if version is not None and not VERSION.fullmatch(version):
        sys.exit(f"release version {version!r} is not X.Y.Z (tag vX.Y.Z)")
    name = json.loads((root / "hacs.json").read_text())["filename"]
    with tempfile.TemporaryDirectory() as tmp:
        stage = pathlib.Path(tmp) / folder.name
        shutil.copytree(folder, stage, ignore=shutil.ignore_patterns("__pycache__"))
        if version:
            manifest = json.loads((stage / "manifest.json").read_text())
            manifest["version"] = version
            (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        out.mkdir(parents=True, exist_ok=True)
        path = out / name
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(stage.rglob("*")):
                if file.is_file():
                    archive.write(file, file.relative_to(stage).as_posix())
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=pathlib.Path, metavar="DIR", required=True, help="write the HACS release zip into DIR")
    parser.add_argument("--version", help="version to stamp into the zip's manifest.json (the release tag)")
    args = parser.parse_args()
    print(f"wrote {write_zip(integration_folder(), args.zip, args.version)}")


if __name__ == "__main__":
    main()
