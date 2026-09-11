"""Fan entity for an AC Infinity Bluetooth controller."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import DEVICE_MODEL, DOMAIN
from .coordinator import ACInfinityDataUpdateCoordinator
from .models import ACInfinityData
from .vendor.ac_infinity_ble import ACInfinityController

SPEED_RANGE = (1, 10)

PRESET_AUTO_MODE = "Auto"
PRESET_ON_MODE = "On"
WORK_TYPE_ON = 2
WORK_TYPE_AUTO = 3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the controller fan entity."""
    data: ACInfinityData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ACInfinityFan(data.coordinator, data.device)])


class ACInfinityFan(CoordinatorEntity[ACInfinityDataUpdateCoordinator], FanEntity):
    """Represent the selected AC Infinity controller port as a fan."""

    _attr_has_entity_name = True
    _attr_name = "Fan"
    _attr_speed_count = int_states_in_range(SPEED_RANGE)
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = [PRESET_AUTO_MODE, PRESET_ON_MODE]

    @property
    def is_on(self) -> bool | None:
        """Return true only if fan is actually spinning.

        HA's base FanEntity falls back to `percentage > 0 or preset_mode is
        not None` when this isn't overridden — which reports "on" the moment
        any preset_mode is set, even for the intentionally-idle Auto case
        below. Overriding this makes _attr_is_on authoritative.
        """
        return self._attr_is_on

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityController,
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator)
        self._device = device
        self._attr_extra_state_attributes = {"physical_port": device.port}
        self._attr_unique_id = f"{device.address}_fan"
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
        self._async_update_attrs()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set speed in ten discrete steps; zero turns the fan off."""
        speed = 0
        if percentage > 0:
            speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self._device.set_speed(speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on, optionally at a requested percentage or preset."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
            return
        speed = None
        if percentage is not None:
            speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self._device.turn_on(speed)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off without overwriting the stored ON speed."""
        await self._device.turn_off()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Select Auto or On mode without rewriting either saved speed preset."""
        if preset_mode == PRESET_AUTO_MODE:
            await self._device.set_mode_auto()
        elif preset_mode == PRESET_ON_MODE:
            await self._device.turn_on(None)
        else:
            raise ValueError(f"Unsupported preset mode: {preset_mode}")

    @callback
    def _async_update_attrs(self) -> None:
        """Update Home Assistant state from the controller model."""
        work_type = self._device.state.work_type
        fan_speed = self._device.state.fan
        if work_type == WORK_TYPE_AUTO:
            self._attr_preset_mode = PRESET_AUTO_MODE
            # Speed 1 is the range floor, not really "spinning" — treat it as
            # idle so the icon doesn't animate while auto-mode is just waiting.
            if fan_speed and fan_speed > 1:
                self._attr_is_on = True
                self._attr_percentage = ranged_value_to_percentage(SPEED_RANGE, fan_speed)
            else:
                self._attr_is_on = False
                self._attr_percentage = 0
        elif work_type == WORK_TYPE_ON:
            self._attr_is_on = True
            self._attr_preset_mode = PRESET_ON_MODE
            self._attr_percentage = (
                ranged_value_to_percentage(SPEED_RANGE, fan_speed) if fan_speed else 0
            )
        else:
            self._attr_is_on = False
            self._attr_preset_mode = None
            self._attr_percentage = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle telemetry, command, and periodic model updates."""
        self._async_update_attrs()
        self.async_write_ha_state()
