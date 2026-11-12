"""Install the quirk files of this collection that match your ZHA devices.

The list of quirk files comes from the newest content-<n> state of the repository (checked every
few hours or with the "check for quirk updates" button, kept across restarts). It matches the
files against the ZHA devices in the device registry and gathers every install, update and
removal into one change list, a repair issue. A file is downloaded when the list would write it:
the guard (guard.py) checks its code before the list and again before it is written, a refused
file is never written. Nothing is written, updated, removed or reloaded until the user confirms
the list in the issue's fix flow.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .manager import QuirkManager

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.BUTTON]

type QuirksConfigEntry = ConfigEntry[QuirkManager]


async def async_setup_entry(hass: HomeAssistant, entry: QuirksConfigEntry) -> bool:
    manager = QuirkManager(hass, entry)
    entry.runtime_data = manager
    await manager.async_setup()
    await manager.async_clean_temp()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: QuirksConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    if entry.disabled_by is not None:
        # Disabled: its offers cannot be acted on, so they go (they come back when it is enabled).
        entry.runtime_data.async_delete_issues()
    # A plain reload keeps the issues: they keep whether the user ignored them. The next setup
    # brings them up to date.
    return True


async def async_remove_entry(hass: HomeAssistant, entry: QuirksConfigEntry) -> None:
    # The installed files and their records stay: a new entry can still update them.
    registry = ir.async_get(hass)
    for domain, issue_id in list(registry.issues):
        if domain == DOMAIN:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
