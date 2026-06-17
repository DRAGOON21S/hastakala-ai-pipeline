"""Gemini/LangChain client for the two LLM stages."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .config import (
    configure_google_credentials,
    use_vertex_ai,
    vertex_location,
    vertex_project,
)
from .prompts import (
    STORYTELLER_SYSTEM_PROMPT,
    STRUCTURING_SYSTEM_PROMPT,
    VISUAL_PLANNER_SYSTEM_PROMPT,
)
from .schemas import (
    RawProduct,
    SpecsFormattingOutput,
    StorytellingOutput,
    VisualPlanningOutput,
)


class GeminiContentClient:
    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.65,
    ) -> None:
        load_dotenv()
        configure_google_credentials()
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.1-pro-preview")

        if use_vertex_ai():
            from langchain_google_vertexai import ChatVertexAI

            project = vertex_project()
            location = vertex_location()
            self.story_llm = ChatVertexAI(
                model=self.model,
                project=project,
                location=location,
                temperature=temperature,
            ).with_structured_output(StorytellingOutput)
            self.specs_llm = ChatVertexAI(
                model=self.model,
                project=project,
                location=location,
                temperature=0.2,
            ).with_structured_output(SpecsFormattingOutput)
            self.visual_llm = ChatVertexAI(
                model=self.model,
                project=project,
                location=location,
                temperature=0.7,
            ).with_structured_output(VisualPlanningOutput)
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Add it to your environment or .env file."
            )

        self.story_llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=api_key,
            temperature=temperature,
        ).with_structured_output(StorytellingOutput)
        self.specs_llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=api_key,
            temperature=0.2,
        ).with_structured_output(SpecsFormattingOutput)
        self.visual_llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=api_key,
            temperature=0.7,
        ).with_structured_output(VisualPlanningOutput)

    def generate_story(self, product: RawProduct) -> StorytellingOutput:
        payload = {
            "raw_product_name": product.product_name,
            "category": product.category,
            "art_style_or_craft_type": product.craft_type,
            "short_description": product.short_description,
            "material": product.material,
        }
        result = self.story_llm.invoke(
            [
                SystemMessage(content=STORYTELLER_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        "Create the premium product storytelling fields for "
                        f"this raw product submission:\n{payload}"
                    )
                ),
            ]
        )
        return result if isinstance(result, StorytellingOutput) else StorytellingOutput.model_validate(result)

    def format_specs(
        self,
        product: RawProduct,
        story: StorytellingOutput,
    ) -> SpecsFormattingOutput:
        payload = {
            "storytelling_output": story.model_dump(),
            "raw_material": product.material,
            "raw_craft_type": product.craft_type,
            "height_cm": product.height_cm,
            "width_cm": product.width_cm,
            "weight_kg": product.weight_kg,
        }
        result = self.specs_llm.invoke(
            [
                SystemMessage(content=STRUCTURING_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        "Format this product for the frontend specifications "
                        f"accordion:\n{payload}"
                    )
                ),
            ]
        )
        return result if isinstance(result, SpecsFormattingOutput) else SpecsFormattingOutput.model_validate(result)

    def plan_visuals(
        self,
        product: RawProduct,
        story: StorytellingOutput,
        specs: SpecsFormattingOutput,
    ) -> VisualPlanningOutput:
        payload = {
            "product_id": product.product_id,
            "raw_product_name": product.product_name,
            "category": product.category,
            "craft_type": product.craft_type,
            "short_description": product.short_description,
            "material": product.material,
            "dimensions_cm": {
                "height": product.height_cm,
                "width": product.width_cm,
            },
            "storytelling_output": story.model_dump(),
            "specifications_output": specs.model_dump(),
        }
        result = self.visual_llm.invoke(
            [
                SystemMessage(content=VISUAL_PLANNER_SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        "Create product-specific image-generation prompts for "
                        f"this artwork:\n{payload}"
                    )
                ),
            ]
        )
        return result if isinstance(result, VisualPlanningOutput) else VisualPlanningOutput.model_validate(result)
