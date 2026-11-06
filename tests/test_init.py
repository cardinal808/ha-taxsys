"""Tests for setup, entities and diagnostics."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.taxsys.api import TaxsysAuthError, TaxsysConnectionError
from custom_components.taxsys.diagnostics import async_get_config_entry_diagnostics

GET_RIDES = "custom_components.taxsys.api.TaxsysClient.async_get_rides"


async def _setup(hass, config_entry):
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_entities(
    hass: HomeAssistant, config_entry, mock_get_rides, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-11-09T07:30:00+01:00")
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    pickup = hass.states.get("sensor.taxsys_0000000_pickup")
    assert pickup.state == "2026-11-09T06:52:00+00:00"
    assert pickup.attributes["driver"] == "1234 - JAN JANSEN"
    assert pickup.attributes["live_location"] == "Hoofdweg 12, Ergens"

    home = hass.states.get("sensor.taxsys_0000000_home_arrival")
    assert home.state == "2026-11-09T13:48:00+00:00"
    assert home.attributes["pickup_time"] == "14:05"

    rides = hass.states.get("sensor.taxsys_0000000_rides")
    assert rides.state == "3"
    assert len(rides.attributes["rides"]) == 3

    window = hass.states.get("binary_sensor.taxsys_0000000_ride_window")
    assert window.state == "on"

    # Inside a ride window the coordinator polls every 5 minutes.
    assert config_entry.runtime_data.update_interval == timedelta(minutes=5)

    # After the morning ride the window closes on the next tick.
    freezer.move_to("2026-11-09T09:00:00+01:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.taxsys_0000000_ride_window").state == "off"

    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diag["entry"]["password"] == "**REDACTED**"
    assert diag["rides"][0]["driver"] == "**REDACTED**"

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_auth_failure_starts_reauth(hass: HomeAssistant, config_entry) -> None:
    with patch(GET_RIDES, side_effect=TaxsysAuthError):
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == SOURCE_REAUTH for f in flows)


async def test_connection_error_retries(hass: HomeAssistant, config_entry) -> None:
    with patch(GET_RIDES, side_effect=TaxsysConnectionError("down")):
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY
