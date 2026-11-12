"""Device pictures for the notices: the zigbee2mqtt.io picture of a device, scaled down to a
thumbnail that links to the full picture.

Repair texts hold markdown only, and Home Assistant drops every attribute of an image but its
source: the picture itself has to be small. The thumbnails are fetched once per pinned picture for
the devices the notices name, kept in .storage/xquirks_pictures/ under the pin (a picture pinned
anew is fetched again) and served by Home Assistant without a login (an image in a dialog cannot
send one). The path holds a random token of this run instead, so nobody who has not seen the
notices can ask which device pictures are there. The view serves only thumbnails already on disk,
so a request to it never makes Home Assistant fetch anything.

Only pictures pinned in the manifest are fetched (picture_sha256), only
from the picture host itself (no redirects), and only bytes that match the pin reach the decoder:
a picture that changed on the host after it was pinned is not shown. Only PNG is decoded, only up
to MAX_SIDE pixels per side (checked before the decoding).
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import secrets
import tempfile
import time
from collections.abc import Iterable
from urllib.parse import quote

import aiohttp
from aiohttp import web
from PIL import Image, UnidentifiedImageError

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.hass_dict import HassKey

from .const import FETCH_TIMEOUT, MAX_DOWNLOAD

_LOGGER = logging.getLogger(__name__)

PICTURE_URL = "https://www.zigbee2mqtt.io/images/devices/{name}"
VIEW_URL = "/api/xquirks/picture/{token}/{name}"
# The names the manifest uses (the z2m model, '/', ':', "'" and ' ' as '-').
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._()+-]*\.png")
FOLDER = (".storage", "xquirks_pictures")
SHA256 = re.compile(r"[0-9a-f]{64}")
# A thumbnail's file name: the pin of its picture, so a picture pinned anew is another file.
THUMBNAIL = "{pin}.png"
THUMBNAIL_NAME = re.compile(r"([0-9a-f]{64})\.png")
SIZE = 128
# Zigbee2MQTT's pictures are a few hundred pixels per side. A larger one is refused before it is
# decoded: a small compressed file can stand for a huge image.
MAX_SIDE = 2048
# A picture that could not be fetched is tried again after this many seconds.
RETRY_AFTER = 24 * 3600


def scale(content: bytes) -> bytes:
    """The picture as a PNG thumbnail; ValueError when it is no PNG or too large (blocking: run in the executor)."""
    try:
        # Opening reads the header only; thumbnail() decodes.
        with Image.open(io.BytesIO(content), formats=["PNG"]) as image:
            if max(image.size) > MAX_SIDE:
                raise ValueError(f"{image.size[0]} x {image.size[1]} pixels, more than {MAX_SIDE} per side")
            image.thumbnail((SIZE, SIZE))
            out = io.BytesIO()
            image.save(out, "PNG", optimize=True)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as err:
        raise ValueError(f"not a usable picture: {err}") from err
    return out.getvalue()


def _write(folder: str, name: str, content: bytes) -> None:
    os.makedirs(folder, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=folder, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.replace(temp, os.path.join(folder, name))
    except BaseException:
        os.unlink(temp)
        raise


def _pins_on_disk(folder: str) -> set[str]:
    """The pins of the thumbnails in folder."""
    try:
        return {match.group(1) for name in os.listdir(folder) if (match := THUMBNAIL_NAME.fullmatch(name))}
    except FileNotFoundError:
        return set()


async def _download(session: aiohttp.ClientSession, url: str) -> bytes:
    # A redirect would lead to a host this integration does not know: it counts as a failure.
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT), allow_redirects=False) as response:
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        if (length := response.headers.get("Content-Length", "")).isdigit() and int(length) > MAX_DOWNLOAD:
            raise ValueError(f"larger than {MAX_DOWNLOAD} bytes")
        chunks, size = [], 0
        async for chunk in response.content.iter_chunked(65536):
            size += len(chunk)
            if size > MAX_DOWNLOAD:
                raise ValueError(f"larger than {MAX_DOWNLOAD} bytes")
            chunks.append(chunk)
        return b"".join(chunks)


class Pictures:
    """The thumbnails on disk; one per Home Assistant run, shared by config entries."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.folder = hass.config.path(*FOLDER)
        # Part of every picture path: the view answers only requests that carry it.
        self.token = secrets.token_hex(16)
        # The pins of the thumbnails on disk.
        self.cached: set[str] = set()
        # Picture name -> when fetching it failed last.
        self.failed: dict[str, float] = {}

    def markdown(self, name: str | None, pin: str | None) -> str:
        """The thumbnail linking to the full picture, as a paragraph; empty for a name in another shape
        than the manifest's (entries may share a pin) or without a thumbnail of this pin on disk."""
        if not name or not NAME.fullmatch(name) or pin not in self.cached:
            return ""
        return f"[![]({VIEW_URL.format(token=self.token, name=THUMBNAIL.format(pin=pin))})]({PICTURE_URL.format(name=quote(name))})\n\n"

    def missing(self, pins: Iterable[tuple[str | None, str | None]]) -> list[tuple[str, str]]:
        """The (name, sha256) of valid pinned pictures without a thumbnail that are not waiting for a retry."""
        now = time.time()
        return sorted(
            (name, sha)
            for name, sha in {(n, s) for n, s in pins if n and s}
            if NAME.fullmatch(name) and SHA256.fullmatch(sha) and sha not in self.cached and now - self.failed.get(name, 0) >= RETRY_AFTER
        )

    async def async_fetch(self, pins: Iterable[tuple[str, str]]) -> bool:
        """Fetch, check against the pin and scale the pictures one after the other; True when a new thumbnail arrived."""
        session = async_get_clientsession(self.hass)
        new = False
        for name, sha in pins:
            if not NAME.fullmatch(name) or not SHA256.fullmatch(sha) or sha in self.cached:
                continue
            try:
                content = await _download(session, PICTURE_URL.format(name=quote(name)))
                if hashlib.sha256(content).hexdigest() != sha:
                    raise ValueError("the picture does not match its pin")
                thumbnail = await self.hass.async_add_executor_job(scale, content)
                await self.hass.async_add_executor_job(_write, self.folder, THUMBNAIL.format(pin=sha), thumbnail)
            except (aiohttp.ClientError, TimeoutError, ValueError, OSError) as err:
                _LOGGER.debug("No picture %s: %s", name, err)
                self.failed[name] = time.time()
                continue
            self.cached.add(sha)
            self.failed.pop(name, None)
            new = True
        return new


class PictureView(HomeAssistantView):
    """A thumbnail on disk, without a login but with the token of this run; 404 for everything else."""

    url = VIEW_URL
    name = "api:xquirks:picture"
    requires_auth = False

    def __init__(self, pictures: Pictures) -> None:
        self.pictures = pictures

    async def get(self, request: web.Request, token: str, name: str) -> web.StreamResponse:
        if not secrets.compare_digest(token.encode(), self.pictures.token.encode()) or not (match := THUMBNAIL_NAME.fullmatch(name)) or match.group(1) not in self.pictures.cached:
            return web.Response(status=404)
        return web.FileResponse(os.path.join(self.pictures.folder, name), headers={"Cache-Control": "public, max-age=86400"})


DATA_PICTURES: HassKey[Pictures] = HassKey("xquirks_pictures")


async def async_get_pictures(hass: HomeAssistant) -> Pictures:
    """The pictures of this run; the first call reads the folder and registers the view."""
    if (pictures := hass.data.get(DATA_PICTURES)) is None:
        pictures = hass.data[DATA_PICTURES] = Pictures(hass)
        pictures.cached = await hass.async_add_executor_job(_pins_on_disk, pictures.folder)
        hass.http.register_view(PictureView(pictures))
    return pictures
