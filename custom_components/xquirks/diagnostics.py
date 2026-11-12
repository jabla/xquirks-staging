"""Diagnostics: the folder, the installed files and their state, what is offered."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import QuirksConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: QuirksConfigEntry) -> dict[str, Any]:
    return await entry.runtime_data.async_diagnostics()
