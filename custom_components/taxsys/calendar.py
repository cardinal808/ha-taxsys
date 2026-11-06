"""Calendar for Taxsys: every ride on the schedule as an event."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import PART_MORNING
from .coordinator import TaxsysConfigEntry, TaxsysCoordinator
from .entity import TaxsysEntity
from .parser import Ride, ride_end

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TaxsysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar."""
    async_add_entities([TaxsysCalendar(entry.runtime_data)])


def _place(text: str) -> str:
    """First line of an address block, e.g. the school name."""
    return text.split(",")[0].strip() if text else ""


def ride_event(ride: Ride) -> CalendarEvent | None:
    """Turn a ride into a calendar event."""
    if ride.pickup is None:
        return None
    end = (
        ride.arrival
        if ride.arrival and ride.arrival > ride.pickup
        else ride.pickup + timedelta(minutes=30)
    )
    label = "Taxi ophalen" if ride.part == PART_MORNING else "Taxi naar huis"
    destination = _place(ride.destination)
    summary = f"{label} → {destination}" if destination else label
    if ride.status:
        summary += f" ({ride.status})"
    lines = [
        f"Ophalen: {ride.pickup_time}",
        f"Aankomst: {ride.arrival_time}",
        f"Van: {ride.origin}",
        f"Naar: {ride.destination}",
    ]
    if ride.status:
        lines.append(f"Status: {ride.status}")
    if ride.driver:
        lines.append(f"Chauffeur: {ride.driver}")
    if ride.route:
        lines.append(f"Route: {ride.route}")
    if ride.live_location:
        lines.append(f"Live: {ride.live_location} ({ride.live_time or '?'})")
    return CalendarEvent(
        start=ride.pickup,
        end=end,
        summary=summary,
        description="\n".join(lines),
        location=ride.origin or None,
        uid=f"{ride.date.isoformat()}_{ride.part}",
    )


class TaxsysCalendar(TaxsysEntity, CalendarEntity):
    """All rides on the Taxsys schedule."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: TaxsysCoordinator) -> None:
        super().__init__(coordinator, "schedule")

    def _events(self) -> list[CalendarEvent]:
        return [
            event
            for ride in self.coordinator.data.rides
            if (event := ride_event(ride)) is not None
        ]

    @property
    def event(self) -> CalendarEvent | None:
        """Current or next ride."""
        now = dt_util.now()
        for ride in self.coordinator.data.rides:
            if ride_end(ride) > now and (event := ride_event(ride)):
                return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Rides that overlap the requested period."""
        return [
            event
            for event in self._events()
            if event.end > start_date and event.start < end_date
        ]
