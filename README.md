# Egg Delivery Tracker — v0.1.6

A custom integration for **Home Assistant** that tracks your regular egg deliveries, extra deliveries, and one-off changes to your supplier's schedule. It provides a countdown, delivery calendar, delivery history, and automatic confirmation.

> **Version 0.1.6** includes the special-delivery date-field fix. It builds on the v0.1.5 configuration dropdown and the v0.1.2 special-delivery and exact-time confirmation features. This is an early release; it has not been fully tested in a running Home Assistant instance.

## Installation / updating

1. **Back up Home Assistant** before updating a custom integration.
2. Extract the ZIP and copy `HassEgg/custom_components/egg_delivery_tracker/` to `/config/custom_components/egg_delivery_tracker/`, replacing the existing files.
3. **Restart Home Assistant** and refresh your dashboard/browser.
4. Go to **Settings → Devices & services → Egg Delivery Tracker → Configure**.

**Do not delete or re-add your existing integration during an update.** The update is designed to retain the existing config entry, stored deliveries, history, and entity unique IDs. If entity IDs were previously renamed by Home Assistant, the names may remain different from the examples below.

## Configuration

The **Configure** screen starts with an **Action** dropdown. Choose an option and continue:

| Action | Purpose |
| --- | --- |
| **Regular schedule and confirmation** | Delivery weekday, interval in days (default **14**), anchor/next scheduled date, automatic confirmation toggle and local confirmation time (default **23:59**). |
| **Add an extra delivery** | Choose an extra delivery date, optional expected arrival time and description, and whether to skip automatic confirmation for that delivery. Regular deliveries remain unchanged. |
| **Replace a regular delivery** | Select the original regular delivery, choose its new date and optional arrival time, and optionally reset the recurring cycle. |
| **Remove a planned special delivery** | Remove a pending extra or replacement delivery. For a replacement, this restores its original regular date and undoes any cycle reset associated with it. |

### Additional vs replacement deliveries

Suppose your regular deliveries are **12 Nov, 26 Nov, 10 Dec**:

- **Additional delivery on 19 Nov:** 12 Nov, **19 Nov**, 26 Nov, 10 Dec.
- **Replace 26 Nov with 24 Nov; keep cycle:** 12 Nov, **24 Nov**, 10 Dec.
- **Replace 26 Nov with 24 Nov; reset cycle:** 12 Nov, **24 Nov**, 8 Dec, 22 Dec.

The optional **delivery time** is an *expected arrival time shown in the calendar*; it is **not** the automatic confirmation time. Calendar events with an arrival time last 30 minutes; deliveries without an arrival time are displayed as all-day events.

### Date fields in v0.1.6

The **Add an extra delivery** and **Replace a regular delivery** forms now explicitly default their new-date field to the current local date in `YYYY-MM-DD` format. This fixes the **“Could not parse date”** error triggered when the form appeared to display today's date without actually having a valid date value. You can still pick a different date using the date selector.

For replacement deliveries, choose the original regular delivery in the separate **Replaces date** dropdown as well.

## Automatic delivery confirmation

When enabled, the integration schedules confirmation at the configured **local time** (default 23:59) on a scheduled delivery date. The periodic coordinator refresh remains a fallback for delays/reloads. Manual confirmations, undo, and per-delivery skip-auto-confirmation remain supported. If Home Assistant was offline at the configured time, an unconfirmed delivery due **today** can be confirmed when it starts again; older days are not automatically backfilled.

After a delivery is confirmed, the next scheduled delivery and countdown should advance. Test this behavior with a temporary date/time first and restore your normal schedule afterward.

## Entities

The integration exposes these kinds of entities (actual IDs depend on the Home Assistant entity registry):

| Example entity ID | Meaning |
| --- | --- |
| `calendar.egg_deliveries` | Upcoming regular and special deliveries |
| `binary_sensor.egg_delivery_today` | Whether a delivery is scheduled for today |
| `sensor.egg_next_delivery` | Date of the next delivery |
| `sensor.egg_days_until_delivery` | Days remaining until the next delivery |
| `sensor.egg_last_delivery` | Most recently confirmed delivery |
| `sensor.egg_next_delivery_type` | Type of the next delivery |

## Actions / services

The integration provides these services for advanced use:

- `egg_delivery_tracker.log_delivery`
- `egg_delivery_tracker.add_special_delivery` — use `date` and `kind`; replacements also require `replaces_date`, and may specify `reset_cycle` and `delivery_time`
- `egg_delivery_tracker.remove_special_delivery` — use `delivery_id`
- `egg_delivery_tracker.undo_delivery` — use `delivery_id`
- `egg_delivery_tracker.skip_auto_confirmation` — use `delivery_id`
- `egg_delivery_tracker.set_next_delivery` — use `date`

For routine special deliveries, use **Configure** rather than manually entering service data. Scheduled normal delivery IDs have the form `normal-YYYY-MM-DD`.

## Optional Lovelace card

`HassEgg/www/egg-delivery-card.js` is an **experimental** separate frontend card. It is **not automatically registered as a HACS frontend card**. The integration itself works without the card; the standard sensors and calendar can be used in regular Home Assistant dashboards.

## Troubleshooting

**Configuration fields or menu options are blank**

- v0.1.5+ uses a labelled **Action dropdown** in place of the earlier four-row menu.
- Restart Home Assistant after copying new Python files and refresh your browser (hard refresh if necessary).
- Check that the complete integration directory was replaced and that the installed `manifest.json` version is `0.1.6`.

**“Could not parse date” on an extra or replacement delivery**

- v0.1.6 provides an explicit default date. Check that v0.1.6 is installed and Home Assistant was restarted.
- As a workaround, manually pick the date in the calendar field.

**Configuration form fails or integration does not load**

- Go to **Settings → System → Logs** and find the traceback mentioning `egg_delivery_tracker`.
- Include the traceback and your Home Assistant version when reporting a bug: <https://github.com/lowe493/HassEgg/issues>.

**Some entity IDs differ from the examples**

- Home Assistant preserves existing entity IDs. Inspect **Developer Tools → States** for your actual names rather than deleting the integration.

## Release notes

- **v0.1.6:** Set valid local-date defaults for the extra and replacement delivery forms, fixing “Could not parse date” if the user leaves today preselected.
- **v0.1.5:** Replace blank/translation-dependent option menu rows with a labelled Action dropdown.
- **v0.1.4:** Attempt explicit menu-row labels (superseded by the v0.1.5 dropdown).
- **v0.1.3:** Add `translations/en.json` and update Home Assistant selectors for regular settings and weekday selection.
- **v0.1.2:** Add additional and replacement deliveries, optional cycle reset, optional arrival time, removal of pending specials, and exact-time automatic confirmation with periodic fallback.

## Notes and limitations

- Designed for a single configuration entry on a Home Assistant instance.
- Only pending special deliveries can be removed directly. If already confirmed, undo their confirmation first.
- This project is an early custom integration. Python syntax/package checks alone do not guarantee runtime compatibility with every Home Assistant release.

Repository: <https://github.com/lowe493/HassEgg>
