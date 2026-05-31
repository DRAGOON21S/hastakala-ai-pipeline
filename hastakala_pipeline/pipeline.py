"""Pipeline orchestration and output writing."""

from __future__ import annotations

import json
from pathlib import Path

from .fallbacks import fallback_specs, fallback_story, fallback_visual_plan
from .image_generation import ImagenGenerator, generate_visual_batch
from .llm_client import GeminiContentClient
from .media import find_local_product_media, import_root_images_for_product
from .parsing import load_products_from_csv
from .schemas import (
    ArtistInfo,
    FinalProduct,
    GeneratedMedia,
    LocalMedia,
    MainContent,
    SpecificationsAccordion,
    StickySidebar,
    UiMapping,
)


def run_pipeline(
    input_csv: str | Path,
    output_txt: str | Path,
    assets_root: str | Path = "assets/products",
    model: str | None = None,
    image_model: str | None = None,
    generate_images: bool = True,
    limit: int | None = None,
    import_root_images: bool = False,
    artist_index: int | None = None,
    product_index: int | None = None,
    offline_fallback: bool = False,
    force_offline_content: bool = False,
) -> list[FinalProduct]:
    products = load_products_from_csv(input_csv)
    if artist_index is not None:
        products = select_products_by_artist_index(
            products,
            artist_index=artist_index,
            product_index=product_index,
        )
    if limit is not None:
        products = products[:limit]

    client = GeminiContentClient(model=model)
    image_generator = ImagenGenerator(model=image_model) if generate_images else None

    final_products: list[FinalProduct] = []
    for product in products:
        if import_root_images:
            import_root_images_for_product(
                product.product_id,
                source_root=Path(input_csv).parent,
                assets_root=assets_root,
            )

        try:
            if force_offline_content:
                raise RuntimeError("Forced offline content mode.")
            story = client.generate_story(product)
            specs = client.format_specs(product, story)
            visual_plan = client.plan_visuals(product, story, specs)
        except Exception:
            if not offline_fallback:
                raise
            story = fallback_story(product)
            specs = fallback_specs(product)
            visual_plan = fallback_visual_plan(product, story, specs)
        media_path, media_files = find_local_product_media(product.product_id, assets_root)
        product_dir = Path(assets_root) / product.product_id
        mockups = generate_visual_batch(
            image_generator,
            visual_plan.mockup_shots,
            product_dir=product_dir,
            prefix="mockup",
            enabled=generate_images,
        )
        story_images = generate_visual_batch(
            image_generator,
            visual_plan.story_images,
            product_dir=product_dir,
            prefix="story",
            enabled=generate_images,
        )

        final_products.append(
            FinalProduct(
                product_id=product.product_id,
                artist_info=ArtistInfo(
                    name=product.artist_name,
                    id=product.artist_id,
                ),
                ui_mapping=UiMapping(
                    sticky_sidebar=StickySidebar(
                        title=story.display_title,
                        hook_subtitle=story.hero_hook,
                        price_inr=product.price_inr,
                        availability_status=product.availability or "Availability on request",
                    ),
                    main_content=MainContent(
                        rich_description_html=story.main_description,
                    ),
                    timeline_story=story.timeline_story,
                    specifications_accordion=SpecificationsAccordion(
                        materials=specs.materials,
                        dimensions_cm={
                            "height": specs.dimensions_cm.height or product.height_cm,
                            "width": specs.dimensions_cm.width or product.width_cm,
                        },
                        weight_kg=specs.weight_kg,
                        craft_type=specs.craft_type,
                    ),
                ),
                local_media=LocalMedia(
                    directory_path=media_path,
                    saved_filenames=media_files,
                    generated_mockup_filenames=[
                        visual.filename for visual in mockups if visual.filename
                    ],
                    generated_story_filenames=[
                        visual.filename for visual in story_images if visual.filename
                    ],
                ),
                generated_media=GeneratedMedia(
                    mockup_shots=mockups,
                    story_images=story_images,
                ),
            )
        )

    write_json_txt(final_products, output_txt)
    return final_products


def select_products_by_artist_index(
    products: list,
    artist_index: int,
    product_index: int | None = None,
) -> list:
    if artist_index < 1:
        raise ValueError("--artist-index must be 1 or greater.")

    artists: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for product in products:
        key = (product.artist_id, product.artist_name)
        if key not in seen:
            seen.add(key)
            artists.append(key)

    if artist_index > len(artists):
        raise ValueError(
            f"--artist-index {artist_index} is out of range. Found {len(artists)} artists."
        )

    target_artist = artists[artist_index - 1]
    selected = [
        product
        for product in products
        if (product.artist_id, product.artist_name) == target_artist
    ]

    if product_index is not None:
        if product_index < 1:
            raise ValueError("--product-index must be 1 or greater.")
        if product_index > len(selected):
            raise ValueError(
                f"--product-index {product_index} is out of range for artist "
                f"{target_artist[1]}. Found {len(selected)} products."
            )
        selected = [selected[product_index - 1]]

    return selected


def write_json_txt(products: list[FinalProduct], output_txt: str | Path) -> None:
    path = Path(output_txt)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [product.model_dump() for product in products]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
