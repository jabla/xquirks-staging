"""A button that looks for a newer content state in the repository right away."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import QuirksConfigEntry
from .const import DESCRIPTION, DOMAIN, TITLE


async def async_setup_entry(hass: HomeAssistant, entry: QuirksConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([CheckButton(entry)])


class CheckButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "check_now"

    def __init__(self, entry: QuirksConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_check_now"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=TITLE, model=DESCRIPTION, entry_type=DeviceEntryType.SERVICE)

    async def async_press(self) -> None:
        await self._entry.runtime_data.async_check()
