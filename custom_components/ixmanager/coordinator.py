"""One coordinated snapshot; no stale values after failed/offline updates."""
from datetime import timedelta
import logging
import time
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import ApiError, AuthError
from .const import DOMAIN, UPDATE_SECONDS, DISCOVERY_SECONDS

class IxmanagerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, api):
        super().__init__(hass, logging.getLogger(__name__), name=DOMAIN,
                         config_entry=entry, update_interval=timedelta(seconds=UPDATE_SECONDS))
        self.api = api
        self._device_ids = []
        self._discover_at = 0

    async def _async_update_data(self):
        try:
            ids = self._device_ids
            rediscover = time.monotonic() >= self._discover_at
            if rediscover:
                ids = await self.api.async_discover()
            data = {}
            for device_id in ids:
                data[device_id] = await self.api.async_device(device_id, initial=rediscover)
            # Commit discovery only after the complete snapshot succeeded.
            if rediscover:
                self._device_ids = ids
                self._discover_at = time.monotonic() + DISCOVERY_SECONDS
            return data
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from None
        except ApiError as err:
            raise UpdateFailed(str(err)) from None
