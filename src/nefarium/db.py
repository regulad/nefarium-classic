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
from typing import overload

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
)
from pymongo import MongoClient
from pymongo.database import Database


def _get_database_uri(uri: str | None = None) -> str:
    return uri or environ.get("NEFARIUM_MONGO_URI") or "mongodb://localhost:27017"


def get_sync_database_client(*, uri: str | None = None) -> MongoClient:
    return MongoClient(_get_database_uri(uri))


def get_database_client(*, uri: str | None = None) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(_get_database_uri(uri))



@overload
def get_database(client: MongoClient) -> Database:
    ...

@overload
def get_database(client: AsyncIOMotorClient) -> AsyncIOMotorDatabase:
    ...

@overload
def get_database(client: MongoClient, *, db: str) -> Database:
    ...
    
@overload
def get_database(client: AsyncIOMotorClient, *, db: str) -> AsyncIOMotorDatabase:
    ...

def get_database(
    client: AsyncIOMotorClient | MongoClient, *, db: str | None = None
) -> AsyncIOMotorDatabase | Database:
    db = db or environ.get("NEFARIUM_MONGO_DB") or "nefarium"

    return client[db]


__all__ = ("get_database_client", "get_sync_database_client", "get_database")
