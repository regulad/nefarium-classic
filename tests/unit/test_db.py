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

from os import environ

import pytest

from nefarium.server import *


def test_sync_db():
    environ["NEFARIUM_MONGO_URI"] = "mongodb://localhost:27018"
    environ["NEFARIUM_MONGO_DB"] = "nefarium2"

    client = get_sync_database_client()
    database = get_database(client)

    # assert client.__init_kwargs["host"] == "mongodb://localhost:27018"
    # this is obscured by pymongo, so this is "real useful"
    assert database.name == "nefarium2"


@pytest.mark.asyncio
async def test_async_db():
    environ["NEFARIUM_MONGO_URI"] = "mongodb://localhost:27018"
    environ["NEFARIUM_MONGO_DB"] = "nefarium2"

    client = get_async_database_client()
    database = get_database(client)

    # assert client.__init_kwargs["host"] == "mongodb://localhost:27018"
    # this is obscured by pymongo, so this is "real useful"
    assert database.name == "nefarium2"
