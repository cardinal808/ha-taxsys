"""Constants for the Taxsys integration."""

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

DOMAIN = "taxsys"

CONF_COMPANY = "company"
CONF_CLIENT_NUMBER = "client_number"

BASE_URL = "https://account.taxsys.nl/taxsys/"
PORTAL_ORIGIN = "https://account.taxsys.nl"

# The portal is Dutch; all times on it are local Dutch time.
PORTAL_TZ = ZoneInfo("Europe/Amsterdam")

# Polling: every few minutes around a ride, rarely otherwise.
FAST_INTERVAL = timedelta(minutes=5)
MAX_IDLE_INTERVAL = timedelta(hours=3)
# Refresh window around a ride: from this long before the pickup time ...
WINDOW_BEFORE = timedelta(minutes=45)
# ... until this long after the arrival time.
WINDOW_AFTER = timedelta(minutes=15)
# Daily early refresh so the day's times are known before the first window.
MORNING_REFRESH_HOUR = 6
MORNING_REFRESH_MINUTE = 30

PART_MORNING = "ochtend"
PART_AFTERNOON = "middag"
