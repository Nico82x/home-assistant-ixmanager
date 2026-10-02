"""iXmanager v0.1: cloud polling, read-only."""
from homeassistant.const import Platform, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import IxmanagerApi
from .coordinator import IxmanagerCoordinator

PLATFORMS = [Platform.SENSOR]

async def async_setup_entry(hass, entry):
    api = IxmanagerApi(async_get_clientsession(hass), hass.async_add_executor_job,
                       entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    coordinator = IxmanagerCoordinator(hass, entry, api)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await api.async_close()
        raise
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.api.async_close()
    return unloaded
