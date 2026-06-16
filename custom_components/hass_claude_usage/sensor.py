"""Sensor platform for Claude Usage integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from . import ClaudeUsageConfigEntry, ClaudeUsageCoordinator
from .const import (
    CODEX_SENSOR_DEFINITIONS,
    CONF_ACCOUNT_NAME,
    CONF_PROVIDER,
    CONF_SUBSCRIPTION_LEVEL,
    DOMAIN,
    PROVIDER_ANTIGRAVITY,
    PROVIDER_CLAUDE,
    PROVIDER_CODEX,
    SENSOR_DEFINITIONS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ClaudeUsageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for the configured provider."""
    coordinator = entry.runtime_data
    provider = entry.data.get(CONF_PROVIDER, PROVIDER_CLAUDE)

    if provider == PROVIDER_CODEX:
        async_add_entities(
            CodexUsageSensor(coordinator, entry, key, name, unit, icon, device_class)
            for key, name, unit, icon, device_class in CODEX_SENSOR_DEFINITIONS
        )

    elif provider == PROVIDER_ANTIGRAVITY:
        tracked: set[str] = set()

        def _make_model_sensors(models: dict[str, Any]) -> list[AntigravityModelSensor]:
            new_entities = []
            for model_id, model_data in models.items():
                if model_id not in tracked:
                    tracked.add(model_id)
                    label = model_data.get("label", model_id)
                    new_entities.append(
                        AntigravityModelSensor(coordinator, entry, model_id, label, "remaining_percent")
                    )
                    new_entities.append(
                        AntigravityModelSensor(coordinator, entry, model_id, label, "reset_at")
                    )
            return new_entities

        initial: list[SensorEntity] = [AntigravityApiErrorSensor(coordinator, entry)]
        initial.extend(_make_model_sensors(coordinator.data.get("models", {}) if coordinator.data else {}))
        async_add_entities(initial)

        @callback
        def _async_add_new_models() -> None:
            if coordinator.data is None:
                return
            new_entities = _make_model_sensors(coordinator.data.get("models", {}))
            if new_entities:
                async_add_entities(new_entities)

        entry.async_on_unload(coordinator.async_add_listener(_async_add_new_models))

    else:
        # Claude (default, preserves backward compatibility)
        async_add_entities(
            ClaudeUsageSensor(coordinator, entry, key, name, unit, icon, device_class)
            for key, name, unit, icon, device_class in SENSOR_DEFINITIONS
        )


class ClaudeUsageSensor(CoordinatorEntity[ClaudeUsageCoordinator], SensorEntity):
    """A sensor for a Claude usage metric."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ClaudeUsageCoordinator,
        entry: ClaudeUsageConfigEntry,
        key: str,
        name: str,
        unit: str | None,
        icon: str,
        device_class: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._is_timestamp = device_class == "timestamp"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        if self._is_timestamp:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif unit is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        account_name = entry.data.get(CONF_ACCOUNT_NAME)
        subscription_level = entry.data.get(CONF_SUBSCRIPTION_LEVEL)

        device_name_parts = ["Claude Usage"]
        if account_name:
            device_name_parts.append(f"({account_name}")
            if subscription_level:
                device_name_parts.append(f"- {subscription_level})")
            else:
                device_name_parts[-1] += ")"
        device_name = " ".join(device_name_parts)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Return True if the sensor value is present in coordinator data."""
        if self._key == "api_error":
            return True
        if not super().available:
            return False
        if self.coordinator.data is None:
            return False
        return self._key in self.coordinator.data

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self._key == "api_error":
            return 0 if self.coordinator.last_update_success else 1
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self._key)
        if value is not None and self._is_timestamp:
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid timestamp value for %s: %s", self._key, value)
                return None
        return value


class CodexUsageSensor(CoordinatorEntity[DataUpdateCoordinator[dict[str, Any]]], SensorEntity):
    """A sensor for a Codex usage metric."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ClaudeUsageConfigEntry,
        key: str,
        name: str,
        unit: str | None,
        icon: str,
        device_class: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._is_timestamp = device_class == "timestamp"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        if self._is_timestamp:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif unit is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Codex Usage (OpenAI)",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Return True if sensor data is available."""
        if self._key == "codex_api_error":
            return True
        if not super().available:
            return False
        if self.coordinator.data is None:
            return False
        return self._key in self.coordinator.data

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self._key == "codex_api_error":
            return 0 if self.coordinator.last_update_success else 1
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self._key)
        if value is not None and self._is_timestamp:
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid timestamp value for %s: %s", self._key, value)
                return None
        return value


class AntigravityModelSensor(
    CoordinatorEntity[DataUpdateCoordinator[dict[str, Any]]], SensorEntity
):
    """A sensor for a single Antigravity model quota metric."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ClaudeUsageConfigEntry,
        model_id: str,
        label: str,
        metric: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._model_id = model_id
        self._metric = metric  # "remaining_percent" or "reset_at"
        self._attr_unique_id = f"{entry.entry_id}_antigravity_{model_id}_{metric}"

        if metric == "remaining_percent":
            self._attr_name = f"{label} Remaining"
            self._attr_native_unit_of_measurement = "%"
            self._attr_icon = "mdi:gauge"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_name = f"{label} Reset Time"
            self._attr_icon = "mdi:timer-refresh"
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Antigravity Usage (Google)",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Return True if the model is present in coordinator data."""
        if not super().available:
            return False
        if self.coordinator.data is None:
            return False
        return self._model_id in self.coordinator.data.get("models", {})

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        model_data = self.coordinator.data.get("models", {}).get(self._model_id)
        if model_data is None:
            return None

        if self._metric == "remaining_percent":
            fraction = model_data.get("remaining_fraction")
            if fraction is None:
                return None
            return round(fraction * 100, 1)

        reset_time = model_data.get("reset_time")
        if reset_time is None:
            return None
        try:
            return datetime.fromisoformat(reset_time)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid reset_time for Antigravity model %s: %s", self._model_id, reset_time
            )
            return None


class AntigravityApiErrorSensor(
    CoordinatorEntity[DataUpdateCoordinator[dict[str, Any]]], SensorEntity
):
    """Sensor reporting 1 when the last Antigravity API fetch failed, 0 otherwise."""

    _attr_has_entity_name = True
    _attr_name = "API Error"
    _attr_native_unit_of_measurement = "errors"
    _attr_icon = "mdi:alert-circle"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ClaudeUsageConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_antigravity_api_error"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Antigravity Usage (Google)",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Always available — reports error state."""
        return True

    @property
    def native_value(self) -> int:
        """Return 0 if last update succeeded, 1 if it failed."""
        return 0 if self.coordinator.last_update_success else 1
