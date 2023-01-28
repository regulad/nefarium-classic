# nefarium provides an API similar to OAuth for websites that do not support it
# Copyright (C) 2023  Parker Wahle
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

from asyncio import AbstractEventLoop
from logging import getLogger
from os import environ
from typing import Any, Text

import httpx
from authcaptureproxy import AuthCaptureProxy
from motor.motor_asyncio import AsyncIOMotorCollection
from yarl import URL

from ..helpers import truthy_string
from ..types import *

logger = getLogger(__name__)


def get_httpx_client(flow: Flow) -> httpx.AsyncClient:
    proxies = {}
    if (proxy := truthy_string(flow.get("request_proxy"))) is not None:  # type: ignore # manually checked
        proxies["http"] = proxy
        proxies["https"] = proxy
        logger.warning(
            f"Using proxy from flow config: {proxy}. This could get overwritten by AuthCaptureProxy."
        )
    elif (proxy := truthy_string(environ.get("NEFARIUM_PROXY"))) is not None:  # type: ignore # manually checked
        proxies["http"] = proxy
        proxies["https"] = proxy
        logger.warning(
            f"Using proxy from environment variable: {proxy}. This could get overwritten by AuthCaptureProxy."
        )

    return httpx.AsyncClient(proxies=proxies or None)  # type: ignore # manually checked


def create_proxy(
    flow: Flow,
    session: Session,
    base_url: URL,
    loop: AbstractEventLoop,
    collection: AsyncIOMotorCollection,
) -> AuthCaptureProxy:
    proxy = AuthCaptureProxy(
        base_url,
        # should be called on first go, so this will be correct unless the proxy cache rolls over which should be rare
        URL(flow["proxy_target"]),
        #    session=get_httpx_client(flow),
        # note: this client may get clobbered by the AuthCaptureProxy so proxies may be unreliable?
    )

    callback_url: URL = URL(session["redirect_url"])

    def check_auth_data(
        resp: httpx.Response, data: dict[Text, Any], query: dict[Text, Any]
    ) -> Any | None:
        """
        Check if the auth data is valid. A closure that uses the flow config to determine if the auth data is valid.
        :param resp:
        :param data:
        :param query:
        :return: Auth data if valid, None otherwise. Must be JSON serializable.
        """
        return None  # TODO check in accordance with flow config

    async def update_auth_state(auth_data: Any) -> None:
        await collection.update_one(
            {"_id": session["_id"]},
            {"$set": {"state": "authed", "auth_data": auth_data}},
        )

    def on_auth_data(
        resp: httpx.Response, data: dict[Text, Any], query: dict[Text, Any]
    ) -> URL | None:
        """
        A callback for AuthCaptureProxy that checks if the auth data is valid.
        :param resp:
        :param data:
        :param query:
        :return: The callback URL if auth data is valid, None otherwise
        """
        # store callback URL in closure
        if auth_data := check_auth_data(resp, data, query):
            loop.create_task(update_auth_state(auth_data))

            return callback_url.with_query({"state": auth_data})
        else:
            return None  # can continue

    def filter_output(
        resp: httpx.Response, data: dict[Text, Any], query: dict[Text, Any]
    ) -> URL | None:
        """
        Prevent redirecting out of the proxy target.
        :param resp:
        :param data:
        :param query:
        :return:
        """
        # TODO: stop cloudflare from redirecting to the proxy target
        # maybe beautifulsoup the response and change the URLs using regex
        return None

    proxy.tests = {"test_auth": on_auth_data, "test_filter_output": filter_output}

    return proxy


__all__ = ("create_proxy",)
