"""Number entities for an AC Infinity Bluetooth controller's speed presets."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
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
    """Set up controller min/max speed number entities."""
    data: ACInfinityData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MinSpeedNumber(data.coordinator, data.device),
            MaxSpeedNumber(data.coordinator, data.device),
            AutoHighTempNumber(data.coordinator, data.device),
            AutoLowTempNumber(data.coordinator, data.device),
        ]
    )


class ACInfinityNumber(
    CoordinatorEntity[ACInfinityDataUpdateCoordinator], NumberEntity
):
    """Base class for the controller's stored speed-preset numbers."""

    _attr_has_entity_name = True
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityController,
    ) -> None:
        """Initialize a number entity."""
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
        """Update the native value."""
        raise NotImplementedError


class MinSpeedNumber(ACInfinityNumber):
    """Stored minimum speed preset (auto-mode floor)."""

    _attr_name = "Min Speed"
    _attr_icon = "mdi:fan-chevron-down"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.address}_min_speed"
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_native_value = self._device.min_speed

    async def async_set_native_value(self, value: float) -> None:
        """Write the new minimum speed preset to the controller."""
        await self._device.async_set_min_speed(int(value))


class MaxSpeedNumber(ACInfinityNumber):
    """Stored maximum speed preset (auto-mode ceiling)."""

    _attr_name = "Max Speed"
    _attr_icon = "mdi:fan-chevron-up"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.address}_max_speed"
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_native_value = self._device.max_speed

    async def async_set_native_value(self, value: float) -> None:
        """Write the new maximum speed preset to the controller."""
        await self._device.async_set_max_speed(int(value))


def _c_to_f(celsius: int) -> int:
    return round((celsius * 9.0 / 5.0) + 32.0)


def _f_to_c(fahrenheit: float) -> int:
    return round((fahrenheit - 32.0) * 5.0 / 9.0)


class ACInfinityAutoTempNumber(ACInfinityNumber):
    """Base class for the two auto-mode temperature thresholds.

    The controller only stores a single whole-degree Celsius byte, but this
    unit is always Fahrenheit at the entity boundary; conversion happens
    here, not via HA's automatic unit conversion, so the UI shows real
    whole-Fahrenheit steps instead of unevenly-spaced converted Celsius
    steps. Some adjacent Fahrenheit values still round to the same
    underlying Celsius byte — that's a hardware precision limit, not
    something this conversion can remove.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_min_value = _c_to_f(0)
    _attr_native_max_value = _c_to_f(90)
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT


class AutoHighTempNumber(ACInfinityAutoTempNumber):
    """Auto-mode high-temperature threshold."""

    _attr_name = "Auto Mode High Temperature"
    _attr_icon = "mdi:thermometer-high"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.address}_auto_high_temp"
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        value = self._device.auto_high_temp
        self._attr_native_value = None if value is None else _c_to_f(value)

    async def async_set_native_value(self, value: float) -> None:
        await self._device.async_set_auto_high_temp(_f_to_c(value))


class AutoLowTempNumber(ACInfinityAutoTempNumber):
    """Auto-mode low-temperature threshold."""

    _attr_name = "Auto Mode Low Temperature"
    _attr_icon = "mdi:thermometer-low"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.address}_auto_low_temp"
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        value = self._device.auto_low_temp
        self._attr_native_value = None if value is None else _c_to_f(value)

    async def async_set_native_value(self, value: float) -> None:
        await self._device.async_set_auto_low_temp(_f_to_c(value))
