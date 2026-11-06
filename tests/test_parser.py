"""Tests for the schedule parser and polling interval."""

from datetime import date, datetime, timedelta

import pytest

from custom_components.taxsys.api import TaxsysAuthError, TaxsysClient, TaxsysParseError
from custom_components.taxsys.const import PORTAL_TZ
from custom_components.taxsys.coordinator import next_interval
from custom_components.taxsys.parser import next_ride


def test_parse_rides(rides) -> None:
    assert len(rides) == 3
    first = rides[0]
    assert first.date == date(2026, 11, 9)
    assert first.day == "Maandag"
    assert first.part == "ochtend"
    assert first.pickup_time == "07:52"
    assert first.arrival_time == "08:35"  # the hidden cell is skipped
    assert first.pickup == datetime(2026, 11, 9, 7, 52, tzinfo=PORTAL_TZ)
    assert first.origin == "Thuis, Dorpsstraat 1, Ergens"
    assert first.driver == "1234 - JAN JANSEN"
    assert first.live_location == "Hoofdweg 12, Ergens"
    assert first.live_time == "07:41"
    assert rides[1].part == "middag"
    assert rides[1].live_location is None
    assert rides[2].date == date(2026, 11, 10)  # four-digit year


def test_next_ride(rides) -> None:
    assert next_ride(rides, "ochtend", date(2026, 11, 9)) is rides[0]
    assert next_ride(rides, "ochtend", date(2026, 11, 10)) is rides[2]
    assert next_ride(rides, "middag", date(2026, 11, 10)) is None


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        # Inside the morning window (07:07 - 08:50).
        (datetime(2026, 11, 9, 7, 30, tzinfo=PORTAL_TZ), timedelta(minutes=5)),
        # Between windows: wait until the afternoon window opens at 13:20.
        (datetime(2026, 11, 9, 12, 20, tzinfo=PORTAL_TZ), timedelta(hours=1)),
        # Long gap: capped at three hours.
        (datetime(2026, 11, 9, 9, 0, tzinfo=PORTAL_TZ), timedelta(hours=3)),
        # Late evening: next is the 06:30 refresh.
        (datetime(2026, 11, 9, 5, 0, tzinfo=PORTAL_TZ), timedelta(minutes=90)),
    ],
)
def test_next_interval(rides, now, expected) -> None:
    assert next_interval(rides, now) == expected


async def test_client_detects_login_page(schedule_html) -> None:
    client = TaxsysClient(None, "G-XXX", "1", "u", "p")

    async def login_page():
        return '<form><input name="password"></form>'

    client.async_fetch_html = login_page
    with pytest.raises(TaxsysAuthError):
        await client.async_get_rides()

    async def other_page():
        return "<html>onderhoud</html>"

    client.async_fetch_html = other_page
    with pytest.raises(TaxsysParseError):
        await client.async_get_rides()

    async def schedule():
        return schedule_html

    client.async_fetch_html = schedule
    assert len(await client.async_get_rides()) == 3
