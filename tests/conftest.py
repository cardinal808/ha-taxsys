"""Fixtures for Taxsys tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taxsys.const import CONF_CLIENT_NUMBER, CONF_COMPANY, DOMAIN
from custom_components.taxsys.parser import parse_schedule

FIXTURE = Path(__file__).parent / "fixtures" / "schedule.html"

ENTRY_DATA = {
    CONF_COMPANY: "G-XXX",
    CONF_CLIENT_NUMBER: "0000000",
    CONF_USERNAME: "ouder@example.com",
    CONF_PASSWORD: "geheim",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components in every test."""
    yield


@pytest.fixture
def schedule_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def rides(schedule_html):
    return parse_schedule(schedule_html)


@pytest.fixture
def mock_get_rides(rides):
    with patch(
        "custom_components.taxsys.api.TaxsysClient.async_get_rides",
        return_value=rides,
    ) as mock:
        yield mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Taxsys 0000000",
        unique_id="g-xxx_0000000",
        data=ENTRY_DATA,
    )
