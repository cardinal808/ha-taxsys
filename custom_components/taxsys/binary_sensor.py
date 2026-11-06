"""Binary sensor for Taxsys: is a ride happening around now?"""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .coordinator import TaxsysConfigEntry, TaxsysCoordinator, ride_windows
from .entity import TaxsysEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TaxsysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor."""
    async_add_entities([TaxsysRideWindowSensor(entry.runtime_data)])


class TaxsysRideWindowSensor(TaxsysEntity, BinarySensorEntity):
    """On from 45 min before pickup until 15 min after arrival of any ride.

    Handy as a visibility condition for a dashboard card.
    """

    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: TaxsysCoordinator) -> None:
        super().__init__(coordinator, "ride_window")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Re-evaluate every minute; the window depends on the clock, not only on new data.
        self.async_on_remove(
            async_track_time_interval(self.hass, self._tick, timedelta(minutes=1))
        )

    @callback
    def _tick(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        now = dt_util.now()
        return any(
            start <= now < end
            for start, end in ride_windows(self.coordinator.data.rides)
        )
