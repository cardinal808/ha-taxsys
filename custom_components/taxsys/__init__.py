"""The Taxsys (leerlingenvervoer) integration."""

from __future__ import annotations

import aiohttp
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import TaxsysClient
from .const import CONF_CLIENT_NUMBER, CONF_COMPANY
from .coordinator import TaxsysConfigEntry, TaxsysCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.SENSOR,
]


def create_client(hass: HomeAssistant, data: dict) -> TaxsysClient:
    """Client with its own cookie jar, so logins don't leak between entries."""
    session = async_create_clientsession(hass, cookie_jar=aiohttp.CookieJar())
    return TaxsysClient(
        session,
        data[CONF_COMPANY],
        data[CONF_CLIENT_NUMBER],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )


async def async_setup_entry(hass: HomeAssistant, entry: TaxsysConfigEntry) -> bool:
    """Set up Taxsys from a config entry."""
    coordinator = TaxsysCoordinator(hass, entry, create_client(hass, dict(entry.data)))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TaxsysConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
