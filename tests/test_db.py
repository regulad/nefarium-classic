from os import environ
from nefarium import *


def test_environment_variable_reading():
    environ["NEFARIUM_MONGO_URI"] = "mongodb://localhost:27018"
    environ["NEFARIUM_MONGO_DB"] = "nefarium2"

    client = get_sync_database_client()
    database = get_database(client)

    # assert client.__init_kwargs["host"] == "mongodb://localhost:27018"
    # this is obscured by pymongo, so this is "real useful"
    assert database.name == "nefarium2"
