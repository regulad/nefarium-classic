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

import re
from asyncio import AbstractEventLoop
from logging import getLogger
from os import environ
from typing import Any, Text

import cssutils
import httpx
from aiohttp import hdrs
from authcaptureproxy import AuthCaptureProxy
from bs4 import BeautifulSoup
from cssutils.css import CSSStyleSheet
from motor.motor_asyncio import AsyncIOMotorCollection
from yarl import URL

from ..helpers import truthy_string, is_url, httpx_to_yarl, IS_SLOW
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


def fix_url(proxy_url: URL, request_url: URL, url: str | URL) -> str | URL:
    """
    Fix a URL to work with the proxy. This method will be executed in an async context.
    :param proxy_url:
    :param request_url:
    :param url:
    :return:
    """
    if not (native_url := isinstance(url, URL)):
        if "base64" in url:
            return url  # can't do anything
        parsed_url = URL(url)
    else:
        parsed_url = url

    if not parsed_url.is_absolute():
        parsed_url = proxy_url.with_path(proxy_url.path + parsed_url.path)
    elif parsed_url.host == request_url.host:
        if request_url.host is not None:
            parsed_url = (
                parsed_url.with_scheme(request_url.scheme)
                .with_host(request_url.host)
                .with_path(proxy_url.path + parsed_url.path)
            )
    else:
        pass  # cloudflare stuff. handle

    return parsed_url if native_url else str(parsed_url)


def fix_javascript_string_literal(
    proxy_url: URL, request_url: URL, string_literal: str
) -> str:
    quoteless = string_literal[1:-1].lstrip("\\")  # thing

    if is_url(quoteless):
        return f"{string_literal[0]}{fix_url(proxy_url, request_url, quoteless)}{string_literal[-1]}"
    else:
        return string_literal


def fix_javascript(proxy_url: URL, request_url: URL, javascript: str) -> str:
    """
    Fix javascript to work with the proxy. This method will be executed in an async context.
    :param proxy_url:
    :param request_url:
    :param javascript:
    :return:
    """
    # find string literals with regex and pass them to is_javascript_string_literal
    # https://stackoverflow.com/a/1732454/10428126
    return re.sub(
        r"\"(\\.|[^\"\\])*\"|'(\\.|[^'\\])*'|`[^`]*`",
        lambda match: fix_javascript_string_literal(
            proxy_url, request_url, match.group(0)
        ),
        javascript,
    )


def fix_css_cssutils(
    proxy_url: URL, request_url: URL, css: str, *, inline: bool = False
) -> str:
    """
    Fix CSS to work with the proxy. This method will be executed in an async context.
    WARNING: This method is extremely computationally expensive. Use with caution.
    :param inline:
    :param proxy_url:
    :param request_url:
    :param css:
    :return:
    """
    stylesheet: CSSStyleSheet = cssutils.parseString(
        css if not inline else "*{" + css + "}"
    )

    for rule in stylesheet:
        if rule.type == rule.STYLE_RULE:
            for prop in rule.style:
                prop.value = re.sub(
                    r"url\(([^)]+)\)",
                    lambda match: f"url({fix_url(proxy_url, request_url, match.group(1))})",
                    prop.value,
                )

    return stylesheet.cssText.decode("utf-8")


def fix_css_fast(
    proxy_url: URL, request_url: URL, css: str, *, inline: bool = False
) -> str:
    """
    Fix CSS to work with the proxy. This method will be executed in an async context.
    :param inline:
    :param proxy_url:
    :param request_url:
    :param css:
    :return:
    """
    # this was written by Copilot, so it could be wrong or unsafe.
    # someone who is better at regex than me should check it
    return re.sub(
        r"url\(([^)]+)\)",
        lambda match: f"url({fix_url(proxy_url, request_url, match.group(1))})",
        css if not inline else "*{" + css + "}",
    )


fix_css = fix_css_cssutils if IS_SLOW else fix_css_fast


def fix_html_bs4(proxy_url: URL, request_url: URL, html: str) -> str:
    """
    Fix HTML to work with the proxy. This method will be executed in an async context.
    WARNING: This method is extremely computationally expensive. Use with caution.
    :param proxy_url:
    :param request_url:
    :param html:
    :return:
    """
    soups = BeautifulSoup(html, "html.parser")

    for tag in soups.find_all("script"):
        if tag.has_attr("src"):
            tag["src"] = fix_url(proxy_url, request_url, tag["src"])
        else:
            tag.string = fix_javascript(proxy_url, request_url, tag.string)

    for tag in soups.find_all("link"):
        if tag.has_attr("href"):
            tag["href"] = fix_url(proxy_url, request_url, tag["href"])

    for tag in soups.find_all("img"):
        if tag.has_attr("src"):
            tag["src"] = fix_url(proxy_url, request_url, tag["src"])

    for tag in soups.find_all("a"):
        if tag.has_attr("href"):
            tag["href"] = fix_url(proxy_url, request_url, tag["href"])

    for tag in soups.find_all("style"):
        tag.string = fix_css(proxy_url, request_url, tag.string)

    for tag in soups.find_all(
        attrs={"style": lambda style: bool(truthy_string(style))}
    ):
        tag["style"] = fix_css(proxy_url, request_url, tag["style"], inline=True)

    return str(soups)


def fix_html_fast(proxy_url: URL, request_url: URL, html: str) -> str:
    """
    Fix HTML to work with the proxy. This method will be executed in an async context.
    :param proxy_url:
    :param request_url:
    :param html:
    :return:
    """
    return html


fix_html = fix_html_bs4 if IS_SLOW else fix_html_fast


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
        proxy_target := URL(flow["proxy_target"]),
        session=get_httpx_client(flow),
        # note: this client may get clobbered by the AuthCaptureProxy so proxies may be unreliable?
    )
    proxy.headers = {hdrs.ACCEPT_ENCODING: "gzip"}  # httpx

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
    ) -> URL | None | str:
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
    ) -> URL | None | str:
        """
        Prevent redirecting out of the proxy target.
        :param resp:
        :param data:
        :param query:
        :return:
        """
        return_type: str = resp.headers[hdrs.CONTENT_TYPE].lower().split(";")[0]
        match return_type:
            case "text/html" | "application/xhtml+xml":
                resp._text = fix_html(base_url, httpx_to_yarl(resp.url), resp.text)
            case "text/javascript":
                resp._text = fix_javascript(
                    base_url, httpx_to_yarl(resp.url), resp.text
                )
            case "text/css":
                resp._text = fix_css(base_url, httpx_to_yarl(resp.url), resp.text)
        return None

    proxy.tests = {"test_auth": on_auth_data, "test_filter_output": filter_output}

    return proxy


__all__ = ("create_proxy",)
