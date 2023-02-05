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

from datetime import datetime
from logging import getLogger
from urllib.parse import urlparse

import tldextract
from aiohttp.web import RouteTableDef
from aiohttp.web_exceptions import (
    HTTPBadRequest,
    HTTPNotFound,
    HTTPFound,
    HTTPInternalServerError,
    HTTPException,
)
from aiohttp.web_request import Request
from aiohttp.web_response import Response
from aiohttp_session import get_session
from authcaptureproxy import AuthCaptureProxy
from bson import ObjectId
from bson.errors import InvalidId
from httpx import Cookies
from motor.motor_asyncio import AsyncIOMotorCollection
from yarl import URL

from .proxy import create_proxy
from ..helpers import truthy_string, LimitedSizeDict, IS_DEBUG
from ..types import Flow, Session

CLONE_PROXY = False
# experimental, may not work
# if it is False while FOLLOW_REDIRECTS_OUT_OF_DOMAIN is True, cookies will get fucked up
FOLLOW_REDIRECTS_OUT_OF_DOMAIN = False
# If this is True, nefarium will try to follow redirects to other domains and will not return a 400
MAX_PROXY_SESSIONS = 10

routes = RouteTableDef()

logger = getLogger(__name__)


@routes.get("/flows/{flow_id}")
async def initialize_flow(request: Request) -> Response:
    aiohttp_session = await get_session(request)

    flow_id: str = request.match_info["flow_id"]  # hex

    try:
        object_id = ObjectId(flow_id)  # raises if invalid
    except InvalidId as e:
        raise HTTPBadRequest(reason="Unparseable Flow ID") from e

    flow = await request.app["db"]["flows"].find_one({"_id": object_id})

    if flow is None:
        raise HTTPNotFound(reason="Flow ID not found")

    redirect_uri: str | None = truthy_string(request.query.get("redirect_uri", ""))

    final_redirect_uri: str | None = None
    if redirect_uri is not None:
        try:
            parsed = urlparse(redirect_uri.lower().strip())
        except ValueError as e:
            raise HTTPBadRequest(reason="Unparseable redirect URI") from e

        if not URL(redirect_uri).is_absolute():
            raise HTTPBadRequest(reason="Redirect URI must be absolute")
        elif parsed.scheme not in ("http", "https"):
            raise HTTPBadRequest(reason="Redirect URI must be HTTP or HTTPS")
        elif parsed.netloc not in flow["redirect_uri_domains"]:
            # ok, so our redirect URI is not directly on the list
            # we need to check if any wildcard is matched

            redirect_uri_result = tldextract.extract(parsed.netloc)
            allowed: bool = False

            if "*" in flow["redirect_uri_domains"]:
                # allow global wildcard
                allowed = True
            else:
                for domain in flow["redirect_uri_domains"]:
                    try:
                        domain_result = tldextract.extract(domain)
                        if (
                            redirect_uri_result.registered_domain
                            == domain_result.registered_domain
                            and (
                                redirect_uri_result.subdomain.endswith(
                                    domain_result.subdomain
                                )
                                or domain_result.subdomain
                                == "*"  # allow wildcard like *.twitter.com
                            )
                        ):
                            allowed = True
                    except ValueError:
                        continue

            if not allowed:
                raise HTTPBadRequest(reason="Redirect URI not allowed per flow rules")
            else:
                final_redirect_uri = parsed.geturl()
        else:
            # redirect URI is good as is.
            final_redirect_uri = parsed.geturl()
    # redirect_uri is not declared
    elif "redirect_code" in flow and flow["redirect_code"]:
        # redirect code is set, so we do not need to follow the redirect URI.
        pass  # lets the final_redirect_uri be none
    elif not IS_DEBUG:
        raise HTTPBadRequest(reason="Missing redirect URI")

    new_session = await request.app["db"]["sessions"].insert_one(
        {
            "flow_id": flow["_id"],
            "state": "pending",
            "auth_data": None,
            "redirect_uri": final_redirect_uri,
            "ip_address": request.remote,
            "created_at": datetime.utcnow(),
        }
    )

    new_session_id = new_session.inserted_id

    return HTTPFound(
        location=f"/flows/{flow_id}/session/{new_session_id}/auth"
    )  # auth time


async def handle_auth(request: Request) -> Response:
    # this code handles out of domain redirects
    scheme: str | None = request.match_info.get("scheme")
    domain: str | None = request.match_info.get("domain")
    tail: str | None = request.match_info.get("tail")
    built_url: URL | None = (
        URL.build(scheme=scheme, host=domain)
        if scheme is not None and domain is not None
        else None
    )
    if built_url is not None and not FOLLOW_REDIRECTS_OUT_OF_DOMAIN:
        raise HTTPBadRequest(
            reason="Redirect URI not allowed per nefarium configuration"
        )

    aiohttp_session = await get_session(request)

    flow_id: str | None = request.match_info.get("flow_id")  # hex

    if flow_id is None:
        if "flow_id" in aiohttp_session:
            flow_id = aiohttp_session["flow_id"]
        else:
            raise HTTPBadRequest(reason="Missing flow ID")

    try:
        object_id = ObjectId(flow_id)  # raises if invalid
    except InvalidId as e:
        raise HTTPBadRequest(reason="Unparseable Flow ID") from e

    flow: Flow | None = await request.app["db"]["flows"].find_one({"_id": object_id})

    if flow is None:
        raise HTTPNotFound(reason="Flow ID not found")
    else:
        if aiohttp_session.get("flow_id") != flow_id:
            aiohttp_session["flow_id"] = flow_id

    session_id: str | None = request.match_info.get("session_id")  # hex

    if session_id is None:
        if "session_id" in aiohttp_session:
            session_id = aiohttp_session["session_id"]
        else:
            raise HTTPBadRequest(reason="Missing session ID")

    try:
        object_id = ObjectId(session_id)  # raises if invalid
    except InvalidId as e:
        raise HTTPBadRequest(reason="Unparseable Session ID") from e

    session: Session | None = await request.app["db"]["sessions"].find_one(
        {"_id": object_id}
    )

    if session is None:
        raise HTTPNotFound(reason="Session ID not found")
    else:
        if aiohttp_session.get("session_id") != session_id:
            aiohttp_session["session_id"] = session_id

    if session["flow_id"] != flow["_id"]:
        raise HTTPBadRequest(reason="Session ID does not match Flow ID")
    elif session["state"] != "pending":
        raise HTTPBadRequest(reason="Session already completed")

    # get AuthCaptureProxy
    proxies: LimitedSizeDict = request.app["auth_capture_proxies"]

    cookies: Cookies | None = None

    if session_id not in proxies:
        cookies = Cookies()
        # this is here because we may need to reuse the session of the proxy to preserve cookies
        session_collection: AsyncIOMotorCollection = request.app["db"]["sessions"]
        # this is done to prevent the request from being a closure variable in the proxy_factory function
        # which may take a lot of memory
        initial_base_url: URL = request.url

        def proxy_factory(*, base_url: URL | None = None) -> AuthCaptureProxy:
            # new_proxy is a closure variable at this point, but it may have been set by the time this is called
            # I think python will garbage collect the unused closure variables like the session, but I could be wrong?
            return create_proxy(
                flow,  # type: ignore  # do closures break mypy
                session,  # type: ignore
                base_url or initial_base_url,
                session_collection,
                cookie_jar=cookies,
            )

        new_proxy = proxy_factory()

        new_proxy.__factory = proxy_factory
        new_proxy.__sub_proxies = LimitedSizeDict(size_limit=10)
        # ok so we need to do this for performance reasons, because the proxies are SLOW to switch

        proxies[session_id] = new_proxy

    proxy: AuthCaptureProxy = proxies[session_id]
    cookies = proxy.session.cookies

    if CLONE_PROXY and built_url:
        if built_url not in proxy.__sub_proxies:  # type: ignore
            new_base_url = proxy.__initial_proxy_url.with_path(  # type: ignore
                f"{proxy.__initial_proxy_url.path.removesuffix('auth')}out/{scheme}/{domain}"  # type: ignore
            )
            # this code is the same as below so that we can skip a step
            proxy.__sub_proxies[built_url] = proxy.__factory(base_url=new_base_url)  # type: ignore
        proxy = proxy.__sub_proxies[built_url]  # type: ignore
        # the above code is a hacky way to clone the proxy, but it works for now
        # Additionally, the session will not be properly closed when it is garbage collected

    async with proxy.__process_lock:  # type: ignore
        if proxy.session.cookies is not cookies:
            # it's possible that dumb ol' authcaptureproxy changed the cookie jar and we need to try and fix it
            proxy.session.cookies = cookies

        # =====================START HACKY CODE=====================
        if built_url is not None and built_url != proxy._host_url:
            await proxy.change_host_url(built_url)
        elif proxy._host_url != proxy.__initial_host_url:  # type: ignore
            await proxy.change_host_url(proxy.__initial_host_url)  # type: ignore

        if built_url is not None:
            proxy._proxy_url = proxy.__initial_proxy_url.with_path(  # type: ignore
                f"{proxy.__initial_proxy_url.path.removesuffix('auth')}out/{scheme}/{domain}"  # type: ignore
            )
        elif proxy.__initial_proxy_url != proxy._proxy_url:  # type: ignore
            proxy._proxy_url = proxy.__initial_proxy_url  # type: ignore
        # =====================END HACKY CODE=======================

        try:
            return await proxy.all_handler(request)
        except Exception as e:
            logger.exception("Error in proxy handler!")
            raise HTTPInternalServerError(
                reason="Failed to pass login data back!"
            ) from e


routes.view("/flows/{flow_id}/session/{session_id}/auth")(handle_auth)
routes.view("/flows/{flow_id}/session/{session_id}/out/{scheme}/{domain}/{tail:.*}")(
    handle_auth
)  # dealing with redirects out
routes.view("/flows/{flow_id}/session/{session_id}/auth/{tail:.*}")(
    handle_auth
)  # other routes go through proxy


@routes.view("/{tail:.*}")
async def handle_root(request: Request) -> Response:
    """
    handle bad routes
    :param request:
    :return:
    """
    aiohttp_session = await get_session(request)

    if "flow_id" in aiohttp_session and "session_id" in aiohttp_session:
        try:
            return await handle_auth(request)
        except HTTPException as e:
            raise HTTPInternalServerError(reason="Failed to handle catch-all!") from e
    else:
        raise HTTPNotFound()


__all__ = ("routes",)
