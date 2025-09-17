"""WooCommerce tap class."""

from typing import List

from singer_sdk import Stream, Tap
from singer_sdk import typing as th  # JSON schema typing helpers

from tap_woocommerce.streams import (
    WooCommerceStream,
    ProductsStream,
    OrdersStream,
    CouponsStream,
    ProductVarianceStream,
    SubscriptionStream,
    CustomersStream,
    StoreSettingsStream,
    OrderNotesStream,
)

STREAM_TYPES = [
    ProductsStream,
    OrdersStream,
    CouponsStream,
    ProductVarianceStream,
    SubscriptionStream,
    CustomersStream,
    StoreSettingsStream,
    OrderNotesStream,
]

import logging


class TapWooCommerce(Tap):
    """WooCommerce tap class."""

    name = "tap-woocommerce"

    config_jsonschema = th.PropertiesList(
        th.Property("consumer_key", th.StringType, required=True),
        th.Property("consumer_secret", th.StringType, required=True),
        th.Property("site_url", th.StringType, required=True),
        th.Property("start_date", th.DateTimeType, default="2000-01-01T00:00:00.000Z"),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        available_streams = []
        for stream_class in STREAM_TYPES:
            # check that endpoint exists
            stream = stream_class(tap=self)
            if stream.check_endpoint_exists():
                available_streams.append(stream)
            else:
                logging.info(
                    f"Endpoint {stream_class.name} is not available for this store, skipping."
                )
        return available_streams


if __name__ == "__main__":
    TapWooCommerce.cli()
