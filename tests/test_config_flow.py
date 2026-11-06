"""Tests for the config flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.taxsys.api import (
    TaxsysAuthError,
    TaxsysConnectionError,
    TaxsysParseError,
)
from custom_components.taxsys.const import DOMAIN

from .conftest import ENTRY_DATA

GET_RIDES = "custom_components.taxsys.api.TaxsysClient.async_get_rides"


@pytest.fixture(autouse=True)
def no_setup():
    with patch("custom_components.taxsys.async_setup_entry", return_value=True):
        yield


async def test_user_flow(hass: HomeAssistant, rides) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with patch(GET_RIDES, return_value=rides):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**ENTRY_DATA, "company": " G-XXX "}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Taxsys 0000000"
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == "g-xxx_0000000"


@pytest.mark.parametrize(
    ("error", "key"),
    [
        (TaxsysAuthError, "invalid_auth"),
        (TaxsysParseError, "schedule_not_found"),
        (TaxsysConnectionError, "cannot_connect"),
        (RuntimeError, "unknown"),
    ],
)
async def test_user_flow_errors(hass: HomeAssistant, rides, error, key) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(GET_RIDES, side_effect=error):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], ENTRY_DATA
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": key}

    # Recovers after fixing the input.
    with patch(GET_RIDES, return_value=rides):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], ENTRY_DATA
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_already_configured(hass: HomeAssistant, config_entry) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], ENTRY_DATA
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, config_entry, rides) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    with patch(GET_RIDES, side_effect=TaxsysAuthError):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "ouder@example.com", CONF_PASSWORD: "fout"},
        )
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(GET_RIDES, return_value=rides):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "ouder@example.com", CONF_PASSWORD: "nieuw"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "nieuw"
