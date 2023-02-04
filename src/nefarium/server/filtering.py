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
from logging import getLogger
from typing import overload

import cssutils
import tldextract
from bs4 import BeautifulSoup
from cssutils.css import CSSStyleSheet
from yarl import URL

from ..helpers import truthy_string, is_url, wrap_css_inline, unwrap_css_inline

logger = getLogger(__name__)


def fix_html_bs4(proxy_url: URL, request_url: URL, html: str) -> str:
    """
    Fix HTML to work with the proxy.
    :param proxy_url: The URL of the proxy. i.e. http://localhost:8080/flows/1234/session/1234/auth
    :param request_url: The URL that the proxy is proxying. This doesn't change. i.e. https://example.com/login
    :param html: The HTML.
    :return: The fixed HTML.
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
        tag.string = fix_css_cssutils(proxy_url, request_url, tag.string)

    for tag in soups.find_all(
        attrs={"style": lambda style: truthy_string(style) is not None}
    ):
        tag["style"] = fix_css_cssutils(
            proxy_url, request_url, tag["style"], inline=True
        )

    return str(soups)


def fix_css_cssutils(
    proxy_url: URL, request_url: URL, css: str, *, inline: bool = False
) -> str:
    """
    Fix CSS to work with the proxy.
    :param proxy_url: The URL of the proxy. i.e. http://localhost:8080/flows/1234/session/1234/auth
    :param request_url: The URL that the proxy is proxying. This doesn't change. i.e. https://example.com/login
    :param css: The CSS to fix.
    :param inline: If this CSS is inline in an HTML tag, and does not have a selector.
    :return: The fixed CSS.
    """
    stylesheet: CSSStyleSheet = cssutils.parseString(
        css if not inline else wrap_css_inline(css)
    )

    for rule in stylesheet:
        if rule.type == rule.STYLE_RULE:
            for prop in rule.style:
                prop.value = re.sub(
                    r"url\(([^)]+)\)",
                    lambda match: f"url({fix_string_literal(proxy_url, request_url, match.group(1))})",
                    prop.value,
                )

    decoded = stylesheet.cssText.decode("utf-8")

    return decoded if not inline else unwrap_css_inline(decoded)


def fix_javascript(proxy_url: URL, request_url: URL, javascript: str) -> str:
    """
    Fix javascript to work with the proxy.
    :param proxy_url: The URL of the proxy. i.e. http://localhost:8080/flows/1234/session/1234/auth
    :param request_url: The URL that the proxy is proxying. This doesn't change. i.e. https://example.com/login
    :param javascript: A string of JavaScript to fix.
    :return: The fixed JavaScript.
    """
    # find string literals with regex and pass them to is_javascript_string_literal
    # https://stackoverflow.com/a/1732454/10428126
    # if a developer of a website did "https://exam" + "ple.com", we would be defeated.
    return re.sub(
        r"\"(\\.|[^\"\\])*\"|'(\\.|[^'\\])*'|`[^`]*`",
        lambda match: fix_string_literal(proxy_url, request_url, match.group(0)),
        javascript,
    )


def fix_string_literal(proxy_url: URL, request_url: URL, string_literal: str) -> str:
    """
    Fixes a single string literal in JavaScript or CSS.
    Note that this method always keeps quotes.
    :param proxy_url: The URL of the proxy. i.e. http://localhost:8080/flows/1234/session/1234/auth
    :param request_url: The URL that the proxy is proxying. This doesn't change. i.e. https://example.com/login
    :param string_literal: A string literal in JavaScript. i.e. "https://example.com/login/resource"
    :return: The fixed string literal. i.e. "http://localhost:8080/flows/1234/session/1234/auth/login/resource"
    """
    if string_literal.startswith(("'", '"', "`")) and string_literal.endswith(
        ("'", '"', "`")
    ):
        quoteless = string_literal[1:-1].lstrip("\\")

        if is_url(quoteless):
            return f"{string_literal[0]}{fix_url(proxy_url, request_url, quoteless)}{string_literal[-1]}"
        else:
            return string_literal
    else:
        return fix_url(proxy_url, request_url, string_literal)


@overload
def fix_url(proxy_url: URL, request_url: URL, url: str) -> str:
    ...


@overload
def fix_url(proxy_url: URL, request_url: URL, url: URL) -> URL:
    ...


def fix_url(proxy_url: URL, request_url: URL, url: str | URL) -> str | URL:
    """
    Fix a URL to work with the proxy. This method will be executed in an async context.
    :param proxy_url: The URL of the proxy. i.e. http://localhost:8080/flows/1234/session/1234/auth
    :param request_url: The URL of the request. i.e. https://example.com/login
    :param url: The URL to correct for the proxy. i.e. /login/resource
    :return: The corrected URL. i.e. http://localhost:8080/flows/1234/session/1234/auth/login/resource
    """
    if not (native_url := isinstance(url, URL)):
        if "base64" in url:
            return url  # can't do anything
        parsed_url = URL(url)
    else:
        parsed_url = url

    if not parsed_url.is_absolute():
        # this branch fixes relative paths, so they don't go to the root but instead the current session auth
        parsed_url = proxy_url.with_path(proxy_url.path + parsed_url.path)
    elif parsed_url.host is not None and request_url.host is not None:
        parsed_result = tldextract.extract(parsed_url.host)
        request_result = tldextract.extract(request_url.host)

        if parsed_result.registered_domain != request_result.registered_domain:
            # weird. we got redirected out.
            # NOTICE: authcaptureproxy sometimes redirects from this. if it does, we are fine.
            # if it doesn't, we are screwed and this URL will likely not work.
            logger.debug(
                f"Got redirected out of the domain! {request_url} -> {parsed_url}"
            )
            # we will still do the following just incase it works
            parsed_url = proxy_url.with_path(proxy_url.path + parsed_url.path)
        else:
            # this request will be handled normally.
            parsed_url = proxy_url.with_path(proxy_url.path + parsed_url.path)
    else:
        # this request is not currently proxied.
        # cloudflare handling code will probably go here.
        pass

    return parsed_url if native_url else str(parsed_url)


__all__ = (
    "fix_html_bs4",
    "fix_css_cssutils",
    "fix_string_literal",
    "fix_javascript",
    "fix_url",
)
