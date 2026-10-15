# comfyuiAHP_nodepack

A collection of utility nodes for [ComfyUI](https://github.com/comfyanonymous/ComfyUI), made by AHP. Every node in this pack has the `AHP` prefix, and each node lives in its own file.

The first node is the **AHP Folder Picker**. It is built only from ComfyUI's own mechanisms, the same ones the built-in Load Image node uses. It has no JavaScript and no tkinter. It shows a dropdown labelled **folder** and outputs the chosen folder's full path as a plain string with no quotation marks.

## Contents

- [Nodes](#nodes)
- [How it works](#how-it-works)
- [Installation](#installation)
- [Using the AHP Folder Picker](#using-the-ahp-folder-picker)
- [Why there is no upload or browse button](#why-there-is-no-upload-or-browse-button)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Adding a new AHP node](#adding-a-new-ahp-node)
- [Naming conventions](#naming-conventions)
- [License](#license)

## Nodes

| Display name | Node ID | Category | File | Purpose |
|---|---|---|---|---|
| AHP Folder Picker | `AHP_FolderPicker` | `AHP/Path` | `nodes/ahp_folder_picker.py` | Choose a folder and output its full path as a string |

### AHP Folder Picker

**Inputs**

| Name | Type | Widget | Required | Description |
|---|---|---|---|---|
| `folder` | Dropdown | Lists every folder inside `ComfyUI/input` | Yes | The folder to use. The label is shown as "folder". |
| `custom_path` | STRING | Text field | No | A full folder path, for example `D:\Photos\raw`. When this is filled in, it replaces the dropdown choice. |

**Outputs**

| Name | Type | Description |
|---|---|---|
| `folder_path` | STRING | The full folder path with no quotation marks. |

## How it works

The node uses three ComfyUI mechanisms that the built-in Load Image node also uses.

1. **Dropdown.** The list of options is built from the folders in ComfyUI's input directory, `ComfyUI/input/`. Loose files are ignored. Only folders appear.
2. **Validation.** Before a workflow runs, ComfyUI checks that the chosen folder exists. If it does not, the node shows a clear error instead of failing later.
3. **Change detection.** The node hashes the folder's entries and their modification times. When a file is added, removed or changed, the hash changes and ComfyUI runs the node again. This matches how Load Image handles changed files.

Quotation marks are removed from the output. This matters on Windows, where "Copy as path" wraps a path in double quotes. Double quotes are removed everywhere in the path, because Windows does not allow them in names. Single quotes are removed only from the ends, so a folder called `John's photos` keeps its apostrophe.

## Installation

Requirements:

- ComfyUI (a recent version with custom node support)
- Python 3.10 or newer, which is the Python that ComfyUI uses

No extra packages are needed.

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

Then restart ComfyUI.

## Using the AHP Folder Picker

**Option A: a folder inside ComfyUI/input (the native way)**

1. Copy or move your folder into `ComfyUI/input/`. For example, `ComfyUI/input/shoots_2026/`.
2. In ComfyUI, refresh the node definitions. Press **R**, or restart ComfyUI if the folder does not appear.
3. Add the **AHP Folder Picker** node and open the **folder** dropdown. Choose your folder.
4. Connect `folder_path` to the node that needs a path, such as a batch image loader.

**Option B: any folder on your computer**

1. Copy the full path of the folder. On Windows you can use "Copy as path" in File Explorer.
2. Paste it into `custom_path`. Quotation marks around it are removed automatically.
3. Run the workflow. The output is the path you pasted, with no quotation marks.

When `custom_path` is filled in, it is used and the dropdown is ignored.

## Why there is no upload or browse button

The built-in Load Image node has a "choose file to upload" button. That button is part of ComfyUI itself, and it works only for files. It sends one file to the server and saves it in `ComfyUI/input/`. A browser cannot hand a folder path or a whole folder to a custom node without JavaScript, and this pack avoids JavaScript on purpose. So the folder is picked from the dropdown, or typed into `custom_path`.

The folder icon from the Load Image layout is also not available. Icons need custom frontend code.

## Troubleshooting

**The folder I added does not appear in the dropdown.**
The dropdown is built when ComfyUI starts or refreshes its node list. Press **R** in ComfyUI, or restart it.

**"Folder not found" error when the workflow runs.**
The chosen folder does not exist. Check the spelling of the folder name, or the path in `custom_path`. Also check that the folder is inside `ComfyUI/input/` if you are using the dropdown.

**The dropdown shows "(no folders in ComfyUI/input)".**
There are no folders in `ComfyUI/input/` yet. Add one, refresh, and choose it. Or use `custom_path` instead.

**The output still shows quotation marks.**
Update the pack with `git pull` and restart ComfyUI, so the new code loads. The pack version is in `pyproject.toml`.

**The workflow does not re-run after I add files to the folder.**
Change detection looks at the folder's top-level entries and their modification times. Files added inside sub-subfolders do not change the hash. Make sure the files you add are directly inside the chosen folder.

## Project structure

```text
comfyuiAHP_nodepack/
├── __init__.py                  # ComfyUI entry point. Auto-loads every nodes/ahp_*.py file.
├── pyproject.toml               # Package and ComfyUI Registry metadata
├── README.md                    # This file
├── LICENSE                      # GNU General Public License v3.0
├── .gitignore                   # Files that git should not track
└── nodes/
    ├── __init__.py              # Makes nodes/ a Python package
    └── ahp_folder_picker.py     # AHP Folder Picker: dropdown node, path logic, validation
```

## Adding a new AHP node

The pack is built to grow. You do not need to edit `__init__.py` when you add a node.

1. Create `nodes/ahp_<name>.py`. Use a lowercase name with underscores, for example `nodes/ahp_image_resize.py`.
2. Define the node class in that file, and export `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` at the bottom.
3. Restart ComfyUI and test the node.
4. Add a row for the node to the table in this README.

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
| Class name | `AHP` + `PascalCase` | `AHPFolderPicker` |
| Node ID (mapping key) | `AHP_` + `PascalCase` with underscores | `AHP_FolderPicker` |
| Display name | `AHP ` + words | `AHP Folder Picker` |
| Category | `AHP/<Group>` | `AHP/Path`, `AHP/Image`, `AHP/Utils` |

Node IDs must be unique across all installed custom nodes, so the `AHP_` prefix keeps them from clashing with other packs.

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.

You are free to use, study, share and change this software. If you distribute a modified version, you must also release it under GPL-3.0 with its source code.
