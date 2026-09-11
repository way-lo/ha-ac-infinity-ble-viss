"""Switch entities for an AC Infinity Bluetooth controller's auto-mode triggers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_MODEL, DOMAIN
from .coordinator import ACInfinityDataUpdateCoordinator
from .models import ACInfinityData
from .vendor.ac_infinity_ble import ACInfinityController


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up controller auto-mode trigger switches."""
    data: ACInfinityData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HighTempTriggerSwitch(data.coordinator, data.device),
            LowTempTriggerSwitch(data.coordinator, data.device),
        ]
    )


class ACInfinitySwitch(
    CoordinatorEntity[ACInfinityDataUpdateCoordinator], SwitchEntity
):
    """Base class for the controller's auto-mode trigger switches."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityController,
    ) -> None:
        """Initialize a switch entity."""
        super().__init__(coordinator)
        self._device = device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.address)},
            name=device.name,
            model=DEVICE_MODEL.get(
                device.state.type, f"Controller type {device.state.type}"
            ),
            manufacturer="AC Infinity",
            sw_version=str(device.state.version),
            connections={(dr.CONNECTION_BLUETOOTH, device.address)},
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Publish notification-driven or polled value changes."""
        self._async_update_attrs()
        self.async_write_ha_state()

    @callback
    def _async_update_attrs(self) -> None:
        """Update the is_on state."""
        raise NotImplementedError


class HighTempTriggerSwitch(ACInfinitySwitch):
    """Enable or disable the auto-mode high-temperature trigger."""

    _attr_name = "Auto Mode High Temperature Trigger"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.address}_auto_high_temp_trigger"
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_is_on = self._device.auto_high_temp_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the auto-mode high-temperature trigger."""
        await self._device.async_set_auto_mode_high_temp_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the auto-mode high-temperature trigger."""
        await self._device.async_set_auto_mode_high_temp_enabled(False)


class LowTempTriggerSwitch(ACInfinitySwitch):
    """Enable or disable the auto-mode low-temperature trigger."""

    _attr_name = "Auto Mode Low Temperature Trigger"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.address}_auto_low_temp_trigger"
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_is_on = self._device.auto_low_temp_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the auto-mode low-temperature trigger."""
        await self._device.async_set_auto_mode_low_temp_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the auto-mode low-temperature trigger."""
        await self._device.async_set_auto_mode_low_temp_enabled(False)
