"""Config flow: one entry, no settings needed. Options: the devices xquirks leaves alone."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import DeviceSelector, DeviceSelectorConfig

from .const import CONF_EXCLUDED, DOMAIN, TITLE, ZHA_DOMAIN
from .manager import zha_folder


class QuirksConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        # manifest.json has single_config_entry: Home Assistant aborts a second flow itself.
        if user_input is not None:
            return self.async_create_entry(title=TITLE, data={})
        return self.async_show_form(
            step_id="user",
            description_placeholders={"folder": zha_folder(self.hass) or "not configured"},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> QuirksOptionsFlow:
        return QuirksOptionsFlow()


class QuirksOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            # Saving reloads nothing: the manager plans again (its update listener).
            return self.async_create_entry(data={CONF_EXCLUDED: sorted(user_input.get(CONF_EXCLUDED, []))})
        excluded = list(self.config_entry.options.get(CONF_EXCLUDED, []))
        schema = vol.Schema({vol.Optional(CONF_EXCLUDED, default=excluded): DeviceSelector(DeviceSelectorConfig(integration=ZHA_DOMAIN, multiple=True))})
        return self.async_show_form(step_id="init", data_schema=schema)
