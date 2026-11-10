from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def safe_name(name: str) -> str:
    stem = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", Path(name).stem)[:80] or "image"
    suffix = Path(name).suffix.lower()
    return stem + (suffix if suffix in IMAGE_EXTENSIONS else ".png")


def inspect_bytes(raw: bytes) -> dict:
    with Image.open(io.BytesIO(raw)) as image:
        image.verify()
    with Image.open(io.BytesIO(raw)) as image:
        width, height = image.size
        fmt = (image.format or "PNG").lower()
    return {"width": width, "height": height, "format": fmt, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def save_image(raw: bytes, original_name: str, root: Path) -> dict:
    info = inspect_bytes(raw)
    ext = ".jpg" if info["format"] in ("jpg", "jpeg") else ".png"
    filename = info["sha256"][:16] + ext
    originals = root / "originals"; thumbs = root / "thumbs"
    originals.mkdir(parents=True, exist_ok=True); thumbs.mkdir(parents=True, exist_ok=True)
    path = originals / filename
    if not path.exists(): path.write_bytes(raw)
    with Image.open(io.BytesIO(raw)) as image:
        preview = ImageOps.exif_transpose(image).convert("RGB")
        preview.thumbnail((640, 420))
        thumb_path = thumbs / (info["sha256"][:16] + ".jpg")
        preview.save(thumb_path, format="JPEG", quality=86, optimize=True)
    return {"sha256": info["sha256"], "filename": safe_name(original_name), "stored_path": str(path.relative_to(root.parent)), "thumb_path": str(thumb_path.relative_to(root.parent)), "media_type": "image", "width": info["width"], "height": info["height"], "size_bytes": info["size_bytes"]}


def resolve(root: Path, stored_path: str) -> Path:
    path = (root.parent / stored_path).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("素材路径超出项目目录")
    return path
