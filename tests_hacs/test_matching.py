"""The integration's matching rules on the fixture manifest."""

from __future__ import annotations

from .conftest import MANIFEST
from .integration import matching


def test_rules_on_the_fixture():
    devices = {("_TZE200_aaaa", "TS0601"), ("_TZE200_zzzz", "TS0601"), ("Anyone", "B-1"), ("Other", "B-1"), ("Acme", "C-1"), ("acme", "C-1"), ("Acme", "D-1")}
    found = {(device, slug) for device, slug, _entry in matching.matches(MANIFEST, devices)}
    assert found == {
        (("_TZE200_aaaa", "TS0601"), "tuya_a"),  # exact fingerprint
        (("Anyone", "B-1"), "acme_b"),  # model-only fingerprint, any manufacturer
        (("Acme", "C-1"), "acme_c"),  # exact, case matters
        (("Acme", "D-1"), "acme_d"),  # matches; it has no file, the plan skips it
    }  # ("Other", "B-1") is claimed elsewhere
