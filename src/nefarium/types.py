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
from typing import TypedDict

from bson import ObjectId

logger = getLogger(__name__)


class Flow(TypedDict):
    _id: ObjectId
    name: str
    description: str | None
    redirect_url_domains: list[str]
    proxy_target: str
    auth_data_goals: dict[str, str]  # TODO


class Session(TypedDict):
    _id: ObjectId
    flow_id: ObjectId
    state: str
    redirect_url: str
    auth_data: dict[str, str] | None
    ip_address: str


__all__ = ("Flow", "Session")
