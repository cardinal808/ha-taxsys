"""Sensors for Taxsys."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TaxsysConfigEntry, TaxsysCoordinator
from .entity import TaxsysEntity
from .parser import Ride

PARALLEL_UPDATES = 0


def ride_attributes(ride: Ride | None) -> dict[str, Any]:
    """Attributes shared by the ride sensors."""
    if ride is None:
        return {}
    return {
        "date": ride.date.isoformat(),
        "day": ride.day,
        "pickup_time": ride.pickup_time,
        "arrival_time": ride.arrival_time,
        "origin": ride.origin,
        "destination": ride.destination,
        "status": ride.status,
        "route": ride.route,
        "driver": ride.driver,
        "live_location": ride.live_location,
        "live_time": ride.live_time,
    }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TaxsysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            TaxsysPickupSensor(coordinator),
            TaxsysHomeArrivalSensor(coordinator),
            TaxsysRidesSensor(coordinator),
        ]
    )


class TaxsysPickupSensor(TaxsysEntity, SensorEntity):
    """Pickup time (O-tijd) of the next morning ride."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:taxi"

    def __init__(self, coordinator: TaxsysCoordinator) -> None:
        super().__init__(coordinator, "pickup")

    @property
    def _ride(self) -> Ride | None:
        return self.coordinator.data.morning

    @property
    def native_value(self) -> datetime | None:
        return self._ride.pickup if self._ride else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return ride_attributes(self._ride)


class TaxsysHomeArrivalSensor(TaxsysEntity, SensorEntity):
    """Arrival time (A-tijd) of the next afternoon ride."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:home-clock"

    def __init__(self, coordinator: TaxsysCoordinator) -> None:
        super().__init__(coordinator, "home_arrival")

    @property
    def _ride(self) -> Ride | None:
        return self.coordinator.data.afternoon

    @property
    def native_value(self) -> datetime | None:
        return self._ride.arrival if self._ride else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return ride_attributes(self._ride)


class TaxsysRidesSensor(TaxsysEntity, SensorEntity):
    """Number of rides on the schedule, with the full list as attribute."""

    _attr_icon = "mdi:calendar-clock"
    _unrecorded_attributes = frozenset({"rides"})

    def __init__(self, coordinator: TaxsysCoordinator) -> None:
        super().__init__(coordinator, "rides")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.rides)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"rides": [ride.as_dict() for ride in self.coordinator.data.rides]}
