# comfyuiAHP_nodepack

A collection of utility nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI), made by AHP. Every node in this pack has the `AHP` prefix, and each node lives in its own file.

The pack has two nodes so far:

- **AHP Folder Picker** has a **Browse Folder** button that opens your operating system's folder dialog. It outputs the chosen folder's full path as a plain string with no quotation marks. It does not use tkinter.
- **AHP Markdown Note** is a text note with a rich Markdown preview. It supports tables, task lists, footnotes, definition lists, math, and right-to-left (RTL) languages such as Persian and Arabic.
- **AHP Load Image** has a **Browse Image** button that opens your system's file chooser. It outputs the image, its mask, the full path, and the folder that contains it.
- **AHP Image Crop Fit Canvas** places a cut-out product in the middle of a fixed-size canvas, with padding, selectable scaling modes, and a smart fit for very wide, low objects. It outputs an image and a mask, ready for a watermark and for a product website.

## Contents

- [Nodes](#nodes)
- [AHP Markdown Note](#ahp-markdown-note)
- [How the AHP Folder Picker works](#how-the-ahp-folder-picker-works)
- [Installation](#installation)
- [Using the AHP Folder Picker](#using-the-ahp-folder-picker)
- [Platform support](#platform-support)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Adding a new AHP node](#adding-a-new-ahp-node)
- [Naming conventions](#naming-conventions)
- [License](#license)

## Nodes

| Display name | Node ID | Category | File | Purpose |
|---|---|---|---|---|
| AHP Folder Picker | `AHP_FolderPicker` | `AHP/Path` | `nodes/ahp_folder_picker.py` | Choose a folder with a button and output its full path as a string |
| AHP Markdown Note | `AHP_MarkdownNote` | `AHP/Text` | `nodes/ahp_markdown_note.py` | Write a note in Markdown, with a live rich preview that supports RTL languages |
| AHP Load Image | `AHP_LoadImage` | `AHP/Image` | `nodes/ahp_load_image.py` | Load an image from a path and output the image, mask, full path and directory |
| AHP Image Crop Fit Canvas | `AHP_ImageCropFitCanvas` | `AHP/Image` | `nodes/ahp_image_crop_fit_canvas.py` | Crop a cut-out product and centre it on a fixed canvas, with padding and scaling modes |

### AHP Folder Picker

**Inputs**

| Name | Type | Widget | Required | Description |
|---|---|---|---|---|
| `folder_path` | STRING | Text field, with a **Browse Folder** button under it | No | The folder path. Click the button to choose a folder, or type or paste a path. Leave it empty if you do not need a folder. |

**Outputs**

| Name | Type | Description |
|---|---|---|
| `folder_path` | STRING | The folder path with no quotation marks. It is an empty string if no folder was chosen. |

### AHP Image Crop Fit Canvas

Places a cut-out product in the middle of a canvas. It is meant for product photos that will get a watermark later and go on a product website.

**Inputs**

| Name | Type | Default | Description |
|---|---|---|---|
| `image` | IMAGE | required | The product image. Transparent (RGBA) or RGB. |
| `canvas_width` | INT | 1080 | Width of the output canvas, in pixels. |
| `canvas_height` | INT | 1080 | Height of the output canvas, in pixels. |
| `canvas_padding` | INT | 80 | Margin between the canvas edge and the working area, in pixels, on every side. |
| `inner_box_padding` | INT | 40 | Extra space inside the working area, around the object, in pixels, on every side. |
| `scaling_mode` | Dropdown | `smart_fit` | How the object is scaled. See the table below. |
| `background` | Dropdown | `white` | `white`, `black`, or `transparent`. |
| `mask` | MASK | none | Marks the object. Optional. If it is missing, the image's alpha channel is used, or the whole image if there is no alpha. |

**Outputs**

| Name | Type | Description |
|---|---|---|
| `image` | IMAGE | The canvas with the centred object. RGB for `white` or `black`. RGBA for `transparent`. |
| `mask` | MASK | The object's position on the canvas. Use it for the watermark or for masking later. |

**Scaling modes**

| Mode | What it does |
|---|---|
| `smart_fit` | Fits the whole object inside the inner box. A very wide, low object may use part of the inner padding, so it looks larger. Recommended for products. |
| `fit` | Fits the whole object inside the inner box, keeping its shape. Never crops. |
| `fit_no_upscale` | Like `fit`, but never enlarges the object beyond its original size. |
| `fill` | Covers the inner box. The edges of the object that fall outside it are cropped. |
| `stretch` | Fills the inner box exactly, ignoring the aspect ratio. Distorts the object. |

**How the smart fit works.** Very wide, low objects, such as a belt, a scarf, or a long bottle, look too small in a square canvas. `smart_fit` checks two things: the object is at least 2.5 times wider than it is tall, and its fitted height is less than 35% of the canvas height. If both are true, the object may extend into up to half of the inner box padding on the left and right. It never touches the canvas padding, and its height stays inside the inner box, so the change is only a little larger. These limits are constants at the top of `nodes/ahp_image_crop_fit_canvas.py` (`SMART_WIDE_RATIO`, `SMART_MIN_HEIGHT_RATIO`, `SMART_BLEED_FRACTION`), and you can change them there.

**Background and transparency.** With `white` or `black`, a transparent part of an RGBA image is blended onto that colour, and the output is RGB. With `transparent`, the output is RGBA with a clear background, and the object keeps its own transparency.

**Mask.** If you connect a mask, the object is cropped to the mask's shape. Without a mask, the alpha channel is used. An RGB image with no mask counts as one whole object.

**Credit.** The cropping, scaling and centring logic is adapted from the "fit to canvas" script by Ali Haghighat Panah. The pixel-based inputs, the scaling modes, the smart fit rule, the optional mask input and the background choice were added for this pack. See the note in the file header.

### AHP Load Image

Loads one image, so you can use the picture and know where it came from.

**Choosing the image.** Click **Browse Image** to open your operating system's file chooser (the Explorer window on Windows, Finder on macOS, or zenity/kdialog on Linux). It shows image files, and it opens in the folder of the current image if there is one. Or type or paste the path into the field. Quotation marks are removed automatically, and `~` is the home folder. The same platform notes as the Folder Picker apply: on a remote or headless server, type the path instead.

**Preview.** Click **Preview Image** to see the picture in the node. The preview is a plain RGB PNG, the same way ComfyUI's own image nodes show a picture. It has no alpha channel and no mask overlay. Transparent areas are shown on a white background, and large photos are scaled down to 1024 pixels for the preview only. The workflow itself still gets the full-size image. The preview also appears after Browse Image, and when a saved workflow loads.

**Inputs**

| Name | Type | Description |
|---|---|---|
| `path` | STRING | The full path to the image file. Set by Browse Image, or typed or pasted. |

**Outputs**

| Name | Type | Description |
|---|---|---|
| `image` | IMAGE | The picture, RGB, values 0 to 1. |
| `mask` | MASK | The transparent areas, with 1 for transparent and 0 for opaque. It is all zeros if the image has no transparency. This matches ComfyUI's built-in Load Image. |
| `path` | STRING | The full path to the file, with no quotation marks. |
| `directory` | STRING | The folder that contains the file. |

**Notes**

- Supported formats are whatever Pillow opens: PNG, JPEG, WEBP, BMP, TIFF and GIF (first frame), among others. Camera RAW formats such as CR2 are not supported by this node.
- The camera's rotation tag is applied, so photos taken in portrait appear upright.
- The workflow re-runs when the file changes.
- If the path is empty or the file does not exist, the node shows a clear error.

### AHP Markdown Note

**Inputs**

| Name | Type | Widget | Required | Description |
|---|---|---|---|---|
| `text` | STRING | Tabbed editor: **Plain text** and **Markdown** | No | The note, written in Markdown. The editor lays out RTL text correctly. |

**Outputs**

| Name | Type | Description |
|---|---|---|
| `markdown` | STRING | The note exactly as written. |
| `html` | STRING | The note rendered to HTML. Every block has `dir="auto"`, so RTL text is laid out right-to-left. |

**Tabs.** The node has two tabs. **Plain text** is the editor, where you write the note. **Markdown** shows the rendered note. The rendering is done by the same Python code that produces the `html` output, so the preview matches the workflow output. Switching to the Markdown tab renders the note, and the tab then updates as you type.

**Supported Markdown**

| Feature | Example |
|---|---|
| Headings (with anchors) | `# Title`, `## Section` |
| Emphasis, strikethrough, highlight | `**bold**`, `*italic*`, `~~gone~~`, `==marked==` |
| Subscript and superscript | `H~2~O`, `x^2^` |
| Links, bare URLs, images | `[link](https://example.com)`, `https://example.com`, `![alt](picture.png)` |
| Wikilinks (Obsidian style) | `[[Note]]`, `[[Note\|shown text]]` |
| Lists and task lists | `- item`, `- [x] done`, `- [ ] to do` |
| Quotes | `> quote` |
| Obsidian callouts | `> [!warning] Title` followed by the body |
| Admonitions | `!!! note "Title"` followed by an indented body |
| Code and fenced code | `` `inline` ``, fenced blocks with a language name |
| Tables | a header row, a separator row, then the data rows |
| Footnotes | `Text[^1]` and `[^1]: Note` |
| Definition lists | a term on one line, then `: definition` on the next |
| Field lists | `:name: value` |
| Math | `$e^{i\pi}+1=0$` inline, and `$$` on its own lines for a display block |
| Horizontal rules | `---` |
| Front matter | a `---` block at the very top, read and hidden as metadata |

Not supported: emoji shortcodes such as `:smile:`, and the Obsidian embeds `![[file]]`. These need extra libraries that are not part of the pack yet.

**Right-to-left and mixed text**

- Each paragraph, heading, list item, quote and table cell chooses its direction from its first strong character. Persian or Arabic text lines up on the right. English text lines up on the left. A note can mix both.
- Code blocks and math always stay left-to-right, even inside a right-to-left paragraph.
- Lists, quotes and indents use the correct side for the direction.

**Safety.** Raw HTML typed into a note is shown as text, not rendered. A workflow can be shared with its notes inside it, and rendering raw HTML would let a shared note run scripts on the machine that opens it. This is a deliberate choice, and the pack does not offer an option to turn it off.

**Fonts.** The preview uses Vazirmatn if it is installed, and then falls back to Tahoma, Segoe UI, Noto Naskh Arabic and Noto Sans. Install Vazirmatn for the best Persian and Arabic display. It is a free font and is not bundled with the pack.

**Preview.** The preview updates a moment after you stop typing. It is rendered by the same Python code that produces the `html` output, so what you see is what the workflow outputs.

## How the AHP Folder Picker works

1. **Browse Folder** sends a request from the ComfyUI browser page to the ComfyUI server on the same computer.
2. The server opens the folder dialog that belongs to your operating system, on the computer that runs ComfyUI.
3. When you choose a folder, its path is written into the `folder_path` text field. If you cancel, the field is not changed.
4. When the workflow runs, the node cleans the path and passes it on as `folder_path`.

**Cleaning the path.** Quotation marks are removed from the output. This matters on Windows, where "Copy as path" wraps a path in double quotes. Double quotes are removed everywhere in the path, because Windows does not allow them in names. Single quotes are removed only from the ends, so a folder called `John's photos` keeps its apostrophe.

## Installation

Requirements:

- ComfyUI (a recent version with custom node support)
- Python 3.10 or newer, which is the Python that ComfyUI uses
- A computer where you can see the desktop. The dialog opens on the screen of the machine running ComfyUI. See [Platform support](#platform-support).

The AHP Markdown Note needs three small Python libraries. Install them into the same Python that runs ComfyUI.

Standard install (ComfyUI run from its own folder):

```bash
python -m pip install -r custom_nodes/comfyuiAHP_nodepack/requirements.txt
```

Windows portable build (run from the `ComfyUI_windows_portable` folder):

```bash
python_embeded\python.exe -m pip install -r ComfyUI\custom_nodes\comfyuiAHP_nodepack\requirements.txt
```

The folder picker needs no extra libraries. If a library is missing, the Markdown note does not load, and the other AHP nodes still work. The console shows which module failed.

### Option 1: Git clone (recommended while developing)

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_GITHUB_USERNAME/comfyuiAHP_nodepack.git
```

Restart ComfyUI. The AHP Folder Picker appears in the node menu under **AHP → Path**.

### Option 2: Manual copy

1. Download or copy the `comfyuiAHP_nodepack` folder.
2. Place it inside `ComfyUI/custom_nodes/`.
3. Restart ComfyUI.

Put the whole `comfyuiAHP_nodepack` folder in `custom_nodes/`, not only its `.py` files, because the node files depend on each other.

### Updating

```bash
cd ComfyUI/custom_nodes/comfyuiAHP_nodepack
git pull
```

Then restart ComfyUI and refresh the browser tab, so the button script reloads.

## Using the AHP Folder Picker

1. Add the **AHP Folder Picker** node to your workflow.
2. Click **Browse Folder** and choose a folder in the dialog. The path appears in the text field.
3. Connect `folder_path` to the node that needs a folder, such as a batch image loader.
4. Queue the workflow.

You can also paste or type a path into the text field. Quotation marks around it are removed automatically.

The input is optional. If you leave the field empty, the output is an empty string, and the workflow still runs.

## Platform support

| System | Dialog used | Notes |
|---|---|---|
| Windows | The standard Windows file dialog (Explorer style), opened with PowerShell | Included with Windows. Nothing to install. |
| macOS | Finder folder chooser, opened with `osascript` | Included with macOS. The first time, macOS may ask permission for the terminal or ComfyUI to control your computer. Allow it. |
| Linux with a desktop | `zenity`, or `kdialog` if `zenity` is missing | Install one of them, for example `sudo apt install zenity`. |
| Remote or headless server | None | No screen is available, so the button shows an error. Type the path into the field instead. |

## Troubleshooting

**The Browse Folder button does nothing, or shows an error.**
Check the message. Common causes are:

- *No display.* ComfyUI is running on a server with no desktop. Type the path instead.
- *No folder dialog tool on Linux.* Install `zenity` or `kdialog`.
- *The button is missing.* The button script did not load. Restart ComfyUI and refresh the browser tab. Check that `web/js/ahp_folder_picker.js` exists inside the pack folder.

**The dialog did not appear.**
It may have opened behind other windows. Check the taskbar on Windows, or Mission Control on macOS.

**The output has quotation marks, or the path is wrong.**
Update the pack with `git pull`, restart ComfyUI, and refresh the browser tab. The output is cleaned by the node, not by the browser.

**How to choose a folder in the Windows dialog.**
Double-click into the folder you want, so you are inside it. Leave the file name box as "Select this folder", then click **Open**. The node takes the folder you are inside. If you click Open while a folder is only highlighted, the dialog opens that folder first, so click Open once more.

**"Folder does not exist" appears in the console.**
The path is set but the folder is not there. This is only a warning. Create the folder, or choose a different one.

**The AHP Markdown Note appears, but the preview says libraries are not installed.**
The node always appears in the node list. Its three Markdown libraries are needed to render, and the message names them. Install them as shown under [Installation](#installation), then restart ComfyUI.

**The preview does not update.**
Click in the text box and type a character, or reload the browser tab. If it still does not update, restart ComfyUI so the browser script reloads.

**Persian or Arabic text shows in the wrong font or looks broken.**
Install the Vazirmatn font, then restart the browser. The preview also needs a font that supports Arabic script. Noto Naskh Arabic is a good fallback.

**Math shows as red code instead of a formula.**
The LaTeX has an error, or uses a command the converter does not support. The red text is the original LaTeX, so check it for typos.

## Project structure

```text
comfyuiAHP_nodepack/
├── __init__.py                  # ComfyUI entry point. Auto-loads every nodes/ahp_*.py file.
├── pyproject.toml               # Package and ComfyUI Registry metadata
├── README.md                    # This file
├── LICENSE                      # GNU General Public License v3.0
├── .gitignore                   # Files that git should not track
├── requirements.txt             # Python libraries the Markdown note needs
├── nodes/
│   ├── __init__.py              # Makes nodes/ a Python package
│   ├── ahp_folder_picker.py     # AHP Folder Picker: node, OS dialogs, server route
│   ├── ahp_markdown_note.py     # AHP Markdown Note: node, Markdown renderer, preview route
│   ├── ahp_image_crop_fit_canvas.py # AHP Image Crop Fit Canvas: crop, scale and centre on a canvas
│   ├── _dialogs.py              # Shared OS file-dialog helpers (not a node)
│   └── ahp_load_image.py        # AHP Load Image: Browse Image route, load, output image, mask, path, directory
└── web/
    └── js/
        ├── ahp_folder_picker.js # AHP Folder Picker: Browse Folder button
        ├── ahp_load_image.js    # AHP Load Image: Browse Image button
        └── ahp_markdown_note.js # AHP Markdown Note: live preview and RTL text box
```

## Adding a new AHP node

The pack is built to grow. You do not need to edit `__init__.py` when you add a node.

1. Create `nodes/ahp_<name>.py`. Use a lowercase name with underscores, for example `nodes/ahp_image_resize.py`.
2. Define the node class in that file, and export `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` at the bottom.
3. If the node needs a button or other browser behaviour, add `web/js/ahp_<name>.js`. Every `.js` file in `web/js/` loads automatically.
4. Restart ComfyUI and test the node.
5. Add a row for the node to the table in this README.

Minimal template:

```python
# nodes/ahp_example.py
class AHPExample:
    CATEGORY = "AHP/Utils"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {"text": ("STRING", {"default": "", "multiline": True})},
        }

    def run(self, text=""):
        return (text.strip(),)


NODE_CLASS_MAPPINGS = {"AHP_Example": AHPExample}
NODE_DISPLAY_NAME_MAPPINGS = {"AHP_Example": "AHP Example"}
```

## Naming conventions

| Item | Convention | Example |
|---|---|---|
| Node file | `nodes/ahp_<snake_case>.py` | `nodes/ahp_folder_picker.py` |
| Frontend file | `web/js/ahp_<snake_case>.js` | `web/js/ahp_folder_picker.js` |
| Class name | `AHP` + `PascalCase` | `AHPFolderPicker` |
| Node ID (mapping key) | `AHP_` + `PascalCase` with underscores | `AHP_FolderPicker` |
| Display name | `AHP ` + words | `AHP Folder Picker` |
| Category | `AHP/<Group>` | `AHP/Path`, `AHP/Image`, `AHP/Utils` |
| Server route | `/ahp/<node_snake_case>/<action>` | `/ahp/folder_picker/select` |

Node IDs must be unique across all installed custom nodes, so the `AHP_` prefix keeps them from clashing with other packs.

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.

You are free to use, study, share and change this software. If you distribute a modified version, you must also release it under GPL-3.0 with its source code.
