from datetime import datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EggDeliveryCalendar(hass.data[DOMAIN][entry.entry_id])])

class EggDeliveryCalendar(CoordinatorEntity, CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "Deliveries"
    _attr_icon = "mdi:calendar"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_calendar"
    @property
    def event(self):
        return self._event
    async def async_get_events(self, hass, start_date, end_date):
        events = []
        for item in self.coordinator.upcoming(100):
            start = datetime.combine(datetime.fromisoformat(item["date"]).date(), datetime.min.time())
            if start_date <= start <= end_date:
                events.append(CalendarEvent(
                    start=start, end=start + timedelta(days=1),
                    summary=item.get("description", "Egg delivery"),
                    description=f'{item.get("kind", "normal").title()} delivery · {item.get("status", "pending")}',
                ))
        return events
