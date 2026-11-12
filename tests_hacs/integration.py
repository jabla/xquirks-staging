"""The integration under test, found by its folder: the domain is written nowhere in tests_hacs/."""

from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
(FOLDER,) = [path.parent for path in (ROOT / "custom_components").glob("*/manifest.json")]
PACKAGE = f"custom_components.{FOLDER.name}"

const = importlib.import_module(f"{PACKAGE}.const")
content = importlib.import_module(f"{PACKAGE}.content")
diagnostics = importlib.import_module(f"{PACKAGE}.diagnostics")
files = importlib.import_module(f"{PACKAGE}.files")
guard = importlib.import_module(f"{PACKAGE}.guard")
manager = importlib.import_module(f"{PACKAGE}.manager")
matching = importlib.import_module(f"{PACKAGE}.matching")
pictures = importlib.import_module(f"{PACKAGE}.pictures")
plan = importlib.import_module(f"{PACKAGE}.plan")
text = importlib.import_module(f"{PACKAGE}.text")
DOMAIN = const.DOMAIN

