"""
AHP Folder Picker

An optional text field with a "Browse Folder" button.

The button (web/js/ahp_folder_picker.js) asks the ComfyUI server to open the
operating system's own folder dialog on the computer that runs ComfyUI:

- Windows: the standard Windows file dialog (the Explorer-style window that
  most Windows programs use), started with PowerShell
- macOS:   the Finder folder chooser, started with osascript
- Linux:   zenity or kdialog, if one of them is installed

The folder_path input is optional. The output is the chosen path as a plain
string with no quotation marks, or an empty string if nothing is chosen.
The node does not use tkinter.

Licensed under the GNU General Public License v3.0. See LICENSE.
"""

import asyncio
import base64
import os
import subprocess
import sys

from aiohttp import web

try:
    from server import PromptServer
except ImportError:  # Lets the module be imported outside ComfyUI, e.g. in tests
    PromptServer = None


ROUTE = "/ahp/folder_picker/select"
DIALOG_TITLE = "AHP Folder Picker - choose a folder"


class DialogError(RuntimeError):
    """The folder dialog could not be opened. The message explains why."""


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


def _finish(raw):
    """Clean the dialog's output and normalise the separators for this OS."""
    chosen = clean_path(raw)
    return os.path.normpath(chosen) if chosen else ""


# ---------------------------------------------------------------- Windows

def _ps_quote(text):
    """Quote a string for PowerShell as a single-quoted literal."""
    return "'" + text.replace("'", "''") + "'"


def _windows_command(initial_dir):
    script = "\n".join([
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8",
        "Add-Type -AssemblyName System.Windows.Forms",
        # The Open dialog is the modern Windows file dialog. Set up as below,
        # it lets the user pick a folder, so it works as a folder chooser.
        "$dialog = New-Object System.Windows.Forms.OpenFileDialog",
        f"$dialog.Title = {_ps_quote(DIALOG_TITLE)}",
        "$dialog.CheckFileExists = $false",
        "$dialog.CheckPathExists = $true",
        "$dialog.ValidateNames = $false",
        "$dialog.FileName = 'Select this folder'",
        f"$start = {_ps_quote(initial_dir)}",
        "if ($start -and (Test-Path -LiteralPath $start)) { $dialog.InitialDirectory = $start }",
        # A hidden, topmost owner keeps the dialog in front of the browser.
        "$owner = New-Object System.Windows.Forms.Form",
        "$owner.TopMost = $true",
        "$owner.ShowInTaskbar = $false",
        "if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {",
        # The folder is the directory part of the chosen "file" name.
        "    Write-Output ([System.IO.Path]::GetDirectoryName($dialog.FileName))",
        "}",
        "$owner.Dispose()",
    ])
    # -EncodedCommand takes UTF-16LE base64, so Persian and other non-ASCII
    # folder names survive the trip through the command line.
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [
        "powershell", "-NoProfile", "-NonInteractive", "-STA",
        "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded,
    ]


# ------------------------------------------------------------------ macOS

def _applescript_quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _mac_command(initial_dir):
    script = f"POSIX path of (choose folder with prompt {_applescript_quote(DIALOG_TITLE)}"
    if initial_dir:
        script += f" default location POSIX file {_applescript_quote(initial_dir)}"
    script += ")"
    return ["osascript", "-e", script]


# ------------------------------------------------------------------ Linux

def _linux_dialog(initial_dir):
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise DialogError(
            "No graphical display was found, so no folder dialog can open. "
            "Type the folder path into the field instead."
        )

    start = initial_dir or os.path.expanduser("~")
    attempts = [
        ["zenity", "--file-selection", "--directory",
         f"--title={DIALOG_TITLE}", f"--filename={start.rstrip(os.sep)}{os.sep}"],
        ["kdialog", "--title", DIALOG_TITLE, "--getexistingdirectory", start],
    ]
    for command in attempts:
        try:
            result = subprocess.run(command, capture_output=True, check=False)
        except FileNotFoundError:
            continue  # This tool is not installed, so try the next one
        # Both tools exit with status 1 when the user cancels.
        if result.returncode == 0:
            return _finish(result.stdout.decode("utf-8", errors="replace"))
        return ""

    raise DialogError(
        "No folder dialog tool was found. Install zenity or kdialog, "
        "or type the folder path into the field instead."
    )


# ------------------------------------------------------------ Shared logic

def open_folder_dialog(initial_dir=""):
    """Open the OS folder dialog and return the chosen path, or "" if cancelled."""
    if sys.platform.startswith("win"):
        command = _windows_command(initial_dir)
    elif sys.platform == "darwin":
        command = _mac_command(initial_dir)
    else:
        return _linux_dialog(initial_dir)

    try:
        result = subprocess.run(command, capture_output=True, check=False)
    except FileNotFoundError as error:
        raise DialogError(f"Could not start the folder dialog: {error}") from error

    stdout = result.stdout.decode("utf-8", errors="replace")
    if result.returncode == 0:
        return _finish(stdout)

    stderr = result.stderr.decode("utf-8", errors="replace")
    if "-128" in stderr:  # macOS: the user pressed Cancel
        return ""
    raise DialogError(stderr.strip() or "The folder dialog failed.")


if PromptServer is not None:

    @PromptServer.instance.routes.post(ROUTE)
    async def ahp_select_folder(request):
        """Called by the Browse Folder button. Responds with {"path": ...}."""
        try:
            body = await request.json()
        except Exception:
            body = {}

        current = clean_path(body.get("current", "")) if isinstance(body, dict) else ""
        initial_dir = current if os.path.isdir(current) else ""

        try:
            # The dialog blocks until the user answers, so run it in a worker thread.
            folder = await asyncio.to_thread(open_folder_dialog, initial_dir)
        except DialogError as error:
            return web.json_response({"path": "", "error": str(error)}, status=500)
        except Exception as error:
            return web.json_response(
                {"path": "", "error": f"Could not open the folder dialog: {error}"},
                status=500,
            )

        return web.json_response({"path": folder, "cancelled": folder == ""})


class AHPFolderPicker:
    """Outputs the chosen folder path as a clean string. The input is optional."""

    CATEGORY = "AHP/Path"
    FUNCTION = "get_folder_path"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("folder_path",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "folder_path": ("STRING", {"default": "", "multiline": False}),
            },
        }

    def get_folder_path(self, folder_path=""):
        path = clean_path(folder_path)
        if path and not os.path.isdir(path):
            print(f"[AHP Folder Picker] Warning: folder does not exist (yet): {path}")
        return (path,)


NODE_CLASS_MAPPINGS = {
    "AHP_FolderPicker": AHPFolderPicker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AHP_FolderPicker": "AHP Folder Picker",
}
