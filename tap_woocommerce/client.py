"""REST client handling, including WooCommerceStream base class."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Optional, cast

import backoff
import requests
from random_user_agent.user_agent import UserAgent
from singer_sdk.authenticators import BasicAuthenticator
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream
from singer_sdk.exceptions import FatalAPIError, RetriableAPIError

logging.getLogger("backoff").setLevel(logging.CRITICAL)


class WooCommerceStream(RESTStream):
    """WooCommerce stream class."""

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        site_url = self.config["site_url"]
        return f"{site_url}/wp-json/wc/v3/"

    def get_wc_version(self):
        status_url = f"{self.url_base}system_status"
        headers = self.http_headers
        headers.update(self.authenticator.auth_headers or {})
        try:
            result = self.requests_session.get(url=status_url, headers=headers)
            result_dict = result.json()
        except:
            return True
        if not result_dict.get("environment"):
            return True
        wc_version = result_dict["environment"].get("version")
        wc_version = ".".join(wc_version.split(".")[:-1])
        wc_version = float(wc_version)
        if wc_version >= 5.3:
            return True
        return False

    records_jsonpath = "$[*]"
    user_agents = UserAgent(software_engines="blink", software_names="chrome")
    new_version = None

    @property
    def authenticator(self) -> BasicAuthenticator:
        """Return a new authenticator object."""
        return BasicAuthenticator.create_for_stream(
            self,
            username=self.config.get("consumer_key"),
            password=self.config.get("consumer_secret"),
        )

    def get_next_page_token(
        self, response: requests.Response, previous_token: Optional[Any]
    ) -> Optional[Any]:
        """Return a token for identifying next page or None if no more pages."""
        # Get the total pages header
        total_pages = response.headers.get("X-WP-TotalPages")
        if response.status_code >= 400:
            total_pages = previous_token + 1

        if total_pages is None:
            return None

        if previous_token is None:
            return 2

        if int(total_pages) > previous_token:
            return previous_token + 1

        return None

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization."""

        if self.new_version == None:
            self.new_version = self.get_wc_version()

        params: dict = {}
        params["per_page"] = 100
        params["order"] = "asc"
        if next_page_token:
            params["page"] = next_page_token
        if self.replication_key:
            self.start_date = self.get_starting_timestamp(context).replace(tzinfo=None)
            if self.new_version:
                params["modified_after"] = self.start_date.isoformat()
            else:
                lookup_days = self.config.get("check_modify_date", 60)
                params["after"] = (self.start_date - timedelta(days=lookup_days)).isoformat()
        return params

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result rows."""
        if response.status_code >= 500 and self.config.get("ignore_server_errors"):
            return []
        if self.replication_key and not self.new_version:
            for record in extract_jsonpath(
                self.records_jsonpath, input=response.json()
            ):
                record_mod_date = datetime.strptime(
                    record[self.replication_key], "%Y-%m-%dT%H:%M:%S"
                )
                if record_mod_date > self.start_date:
                    yield record
        else:
            yield from extract_jsonpath(self.records_jsonpath, input=response.json())

    @property
    def http_headers(self) -> dict:
        """Return headers dict to be used for HTTP requests."""
        result = self._http_headers
        result["Content-Type"] = "application/json"
        result["User-Agent"] = self.user_agents.get_random_user_agent().strip()
        return result

    def validate_response(self, response: requests.Response) -> None:
        """Validate HTTP response."""
        if response.status_code >= 500 and self.config.get("ignore_server_errors"):
            pass
        elif 500 <= response.status_code < 600 or response.status_code in [429]:
            msg = (
                f"{response.status_code} Server Error: "
                f"{response.reason} for path: {self.path}"
            )
            raise RetriableAPIError(msg)
        elif 400 <= response.status_code < 500:
            msg = (
                f"{response.status_code} Client Error: "
                f"{response.reason} for path: {self.path}"
            )
            raise FatalAPIError(msg)
