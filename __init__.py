"""
comfyuiAHP_nodepack - entry point loaded by ComfyUI.

Every file in ./nodes whose name starts with "ahp_" is imported automatically.
Each such file must define NODE_CLASS_MAPPINGS (and optionally
NODE_DISPLAY_NAME_MAPPINGS). To add a new node, just create a new
nodes/ahp_<name>.py file - nothing here needs to change.
"""

import importlib
from pathlib import Path

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

_NODES_DIR = Path(__file__).resolve().parent / "nodes"

for _node_file in sorted(_NODES_DIR.glob("ahp_*.py")):
    try:
        _module = importlib.import_module(f".nodes.{_node_file.stem}", package=__name__)
    except Exception as _error:  # One broken node must not stop the others
        print(f"[comfyuiAHP_nodepack] Could not load {_node_file.name}: {_error}")
        continue
    NODE_CLASS_MAPPINGS.update(getattr(_module, "NODE_CLASS_MAPPINGS", {}))
    NODE_DISPLAY_NAME_MAPPINGS.update(getattr(_module, "NODE_DISPLAY_NAME_MAPPINGS", {}))

# Frontend JavaScript (the Browse Folder button) lives here.
WEB_DIRECTORY = "./web/js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
