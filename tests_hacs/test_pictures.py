"""Device pictures in the notices: fetched once, scaled down, served from disk only."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from PIL import Image

from .conftest import MANIFEST, NO_QUIRK, REPOS, Repo, Zha, apply_list, issue_of, published, quirk_revision, quirk_text, setup_entry, start_fix, write_repo
from .integration import DOMAIN, content, pictures

IEEE_A = "00:11:22:33:44:55:66:01"
IEEE_B = "00:11:22:33:44:55:66:02"
BIG = pictures.PICTURE_URL.format(name="A.png")


def thumb(hass: HomeAssistant, picture: bytes) -> str:
    """The path of the thumbnail of a picture, with the token of this run."""
    return pictures.VIEW_URL.format(token=hass.data[pictures.DATA_PICTURES].token, name=pictures.THUMBNAIL.format(pin=hashlib.sha256(picture).hexdigest()))


def stored(hass: HomeAssistant, picture: bytes) -> Path:
    """Where the thumbnail of a picture is kept: under its pin."""
    return Path(hass.config.path(*pictures.FOLDER, pictures.THUMBNAIL.format(pin=hashlib.sha256(picture).hexdigest())))


def png(width: int, height: int) -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", (width, height), (200, 30, 30, 255)).save(out, "PNG")
    return out.getvalue()


def with_pictures(repo_dir: Path, picture: bytes | None = b"") -> Path:
    """The test bundle whose manifest names a picture for each device, pinned to these bytes (None:
    no pin), as content tags hold it."""
    pin = hashlib.sha256(picture).hexdigest() if picture is not None else None
    manifest = {slug: {**entry, "picture": f"{entry['model']}.png", "picture_sha256": pin} for slug, entry in MANIFEST.items()}
    return write_repo(repo_dir, manifest)


def picture_requests(aioclient_mock) -> int:
    return sum(1 for _method, url, _data, _headers in aioclient_mock.mock_calls if str(url).startswith("https://www.zigbee2mqtt.io/"))


def users_copy(quirks_dir: Path) -> None:
    """A file of the user's own under the name of the quirk for device A: the users_file notice names that device."""
    (quirks_dir / "z2m_tuya_a.py").write_text("# my own copy\n")


def withdraw_tuya_a(repo_dir: Path) -> None:
    """The working tree withdraws revision 1 of z2m_tuya_a.py."""
    (repo_dir / "data").mkdir(exist_ok=True)
    (repo_dir / "data" / "withdrawn.toml").write_text(f'[[withdrawn]]\nfile = "z2m_tuya_a.py"\nrevision = "{quirk_revision("tuya_a")}"\nreason = "Drives the valve fully open."\n')


def picture_of(hass: HomeAssistant, kind: str = "users_file") -> str:
    """The picture paragraph of the notice of this kind (notices are no dialogs: it is a placeholder of the issue)."""
    return issue_of(hass, kind).translation_placeholders["picture"]


async def test_a_notice_shows_the_thumbnail_linked_to_the_full_picture(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    picture = png(512, 300)
    aioclient_mock.get(BIG, content=picture)
    users_copy(quirks_dir)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, with_pictures(repo_dir, picture))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert picture_of(hass) == f"[![]({thumb(hass, picture)})]({BIG})\n\n"
    with Image.open(stored(hass, picture)) as image:
        assert image.size == (128, 75)
    assert picture_requests(aioclient_mock) == 1

    # Fetched once: later refreshes and new devices of the same model use the file on disk.
    zha.add_device(IEEE_B, "_TZE200_aaaa", "TS0601")
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert picture_requests(aioclient_mock) == 1


async def test_a_picture_pinned_anew_is_fetched_again(hass: HomeAssistant, zha: Zha, repo: Repo, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    old, new = png(512, 300), png(300, 512)
    aioclient_mock.get(BIG, content=old)
    users_copy(quirks_dir)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, with_pictures(repo_dir, old))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert picture_requests(aioclient_mock) == 1

    # zigbee2mqtt.io replaced the picture, the weekly sync pinned the new one.
    aioclient_mock.clear_requests()
    repo.register()
    aioclient_mock.get(BIG, content=new)
    with_pictures(repo_dir, new)
    repo.publish()
    await entry.runtime_data.async_check()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert picture_requests(aioclient_mock) == 1
    assert picture_of(hass) == f"[![]({thumb(hass, new)})]({BIG})\n\n"
    with Image.open(stored(hass, new)) as image:
        assert image.size == (75, 128)


async def test_no_picture_no_image(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    aioclient_mock.get(BIG, status=404)
    users_copy(quirks_dir)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, with_pictures(repo_dir))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert picture_of(hass) == ""
    assert not stored(hass, b"").exists()
    # A failed picture is not asked for again on every refresh.
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert picture_requests(aioclient_mock) == 1
    assert (await entry.runtime_data.async_diagnostics())["content"]["pictures"] == {"on_disk": 0, "failed": ["A.png"]}


async def test_something_that_is_no_picture_is_not_kept(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    aioclient_mock.get(BIG, text="<html>not found</html>")
    users_copy(quirks_dir)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    await setup_entry(hass, with_pictures(repo_dir, b"<html>not found</html>"))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert picture_of(hass) == ""
    assert not stored(hass, b"<html>not found</html>").exists()


async def test_view_serves_thumbnails_on_disk_only(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock, hass_client_no_auth):
    folder = Path(hass.config.path(*pictures.FOLDER))
    folder.mkdir(parents=True)
    stored(hass, b"B-1").write_bytes(png(128, 128))
    # A thumbnail kept under its picture's name (before thumbnails were kept under their pin).
    (folder / "B-1.png").write_bytes(png(128, 128))
    (folder / "notes.txt").write_text("not a picture")
    await setup_entry(hass, repo_dir)
    client = await hass_client_no_auth()

    response = await client.get(thumb(hass, b"B-1"))
    assert response.status == 200
    assert response.headers["Cache-Control"] == "public, max-age=86400"
    assert await response.read() == stored(hass, b"B-1").read_bytes()

    view = pictures.VIEW_URL.format(token=hass.data[pictures.DATA_PICTURES].token, name="{}")
    for path in (thumb(hass, b"C-1"), *(view.format(name) for name in ("B-1.png", "notes.txt", "..%2F..%2Fsecrets.yaml", "%2E%2E.png", ".hidden.png"))):
        response = await client.get(path)
        # Home Assistant's own filters answer some of these with 400 before the view sees them.
        assert response.status in (400, 404), path
    # A request for a picture that is not on disk never makes Home Assistant fetch it.
    assert picture_requests(aioclient_mock) == 0


def test_names_outside_the_manifest_shape_are_never_fetched(hass: HomeAssistant):
    store = pictures.Pictures(hass)
    pin = "a" * 64
    names = ["A.png", "../x.png", "a/b.png", ".x.png", "x.svg", None, "A.png"]
    assert store.missing((name, pin) for name in names) == [("A.png", pin)]
    # Only pinned pictures, with a pin in the manifest's shape.
    assert store.missing([("A.png", None), ("A.png", "A" * 64), ("A.png", "a" * 63)]) == []
    store.cached.add(pin)
    assert store.missing([("A.png", pin)]) == []
    # A picture pinned anew is missing again: its thumbnail is another file.
    assert store.missing([("A.png", "b" * 64)]) == [("A.png", "b" * 64)]
    assert store.markdown("ES1ZZ(TY).png", "c" * 64) == ""
    store.cached.add("c" * 64)
    # Parentheses would end the markdown link: they are encoded.
    assert store.markdown("ES1ZZ(TY).png", "c" * 64) == f"[![](/api/xquirks/picture/{store.token}/{'c' * 64}.png)](https://www.zigbee2mqtt.io/images/devices/ES1ZZ%28TY%29.png)\n\n"
    assert store.markdown("ES1ZZ(TY).png", None) == store.markdown(None, "c" * 64) == ""
    # Entries may share a pin: its thumbnail on disk never links a name outside the manifest's shape.
    for name in ("../x.png", "a/b.png", "x/../y.png", ".x.png", "x.svg"):
        assert store.markdown(name, "c" * 64) == "", name


async def test_the_view_is_registered_once_per_run(hass: HomeAssistant, zha: Zha, repo_dir: Path):
    entry = await setup_entry(hass, repo_dir)
    first = entry.runtime_data.pictures
    with published(repo_dir):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.config_entries.async_get_entry(entry.entry_id).runtime_data.pictures is first
    assert DOMAIN in hass.config.components


NOTICES = ["blocked", "users_file", "changed", "withdrawn_copy", "withdrawn_installed", "not_applied"]


@pytest.mark.parametrize("kind", NOTICES)
async def test_each_notice_about_a_device_gets_its_picture_once_it_is_fetched(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock, kind: str):
    picture = png(256, 256)
    aioclient_mock.get(BIG, content=picture)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601", "Radar")
    with_pictures(repo_dir, picture)
    if kind == "blocked":
        (quirks_dir / "my_tuya_radar.py").write_text("# the user's own quirk for _TZE200_aaaa / TS0601\n")
        zha.apply_quirks({IEEE_A: "my_tuya_radar:(_TZE200_aaaa / TS0601)"})
    elif kind == "users_file":
        users_copy(quirks_dir)
    elif kind == "withdrawn_copy":
        # An exact copy of the offered file put there by hand, at a revision withdrawn since.
        (quirks_dir / "z2m_tuya_a.py").write_bytes(quirk_text("tuya_a"))
        withdraw_tuya_a(repo_dir)
    entry = await setup_entry(hass, repo_dir)
    if kind in ("changed", "withdrawn_installed", "not_applied"):
        # The list installs the file without a picture; the notice comes once ZHA loaded it.
        await apply_list(hass)
        zha.reload({IEEE_A: NO_QUIRK if kind == "not_applied" else "z2m_tuya_a:TuyaA"})
        if kind == "changed":
            (quirks_dir / "z2m_tuya_a.py").write_text("# tuned by the user\n")
        if kind == "withdrawn_installed":
            withdraw_tuya_a(repo_dir)
            REPOS[repo_dir].publish()
            await entry.runtime_data.async_check()
        else:
            await entry.runtime_data.async_refresh()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert picture_of(hass, kind) == f"[![]({thumb(hass, picture)})]({BIG})\n\n"
    assert picture_requests(aioclient_mock) == 1


async def test_the_change_list_shows_no_picture(hass: HomeAssistant, zha: Zha, repo_dir: Path, aioclient_mock):
    """The list names its files and devices in words: no picture is fetched for it."""
    aioclient_mock.get(BIG, content=png(512, 300))
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    await setup_entry(hass, with_pictures(repo_dir, png(512, 300)))
    await hass.async_block_till_done(wait_background_tasks=True)
    flow = await start_fix(hass, issue_of(hass, "changes"))
    assert "picture" not in flow["description_placeholders"] and "![" not in flow["description_placeholders"]["changes"]
    assert picture_requests(aioclient_mock) == 0


def png_header(width: int, height: int) -> bytes:
    """A valid PNG of that size whose pixel data compresses to almost nothing."""
    import struct
    import zlib

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    rows = zlib.compress(b"\0" * (1 + width) * height, 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)) + chunk(b"IDAT", rows) + chunk(b"IEND", b"")


@pytest.mark.parametrize("fmt", ["BMP", "GIF", "TIFF", "WEBP", "JPEG", "ICO"])
def test_only_pngs_are_decoded(fmt: str):
    out = io.BytesIO()
    Image.new("RGB", (64, 64), (1, 2, 3)).save(out, fmt)
    with pytest.raises(ValueError, match="not a usable picture"):
        pictures.scale(out.getvalue())


def test_a_large_picture_is_refused_before_it_is_decoded():
    data = png_header(pictures.MAX_SIDE + 1, 1)
    with patch("PIL.PngImagePlugin.PngImageFile.load", side_effect=AssertionError("decoded")), pytest.raises(ValueError, match="pixels"):
        pictures.scale(data)
    assert pictures.scale(png_header(pictures.MAX_SIDE, 2)).startswith(b"\x89PNG")


async def test_a_redirect_is_not_followed():
    class Response:
        status, headers = 301, {"Location": "https://elsewhere.example/A.png"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    class Session:
        def get(self, url, **kwargs):
            self.kwargs = kwargs
            return Response()

    session = Session()
    with pytest.raises(ValueError, match="HTTP 301"):
        await pictures._download(session, BIG)
    assert session.kwargs["allow_redirects"] is False


async def test_the_view_needs_the_token_of_this_run(hass: HomeAssistant, zha: Zha, repo_dir: Path, hass_client_no_auth):
    stored(hass, b"B-1").parent.mkdir(parents=True)
    stored(hass, b"B-1").write_bytes(png(128, 128))
    await setup_entry(hass, repo_dir)
    client = await hass_client_no_auth()
    token = hass.data[pictures.DATA_PICTURES].token
    assert len(token) == 32
    assert (await client.get(thumb(hass, b"B-1"))).status == 200
    # Without the token nobody learns which device pictures are there.
    name = stored(hass, b"B-1").name
    for path in (f"/api/xquirks/picture/{name}", f"/api/xquirks/picture/{'0' * 32}/{name}", f"/api/xquirks/picture/{token[:-1]}ä/{name}"):
        assert (await client.get(path)).status in (400, 404), path


async def test_a_picture_that_does_not_match_its_pin_is_not_decoded(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    aioclient_mock.get(BIG, content=png(512, 300))
    users_copy(quirks_dir)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    with patch.object(pictures, "scale", side_effect=AssertionError("decoded")):
        entry = await setup_entry(hass, with_pictures(repo_dir, png(300, 512)))
        await hass.async_block_till_done(wait_background_tasks=True)

    assert picture_of(hass) == ""
    assert picture_requests(aioclient_mock) == 1
    assert (await entry.runtime_data.async_diagnostics())["content"]["pictures"] == {"on_disk": 0, "failed": ["A.png"]}


async def test_an_unpinned_picture_is_never_fetched(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path, aioclient_mock):
    aioclient_mock.get(BIG, content=png(512, 300))
    users_copy(quirks_dir)
    zha.add_device(IEEE_A, "_TZE200_aaaa", "TS0601")
    await setup_entry(hass, with_pictures(repo_dir, None))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert picture_of(hass) == ""
    assert picture_requests(aioclient_mock) == 0


@pytest.mark.parametrize("pin", ["A" * 64, "a" * 63, 7, ["a" * 64]])
def test_a_malformed_pin_makes_the_manifest_entry_bad(pin):
    entry = {**next(iter(MANIFEST.values())), "picture": "A.png", "picture_sha256": pin}
    with pytest.raises(content.BadContent, match="picture_sha256"):
        content.check_entry("a", entry)
    content.check_entry("a", {**entry, "picture_sha256": "a" * 64})
    content.check_entry("a", {**entry, "picture_sha256": None})
