# ComfyUI-AHP_BatchCropByMask

**AHP Batch Crop By Mask** crops a batch of images and masks to the object in each mask. Unlike the single-image crop node it's based on, it accepts batches, and it can give you one shared crop size for the whole batch or a separate box for each frame.

- Node name in ComfyUI: **AHP Batch Crop By Mask**
- Category: `AHP/image`
- Author: **Ali Haghighat panah**
- License: MIT (see [LICENSE](LICENSE))

---

## How it works

For each frame, the node:

1. **Pairs the image and mask.** Frame *i* of the image batch goes with frame *i* of the mask batch. A batch of 1 is reused for every frame of the other input.
2. **Inverts the mask (optional).** If `invert_mask` is on, the mask becomes `1 − mask`.
3. **Finds the object.** The `detect` mode decides how the box is found: from all mask pixels, from the largest object, or as the largest rectangle that fits inside the mask.
4. **Sets the box.** The `box_mode` decides whether all frames share one box or each frame has its own. The reserves add or remove margin, the box is kept inside the canvas, and the size can be rounded up to a multiple.
5. **Crops.** The image, the mask, and a preview are cut to the box. Any part of the box that falls outside the frame is filled with zeros.
6. **Stacks the results.** Outputs are returned as batches. In `per_image` mode, smaller crops are padded so the batch has one size.

## Batch behavior

| Image batch | Mask batch | Result |
|---|---|---|
| N | N | Frame *i* uses image *i* and mask *i* |
| N | 1 | The one mask crops every image |
| 1 | N | The one image is cropped by each mask |
| N | M (N ≠ M, neither is 1) | Error: the batch sizes do not match |

## Using with AHP Separate Masks

1. Connect your image batch to `image`.
2. Connect `mask` from **AHP Separate Masks** to `mask`, and `frame_index` to `object_frames`.
3. Set `box_mode` to `per_image`.

Each object is cropped from the image of the frame it came from, and the crops are padded to the same size for batching. Use `box_preview` to check each crop.

Without `object_frames`, the mask batch and image batch must match in size, or one of them must be a single item.

## Mask quality

Mask values are passed through without changes. Nothing is clamped, rounded, or thresholded in the crop, so soft edges and anti-aliased values stay exactly as they were in the input. Detection uses a 0.5 level only to find the box, and that level never touches the output.

## Box modes

| Mode | What you get | When to use it |
|---|---|---|
| `union` | One box that covers the object in every frame. All crops are the same size | Video frames or a sequence where the object should stay in the same place |
| `per_image` | A box for each frame. Crops are padded with zeros to the largest size, top-left aligned | Each frame has its object in a different place or size |

In `per_image` mode, the `crop_box` output has one box per frame. Use the `box_preview` output to check the boxes visually.

## Detection modes

| Mode | Box comes from | Notes |
|---|---|---|
| `mask_area` | Every pixel that's part of the mask | Default. Includes small stray pixels |
| `min_bounding_rect` | The largest connected object | Ignores small separate objects |
| `max_inscribed_rect` | The largest rectangle that fits completely inside the mask | Good for cropping a clean area without any background. Slower on large images (about 0.15 s for 1024 × 1024) |

## Inputs

### Required

| Input | Default | What it does |
|---|---|---|
| `image` | — | Images to crop. One per frame, or a single image |
| `mask` | — | Masks that define the object. One per frame, or a single mask |
| `invert_mask` | off | Flips the mask (1 − mask) before detection |
| `detect` | mask_area | `mask_area`, `min_bounding_rect`, or `max_inscribed_rect` |
| `box_mode` | union | `union` or `per_image` |
| `top_reserve` | 20 | Extra pixels above the object. Negative values shrink the box |
| `bottom_reserve` | 20 | Extra pixels below the object. Negative values shrink the box |
| `left_reserve` | 20 | Extra pixels to the left of the object. Negative values shrink the box |
| `right_reserve` | 20 | Extra pixels to the right of the object. Negative values shrink the box |
| `round_to_multiple` | None | Rounds the crop width and height up to a multiple of 8, 16, 32, 64, 128, 256, or 512, centered |

### Optional

| Input | What it does |
|---|---|
| `object_frames` | Connect `frame_index` from AHP Separate Masks. Each mask is cropped from the image of the frame it came from |
| `crop_box` | A fixed box `(x1, y1, x2, y2)` used for every frame. Skips detection, reserves, and rounding |

## Outputs

| Output | Type | What it contains |
|---|---|---|
| `cropped_image` | IMAGE batch | The cropped images. The channel count matches the input |
| `cropped_mask` | MASK batch | The cropped masks |
| `crop_box` | BOX | A list of `[x1, y1, x2, y2]` boxes, one per frame. In `union` mode, every entry is the same |
| `box_preview` | IMAGE batch | The mask for each frame, with the detected object in red and the final crop box in green |

## Differences from the original CropByMask V3

The original node in ComfyUI_LayerStyle handles one image and one mask. This version:

| Area | Original (CropByMask V3) | This version |
|---|---|---|
| Batch input | Uses the first mask only | Pairs images and masks frame by frame, with broadcasting for single inputs |
| Batch output | Images of different sizes can't be stacked | `union` mode gives one size. `per_image` mode pads to the largest |
| Box per frame | One box | One box per frame, returned as a list |
| Dependencies | Needs the whole ComfyUI_LayerStyle package (`imagefunc.py`) | Standalone. Only numpy, OpenCV, Pillow, and torch are needed |
| Largest inscribed rectangle | Tries rectangles between contour points | Histogram-based search over the mask pixels. Finds the largest rectangle fully inside the mask |
| Empty masks | Returns an unclear box | Falls back to the full frame, with a printed warning |
| Reserve clamping | Box clamped to the canvas | Same, plus a minimum size of 1 pixel when reserves shrink the box to nothing |
| Output channels | Always RGBA | Same as the input |

## Installation

Clone into your `ComfyUI/custom_nodes` folder and install the requirements:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/ComfyUI-AHP_BatchCropByMask.git
pip install -r ComfyUI-AHP_BatchCropByMask/requirements.txt
```

Restart ComfyUI. Double-click the canvas and search for **AHP Batch Crop By Mask**.

## Running the tests

```bash
cd ComfyUI-AHP_BatchCropByMask
python tests/test_ahp_batch_crop_by_mask.py
```

The tests run without ComfyUI.

## Credits

- **Author and batch modifications:** Ali Haghighat panah
- **Original node:** CropByMask V3 from [ComfyUI_LayerStyle](https://github.com/chflame163/ComfyUI_LayerStyle) by chflame163, MIT License
- **Development assistance:** Claude (Anthropic)

## License

MIT License. The original copyright notice from ComfyUI_LayerStyle is kept in [LICENSE](LICENSE), along with the author's copyright for the changes.
