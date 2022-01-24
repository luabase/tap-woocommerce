# tap-woocommerce

[Singer](https://www.singer.io/) tap that extracts data from a [WooCommerce](https://woocommerce.com/) shop and produces JSON-formatted data following the [Singer spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

Built with the [Meltano Tap SDK](https://sdk.meltano.com) for Singer Taps.

```bash
$ mkvirtualenv -p python3 tap-woocommerce
$ pip install git+https://github.com/hotgluexyz/tap-woocommerce.git
$ tap-woocommerce --config config.json --discover
$ tap-woocommerce --config config.json --catalog catalog.json --state state.json
```

# Quickstart

## Install the tap

```
> pip install git+https://github.com/hotgluexyz/tap-woocommerce.git
```

## Create a Config file

```
{
  "site_url": "https://example.com",
  "consumer_key": "ck_woocommerce",
  "consumer_secret": "cs_woocommerce",
  "start_date": "2018-01-08T00:00:00Z"
}
```

The `consumer_key` and `consumer_secret` keys are generated from within WooCommerce settings > Advanced > REST API > API Keys. [Learn more on the WooCommerce docs](https://woocommerce.github.io/woocommerce-rest-api-docs/#rest-api-keys)

The `site_url` should be the URL of the WordPress site containing your WooCommerce shop.

The `start_date` is used by the tap as a bound on SOQL queries when searching for records.  This should be an [RFC3339](https://www.ietf.org/rfc/rfc3339.txt) formatted date-time, like "2018-01-08T00:00:00Z". For more details, see the [Singer best practices for dates](https://github.com/singer-io/getting-started/blob/master/BEST_PRACTICES.md#dates).

## Run Discovery

To run discovery mode, execute the tap with the config file.

```
> tap-woocommerce --config config.json --discover > catalog.json
```

## Sync Data

To sync data, select fields in the `catalog.json` output and run the tap.

```
> tap-woocommerce --config config.json --catalog catalog.json [--state state.json]
```
