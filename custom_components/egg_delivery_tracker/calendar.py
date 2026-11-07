"""Upcoming egg deliveries shown on the Home Assistant calendar."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

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
        arrival = item.get("delivery_time")
        if arrival:
            delivery_time = time.fromisoformat(arrival)
            start = datetime.combine(due, delivery_time, tzinfo=dt_util.get_default_time_zone())
            end = start + timedelta(minutes=30)
        else:
            start, end = due, due + timedelta(days=1)
        return CalendarEvent(
            start=start,
            end=end,
            summary=item.get("description", "Egg delivery"),
            description=f"{item.get('kind', 'normal').title()} delivery · {item.get('status', 'pending')}",
        )

    @property
    def event(self):
        item = self.coordinator.next_delivery
        return self._make_event(item) if item else None

    async def async_get_events(self, hass, start_date, end_date):
        events = []
        for item in self.coordinator.upcoming(200):
            event = self._make_event(item)
            # Calendar query bounds are timezone-aware datetimes; convert timed
            # events to this timezone, all-day events to date bounds.
            if isinstance(event.start, datetime):
                if event.end > start_date and event.start < end_date:
                    events.append(event)
            elif event.end > start_date.date() and event.start < end_date.date():
                events.append(event)
        return events
