// comfyuiAHP_nodepack - AHP Load Image frontend.
// Adds a "Browse Image" button. The button asks the server to open the operating
// system's file chooser and writes the chosen path into the path field.
// Licensed under the GNU General Public License v3.0. See LICENSE.

import { app } from "../../scripts/app.js";

const NODE_CLASS = "AHP_LoadImage";
const PATH_WIDGET = "path";
const ROUTE = "/ahp/load_image/select";

app.registerExtension({
  name: "AHP.LoadImage",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_CLASS) return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;

    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);

      const pathWidget = this.widgets?.find((w) => w.name === PATH_WIDGET);

      this.addWidget("button", "Browse Image", null, async () => {
        try {
          const response = await fetch(ROUTE, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ current: pathWidget ? pathWidget.value : "" }),
          });

          const data = await response.json();

          if (!response.ok || data.error) {
            alert(data.error || "The file dialog could not be opened.");
            return;
          }

          // The user cancelled: keep the current value.
          if (!data.path) return;

          if (pathWidget) {
            pathWidget.value = data.path;
          }
          app.graph.setDirtyCanvas(true, true);
        } catch (error) {
          alert(`AHP Load Image: ${error}`);
        }
      });

      return result;
    };
  },
});
