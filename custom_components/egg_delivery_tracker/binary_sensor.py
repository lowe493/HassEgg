from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EggDeliveryToday(hass.data[DOMAIN][entry.entry_id])])

class EggDeliveryToday(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Delivery today"
    _attr_icon = "mdi:egg"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_delivery_today"
    @property
    def is_on(self):
        item = self.coordinator.next_delivery
        return bool(item and item["date"] == dt_util.now().date().isoformat())
