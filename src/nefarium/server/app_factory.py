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

from aiohttp.web import Application
from aiohttp_session import setup as setup_session

from .db import *
from .routes import *
from ..helpers import LimitedSizeDict

logger = getLogger(__name__)


async def app_factory() -> Application:
    app = Application()
    setup_session(app, await get_cookie_storage(cookie_name="__nefarium_session"))

    app["db_client"] = get_async_database_client()
    app["db"] = get_database(app["db_client"])

    # can't store these in db because they can't be serialized, and I imagine they are also big in memory
    app["auth_capture_proxies"] = LimitedSizeDict(size_limit=200)

    app.add_routes(routes)

    return app


__all__ = ("app_factory",)
