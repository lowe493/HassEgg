"""Initial setup and special-delivery management via Configure."""
from __future__ import annotations

from datetime import date
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


def _valid_date(value):
    date.fromisoformat(str(value))
    return str(value)


def _valid_clock(value):
    from datetime import time
    time.fromisoformat(str(value))
    return str(value)[:5]


class EggDeliveryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            user_input[CONF_DELIVERY_DAY] = DAY_OPTIONS[user_input[CONF_DELIVERY_DAY]]
            return self.async_create_entry(title="Egg Delivery Tracker", data=user_input)
        schema = vol.Schema({
            vol.Required(CONF_DELIVERY_DAY, default="Thursday"): selector.SelectSelector(selector.SelectSelectorConfig(options=list(DAY_OPTIONS), mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_INTERVAL, default=14): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            vol.Required(CONF_ANCHOR, default=dt_util.now().date().isoformat()): selector.DateSelector(),
            vol.Required(CONF_AUTO_CONFIRM, default=True): bool,
            vol.Required(CONF_AUTO_CONFIRM_TIME, default="23:59"): selector.TimeSelector(),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EggDeliveryOptionsFlow()


class EggDeliveryOptionsFlow(config_entries.OptionsFlow):
    """Menu-based management; special entries are saved in the existing Store."""

    def _coordinator(self):
        return self.hass.data[DOMAIN][self.config_entry.entry_id]

    def _complete(self):
        # Preserve options; no reload is needed for Store-only changes.
        return self.async_create_entry(data=dict(self.config_entry.options))

    async def async_step_init(self, user_input=None):
        """Use a labelled selector instead of a translation-dependent menu.

        Certain HA frontends render options-flow menu rows without their labels.
        A SelectSelector gives each option an explicit visible label.
        """
        choices = [
            {"value": "settings", "label": "Regular schedule and confirmation"},
            {"value": "additional", "label": "Add an extra delivery"},
            {"value": "replacement", "label": "Replace a regular delivery"},
            {"value": "remove_special", "label": "Remove a planned special delivery"},
        ]
        if user_input is not None:
            destination = user_input["action"]
            if destination == "settings":
                return await self.async_step_settings()
            if destination == "additional":
                return await self.async_step_additional()
            if destination == "replacement":
                return await self.async_step_replacement()
            if destination == "remove_special":
                return await self.async_step_remove_special()
        schema = vol.Schema({
            vol.Required("action"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=choices,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        })
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            user_input[CONF_DELIVERY_DAY] = DAY_OPTIONS[user_input[CONF_DELIVERY_DAY]]
            return self.async_create_entry(data={**self.config_entry.options, **user_input})
        current = {**DEFAULTS, **self.config_entry.data, **self.config_entry.options}
        day_name = next((k for k, v in DAY_OPTIONS.items() if v == current[CONF_DELIVERY_DAY]), "Thursday")
        schema = vol.Schema({
            vol.Required(CONF_DELIVERY_DAY, default=day_name): selector.SelectSelector(selector.SelectSelectorConfig(options=list(DAY_OPTIONS), mode=selector.SelectSelectorMode.DROPDOWN)),
            vol.Required(CONF_INTERVAL, default=current[CONF_INTERVAL]): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            vol.Required(CONF_ANCHOR, default=str(current[CONF_ANCHOR] or dt_util.now().date().isoformat())): selector.DateSelector(),
            vol.Required(CONF_AUTO_CONFIRM, default=current[CONF_AUTO_CONFIRM]): bool,
            vol.Required(CONF_AUTO_CONFIRM_TIME, default=str(current[CONF_AUTO_CONFIRM_TIME])[:5]): selector.TimeSelector(),
        })
        return self.async_show_form(step_id="settings", data_schema=schema)

    def _special_schema(self, replacement=False, originals=None):
        fields = {}
        if replacement:
            fields[vol.Required("replaces_date")] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=originals, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        fields[vol.Required("date")] = selector.DateSelector()
        fields[vol.Optional("delivery_time")] = selector.TimeSelector()
        fields[vol.Optional("description", default="Replacement egg delivery" if replacement else "Extra egg delivery")] = str
        fields[vol.Optional("skip_auto_confirmation", default=False)] = bool
        if replacement:
            fields[vol.Optional("reset_cycle", default=False)] = bool
        return vol.Schema(fields)

    async def async_step_additional(self, user_input=None):
        if user_input is not None:
            await self._coordinator().async_add_special(
                user_input["date"], user_input.get("description", "Extra egg delivery"),
                "additional", user_input.get("skip_auto_confirmation", False), False,
                delivery_time=user_input.get("delivery_time"),
            )
            return self._complete()
        return self.async_show_form(step_id="additional", data_schema=self._special_schema())

    async def async_step_replacement(self, user_input=None):
        coordinator = self._coordinator()
        today = dt_util.now().date()
        replaced = {
            item.get("replaces_date") for item in coordinator.deliveries
            if item.get("kind") == "replacement" and item.get("status") != "cancelled"
        }
        delivered = {
            item.get("date") for item in coordinator.deliveries
            if item.get("status") == "delivered"
        }
        originals = [
            {"value": due.isoformat(), "label": due.strftime("%a %d %b %Y")}
            for due in coordinator.normal_dates(today, 26)
            if due.isoformat() not in replaced and due.isoformat() not in delivered
        ]
        if not originals:
            return self.async_abort(reason="no_regular_deliveries")
        if user_input is not None:
            try:
                await coordinator.async_add_special(
                    user_input["date"], user_input.get("description", "Replacement egg delivery"),
                    "replacement", user_input.get("skip_auto_confirmation", False),
                    user_input.get("reset_cycle", False),
                    replaces_date=user_input["replaces_date"],
                    delivery_time=user_input.get("delivery_time"),
                )
            except ValueError:
                return self.async_show_form(step_id="replacement",
                                            data_schema=self._special_schema(True, originals),
                                            errors={"base": "invalid_replacement"})
            return self._complete()
        return self.async_show_form(step_id="replacement", data_schema=self._special_schema(True, originals))

    async def async_step_remove_special(self, user_input=None):
        coordinator = self._coordinator()
        specials = [item for item in coordinator.deliveries
                    if item.get("source") == "special" and item.get("status") == "pending"]
        if not specials:
            return self.async_abort(reason="no_special_deliveries")
        choices = [
            {"value": item["id"], "label": f"{item['date']} — {item.get('description', 'Special')} ({item['kind']})"}
            for item in sorted(specials, key=lambda i: i["date"])
        ]
        schema = vol.Schema({
            vol.Required("delivery_id"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=choices, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        })
        if user_input is not None:
            try:
                await coordinator.async_remove_special(user_input["delivery_id"])
            except ValueError:
                return self.async_show_form(step_id="remove_special", data_schema=schema,
                                            errors={"base": "invalid_special"})
            return self._complete()
        return self.async_show_form(step_id="remove_special", data_schema=schema)
