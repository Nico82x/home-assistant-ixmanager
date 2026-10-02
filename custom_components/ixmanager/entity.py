"""Shared entity base for sensors and future reviewed control platforms."""
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

class IxmanagerEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, device_id, parameter_key, desired=False):
        super().__init__(coordinator)
        self.device_id = device_id
        self.parameter_key = parameter_key
        self.desired = desired
        self._attr_unique_id = f"{device_id}:{parameter_key}:{'desired' if desired else 'value'}"
        device = coordinator.data[device_id]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)},
            name=device.name, manufacturer="Pool-Systems / iXmanager", model=device.model)

    @property
    def parameter(self):
        device = self.coordinator.data.get(self.device_id)
        return device.parameters.get(self.parameter_key) if device else None

    @property
    def available(self):
        device = self.coordinator.data.get(self.device_id)
        return bool(super().available and device and device.online and self.parameter)
