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
from logging import getLogger
from typing import TypedDict, Literal, NotRequired

from bson import ObjectId

logger = getLogger(__name__)


class AuthGoals(TypedDict):
    """
    AuthGoals is a TypedDict that represents the goals of an auth flow.
    """

    goal_urls: list[str]
    # a list of URLs the user should have navigated to, or a regex to match against
    # if empty, checks will be run on all pages.
    # if a URL is relative, the path will be compared

    return_body_requires_type: Literal["regex"] | Literal[
        "json"
    ] | None  # type of body to check
    return_body_requires_json_schema: str | dict | None  # JSONSCHEMA, only applies to "json" type
    # JSON schema to match against, if true, entire JSON will be passed
    return_body_requires_regex: str | None  # only applies to "regex" type

    required_cookies: list[str]  # list of required cookies present in the request
    required_cookies_regex: dict[str, str | None]  # regex to match against

    required_headers: list[str]  # list of required headers present in the request
    required_headers_regex: dict[str, str | None]  # regex to match against

    required_query_params: list[
        str
    ]  # list of required query parameters present in the request
    required_query_params_regex: dict[str, str | None]  # regex to match against

    status_codes: list[int]  # list of valid status codes

    # the `code` sent back to the client as a query parameter to the redirect_uri is UTF-8 Base64 encoded JSON with the following keys:
    # - status: int | undefined
    #   the status code of the response, or undefined if no status_codes are specified or if only one is
    # - cookies: object | undefined
    #   an object containing the cookies in required_cookies and their values
    # - query: object | undefined
    #   an object containing the query parameters in required_query_params and their values
    # - body: string | null | undefined
    #   the body of the response that matched the regex, if type is "regex"
    #   the ENTIRE body of the response
    # - json: object | null | undefined
    #   the body of the response that matched the JSON definition, if type is "json"
    #   the ENTIRE body of the response
    # - headers: object | undefined
    #   an object containing the RESPONSE headers in required_headers and their values
    # The Redirect URI will be redirected to when all of declared criteria are met.


class Flow(TypedDict):
    """
    Flow is a TypedDict that represents an auth flow.
    """

    _id: ObjectId
    name: str
    description: NotRequired[str]
    redirect_uri_domains: list[str]
    proxy_target: str
    auth_goals: NotRequired[AuthGoals]
    request_proxy: NotRequired[str]
    filter_response: bool  # whether to filter the response body
    redirect_code: NotRequired[bool]


class Session(TypedDict):
    """
    Session is a TypedDict that represents a session.
    """

    _id: ObjectId
    flow_id: ObjectId
    state: str
    redirect_uri: str
    ip_address: str
    auth_data: dict[str, str] | None
    state_data: NotRequired[str]
    created_at: datetime


__all__ = ("Flow", "Session", "AuthGoals")
