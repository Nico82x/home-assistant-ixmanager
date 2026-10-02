"""Pure metadata/value adapter shared with future entity platforms."""
from dataclasses import dataclass
import math

class SchemaError(Exception):
    """Unexpected API structure; do not silently misassign values."""

@dataclass(frozen=True)
class Parameter:
    group: str
    name: str
    label: str
    kind: str
    value: object
    desired: object
    options: dict
    settable: bool
    show_desired: bool

    @property
    def key(self):
        return f"{self.group}:{self.name}"

    @property
    def future_platform(self):
        """Only a type hint, never authorization to expose a control."""
        return {"NUMBER": "number", "ENUM": "select", "TOGGLE": "switch"}.get(self.kind)

    def state(self, desired=False):
        value = self.desired if desired else self.value
        if value is None or value == "":
            return None
        if self.kind == "NUMBER":
            try:
                number = float(value)
                return number if math.isfinite(number) else None
            except (ValueError, TypeError):
                return None
        if self.kind == "TOGGLE":
            if value in (True, "true"):
                return "on"
            if value in (False, "false"):
                return "off"
            return None
        return str(value)[:255]

@dataclass(frozen=True)
class Device:
    id: str
    name: str
    model: str
    online: bool
    parameters: dict[str, Parameter]


def parse_device(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
        raise SchemaError("Missing device ID")
    live = raw.get("liveDeviceData")
    if not isinstance(live, dict):
        raise SchemaError("Missing liveDeviceData")
    parameters = {}
    for group in ("operatingValues", "controls"):
        rows = live.get(group)
        if not isinstance(rows, list):
            raise SchemaError("Missing parameter list")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                raise SchemaError("Parameter without name")
            if row.get("type") not in ("NUMBER", "ENUM", "TOGGLE", "TEXT", "STRING"):
                continue
            # Service/action controls (including protectionReset) are excluded.
            # Only operating values become sensors in this release.
            if group != "operatingValues":
                continue
            options = row.get("options") or {}
            if not isinstance(options, dict):
                raise SchemaError("Invalid parameter options")
            p = Parameter(group, row["name"], row.get("label") or row["name"],
                          row["type"], row.get("value"), row.get("desiredValue"),
                          options, row.get("settable") is True,
                          row.get("showDesired") is True)
            if p.key in parameters:
                raise SchemaError("Duplicate parameter name")
            parameters[p.key] = p
    thing = raw.get("thingType") or {}
    return Device(raw["id"], raw.get("name") or "iXmanager",
                  thing.get("businessName") or thing.get("name") or "Pool controller",
                  raw.get("connectionStatus") == "ONLINE", parameters)
