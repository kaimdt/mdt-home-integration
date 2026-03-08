"""Button platform for MDT HOME Dashboard integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DASHBOARD_URL, DATA_CLIENT, DEFAULT_NAME, DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MDT HOME Dashboard buttons based on a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data.get(DATA_CLIENT)

    async_add_entities([
        MDTDashboardRefreshButton(hass, entry, client),
        MDTDashboardClearCacheButton(hass, entry, client),
        MDTDashboardRestartButton(hass, entry, client),
    ])


class _BaseButton(ButtonEntity):
    """Base class for MDT Dashboard buttons."""

    def __init__(self, hass, entry, client, button_type, name, icon):
        self.hass = hass
        self._entry = entry
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_{button_type}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_has_entity_name = True
        self._button_type = button_type

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.data.get(CONF_NAME, DEFAULT_NAME),
            "manufacturer": "MDT",
            "model": "Home Dashboard",
            "sw_version": VERSION,
            "configuration_url": self._entry.data.get(CONF_DASHBOARD_URL),
        }

    async def _send(self, command: str) -> None:
        """Send a command to the dashboard backend and fire an HA event."""
        if self._client:
            try:
                await self._client.send_command(command)
            except Exception:
                _LOGGER.warning("Dashboard unreachable for command %s", command)
        self.hass.bus.async_fire(
            f"{DOMAIN}_button",
            {"button_type": self._button_type, "action": "pressed"},
        )


class MDTDashboardRefreshButton(_BaseButton):
    """Trigger a state refresh on the dashboard backend."""

    def __init__(self, hass, entry, client):
        super().__init__(hass, entry, client, "refresh", "Refresh", "mdi:refresh")

    async def async_press(self) -> None:
        await self._send("refresh")


class MDTDashboardClearCacheButton(_BaseButton):
    """Clear the dashboard entity cache."""

    def __init__(self, hass, entry, client):
        super().__init__(hass, entry, client, "clear_cache", "Clear Cache", "mdi:delete-sweep")

    async def async_press(self) -> None:
        await self._send("clear_cache")


class MDTDashboardRestartButton(_BaseButton):
    """Request a dashboard restart."""

    def __init__(self, hass, entry, client):
        super().__init__(hass, entry, client, "restart", "Restart Backend", "mdi:restart")

    async def async_press(self) -> None:
        await self._send("restart")
