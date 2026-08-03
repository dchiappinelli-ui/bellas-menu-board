#!/usr/bin/env python3
"""
Bella's Bake Shop — nightly Square catalog sync.

Pulls the categories used on the digital menu board, cleans them up,
and writes data/menu.json. Runs once a night via GitHub Actions
(see .github/workflows/nightly-sync.yml) — no server, no polling.

Requires env var SQUARE_ACCESS_TOKEN (a Square API access token with
ITEMS_READ permission). Set this as a GitHub Actions secret, never
commit it to the repo.
"""

import json
import os
import sys
from datetime import datetime, timezone
import requests

SQUARE_API_BASE = "https://connect.squareup.com/v2"
SQUARE_VERSION = "2025-01-23"  # Square API version header

# Board categories -> (output key, price ceiling, excluded item names)
CATEGORY_CONFIG = {
    "ARTISAN SANDWICHES": {"ceiling": 20, "exclude": {"BUILD-A-SANDWICH"}},
    "GOURMET PASTRY":     {"ceiling": 20, "exclude": {"CUSTOM CAKE", "CHOCOLATE CAKE"}},
    "COFFEE":             {"ceiling": 15, "exclude": {"Box Coffee 10 cups"}},
    "SPECIALTY DRINKS":   {"ceiling": 15, "exclude": set()},
    "BREAD":              {"ceiling": 25, "exclude": {"Easter Bread 13"}},
}

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "menu.json")


def square_headers(token):
    return {
        "Square-Version": SQUARE_VERSION,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def fetch_all_catalog_objects(token):
    """Page through Square's catalog and return (objects_by_id, category_name_by_id)."""
    objects_by_id = {}
    cursor = None
    while True:
        body = {
            "object_types": ["ITEM", "ITEM_VARIATION", "CATEGORY"],
            "include_related_objects": True,
            "limit": 200,
        }
        if cursor:
            body["cursor"] = cursor
        resp = requests.post(
            f"{SQUARE_API_BASE}/catalog/search",
            headers=square_headers(token),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()

        for obj in payload.get("objects", []) + payload.get("related_objects", []):
            objects_by_id[obj["id"]] = obj

        cursor = payload.get("cursor")
        if not cursor:
            break

    category_name_by_id = {
        oid: obj.get("category_data", {}).get("name")
        for oid, obj in objects_by_id.items()
        if obj.get("type") == "CATEGORY"
    }
    return objects_by_id, category_name_by_id


def item_category_names(item, category_name_by_id):
    idata = item.get("item_data", {})
    names = set()
    for c in idata.get("categories", []):
        n = category_name_by_id.get(c.get("id"))
        if n:
            names.add(n)
    rc = idata.get("reporting_category", {}).get("id")
    if category_name_by_id.get(rc):
        names.add(category_name_by_id[rc])
    return names


def build_menu(objects_by_id, category_name_by_id):
    target_cats = set(CATEGORY_CONFIG.keys())
    menu = {c: {} for c in target_cats}  # name -> item dict, dedup by name

    for obj in objects_by_id.values():
        if obj.get("type") != "ITEM" or obj.get("is_deleted"):
            continue
        cats = item_category_names(obj, category_name_by_id) & target_cats
        if not cats:
            continue

        idata = obj["item_data"]
        name = (idata.get("name") or "").strip()
        if not name:
            continue

        prices = []
        for v in idata.get("variations", []):
            pm = v.get("item_variation_data", {}).get("price_money")
            if pm and pm.get("amount") is not None:
                prices.append(pm["amount"] / 100)
        if not prices:
            continue
        price = min(prices)

        description = (idata.get("description") or "").strip()

        for cat in cats:
            cfg = CATEGORY_CONFIG[cat]
            if name in cfg["exclude"]:
                continue
            if price > cfg["ceiling"]:
                continue
            menu[cat][name] = {"name": name, "price": price, "description": description}

    return {cat: sorted(items.values(), key=lambda x: x["name"]) for cat, items in menu.items()}


def main():
    token = os.environ.get("SQUARE_ACCESS_TOKEN")
    if not token:
        print("ERROR: SQUARE_ACCESS_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    objects_by_id, category_name_by_id = fetch_all_catalog_objects(token)
    menu = build_menu(objects_by_id, category_name_by_id)

    output = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "menu": menu,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    counts = {cat: len(items) for cat, items in menu.items()}
    print(f"Synced OK. Item counts: {counts}")


if __name__ == "__main__":
    main()
