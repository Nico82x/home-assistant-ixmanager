"""UI setup and credential renewal; no YAML or hardcoded device identifiers."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import ApiError, AuthError, IxmanagerApi, NoDevicesError
from .const import DOMAIN

class IxmanagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        return await self._credentials("user", user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._credentials("reauth_confirm", user_input)

    async def _credentials(self, step, user_input):
        errors = {}
        if user_input is not None:
            user_input = dict(user_input)
            user_input[CONF_USERNAME] = user_input[CONF_USERNAME].strip()
            api = IxmanagerApi(async_get_clientsession(self.hass),
                self.hass.async_add_executor_job,
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            try:
                try:
                    devices = await api.async_discover()
                    # Validate metadata before saving credentials.
                    for device_id in devices:
                        await api.async_device(device_id, initial=True)
                finally:
                    await api.async_close()
            except AuthError:
                errors["base"] = "invalid_auth"
            except NoDevicesError:
                errors["base"] = "no_devices"
            except ApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(api.account_id)
                if step == "reauth_confirm":
                    entry = self._get_reauth_entry()
                    if entry.unique_id != api.account_id:
                        return self.async_abort(reason="wrong_account")
                    return self.async_update_reload_and_abort(entry, data_updates=user_input)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="iXmanager", data=user_input)
        username = ""
        if step == "reauth_confirm":
            username = self._get_reauth_entry().data[CONF_USERNAME]
        return self.async_show_form(step_id=step, data_schema=vol.Schema({
            vol.Required(CONF_USERNAME, default=username): str,
            vol.Required(CONF_PASSWORD): str,
        }), errors=errors)
