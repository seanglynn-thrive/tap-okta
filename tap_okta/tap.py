"""okta tap class."""

from typing import List

from singer_sdk import Tap, Stream
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_okta.streams import (
    UsersStream
)

PLUGIN_NAME = "tap-okta"

STREAM_TYPES = [
    UsersStream
]


class Tapokta(Tap):
    """okta tap class."""
    name = "tap-okta"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key", th.StringType, required=True, default="***REMOVED***",
            description="The token to authenticate against the API service"
        ),
        th.Property(
            "api_url", th.StringType, default="***REMOVED***", # this
            description="The url for the API service"
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]

cli = Tapokta.cli


if __name__ == '__main__':
    cli()