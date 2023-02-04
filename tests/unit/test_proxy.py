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

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from yarl import URL

from nefarium.server import create_proxy, get_database

from . import *


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the session instead of each test case.
    Required for using pytest-motor properly.
    :return: The event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_proxy_creation(motor_client: AsyncIOMotorClient):
    database = get_database(motor_client)

    proxy = create_proxy(
        dummy_flow(),
        dummy_session(),
        URL("http://localhost:8080/flows/1234/sessions/1234/auth"),
        database["sessions"],  # type: ignore
    )

    assert proxy is not None
    assert len(proxy.tests.items()) > 0
    assert len(proxy.modifiers.items()) > 0
