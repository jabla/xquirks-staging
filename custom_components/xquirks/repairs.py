"""Fix flows: the change list (confirmed as a whole) and the reminder to reload ZHA.

The change list's dialog shows every install, update and removal; "Apply all" carries them out
together (manager.async_apply) and reloads ZHA right after, so they take effect without another
step. The "changes wait for a ZHA reload" issue is left only when ZHA was not loaded; it reloads
ZHA when the user picks it.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from . import text
from .const import DOMAIN

if TYPE_CHECKING:
    from .manager import QuirkManager


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict | None) -> RepairsFlow:
    data = dict(data or {})
    flows = {"changes": ChangesFlow, "reload": ReloadFlow}
    return flows.get(data.get("kind"), UnknownFlow)(issue_id, data)


class _QuirkFlow(RepairsFlow):
    """The dialog is a menu: the change ("apply") or "not_now".

    Home Assistant shows no Ignore for fixable issues, so "not_now" ignores the issue itself. It
    then waits under "Show ignored repairs"; a list with another id comes back as a new issue.
    """

    # The abort when the issue went while the dialog was open.
    GONE = "nothing_to_do"

    def __init__(self, issue_id: str, data: dict) -> None:
        super().__init__()
        self.issue_id = issue_id
        self.issue_data = data

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        # Home Assistant calls init with {"issue_id": ...} as user_input: the dialog is "confirm".
        return await self.async_step_confirm()

    async def async_step_not_now(self, user_input: dict | None = None) -> FlowResult:
        if ir.async_get(self.hass).async_get_issue(DOMAIN, self.issue_id) is None:
            # Another list came, or ZHA reloaded, while the dialog was open: nothing to put aside.
            return self.async_abort(reason=self.GONE)
        ir.async_ignore_issue(self.hass, DOMAIN, self.issue_id, True)
        return self.async_abort(reason="not_now")

    def _manager(self) -> QuirkManager | None:
        entries = self.hass.config_entries.async_loaded_entries(DOMAIN)
        return entries[0].runtime_data if entries else None


class ChangesFlow(_QuirkFlow):
    """Every change of the list, applied together or not at all."""

    GONE = "stale"

    def _gone(self, manager: QuirkManager) -> FlowResult | None:
        """The abort when the list the issue was made for is not the current one."""
        plan = manager.plan
        if plan.held:
            return self._held(plan.held)
        if not plan.changes or plan.key != self.issue_data.get("key"):
            return self.async_abort(reason="stale")
        return None

    def _held(self, reason: str) -> FlowResult:
        """Nothing was changed: a whole text per reason the list is held (plan.py), in the user's language."""
        return self.async_abort(reason=f"held_{reason}")

    async def async_step_confirm(self, user_input: dict | None = None) -> FlowResult:
        if (manager := self._manager()) is None:
            return self.async_abort(reason="not_loaded")
        # Decided on a fresh plan, as the apply is: a hold whose cause went away ends here.
        await manager.async_refresh()
        if (gone := self._gone(manager)) is not None:
            return gone
        placeholders = {"changes": await manager.async_change_text(), "folder": manager.folder or ""}
        return self.async_show_menu(step_id="confirm", menu_options=["apply", "not_now"], description_placeholders=placeholders)

    async def async_step_apply(self, user_input: dict | None = None) -> FlowResult:
        if (manager := self._manager()) is None:
            return self.async_abort(reason="not_loaded")
        # Home Assistant cancels this request when the browser goes away: the list is carried out to
        # its end all the same, only the reload of ZHA is then left to the reminder.
        applied = await asyncio.shield(self.hass.async_create_task(manager.async_apply(self.issue_data.get("key", ""))))
        if applied.held:
            return self._held(applied.held)
        if applied.stale:
            return self.async_abort(reason="stale")
        placeholders: dict[str, Any] = {"folder": manager.folder or ""}
        if applied.failed and not applied.left:
            return self.async_abort(reason="failed", description_placeholders={**placeholders, "failed": applied.failed})
        reloading = manager.async_reload_zha()
        if applied.failed:
            # Some steps could not be undone: ZHA loads what is there, the next list repairs the rest.
            return self.async_abort(reason="failed_partly", description_placeholders={**placeholders, "failed": applied.failed, "left": text.name_list(applied.left)})
        return self.async_abort(reason="done" if reloading else "done_zha_not_loaded", description_placeholders={**placeholders, "done": text.name_list(applied.done)})


class ReloadFlow(_QuirkFlow):
    async def async_step_confirm(self, user_input: dict | None = None) -> FlowResult:
        if (manager := self._manager()) is None:
            return self.async_abort(reason="not_loaded")
        if not (changes := manager.data["pending"]["changes"]):
            return self.async_abort(reason="nothing_to_do")
        placeholders = {"changes": text.name_list([f"`{c['file']}`: {c['change']}" for c in changes]), "folder": manager.folder or ""}
        return self.async_show_menu(step_id="confirm", menu_options=["apply", "not_now"], description_placeholders=placeholders)

    async def async_step_apply(self, user_input: dict | None = None) -> FlowResult:
        if (manager := self._manager()) is None:
            return self.async_abort(reason="not_loaded")
        if not manager.data["pending"]["changes"]:
            return self.async_abort(reason="nothing_to_do")
        manager.async_reload_zha()
        return self.async_create_entry(data={})


class UnknownFlow(RepairsFlow):
    def __init__(self, issue_id: str, data: dict) -> None:
        super().__init__()

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        return self.async_abort(reason="nothing_to_do")
