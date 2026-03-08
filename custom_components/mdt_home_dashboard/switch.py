"""Switch platform for MDT HOME Dashboard integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DASHBOARD_URL,
    DATA_CLIENT,
    DEFAULT_NAME,
    DOMAIN,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MDT HOME Dashboard switches based on a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data.get(DATA_CLIENT)

    async_add_entities([
        MDTDashboardScreensaverSwitch(hass, entry, client),
        MDTDashboardAutoThemeSwitch(hass, entry, client),
        MDTDashboardWebhooksSwitch(hass, entry, client),
        MDTDashboardSleepModeSwitch(hass, entry, client),
    ])


class _BaseSwitch(SwitchEntity):
    """Base class for MDT Dashboard switches."""

    def __init__(self, hass, entry, client, switch_type, name, icon, default=False):
        self.hass = hass
        self._entry = entry
        self._client = client
        self._switch_type = switch_type
        self._attr_unique_id = f"{entry.entry_id}_{switch_type}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_has_entity_name = True
        self._is_on = default

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

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def _toggle(self, state: bool) -> None:
        self._is_on = state
        # Fire HA event so the dashboard (via WS subscription) can react
        self.hass.bus.async_fire(
            f"{DOMAIN}_switch",
            {"switch_type": self._switch_type, "state": "on" if state else "off"},
        )
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._toggle(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._toggle(False)


class MDTDashboardScreensaverSwitch(_BaseSwitch):
    def __init__(self, hass, entry, client):
        super().__init__(hass, entry, client, "screensaver", "Screensaver", "mdi:monitor-off")


class MDTDashboardAutoThemeSwitch(_BaseSwitch):
    def __init__(self, hass, entry, client):
        super().__init__(hass, entry, client, "auto_theme", "Auto Theme", "mdi:theme-light-dark")


class MDTDashboardWebhooksSwitch(_BaseSwitch):
    def __init__(self, hass, entry, client):
        super().__init__(
            hass, entry, client, "webhooks", "Webhooks", "mdi:webhook",
            default=entry.data.get("enable_webhooks", True),
        )


class MDTDashboardSleepModeSwitch(_BaseSwitch):
    def __init__(self, hass, entry, client):
        super().__init__(hass, entry, client, "sleep_mode", "Sleep Mode", "mdi:sleep")
