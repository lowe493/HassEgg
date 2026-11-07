"""Upcoming egg delivery dates as an all-day calendar."""
from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EggDeliveryCalendar(hass.data[DOMAIN][entry.entry_id])])


class EggDeliveryCalendar(CoordinatorEntity, CalendarEntity):
    _attr_has_entity_name = False
    _attr_name = "Egg deliveries"
    _attr_icon = "mdi:calendar"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_calendar"

    @staticmethod
    def _make_event(item):
        due = date.fromisoformat(item["date"])
        return CalendarEvent(
            start=due,
            end=due + timedelta(days=1),
            summary=item.get("description", "Egg delivery"),
            description=f"{item.get('kind', 'normal').title()} delivery · {item.get('status', 'pending')}",
        )

    @property
    def event(self):
        item = self.coordinator.next_delivery
        return self._make_event(item) if item else None

    async def async_get_events(self, hass, start_date, end_date):
        # An all-day CalendarEvent must have date values (not naive datetimes).
        # An event overlaps when its end is after the lower bound and its
        # start is before the upper bound.
        return [
            event
            for item in self.coordinator.upcoming(100)
            if (event := self._make_event(item)).end > start_date.date()
            and event.start < end_date.date()
        ]
