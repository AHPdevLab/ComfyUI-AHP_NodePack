# AHP Batch Crop By Mask
# Copyright (C) 2026 Ali Haghighat panah
#
# Based on CropByMaskV3 from ComfyUI_LayerStyle by chflame163
# (https://github.com/chflame163/ComfyUI_LayerStyle, py/crop_by_mask_v3.py), MIT License.
# Batch support, box modes, padding, and the largest-rectangle search were written by
# Ali Haghighat panah. Development was assisted by Claude (Anthropic).
#
# Licensed under the MIT License. See LICENSE.

from inspect import cleandoc

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw

DETECT_MODES = ["mask_area", "min_bounding_rect", "max_inscribed_rect"]
BOX_MODES = ["union", "per_image"]
MULTIPLES = ["8", "16", "32", "64", "128", "256", "512", "None"]


# ----------------------------------------------------------------- helpers

def round_up(number, multiple):
    return ((number + multiple - 1) // multiple) * multiple


def largest_rectangle(binary):
    """Largest axis-aligned rectangle made only of True pixels. Returns (x, y, w, h) or None."""
    H, W = binary.shape
    heights = [0] * W
    best_area, best = 0, None
    for y in range(H):
        row = binary[y].tolist()
        for x in range(W):
            heights[x] = heights[x] + 1 if row[x] else 0
        stack = []  # entries: (start_x, bar_height)
        for x in range(W + 1):
            h = heights[x] if x < W else 0
            start = x
            while stack and stack[-1][1] >= h:
                sx, sh = stack.pop()
                area = sh * (x - sx)
                if area > best_area:
                    best_area = area
                    best = (sx, y - sh + 1, x - sx, sh)
                start = sx
            stack.append((start, h))
    return best


def detect_box(binary, method):
    """binary: 2D bool array. Returns (x, y, w, h), or None when the mask is empty."""
    if not binary.any():
        return None
    if method == "mask_area":
        ys, xs = np.where(binary)
        return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
    if method == "min_bounding_rect":
        contours, _ = cv2.findContours(binary.astype(np.uint8) * 255, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        best, best_area = None, -1
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w * h > best_area:
                best, best_area = (int(x), int(y), int(w), int(h)), w * h
        return best
    return largest_rectangle(binary)


def finalize_box(box, W, H, top, bottom, left, right, multiple):
    """Apply reserves (clamped to the canvas), then round the size up to a multiple, centered."""
    x, y, w, h = box
    x1 = max(x - left, 0)
    y1 = max(y - top, 0)
    x2 = min(x + w + right, W)
    y2 = min(y + h + bottom, H)
    if x2 <= x1:
        x2 = min(x1 + 1, W)
    if y2 <= y1:
        y2 = min(y1 + 1, H)
    if multiple:
        width = round_up(x2 - x1, multiple)
        height = round_up(y2 - y1, multiple)
        x1 -= (width - (x2 - x1)) // 2
        y1 -= (height - (y2 - y1)) // 2
        x2 = x1 + width
        y2 = y1 + height
    return int(x1), int(y1), int(x2), int(y2)


def crop_with_fill(t, box):
    """Crop a (H, W, ...) tensor. Areas outside the canvas are filled with zeros."""
    x1, y1, x2, y2 = box
    H, W = t.shape[0], t.shape[1]
    out = torch.zeros((y2 - y1, x2 - x1) + tuple(t.shape[2:]), dtype=t.dtype)
    sx1, sy1 = max(x1, 0), max(y1, 0)
    sx2, sy2 = min(x2, W), min(y2, H)
    if sx2 > sx1 and sy2 > sy1:
        out[sy1 - y1:sy2 - y1, sx1 - x1:sx2 - x1] = t[sy1:sy2, sx1:sx2]
    return out


def pad_to(t, h, w):
    """Place a (h0, w0, ...) tensor at the top-left of a zero canvas of size (h, w)."""
    out = torch.zeros((h, w) + tuple(t.shape[2:]), dtype=t.dtype)
    out[:t.shape[0], :t.shape[1]] = t
    return out


def pair_inputs(image, mask, object_frames=None):
    """Match image and mask batches.

    object_frames: optional list from AHP_SeparateMasks. object_frames[i] is the frame that
    mask i came from, so mask i is cropped from image[object_frames[i]]. A single image is reused.

    Without object_frames, a batch of 1 is repeated to match the other input.
    """
    if image.dim() == 3:
        image = image.unsqueeze(0)
    if mask.dim() == 2:
        mask = mask.unsqueeze(0)

    if object_frames is not None:
        frames = [int(f) for f in object_frames]
        if len(frames) == 0:
            raise ValueError("object_frames is empty, so there is nothing to crop.")
        if mask.shape[0] != len(frames):
            raise ValueError(f"object_frames has {len(frames)} entries but the mask batch has {mask.shape[0]} mask(s).")
        bi = image.shape[0]
        if bi == 1:
            index = [0] * len(frames)
        else:
            if min(frames) < 0 or max(frames) >= bi:
                raise ValueError(f"object_frames refers to frame {max(frames)}, but the image batch has only {bi} image(s).")
            index = frames
        image = image[index]
    else:
        bi, bm = image.shape[0], mask.shape[0]
        if bi == bm:
            pass
        elif bm == 1:
            mask = mask.expand(bi, -1, -1)
        elif bi == 1:
            image = image.expand(bm, -1, -1, -1)
        else:
            raise ValueError(f"Batch sizes do not match: {bi} image(s) and {bm} mask(s). "
                             f"Use the same count, or 1 for one of them, or connect frame_index from AHP_SeparateMasks.")

    if image.shape[1] != mask.shape[1] or image.shape[2] != mask.shape[2]:
        raise ValueError(f"Image size {tuple(image.shape[1:3])} and mask size {tuple(mask.shape[1:3])} differ.")
    return image, mask


def draw_preview(mask_frame, detected, box):
    """Mask as a gray picture with the detected object in red and the final crop box in green."""
    gray = (mask_frame.numpy() * 255).astype(np.uint8)
    img = Image.fromarray(gray).convert("RGB")
    draw = ImageDraw.Draw(img)
    line = max(2, (img.width + img.height) // 200)
    if detected is not None:
        x, y, w, h = detected
        draw.rectangle((x, y, x + w - 1, y + h - 1), outline=(255, 0, 0), width=line)
    x1, y1, x2, y2 = box
    draw.rectangle((x1, y1, x2 - 1, y2 - 1), outline=(0, 255, 0), width=line)
    return torch.from_numpy(np.asarray(img).astype(np.float32) / 255.0)


# ----------------------------------------------------------------- node

class AHP_BatchCropByMask:
    """
    Crops a batch of images and masks to the object in each mask.

    Pairing
    -------
    Image and mask batches are paired frame by frame. A batch of 1 is reused for every frame
    of the other input, so one mask can crop a whole image batch, or one image can be cropped
    by each mask in a batch.

    If object_frames is connected (from AHP Separate Masks), each mask is paired with the
    frame it came from, so one image batch can be cropped by masks from several frames.

    Mask values are never changed, so soft edges and anti-aliasing pass through unchanged.

    box_mode
    --------
    union:
        One box covers the object in every frame. All outputs have the same size.
    per_image:
        Each frame gets its own box. Smaller crops are padded with zeros (top-left aligned)
        so the batch can be stacked. The crop_box output lists each frame's box.

    detect
    ------
    mask_area:
        Bounding box of all mask pixels.
    min_bounding_rect:
        Bounding box of the largest connected object.
    max_inscribed_rect:
        Largest rectangle that fits entirely inside the mask. Slower on large images.

    Class methods
    -------------
    INPUT_TYPES (dict):
        Tell the main program input parameters of nodes.
    IS_CHANGED:
        optional method to control when the node is re executed.

    Attributes
    ----------
    RETURN_TYPES (`tuple`):
        The type of each element in the output tuple.
    RETURN_NAMES (`tuple`):
        Optional: The name of each output in the output tuple.
    FUNCTION (`str`):
        The name of the entry-point method. Here it is "crop_by_mask".
    OUTPUT_NODE ([`bool`]):
        If this node is an output node. Assumed to be False if not present.
    CATEGORY (`str`):
        The category the node should appear in the UI.
    crop_by_mask(...) -> tuple:
        The entry point method. Its name must be the same as the value of property `FUNCTION`.
    """

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        """
            Return a dictionary which contains config for all input fields.

            Returns: `dict`:
                - Key input_fields_group (`string`): Can be either required, hidden or optional.
                - Value input_fields (`dict`): Contains input fields config.
        """
        reserve = {"default": 20, "min": -9999, "max": 9999, "step": 1}
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Images to crop. One per frame, or a single image to reuse."}),
                "mask": ("MASK", {"tooltip": "Masks that define the object in each frame. One per frame, or a single mask to reuse."}),
                "invert_mask": ("BOOLEAN", {"default": False, "tooltip": "Invert every mask (1 - mask) before detection."}),
                "detect": (DETECT_MODES, {"tooltip": "How the crop box is found from the mask."}),
                "box_mode": (BOX_MODES, {"tooltip": "union: one box for the whole batch. per_image: a box for each frame, padded to the largest."}),
                "top_reserve": ("INT", {**reserve, "tooltip": "Extra pixels above the object. Negative values shrink the box."}),
                "bottom_reserve": ("INT", {**reserve, "tooltip": "Extra pixels below the object. Negative values shrink the box."}),
                "left_reserve": ("INT", {**reserve, "tooltip": "Extra pixels to the left of the object. Negative values shrink the box."}),
                "right_reserve": ("INT", {**reserve, "tooltip": "Extra pixels to the right of the object. Negative values shrink the box."}),
                "round_to_multiple": (MULTIPLES, {"tooltip": "Round the crop width and height up to this multiple, centered. Useful for models that need sizes like 64 or 512."}),
            },
            "optional": {
                "crop_box": ("BOX", {"tooltip": "A fixed box (x1, y1, x2, y2) for every frame. Skips detection and reserves."}),
                "object_frames": ("AHP_FRAME_INDEX", {"tooltip": "Connect frame_index from AHP Separate Masks. Each mask is cropped from the image of the frame it came from."}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "BOX", "IMAGE")
    RETURN_NAMES = ("cropped_image", "cropped_mask", "crop_box", "box_preview")
    FUNCTION = "crop_by_mask"
    OUTPUT_NODE = False
    CATEGORY = "AHP/image"
    DESCRIPTION = cleandoc(__doc__)

    def crop_by_mask(self, image, mask, invert_mask, detect, box_mode,
                     top_reserve, bottom_reserve, left_reserve, right_reserve,
                     round_to_multiple, crop_box=None, object_frames=None):
        image, mask = pair_inputs(image, mask, object_frames)
        image = image.cpu()
        # Mask values are passed through unchanged (no clamping or rounding), so soft edges survive.
        masks = mask.detach().float().cpu()
        if invert_mask:
            masks = 1.0 - masks

        N, H, W = masks.shape[0], masks.shape[1], masks.shape[2]
        multiple = None if round_to_multiple == "None" else int(round_to_multiple)
        reserves = (top_reserve, bottom_reserve, left_reserve, right_reserve)

        # Step 1: find each frame's object.
        detected = [detect_box(masks[i].numpy() >= 0.5, detect) for i in range(N)]

        # Step 2: decide the final crop box for each frame.
        if crop_box is not None:
            fixed = tuple(int(v) for v in crop_box)
            finals = [fixed] * N
        elif box_mode == "union":
            valid = [d for d in detected if d is not None]
            if valid:
                x1 = min(d[0] for d in valid)
                y1 = min(d[1] for d in valid)
                x2 = max(d[0] + d[2] for d in valid)
                y2 = max(d[1] + d[3] for d in valid)
                union = (x1, y1, x2 - x1, y2 - y1)
            else:
                union = (0, 0, W, H)
                print("# AHP Batch Crop By Mask -> warning: all masks are empty, cropping the full frame.")
            finals = [finalize_box(union, W, H, *reserves, multiple)] * N
        else:  # per_image
            finals = []
            for d in detected:
                if d is None:
                    d = (0, 0, W, H)
                    print("# AHP Batch Crop By Mask -> warning: an empty mask was found, cropping the full frame for it.")
                finals.append(finalize_box(d, W, H, *reserves, multiple))

        # Step 3: crop images, masks, and build previews.
        crop_imgs, crop_masks, previews = [], [], []
        for i in range(N):
            box = finals[i]
            crop_imgs.append(crop_with_fill(image[i], box))
            crop_masks.append(crop_with_fill(masks[i], box))
            previews.append(draw_preview(masks[i], detected[i], box))

        # Step 4: stack. Per-image crops are padded to the largest size so they can be batched.
        out_h = max(c.shape[0] for c in crop_imgs)
        out_w = max(c.shape[1] for c in crop_imgs)
        out_images = torch.stack([pad_to(c, out_h, out_w) for c in crop_imgs], dim=0)
        out_masks = torch.stack([pad_to(c, out_h, out_w) for c in crop_masks], dim=0)
        out_previews = torch.stack(previews, dim=0)

        boxes = [list(b) for b in finals]
        print(f"# AHP Batch Crop By Mask -> processed {N} frame(s), box mode: {box_mode if crop_box is None else 'fixed'}")
        return (out_images, out_masks, boxes, out_previews)


# A dictionary that contains all nodes you want to export with their names
# NOTE: names should be globally unique
NODE_CLASS_MAPPINGS = {
    "AHP_BatchCropByMask": AHP_BatchCropByMask,
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "AHP_BatchCropByMask": "AHP Batch Crop By Mask",
}
