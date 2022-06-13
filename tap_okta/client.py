"""okta tap stream classes."""

import requests
from pathlib import Path
from typing import Any, Dict, Optional, Iterable
import copy
from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import APIKeyAuthenticator
from urllib.parse import urlparse, parse_qs
import logging
from urllib import parse
from tap_okta import utils

logger = logging.getLogger("okta_client")
OKTA_TS_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class oktaStream(RESTStream):
    """okta stream class."""

    limit: int = 1000
    page_cnt: int = 1

    next_page_token: Optional[str] = None
    previous_token: Optional[str] = None

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        return self.config["api_url"]

    @property
    def authenticator(self) -> APIKeyAuthenticator:
        """Return a new authenticator object."""
        api_key = self.config.get("api_key")
        if isinstance(api_key, str):
            auth = APIKeyAuthenticator.create_for_stream(
                self, key="apikey", value=api_key, location="header"
            )
        else:
            raise Exception("Cannot find 'api_key' in config!")
        return auth

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed."""
        headers: dict = {}
        api_key = self.config.get("api_key")

        if isinstance(api_key, str):
            headers["Authorization"] = "SSWS " + api_key
        else:
            raise Exception("Cannot find 'api_key' in config!")

        return headers

    def parse_okta_page_code(self, next_page_url):
        """Parse next page token from next_page_url and return code."""
        self.logger.info(f"Beginning okta page code parse from url: {next_page_url}")
        o = urlparse(next_page_url)
        query = parse_qs(o.query)
        self.logger.info(f"Parsing okta_page query: {query}")
        # Retrieve okta next_page_value value
        after_param = query["after"].pop()
        self.logger.info(f"Parsed page code {after_param}")
        return after_param

    def get_incremental_request_param(
        self, params: dict, ts_val: str
    ) -> Dict[str, Any]:
        """Append params with incremental load query filter."""
        incremental_column = self.replication_key
        filter_value = '{0}+gt+"{1}"'.format(incremental_column, ts_val)
        params["filter"] = filter_value

        payload_str = parse.urlencode(params, safe=":+")
        params = parse.parse_qs(payload_str)
        self.logger.info(f"Returning params with incremental filter:\n{params}")
        return params

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""
        params: dict = {}

        params["limit"] = self.limit

        # If incremental load value is set im Meltano state
        incremental_val = self.get_starting_timestamp(context)

        # If context dict exists and next_page_token value exists
        if context and next_page_token is not None:
            self.logger.info(f"next_page_token is available in context: {context}")
            params["page"] = next_page_token
            params["after"] = self.parse_okta_page_code(next_page_token)
        # If replication key is set + incremental value is retrieved from meltano state
        if self.replication_key and incremental_val:
            params["sort"] = "asc"
            params["order_by"] = self.replication_key
            params["format"] = "json"

            # Validate meltano ts
            utils.validate_datetime(incremental_val)
            # Format meltano ts -> Okta ts
            formatted_incremental_val = utils.reformat_datetime(
                incremental_val, utils.TS_FORMAT, OKTA_TS_FORMAT
            )

            # Appending params with incremental load query filter
            params = self.get_incremental_request_param(
                params, formatted_incremental_val
            )

        self.logger.info(f"get_url_params ({self.page_cnt}) context: {context}")
        self.logger.info(f"get_url_params ({self.page_cnt}) params: {params}")
        self.logger.info(
            f"get_url_params ({self.page_cnt}) next_page_token: {next_page_token}"
        )

        return params

    def request_records(self, context: Optional[dict]) -> Iterable[dict]:
        """Request records from REST endpoint(s), returning response records.

        If pagination is detected, pages will be recursed automatically.

        Args:
            context: Stream partition or context dictionary.

        Yields
            An item for every record in the response.

        Raises
            RuntimeError: If a loop in pagination is detected. That is, when two
                consecutive pagination tokens are identical.
        """
        # Init empty context dict if not exists
        context = context if context else {}

        finished = False
        while not finished:
            # time.sleep(5)
            decorated_request = self.request_decorator(self._request)
            self.logger.info(f"\n======PAGE {self.page_cnt}======")

            prepared_request = self.prepare_request(
                context=context, next_page_token=self.next_page_token
            )
            self.logger.info(f"prepared_request.url: {prepared_request.url}")
            self.logger.info(f"prepared_request.path_url: {prepared_request.path_url}")
            self.logger.debug(f"prepared_request.hooks: {prepared_request.hooks}")
            self.logger.debug(f"prepared_request.headers: {prepared_request.headers}")

            resp = decorated_request(prepared_request, context)
            self.logger.info(f"Response status: {resp.status_code}")

            for row in self.parse_response(resp):
                yield row

            self.previous_token = copy.copy(self.next_page_token)
            context["previous_token"] = self.next_page_token
            self.logger.info(f"previous_token: {self.previous_token}")

            self.next_page_token = self.get_next_page_token(
                response=resp, previous_token=self.previous_token
            )
            context["next_page_token"] = self.next_page_token
            self.logger.info(f"next_page_token: {self.next_page_token }")

            self.logger.info(
                f"Validating next_page_token: if {self.next_page_token} == {self.previous_token}"
            )
            # time.sleep(5)
            if self.next_page_token and self.next_page_token == self.previous_token:
                raise RuntimeError(
                    f"Loop detected in pagination."
                    f"Pagination token {self.next_page_token } is identical to prior token."
                )
            # Cycle until get_next_page_token() no longer returns a value
            finished = not self.next_page_token
            self.page_cnt += 1

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Any:
        """Return token identifying next page or None if all records have been read.

        Args:
            response: A raw `requests.Response`_ object.
            previous_token: Previous pagination reference.

        Returns
            Reference value to retrieve next page.

        .. _requests.Response:
            https://docs.python-requests.org/en/latest/api/#requests.Response
        """
        """Return a token for identifying next page or None if no more pages."""

        resp_header = response.headers["Link"]
        response_links = requests.utils.parse_header_links(resp_header)
        self.logger.info(f" [{self.page_cnt}] response_links: {response_links}")
        for link in response_links:
            if link["rel"] == "next":
                self.logger.debug(f" [{self.page_cnt}] link['rel'] == 'next'")
                next_page_token = link["url"]
            else:
                self.logger.debug(f" [{self.page_cnt}] link['rel'] != 'next'")
                next_page_token = None
        self.logger.info(
            f" [{self.page_cnt}] RETURNING next_page_token: {next_page_token}"
        )
        return next_page_token
