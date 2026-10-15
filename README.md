# comfyuiAHP_nodepack

A collection of utility nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI), made by AHP. Every node in this pack has the `AHP` prefix, and each node lives in its own file.

The first node is the **AHP Folder Picker**. It has a **Browse Folder** button that opens your operating system's folder dialog. It outputs the chosen folder's full path as a plain string with no quotation marks. The node does not use tkinter.

## Contents

- [Nodes](#nodes)
- [How it works](#how-it-works)
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

### AHP Folder Picker

**Inputs**

| Name | Type | Widget | Required | Description |
|---|---|---|---|---|
| `folder_path` | STRING | Text field, with a **Browse Folder** button under it | No | The folder path. Click the button to choose a folder, or type or paste a path. Leave it empty if you do not need a folder. |

**Outputs**

| Name | Type | Description |
|---|---|---|
| `folder_path` | STRING | The folder path with no quotation marks. It is an empty string if no folder was chosen. |

## How it works

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

No Python packages need to be installed. The node uses only the Python standard library and aiohttp, which ComfyUI already includes.

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
│   └── ahp_folder_picker.py     # AHP Folder Picker: node, OS dialogs, server route
└── web/
    └── js/
        └── ahp_folder_picker.js # AHP Folder Picker: Browse Folder button
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
