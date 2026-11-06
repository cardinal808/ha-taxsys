"""Data update coordinator for Taxsys."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import TaxsysAuthError, TaxsysClient, TaxsysError
from .const import (
    DOMAIN,
    FAST_INTERVAL,
    MAX_IDLE_INTERVAL,
    MORNING_REFRESH_HOUR,
    MORNING_REFRESH_MINUTE,
    PART_AFTERNOON,
    PART_MORNING,
    PORTAL_TZ,
    WINDOW_AFTER,
    WINDOW_BEFORE,
)
from .parser import Ride, next_ride

_LOGGER = logging.getLogger(__name__)

type TaxsysConfigEntry = ConfigEntry[TaxsysCoordinator]


@dataclass
class TaxsysData:
    """Latest schedule."""

    rides: list[Ride] = field(default_factory=list)
    morning: Ride | None = None
    afternoon: Ride | None = None
    updated: datetime | None = None


def ride_windows(rides: list[Ride]) -> list[tuple[datetime, datetime]]:
    """Time spans around each ride in which we poll often."""
    windows = []
    for ride in rides:
        if ride.pickup and ride.arrival:
            windows.append((ride.pickup - WINDOW_BEFORE, ride.arrival + WINDOW_AFTER))
    return windows


def next_interval(rides: list[Ride], now: datetime) -> timedelta:
    """Poll every few minutes during a ride window, otherwise sleep until the next one."""
    windows = ride_windows(rides)
    if any(start <= now < end for start, end in windows):
        return FAST_INTERVAL

    local = now.astimezone(PORTAL_TZ)
    morning = local.replace(
        hour=MORNING_REFRESH_HOUR,
        minute=MORNING_REFRESH_MINUTE,
        second=0,
        microsecond=0,
    )
    if morning <= local:
        morning += timedelta(days=1)
    candidates = [morning] + [start for start, _ in windows if start > now]
    wait = min(candidates) - now
    return max(timedelta(minutes=1), min(wait, MAX_IDLE_INTERVAL))


class TaxsysCoordinator(DataUpdateCoordinator[TaxsysData]):
    """Fetch the schedule with an adaptive interval."""

    config_entry: TaxsysConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TaxsysConfigEntry, client: TaxsysClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=FAST_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> TaxsysData:
        try:
            rides = await self.client.async_get_rides()
        except TaxsysAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="auth_failed"
            ) from err
        except TaxsysError as err:
            # Retry soon after an error.
            self.update_interval = FAST_INTERVAL
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        now = dt_util.now()
        self.update_interval = next_interval(rides, now)
        _LOGGER.debug(
            "Fetched %d rides, next update in %s", len(rides), self.update_interval
        )
        return TaxsysData(
            rides=rides,
            morning=next_ride(rides, PART_MORNING, now),
            afternoon=next_ride(rides, PART_AFTERNOON, now),
            updated=now,
        )
