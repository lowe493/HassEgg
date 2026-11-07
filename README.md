# Egg Delivery Tracker

A HACS custom integration for managing recurring and special egg deliveries in Home Assistant.

## Current starter release

This repository is an initial working scaffold. It includes:
- Configurable weekday, interval and anchor date.
- Automatic confirmation at a configurable local time (default 23:59).
- Special additional and replacement deliveries.
- Optional per-delivery auto-confirm skip.
- Manual log, undo and schedule services.
- Sensors, a binary sensor and a calendar entity.
- Persistent delivery data across restarts.

## Install through HACS (custom repository)

1. Copy this repository to a GitHub repository.
2. In HACS, open **Integrations → ⋮ → Custom repositories**.
3. Add the repository URL and choose **Integration**.
4. Install **Egg Delivery Tracker** and restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and search for Egg Delivery Tracker.

The Lovelace card is a separate frontend resource in `www/egg-delivery-card.js`. Copy it to `/config/www/egg-delivery-card.js`, add it as a JavaScript module resource (`/local/egg-delivery-card.js`), then add a manual card:

```yaml
type: custom:egg-delivery-card
entity: sensor.egg_delivery_tracker_next_delivery
```

## Services

- `egg_delivery_tracker.log_delivery`
- `egg_delivery_tracker.add_special_delivery`
- `egg_delivery_tracker.undo_delivery`
- `egg_delivery_tracker.skip_auto_confirmation`
- `egg_delivery_tracker.set_next_delivery`

For a replacement delivery, `reset_cycle: false` preserves the recurring cycle; `true` starts a new cycle from the special date.

## Notes

This is an early 0.1.0 implementation intended for testing in a non-critical Home Assistant instance. Review the limitations below before relying on it:

- The replacement workflow is intentionally conservative and should be tested against your supplier's exact rescheduling rules.
- Service IDs for normal scheduled deliveries are generated from their date (`normal-YYYY-MM-DD`); use special delivery IDs from entity/calendar data for per-delivery skip and undo actions.
- A production release should add automated tests, richer history management, translations, diagnostics, and a polished card editor.
- The frontend card is a lightweight first version, not yet distributed as a separate HACS Lovelace plugin.

## Development

Python integration code lives in `custom_components/egg_delivery_tracker/`.
