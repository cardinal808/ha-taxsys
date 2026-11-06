"""Run the real HTTP login sequence against a fake local portal."""

import hashlib

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from custom_components.taxsys import api
from custom_components.taxsys.api import TaxsysAuthError, TaxsysClient


@pytest.fixture
async def portal(socket_enabled, schedule_html, monkeypatch):
    sessions: dict[str, bool] = {}

    async def handler(request: web.Request) -> web.Response:
        page = request.query.get("page")
        sid = request.cookies.get("PHPSESSID")
        if page == "login" and request.method == "GET":
            resp = web.Response(text="<form><input name='password'></form>")
            sid = f"s{len(sessions)}"
            sessions[sid] = False
            resp.set_cookie("PHPSESSID", sid)
            return resp
        if page == "login" and request.method == "POST":
            form = await request.post()
            expected = hashlib.sha512(b"BSAgeheim").hexdigest()
            if sid in sessions and form["passwordENC"] == expected:
                sessions[sid] = True
            return web.Response(text="ok")
        if page == "deelnemerMutatie" and sessions.get(sid):
            assert request.query["klantNr"] == "0000000"
            return web.Response(text=schedule_html)
        return web.Response(text='<form><input name="password"></form>')

    app = web.Application()
    app.router.add_route("*", "/taxsys/", handler)
    server = TestServer(app)
    await server.start_server()
    monkeypatch.setattr(api, "BASE_URL", str(server.make_url("/taxsys/")))
    yield
    await server.close()


async def test_login_and_fetch(portal) -> None:
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as s:
        rides = await TaxsysClient(
            s, "G-XXX", "0000000", "u", "geheim"
        ).async_get_rides()
        assert len(rides) == 3
        # A second fetch logs in again with a fresh cookie.
        rides = await TaxsysClient(
            s, "G-XXX", "0000000", "u", "geheim"
        ).async_get_rides()
        assert len(rides) == 3


async def test_wrong_password(portal) -> None:
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True)) as s:
        with pytest.raises(TaxsysAuthError):
            await TaxsysClient(s, "G-XXX", "0000000", "u", "fout").async_get_rides()
