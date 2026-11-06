"""Config flow for Taxsys."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    TaxsysAuthError,
    TaxsysClient,
    TaxsysConnectionError,
    TaxsysParseError,
)
from .const import CONF_CLIENT_NUMBER, CONF_COMPANY, DOMAIN

_LOGGER = logging.getLogger(__name__)

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_COMPANY): str,
        vol.Required(CONF_CLIENT_NUMBER): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_input)
    for key in (CONF_COMPANY, CONF_CLIENT_NUMBER, CONF_USERNAME):
        if key in data:
            data[key] = str(data[key]).strip()
    return data


class TaxsysConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Taxsys."""

    VERSION = 1

    async def _async_validate(self, data: dict[str, Any]) -> dict[str, str]:
        """Try to log in and read the schedule. Return form errors."""
        session = async_create_clientsession(
            self.hass, auto_cleanup=False, cookie_jar=aiohttp.CookieJar()
        )
        client = TaxsysClient(
            session,
            data[CONF_COMPANY],
            data[CONF_CLIENT_NUMBER],
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
        )
        try:
            await client.async_get_rides()
        except TaxsysAuthError:
            return {"base": "invalid_auth"}
        except TaxsysParseError:
            return {"base": "schedule_not_found"}
        except TaxsysConnectionError:
            return {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error while validating Taxsys login")
            return {"base": "unknown"}
        finally:
            await session.close()
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step: portal details and login."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(user_input)
            await self.async_set_unique_id(
                f"{data[CONF_COMPANY]}_{data[CONF_CLIENT_NUMBER]}".lower()
            )
            self._abort_if_unique_id_configured()
            errors = await self._async_validate(data)
            if not errors:
                return self.async_create_entry(
                    title=f"Taxsys {data[CONF_CLIENT_NUMBER]}", data=data
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Login stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for new credentials."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, **_clean(user_input)}
            errors = await self._async_validate(data)
            if not errors:
                return self.async_update_reload_and_abort(entry, data=data)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME, default=entry.data.get(CONF_USERNAME, "")
                ): str,
                vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=schema, errors=errors
        )
