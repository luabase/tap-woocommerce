"""REST client handling, including WooCommerceStream base class."""

import requests
import backoff
import logging
from typing import Any, Dict, Optional, cast

from singer_sdk.streams import RESTStream
from singer_sdk.authenticators import BasicAuthenticator


class WooCommerceStream(RESTStream):
    """WooCommerce stream class."""

    @property
    def url_base(self) -> str:
        """Return the API URL root, configurable via tap settings."""
        site_url = self.config["site_url"]
        return f"{site_url}/wp-json/wc/v3/"

    records_jsonpath = "$[*]"

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
        params: dict = {}
        params["per_page"] = 100
        params["order"] = "asc"
        if next_page_token:
            params["page"] = next_page_token
        if self.replication_key:
            start_date = self.get_starting_timestamp(context).replace(tzinfo=None)
            params["modified_after"] = start_date.isoformat()
            params["after"] = start_date.isoformat()
            params["date_query_column"] = "post_modified"

        return params


    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException),
        max_tries=5,
        factor=2,
    )
    def _request_with_backoff(
        self, prepared_request, context: Optional[dict]
    ) -> requests.Response:
        response = self.requests_session.send(prepared_request)
        if self._LOG_REQUEST_METRICS:
            extra_tags = {}
            if self._LOG_REQUEST_METRIC_URLS:
                extra_tags["url"] = cast(str, prepared_request.path_url)
            self._write_request_duration_log(
                endpoint=self.path,
                response=response,
                context=context,
                extra_tags=extra_tags,
            )
        if response.status_code in [401, 403, 404]:
            self.logger.info("Failed request for {}".format(prepared_request.url))
            self.logger.info(
                f"Reason: {response.status_code} - {str(response.content)}"
            )
            raise RuntimeError(
                "Requested resource was unauthorized, forbidden, or not found."
            )
        elif response.status_code >= 400:
            raise requests.exceptions.RequestException(
                f"Failed making request to API: {prepared_request.url} "
                f"[{response.status_code} - {str(response.content)}]".replace(
                    "\\n", "\n"
                )
            )
        logging.debug("Response received successfully.")
        return response