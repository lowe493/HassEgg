"""Delivery schedule, persisted exceptions and exact-time auto-confirmation."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
import logging
import uuid

from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, UPDATE_INTERVAL, CONF_DELIVERY_DAY, CONF_INTERVAL, CONF_ANCHOR,
    CONF_AUTO_CONFIRM, CONF_AUTO_CONFIRM_TIME, DEFAULTS,
)

_LOGGER = logging.getLogger(__name__)


def _date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _clock(value, default="23:59"):
    try:
        return time.fromisoformat(str(value or default))
    except (TypeError, ValueError):
        return time.fromisoformat(default)


class EggDeliveryCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, store, saved):
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.entry = entry
        self.store = store
        self.deliveries = list(saved.get("deliveries", []))
        self.last_auto_date = saved.get("last_auto_date")
        self._timer_cancel = None

    @property
    def settings(self):
        return {**DEFAULTS, **self.entry.data, **self.entry.options}

    def _anchor(self):
        raw = self.settings.get(CONF_ANCHOR)
        try:
            anchor = _date(raw)
        except (TypeError, ValueError):
            anchor = dt_util.now().date()
        weekday = int(self.settings[CONF_DELIVERY_DAY])
        if anchor.weekday() != weekday:
            anchor += timedelta(days=(weekday - anchor.weekday()) % 7)
        return anchor

    @staticmethod
    def _dates_in_segment(anchor, lower, upper, interval, count):
        """Return dates in [lower, upper) on an anchor's recurring phase."""
        first = max(anchor, lower)
        n = max(0, (first - anchor).days // interval)
        candidate = anchor + timedelta(days=n * interval)
        if candidate < first:
            candidate += timedelta(days=interval)
        dates = []
        while len(dates) < count and (upper is None or candidate < upper):
            dates.append(candidate)
            candidate += timedelta(days=interval)
        return dates

    def normal_dates(self, start: date, count: int = 12) -> list[date]:
        """Regular deliveries, with optional cycle resets at replacement dates."""
        interval = max(1, int(self.settings[CONF_INTERVAL]))
        # Reset applies from the replacement's NEW date onwards. Previous
        # regular occurrences are preserved, even if reset was planned ahead.
        resets = sorted({
            _date(item["date"])
            for item in self.deliveries
            if item.get("kind") == "replacement" and item.get("reset_cycle")
            and item.get("status") != "cancelled"
        })
        anchor = self._anchor()
        lower = start
        result = []
        for reset in resets + [None]:
            if reset is not None and reset <= lower:
                anchor = reset
                continue
            result.extend(self._dates_in_segment(anchor, lower, reset, interval, count))
            if reset is None:
                break
            lower = reset
            anchor = reset
        return sorted(set(result))[:count]

    def upcoming(self, count=12):
        today = dt_util.now().date()
        records = []
        replaced_dates = {
            item.get("replaces_date") for item in self.deliveries
            if item.get("kind") == "replacement" and item.get("status") != "cancelled"
        }
        replacement_new_dates = {
            item.get("date") for item in self.deliveries
            if item.get("kind") == "replacement" and item.get("status") != "cancelled"
        }
        # Stored records replace synthetic normal occurrences of the same date.
        stored_normal_dates = {
            item["date"] for item in self.deliveries
            if item.get("kind") == "normal" and item.get("status") != "cancelled"
        }
        for due in self.normal_dates(today, count + len(self.deliveries) + 20):
            stamp = due.isoformat()
            if stamp in replaced_dates or stamp in stored_normal_dates or stamp in replacement_new_dates:
                continue
            records.append({
                "id": f"normal-{stamp}", "date": stamp,
                "description": "Regular egg delivery", "kind": "normal",
                "status": "pending", "source": "schedule",
                "skip_auto_confirmation": False,
            })
        records.extend(
            item for item in self.deliveries
            if item.get("status") == "pending" and item.get("date", "") >= today.isoformat()
        )
        records.sort(key=lambda item: (item["date"], item["id"]))
        return records[:count]

    @property
    def next_delivery(self):
        items = self.upcoming(1)
        return items[0] if items else None

    async def _persist(self):
        await self.store.async_save({
            "deliveries": self.deliveries,
            "last_auto_date": self.last_auto_date,
        })

    async def async_log_delivery(self, delivery_date=None, note="", source="manual", delivery_id=None):
        target = _date(delivery_date or dt_util.now().date())
        candidates = [item for item in self.upcoming(200) if item["date"] == target.isoformat()]
        record = next((item for item in candidates if item["id"] == delivery_id), None) if delivery_id else None
        if record is None and delivery_id is None:
            record = next(iter(candidates), None)
        if delivery_id and record is None:
            return False
        # Avoid double-recording a particular delivery; support multiple distinct
        # deliveries on a day if the user explicitly schedules them.
        if record and any(item.get("id") == record["id"] and item.get("status") == "delivered"
                          for item in self.deliveries):
            return False
        if record and record.get("source") == "special":
            stored = next((item for item in self.deliveries if item["id"] == record["id"]), None)
            if stored is None or stored["status"] != "pending":
                return False
            stored.update(status="delivered", confirmed_by=source,
                          delivered_at=dt_util.now().isoformat(), note=note or stored.get("note", ""))
        else:
            if record is None and any(item.get("date") == target.isoformat() and item.get("status") == "delivered"
                                      for item in self.deliveries):
                return False
            # The synthetic scheduled ID is stable, so undoing does not create duplicates.
            identifier = record["id"] if record else str(uuid.uuid4())
            stored = next((item for item in self.deliveries if item["id"] == identifier), None)
            if stored:
                stored.update(status="delivered", confirmed_by=source,
                              delivered_at=dt_util.now().isoformat(), note=note)
            else:
                self.deliveries.append({
                    "id": identifier, "date": target.isoformat(),
                    "description": record["description"] if record else "Manual delivery",
                    "kind": "normal" if record else "additional",
                    "status": "delivered", "source": "schedule" if record else "manual",
                    "skip_auto_confirmation": False, "confirmed_by": source,
                    "delivered_at": dt_util.now().isoformat(), "note": note,
                })
        if source == "automatic":
            self.last_auto_date = target.isoformat()
        await self._persist()
        self.async_set_updated_data({})
        self._reschedule_timer()
        return True

    async def async_add_special(self, due_date, description="Special delivery", kind="additional",
                                skip_auto=False, reset_cycle=False, replaces_date=None,
                                delivery_time=None):
        due = _date(due_date)
        if kind not in ("additional", "replacement"):
            raise ValueError("Unknown special-delivery type")
        if kind == "replacement":
            if replaces_date is None:
                raise ValueError("Select the regular delivery date to replace")
            original = _date(replaces_date)
            if original not in self.normal_dates(min(original, dt_util.now().date()), 200):
                raise ValueError("Replacement must reference a regular delivery")
            if any(item.get("kind") == "replacement" and item.get("status") != "cancelled"
                   and item.get("replaces_date") == original.isoformat() for item in self.deliveries):
                raise ValueError("That regular delivery has already been replaced")
            if any(item.get("date") == original.isoformat() and item.get("status") == "delivered"
                   for item in self.deliveries):
                raise ValueError("A confirmed delivery cannot be replaced")
        else:
            original = None
            reset_cycle = False
        if delivery_time:
            delivery_time = _clock(delivery_time, "00:00").strftime("%H:%M")
        item = {
            "id": str(uuid.uuid4()), "date": due.isoformat(),
            "description": description or "Special delivery", "kind": kind,
            "status": "pending", "skip_auto_confirmation": bool(skip_auto),
            "source": "special", "replaces_date": original.isoformat() if original else None,
            "reset_cycle": bool(reset_cycle), "delivery_time": delivery_time or None,
        }
        self.deliveries.append(item)
        await self._persist()
        self.async_set_updated_data({})
        self._reschedule_timer()
        return item

    async def async_remove_special(self, delivery_id):
        item = next((x for x in self.deliveries if x.get("id") == delivery_id), None)
        if item is None or item.get("source") != "special":
            raise ValueError("Special delivery not found")
        if item.get("status") == "delivered":
            raise ValueError("Undo its confirmation before removing it")
        self.deliveries.remove(item)
        await self._persist()
        self.async_set_updated_data({})
        self._reschedule_timer()

    async def async_undo_delivery(self, delivery_id):
        item = next((x for x in self.deliveries if x.get("id") == delivery_id), None)
        if item is None or item.get("status") != "delivered":
            raise ValueError("Confirmed delivery not found")
        item["status"] = "pending"
        item.pop("confirmed_by", None)
        item.pop("delivered_at", None)
        await self._persist()
        self.async_set_updated_data({})
        self._reschedule_timer()

    async def async_skip_auto(self, delivery_id):
        item = next((x for x in self.deliveries if x.get("id") == delivery_id), None)
        if item is None and delivery_id.startswith("normal-"):
            due = _date(delivery_id.removeprefix("normal-"))
            if due not in self.normal_dates(min(due, dt_util.now().date()), 200):
                raise ValueError("Regular delivery not found")
            item = {"id": delivery_id, "date": due.isoformat(), "kind": "normal",
                    "description": "Regular egg delivery", "status": "pending",
                    "source": "schedule"}
            self.deliveries.append(item)
        if item is None:
            raise ValueError("Delivery not found")
        item["skip_auto_confirmation"] = True
        await self._persist()
        self.async_set_updated_data({})
        self._reschedule_timer()

    async def async_set_next(self, due_date):
        due = _date(due_date)
        new_options = dict(self.entry.options)
        new_options[CONF_ANCHOR] = due.isoformat()
        new_options[CONF_DELIVERY_DAY] = due.weekday()
        self.hass.config_entries.async_update_entry(self.entry, options=new_options)
        self.async_set_updated_data({})
        self._reschedule_timer()

    async def _async_update_data(self):
        # Polling is a safety net for restarts and missed event callbacks; the
        # scheduled callback normally confirms at the exact configured time.
        await self.async_process_due()
        return {"updated_at": dt_util.now().isoformat()}

    async def async_process_due(self):
        now = dt_util.now()
        if self.settings[CONF_AUTO_CONFIRM]:
            cutoff = _clock(self.settings[CONF_AUTO_CONFIRM_TIME])
            if now.time().replace(tzinfo=None) >= cutoff:
                for item in list(self.upcoming(200)):
                    if item["date"] == now.date().isoformat() and not item.get("skip_auto_confirmation"):
                        await self.async_log_delivery(
                            now.date(), "Automatically confirmed at configured time.",
                            "automatic", item["id"]
                        )
        self._reschedule_timer()

    def _reschedule_timer(self):
        if self._timer_cancel:
            self._timer_cancel()
            self._timer_cancel = None
        if not self.settings[CONF_AUTO_CONFIRM]:
            return
        now = dt_util.now()
        cutoff = _clock(self.settings[CONF_AUTO_CONFIRM_TIME])
        for item in self.upcoming(200):
            if item.get("skip_auto_confirmation"):
                continue
            due = _date(item["date"])
            scheduled = dt_util.as_local(datetime.combine(due, cutoff, tzinfo=dt_util.get_default_time_zone()))
            if scheduled > now:
                self._timer_cancel = async_track_point_in_time(self.hass, self._timer_fired, scheduled)
                return
        # No upcoming delivery in the current search horizon.

    def _timer_fired(self, now):
        self._timer_cancel = None
        self.hass.async_create_task(self.async_process_due())

    async def async_start_scheduler(self):
        await self.async_process_due()

    def async_stop_scheduler(self):
        if self._timer_cancel:
            self._timer_cancel()
            self._timer_cancel = None
