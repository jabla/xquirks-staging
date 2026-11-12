"""tools/check_content.py on synthetic content tags: what CI runs on the newest content-<n> tag."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from .conftest import content_json, quirk_text, tag_files, write_repo

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_content", ROOT / "tools/check_content.py")
check_content = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_content)


# The docstring lines every shipped quirk file has (content.GENERATED), which the synthetic files lack.
HEAD = b"\n\nGenerated from the Zigbee2MQTT definition of a test device.\nData: zigbee-herdsman-converters, MIT, Copyright (c) 2018 Koen Kanters.\nStatus: generated.\n"


def generated(body: bytes) -> bytes:
    """A synthetic quirk file with the docstring of a shipped one."""
    return body.replace(b"\n\nStatus: generated.\n", HEAD, 1)


def repo(folder: Path, edit=None) -> Path:
    """The synthetic repository with the docstrings of shipped files (edit: bytes -> bytes on each)."""
    write_repo(folder)
    for path in sorted((folder / "quirks").glob("*.py")):
        path.write_bytes((edit or (lambda body: body))(generated(path.read_bytes())))
    return folder


def tree_of(files: dict[str, bytes], tree: Path) -> Path:
    for path, data in files.items():
        (tree / path).parent.mkdir(parents=True, exist_ok=True)
        (tree / path).write_bytes(data)
    return tree


def tag_tree(tmp_path: Path, **replace: bytes) -> Path:
    """The tree of a content tag of the synthetic repository, some of its files replaced."""
    return tree_of(tag_files(repo(tmp_path / "repo")) | replace, tmp_path / "tag")


def test_a_tag_for_this_guard_reads_and_passes(tmp_path):
    assert check_content.problems(tag_tree(tmp_path), "content-7") == ([], "3 files read and guarded")
    assert check_content.main([str(tag_tree(tmp_path / "again")), "--tag", "content-7"]) == 0


def test_a_tag_for_another_guard_is_only_parsed(tmp_path, capsys):
    tree = tag_tree(tmp_path, **{"content.json": content_json("f" * 64), "quirks/z2m_acme_b.py": b"broken"})
    found, checked = check_content.problems(tree, "content-2")
    assert found == [] and checked.startswith("3 files listed; content for the guard ffffffffffff") and checked.endswith("files not checked")


@pytest.mark.parametrize(
    ("replace", "line"),
    [
        ({"manifest.json": b"{"}, "manifest.json: Expecting property name"),
        ({"hacs.json": b"[]"}, "hacs.json: "),
        ({"data/withdrawn.toml": b'[[withdrawn]]\nfile = "../x.py"\nrevision = "1a2b3c4d"\nreason = "x"\n'}, "data/withdrawn.toml: "),
        ({"quirks/z2m_acme_b.py": generated(quirk_text("acme_b", 2))}, "quirks/z2m_acme_b.py: not the sha256 its manifest entry states"),
        ({"quirks/z2m_acme_b.py": quirk_text("acme_b")}, "quirks/z2m_acme_b.py: not the sha256 its manifest entry states"),
    ],
)
def test_content_this_integration_cannot_read_is_refused(tmp_path, replace, line):
    found, _ = check_content.problems(tag_tree(tmp_path, **replace), "content-3")
    assert len(found) == 1 and found[0].startswith(line), found


def test_a_withdrawn_revision_and_guard_refusals_are_named(tmp_path, capsys):
    files = tag_files(repo(tmp_path / "repo"))
    manifest = json.loads(files["manifest.json"])
    revision = manifest["acme_b"]["revision"]
    withdrawn = f'[[withdrawn]]\nfile = "z2m_acme_b.py"\nrevision = "{revision}"\nreason = "Wrong values."\n'.encode()
    found, _ = check_content.problems(tag_tree(tmp_path, **{"data/withdrawn.toml": withdrawn}), "content-4")
    assert found == [f"quirks/z2m_acme_b.py: revision {revision} is withdrawn"]
    # Code the guard does not know, with the manifest entry's sha256 and revision matching; a file
    # without the docstring of a shipped one.
    def edit(body: bytes) -> bytes:
        return body.replace(b"# version 1\n", b"# version 1\nimport os\n") if b"acme_c" in body else body

    other = tag_files(repo(tmp_path / "other", edit))
    assert check_content.main([str(tree_of(other, tmp_path / "other-tag")), "--tag", "content-5"]) == 1
    out = capsys.readouterr().out
    assert out.startswith("content-5: quirks/z2m_acme_c.py: ") and out.count("\n") == 1
    plain = tag_files(write_repo(tmp_path / "plain"))
    assert check_content.problems(tree_of(plain, tmp_path / "plain-tag"), "content-5")[0] == [
        f"quirks/{name}: not a generated quirk file" for name in ("z2m_acme_b.py", "z2m_acme_c.py", "z2m_tuya_a.py")
    ]


def test_the_download_limit_and_the_stated_revision_count(tmp_path, monkeypatch):
    """Every file the integration fetches stays within its download limit, the manifest too; a file
    must have the revision its entry states."""
    const = check_content.integration()[2]
    tree = tag_tree(tmp_path)
    monkeypatch.setattr(const, "MAX_DOWNLOAD", (tree / "manifest.json").stat().st_size - 1)
    assert check_content.problems(tree, "content-8")[0] == [f"manifest.json: {(tree / 'manifest.json').stat().st_size} bytes, the integration reads at most {const.MAX_DOWNLOAD}"]
    # The manifest at the limit, hacs.json over it.
    limit = (tree / "manifest.json").stat().st_size
    monkeypatch.setattr(const, "MAX_DOWNLOAD", limit)
    (tree / "hacs.json").write_text((tree / "hacs.json").read_text() + " " * limit)
    assert check_content.problems(tree, "content-8")[0] == [f"hacs.json: {(tree / 'hacs.json').stat().st_size} bytes, the integration reads at most {limit}"]
    tree = tag_tree(tmp_path / "again")
    monkeypatch.undo()
    manifest = json.loads((tree / "manifest.json").read_text())
    manifest["acme_c"]["revision"] = "0" * 8
    (tree / "manifest.json").write_text(json.dumps(manifest))
    assert check_content.problems(tree, "content-8")[0] == [f"quirks/z2m_acme_c.py: revision {check_content.integration()[1].effective_revision((tree / 'quirks/z2m_acme_c.py').read_bytes())}, its manifest entry states 00000000"]


def test_a_missing_file_and_a_bad_tag_are_named(tmp_path):
    tree = tag_tree(tmp_path)
    (tree / "quirks/z2m_acme_c.py").unlink()
    assert check_content.problems(tree, "content-6")[0] == ["quirks/z2m_acme_c.py: no regular file"]
    assert check_content.problems(tree, "content-0")[0] == ["content-0: not content-<n>"]
