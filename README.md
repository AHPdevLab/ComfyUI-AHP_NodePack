# comfyuiAHP_nodepack

A collection of utility nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI), made by AHP. Every node in this pack has the `AHP` prefix, and each node lives in its own file.

The first node is the **AHP Folder Picker**. It has a button that opens a native folder dialog, and it outputs the chosen folder path as a plain string with no quotation marks.

## Contents

- [Nodes](#nodes)
- [Installation](#installation)
- [Using the AHP Folder Picker](#using-the-ahp-folder-picker)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Adding a new AHP node](#adding-a-new-ahp-node)
- [Naming conventions](#naming-conventions)
- [License](#license)

## Nodes

| Display name | Node ID | Category | File | Purpose |
|---|---|---|---|---|
| AHP Folder Picker | `AHP_FolderPicker` | `AHP/Path` | `nodes/ahp_folder_picker.py` | Pick a folder with a button and output its path as a string |

### AHP Folder Picker

**Inputs**

| Name | Type | Widget | Description |
|---|---|---|---|
| `folder_path` | STRING | Text field and **Select Folder** button | The folder path. Type or paste it, or click the button to choose a folder. |

**Outputs**

| Name | Type | Description |
|---|---|---|
| `folder_path` | STRING | The cleaned folder path. It never contains quotation marks. |

**Behaviour**

- Clicking **Select Folder** opens a folder chooser on the machine that runs ComfyUI. Choosing a folder fills in the text field. Cancelling leaves the field as it was.
- The output is cleaned before it is passed on. Whitespace and quotation marks are removed. This matters on Windows, where "Copy as path" wraps a path in double quotes. Double quotes are removed from everywhere in the path, because Windows does not allow them in names. Single quotes are removed only from the ends, so a folder called `John's photos` keeps its apostrophe.
- Paths returned by the folder dialog are normalised to your operating system's separators. For example, `C:/Photos/raw` becomes `C:\Photos\raw` on Windows. Typed paths are passed through as you enter them, apart from the quote cleaning.
- If the path does not exist yet, the node still outputs it and prints a warning in the console. This is useful for output folders that a later node will create.
- If the field is empty, the node stops with a clear error message: "no folder selected".

## Installation

Requirements:

- ComfyUI (a recent version with custom node support)
- Python 3.10 or newer, which is the Python that ComfyUI uses
- Tkinter, which ships with the official Python installers on Windows and macOS. On Linux, install it with your package manager, for example `sudo apt install python3-tk`.

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

Do not put the `.py` files directly into `custom_nodes/`. The whole `comfyuiAHP_nodepack` folder has to go in, because the node files depend on each other.

### Updating

```bash
cd ComfyUI/custom_nodes/comfyuiAHP_nodepack
git pull
```

Then restart ComfyUI. Browser JavaScript changes may also need a page refresh.

## Using the AHP Folder Picker

1. Add the node: double-click the canvas, search for **AHP Folder Picker**, and select it.
2. Click **Select Folder** and choose a folder in the dialog. The path appears in the field.
3. Connect the `folder_path` output to any node that takes a string path. For example, it can feed a batch image loader, or a save node that needs a folder.
4. Queue the workflow as usual.

If you already have a path, you can paste it into the field. Quotation marks around it are removed automatically.

## Troubleshooting

**The Select Folder button does nothing, or shows "Could not open the folder dialog".**
The dialog is opened on the machine that runs ComfyUI, not in your browser. This matters in these cases:

- *ComfyUI runs on a remote or headless server* (a cloud GPU, RunPod, or a Linux box with no desktop). There is no screen to show the dialog, so type or paste the path into the field instead.
- *Tkinter is missing.* Install it as described under [Installation](#installation), then restart ComfyUI.
- *Linux without a display.* Start ComfyUI from a desktop session, or type the path manually.

**The dialog opens behind other windows.**
The node asks the system to keep the dialog on top. If it still stays hidden, check your taskbar or Mission Control.

**"no folder selected" error when the workflow runs.**
The field is empty. Use the button or type a path, then run again.

**The output still shows quotation marks.**
Update the pack with `git pull` and restart ComfyUI, so the new cleaning code loads. The pack version is shown in `pyproject.toml`, and it should be 0.1.0 or newer.

**The button is missing.**
The JavaScript did not load. Restart ComfyUI and refresh the browser tab. Check that the `web/js/ahp_folder_picker.js` file exists inside the pack folder.

## Project structure

```text
comfyuiAHP_nodepack/
├── __init__.py                  # ComfyUI entry point. Auto-loads every nodes/ahp_*.py file.
├── pyproject.toml               # Package and ComfyUI Registry metadata
├── README.md                    # This file
├── LICENSE                      # GNU General Public License v3.0
├── .gitignore                   # Files that git should not track
├── nodes/
│   ├── __init__.py              # Makes nodes/ a Python package
│   └── ahp_folder_picker.py     # AHP Folder Picker: Python node and server route
└── web/
    └── js/
        └── ahp_folder_picker.js # AHP Folder Picker: frontend button
```

## Adding a new AHP node

The pack is built to grow. You do not need to edit `__init__.py` when you add a node.

1. Create `nodes/ahp_<name>.py`. Use a lowercase name with underscores, for example `nodes/ahp_image_resize.py`.
2. Define the node class in that file, and export `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` at the bottom.
3. If the node needs a button or other frontend behaviour, add `web/js/ahp_<name>.js`. Every `.js` file in `web/js/` loads automatically.
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
        return {"required": {"text": ("STRING", {"default": "", "multiline": True})}}

    def run(self, text):
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
