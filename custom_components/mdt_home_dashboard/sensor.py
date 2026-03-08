"""Sensor platform for MDT HOME Dashboard integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_DASHBOARD_URL,
    DATA_CLIENT,
    DATA_COORDINATOR,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SENSOR_CONNECTED_CLIENTS,
    SENSOR_DASHBOARD_STATE,
    SENSOR_LAST_UPDATE,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MDT HOME Dashboard sensors based on a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    client = entry_data.get(DATA_CLIENT)

    coordinator = MDTDashboardDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator so other platforms (binary_sensor, button) can reuse it
    entry_data[DATA_COORDINATOR] = coordinator

    sensors = [
        MDTDashboardConnectedClientsSensor(coordinator, entry),
        MDTDashboardLastUpdateSensor(coordinator, entry),
        MDTDashboardStateSensor(coordinator, entry),
        MDTDashboardActiveThemeSensor(coordinator, entry),
        MDTDashboardCurrentPageSensor(coordinator, entry),
        MDTDashboardEntityCountSensor(coordinator, entry),
        MDTDashboardVersionSensor(coordinator, entry),
    ]

    async_add_entities(sensors)


class MDTDashboardDataUpdateCoordinator(DataUpdateCoordinator):
    """Fetches real data from the dashboard backend via /api/integration/status."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client) -> None:
        self.entry = entry
        self._client = client  # DashboardClient | None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll the dashboard backend for live metrics."""
        if self._client is None:
            # No URL configured — return offline placeholder
            return {
                "status": "not_configured",
                "ha_connected": False,
                "connected_clients": 0,
                "entity_count": 0,
                "version": VERSION,
                "timestamp": None,
            }

        try:
            data = await self._client.get_status()
            data["online"] = True
            return data
        except Exception as err:
            # When the dashboard is unreachable we still update data so
            # binary sensors can reflect the outage (raise UpdateFailed would
            # prevent coordinator.data from updating).
            _LOGGER.debug("Dashboard unreachable: %s", err)
            return {
                "status": "offline",
                "online": False,
                "ha_connected": False,
                "connected_clients": 0,
                "entity_count": 0,
                "version": "unknown",
                "timestamp": None,
            }


class MDTDashboardSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for MDT Dashboard sensors."""

    def __init__(
        self,
        coordinator: MDTDashboardDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.data.get(CONF_NAME, DEFAULT_NAME),
            "manufacturer": "MDT",
            "model": "Home Dashboard",
            "sw_version": self.coordinator.data.get("version", VERSION),
            "configuration_url": self._entry.data.get(CONF_DASHBOARD_URL),
        }


class MDTDashboardConnectedClientsSensor(MDTDashboardSensorBase):
    """Number of frontend browser clients connected to the dashboard."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, SENSOR_CONNECTED_CLIENTS)
        self._attr_name = "Connected Clients"
        self._attr_icon = "mdi:devices"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return self.coordinator.data.get("connected_clients", 0)


class MDTDashboardLastUpdateSensor(MDTDashboardSensorBase):
    """Last timestamp the dashboard reported data."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, SENSOR_LAST_UPDATE)
        self._attr_name = "Last Update"
        self._attr_icon = "mdi:update"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("timestamp")


class MDTDashboardStateSensor(MDTDashboardSensorBase):
    """Overall dashboard state (ok / offline / not_configured)."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, SENSOR_DASHBOARD_STATE)
        self._attr_name = "Dashboard State"
        self._attr_icon = "mdi:monitor-dashboard"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "connected_clients": self.coordinator.data.get("connected_clients", 0),
            "ha_connected": self.coordinator.data.get("ha_connected", False),
        }


class MDTDashboardActiveThemeSensor(MDTDashboardSensorBase):
    """Active theme reported by the dashboard (if available)."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "active_theme")
        self._attr_name = "Active Theme"
        self._attr_icon = "mdi:theme-light-dark"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("active_theme", "auto")


class MDTDashboardCurrentPageSensor(MDTDashboardSensorBase):
    """Current page shown on the dashboard."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "current_page")
        self._attr_name = "Current Page"
        self._attr_icon = "mdi:page-layout-body"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("current_page", "home")


class MDTDashboardEntityCountSensor(MDTDashboardSensorBase):
    """Number of HA entities cached by the dashboard backend."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "entity_count")
        self._attr_name = "Entity Count"
        self._attr_icon = "mdi:counter"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return self.coordinator.data.get("entity_count", 0)


class MDTDashboardVersionSensor(MDTDashboardSensorBase):
    """Dashboard backend version."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "backend_version")
        self._attr_name = "Backend Version"
        self._attr_icon = "mdi:information-outline"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("version", "unknown")

