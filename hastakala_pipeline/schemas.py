"""Pydantic schemas for raw, intermediate, and final pipeline data."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class RawProduct(BaseModel):
    row_number: int
    product_id: str
    artist_name: str = ""
    artist_id: str = ""
    price_inr: int | None = None
    product_name: str = ""
    category: str = ""
    craft_type: str = ""
    short_description: str = ""
    material: str = ""
    height_cm: float | None = None
    width_cm: float | None = None
    weight_kg: float | None = None
    availability: str = ""
    raw_row: dict[str, Any] = Field(default_factory=dict)


class TimelineItem(BaseModel):
    phase: str
    title: str
    description: str

    @field_validator("phase", mode="before")
    @classmethod
    def coerce_phase(cls, value: Any) -> str:
        return str(value).strip()


class StorytellingOutput(BaseModel):
    display_title: str
    hero_hook: str
    main_description: str
    timeline_story: list[TimelineItem] = Field(min_length=3, max_length=3)


class DimensionsCm(BaseModel):
    height: float | int | None = None
    width: float | int | None = None


class SpecsFormattingOutput(BaseModel):
    materials: list[str]
    dimensions_cm: DimensionsCm
    weight_kg: float | None
    craft_type: str
    ui_bullets: list[str] = Field(default_factory=list)


class VisualPrompt(BaseModel):
    slug: str
    title: str
    placement_context: str
    prompt: str
    aspect_ratio: str = "4:3"


class VisualPlanningOutput(BaseModel):
    mockup_shots: list[VisualPrompt] = Field(min_length=2, max_length=2)
    story_images: list[VisualPrompt] = Field(min_length=2, max_length=2)


class GeneratedVisual(BaseModel):
    slug: str
    title: str
    placement_context: str
    prompt: str
    aspect_ratio: str
    filename: str | None = None
    generation_status: str = "planned"
    error: str | None = None


class ArtistInfo(BaseModel):
    name: str
    id: str


class StickySidebar(BaseModel):
    title: str
    hook_subtitle: str
    price_inr: int | None
    availability_status: str


class MainContent(BaseModel):
    rich_description_html: str


class SpecificationsAccordion(BaseModel):
    materials: list[str]
    dimensions_cm: dict[str, float | int | None]
    weight_kg: float | None
    craft_type: str


class UiMapping(BaseModel):
    sticky_sidebar: StickySidebar
    main_content: MainContent
    timeline_story: list[TimelineItem]
    specifications_accordion: SpecificationsAccordion


class LocalMedia(BaseModel):
    directory_path: str
    saved_filenames: list[str]
    generated_mockup_filenames: list[str] = Field(default_factory=list)
    generated_story_filenames: list[str] = Field(default_factory=list)


class GeneratedMedia(BaseModel):
    mockup_shots: list[GeneratedVisual] = Field(default_factory=list)
    story_images: list[GeneratedVisual] = Field(default_factory=list)


class FinalProduct(BaseModel):
    product_id: str
    artist_info: ArtistInfo
    ui_mapping: UiMapping
    local_media: LocalMedia
    generated_media: GeneratedMedia = Field(default_factory=GeneratedMedia)
