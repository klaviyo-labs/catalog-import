import csv
import os

from itertools import chain, groupby
from typing import Any, Dict, Set
from klaviyo_api import KlaviyoAPI
from openapi_client.exceptions import ApiException

# For now, storing as ENVs. In future move to cli or web-based input
API_KEY = os.environ.get("KLAVIYO_PRIVATE_KEY")
INPUT_FILE = os.environ.get("INPUT_FILE")

# API will throw errors if these are not set as is.
INTEGRATION_TYPE = "$custom"
CATALOG_TYPE = "$default"

klaviyo = KlaviyoAPI(API_KEY, max_delay=60, max_retries=3, test_host=None)


def create_item(
    request: Any,
    body: Dict,
    object_name: str,
    update_request: Any = None,
    item_id: str = None,
) -> None:
    """
    Creates an item given a request and body.
    Can optionally request updates on 409 conflict.
    """

    def update_item(request, item_id, body: Dict, object_name: str) -> None:
        """
        Updates an item given a request, body, and object name.
        Pops various data points from a create body to produce an acceptable request for updates.
        """
        body["data"]["id"] = item_id
        body["data"]["attributes"].pop("external_id")
        body["data"]["attributes"].pop("catalog_type")
        body["data"]["attributes"].pop("integration_type")

        if body["data"].get("relationships"):
            body["data"].pop("relationships")
        if body["data"]["attributes"].get("sku"):
            body["data"]["attributes"].pop("sku")

        request(item_id, body)
        print(f"{object_name} updated")

    try:
        request(body)
        print(f"{object_name} created")
    except ApiException as exp:
        if exp.status == 409:
            print(f"{object_name} already exists")
            if update_request:
                update_item(
                    update_request,
                    item_id,
                    body,
                    object_name,
                )
        else:
            raise


def import_categories(categories: Set[str]) -> None:
    """
    Creates catalog categories
    """
    for category in categories:
        body = {
            "data": {
                "type": "catalog-category",
                "attributes": {
                    "external_id": category,
                    "name": category,
                    "integration_type": INTEGRATION_TYPE,
                    "catalog_type": CATALOG_TYPE,
                },
                "relationships": {},
            }
        }
        create_item(klaviyo.Catalogs.create_catalog_category, body, category)


def import_item(item: Dict) -> None:
    """
    Creates or updates (if exists) catalog categories
    """
    categories = list(
        map(
            lambda category: {
                "type": "catalog-category",
                "id": f"{INTEGRATION_TYPE}:::{CATALOG_TYPE}:::{category}",
            },
            item["categories"].split("//"),
        )
    )

    metadata = dict(
        (f"{key.replace('metadata.','')}", value)
        for (key, value) in dict(
            filter(lambda x: "metadata." in x[0] and "variant" not in x[0], item.items())
        ).items()
    )
    body = {
        "data": {
            "type": "catalog-item",
            "attributes": {
                "external_id": item["external_id"],
                "integration_type": INTEGRATION_TYPE,
                "title": item["title"],
                "catalog_type": CATALOG_TYPE,
                "description": item["description"],
                "price": float(item["price"]) or 0.00,
                "url": item["product_url"],
                "image_full_url": item["image_full_url"],
                "image_thumbnail_url": item["image_full_url"],
                "images": [],
                "published": True,
                "custom_metadata": metadata,
            },
            "relationships": {"categories": {"data": categories}},
        }
    }

    create_item(
        klaviyo.Catalogs.create_catalog_item,
        body,
        f"Product: {item['title']}",
        klaviyo.Catalogs.update_catalog_item,
        f"{INTEGRATION_TYPE}:::{CATALOG_TYPE}:::{item['external_id']}",
    )


def import_variant_from_item(item: Dict) -> None:
    """
    Creates or updates (if exists) catalog variants
    """
    images = []  # TODO Add logic
    metadata = dict(
        (f"{key.replace('variant.metadata.', '')}", value)
        for (key, value) in dict(
            filter(lambda x: "variant.metadata." in x[0], item.items())
        ).items()
    )

    body = {
        "data": {
            "type": "catalog-variant",
            "attributes": {
                "external_id": item["variant.sku"],
                "catalog_type": CATALOG_TYPE,
                "integration_type": INTEGRATION_TYPE,
                "title": item["variant.title"],
                "description": item["variant.description"] or item["description"],
                "sku": item["variant.sku"],
                "inventory_policy": int(item["variant.inventory_policy"]) or 1,
                "inventory_quantity": int(item["variant.inventory_quantity"]) or 0,
                "price": float(item["variant.price"] or item["price"]),
                "url": item["variant.product_url"] or item["product_url"],
                "image_full_url": item["variant.image_full_url"]
                or item["image_full_url"],
                "image_thumbnail_url": item["variant.image_full_url"]
                or item["image_full_url"],
                "images": images,
                "published": True,
                "custom_metadata": metadata,
            },
            "relationships": {
                "item": {
                    "data":
                        {
                            "type": "catalog-item",
                            "id": f"{INTEGRATION_TYPE}:::{CATALOG_TYPE}:::{item['external_id']}",
                        }
                }
            },
        }
    }

    create_item(
        klaviyo.Catalogs.create_catalog_variant,
        body,
        f"Product: {item['title']}, Variant: {item['variant.title']}",
        klaviyo.Catalogs.update_catalog_variant,
        f"{INTEGRATION_TYPE}:::{CATALOG_TYPE}:::{item['variant.sku']}",
    )


def main() -> None:
    """
    Main Operation
    """
    with open(INPUT_FILE) as file:
        reader = csv.DictReader(file)
        data = [row for _, row in enumerate(reader)]

    # Get all unique categories and import
    categories = set(
        chain(*map(lambda x: x.split("//"), set(map(lambda x: x["categories"], data))))
    )
    import_categories(categories)

    # Fetches each Parent item (first seen) and import
    for _, group in groupby(data, lambda x: x["external_id"]):
        import_item(list(group)[0])

    # Import all the variant line items
    for variant in data:
        import_variant_from_item(variant)


if __name__ == "__main__":
    main()
