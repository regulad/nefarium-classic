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

from logging import getLogger
from typing import Text, Any
from urllib.parse import urlparse

import httpx
from aiohttp.web import RouteTableDef
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotFound, HTTPFound
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from authcaptureproxy import AuthCaptureProxy
from bson import ObjectId
from bson.errors import InvalidId
from yarl import URL

from .helpers import truthy_string, LimitedSizeDict
from .types import Flow, Session

routes = RouteTableDef()

logger = getLogger(__name__)


@routes.get("/flows/{flow_id}")
async def initialize_flow(request: Request) -> Response:
    flow_id: str = request.match_info["flow_id"]  # hex

    try:
        object_id = ObjectId(flow_id)  # raises if invalid
    except InvalidId as e:
        raise HTTPBadRequest(reason="Unparseable Flow ID") from e

    flow = await request.app["db"]["flows"].find_one({"_id": object_id})

    if flow is None:
        raise HTTPNotFound(reason="Flow ID not found")

    redirect_url: str | None = truthy_string(
        request.query.get("redirect_url", "")
    ) or truthy_string(request.query.get("redirect_uri", ""))

    if redirect_url is not None:
        try:
            parsed = urlparse(redirect_url.lower().strip())
        except ValueError as e:
            raise HTTPBadRequest(reason="Unparseable redirect URL") from e
        if not URL(redirect_url).is_absolute():
            raise HTTPBadRequest(reason="Redirect URL must be absolute")
        elif parsed.netloc not in flow["redirect_url_domains"]:
            # TODO: check for wildcards
            raise HTTPBadRequest(reason="Redirect URL not allowed")
    else:
        raise HTTPBadRequest(reason="Missing redirect URL")

    new_session = await request.app["db"]["sessions"].insert_one(
        {
            "flow_id": flow["_id"],
            "state": "pending",
            "auth_data": None,
            "redirect_url": parsed.geturl(),
            "ip_address": request.remote,
        }
    )

    new_session_id = new_session.inserted_id

    return HTTPFound(
        location=f"/flows/{flow_id}/session/{new_session_id}/auth"
    )  # auth time


async def handle_auth(request: Request) -> Response:
    flow_id: str = request.match_info["flow_id"]  # hex

    try:
        object_id = ObjectId(flow_id)  # raises if invalid
    except InvalidId as e:
        raise HTTPBadRequest(reason="Unparseable Flow ID") from e

    flow: Flow | None = await request.app["db"]["flows"].find_one({"_id": object_id})

    if flow is None:
        raise HTTPNotFound(reason="Flow ID not found")

    session_id: str = request.match_info["session_id"]  # hex

    try:
        object_id = ObjectId(session_id)  # raises if invalid
    except InvalidId as e:
        raise HTTPBadRequest(reason="Unparseable Session ID") from e

    session: Session | None = await request.app["db"]["sessions"].find_one(
        {"_id": object_id}
    )

    if session["flow_id"] != flow["_id"]:
        raise HTTPBadRequest(reason="Session ID does not match Flow ID")
    elif session["state"] != "pending":
        raise HTTPBadRequest(reason="Session already completed")

    # get AuthCaptureProxy
    proxies: LimitedSizeDict = request.app["auth_capture_proxies"]

    proxy: AuthCaptureProxy
    if session_id not in proxies:
        proxy = AuthCaptureProxy(
            request.url,
            # should be called on first go, so this will be correct unless the proxy cache rolls over which should be rare
            URL(flow["proxy_target"]),
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
            await request.app["db"]["sessions"].update_one(
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
                request.app.loop.create_task(update_auth_state(auth_data))

                try:
                    del proxies[session_id]  # free to GC
                except NameError:
                    pass

                return callback_url.with_query({"state": auth_data})
            else:
                return None  # can continue

        def prevent_redirect_out(
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

        proxy.tests = {"test_auth": on_auth_data, "test_redirect": prevent_redirect_out}
        proxies[session_id] = proxy
    else:
        proxy = proxies[session_id]

    return await proxy.all_handler(request)


routes.view("/flows/{flow_id}/session/{session_id}/auth")(handle_auth)
routes.view("/flows/{flow_id}/session/{session_id}/auth/{tail:.*}")(
    handle_auth
)  # other routes go through proxy

__all__ = ("routes",)
