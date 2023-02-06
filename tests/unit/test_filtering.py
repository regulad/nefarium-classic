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

import pytest
from yarl import URL

from nefarium import normalize_css, normalize_html
from nefarium.server import (
    fix_html_bs4,
    fix_css_cssutils,
    fix_javascript,
    fix_url,
    fix_string_literal,
)

from .. import dummy_proxy_configuration


@pytest.mark.parametrize(
    "proxy_url, request_url, url, fixed_url",
    [
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            "/login/basename",
            "http://localhost:8080/flows/1234/session/1234/auth/login/basename",
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            URL("/login/basename"),
            URL("http://localhost:8080/flows/1234/session/1234/auth/login/basename"),
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            "/login/resource",
            "http://localhost:8080/flows/1234/session/1234/auth/login/resource",
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            URL("/login/resource"),
            URL("http://localhost:8080/flows/1234/session/1234/auth/login/resource"),
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            "https://example.com/login/basename",
            "http://localhost:8080/flows/1234/session/1234/auth/login/basename",
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            URL("https://example.com/login/basename"),
            URL("http://localhost:8080/flows/1234/session/1234/auth/login/basename"),
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            "https://example.com/login/resource",
            "http://localhost:8080/flows/1234/session/1234/auth/login/resource",
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            URL("https://example.com/login/resource"),
            URL("http://localhost:8080/flows/1234/session/1234/auth/login/resource"),
        ),
    ],
)
def test_url_filter(proxy_url, request_url, url, fixed_url):
    assert (
        fix_url(proxy_url, request_url, dummy_proxy_configuration(), url) == fixed_url
    )


@pytest.mark.parametrize(
    "proxy_url, request_url, literal, fixed_literal",
    [
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            '"/login/basename"',
            '"http://localhost:8080/flows/1234/session/1234/auth/login/basename"',
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            "'/login/basename'",
            "'http://localhost:8080/flows/1234/session/1234/auth/login/basename'",
        ),
    ],
)
def test_literal_fiter(proxy_url, request_url, literal, fixed_literal):
    assert (
        fix_string_literal(proxy_url, request_url, dummy_proxy_configuration(), literal)
        == fixed_literal
    )


@pytest.mark.parametrize(
    "proxy_url, request_url, inline, css, fixed_css",
    [
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            False,
            """
            * {
                background-image: url('/login/picture.png')
            }
            """,
            """
            * {
                background-image: url('http://localhost:8080/flows/1234/session/1234/auth/login/picture.png')
            }
            """,
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            False,
            """
            * {
                background-image: url("/login/picture.png")
            }
            """,
            """
            * {
                background-image: url("http://localhost:8080/flows/1234/session/1234/auth/login/picture.png")
            }
            """,
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            False,
            """
            * {
                background-image: url(/login/picture.png)
            }
            """,
            """
            * {
                background-image: url(http://localhost:8080/flows/1234/session/1234/auth/login/picture.png)
            }
            """,
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            True,
            "background-image: url('/login/picture.png')",
            "background-image: url(http://localhost:8080/flows/1234/session/1234/auth/login/picture.png)"
            # doesn't have quotes for no reason in particular
        ),
    ],
)
def test_css_cssutils_filter(proxy_url, request_url, inline, css, fixed_css):
    if inline:
        assert (
            fix_css_cssutils(
                proxy_url, request_url, dummy_proxy_configuration(), css, inline=inline
            )
            == fixed_css
        )
    else:
        assert normalize_css(
            fix_css_cssutils(
                proxy_url, request_url, dummy_proxy_configuration(), css, inline=inline
            )
        ) == normalize_css(fixed_css)


@pytest.mark.parametrize(
    "proxy_url, request_url, js, fixed_js",
    [
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            'var words = "/login/basename";',
            'var words = "http://localhost:8080/flows/1234/session/1234/auth/login/basename";',
        ),
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            "var words = '/login/basename';",
            "var words = 'http://localhost:8080/flows/1234/session/1234/auth/login/basename';",
        ),
    ],
)
def test_js_filter(proxy_url, request_url, js, fixed_js):
    assert (
        fix_javascript(proxy_url, request_url, dummy_proxy_configuration(), js)
        == fixed_js
    )


@pytest.mark.parametrize(
    "proxy_url, request_url, html, fixed_html",
    [
        (
            URL("http://localhost:8080/flows/1234/session/1234/auth"),
            URL("https://example.com/login/basename"),
            """
            <html>
                <head>
                    <link rel="stylesheet" href="/login/sheet.css">
                </head>
                <body>
                    <img src="/login/picture.png">
                    <script src="/login/script.js"></script>
                </body>
            </html>
            """,
            """
            <html>
                <head>
                    <link rel="stylesheet" href="http://localhost:8080/flows/1234/session/1234/auth/login/sheet.css">
                </head>
                <body>
                    <img src="http://localhost:8080/flows/1234/session/1234/auth/login/picture.png">
                    <script src="http://localhost:8080/flows/1234/session/1234/auth/login/script.js"></script>
                </body>
            </html>
            """,
        )
    ],
)
def test_html_bs4_filter(proxy_url, request_url, html, fixed_html):
    assert normalize_html(
        fix_html_bs4(proxy_url, request_url, dummy_proxy_configuration(), html)
    ) == normalize_html(fixed_html)
