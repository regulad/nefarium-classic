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

import asyncio
import base64
import json
import re
from functools import partial
from logging import getLogger
from os import environ
from typing import Any, Text, Callable

import httpx
from aiohttp import hdrs
from authcaptureproxy import AuthCaptureProxy
from authcaptureproxy.helper import run_func
from jsonschema.validators import validate

# from authcaptureproxy.examples.testers import test_amazon
from motor.motor_asyncio import AsyncIOMotorCollection
from yarl import URL

from .filtering import fix_html_bs4, fix_css_cssutils, fix_javascript
from ..helpers import truthy_string, IS_DEBUG, httpx_to_yarl, normalize_html, make_async
from ..types import *

logger = getLogger(__name__)


def build_page(flow: Flow, code: str) -> str:
    """
    Builds an HTML page that contains an auth code.
    :param flow: The flow that the auth code is for.
    :param code: The Base64 encoded auth code.
    :return: The HTML page.
    """

    flow_name = flow["name"]

    return normalize_html(
        f"""
    <!DOCTYPE html>
    <html lang="en-US">
        <head>
            <title>Nefarium for {flow_name}</title>
            <style>
                body {{
                    font-family: sans-serif;
                }}
                #auth-code {{
                    text-align: center;
                    padding: 0.2em;
                    background-color: #e8e8e8;
                    font-family: monospace;
                    overflow-wrap: break-word;
                    max-width: 100vw;  /* I dunno */
                }}
            </style>
        </head>
        <body>
            <h1>Nefarium Auth Code for {flow_name}</h1>
            <p>Copy and paste the following code into your app to authenticate with {flow_name}</p>
            <div id="auth-code">{code}</div>
            <footer>
                <p><i>Generated by <a href="https://github.com/regulad/nefarium">Nefarium</a></i></p>
            </footer>
        </body>
    </html>
    """
    )


def get_test_response(
    flow: Flow, session: Session, *, update_db: None | Callable = None  # type: ignore # intellij j tripping
) -> Callable:
    """
    Returns a closure that can be passed to an AuthCaptureProxy as a tester
    :param session: The session object.
    :param flow: The flow object.
    :param update_db: A function that updates the database with the new auth code.
    :return:
    """
    auth_goals: AuthGoals = flow["auth_goals"]

    async def test_response(
        resp: httpx.Response, data: dict[Text, Any], query: dict[Text, Any]
    ) -> URL | None | str:
        if auth_goals is None:
            # No auth goals were set, so we can't test anything.
            # this is legacy support
            assert (
                IS_DEBUG
            ), "No auth goals were set, but the test_response function was called."
            return None

        return_code: dict[Text, Any] = {}

        # ==CHECK STATUS CODE==
        if len(status_codes := auth_goals["status_codes"]) > 0:
            if resp.status_code not in status_codes:
                # The status code doesn't match. We need to leave.
                return None

            if len(status_codes) > 1:
                # Possible status codes could exist, so we need to encode the status code
                return_code["status_code"] = resp.status_code

        # ==CHECK URL==
        if len(goal_urls := auth_goals["goal_urls"]) > 0:
            if not resp.url:
                # For websocket connections or any other type of response where the URL is not set,
                # we can't use it here.
                return None

            for goal_url in goal_urls:
                if goal_url.startswith("/"):
                    if resp.url.path == goal_url:
                        break
                elif goal_url in str(resp.url):  # written by copilot, needs testing
                    break
            else:
                # The goal URL doesn't match. We need to leave.
                return None

        # ==CHECK COOKIES==
        if len(required_cookies := auth_goals["required_cookies"]) > 0:
            return_code["cookies"] = {}
            for cookie in required_cookies:
                if cookie not in resp.cookies:
                    # The cookie is not present. We need to leave.
                    return None
                elif cookie in auth_goals["required_cookies_regex"]:
                    if (
                        maybe_cookie_regex_def := auth_goals["required_cookies_regex"][
                            cookie
                        ]
                    ) is not None:
                        # validate the cookie
                        cookie_regex = re.compile(maybe_cookie_regex_def)
                        cookie_data = resp.cookies[cookie]
                        if not cookie_regex.match(cookie_data):
                            # The cookie data doesn't match. We need to leave.
                            return None

                # cookie is good, add it to return code
                return_code["cookies"][cookie] = resp.cookies[cookie]

        # ==CHECK HEADERS==
        if len(required_headers := auth_goals["required_headers"]) > 0:
            return_code["headers"] = {}
            for header in required_headers:
                if header not in resp.headers:
                    # The header is not present. We need to leave.
                    return None
                elif header in auth_goals["required_headers_regex"]:
                    if (
                        maybe_header_regex_def := auth_goals["required_headers_regex"][
                            header
                        ]
                    ) is not None:
                        # validate the header
                        header_regex = re.compile(maybe_header_regex_def)
                        header_data = resp.headers[header]
                        if not header_regex.match(header_data):
                            # The header data doesn't match. We need to leave.
                            return None

                # header is good, add it to return code
                return_code["headers"][header] = resp.headers[header]

        # ==CHECK QUERY PARAMETERS==
        if len(required_query_params := auth_goals["required_query_params"]) > 0:
            return_code["query"] = {}
            current_query = httpx_to_yarl(resp.url).query
            for param in required_query_params:
                if param not in current_query:
                    # The query parameter is not present. We need to leave.
                    return None
                elif param in auth_goals["required_query_params_regex"]:
                    if (
                        maybe_param_regex := auth_goals["required_query_params_regex"][
                            param
                        ]
                    ) is not None:
                        # validate the cookie
                        param_regex = re.compile(maybe_param_regex)
                        param_text = current_query[param]
                        if not param_regex.match(param_text):
                            # The cookie data doesn't match. We need to leave.
                            return None

                # cookie is good, add it to return code
                return_code["query"][param] = current_query[param]

        # ==CHECK BODY==
        if (required_body_type := auth_goals["return_body_requires_type"]) is not None:
            match required_body_type:
                case "json":
                    if resp.headers.get(hdrs.CONTENT_TYPE) != "application/json":
                        # The content type is not JSON. We need to leave.
                        return None
                    else:
                        # Content is JSON.
                        try:
                            body_json = resp.json()
                        except Exception as e:
                            logger.debug(f"Error validating JSON for {resp}: {e}")
                            return None

                        if (
                            body_schema_maybe_str := auth_goals[
                                "return_body_requires_json_schema"
                            ]
                        ) is not None:
                            # there is a schema defined, we need to check it
                            if not isinstance(body_schema_maybe_str, str):
                                body_schema = body_schema_maybe_str
                            else:
                                try:
                                    body_schema = json.loads(body_schema_maybe_str)
                                except Exception as e:
                                    logger.warning(
                                        f"Malformed flow! Error parsing JSON schema for {resp}: {e}"
                                    )
                                    return None

                            try:
                                validate(body_json, body_schema)
                            except Exception as e:
                                logger.debug(
                                    f"Error validating JSON schema for {resp}: {e}"
                                )
                                return None

                        # json is good, SEND IT
                        return_code["json"] = body_json
                case "regex":
                    if (
                        required_body_regex := auth_goals["return_body_requires_regex"]
                    ) is not None:
                        body_regex = re.compile(required_body_regex)
                        if not body_regex.match(resp.text):
                            # The body does not match the regex. We need to leave.
                            return None
                        else:
                            # Body matches regex.
                            return_code["body"] = resp.text

        # At this point, we know that the response is valid, and it returns some sort of authentication state.

        assert return_code, "No return code was added!"

        final_code = return_code.copy()

        if update_db is not None:
            try:
                await run_func(update_db, "update_db", final_code)
            except Exception as e:
                logger.exception(f"Error calling update database: {e}")

        json_code = json.dumps(final_code)
        utf_json = json_code.encode("utf-8")
        base64_code_bytes = base64.b64encode(utf_json)
        base64_code = base64_code_bytes.decode("utf-8")

        # decoding final code
        # json.loads(base64.b64decode(base64_code))

        should_present_code = "redirect_code" in flow and flow["redirect_code"]

        if (redirect_uri := session["redirect_uri"]) is None:
            if should_present_code:
                return build_page(flow, base64_code)
            else:
                assert IS_DEBUG, "Redirect URI is None, but we are not in debug mode!"
                return json_code

        final_query = {
            "code": base64_code,
        }

        if (
            "state_data" in session
            and (state_data := session["state_data"]) is not None
        ):
            final_query["state"] = state_data

        return URL(redirect_uri).with_query(final_query)

    return test_response


def get_httpx_client(flow: Flow, *args, **kwargs) -> httpx.AsyncClient:
    proxies = {}

    # Proxy
    if (
        "request_proxy" in flow
        and (proxy := truthy_string(flow.get("request_proxy"))) is not None
    ):  # type: ignore # manually checked
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

    if proxies:
        kwargs["proxies"] = proxies

    return httpx.AsyncClient(*args, **kwargs)  # type: ignore # manually checked


def create_proxy(
    flow: Flow,
    session: Session,
    base_url: URL,
    collection: AsyncIOMotorCollection,
    *,
    cookie_jar: httpx.Cookies | None = None,
) -> AuthCaptureProxy:
    """
    Creates a proxy for the given flow.
    :param flow: The flow to create a proxy for.
    :param session: The session to create a proxy for.
    :param base_url: The base URL of the proxy. i.e. http://localhost:8080/flows/1234/session/1234/auth
    :param collection: The Motor collection to commit to.
    :param cookie_jar: The cookie jar to use for the proxy.
    :return:
    """
    proxy = AuthCaptureProxy(
        base_url,
        # should be called on first go, so this will be correct unless the proxy cache rolls over which should be rare
        proxy_target := URL(flow["proxy_target"]),
        session=get_httpx_client(flow, cookies=cookie_jar),
        # note: this client may get clobbered by the AuthCaptureProxy so proxies may be unreliable?
    )

    proxy.__process_lock = asyncio.Lock()
    proxy.__initial_host_url = proxy._host_url
    proxy.__initial_proxy_url = proxy._proxy_url

    proxy._active = True  # type: ignore # we don't attach the proxy to a runner so we need to do it manually

    proxy.headers = {hdrs.ACCEPT_ENCODING: "gzip"}  # httpx

    if "auth_goals" in flow:

        async def update_auth_state(auth_data: Any) -> None:
            await collection.update_one(
                {"_id": session["_id"]},
                {"$set": {"state": "authed", "auth_data": auth_data}},
            )

        proxy.tests = {
            "test_auth": get_test_response(flow, session, update_db=update_auth_state),
        }

    if flow["filter_response"]:
        html_modifiers = {  # type: ignore  # PyCharm is ANGRY
            "post_authcaptureproxy_fixes": make_async(
                partial(fix_html_bs4, base_url, proxy_target),  # type: ignore  # mypy is ANGRY
            ),
        }

        proxy.modifiers = {
            "text/html": html_modifiers,
            "application/xhtml+xml": html_modifiers,
            "text/javascript": {
                "fix_javascript": make_async(
                    partial(fix_javascript, base_url, proxy_target),
                ),
            },
            "text/css": {
                "fix_css": make_async(
                    partial(fix_css_cssutils, base_url, proxy_target)
                ),
            },
        }

    return proxy


__all__ = ("create_proxy",)
