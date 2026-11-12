"""The repository's own files: the brand images Home Assistant serves, the workflows."""

from __future__ import annotations

import re
import struct
from pathlib import Path

from .integration import FOLDER

ROOT = Path(__file__).resolve().parents[1]


def test_brand_images_have_home_assistant_sizes():
    """Home Assistant serves custom_components/<domain>/brand/ itself: square PNGs of 256 and 512 px
    with transparency (tools/render_brand.py renders them from brand/icon.svg)."""
    folder = FOLDER / "brand"
    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        head = (folder / name).read_bytes()[:26]
        assert head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", name
        width, height, _, color_type = struct.unpack(">IIBB", head[16:26])
        assert (width, height, color_type) == (size, size, 6), name  # 6: RGBA


def test_checkouts_leave_no_token_on_disk():
    """Every actions/checkout sets persist-credentials: false: the steps after it run code from pip
    and from the pull request, which could read a token in .git/config."""
    checkouts, missing = 0, []
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        text = path.read_text()
        # the step: its first line and the lines indented deeper than its dash
        for step in re.finditer(r"^( +)- uses: actions/checkout@.*\n((?:\1  .*\n)*)", text, re.M):
            checkouts += 1
            if not re.search(r"^ +persist-credentials: false$", step[2], re.M):
                missing.append(f"{path.name}:{text.count(chr(10), 0, step.start()) + 1}")
    assert checkouts and missing == []


def test_no_workflow_pipes_into_grep_q():
    """grep -q stops reading at its first match: the command writing into the pipe then dies of
    SIGPIPE, which pipefail (the default shell of a run step) makes the result of the pipeline."""
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        assert not re.search(r"\|\s*grep\s+-\w*q", path.read_text()), path.name
