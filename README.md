# Egg Delivery Tracker v0.1.2

Home Assistant custom integration for recurring egg deliveries, one-off deliveries and supplier date changes.

## Install/update without losing your configuration

1. Make a Home Assistant backup before updating custom integrations.
2. Extract this ZIP. Copy **`HassEgg/custom_components/egg_delivery_tracker`** over your existing **`/config/custom_components/egg_delivery_tracker`** directory.
3. Restart Home Assistant. **Do not delete or re-add the existing integration**: your config entry and stored delivery history are retained.
4. Go to **Settings → Devices & services → Egg Delivery Tracker → Configure**.

> This update has passed Python compilation and local schedule simulations but has not been tested inside a running Home Assistant instance. Please verify the new options screen and scheduler after installation.

## Configure menu

- **Regular schedule and confirmation**: weekday, interval (14 days by default), anchor date and exact-time automatic confirmation (23:59 by default).
- **Add an extra delivery**: select an extra date, optional expected arrival time and description. This does not move your regular dates.
- **Replace a regular delivery**: select the **original** delivery from a list, then set its replacement date and optional arrival time. With **Reset fortnightly cycle** turned off, later regular dates stay unchanged. With it on, subsequent normal deliveries repeat at the interval starting on the new date. Regular deliveries *before* the replacement remain unchanged.
- **Remove a planned special delivery**: deletes an unconfirmed extra or replacement. Removing a replacement restores the original delivery and removes any cycle reset from that replacement.

Example regular dates: 12 Nov, 26 Nov, 10 Dec.
- **Extra on 19 Nov** → 12 Nov, **19 Nov**, 26 Nov, 10 Dec.
- **Replace 26 Nov with 24 Nov, keep cycle** → 12 Nov, **24 Nov**, 10 Dec.
- **Replace 26 Nov with 24 Nov, reset cycle** → 12 Nov, **24 Nov**, 8 Dec, 22 Dec.

**Arrival time** is optional calendar information only. It does not alter the automatic **confirmation time**, which is configured under Regular schedule and confirmation. A calendar event with an arrival time is shown as a 30-minute event; otherwise it is all-day.

## Automatic confirmations

Home Assistant schedules a callback for the configured local confirmation time, instead of waiting for the five-minute coordinator check. The existing periodic update remains a fallback for unexpected scheduling delays and reloads. Manual confirmation, undo and per-delivery skip remain available. If Home Assistant was offline when the configured time passed, an unconfirmed delivery due **today** is automatically confirmed when Home Assistant starts again; past days are not automatically backfilled.

## Home Assistant entities

- `calendar.egg_deliveries`
- `binary_sensor.egg_delivery_today`
- `sensor.egg_next_delivery`
- `sensor.egg_days_until_delivery`
- `sensor.egg_last_delivery`
- `sensor.egg_next_delivery_type`

The actual IDs may differ if Home Assistant kept IDs previously assigned to the entities. The unique IDs have not changed.

## Services/actions

- `egg_delivery_tracker.log_delivery`
- `egg_delivery_tracker.add_special_delivery` — `date` and `kind`; when `kind: replacement`, supply `replaces_date`, and optionally `reset_cycle` and `delivery_time`
- `egg_delivery_tracker.remove_special_delivery` — `delivery_id`
- `egg_delivery_tracker.undo_delivery` — `delivery_id`
- `egg_delivery_tracker.skip_auto_confirmation` — `delivery_id`
- `egg_delivery_tracker.set_next_delivery` — `date`

For routine extra/replacement deliveries, use the **Configure** menu instead of writing service data. Scheduled regular delivery IDs use `normal-YYYY-MM-DD`.

## Important notes

- One Home Assistant instance/config entry is supported by this release.
- Removing a special delivery is only possible while it is pending; undo confirmation first if necessary.
- The frontend `www/egg-delivery-card.js` is a separate experimental Lovelace card, not automatically installed as a HACS frontend card.
- This is an early custom integration; please test it with your real schedule and check Home Assistant logs.

## v0.1.3: Configuration UI fix

- Adds `custom_components/egg_delivery_tracker/translations/en.json` so Home Assistant renders options menu and form labels.
- Uses Home Assistant date/time selectors in initial setup and regular settings rather than custom callable validators.
- Changes weekday selection to a dropdown selector.
- Does not modify the existing delivery Store data or entity unique IDs.

If the configuration menu is still blank after a full Home Assistant restart, refresh the browser cache. If any option errors, inspect Settings > System > Logs and capture the Python traceback.
