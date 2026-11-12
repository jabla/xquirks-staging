"""Config flow (one entry) and the options (the devices xquirks leaves alone)."""

from __future__ import annotations

from pathlib import Path

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import STRINGS, Zha, apply_list, listed, published, setup_entry
from .integration import DOMAIN, const

IEEE = "00:11:22:33:44:55:66:01"


async def test_user_flow_creates_the_entry(hass: HomeAssistant, zha: Zha, quirks_dir: Path, repo_dir: Path):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"] == {"folder": str(quirks_dir)}
    with published(repo_dir):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done(wait_background_tasks=True)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.state is config_entries.ConfigEntryState.LOADED

    # Only one entry.
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_flow_without_custom_quirks_path(hass: HomeAssistant, zha: Zha):
    zha.data.yaml_config.pop("custom_quirks_path")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["description_placeholders"] == {"folder": "not configured"}


async def test_options_list_the_devices_xquirks_leaves_alone(hass: HomeAssistant, zha: Zha, repo_dir: Path, quirks_dir: Path):
    """Saving the options plans again: a file only an excluded device runs goes with the next list."""
    device = zha.add_device(IEEE, "_TZE200_aaaa", "TS0601")
    entry = await setup_entry(hass, repo_dir)
    await apply_list(hass)
    zha.reload({IEEE: "z2m_tuya_a:TuyaA"})
    await entry.runtime_data.async_refresh()
    assert listed(hass)["install"] == listed(hass)["remove"] == []

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "init"
    assert set(result["data_schema"].schema) == {const.CONF_EXCLUDED}
    assert set(STRINGS["options"]["step"]["init"]["data"]) == {const.CONF_EXCLUDED}
    result = await hass.config_entries.options.async_configure(result["flow_id"], {const.CONF_EXCLUDED: [device]})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert result["type"] is FlowResultType.CREATE_ENTRY and entry.options == {const.CONF_EXCLUDED: [device]}
    assert listed(hass)["remove"] == ["z2m_tuya_a.py"]
    # Nothing goes before the list is confirmed.
    assert (quirks_dir / "z2m_tuya_a.py").exists()

    # Taken off the list again: the file stays.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {const.CONF_EXCLUDED: []})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert listed(hass)["remove"] == []
