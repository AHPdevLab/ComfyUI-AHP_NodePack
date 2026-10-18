"""
AHP Image Crop Fit Canvas

Places a cut-out product in the middle of a fixed-size canvas, ready for a
watermark and for a product website.

Steps for each image:
1. Crop to the object, using the mask (or the alpha channel if the mask is empty).
2. Scale it to fit the inner box, using the chosen scaling mode.
3. Centre it in the inner box on the canvas.

Layout, in pixels:
- canvas_padding:    the margin between the canvas edge and the working area.
- inner_box_padding: the extra space inside the working area, around the object.

Scaling modes:
- smart_fit:      fits the object, and for very wide, low objects it may use part
                  of the inner box padding, so the object is shown larger.
- fit:            fits the whole object inside the inner box, keeping its shape.
- fit_no_upscale: like fit, but never makes the object larger than its original size.
- fill:           covers the inner box and crops the edges of the object.
- stretch:        fills the inner box exactly, ignoring the aspect ratio.

Background: white or black fill for RGB output. "transparent" gives an RGBA
image with transparent surroundings. Transparent areas of an RGBA input are
composited onto the chosen background.

The cropping, scaling and centring logic is adapted from the "fit to canvas"
script by Ali Haghighat Panah, with pixel-based inputs, the scaling modes, the
smart fit rule, an optional mask input and the background choice added.

Licensed under the GNU General Public License v3.0. See LICENSE.
"""

import numpy as np
import torch
from PIL import Image

try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # Pillow older than 9.1
    RESAMPLE = Image.LANCZOS


# Pixels above this value count as part of the object.
OBJECT_THRESHOLD = 0.01

# Smart fit: a "very wide, low" object is one whose width is at least this many
# times its height. Its fitted height must also be below this share of the canvas
# height before the rule applies.
SMART_WIDE_RATIO = 2.5
SMART_MIN_HEIGHT_RATIO = 0.35

# Smart fit: the share of the inner box padding that a wide, low object may use
# on each side. 0.5 means it may use half of the inner padding, so it stays
# clear of the canvas padding.
SMART_BLEED_FRACTION = 0.5

SCALING_MODES = ["smart_fit", "fit", "fit_no_upscale", "fill", "stretch"]
BACKGROUNDS = ["white", "black", "transparent"]
BACKGROUND_RGB = {"white": (1.0, 1.0, 1.0), "black": (0.0, 0.0, 0.0)}


def _object_bbox(img, mask):
    """
    Bounding box of the object as (x0, y0, x1, y1).

    Uses the mask first. If the mask is empty and the image has an alpha channel,
    it uses the alpha channel. If neither has any content, it uses the whole image.
    """
    H, W = mask.shape
    obj = mask > OBJECT_THRESHOLD
    if not obj.any() and img.shape[-1] == 4:
        alpha = img[..., 3] > OBJECT_THRESHOLD
        if alpha.any() and not alpha.all():
            obj = alpha
    if not obj.any():
        obj = np.ones((H, W), dtype=bool)
    ys, xs = np.where(obj)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _resize(arr, new_w, new_h):
    """Lanczos resize. arr is float in [0, 1], shaped (H, W) or (H, W, C)."""
    arr8 = np.round(np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8)
    if arr8.ndim == 3 and arr8.shape[-1] == 1:
        arr8 = arr8[..., 0]
    pil = Image.fromarray(arr8).resize((new_w, new_h), RESAMPLE)
    return np.asarray(pil, dtype=np.float32) / 255.0


def _boxes(canvas_w, canvas_h, canvas_pad, inner_pad):
    """Return (outer_box, inner_box), each as (x0, y0, x1, y1)."""
    outer = (canvas_pad, canvas_pad, canvas_w - canvas_pad, canvas_h - canvas_pad)
    inner = (
        outer[0] + inner_pad,
        outer[1] + inner_pad,
        outer[2] - inner_pad,
        outer[3] - inner_pad,
    )
    return outer, inner


def _target_size(w, h, box_w, box_h, mode, inner_pad, canvas_h):
    """Return the resized (width, height) of the object, before any cropping."""
    if mode == "stretch":
        return box_w, box_h

    fit = min(box_w / w, box_h / h)

    if mode == "fit":
        scale = fit
    elif mode == "fit_no_upscale":
        scale = min(1.0, fit)
    elif mode == "fill":
        scale = max(box_w / w, box_h / h)
    elif mode == "smart_fit":
        scale = fit
        fitted_height_ratio = fit * h / canvas_h
        if w / h >= SMART_WIDE_RATIO and fitted_height_ratio < SMART_MIN_HEIGHT_RATIO:
            # Let the wide object use part of the inner padding on each side.
            # Height stays inside the inner box, so only the width grows.
            bleed = inner_pad * SMART_BLEED_FRACTION
            relaxed = min((box_w + 2 * bleed) / w, box_h / h)
            scale = max(scale, relaxed)
    else:
        raise ValueError(f"Unknown scaling mode: {mode}")

    return max(1, round(w * scale)), max(1, round(h * scale))


def _paste(dst, src, x, y):
    """Copy src into dst with its top-left corner at (x, y), clipped to dst."""
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    dst[y0:y1, x0:x1] = src[y0 - y:y1 - y, x0 - x:x1 - x]


def _process_one(img, msk, canvas_w, canvas_h, canvas_pad, inner_pad, mode, background):
    """Return (canvas_image, canvas_mask) for one image and its mask."""
    C = img.shape[-1]
    _, inner = _boxes(canvas_w, canvas_h, canvas_pad, inner_pad)
    box_x0, box_y0, box_x1, box_y1 = inner
    box_w, box_h = box_x1 - box_x0, box_y1 - box_y0

    # 1. Crop to the object.
    bx0, by0, bx1, by1 = _object_bbox(img, msk)
    img_c = img[by0:by1, bx0:bx1]
    msk_c = msk[by0:by1, bx0:bx1]
    h, w = msk_c.shape

    # 2. Size the object for the chosen mode.
    new_w, new_h = _target_size(w, h, box_w, box_h, mode, inner_pad, canvas_h)
    img_r = _resize(img_c, new_w, new_h)
    msk_r = _resize(msk_c, new_w, new_h)

    # Fill covers the box, so trim the overflow here to keep the edges
    # inside the inner box.
    if mode == "fill":
        pw, ph = min(new_w, box_w), min(new_h, box_h)
        cx, cy = (new_w - pw) // 2, (new_h - ph) // 2
        img_r = img_r[cy:cy + ph, cx:cx + pw]
        msk_r = msk_r[cy:cy + ph, cx:cx + pw]
        new_w, new_h = pw, ph

    # 3. Centre it in the inner box.
    ox = box_x0 + (box_w - new_w) // 2
    oy = box_y0 + (box_h - new_h) // 2

    obj_rgb = img_r[..., :3]
    obj_alpha = img_r[..., 3] if C == 4 else np.ones((new_h, new_w), dtype=np.float32)

    if background == "transparent":
        canvas_img = np.zeros((canvas_h, canvas_w, 4), dtype=np.float32)
        obj_out = np.dstack([obj_rgb, obj_alpha])
        _paste(canvas_img, obj_out, ox, oy)
    else:
        bg = np.array(BACKGROUND_RGB[background], dtype=np.float32)
        canvas_img = np.empty((canvas_h, canvas_w, 3), dtype=np.float32)
        canvas_img[:] = bg
        # Composite the object over the background, so transparent parts of
        # an RGBA input take the background colour.
        blended = obj_rgb * obj_alpha[..., None] + bg * (1.0 - obj_alpha[..., None])
        _paste(canvas_img, blended, ox, oy)

    canvas_mask = np.zeros((canvas_h, canvas_w), dtype=np.float32)
    _paste(canvas_mask, msk_r, ox, oy)
    return canvas_img, canvas_mask


def fit_image_to_canvas(image, mask, canvas_w, canvas_h, canvas_pad, inner_pad, mode, background):
    """
    Apply the fit to every image in the batch.

    image: torch tensor [B, H, W, C], values in [0, 1]
    mask:  torch tensor [B, H, W], or None. If None, the alpha channel is used.
    """
    device = image.device
    img_all = image.detach().cpu().float().numpy()
    B, _, _, C = img_all.shape

    if mask is None:
        if C == 4:
            msk_all = img_all[..., 3].copy()
        else:
            msk_all = np.ones(img_all.shape[:3], dtype=np.float32)
    else:
        msk_all = mask.detach().cpu().float().numpy()

    out_imgs, out_masks = [], []
    for i in range(B):
        msk = msk_all[min(i, msk_all.shape[0] - 1)]
        canvas_img, canvas_mask = _process_one(
            img_all[i], msk, canvas_w, canvas_h, canvas_pad, inner_pad, mode, background
        )
        out_imgs.append(canvas_img)
        out_masks.append(canvas_mask)

    result = torch.from_numpy(np.stack(out_imgs)).to(device)
    mask_result = torch.from_numpy(np.stack(out_masks)).to(device)
    return result, mask_result


class AHPImageCropFitCanvas:
    """Crops a cut-out product and centres it on a fixed canvas."""

    CATEGORY = "AHP/Image"
    FUNCTION = "fit"
    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "canvas_width": ("INT", {"default": 1080, "min": 64, "max": 16384, "step": 8}),
                "canvas_height": ("INT", {"default": 1080, "min": 64, "max": 16384, "step": 8}),
                "canvas_padding": ("INT", {"default": 80, "min": 0, "max": 8192, "step": 1}),
                "inner_box_padding": ("INT", {"default": 40, "min": 0, "max": 8192, "step": 1}),
                "scaling_mode": (SCALING_MODES, {"default": "smart_fit"}),
                "background": (BACKGROUNDS, {"default": "white"}),
            },
            "optional": {
                "mask": ("MASK",),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, canvas_width, canvas_height, canvas_padding, inner_box_padding, **_):
        smallest = min(canvas_width, canvas_height)
        if 2 * (canvas_padding + inner_box_padding) >= smallest:
            return (
                "The paddings leave no room for the object. Reduce canvas_padding or "
                "inner_box_padding, or use a larger canvas."
            )
        return True

    def fit(self, image, canvas_width, canvas_height, canvas_padding, inner_box_padding,
            scaling_mode, background, mask=None):
        return fit_image_to_canvas(
            image, mask,
            canvas_w=int(canvas_width),
            canvas_h=int(canvas_height),
            canvas_pad=int(canvas_padding),
            inner_pad=int(inner_box_padding),
            mode=scaling_mode,
            background=background,
        )


NODE_CLASS_MAPPINGS = {
    "AHP_ImageCropFitCanvas": AHPImageCropFitCanvas,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AHP_ImageCropFitCanvas": "AHP Image Crop Fit Canvas",
}
