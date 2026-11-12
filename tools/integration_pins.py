"""The Home Assistant release the integration's tests run on and the minimum it installs on.

Usage: python tools/integration_pins.py [--requirements tests_hacs/requirements.txt]
           [--hacs-json hacs.json] [--release YYYY.M.P]

For a Home Assistant release (the newest one, or the one --release names) it reads the
requirements of the components the integration's tests load (zha and what it imports) from their
manifest.json at that tag, plus the requirements of zha and of Home Assistant's own test package of
that release (pytest-homeassistant) on PyPI; that test package must be there. Only GET requests
(GitHub REST API, PyPI JSON API); a GITHUB_TOKEN in the environment raises the GitHub rate limit.

Prints the pins as JSON. --requirements rewrites every pin of that file the release pins exactly
(the components first, then zha, then the test package), the test package included, plus the
release in its "pinned as in" comment. Then it prints one line for the pull request text and one
line for everything to fix by hand: a requirement the release adds, a pin of the file the release
does not pin exactly, a pin the release sets only under an environment marker. It adds and removes
nothing. A line of the file other than a pin (name==version, an inline comment allowed), a comment
or a blank line stops it. --hacs-json sets the minimum Home Assistant version in hacs.json to that
release, patch number included: HACS installs the integration only on the release its tests ran on
or newer.

Both files are replaced only after both were read, checked and written to a temporary file beside
them: an error up to then leaves both as they were, only the two renames at the end could still fail
apart.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import os
import pathlib
import re
import shutil
import tempfile
import typing
import urllib.error
import urllib.request

# Home Assistant's test package, published with each release under the release's version.
HARNESS = "pytest-homeassistant"
# The components the integration's tests load: zha and what it imports (usb imports hassio).
COMPONENTS = ("zha", "usb", "homeassistant_hardware", "hassio")
# A pin of the requirements file: name==version, an inline comment allowed (whitespace, then "#").
FILE_PIN = re.compile(r"(\s*([A-Za-z0-9][A-Za-z0-9_.-]*)==)([\w.!+-]+)((?:\s+#.*)?\s*)")
# A comment or a blank line.
FILE_OTHER = re.compile(r"\s*(?:#.*)?")
PINNED_AS = re.compile(r"pinned as in \d{4}\.\d+\.\d+\.$")
# A release as Home Assistant tags it.
RELEASE = re.compile(r"\d{4}\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


def get_json(url: str) -> dict | list:
    headers = {"Accept": "application/vnd.github+json"} if "api.github.com" in url else {}
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return json.loads(response.read())


def release_tags() -> list[tuple[int, int, int]]:
    tags = []
    for page in range(1, 6):
        batch = get_json(f"https://api.github.com/repos/home-assistant/core/tags?per_page=100&page={page}")
        for tag in batch:
            m = re.fullmatch(r"(\d{4})\.(\d+)\.(\d+)", tag["name"])
            if m:
                tags.append(tuple(int(x) for x in m.groups()))
        if len(batch) < 100:
            break
    return sorted(set(tags))


# An exact pin as package metadata writes it: name==version or the older name (==version), extras
# allowed; an environment marker follows after ";".
EXACT = re.compile(r"([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[^\]]*\])?(?:==([\w.!+-]+)|\(==([\w.!+-]+)\))")
# A marker that tests the extra, on either side of the comparison.
EXTRA = re.compile(r"(?<![\w.])extra\s*(?:==|!=)|(?:==|!=)\s*extra(?![\w.])")


def canonical(name: str) -> str:
    """A package name as PyPI compares names: case and runs of "-", "_" and "." do not count."""
    return re.sub(r"[-_.]+", "-", name).lower()


def exact_pins(requirements: list[str]) -> tuple[dict[str, str], list[str]]:
    """Canonical name to version of each exact pin without an environment marker, plus the exact
    pins with one (they hold only where the marker does, so they are not taken). A pin for an extra
    is neither: pip installs it only with that extra. Two different pins of one name are refused."""
    pins, marked = {}, []
    for requirement in requirements:
        spec, _, marker = requirement.partition(";")
        m = EXACT.fullmatch(spec.replace(" ", ""))
        if not m or EXTRA.search(marker):
            continue
        name, version = canonical(m.group(1)), m.group(2) or m.group(3)
        if marker.strip():
            marked.append(requirement.strip())
        elif pins.setdefault(name, version) != version:
            raise SystemExit(f"two different pins of {name}: {pins[name]} and {version}")
    return pins, marked


def write_all(texts: dict[pathlib.Path, str]) -> None:
    """Every file or none: each new text goes to a temporary file beside its file (with the file's
    mode) first, the renames come last."""
    temporary = {}
    try:
        for path, text in texts.items():
            if not os.access(path, os.W_OK):
                raise OSError(f"{path} is not writable")
            fd, name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
            temporary[path] = name
            with os.fdopen(fd, "w") as f:
                f.write(text)
            shutil.copymode(path, name)
    except OSError as error:
        for name in temporary.values():
            with contextlib.suppress(OSError):
                os.unlink(name)
        raise SystemExit(f"nothing written: {error}") from None
    for path, name in temporary.items():
        os.replace(name, path)


def component_requirements(version: str, *components: str) -> list[str]:
    """The requirements of Home Assistant components at a release tag."""
    requirements = []
    for component in components:
        content = get_json(f"https://api.github.com/repos/home-assistant/core/contents/homeassistant/components/{component}/manifest.json?ref={version}")
        requirements += json.loads(base64.b64decode(content["content"])).get("requirements", [])
    return requirements


def harness(version: str) -> list[str]:
    """The requirements of the pytest-homeassistant release for this Home Assistant version, which
    must pin that version."""
    try:
        requires = get_json(f"https://pypi.org/pypi/{HARNESS}/{version}/json")["info"]["requires_dist"] or []
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        requires = []
    if f"homeassistant=={version}" not in [r.replace(" ", "") for r in requires]:
        raise SystemExit(f"no {HARNESS} release pins homeassistant=={version} yet")
    return requires


class Pins(typing.NamedTuple):
    """A release's exact pins by canonical name."""

    # What the tests need: the components' pins and the test package.
    needed: dict[str, str]
    # zha's own pins and the test package's, for packages the components do not pin.
    zha: dict[str, str]
    harness: dict[str, str]
    # Pins under an environment marker: canonical name to the requirements. marked_needed names the
    # packages a component sets one for.
    marked: dict[str, list[str]]
    marked_needed: set[str]

    @property
    def known(self) -> dict[str, str]:
        """Every pin the file may follow: the components first, then zha, then the test package."""
        return self.harness | self.zha | self.needed


def pins(version: str) -> Pins:
    needed, marked_components = exact_pins(component_requirements(version, *COMPONENTS))
    needed[HARNESS] = version
    harness_pins, marked_harness = exact_pins(harness(version))
    zha_pins, marked_zha = {}, []
    if needed.get("zha"):
        zha_pins, marked_zha = exact_pins(get_json(f"https://pypi.org/pypi/zha/{needed['zha']}/json")["info"]["requires_dist"] or [])
    marked = {}
    for requirement in marked_components + marked_zha + marked_harness:
        marked.setdefault(canonical(EXACT.match(requirement.replace(" ", "")).group(1)), []).append(requirement)
    marked_needed = {canonical(EXACT.match(requirement.replace(" ", "")).group(1)) for requirement in marked_components}
    return Pins(needed, zha_pins, harness_pins, marked, marked_needed)


def requirements_text(text: str, path: pathlib.Path | str, version: str, found: Pins) -> tuple[str, str | None, list[str]]:
    """The file with every pin the release pins exactly raised and the release in its comment; the
    release the file was pinned to (its test package); a line for everything to fix by hand."""
    known, lines, seen, old, report = found.known, [], set(), None, []
    for number, line in enumerate(text.splitlines(), 1):
        m = FILE_PIN.fullmatch(line)
        if m:
            name, pin = canonical(m.group(2)), f"{m.group(2)}=={m.group(3)}"
            seen.add(name)
            if name == HARNESS:
                old = m.group(3)
            if name in known:
                line = f"{m.group(1)}{known[name]}{m.group(4)}"
            elif name in found.marked:
                report.append(f"- {path} keeps {pin}: Home Assistant {version} pins it only under an environment marker ({'; '.join(found.marked[name])}): fix it by hand")
            else:
                report.append(f"- {path} keeps {pin}, which neither the components' manifests nor zha nor {HARNESS} pin exactly: fix it by hand")
        elif not FILE_OTHER.fullmatch(line):
            raise SystemExit(f"{path}:{number}: {line.strip()!r} is no pin (name==version), comment or blank line: nothing written")
        lines.append(PINNED_AS.sub(f"pinned as in {version}.", line))
    report += [f"- {path} lacks {name}=={pin}, a requirement of Home Assistant {version}: add it by hand" for name, pin in found.needed.items() if name not in seen]
    report += [f"- {path} lacks {requirement}, a requirement of Home Assistant {version} under an environment marker: add it by hand where it holds"
               for name in sorted(found.marked_needed - seen) for requirement in found.marked[name]]
    return "\n".join(lines) + "\n", old, report


def hacs_json_text(text: str, path: pathlib.Path | str, version: str) -> str:
    """hacs.json with the release the tests ran on as the minimum, patch number included."""
    try:
        data = json.loads(text)
    except ValueError as error:
        raise SystemExit(f"{path}: {error}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: no JSON object")
    data["homeassistant"] = version
    return json.dumps(data, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", type=pathlib.Path, help="rewrite the pins of the integration's tests in this file")
    parser.add_argument("--hacs-json", type=pathlib.Path, help="set the minimum Home Assistant version in this hacs.json")
    parser.add_argument("--release", help="the Home Assistant release YYYY.M.P to pin (default: the newest)")
    args = parser.parse_args()
    if args.release is not None and not RELEASE.fullmatch(args.release):
        parser.error(f"--release {args.release!r} is no release YYYY.M.P")
    tags = release_tags()
    if args.release is None:
        version = ".".join(map(str, tags[-1]))
    elif tuple(map(int, args.release.split("."))) in tags:
        version = args.release
    else:
        raise SystemExit(f"Home Assistant has no release {args.release}")
    found = pins(version)
    texts, report = {}, []
    if args.requirements:
        texts[args.requirements], old, lines = requirements_text(args.requirements.read_text(), args.requirements, version, found)
        was = f" (was {old})" if old and old != version else ""
        report += [f"- Home Assistant release of the integration's tests: {version}{was}", *lines]
    else:
        report.append(json.dumps({"ha": version, "pins": dict(sorted(found.needed.items())), "zha": dict(sorted(found.zha.items())),
                                  HARNESS: dict(sorted(found.harness.items())), "marked": found.marked}, indent=1))
    if args.hacs_json:
        texts[args.hacs_json] = hacs_json_text(args.hacs_json.read_text(), args.hacs_json, version)
    write_all(texts)
    print("\n".join(report))


if __name__ == "__main__":
    main()
