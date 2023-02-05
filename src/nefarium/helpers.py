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

import contextvars
import functools
from asyncio import events
from collections import OrderedDict
from concurrent.futures import Executor, ThreadPoolExecutor
from logging import getLogger
from os import environ
from urllib.parse import urlparse

import bs4
import cssutils
import httpx
import yarl

logger = getLogger(__name__)


# for performance reasons, we want more than one executor
executors = {}


def make_async(func, *, name: str = "", create_local_executor: bool = False):
    """
    Make an async function from a callable.
    :param create_local_executor: If True, create a local executor for the function.
    :param name: An optional name for the executor.
    :param func: The callable to make the async function from.
    :return: A function that returns a coroutine to call the callable.
    """

    # stolen from authcaptureproxy
    unknown_name = repr(func)
    if name:
        name = name
    else:
        try:
            # get function name
            name = func.__name__
        except AttributeError:
            # check partial
            try:
                name = func.func.__name__  # type: ignore[attr-defined]
            except AttributeError:
                # unknown
                name = unknown_name

    current_executor: None | Executor = None
    if create_local_executor:
        if name in executors:
            current_executor = executors[name]
        else:
            current_executor = ThreadPoolExecutor(thread_name_prefix=f"{name}-")
            executors[name] = current_executor

    async def async_func(*args, **kwargs):
        loop = events.get_running_loop()
        ctx = contextvars.copy_context()
        func_call = functools.partial(ctx.run, func, *args, **kwargs)
        return await loop.run_in_executor(current_executor, func_call)

    return async_func


def truthy_string(value: str) -> str | None:
    return value if value else None


class LimitedSizeDict(OrderedDict):
    # https://stackoverflow.com/questions/2437617/how-to-limit-the-size-of-a-dictionary
    def __init__(self, *args, **kwargs):
        self.size_limit = kwargs.pop("size_limit", None)
        super().__init__(*args, **kwargs)
        self._check_size_limit()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._check_size_limit()

    def update(self, __m, **kwargs) -> None:  # type: ignore
        super().update(__m, **kwargs)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)


def is_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all(
            [
                result.path or result.netloc,
                result.scheme or yarl.URL(value).is_absolute(),
            ]
        )
    except ValueError:
        return False


def httpx_to_yarl(url: httpx.URL) -> yarl.URL:
    assert is_url(str(url))
    return yarl.URL(str(url))


def debug() -> bool:
    return truthy_string(environ.get("NEFARIUM_DEBUG", "")) is not None


IS_DEBUG = debug()


def normalize_css(css: str) -> str:
    try:
        return cssutils.parseString(css).cssText.decode("utf-8").strip()
    except Exception as e:
        logger.warning(f"Failed to normalize CSS: {e}")
        return css


def wrap_css_inline(css: str) -> str:
    return normalize_css("*{" + css + "}")


def unwrap_css_inline(css: str) -> str:
    return (
        normalize_css(css)
        .removeprefix("* {\n")
        .removesuffix("    }")
        .replace("\n", " ")
        .strip()
    )  # arbitrary


def normalize_html(html: str) -> str:
    return bs4.BeautifulSoup(html, "html.parser").prettify()


__all__ = (
    "LimitedSizeDict",
    "truthy_string",
    "is_url",
    "IS_DEBUG",
    "httpx_to_yarl",
    "make_async",
    "normalize_css",
    "wrap_css_inline",
    "unwrap_css_inline",
    "normalize_html",
)
