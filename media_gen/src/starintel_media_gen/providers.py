from __future__ import annotations

import base64
import os
import time
from pathlib import Path

from .models import RouteDecision


def generate_image(decision: RouteDecision, prompt: str, output: Path, *, aspect_ratio: str = "16:9") -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if decision.provider == "openai":
        return _openai_image(decision.model, prompt, output)
    if decision.provider == "google":
        return _google_image(decision.model, prompt, output, aspect_ratio)
    raise ValueError(decision.provider)


def generate_video(
    decision: RouteDecision,
    prompt: str,
    output: Path,
    *,
    reference_images: tuple[str, ...] = (),
    aspect_ratio: str = "16:9",
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if decision.provider == "google":
        return _google_video(decision.model, prompt, output, reference_images, aspect_ratio)
    raise RuntimeError("OpenAI video execution is intentionally disabled by default because the current Videos API is deprecated")


def _openai_image(model: str, prompt: str, output: Path) -> Path:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("install media_gen dependencies with `uv sync --project media_gen`") from exc
    client = OpenAI(api_key=_required("OPENAI_API_KEY"))
    result = client.images.generate(model=model, prompt=prompt, size="1536x1024", quality="high")
    encoded = result.data[0].b64_json
    if not encoded:
        raise RuntimeError("OpenAI image response did not include b64_json")
    output.write_bytes(base64.b64decode(encoded))
    return output


def _google_image(model: str, prompt: str, output: Path, aspect_ratio: str) -> Path:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("install media_gen dependencies with `uv sync --project media_gen`") from exc
    client = genai.Client(api_key=_required("GEMINI_API_KEY"))
    interaction = client.interactions.create(
        model=model,
        input=prompt,
        response_format={"type": "image", "aspect_ratio": aspect_ratio, "image_size": "4K"},
    )
    image = interaction.output_image
    if not image:
        raise RuntimeError("Gemini image response did not include output_image")
    output.write_bytes(base64.b64decode(image.data))
    return output


def _google_video(
    model: str,
    prompt: str,
    output: Path,
    reference_images: tuple[str, ...],
    aspect_ratio: str,
) -> Path:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError("install media_gen dependencies with `uv sync --project media_gen`") from exc
    client = genai.Client(api_key=_required("GEMINI_API_KEY"))
    references = []
    for path in reference_images[:3]:
        data = Path(path).read_bytes()
        suffix = Path(path).suffix.casefold()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        references.append(types.VideoGenerationReferenceImage(image=types.Image(image_bytes=data, mime_type=mime), reference_type="asset"))
    config = types.GenerateVideosConfig(aspect_ratio=aspect_ratio, reference_images=references or None)
    operation = client.models.generate_videos(model=model, prompt=prompt, config=config)
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)
    video = operation.response.generated_videos[0].video
    client.files.download(file=video)
    video.save(str(output))
    return output


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value
