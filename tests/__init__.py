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

from datetime import datetime

from bson import ObjectId

from nefarium import AuthGoals, Flow, Session, ProxyConfiguration


def dummy_auth_goals() -> AuthGoals:
    return {
        "goal_urls": ["/goal"],
        "return_body_requires_type": None,
        "return_body_requires_json_schema": None,
        "return_body_requires_regex": None,
        "required_cookies": [],
        "required_cookies_regex": {},
        "required_headers": [],
        "required_headers_regex": {},
        "required_query_params": [],
        "required_query_params_regex": {},
        "status_codes": [200],
    }


def dummy_proxy_configuration() -> ProxyConfiguration:
    return dummy_flow()["proxy_configuration"]


def dummy_flow() -> Flow:
    return {
        "_id": ObjectId("1" * 24),
        "name": "Test Flow",
        "description": "This is a test flow.",
        "redirect_uri_domains": ["*"],
        "auth_goals": dummy_auth_goals(),
        "proxy_configuration": {
            "filtering": {
                "html": True,
                "css": True,
                "js": True,
            },
            "target": "https://example.com",
            "proxy_cdns": True,
            "request_proxies": {},
        },
    }


def dummy_session() -> Session:
    return {
        "_id": ObjectId("0" * 24),
        "flow_id": ObjectId("1" * 24),
        "state": "pending",
        "redirect_uri": "https://example.com/redirect",
        "ip_address": "123.123.123.231",
        "auth_data": None,
        "created_at": datetime.utcnow(),
    }


__all__ = (
    "dummy_auth_goals",
    "dummy_flow",
    "dummy_session",
    "dummy_proxy_configuration",
)
