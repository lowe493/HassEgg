from datetime import date
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_INTERVAL

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        EggNextDelivery(coordinator), EggDaysRemaining(coordinator),
        EggLastDelivery(coordinator), EggDeliveryType(coordinator),
    ])

class EggBase(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, suffix):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{suffix}"

class EggNextDelivery(EggBase):
    _attr_name = "Next delivery"
    _attr_icon = "mdi:egg"
    @property
    def native_value(self):
        item = self.coordinator.next_delivery
        return item["date"] if item else None
    @property
    def extra_state_attributes(self):
        item = self.coordinator.next_delivery
        return item or {}

class EggDaysRemaining(EggBase):
    _attr_name = "Days until delivery"
    _attr_native_unit_of_measurement = "days"
    _attr_icon = "mdi:calendar-clock"
    def __init__(self, coordinator):
        super().__init__(coordinator, "days_until")
        self._attr_native_value = None
    @property
    def native_value(self):
        item = self.coordinator.next_delivery
        return (date.fromisoformat(item["date"]) - dt_util.now().date()).days if item else None

class EggLastDelivery(EggBase):
    _attr_name = "Last delivery"
    _attr_icon = "mdi:calendar-check"
    def __init__(self, coordinator):
        super().__init__(coordinator, "last_delivery")
    @property
    def native_value(self):
        delivered = [x for x in self.coordinator.deliveries if x.get("status") == "delivered"]
        delivered.sort(key=lambda x: x.get("date", ""), reverse=True)
        return delivered[0]["date"] if delivered else None

class EggDeliveryType(EggBase):
    _attr_name = "Next delivery type"
    _attr_icon = "mdi:tag"
    def __init__(self, coordinator):
        super().__init__(coordinator, "delivery_type")
    @property
    def native_value(self):
        item = self.coordinator.next_delivery
        return item.get("kind") if item else None
