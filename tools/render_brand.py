"""Render brand/icon.svg into the integration's brand images (Home Assistant 2026.3+ serves
custom_components/<domain>/brand/ itself): icon.png 256 px and icon@2x.png 512 px, transparent.

    python tools/render_brand.py

Needs rsvg-convert; optipng shrinks the files when it is installed. Run it after changing brand/.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SIZES = {"icon.png": 256, "icon@2x.png": 512}


def main() -> None:
    target = next((ROOT / "custom_components").glob("*/manifest.json")).parent / "brand"
    target.mkdir(exist_ok=True)
    for name, size in SIZES.items():
        out = target / name
        subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", str(out), str(ROOT / "brand/icon.svg")], check=True)
        if shutil.which("optipng"):
            subprocess.run(["optipng", "-quiet", "-o7", "-i1", "-strip", "all", str(out)], check=True)
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
