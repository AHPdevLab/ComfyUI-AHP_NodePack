"""
AHP Load Image

Loads one image from a file path, chosen in one of two ways:
- Browse Image: a button that opens the operating system's file chooser.
- Typing or pasting the path into the text field.

Preview: a Preview Image button shows the picture as a plain RGB PNG, with
no alpha channel and no mask overlay, the same way ComfyUI's own image
nodes show a picture. Transparent areas are shown on a white background.

Outputs:
- image:     the picture as a ComfyUI IMAGE (RGB, float values 0 to 1)
- mask:      the transparent areas as a MASK (1 = transparent, the same
             convention as ComfyUI's built-in Load Image). All zeros if the
             image has no transparency.
- path:      the full path to the file
- directory: the folder that contains the file

The formats are whatever Pillow can open: PNG, JPEG, WEBP, BMP, TIFF, GIF
(first frame) and others. Camera RAW formats such as CR2 are not supported.

Licensed under the GNU General Public License v3.0. See LICENSE.
"""

import asyncio
import base64
import hashlib
import io
import os

import numpy as np
import torch
from aiohttp import web
from PIL import Image, ImageOps

from ._dialogs import DialogError, clean_path, open_image_dialog

try:
    from server import PromptServer
except ImportError:  # Lets the module be imported outside ComfyUI, e.g. in tests
    PromptServer = None


BROWSE_ROUTE = "/ahp/load_image/select"
PREVIEW_ROUTE = "/ahp/load_image/preview"
PREVIEW_MAX_SIDE = 1024  # Larger photos are scaled down for the preview only

try:
    _LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # Pillow older than 9.1
    _LANCZOS = Image.LANCZOS


def resolve_path(raw):
    """The full, normalised path for what the user typed, or "" if nothing was typed."""
    cleaned = clean_path(raw)
    if not cleaned:
        return ""
    return os.path.abspath(os.path.expanduser(cleaned))


def _has_transparency(img):
    return img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info


def load_image_tensors(full_path):
    """Return (image, mask) as ComfyUI tensors for one file."""
    with Image.open(full_path) as opened:
        img = ImageOps.exif_transpose(opened)  # Respect the camera's rotation tag
        has_alpha = _has_transparency(img)
        rgba = np.asarray(img.convert("RGBA"), dtype=np.float32) / 255.0

    rgb = rgba[..., :3]
    if has_alpha:
        mask = 1.0 - rgba[..., 3]
    else:
        mask = np.zeros(rgb.shape[:2], dtype=np.float32)

    image_tensor = torch.from_numpy(rgb[None].copy())
    mask_tensor = torch.from_numpy(mask[None].copy())
    return image_tensor, mask_tensor


def make_preview_png(full_path):
    """
    Return (base64_png, (width, height)) for a plain RGB preview.

    The preview has no alpha channel and no mask. Transparent areas are
    shown on a white background, and the picture is scaled down to fit
    PREVIEW_MAX_SIDE, keeping its shape.
    """
    with Image.open(full_path) as opened:
        img = ImageOps.exif_transpose(opened)
        if _has_transparency(img):
            rgba = img.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.getchannel("A"))
        else:
            flat = img.convert("RGB")

    flat.thumbnail((PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE), _LANCZOS)
    buffer = io.BytesIO()
    flat.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii"), flat.size


if PromptServer is not None:

    @PromptServer.instance.routes.post(BROWSE_ROUTE)
    async def ahp_select_image(request):
        """Called by the Browse Image button. Responds with {"path": ...}."""
        try:
            body = await request.json()
        except Exception:
            body = {}

        current = resolve_path(body.get("current", "")) if isinstance(body, dict) else ""
        # Start the chooser in the folder of the current file, if there is one.
        start_dir = os.path.dirname(current) if current else ""
        start_dir = start_dir if os.path.isdir(start_dir) else ""

        try:
            chosen = await asyncio.to_thread(open_image_dialog, start_dir)
        except DialogError as error:
            return web.json_response({"path": "", "error": str(error)}, status=500)
        except Exception as error:
            return web.json_response(
                {"path": "", "error": f"Could not open the file dialog: {error}"},
                status=500,
            )

        return web.json_response({"path": chosen, "cancelled": chosen == ""})

    @PromptServer.instance.routes.post(PREVIEW_ROUTE)
    async def ahp_preview_image(request):
        """Called by the Preview Image button. Responds with {"data_url": ...}."""
        try:
            body = await request.json()
        except Exception:
            body = {}

        path = resolve_path(body.get("path", "")) if isinstance(body, dict) else ""
        if not path:
            return web.json_response({"error": "Choose an image first."}, status=400)
        if not os.path.isfile(path):
            return web.json_response({"error": f"No image file found at: {path}"}, status=404)

        try:
            encoded, (width, height) = await asyncio.to_thread(make_preview_png, path)
        except Exception as error:
            return web.json_response({"error": f"Could not preview this file: {error}"}, status=500)

        return web.json_response({
            "data_url": f"data:image/png;base64,{encoded}",
            "width": width,
            "height": height,
        })


class AHPLoadImage:
    """Loads an image from a path and outputs the image, mask, path and folder."""

    CATEGORY = "AHP/Image"
    FUNCTION = "load"
    RETURN_TYPES = ("IMAGE", "MASK", "STRING", "STRING")
    RETURN_NAMES = ("image", "mask", "path", "directory")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": "", "multiline": False}),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, path):
        full_path = resolve_path(path)
        if not full_path:
            return "Choose an image with Browse Image, or enter its path."
        if not os.path.isfile(full_path):
            return f"No image file found at: {full_path}"
        return True

    @classmethod
    def IS_CHANGED(cls, path):
        """Re-run the node when the file changes. Uses the file's size and modification time."""
        full_path = resolve_path(path)
        digest = hashlib.sha256(full_path.encode("utf-8"))
        try:
            stat = os.stat(full_path)
            digest.update(str(stat.st_mtime_ns).encode("utf-8"))
            digest.update(str(stat.st_size).encode("utf-8"))
        except OSError:
            digest.update(b"missing")
        return digest.hexdigest()

    def load(self, path):
        full_path = resolve_path(path)
        if not full_path:
            raise ValueError("AHP Load Image: choose an image with Browse Image, or enter its path.")
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"AHP Load Image: no image file found at: {full_path}")

        image, mask = load_image_tensors(full_path)
        return (image, mask, full_path, os.path.dirname(full_path))


NODE_CLASS_MAPPINGS = {
    "AHP_LoadImage": AHPLoadImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AHP_LoadImage": "AHP Load Image",
}
