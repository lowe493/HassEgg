from __future__ import annotations

from datetime import date, datetime, time, timedelta
import uuid

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, UPDATE_INTERVAL, CONF_DELIVERY_DAY, CONF_INTERVAL, CONF_ANCHOR,
    CONF_AUTO_CONFIRM, CONF_AUTO_CONFIRM_TIME, DEFAULTS,
)

class EggDeliveryCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, store, saved):
        super().__init__(hass, None, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.entry = entry
        self.store = store
        self.saved = saved
        self.deliveries = saved.get("deliveries", [])
        self.last_auto_date = saved.get("last_auto_date")

    @property
    def settings(self):
        return {**DEFAULTS, **self.entry.data, **self.entry.options}

    def _anchor(self) -> date:
        raw = self.settings.get(CONF_ANCHOR)
        try:
            return date.fromisoformat(str(raw))
        except (TypeError, ValueError):
            return dt_util.now().date()

    def normal_dates(self, start: date, count: int = 12) -> list[date]:
        anchor = self._anchor()
        interval = int(self.settings[CONF_INTERVAL])
        # The anchor establishes the phase; weekday is validated as a convenience.
        if anchor.weekday() != self.settings[CONF_DELIVERY_DAY]:
            anchor += timedelta(days=(self.settings[CONF_DELIVERY_DAY] - anchor.weekday()) % 7)
        if start <= anchor:
            first = anchor
        else:
            steps = (start - anchor).days // interval
            first = anchor + timedelta(days=steps * interval)
            if first < start:
                first += timedelta(days=interval)
        return [first + timedelta(days=i * interval) for i in range(count)]

    def upcoming(self, count=12):
        today = dt_util.now().date()
        normals = self.normal_dates(today, count + 4)
        records = []
        replacement_dates = {
            item["replaces_date"] for item in self.deliveries
            if item.get("kind") == "replacement" and item.get("replaces_date")
        }
        delivered_dates = {
            item.get("date") for item in self.deliveries
            if item.get("status") == "delivered"
        }
        for due in normals:
            if due.isoformat() not in replacement_dates and due.isoformat() not in delivered_dates:
                records.append({
                    "id": f"normal-{due.isoformat()}",
                    "date": due.isoformat(),
                    "description": "Regular egg delivery",
                    "kind": "normal",
                    "status": "pending",
                    "skip_auto_confirmation": False,
                    "source": "schedule",
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
        target = delivery_date or dt_util.now().date()
        if isinstance(target, str):
            target = date.fromisoformat(target)
        existing = next((x for x in self.deliveries if x.get("date") == target.isoformat()
                         and x.get("status") == "delivered"), None)
        if existing:
            return
        record = next((x for x in self.upcoming(100) if x["date"] == target.isoformat()), None)
        if record and record["source"] != "schedule":
            stored = next((x for x in self.deliveries if x["id"] == record["id"]), None)
            if stored:
                stored.update(status="delivered", confirmed_by=source,
                              delivered_at=dt_util.now().isoformat(), note=note or stored.get("note", ""))
                await self._persist()
                self.async_set_updated_data({})
                return
        if record and record["kind"] == "normal":
            self.deliveries.append({
                "id": str(uuid.uuid4()), "date": target.isoformat(),
                "description": "Regular egg delivery", "kind": "normal",
                "status": "delivered", "skip_auto_confirmation": False,
                "source": "schedule", "confirmed_by": source,
                "delivered_at": dt_util.now().isoformat(), "note": note,
            })
        else:
            self.deliveries.append({
                "id": str(uuid.uuid4()), "date": target.isoformat(),
                "description": "Manual delivery", "kind": "additional",
                "status": "delivered", "skip_auto_confirmation": False,
                "source": "manual", "confirmed_by": source,
                "delivered_at": dt_util.now().isoformat(), "note": note,
            })
        await self._persist()
        self.async_set_updated_data({})

    async def async_add_special(self, due_date, description, kind, skip_auto, reset_cycle):
        if isinstance(due_date, str):
            due_date = date.fromisoformat(due_date)
        replaces = None
        if kind == "replacement":
            interval = int(self.settings[CONF_INTERVAL])
            candidates = [
                d for d in self.normal_dates(due_date - timedelta(days=interval), 30)
                if d >= dt_util.now().date()
            ]
            # Match the replacement to the scheduled occurrence nearest its new date.
            if candidates:
                replaces = min(candidates, key=lambda d: abs((d - due_date).days)).isoformat()
        item = {
            "id": str(uuid.uuid4()), "date": due_date.isoformat(),
            "description": description, "kind": kind, "status": "pending",
            "skip_auto_confirmation": bool(skip_auto), "source": "special",
            "replaces_date": replaces, "reset_cycle": bool(reset_cycle),
        }
        self.deliveries.append(item)
        if reset_cycle:
            new_data = dict(self.entry.data)
            new_data["anchor_date"] = due_date.isoformat()
            self.hass.config_entries.async_update_entry(self.entry, data=new_data)
        await self._persist()
        self.async_set_updated_data({})

    async def async_undo_delivery(self, delivery_id):
        item = next((x for x in self.deliveries if x["id"] == delivery_id), None)
        if item:
            item["status"] = "pending"
            item.pop("confirmed_by", None)
            item.pop("delivered_at", None)
            await self._persist()
            self.async_set_updated_data({})

    async def async_skip_auto(self, delivery_id):
        item = next((x for x in self.deliveries if x["id"] == delivery_id), None)
        if item:
            item["skip_auto_confirmation"] = True
            await self._persist()
            self.async_set_updated_data({})

    async def async_set_next(self, due_date):
        if isinstance(due_date, str):
            due_date = date.fromisoformat(due_date)
        new_data = dict(self.entry.data)
        new_data[CONF_ANCHOR] = due_date.isoformat()
        self.hass.config_entries.async_update_entry(self.entry, data=new_data)
        await self._persist()
        self.async_set_updated_data({})

    async def _async_update_data(self):
        now = dt_util.now()
        settings = self.settings
        if settings[CONF_AUTO_CONFIRM]:
            try:
                hour, minute = map(int, settings[CONF_AUTO_CONFIRM_TIME][:5].split(":"))
            except (ValueError, AttributeError):
                hour, minute = 23, 59
            cutoff = time(hour, minute)
            for item in self.upcoming(100):
                due = date.fromisoformat(item["date"])
                if due == now.date() and now.time().replace(tzinfo=None) >= cutoff:
                    if item.get("skip_auto_confirmation") or item["status"] != "pending":
                        continue
                    await self.async_log_delivery(due, "Automatically confirmed at configured time.", "automatic")
        return {"updated_at": now.isoformat()}
