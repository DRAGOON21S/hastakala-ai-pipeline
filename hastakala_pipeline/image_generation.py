"""Imagen-backed generated media creation."""

from __future__ import annotations

import base64
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from .config import (
    configure_google_credentials,
    use_vertex_ai,
    vertex_location,
    vertex_project,
)
from .schemas import GeneratedVisual, VisualPrompt


ALLOWED_ASPECT_RATIOS = {"1:1", "3:4", "4:3", "9:16", "16:9"}


class ImagenGenerator:
    def __init__(self, model: str | None = None) -> None:
        load_dotenv()
        configure_google_credentials()

        from google import genai

        if use_vertex_ai():
            self.client = genai.Client(
                vertexai=True,
                project=vertex_project(),
                location=vertex_location(),
            )
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is missing. Add it to your environment or .env file."
                )
            self.client = genai.Client(api_key=api_key)

        self.provider = os.getenv("IMAGE_PROVIDER", "gemini").strip().lower()
        if self.provider not in {"gemini", "imagen"}:
            raise ValueError("IMAGE_PROVIDER must be either 'gemini' or 'imagen'.")
        if self.provider == "imagen":
            self.model = model or os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001")
        else:
            self.model = model or os.getenv(
                "GEMINI_IMAGE_MODEL",
                "gemini-3-pro-image",
            )

    def generate_visual(
        self,
        visual: VisualPrompt,
        product_dir: str | Path,
        prefix: str,
    ) -> GeneratedVisual:
        output_dir = Path(product_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_slug = slugify(visual.slug or visual.title)
        filename = next_available_filename(output_dir, f"{prefix}-{safe_slug}", ".png")
        output_path = output_dir / filename
        aspect_ratio = normalize_aspect_ratio(visual.aspect_ratio)

        try:
            self._generate_image_file(
                prompt=visual.prompt,
                output_path=output_path,
                aspect_ratio=aspect_ratio,
            )
            return GeneratedVisual(
                slug=visual.slug,
                title=visual.title,
                placement_context=visual.placement_context,
                prompt=visual.prompt,
                aspect_ratio=aspect_ratio,
                filename=filename,
                generation_status="generated",
            )
        except Exception as exc:
            return GeneratedVisual(
                slug=visual.slug,
                title=visual.title,
                placement_context=visual.placement_context,
                prompt=visual.prompt,
                aspect_ratio=aspect_ratio,
                filename=None,
                generation_status="failed",
                error=str(exc),
            )

    def _generate_image_file(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str,
    ) -> None:
        if self.provider == "imagen":
            self._generate_imagen_file(prompt, output_path, aspect_ratio)
            return
        self._generate_gemini_image_file(prompt, output_path, aspect_ratio)

    def _generate_imagen_file(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str,
    ) -> None:
        from google.genai import types

        response = self.client.models.generate_images(
            model=self.model,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                person_generation="dont_allow",
            ),
        )
        generated_images = getattr(response, "generated_images", None) or []
        if not generated_images:
            raise RuntimeError("Imagen returned no generated images.")

        image_obj = generated_images[0].image
        if hasattr(image_obj, "save"):
            image_obj.save(output_path)
            return

        image_bytes = getattr(image_obj, "image_bytes", None)
        if image_bytes is None:
            raise RuntimeError("Imagen response did not include image bytes.")
        if isinstance(image_bytes, str):
            image_bytes = base64.b64decode(image_bytes)
        output_path.write_bytes(image_bytes)

    def _generate_gemini_image_file(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str,
    ) -> None:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                responseModalities=["TEXT", "IMAGE"],
                imageConfig=types.ImageConfig(
                    aspectRatio=aspect_ratio,
                    imageSize="1K",
                ),
            ),
        )

        parts = getattr(response, "parts", None)
        if not parts and getattr(response, "candidates", None):
            parts = response.candidates[0].content.parts
        for part in parts or []:
            as_image = getattr(part, "as_image", None)
            if callable(as_image):
                image = as_image()
                if image is not None:
                    image.save(output_path)
                    return

            inline_data = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
            data = getattr(inline_data, "data", None) if inline_data else None
            if data:
                if isinstance(data, str):
                    data = base64.b64decode(data)
                output_path.write_bytes(data)
                return

        raise RuntimeError("Gemini image model returned no image parts.")


def generate_visual_batch(
    generator: ImagenGenerator | None,
    visuals: list[VisualPrompt],
    product_dir: str | Path,
    prefix: str,
    enabled: bool,
) -> list[GeneratedVisual]:
    if not enabled:
        return [
            GeneratedVisual(
                slug=visual.slug,
                title=visual.title,
                placement_context=visual.placement_context,
                prompt=visual.prompt,
                aspect_ratio=normalize_aspect_ratio(visual.aspect_ratio),
            )
            for visual in visuals
        ]
    if generator is None:
        raise RuntimeError("Image generation is enabled but no ImagenGenerator was provided.")
    return [
        generator.generate_visual(visual, product_dir=product_dir, prefix=prefix)
        for visual in visuals
    ]


def normalize_aspect_ratio(value: str) -> str:
    ratio = str(value or "4:3").strip()
    return ratio if ratio in ALLOWED_ASPECT_RATIOS else "4:3"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "visual"


def next_available_filename(directory: Path, stem: str, suffix: str) -> str:
    candidate = f"{stem}{suffix}"
    index = 2
    while (directory / candidate).exists():
        candidate = f"{stem}-{index}{suffix}"
        index += 1
    return candidate
