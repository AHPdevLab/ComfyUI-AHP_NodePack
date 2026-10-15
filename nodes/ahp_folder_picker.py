"""
AHP Folder Picker

Built only from ComfyUI's own mechanisms, the same ones the built-in Load Image
node uses:

- a combo (dropdown) widget, filled from the folders inside ComfyUI's input
  directory (folder_paths.get_input_directory()),
- VALIDATE_INPUTS, so ComfyUI checks the choice before the workflow runs,
- IS_CHANGED, so the workflow re-runs when the folder's contents change.

It has no JavaScript and no tkinter.

Output: the full folder path as a plain string with no quotation marks.

Licensed under the GNU General Public License v3.0. See LICENSE.
"""

import hashlib
import os

import folder_paths


NO_FOLDERS = "(no folders in ComfyUI/input)"


def clean_path(raw):
    """
    Return a path with surrounding whitespace and quotation marks removed.

    Handles paths copied with "Copy as path" on Windows, which wrap the path
    in double quotes. Double quotes are removed everywhere, because Windows
    does not allow them in file or folder names. Single quotes are removed
    only at the ends, so a folder such as "John's photos" keeps its apostrophe.
    """
    if raw is None:
        return ""
    path = str(raw).strip(" \t\r\n\"'")
    path = path.replace('"', "")
    return path.strip()


def list_input_folders():
    """Folder names inside ComfyUI/input, sorted, for the dropdown."""
    input_dir = folder_paths.get_input_directory()
    if not os.path.isdir(input_dir):
        return [NO_FOLDERS]
    with os.scandir(input_dir) as entries:
        names = sorted(entry.name for entry in entries if entry.is_dir())
    return names or [NO_FOLDERS]


def resolve_folder(folder, custom_path=""):
    """
    Work out the full folder path.

    A non-empty custom_path wins and may be any absolute (or ~) path.
    Otherwise the folder is taken from the dropdown inside ComfyUI/input.
    """
    custom = clean_path(custom_path)
    if custom:
        return os.path.abspath(os.path.expanduser(custom))
    return os.path.abspath(os.path.join(folder_paths.get_input_directory(), folder))


def folder_fingerprint(path):
    """
    A hash of the folder's entries and their modification times.

    ComfyUI re-runs a node when this value changes. It is the same idea the
    built-in Load Image node uses with a file hash.
    """
    digest = hashlib.sha256(path.encode("utf-8"))
    try:
        with os.scandir(path) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                digest.update(entry.name.encode("utf-8"))
                digest.update(str(entry.stat().st_mtime_ns).encode("utf-8"))
    except OSError:
        digest.update(b"missing")
    return digest.hexdigest()


class AHPFolderPicker:
    """Outputs a folder path as a clean string with no quotation marks."""

    CATEGORY = "AHP/Path"
    FUNCTION = "get_folder_path"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("folder_path",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Same look as Load Image's dropdown, labelled "folder".
                "folder": (list_input_folders(),),
            },
            "optional": {
                # Optional full path. When filled in, it replaces the dropdown choice.
                "custom_path": ("STRING", {"default": "", "multiline": False}),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, folder, custom_path=""):
        path = resolve_folder(folder, custom_path)
        if os.path.isdir(path):
            return True
        return (
            f"Folder not found: {path}. Put a folder inside ComfyUI/input "
            "and refresh the node list, or type a full folder path in custom_path."
        )

    @classmethod
    def IS_CHANGED(cls, folder, custom_path=""):
        return folder_fingerprint(resolve_folder(folder, custom_path))

    def get_folder_path(self, folder, custom_path=""):
        return (resolve_folder(folder, custom_path),)


NODE_CLASS_MAPPINGS = {
    "AHP_FolderPicker": AHPFolderPicker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AHP_FolderPicker": "AHP Folder Picker",
}
