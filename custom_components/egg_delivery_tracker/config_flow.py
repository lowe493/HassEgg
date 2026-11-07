from datetime import date, datetime, time
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, CONF_DELIVERY_DAY, CONF_INTERVAL, CONF_ANCHOR,
    CONF_AUTO_CONFIRM, CONF_AUTO_CONFIRM_TIME, DEFAULTS,
)

DAY_OPTIONS = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}

class EggDeliveryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            user_input[CONF_DELIVERY_DAY] = DAY_OPTIONS[user_input[CONF_DELIVERY_DAY]]
            return self.async_create_entry(title="Egg Delivery Tracker", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_DELIVERY_DAY, default=3): vol.In(DAY_OPTIONS),
            vol.Required(CONF_INTERVAL, default=14): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            vol.Required(CONF_ANCHOR, default=dt_util.now().date().isoformat()): str,
            vol.Required(CONF_AUTO_CONFIRM, default=True): bool,
            vol.Required(CONF_AUTO_CONFIRM_TIME, default="23:59"): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EggDeliveryOptionsFlow(config_entry)

class EggDeliveryOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            user_input[CONF_DELIVERY_DAY] = DAY_OPTIONS[user_input[CONF_DELIVERY_DAY]]
            return self.async_create_entry(title="", data=user_input)
        current = {**DEFAULTS, **self.config_entry.data, **self.config_entry.options}
        day_name = next((k for k, v in DAY_OPTIONS.items() if v == current[CONF_DELIVERY_DAY]), "Thursday")
        schema = vol.Schema({
            vol.Required(CONF_DELIVERY_DAY, default=day_name): vol.In(DAY_OPTIONS),
            vol.Required(CONF_INTERVAL, default=current[CONF_INTERVAL]): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            vol.Required(CONF_ANCHOR, default=str(current[CONF_ANCHOR] or dt_util.now().date().isoformat())): str,
            vol.Required(CONF_AUTO_CONFIRM, default=current[CONF_AUTO_CONFIRM]): bool,
            vol.Required(CONF_AUTO_CONFIRM_TIME, default=current[CONF_AUTO_CONFIRM_TIME][:5]): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_init_submit(self, user_input=None):
        if user_input is not None:
            user_input[CONF_DELIVERY_DAY] = DAY_OPTIONS[user_input[CONF_DELIVERY_DAY]]
            return self.async_create_entry(title="", data=user_input)
        return await self.async_step_init()
