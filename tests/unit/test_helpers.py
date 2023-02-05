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

import httpx
import pytest
import yarl

from nefarium import *


@pytest.mark.asyncio
async def test_make_async():
    assert await make_async(lambda: 1)() == 1


@pytest.mark.parametrize(
    "value, none",
    [
        ("", True),
        (" ", False),
        ("a", False),
        ("1", False),
        ("True", False),
        ("true", False),
        ("False", False),
    ],
)
def test_truthy_string(value: str, none: bool):
    assert (
        truthy_string(value) is not none if not none else truthy_string(value) is None
    )


def test_limited_size_dict_popout():
    limited_size_dict = LimitedSizeDict(size_limit=2)
    limited_size_dict["a"] = 1
    limited_size_dict["b"] = 2
    limited_size_dict["c"] = 3
    assert "a" not in limited_size_dict


def test_limited_size_dict_size():
    limited_size_dict = LimitedSizeDict(size_limit=2)
    limited_size_dict["a"] = 1
    limited_size_dict["b"] = 2
    limited_size_dict["c"] = 3
    assert len(limited_size_dict) == 2


@pytest.mark.parametrize(
    "url, result",
    [
        ("https://google.com", True),
        ("http://google.com:12312", True),
        ("http://google.com/", True),
        ("http://google.com/whatever", True),
        ("http://google.com/whatever?with=parameters", True),
        ("/test/", True),
        ("/test", True),
        (":::::", False),
        ("hello", False),
        ("^The.*Spain$", False),
        ("things${thing}", False),
        ("yeah{yeah}", False),
    ],
)
def test_is_url(url: str, result: bool):
    assert is_url(url) == result


@pytest.mark.parametrize(
    "httpx_url, yarl_url",
    [
        (httpx.URL("https://google.com"), yarl.URL("https://google.com")),
        (httpx.URL("http://google.com:12312"), yarl.URL("http://google.com:12312")),
        (httpx.URL("http://google.com/"), yarl.URL("http://google.com/")),
        (
            httpx.URL("http://google.com/whatever"),
            yarl.URL("http://google.com/whatever"),
        ),
        (
            httpx.URL("http://google.com/whatever?with=parameters"),
            yarl.URL("http://google.com/whatever?with=parameters"),
        ),
    ],
)
def test_httpx_to_yarl(httpx_url: httpx.URL, yarl_url: yarl.URL):
    assert httpx_to_yarl(httpx_url) == yarl_url


def test_debug():
    assert not IS_DEBUG


@pytest.mark.parametrize(
    "css_in, css_out",
    [
        (
            "*{   left:3;}",
            "* {\n    left: 3\n    }",
        ),
        (
            "*{ left:3        \n\n}",
            "* {\n    left: 3\n    }",
        ),
        # idk whatever
    ],
)
def test_normalize_css(css_in, css_out):
    assert normalize_css(css_in) == css_out


def test_normalize_html():
    html = """<html><head><title>The Dormouse's story</title></head>
    <body>
    <p class="title"><b>The Dormouse's story</b></p>
    
    <p class="story">Once upon a time there were three little sisters; and their names were
    <a href="http://example.com/elsie" class="sister" id="link1">Elsie</a>,
    <a href="http://example.com/lacie" class="sister" id="link2">Lacie</a> and
    <a href="http://example.com/tillie" class="sister" id="link3">Tillie</a>;
    and they lived at the bottom of a well.</p>
    
    <p class="story">...</p>
    """

    normal_html = """<html>
 <head>
  <title>
   The Dormouse's story
  </title>
 </head>
 <body>
  <p class="title">
   <b>
    The Dormouse's story
   </b>
  </p>
  <p class="story">
   Once upon a time there were three little sisters; and their names were
   <a class="sister" href="http://example.com/elsie" id="link1">
    Elsie
   </a>
   ,
   <a class="sister" href="http://example.com/lacie" id="link2">
    Lacie
   </a>
   and
   <a class="sister" href="http://example.com/tillie" id="link3">
    Tillie
   </a>
   ;
    and they lived at the bottom of a well.
  </p>
  <p class="story">
   ...
  </p>
 </body>
</html>"""

    assert normalize_html(html) == normal_html
