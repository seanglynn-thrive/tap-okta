"""REST client handling, including oktaStream base class."""

import requests
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable

from memoization import cached

from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import APIKeyAuthenticator


SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class oktaStream(RESTStream):
    """okta stream class."""
    limit: int = 10
    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return self.config["api_url"]

    records_jsonpath = "$[*]"  # Or override `parse_response`.
    next_page_token = True

    @property
    def authenticator(self) -> APIKeyAuthenticator:
        """Return a new authenticator object."""
        return APIKeyAuthenticator.create_for_stream(
            self,
            key="apikey",
            value=self.config.get("api_key"),
            location="header"
        )

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers = {}
        headers["Authorization"] = "SSWS " + self.config.get("api_key")
        return headers

    def get_next_page_token(
            self,
            response: requests.Response,
            previous_token: Optional[Any]
        ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        response_links = requests.utils.parse_header_links(response.headers['Link'].rstrip('>').replace('>,<', ',<'))
        for link in response_links:
            if link['rel'] == 'next':
                next_page_token = link['url']
            else:
                next_page_token = None
        return next_page_token


    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        if next_page_token:
            params["page"] = next_page_token
        if self.replication_key:
            params["sort"] = "asc"
            params["order_by"] = self.replication_key
        return params


    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        # TODO: Parse response body and return a set of records.
        yield from extract_jsonpath(self.records_jsonpath, input=response.json())
