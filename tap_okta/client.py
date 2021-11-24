import requests
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Iterable
import copy

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

    def get_url(self, context: Optional[dict]) -> str:
        url = "".join([self.url_base, self.path or ""])
        vals = copy.copy(dict(self.config))
        vals.update(context or {})

        for k, v in vals.items():
            search_text = "".join(["{", k, "}"])
            if search_text in url:
                url = url.replace(search_text, self._url_encode(v))
        return url


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
        self,
        context: Optional[dict],
        next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}
        params["limit"] = self.limit
        if next_page_token:
            params["page"] = next_page_token
        if self.replication_key:
            params["sort"] = "asc"
            params["order_by"] = self.replication_key
        return params

    def request_records(self, context: Optional[dict]) -> Iterable[dict]:
        """Request records from REST endpoint(s), returning response records.

		If pagination is detected, pages will be recursed automatically.

		Args:
			context: Stream partition or context dictionary.

		Yields:
			An item for every record in the response.

		Raises:
			RuntimeError: If a loop in pagination is detected. That is, when two
				consecutive pagination tokens are identical.
		"""
        next_page_token: Any = None
        finished = False
        decorated_request = self.request_decorator(self._request)

        while not finished:
            prepared_request = self.prepare_request(
                context, next_page_token=next_page_token
            )
            resp = decorated_request(prepared_request, context)
            for row in self.parse_response(resp):
                yield row
            previous_token = copy.deepcopy(next_page_token)
            next_page_token = self.get_next_page_token(
                response=resp, previous_token=previous_token
            )
            if next_page_token and next_page_token == previous_token:
                raise RuntimeError(
                    f"Loop detected in pagination. "
                    f"Pagination token {next_page_token} is identical to prior token."
                )
            # Cycle until get_next_page_token() no longer returns a value
            finished = not next_page_token