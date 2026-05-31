"""Local media discovery for product assets."""

from __future__ import annotations

import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}


def find_local_product_media(
    product_id: str,
    assets_root: str | Path = "assets/products",
) -> tuple[str, list[str]]:
    root = Path(assets_root)
    product_dir = root / product_id
    public_path = "/" + product_dir.as_posix().strip("/") + "/"

    if not product_dir.exists():
        return public_path, []

    filenames = sorted(
        item.name
        for item in product_dir.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )
    return public_path, filenames


def import_root_images_for_product(
    product_id: str,
    source_root: str | Path,
    assets_root: str | Path = "assets/products",
) -> list[str]:
    source = Path(source_root)
    destination = Path(assets_root) / product_id
    root_images = sorted(
        item
        for item in source.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not root_images:
        return []

    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for index, image_path in enumerate(root_images, start=1):
        suffix = image_path.suffix.lower()
        target = destination / f"source_{index}{suffix}"
        if target.exists():
            copied.append(target.name)
            continue
        shutil.copy2(image_path, target)
        copied.append(target.name)
    return copied
