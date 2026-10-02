"""Metadata-driven current values and optional read-only desired values."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import callback
from .entity import IxmanagerEntity

UNITS = {"TEMP_CELSIUS": "°C", "PERCENT": "%", "LITER": "L"}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    known = set()

    @callback
    def add_entities():
        entities = []
        for device in (coordinator.data or {}).values():
            for p in device.parameters.values():
                for desired in (False, True) if p.show_desired else (False,):
                    key = (device.id, p.key, desired)
                    if key not in known:
                        known.add(key)
                        entities.append(IxmanagerSensor(coordinator, *key))
        if entities:
            async_add_entities(entities)

    add_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_entities))

class IxmanagerSensor(IxmanagerEntity, SensorEntity):
    def __init__(self, coordinator, device_id, parameter_key, desired=False):
        super().__init__(coordinator, device_id, parameter_key, desired)
        if desired:
            self._attr_entity_registry_enabled_default = False

    @property
    def name(self):
        p = self.parameter
        return (p.label if p else self.parameter_key) + (" Sollwert" if self.desired else "")

    @property
    def native_value(self):
        p = self.parameter
        return p.state(self.desired) if p else None

    @property
    def native_unit_of_measurement(self):
        p = self.parameter
        if not p or p.kind != "NUMBER":
            return None
        return UNITS.get(p.options.get("unit"))

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE if self.native_unit_of_measurement == "°C" else None

    @property
    def state_class(self):
        p = self.parameter
        return SensorStateClass.MEASUREMENT if p and p.kind == "NUMBER" and not self.desired else None

    @property
    def suggested_display_precision(self):
        p = self.parameter
        digits = p.options.get("digits") if p else None
        return digits if type(digits) is int and 0 <= digits <= 6 else None

    @property
    def extra_state_attributes(self):
        p = self.parameter
        if not p:
            return {}
        attrs = {"parameter": p.name, "api_type": p.kind}
        if p.kind == "ENUM":
            values = p.options.get("values", [])
            attrs["value_labels"] = {str(v["value"]): v.get("label", str(v["value"]))
                                     for v in values if isinstance(v, dict) and "value" in v}
        return attrs
