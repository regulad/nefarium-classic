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

from collections import OrderedDict
from logging import getLogger
from os import environ

import httpx
import yarl

logger = getLogger(__name__)


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
    from urllib.parse import urlparse

    try:
        result = urlparse(value)
        return all([result.path, result.scheme or result.query])
    except ValueError:
        return False


def httpx_to_yarl(url: httpx.URL) -> yarl.URL:
    assert is_url(str(url))
    return yarl.URL(str(url))


def debug() -> bool:
    return truthy_string(environ.get("NEFARIUM_DEBUG", "")) is not None


IS_DEBUG = debug()


def fast() -> bool:
    return truthy_string(environ.get("NEFARIUM_FAST", "")) is not None


IS_SLOW = not fast()

__all__ = (
    "LimitedSizeDict",
    "truthy_string",
    "is_url",
    "IS_DEBUG",
    "httpx_to_yarl",
    "IS_SLOW",
)
