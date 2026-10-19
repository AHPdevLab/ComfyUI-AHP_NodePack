"""
Shared helpers for opening the operating system's file chooser.

This file is not a node. The loader only reads files named ahp_*.py.

- Windows: the standard Windows file dialog (Explorer style), via PowerShell.
- macOS:   the Finder file chooser, via osascript.
- Linux:   zenity or kdialog, if one is installed.

Licensed under the GNU General Public License v3.0. See LICENSE.
"""

import base64
import os
import subprocess
import sys


IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif")
IMAGE_DIALOG_TITLE = "AHP Load Image - choose an image"


class DialogError(RuntimeError):
    """The file dialog could not be opened. The message explains why."""


def clean_path(raw):
    """Remove surrounding whitespace and quotation marks from a path."""
    if raw is None:
        return ""
    path = str(raw).strip(" \t\r\n\"'")
    path = path.replace('"', "")
    return path.strip()


def _finish(raw):
    chosen = clean_path(raw)
    return os.path.normpath(chosen) if chosen else ""


def _ps_quote(text):
    return "'" + text.replace("'", "''") + "'"


def _applescript_quote(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------- Windows

def _windows_command(initial_dir):
    extensions = ";".join(f"*.{ext}" for ext in IMAGE_EXTENSIONS)
    script = "\n".join([
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8",
        "Add-Type -AssemblyName System.Windows.Forms",
        "$dialog = New-Object System.Windows.Forms.OpenFileDialog",
        f"$dialog.Title = {_ps_quote(IMAGE_DIALOG_TITLE)}",
        f"$dialog.Filter = {_ps_quote(f'Image files|{extensions}|All files|*.*')}",
        "$dialog.CheckFileExists = $true",
        "$dialog.Multiselect = $false",
        f"$start = {_ps_quote(initial_dir)}",
        "if ($start -and (Test-Path -LiteralPath $start -PathType Container)) { $dialog.InitialDirectory = $start }",
        "$owner = New-Object System.Windows.Forms.Form",
        "$owner.TopMost = $true",
        "$owner.ShowInTaskbar = $false",
        "if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {",
        "    Write-Output $dialog.FileName",
        "}",
        "$owner.Dispose()",
    ])
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [
        "powershell", "-NoProfile", "-NonInteractive", "-STA",
        "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded,
    ]


# ------------------------------------------------------------------ macOS

def _mac_command(initial_dir):
    types = ", ".join(f'"public.{ext}"' for ext in ("png", "jpeg", "webp", "bmp", "tiff", "gif"))
    script = f"POSIX path of (choose file with prompt {_applescript_quote(IMAGE_DIALOG_TITLE)} of type {{{types}}}"
    if initial_dir:
        script += f" default location POSIX file {_applescript_quote(initial_dir)}"
    script += ")"
    return ["osascript", "-e", script]


# ------------------------------------------------------------------ Linux

def _linux_dialog(initial_dir):
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise DialogError(
            "No graphical display was found, so no file dialog can open. "
            "Type the image path into the field instead."
        )

    patterns = " ".join(f"*.{ext}" for ext in IMAGE_EXTENSIONS)
    start = initial_dir or os.path.expanduser("~")
    attempts = [
        ["zenity", "--file-selection", f"--title={IMAGE_DIALOG_TITLE}",
         f"--filename={start.rstrip(os.sep)}{os.sep}",
         f"--file-filter=Images | {patterns}"],
        ["kdialog", "--title", IMAGE_DIALOG_TITLE, "--getopenfilename", start, patterns],
    ]
    for command in attempts:
        try:
            result = subprocess.run(command, capture_output=True, check=False)
        except FileNotFoundError:
            continue
        if result.returncode == 0:
            return _finish(result.stdout.decode("utf-8", errors="replace"))
        return ""  # Cancelled (exit status 1)

    raise DialogError(
        "No file dialog tool was found. Install zenity or kdialog, "
        "or type the image path into the field instead."
    )


# ------------------------------------------------------------ Shared logic

def open_image_dialog(initial_dir=""):
    """Open the OS image chooser and return the chosen file path, or "" if cancelled."""
    if sys.platform.startswith("win"):
        command = _windows_command(initial_dir)
    elif sys.platform == "darwin":
        command = _mac_command(initial_dir)
    else:
        return _linux_dialog(initial_dir)

    try:
        result = subprocess.run(command, capture_output=True, check=False)
    except FileNotFoundError as error:
        raise DialogError(f"Could not start the file dialog: {error}") from error

    if result.returncode == 0:
        return _finish(result.stdout.decode("utf-8", errors="replace"))

    stderr = result.stderr.decode("utf-8", errors="replace")
    if "-128" in stderr:  # macOS: the user pressed Cancel
        return ""
    raise DialogError(stderr.strip() or "The file dialog failed.")
