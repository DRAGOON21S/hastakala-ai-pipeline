"""CSV ingestion and messy field normalization."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .schemas import RawProduct


HEADER_ALIASES = {
    "artist name": "artist_name",
    "hastakala artist id": "artist_id",
    "artist id": "artist_id",
    "product id": "product_id",
    "price": "price_inr",
    "price (rs)": "price_inr",
    "price (inr)": "price_inr",
    "price (\u20b9)": "price_inr",
    "product name": "product_name",
    "category": "category",
    "art style / craft type": "craft_type",
    "art style": "craft_type",
    "craft type": "craft_type",
    "short description": "short_description",
    "description": "short_description",
    "material": "material",
    "materials": "material",
    "height": "height_cm",
    "height cm": "height_cm",
    "width": "width_cm",
    "width cm": "width_cm",
    "weight": "weight_kg",
    "weight kg": "weight_kg",
    "availability": "availability",
}


def load_products_from_csv(csv_path: str | Path) -> list[RawProduct]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)
        rows = list(reader)

    if not rows:
        return []

    headers = rows[0]
    data_rows = rows[1:]
    group_starts = find_product_group_starts(headers)

    artist_counts: defaultdict[str, int] = defaultdict(int)
    products: list[RawProduct] = []
    product_row_number = 0

    for csv_row_number, row_values in enumerate(data_rows, start=2):
        row = row_to_positional_dict(headers, row_values)
        base = normalize_base_row(row)

        product_sections = (
            extract_grouped_products(headers, row_values, group_starts)
            if group_starts
            else [normalize_row(dict(zip(headers, row_values)))]
        )

        for section in product_sections:
            if not has_product_content(section):
                continue

            artist_id = clean_text(base.get("artist_id", ""))
            artist_key = artist_id or f"ROW-{csv_row_number:04d}"
            artist_counts[artist_key] += 1
            product_row_number += 1

            product_id = clean_text(section.get("product_id", ""))
            if not product_id:
                product_id = make_product_id(
                    artist_id,
                    product_row_number,
                    artist_counts[artist_key],
                )

            products.append(
                RawProduct(
                    row_number=product_row_number,
                    product_id=product_id,
                    artist_name=clean_text(base.get("artist_name", "")),
                    artist_id=artist_id,
                    price_inr=parse_price(section.get("price_inr")),
                    product_name=clean_text(section.get("product_name", "")),
                    category=clean_text(section.get("category", "")),
                    craft_type=clean_text(section.get("craft_type", "")),
                    short_description=clean_text(section.get("short_description", "")),
                    material=clean_text(section.get("material", "")),
                    height_cm=parse_dimension_cm(section.get("height_cm")),
                    width_cm=parse_dimension_cm(section.get("width_cm")),
                    weight_kg=parse_weight_kg(section.get("weight_kg")),
                    availability=clean_text(section.get("availability", "")),
                    raw_row=row,
                )
            )

    return products


def row_to_positional_dict(headers: list[str], values: list[str]) -> dict[str, Any]:
    return {
        f"{index}:{header}": values[index] if index < len(values) else ""
        for index, header in enumerate(headers)
    }


def normalize_base_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for positional_header, value in row.items():
        header = positional_header.split(":", 1)[1]
        key = map_header_to_field(header)
        if key in {"artist_name", "artist_id", "product_id"}:
            normalized[key] = value
    return normalized


def find_product_group_starts(headers: list[str]) -> list[int]:
    starts = [
        index
        for index, header in enumerate(headers)
        if map_header_to_field(header) == "image_urls"
    ]
    if starts:
        return starts
    return [
        index
        for index, header in enumerate(headers)
        if map_header_to_field(header) == "price_inr"
    ]


def extract_grouped_products(
    headers: list[str],
    values: list[str],
    group_starts: list[int],
) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for group_number, start in enumerate(group_starts):
        end = group_starts[group_number + 1] if group_number + 1 < len(group_starts) else len(headers)
        section: dict[str, Any] = {}
        for index in range(start, end):
            key = map_header_to_field(headers[index])
            if not key or key in {"image_urls", "handmade_confirmation"}:
                continue
            value = values[index] if index < len(values) else ""
            if key not in section or clean_text(value):
                section[key] = value
        products.append(section)
    return products


def has_product_content(section: dict[str, Any]) -> bool:
    meaningful_keys = {
        "price_inr",
        "product_name",
        "category",
        "craft_type",
        "short_description",
        "material",
        "height_cm",
        "width_cm",
        "weight_kg",
        "availability",
    }
    return any(clean_text(section.get(key, "")) for key in meaningful_keys)


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for header, value in row.items():
        mapped_key = map_header_to_field(header)
        if mapped_key:
            normalized[mapped_key] = value
    return normalized


def map_header_to_field(header: str | None) -> str | None:
    key = normalize_header(header)
    if key in HEADER_ALIASES:
        return HEADER_ALIASES[key]
    if "artist name" in key:
        return "artist_name"
    if "hastakala artist id" in key or key == "artist id":
        return "artist_id"
    if "product id" in key:
        return "product_id"
    if "upload product images" in key:
        return "image_urls"
    if "price" in key:
        return "price_inr"
    if "product name" in key:
        return "product_name"
    if "category" in key:
        return "category"
    if "art style" in key or "craft type" in key:
        return "craft_type"
    if "short description" in key or key == "description":
        return "short_description"
    if "material" in key:
        return "material"
    if "height" in key:
        return "height_cm"
    if "width" in key:
        return "width_cm"
    if "weight" in key:
        return "weight_kg"
    if "availability" in key:
        return "availability"
    if "handmade" in key:
        return "handmade_confirmation"
    return None


def normalize_header(header: str | None) -> str:
    if not header:
        return ""
    compact = re.sub(r"\s+", " ", header.strip().lower())
    compact = re.sub(r"^[^a-z0-9]+", "", compact)
    compact = re.sub(r"\b\d+\.\s*", "", compact)
    compact = compact.replace("short answer (required)", "")
    compact = compact.replace("short answer (number only)", "")
    compact = compact.replace("file upload (images only, 3-5 photos, required)", "")
    compact = compact.replace("file upload (images only, 3–5 photos, required)", "")
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact.replace("rupees", "inr")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def make_product_id(artist_id: str, row_number: int, sequence: int) -> str:
    base = clean_product_id_token(artist_id)
    if not base:
        base = f"HK-AR-{row_number:04d}"
    return f"{base}-{sequence:02d}"


def clean_product_id_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9-]+", "-", clean_text(value).upper()).strip("-")
    return re.sub(r"-{2,}", "-", token)


def parse_price(value: Any) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    matches = re.findall(r"\d+(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?", text)
    if not matches:
        return None
    numeric = float(matches[0].replace(",", ""))
    return int(round(numeric))


def parse_dimension_cm(value: Any) -> float | None:
    text = clean_text(value).lower()
    if not text:
        return None
    number = first_number(text)
    if number is None:
        return None
    if any(unit in text for unit in ["inch", "inches", '"']):
        return clean_number(number * 2.54)
    if re.search(r"\bmm\b", text):
        return clean_number(number / 10)
    if re.search(r"\bm\b", text) and not re.search(r"\bcm\b", text):
        return clean_number(number * 100)
    return clean_number(number)


def parse_weight_kg(value: Any) -> float | None:
    text = clean_text(value).lower()
    if not text:
        return None
    number = first_number(text)
    if number is None:
        return None
    if re.search(r"\b(g|gm|gram|grams)\b", text):
        return clean_number(number / 1000)
    if re.search(r"\b(mg|milligram|milligrams)\b", text):
        return clean_number(number / 1_000_000)
    if re.search(r"\b(lb|lbs|pound|pounds)\b", text):
        return clean_number(number * 0.45359237)
    return clean_number(number)


def first_number(text: str) -> float | None:
    match = re.search(r"\d+(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def clean_number(value: float) -> float | int:
    rounded = round(value, 3)
    if rounded.is_integer():
        return int(rounded)
    return rounded
