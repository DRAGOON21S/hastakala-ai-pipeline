"""Runtime configuration helpers."""

from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path


TRUTHY_VALUES = {"1", "true", "yes", "on"}


def env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in TRUTHY_VALUES


def use_vertex_ai() -> bool:
    return env_truthy("GOOGLE_GENAI_USE_VERTEXAI") or env_truthy(
        "GOOGLE_GENAI_USE_ENTERPRISE"
    )


def vertex_project() -> str:
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT is missing. Set it to your Google Cloud project ID."
        )
    return project


def vertex_location() -> str:
    return os.getenv("GOOGLE_CLOUD_LOCATION", "global").strip() or "global"


def configure_google_credentials() -> None:
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return

    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
    credentials_base64 = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS_JSON_BASE64", ""
    ).strip()
    if not credentials_json and credentials_base64:
        credentials_json = base64.b64decode(credentials_base64).decode("utf-8")

    if not credentials_json:
        return

    credentials_path = Path(tempfile.gettempdir()) / "hastakala-google-credentials.json"
    credentials_path.write_text(credentials_json, encoding="utf-8")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
