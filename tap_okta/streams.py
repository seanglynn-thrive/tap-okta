"""Stream type classes for tap-okta."""

from pathlib import Path
#from typing import Any, Dict, Optional, Union, List, Iterable
#from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_okta.client import oktaStream

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class UsersStream(oktaStream):
    name = "users"
    path = "/users"
    primary_keys = ["id"]
    schema_filepath = SCHEMAS_DIR / "users.json"
