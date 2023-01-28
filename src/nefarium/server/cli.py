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

from argparse import ArgumentParser
from logging import getLogger
from urllib.parse import urlparse

from .db import get_sync_database_client, get_database
from ..types import Flow

logger = getLogger(__name__)


def cli() -> None:
    parser = ArgumentParser(
        prog="nefarium",
        description=(
            "nefarium  Copyright (C) 2023  Parker Wahle"
            "This program comes with ABSOLUTELY NO WARRANTY"
            "This is free software, and you are welcome to redistribute it"
            "under certain conditions"
        ),
    )

    parser.add_argument(
        "-U",
        "--uri",
        type=str,
        help="URI of the MongoDB database to connect to",
        dest="uri",
    )

    parser.add_argument(
        "-D",
        "--database",
        type=str,
        help="Database of the MongoDB database to utilize",
        dest="database",
    )

    args = parser.parse_args()

    uri: str | None = args.uri

    client = get_sync_database_client(uri=uri)

    database = get_database(client, db=args.database)

    print(f"Connected to {database.name} on {client.address}")
    print()
    print(
        "Nefarium will guide you through the process of creating a new flow. "
        "Existing flows can be edited with a MongoDB tool such as MongoDB Compass."
    )
    print()
    name: str  # guaranteed to be set
    while True:
        print("What is the name of the flow?")
        name = input("> ")
        if name:
            break
        else:
            continue
    print()
    print("What is the description of the flow? (optional)")
    description = input("> ")
    print()
    redirect_url_domains = []
    while True:
        print(
            "Add a valid redirect URL domain. Use * to specify a wildcard. Press enter to finish."
        )
        redirect_uri_domain = input("> ")
        if redirect_uri_domain:
            try:
                clean_domain = urlparse(redirect_uri_domain.lower().strip()).netloc
            except ValueError:
                print("Could not decompose URL! Enter again.")
                continue
            if (
                "*" in redirect_uri_domain or "localhost" in redirect_uri_domain
            ):  # tend to get a little mashed
                redirect_url_domains.append(redirect_uri_domain)
            else:
                redirect_url_domains.append(clean_domain)
        else:
            if len(redirect_url_domains) > 0:
                break
            else:
                print(
                    'You must add at least one redirect URL domain! Try "localhost" for testing.'
                )
                continue
    print()
    proxy_target: str  # guaranteed to be set
    while True:
        print("What URL should be proxied?")
        proxy_url = input("> ")
        if proxy_url:
            try:
                parsed = urlparse(proxy_url.lower().strip())
                cleaned = parsed.geturl()
                if parsed.scheme and parsed.netloc:
                    if bool(
                        input(f'Recieved "{cleaned}", is this correct? [y/N] ')
                        .lower()
                        .strip()
                        == "y"
                    ):
                        proxy_target = cleaned
                        break
                    else:
                        continue
                else:
                    raise ValueError
            except ValueError:
                print("Could not decompose URL! Enter again.")
                continue
    print()
    # TODO: ask what should be gathered from proxy request
    print()
    request_proxy: str | None  # guaranteed to be set
    while True:
        print("Do you have a proxy to use? [y/N]")
        if bool(input("> ").lower().strip() == "y"):
            print("What is the proxy URL?")
            proxy_url = input("> ")
            if proxy_url:
                try:
                    parsed = urlparse(proxy_url.lower().strip())
                    cleaned = parsed.geturl()
                    if parsed.scheme and parsed.netloc:
                        if bool(
                            input(f'Recieved "{cleaned}", is this correct? [y/N] ')
                            .lower()
                            .strip()
                            == "y"
                        ):
                            request_proxy = cleaned
                            break
                        else:
                            continue
                    else:
                        raise ValueError
                except ValueError:
                    print("Could not decompose URL! Enter again.")
                    continue
            else:
                print("You must enter a proxy URL!")
                continue
        else:
            request_proxy = None
            break
    print()
    final_dict: Flow = {  # type: ignore
        "name": name,
        "description": description,
        "redirect_url_domains": redirect_url_domains,
        "proxy_target": proxy_target,
        "request_proxy": request_proxy,
        "auth_data_goals": {},  # TODO: add auth data goals
    }
    print("Final flow:")
    print(final_dict)
    print()
    if bool(input("Is this correct? [y/N] ").lower().strip() == "y"):
        print("Creating flow...")
        result = database.flows.insert_one(final_dict)
        print(f"Flow created! ID: {result.inserted_id}")
    else:
        print("Flow creation cancelled.")
        exit(1)


if __name__ == "__main__":
    cli()  # mainly for testing

__all__ = ("cli",)
