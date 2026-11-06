"""Small async client for the Taxsys parent portal.

Taxsys has no public API. This logs in the way a browser does and reads
the HTML page with the transport schedule.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlencode

import aiohttp

from .const import BASE_URL, PORTAL_ORIGIN
from .parser import LOGIN_FORM_MARKER, SCHEDULE_MARKER, Ride, parse_schedule

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
TIMEOUT = aiohttp.ClientTimeout(total=30)


class TaxsysError(Exception):
    """Base error."""


class TaxsysAuthError(TaxsysError):
    """Login rejected."""


class TaxsysConnectionError(TaxsysError):
    """Portal unreachable or returned an error."""


class TaxsysParseError(TaxsysError):
    """Logged in, but the schedule table was not found."""


class TaxsysClient:
    """Fetch the schedule for one participant (klantNr) of one company."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        company: str,
        client_number: str,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._company = company
        self._client_number = client_number
        self._username = username
        self._password = password

    @property
    def _login_url(self) -> str:
        return BASE_URL + "?" + urlencode({"page": "login", "company": self._company})

    @property
    def _schedule_url(self) -> str:
        return (
            BASE_URL
            + "?"
            + urlencode(
                {
                    "page": "deelnemerMutatie",
                    "klantNr": self._client_number,
                    "company": self._company,
                }
            )
        )

    async def _get_text(self, method: str, url: str, **kwargs) -> str:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "nl-NL,nl;q=0.9",
            **kwargs.pop("headers", {}),
        }
        try:
            async with self._session.request(
                method, url, headers=headers, timeout=TIMEOUT, **kwargs
            ) as resp:
                resp.raise_for_status()
                return await resp.text(errors="replace")
        except (TimeoutError, aiohttp.ClientError) as err:
            raise TaxsysConnectionError(str(err) or type(err).__name__) from err

    async def async_fetch_html(self) -> str:
        """Log in and return the raw schedule page."""
        # Start each fetch with a fresh session cookie.
        self._session.cookie_jar.clear()
        await self._get_text("GET", self._login_url)
        form = {
            "submit": "true",
            "username": self._username,
            "password": self._password,
            "passwordENC": hashlib.sha512(
                ("BSA" + self._password).encode("utf-8")
            ).hexdigest(),
            "meta_sw": "1280",
            "meta_sh": "800",
        }
        await self._get_text(
            "POST",
            self._login_url,
            data=form,
            headers={"Referer": self._login_url, "Origin": PORTAL_ORIGIN},
        )
        return await self._get_text("GET", self._schedule_url)

    async def async_get_rides(self) -> list[Ride]:
        """Log in, fetch and parse the schedule."""
        html = await self.async_fetch_html()
        if SCHEDULE_MARKER not in html:
            if LOGIN_FORM_MARKER in html:
                raise TaxsysAuthError("Login failed")
            raise TaxsysParseError("Schedule table not found on the page")
        return parse_schedule(html)
