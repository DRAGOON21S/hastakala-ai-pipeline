"""HTTP API for running the Hastakala pipeline from a frontend."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .config import use_vertex_ai, vertex_location
from .pipeline import run_pipeline


load_dotenv()


class LocalPipelineRequest(BaseModel):
    input_path: str = Field(..., description="CSV path available on the API server.")
    output_path: str = "output/products.txt"
    assets_root: str = "assets/products"
    model: str | None = None
    image_model: str | None = None
    generate_images: bool = True
    limit: int | None = None
    import_root_images: bool = False
    artist_index: int | None = None
    product_index: int | None = None
    offline_fallback: bool = False
    force_offline_content: bool = False


def create_app() -> FastAPI:
    app = FastAPI(title="Hastakala AI Pipeline API", version="1.0.0")

    origins = parse_csv_env("HASTAKALA_CORS_ORIGINS")
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "vertex_ai": use_vertex_ai(),
            "google_cloud_project_configured": bool(
                os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
            ),
            "google_cloud_location": vertex_location(),
            "image_provider": os.getenv("IMAGE_PROVIDER", "gemini"),
        }

    @app.post("/v1/pipeline/run")
    async def run_uploaded_csv(
        csv_file: Annotated[UploadFile, File()],
        _: Annotated[None, Depends(require_api_key)],
        assets_root: Annotated[str, Form()] = "assets/products",
        model: Annotated[str | None, Form()] = None,
        image_model: Annotated[str | None, Form()] = None,
        generate_images: Annotated[bool, Form()] = True,
        limit: Annotated[int | None, Form()] = None,
        import_root_images: Annotated[bool, Form()] = False,
        artist_index: Annotated[int | None, Form()] = None,
        product_index: Annotated[int | None, Form()] = None,
        offline_fallback: Annotated[bool, Form()] = False,
        force_offline_content: Annotated[bool, Form()] = False,
    ) -> dict[str, object]:
        if not csv_file.filename or not csv_file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Upload a .csv file.")

        run_id = uuid.uuid4().hex
        work_dir = Path(tempfile.gettempdir()) / "hastakala-api" / run_id
        work_dir.mkdir(parents=True, exist_ok=True)
        input_path = work_dir / "submissions.csv"
        output_path = work_dir / "products.txt"
        input_path.write_bytes(await csv_file.read())

        products = await run_in_threadpool(
            run_pipeline,
            input_path,
            output_path,
            assets_root,
            model,
            image_model,
            generate_images,
            limit,
            import_root_images,
            artist_index,
            product_index,
            offline_fallback,
            force_offline_content,
        )
        return {
            "run_id": run_id,
            "count": len(products),
            "products": [product.model_dump() for product in products],
        }

    @app.post("/v1/pipeline/run-local")
    async def run_local_csv(
        request: LocalPipelineRequest,
        _: Annotated[None, Depends(require_api_key)],
    ) -> dict[str, object]:
        input_path = Path(request.input_path)
        if not input_path.exists():
            raise HTTPException(status_code=404, detail="input_path does not exist.")

        products = await run_in_threadpool(
            run_pipeline,
            request.input_path,
            request.output_path,
            request.assets_root,
            request.model,
            request.image_model,
            request.generate_images,
            request.limit,
            request.import_root_images,
            request.artist_index,
            request.product_index,
            request.offline_fallback,
            request.force_offline_content,
        )
        return {
            "count": len(products),
            "output_path": request.output_path,
            "products": [product.model_dump() for product in products],
        }

    return app


def parse_csv_env(name: str) -> list[str]:
    return [
        value.strip()
        for value in os.getenv(name, "").split(",")
        if value.strip()
    ]


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    expected = os.getenv("HASTAKALA_API_KEY", "").strip()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key.")


app = create_app()
