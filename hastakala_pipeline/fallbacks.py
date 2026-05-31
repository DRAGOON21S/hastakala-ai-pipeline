"""Deterministic fallback content for quota or API outages."""

from __future__ import annotations

import re

from .parsing import clean_text
from .schemas import (
    DimensionsCm,
    RawProduct,
    SpecsFormattingOutput,
    StorytellingOutput,
    TimelineItem,
    VisualPlanningOutput,
    VisualPrompt,
)


def fallback_story(product: RawProduct) -> StorytellingOutput:
    title = clean_text(product.product_name) or "Handcrafted Artwork"
    craft = clean_text(product.craft_type) or clean_text(product.category) or "handcrafted art"
    material = clean_text(product.material) or "the chosen medium"
    note = clean_text(product.short_description)

    first_para = (
        f"{title} is a handmade {craft.lower()} shaped with attention, patience, "
        f"and a close sensitivity to expression."
    )
    if note:
        first_para += f" The artist's note describes it as: {note}"
    second_para = (
        f"Created using {material}, the piece is presented for a space that values "
        "quiet detail, human touch, and the presence of original craft."
    )

    return StorytellingOutput(
        display_title=refine_title(title),
        hero_hook=f"A considered handmade piece in {craft.lower()}.",
        main_description=f"<p>{first_para}</p><p>{second_para}</p>",
        timeline_story=[
            TimelineItem(
                phase="1",
                title="The Inspiration",
                description=(
                    "The work begins with a focused idea: to hold emotion, form, "
                    "and atmosphere in a single handmade composition."
                ),
            ),
            TimelineItem(
                phase="2",
                title="The Craft",
                description=(
                    f"Layer by layer, the artist works through {material}, using "
                    f"the discipline of {craft.lower()} to build texture and depth."
                ),
            ),
            TimelineItem(
                phase="3",
                title="The Culmination",
                description=(
                    "The final piece carries the visible patience of the hand, ready "
                    "to bring warmth and character into a considered interior."
                ),
            ),
        ],
    )


def fallback_specs(product: RawProduct) -> SpecsFormattingOutput:
    materials = split_materials(product.material)
    return SpecsFormattingOutput(
        materials=materials,
        dimensions_cm=DimensionsCm(height=product.height_cm, width=product.width_cm),
        weight_kg=product.weight_kg,
        craft_type=clean_text(product.craft_type) or clean_text(product.category),
        ui_bullets=[
            bullet
            for bullet in [
                f"Material: {', '.join(materials)}" if materials else "",
                f"Height: {product.height_cm} cm" if product.height_cm else "",
                f"Width: {product.width_cm} cm" if product.width_cm else "",
                f"Weight: {product.weight_kg} kg" if product.weight_kg else "",
            ]
            if bullet
        ],
    )


def fallback_visual_plan(
    product: RawProduct,
    story: StorytellingOutput,
    specs: SpecsFormattingOutput,
) -> VisualPlanningOutput:
    title = story.display_title
    craft = specs.craft_type or product.craft_type or "handcrafted artwork"
    material = ", ".join(specs.materials) if specs.materials else product.material or "handmade material"
    dimensions = format_dimensions(product)

    return VisualPlanningOutput(
        mockup_shots=[
            VisualPrompt(
                slug=f"{slugify(title)}-living-room-mockup",
                title="Warm Living Room Mockup",
                placement_context="living room",
                aspect_ratio="4:3",
                prompt=(
                    f"Product mockup photograph of a {craft} titled {title}, "
                    f"made with {material}{dimensions}, displayed as the focal "
                    "artwork in a calm modern Indian living room with natural wood, "
                    "linen upholstery, soft daylight, breathable negative space, "
                    "editorial ecommerce styling, no people, no logos, no text."
                ),
            ),
            VisualPrompt(
                slug=f"{slugify(title)}-study-mockup",
                title="Study Wall Mockup",
                placement_context="home study or office",
                aspect_ratio="4:3",
                prompt=(
                    f"Premium interior mockup showing {title}, a handmade {craft}, "
                    f"placed on a refined study wall above a minimal desk, material "
                    f"character visible as {material}, warm directional light, "
                    "quiet gallery composition, realistic shadows, no people, no "
                    "brand marks, no text overlay."
                ),
            ),
        ],
        story_images=[
            VisualPrompt(
                slug=f"{slugify(title)}-material-story",
                title="Material Detail Story",
                placement_context="creation detail",
                aspect_ratio="1:1",
                prompt=(
                    f"Close-up story image inspired by the making of {title}: "
                    f"{material} textures, careful handmade marks, art studio "
                    "surface, premium macro product photography, soft side light, "
                    "no hands, no people, no text, no watermark."
                ),
            ),
            VisualPrompt(
                slug=f"{slugify(title)}-final-polish-story",
                title="Final Polish Story",
                placement_context="finished artwork detail",
                aspect_ratio="1:1",
                prompt=(
                    f"Elegant detail image suggesting the final polish of {title}, "
                    f"a {craft}, with emphasis on handmade surface quality, subtle "
                    "depth, quiet shadows, gallery-like restraint, no people, no "
                    "logos, no text."
                ),
            ),
        ],
    )


def split_materials(value: str) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    parts = re.split(r",|/|\+|\band\b|&", text, flags=re.IGNORECASE)
    return [clean_text(part).title() for part in parts if clean_text(part)]


def refine_title(value: str) -> str:
    title = clean_text(value).strip(" .")
    return title[:1].upper() + title[1:] if title else "Handcrafted Artwork"


def format_dimensions(product: RawProduct) -> str:
    if product.height_cm and product.width_cm:
        return f", approximately {product.height_cm} x {product.width_cm} cm"
    return ""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "artwork"
