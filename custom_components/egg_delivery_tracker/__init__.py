from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, PLATFORMS, STORAGE_KEY, STORAGE_VERSION,
    SERVICE_LOG_DELIVERY, SERVICE_ADD_SPECIAL, SERVICE_UNDO_DELIVERY,
    SERVICE_SKIP_AUTO, SERVICE_SET_NEXT,
)
from .coordinator import EggDeliveryCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
    saved = await store.async_load() or {"deliveries": [], "last_auto_date": None}
    coordinator = EggDeliveryCoordinator(hass, entry, store, saved)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def log_delivery(call: ServiceCall) -> None:
        await coordinator.async_log_delivery(
            call.data.get("date"), call.data.get("note", ""), "manual"
        )

    async def add_special(call: ServiceCall) -> None:
        await coordinator.async_add_special(
            call.data["date"], call.data.get("description", "Special delivery"),
            call.data.get("kind", "additional"),
            call.data.get("skip_auto_confirmation", False),
            call.data.get("reset_cycle", False),
        )

    async def undo_delivery(call: ServiceCall) -> None:
        await coordinator.async_undo_delivery(call.data["delivery_id"])

    async def skip_auto(call: ServiceCall) -> None:
        await coordinator.async_skip_auto(call.data["delivery_id"])

    async def set_next(call: ServiceCall) -> None:
        await coordinator.async_set_next(call.data["date"])

    # Register services once, and route them to this integration's sole entry.
    if not hass.services.has_service(DOMAIN, SERVICE_LOG_DELIVERY):
        hass.services.async_register(DOMAIN, SERVICE_LOG_DELIVERY, log_delivery,
            schema=vol.Schema({vol.Optional("date"): cv.date, vol.Optional("note", default=""): cv.string}))
        hass.services.async_register(DOMAIN, SERVICE_ADD_SPECIAL, add_special,
            schema=vol.Schema({
                vol.Required("date"): cv.date,
                vol.Optional("description", default="Special delivery"): cv.string,
                vol.Optional("kind", default="additional"): vol.In(["additional", "replacement"]),
                vol.Optional("skip_auto_confirmation", default=False): cv.boolean,
                vol.Optional("reset_cycle", default=False): cv.boolean,
            }))
        hass.services.async_register(DOMAIN, SERVICE_UNDO_DELIVERY, undo_delivery,
            schema=vol.Schema({vol.Required("delivery_id"): cv.string}))
        hass.services.async_register(DOMAIN, SERVICE_SKIP_AUTO, skip_auto,
            schema=vol.Schema({vol.Required("delivery_id"): cv.string}))
        hass.services.async_register(DOMAIN, SERVICE_SET_NEXT, set_next,
            schema=vol.Schema({vol.Required("date"): cv.date}))
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
