"""Content states in the repository: the content-<n> tags and the files at them.

Only reads: one GitHub API request for the tag list (conditional: an unchanged list comes back
without a body, but without a token GitHub still counts it against the rate limit), content.json and
hacs.json of a newer tag, the manifest and
withdrawn.toml of the state taken, withdrawn.toml of a newer tag this release cannot use. A quirk
file only when the change list would write it: its code is checked before the list. Files are read at the commit
a tag points to, never by the tag's name. Every file is checked against the sha256 its manifest
states before anything is done with it.
"""

from __future__ import annotations

import dataclasses
import json
import re
import time

import aiohttp

from .const import FETCH_TIMEOUT, MAX_DOWNLOAD, RAW_URL, TAGS_URL
from .content import COMMIT, BadContent, ContentState, from_manifest, parse_guard, parse_homeassistant, parse_withdrawn, sha256

# At most nine digits: a longer number is no tag of this repository (and would not convert cheaply).
TAG = re.compile(r"refs/tags/(content-([1-9][0-9]{0,8}))")
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
DIGITS = re.compile(r"[0-9]{1,12}")
# The longest wait a rate limit answer is followed for: a larger value must not stop checks for good.
MAX_WAIT = 24 * 3600


class FetchError(Exception):
    """A request failed or returned something unusable; the message says what."""


class BadTag(FetchError):
    """What a tag holds cannot be used: a required file is missing, too large or malformed. Content
    at a commit never changes, so asking again does not help. The caller names the tag."""


class RateLimited(FetchError):
    """GitHub refuses requests until `until` (epoch seconds)."""

    def __init__(self, until: float) -> None:
        super().__init__(f"GitHub rate limit, next try after {time.strftime('%H:%M', time.localtime(until))}")
        self.until = until


@dataclasses.dataclass(frozen=True)
class Ref:
    """A content-<n> tag as the tag list shows it."""

    number: int
    tag: str
    # The commit the tag points to.
    commit: str


@dataclasses.dataclass(frozen=True)
class Tags:
    # Every content-<n> tag, newest first.
    found: tuple[Ref, ...]
    etag: str | None

    def get(self, tag: str) -> Ref | None:
        return next((ref for ref in self.found if ref.tag == tag), None)


@dataclasses.dataclass(frozen=True)
class Meta:
    """What a tag needs: the guard it was built for (None when it names none) and its Home Assistant release."""

    homeassistant: str | None
    guard: str | None = None


def _timeout() -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(total=FETCH_TIMEOUT)


async def _read(response: aiohttp.ClientResponse, url: str) -> bytes:
    """The body, refused beyond MAX_DOWNLOAD bytes."""
    if (length := response.headers.get("Content-Length", "")).isdigit() and int(length) > MAX_DOWNLOAD:
        raise BadTag(f"{url}: larger than {MAX_DOWNLOAD} bytes")
    chunks, size = [], 0
    async for chunk in response.content.iter_chunked(65536):
        size += len(chunk)
        if size > MAX_DOWNLOAD:
            raise BadTag(f"{url}: larger than {MAX_DOWNLOAD} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def _rate_limit(response: aiohttp.ClientResponse) -> float | None:
    """The time GitHub accepts requests again (at most MAX_WAIT ahead), None when the refusal is not a rate limit."""
    if response.status not in (403, 429):
        return None
    now = time.time()
    if retry := response.headers.get("Retry-After"):
        # Seconds; an HTTP date (or anything else) counts as a minute.
        return now + min(int(retry) if DIGITS.fullmatch(retry) else 60, MAX_WAIT)
    if response.headers.get("X-RateLimit-Remaining") == "0" and DIGITS.fullmatch(reset := response.headers.get("X-RateLimit-Reset", "")):
        return min(float(reset), now + MAX_WAIT)
    return now + 3600 if response.status == 429 else None


async def _fetch(session: aiohttp.ClientSession, url: str, *, missing_ok: bool = False) -> bytes | None:
    """A file; None for a 404 when missing_ok, BadTag for any other 404."""
    try:
        async with session.get(url, timeout=_timeout()) as response:
            if response.status == 404:
                if missing_ok:
                    return None
                raise BadTag(f"{url}: HTTP 404")
            if (until := _rate_limit(response)) is not None:
                raise RateLimited(until)
            if response.status != 200:
                raise FetchError(f"{url}: HTTP {response.status}")
            return await _read(response, url)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise FetchError(f"{url}: {err or type(err).__name__}") from err


def _raw(commit: str, path: str) -> str:
    return RAW_URL.format(commit=commit, path=path)


async def async_tags(session: aiohttp.ClientSession, etag: str | None) -> Tags | None:
    """The content tags; None when the tag list did not change since etag."""
    headers = dict(HEADERS)
    if etag:
        headers["If-None-Match"] = etag
    try:
        async with session.get(TAGS_URL, headers=headers, timeout=_timeout()) as response:
            if response.status == 304:
                return None
            if (until := _rate_limit(response)) is not None:
                raise RateLimited(until)
            if response.status == 404:
                # matching-refs answers with an empty list; 404 means the repository is not reachable.
                raise FetchError(f"{TAGS_URL}: not found")
            if response.status != 200:
                raise FetchError(f"{TAGS_URL}: HTTP {response.status}")
            body = await _read(response, TAGS_URL)
            new_etag = response.headers.get("ETag")
        refs = json.loads(body)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise FetchError(f"{TAGS_URL}: {err or type(err).__name__}") from err
    except (ValueError, RecursionError) as err:
        raise FetchError(f"{TAGS_URL}: {err}") from err
    if not isinstance(refs, list):
        raise FetchError(f"{TAGS_URL}: not a list of refs")
    found: dict[int, Ref] = {}
    # GitHub sends objects only; anything else is a broken answer, not a list without tags.
    if not all(isinstance(item, dict) for item in refs):
        raise FetchError(f"{TAGS_URL}: not a list of refs")
    for item in refs:
        if not (match := TAG.fullmatch(str(item.get("ref", "")))):
            continue
        # Content tags are lightweight: an annotated one (type "tag") is no content state.
        target = item.get("object")
        if not isinstance(target, dict) or target.get("type") != "commit" or not COMMIT.fullmatch(str(target.get("sha", ""))):
            continue
        number = int(match.group(2))
        found[number] = Ref(number, match.group(1), target["sha"])
    return Tags(tuple(found[n] for n in sorted(found, reverse=True)), new_etag)


async def async_meta(session: aiohttp.ClientSession, commit: str) -> Meta:
    """The guard and minimum Home Assistant release of a tag (two small files)."""
    content_json = await _fetch(session, _raw(commit, "content.json"), missing_ok=True)
    hacs_json = await _fetch(session, _raw(commit, "hacs.json"))
    try:
        guard = parse_guard(content_json.decode()) if content_json else None
        homeassistant = parse_homeassistant(hacs_json.decode())
    except (ValueError, AttributeError, RecursionError) as err:
        # BadContent and JSON errors are ValueErrors; JSON that is no object raises the other.
        raise BadTag(str(err)) from err
    return Meta(homeassistant, guard)


async def async_state(session: aiohttp.ClientSession, ref: Ref, homeassistant: str | None) -> ContentState:
    """The content state at the tag: its manifest and withdrawn revisions."""
    manifest = await _fetch(session, _raw(ref.commit, "manifest.json"))
    withdrawn_text = await _fetch(session, _raw(ref.commit, "data/withdrawn.toml"), missing_ok=True)
    try:
        withdrawn = parse_withdrawn(withdrawn_text.decode()) if withdrawn_text else {}
        return from_manifest(json.loads(manifest), tag=ref.tag, content=ref.number, commit=ref.commit, homeassistant=homeassistant, withdrawn=withdrawn)
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError) as err:
        # BadContent and JSON errors are ValueErrors; from_manifest checks the shape of every entry.
        raise BadTag(str(err)) from err


async def async_withdrawn(session: aiohttp.ClientSession, commit: str) -> dict[tuple[str, str], str]:
    """The withdrawn revisions a tag lists, read also when this release cannot use its files (the
    fields of withdrawn.toml never change)."""
    text = await _fetch(session, _raw(commit, "data/withdrawn.toml"), missing_ok=True)
    try:
        return parse_withdrawn(text.decode()) if text else {}
    except (BadContent, UnicodeDecodeError) as err:
        raise BadTag(str(err)) from err


async def async_file(session: aiohttp.ClientSession, state: ContentState, name: str) -> bytes:
    """One quirk file of a fetched state, checked against the sha256 its manifest states."""
    if state.commit is None:
        raise FetchError(f"{state.tag}: no commit known for it")
    content = await _fetch(session, _raw(state.commit, state.paths[name]))
    if sha256(content) != state.shas[name]:
        raise BadTag(f"{name} at {state.tag} does not have the sha256 its manifest states")
    return content
