"""
Run from the package folder:   python tests/test_ahp_batch_crop_by_mask.py
or with pytest:                python -m pytest tests -q
"""
import importlib.util
import os
import sys

import numpy as np
import torch

PKG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_spec = importlib.util.spec_from_file_location(
    "ahp_bcrop_pkg", os.path.join(PKG_DIR, "__init__.py"), submodule_search_locations=[PKG_DIR]
)
pkg = importlib.util.module_from_spec(_spec)
sys.modules["ahp_bcrop_pkg"] = pkg
_spec.loader.exec_module(pkg)

NODE_MODULE = sys.modules["ahp_bcrop_pkg.ahp_batch_crop_by_mask"]
NODE = pkg.NODE_CLASS_MAPPINGS["AHP_BatchCropByMask"]()


def run(image, mask, detect="mask_area", box_mode="union", invert=False,
        top=0, bottom=0, left=0, right=0, multiple="None", crop_box=None, object_frames=None):
    kwargs = dict(invert_mask=invert, detect=detect, box_mode=box_mode,
                  top_reserve=top, bottom_reserve=bottom, left_reserve=left, right_reserve=right,
                  round_to_multiple=multiple)
    if crop_box is not None:
        kwargs["crop_box"] = crop_box
    if object_frames is not None:
        kwargs["object_frames"] = object_frames
    return NODE.crop_by_mask(image, mask, **kwargs)


def rect_mask(H, W, rects):
    m = torch.zeros(H, W)
    for x, y, w, h in rects:
        m[y:y + h, x:x + w] = 1.0
    return m


def rand_images(n, H=64, W=64, C=3):
    g = torch.Generator().manual_seed(0)
    return torch.rand(n, H, W, C, generator=g)


# ---------------------------------------------------------------- registration

def test_registration():
    assert "AHP_BatchCropByMask" in pkg.NODE_CLASS_MAPPINGS
    assert pkg.NODE_DISPLAY_NAME_MAPPINGS["AHP_BatchCropByMask"] == "AHP Batch Crop By Mask"
    assert NODE.RETURN_TYPES == ("IMAGE", "MASK", "BOX", "IMAGE")
    assert NODE.CATEGORY == "AHP/image"
    inputs = NODE.INPUT_TYPES()
    assert set(inputs["required"]["detect"][0]) == {"mask_area", "min_bounding_rect", "max_inscribed_rect"}
    assert set(inputs["required"]["box_mode"][0]) == {"union", "per_image"}
    assert "crop_box" in inputs["optional"]


# ---------------------------------------------------------------- batch pairing

def test_paired_batch_union_gives_same_size_outputs():
    imgs = rand_images(3)
    masks = torch.stack([
        rect_mask(64, 64, [(10, 10, 20, 20)]),
        rect_mask(64, 64, [(30, 15, 10, 25)]),
        rect_mask(64, 64, [(5, 40, 15, 10)]),
    ])
    out_img, out_mask, boxes, previews = run(imgs, masks, box_mode="union")
    assert out_img.shape[0] == 3 and out_mask.shape[0] == 3
    assert out_img.shape[1:3] == out_mask.shape[1:3]
    assert len(boxes) == 3 and all(b == boxes[0] for b in boxes)
    assert previews.shape == (3, 64, 64, 3)


def test_union_box_covers_all_objects():
    imgs = rand_images(2)
    masks = torch.stack([rect_mask(64, 64, [(10, 10, 5, 5)]), rect_mask(64, 64, [(40, 30, 8, 8)])])
    _, _, boxes, _ = run(imgs, masks, box_mode="union")
    x1, y1, x2, y2 = boxes[0]
    assert (x1, y1, x2, y2) == (10, 10, 48, 38)


def test_per_image_gives_each_frame_its_own_box_and_pads():
    imgs = rand_images(2)
    masks = torch.stack([rect_mask(64, 64, [(5, 5, 10, 10)]), rect_mask(64, 64, [(20, 20, 30, 30)])])
    out_img, out_mask, boxes, _ = run(imgs, masks, box_mode="per_image")
    assert boxes[0] == [5, 5, 15, 15]
    assert boxes[1] == [20, 20, 50, 50]
    assert out_img.shape[1:3] == (30, 30)
    # The smaller crop is top-left aligned, so its bottom and right padding must be zero.
    assert out_mask[0, 10:, :].abs().sum().item() == 0.0
    assert out_mask[0, :, 10:].abs().sum().item() == 0.0
    assert out_img[0, 10:, :, :].abs().sum().item() == 0.0


def test_single_mask_is_reused_for_all_images():
    imgs = rand_images(4)
    mask = rect_mask(64, 64, [(10, 10, 20, 20)])
    out_img, out_mask, boxes, _ = run(imgs, mask)
    assert out_img.shape[0] == 4 and out_mask.shape[0] == 4
    assert len(boxes) == 4


def test_single_image_is_reused_for_all_masks():
    img = rand_images(1)
    masks = torch.stack([rect_mask(64, 64, [(0, 0, 10, 10)]), rect_mask(64, 64, [(30, 30, 10, 10)])])
    out_img, out_mask, _, _ = run(img, masks, box_mode="per_image")
    assert out_img.shape[0] == 2 and out_mask.shape[0] == 2


def test_mismatched_batch_sizes_raise():
    try:
        run(rand_images(2), torch.zeros(3, 64, 64))
    except ValueError as e:
        assert "do not match" in str(e)
    else:
        raise AssertionError("expected ValueError for 2 images and 3 masks")


def test_2d_mask_is_accepted():
    out_img, out_mask, _, _ = run(rand_images(1), rect_mask(64, 64, [(10, 10, 5, 5)]))
    assert out_mask.shape[0] == 1


# ---------------------------------------------------------------- detection

def test_mask_area_is_bounding_box_of_all_pixels():
    m = rect_mask(64, 64, [(10, 10, 5, 5), (40, 40, 5, 5)])
    _, _, boxes, _ = run(rand_images(1), m[None], detect="mask_area")
    assert boxes[0] == [10, 10, 45, 45]


def test_min_bounding_rect_uses_largest_object():
    m = rect_mask(64, 64, [(2, 2, 3, 3), (30, 20, 20, 25)])
    _, _, boxes, _ = run(rand_images(1), m[None], detect="min_bounding_rect")
    assert boxes[0] == [30, 20, 50, 45]


def test_max_inscribed_rect_fits_inside_mask():
    # L-shaped mask: the best inscribed rectangle is the 10x30 vertical bar at the left.
    m = rect_mask(64, 64, [(5, 5, 10, 30), (5, 30, 30, 8)])
    out_img, out_mask, boxes, _ = run(rand_images(1), m[None], detect="max_inscribed_rect")
    x1, y1, x2, y2 = boxes[0]
    inner = m[y1:y2, x1:x2]
    assert inner.min().item() == 1.0, "inscribed rectangle leaves the mask"
    assert (x2 - x1) * (y2 - y1) >= 10 * 30


def test_largest_rectangle_known_answer():
    b = np.zeros((10, 12), dtype=bool)
    b[1:4, 1:6] = True   # 3 x 5 = 15
    b[6:8, 2:12] = True  # 2 x 10 = 20 (best)
    x, y, w, h = NODE_MODULE.largest_rectangle(b)
    assert w * h == 20
    assert b[y:y + h, x:x + w].all()


def test_invert_switch_changes_detection():
    m = rect_mask(64, 64, [(20, 20, 10, 10)])
    _, _, normal, _ = run(rand_images(1), m[None])
    _, _, inverted, _ = run(rand_images(1), m[None], invert=True)
    assert normal[0] == [20, 20, 30, 30]
    assert inverted[0] == [0, 0, 64, 64]


# ---------------------------------------------------------------- reserves and rounding

def test_reserves_expand_and_clamp_to_canvas():
    m = rect_mask(64, 64, [(20, 20, 10, 10)])
    _, _, boxes, _ = run(rand_images(1), m[None], top=5, bottom=5, left=5, right=5)
    assert boxes[0] == [15, 15, 35, 35]
    _, _, edge, _ = run(rand_images(1), rect_mask(64, 64, [(0, 0, 10, 10)])[None], top=20, left=20)
    assert edge[0][:2] == [0, 0]


def test_negative_reserve_shrinks_box():
    m = rect_mask(64, 64, [(20, 20, 10, 10)])
    _, _, boxes, _ = run(rand_images(1), m[None], top=-2, bottom=-2, left=-2, right=-2)
    assert boxes[0] == [22, 22, 28, 28]


def test_round_to_multiple_makes_size_multiple():
    m = rect_mask(128, 128, [(40, 40, 30, 30)])
    out_img, out_mask, _, _ = run(rand_images(1, 128, 128), m[None], multiple="64")
    assert out_img.shape[1] % 64 == 0 and out_img.shape[2] % 64 == 0


def test_round_to_multiple_can_extend_past_canvas_with_zero_fill():
    m = rect_mask(64, 64, [(0, 0, 20, 20)])
    out_img, out_mask, boxes, _ = run(rand_images(1), m[None], multiple="128")
    assert out_img.shape[1] == 128 and out_img.shape[2] == 128
    x1, y1, x2, y2 = boxes[0]
    assert x1 < 0 and y1 < 0  # the crop starts before the canvas
    # The padding before the canvas is zero, and the whole 20x20 object is kept.
    assert out_mask[0, :-y1, :].abs().sum().item() == 0.0
    assert out_mask[0, :, :-x1].abs().sum().item() == 0.0
    assert out_mask[0].sum().item() == 400.0


# ---------------------------------------------------------------- content and channels

def test_crop_content_matches_source_region():
    imgs = rand_images(1)
    m = rect_mask(64, 64, [(10, 12, 20, 18)])
    out_img, out_mask, boxes, _ = run(imgs, m[None])
    x1, y1, x2, y2 = boxes[0]
    assert torch.equal(out_img[0], imgs[0, y1:y2, x1:x2, :])
    assert torch.equal(out_mask[0], m[y1:y2, x1:x2])


def test_channel_count_is_preserved():
    out_img, _, _, _ = run(rand_images(2, C=4), torch.stack([rect_mask(64, 64, [(5, 5, 9, 9)])] * 2))
    assert out_img.shape[-1] == 4


# ---------------------------------------------------------------- empty and fixed boxes

def test_empty_mask_falls_back_to_full_frame():
    out_img, out_mask, boxes, _ = run(rand_images(1), torch.zeros(1, 64, 64))
    assert boxes[0] == [0, 0, 64, 64]
    assert out_img.shape[1:3] == (64, 64)


def test_fixed_crop_box_overrides_detection():
    imgs = rand_images(2)
    masks = torch.stack([rect_mask(64, 64, [(0, 0, 4, 4)])] * 2)
    out_img, out_mask, boxes, _ = run(imgs, masks, crop_box=(10, 10, 50, 40))
    assert out_img.shape[1:3] == (30, 40)
    assert boxes == [[10, 10, 50, 40], [10, 10, 50, 40]]


def test_per_image_boxes_are_returned_as_list_of_four_ints():
    _, _, boxes, _ = run(rand_images(2), torch.stack([rect_mask(64, 64, [(5, 5, 6, 6)])] * 2), box_mode="per_image")
    assert len(boxes) == 2 and all(len(b) == 4 for b in boxes)
    assert all(isinstance(v, int) for b in boxes for v in b)



# ---------------------------------------------------------------- compatibility with AHP Separate Masks

def test_registration_accepts_frame_index():
    opt = NODE.INPUT_TYPES()["optional"]
    assert opt["object_frames"][0] == "AHP_FRAME_INDEX"


def test_object_frames_pairs_each_mask_with_its_own_frame():
    imgs = torch.stack([torch.full((64, 64, 3), 0.2), torch.full((64, 64, 3), 0.8)])
    masks = torch.stack([rect_mask(64, 64, [(5, 5, 10, 10)])] * 4)
    out_img, _, boxes, _ = run(imgs, masks, box_mode="per_image", object_frames=[0, 0, 1, 1])
    assert out_img.shape[0] == 4
    means = [round(out_img[k].mean().item(), 2) for k in range(4)]
    assert means == [0.2, 0.2, 0.8, 0.8]


def test_object_frames_with_single_image_reuses_it():
    img = rand_images(1)
    masks = torch.stack([rect_mask(64, 64, [(5, 5, 10, 10)])] * 3)
    out_img, _, _, _ = run(img, masks, box_mode="per_image", object_frames=[0, 0, 0])
    assert out_img.shape[0] == 3


def test_object_frames_length_must_match_masks():
    try:
        run(rand_images(2), torch.zeros(3, 64, 64), object_frames=[0, 1])
    except ValueError as e:
        assert "object_frames" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_object_frames_out_of_range_raises():
    try:
        run(rand_images(2), torch.zeros(1, 64, 64), object_frames=[5])
    except ValueError as e:
        assert "refers to frame" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_soft_mask_values_pass_through_exactly():
    g = torch.Generator().manual_seed(1)
    m = torch.rand(1, 64, 64, generator=g)
    m[0, 10:50, 10:50] = m[0, 10:50, 10:50].clamp(min=0.05)  # keep a non-trivial object
    out_img, out_mask, boxes, _ = run(rand_images(1), m, box_mode="union")
    x1, y1, x2, y2 = boxes[0]
    assert torch.equal(out_mask[0], m[0, y1:y2, x1:x2])


def test_preview_style_mask_batch_of_five_with_one_image():
    masks = torch.stack([rect_mask(64, 64, [(i * 10, 5, 8, 8)]) for i in range(5)])
    out_img, out_mask, boxes, previews = run(rand_images(1), masks, box_mode="per_image")
    assert out_img.shape[0] == 5 and out_mask.shape[0] == 5
    assert len(boxes) == 5 and previews.shape[0] == 5


if __name__ == "__main__":
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
