// comfyuiAHP_nodepack - AHP Load Image frontend.
// Adds two buttons and a preview area:
// - Browse Image: opens the operating system's file chooser and fills in the path.
// - Preview Image: shows the picture as a plain RGB PNG (no alpha, no mask overlay).
// Licensed under the GNU General Public License v3.0. See LICENSE.

import { app } from "../../scripts/app.js";

const NODE_CLASS = "AHP_LoadImage";
const PATH_WIDGET = "path";
const BROWSE_ROUTE = "/ahp/load_image/select";
const PREVIEW_ROUTE = "/ahp/load_image/preview";
const STYLE_ID = "ahp-load-image-style";

const CSS = `
.ahp-image-preview {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  border-radius: 6px;
  background: #1e1e1e;
  color: #9a9a9a;
  font-size: 13px;
}
.ahp-image-preview img {
  max-width: 100%;
  height: auto;
  display: block;
}
.ahp-image-preview .ahp-image-error { color: #ff8a8a; padding: 8px; }
`;

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = CSS;
  document.head.appendChild(style);
}

function showMessage(el, text, isError) {
  el.replaceChildren();
  const div = document.createElement("div");
  if (isError) div.className = "ahp-image-error";
  div.textContent = text;
  el.appendChild(div);
}

app.registerExtension({
  name: "AHP.LoadImage",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_CLASS) return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    const onConfigure = nodeType.prototype.onConfigure;

    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      ensureStyles();

      const pathWidget = this.widgets?.find((w) => w.name === PATH_WIDGET);

      const previewEl = document.createElement("div");
      previewEl.className = "ahp-image-preview";
      showMessage(previewEl, "No image selected. Click Browse Image or Preview Image.", false);

      this.addDOMWidget("ahp_preview", "div", previewEl, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 160,
      });

      // Shows the picture as a plain RGB PNG. Only the newest reply is shown.
      let latest = 0;
      const preview = async () => {
        const id = ++latest;
        const path = pathWidget ? String(pathWidget.value ?? "") : "";
        if (!path.trim()) {
          showMessage(previewEl, "Choose an image first.", true);
          return;
        }
        showMessage(previewEl, "Loading preview…", false);
        try {
          const response = await fetch(PREVIEW_ROUTE, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path }),
          });
          const data = await response.json();
          if (id !== latest) return;
          if (!response.ok || data.error) {
            showMessage(previewEl, data.error || "The preview could not be created.", true);
            return;
          }
          previewEl.replaceChildren();
          const img = document.createElement("img");
          img.alt = "Image preview";
          img.src = data.data_url;
          img.title = `${data.width} × ${data.height}`;
          previewEl.appendChild(img);
        } catch (error) {
          if (id !== latest) return;
          showMessage(previewEl, `Preview error: ${error}`, true);
        }
      };
      this._ahpImagePreview = preview;

      this.addWidget("button", "Browse Image", null, async () => {
        try {
          const response = await fetch(BROWSE_ROUTE, {
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

          if (pathWidget) pathWidget.value = data.path;
          app.graph.setDirtyCanvas(true, true);
          preview();
        } catch (error) {
          alert(`AHP Load Image: ${error}`);
        }
      });

      this.addWidget("button", "Preview Image", null, () => preview());

      // Show the preview of a saved workflow's image when it loads.
      if (pathWidget && String(pathWidget.value ?? "").trim()) preview();

      return result;
    };

    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      this._ahpImagePreview?.();
      return result;
    };
  },
});
