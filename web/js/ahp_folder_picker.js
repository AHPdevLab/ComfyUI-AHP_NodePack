// comfyuiAHP_nodepack - AHP Folder Picker frontend.
// Adds a "Browse Folder" button to the node. The button asks the server to open
// the operating system's folder dialog and writes the chosen path into the
// folder_path text field. Licensed under the GNU General Public License v3.0.
// See LICENSE.

import { app } from "../../scripts/app.js";

const NODE_CLASS = "AHP_FolderPicker";
const PATH_WIDGET = "folder_path";
const ROUTE = "/ahp/folder_picker/select";

app.registerExtension({
  name: "AHP.FolderPicker",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_CLASS) return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;

    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);

      const pathWidget = this.widgets?.find((w) => w.name === PATH_WIDGET);

      this.addWidget("button", "Browse Folder", null, async () => {
        try {
          const response = await fetch(ROUTE, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ current: pathWidget ? pathWidget.value : "" }),
          });

          const data = await response.json();

          if (!response.ok || data.error) {
            alert(data.error || "The folder dialog could not be opened.");
            return;
          }

          // The user cancelled the dialog: keep the current value.
          if (!data.path) return;

          if (pathWidget) {
            pathWidget.value = data.path;
          }
          app.graph.setDirtyCanvas(true, true);
        } catch (error) {
          alert(`AHP Folder Picker: ${error}`);
        }
      });

      return result;
    };
  },
});
