# Catalog Importer

The target audience for this script is AEs, SAs, CSMs, etc. to load custom products, product categories, and variants using custom data in a flat csv file (template found at `./example_catalog.csv`)

## Important disclaimer

All code samples in this repository show examples of how to accomplish certain use cases. We will use our best effort to maintain these examples, but occasionally some items may break. If you notice a broken code sample, please open an issue to let us know something is broken, or alternatively submit a PR with a proposed fix.

## Version

- SDK version: 4.0.0
- API revision: 2023-07-15

## Limitations

_Known limitations that will want enhancements before porting to labs_

- Assumes the data in the flat file is correct with no real safe guards against "bad" data. Not a production-level ETL, but ready to demo.
- Will create categories but not update not delete them.
- Will create and update products and variants but will not delete them.
- Will _not_ explicitly reassign variant/parent relationships.
- Will import main image i.e. `image_full_url` (both at the parent and variable level unless specific value provided for variant level `image_full_url`) but no additional images yet.
- Will import main price i.e. `price` (both at the parent and variable level unless specific value provided for variant level `price`)
- Does not use bulk jobs but rather one-off API requests. Data set should be limited (could easily handle 1000+ lines, but _not_ tested against the 100,000+)

## Usage

- Run `pip install klaviyo-api` to get the [Klaviyo SDK for Python](https://github.com/klaviyo/klaviyo-api-python)
- Use sample excel to build a list of catalog items (with variants) in a flat, csv structure.
- Add `KLAVIYO_PRIVATE_KEY` and `INPUT_FILE` to your environment variables (will change in future)
- Run `python3 ./catalog_importer.py`. Script will output creates and updates.

## Implementation Details

`Categories` needs to be imported as a list of values, but flat csv only supports strings. To import multiple categories, use `//` as a delimiter e.g. `Category 1//Category 2` on a single product `Categories` field will result in two categories.

The script supports product and variant metadata. 
For product metadata, use the `metadata.` prefix on the relevant headers e.g. `metadata.My Key` and the script will import the correct metadata key/value pair.
For variant metadata, use the `variant.metadata.` prefix on the relevant headers e.g. `variant.metadata.My Key` and the script will import the correct metadata key/value pair.
