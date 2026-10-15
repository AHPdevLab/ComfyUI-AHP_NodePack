"""
AHP Folder Picker

A string-path node with a "Select Folder" button.

- The button (web/js/ahp_folder_picker.js) asks the ComfyUI server to open a
  native folder dialog on the machine running ComfyUI, then fills the text
  field with the chosen path.
- The text field can also be typed or pasted into directly.
- The output is the path as a plain string with no quotation marks.

Copyright (C) the comfyuiAHP_nodepack authors.
Licensed under the GNU General Public License v3.0. See LICENSE.
"""

import asyncio
import os
import subprocess
import sys

from aiohttp import web

try:
    from server import PromptServer
except ImportError:  # Lets the module be imported outside ComfyUI, e.g. in tests
    PromptServer = None


ROUTE = "/ahp/folder_picker/select"

# The dialog runs in its own Python process. This keeps tkinter on that
# process's main thread (required on macOS) and stops a dialog from freezing
# the ComfyUI server.
_DIALOG_CODE = r'''
import sys
import tkinter as tk
from tkinter import filedialog

initial = sys.argv[1] if len(sys.argv) > 1 else ""
root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
folder = filedialog.askdirectory(
    initialdir=initial or None,
    title="AHP Folder Picker - choose a folder",
)
root.destroy()
sys.stdout.buffer.write((folder or "").encode("utf-8"))
'''


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


def _open_folder_dialog(initial_dir):
    """Open the native folder dialog and return the chosen path ("" if cancelled)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, "-c", _DIALOG_CODE, initial_dir],
        capture_output=True,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or "folder dialog exited with an error")

    chosen = clean_path(result.stdout.decode("utf-8", errors="replace"))
    return os.path.normpath(chosen) if chosen else ""


if PromptServer is not None:

    @PromptServer.instance.routes.post(ROUTE)
    async def ahp_select_folder(request):
        """Called by the Select Folder button. Responds with {"path": ...}."""
        try:
            body = await request.json()
        except Exception:
            body = {}

        current = clean_path(body.get("current", "")) if isinstance(body, dict) else ""
        initial_dir = current if os.path.isdir(current) else ""

        try:
            # The dialog blocks until the user answers, so run it in a worker thread.
            folder = await asyncio.to_thread(_open_folder_dialog, initial_dir)
        except Exception as error:
            return web.json_response(
                {"path": "", "error": f"Could not open the folder dialog: {error}"},
                status=500,
            )

        return web.json_response({"path": folder, "cancelled": folder == ""})


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
                "folder_path": ("STRING", {"default": "", "multiline": False}),
            }
        }

    def get_folder_path(self, folder_path):
        path = clean_path(folder_path)
        if not path:
            raise ValueError(
                "AHP Folder Picker: no folder selected. "
                "Click 'Select Folder' or type a path into the field."
            )
        if not os.path.isdir(path):
            print(f"[AHP Folder Picker] Warning: folder does not exist (yet): {path}")
        return (path,)


NODE_CLASS_MAPPINGS = {
    "AHP_FolderPicker": AHPFolderPicker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AHP_FolderPicker": "AHP Folder Picker",
}
