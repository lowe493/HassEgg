from datetime import timedelta

DOMAIN = "egg_delivery_tracker"
PLATFORMS = ["sensor", "binary_sensor", "calendar"]
CONF_DELIVERY_DAY = "delivery_day"
CONF_INTERVAL = "interval_days"
CONF_ANCHOR = "anchor_date"
CONF_AUTO_CONFIRM = "auto_confirm"
CONF_AUTO_CONFIRM_TIME = "auto_confirm_time"
DEFAULTS = {
    CONF_DELIVERY_DAY: 3,  # Thursday; Python weekday: Monday=0
    CONF_INTERVAL: 14,
    CONF_ANCHOR: None,
    CONF_AUTO_CONFIRM: True,
    CONF_AUTO_CONFIRM_TIME: "23:59:00",
}
UPDATE_INTERVAL = timedelta(minutes=5)
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_data"
SERVICE_LOG_DELIVERY = "log_delivery"
SERVICE_ADD_SPECIAL = "add_special_delivery"
SERVICE_UNDO_DELIVERY = "undo_delivery"
SERVICE_SKIP_AUTO = "skip_auto_confirmation"
SERVICE_SET_NEXT = "set_next_delivery"
