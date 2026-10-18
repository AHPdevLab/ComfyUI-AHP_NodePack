// comfyuiAHP_nodepack - AHP Markdown Note frontend.
// Adds a live Markdown preview under the note's text box. The preview is rendered
// by the server (POST /ahp/markdown/render), so the Python renderer is the only
// place the Markdown rules live. Licensed under the GNU General Public License v3.0.
// See LICENSE.

import { app } from "../../scripts/app.js";

const NODE_CLASS = "AHP_MarkdownNote";
const TEXT_WIDGET = "text";
const ROUTE = "/ahp/markdown/render";
const DEBOUNCE_MS = 300;
const POLL_MS = 500;
const STYLE_ID = "ahp-markdown-note-style";

const CSS = `
.ahp-md-preview {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  overflow: auto;
  padding: 8px 10px;
  border-radius: 6px;
  background: #1e1e1e;
  color: #e6e6e6;
  font-family: Vazirmatn, Tahoma, "Segoe UI", "Noto Naskh Arabic", "Noto Sans", sans-serif;
  font-size: 14px;
  line-height: 1.7;
  text-align: start;
}
.ahp-md-preview:empty::before {
  content: "Preview appears here";
  opacity: 0.5;
}
.ahp-md-preview .ahp-md-error { color: #ff8a8a; direction: ltr; text-align: left; }
.ahp-md h1, .ahp-md h2, .ahp-md h3, .ahp-md h4, .ahp-md h5, .ahp-md h6 {
  margin: 0.8em 0 0.4em;
  line-height: 1.3;
}
.ahp-md h1 { font-size: 1.6em; border-bottom: 1px solid #444; padding-bottom: 0.2em; }
.ahp-md h2 { font-size: 1.35em; border-bottom: 1px solid #3a3a3a; padding-bottom: 0.15em; }
.ahp-md h3 { font-size: 1.15em; }
.ahp-md p { margin: 0.5em 0; }
.ahp-md a { color: #6cb6ff; }
.ahp-md img { max-width: 100%; }
.ahp-md code {
  font-family: Consolas, "Courier New", monospace;
  background: #2d2d2d;
  padding: 1px 4px;
  border-radius: 4px;
  direction: ltr;
  unicode-bidi: isolate;
}
.ahp-md pre {
  direction: ltr;
  text-align: left;
  unicode-bidi: isolate;
  background: #161616;
  padding: 8px;
  border-radius: 6px;
  overflow: auto;
}
.ahp-md pre code { background: none; padding: 0; }
.ahp-md blockquote {
  margin: 0.6em 0;
  padding: 0.2em 1em;
  border-inline-start: 3px solid #666;
  color: #bbb;
}
.ahp-md table {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  margin: 0.6em 0;
}
.ahp-md th, .ahp-md td { border: 1px solid #555; padding: 4px 8px; }
.ahp-md th { background: #2a2a2a; }
.ahp-md hr { border: none; border-top: 1px solid #444; margin: 1em 0; }
.ahp-md ul, .ahp-md ol { padding-inline-start: 1.6em; margin: 0.4em 0; }
.ahp-md li.task-list-item { list-style: none; }
.ahp-md li.task-list-item input { margin-inline-end: 0.4em; pointer-events: none; }
.ahp-md dt { font-weight: 600; margin-top: 0.4em; }
.ahp-md dd { margin-inline-start: 1.5em; }
.ahp-md .footnotes { font-size: 0.9em; color: #bbb; }
.ahp-md .ahp-math-block { margin: 0.5em 0; overflow-x: auto; text-align: center; }
.ahp-md .ahp-math-error { color: #ff8a8a; }
`;

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = CSS;
  document.head.appendChild(style);
}

app.registerExtension({
  name: "AHP.MarkdownNote",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_CLASS) return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    const onConfigure = nodeType.prototype.onConfigure;

    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);
      ensureStyles();

      const textWidget = this.widgets?.find((w) => w.name === TEXT_WIDGET);
      const previewEl = document.createElement("div");
      previewEl.className = "ahp-md-preview";

      this.addDOMWidget("ahp_preview", "div", previewEl, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => 140,
      });

      // Each request gets a number. Only the newest response is shown, so a
      // slow older reply cannot overwrite a newer preview.
      let latest = 0;
      let timer = null;

      const update = async () => {
        const id = ++latest;
        const text = textWidget ? String(textWidget.value ?? "") : "";
        try {
          const response = await fetch(ROUTE, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
          });
          const data = await response.json();
          if (id !== latest) return;
          if (!response.ok || data.error) {
            previewEl.replaceChildren();
            const err = document.createElement("div");
            err.className = "ahp-md-error";
            err.textContent = data.error || "Preview could not be rendered.";
            previewEl.appendChild(err);
          } else {
            // The server escapes raw HTML, so its output is safe to insert.
            previewEl.innerHTML = data.html;
          }
        } catch (error) {
          if (id !== latest) return;
          previewEl.textContent = `Preview error: ${error}`;
        }
      };

      const scheduleUpdate = () => {
        clearTimeout(timer);
        timer = setTimeout(update, DEBOUNCE_MS);
      };
      this._ahpMarkdownUpdate = scheduleUpdate;

      // Right-to-left aware text entry: the text box lays out each line by its
      // first strong character, so Persian and Arabic type correctly.
      const textarea = textWidget?.inputEl;
      if (textarea) {
        textarea.setAttribute("dir", "auto");
        textarea.style.textAlign = "start";
        textarea.addEventListener("input", scheduleUpdate);
      } else if (textWidget) {
        // No textarea element was found, so poll for changes instead.
        let last = null;
        setInterval(() => {
          const current = String(textWidget.value ?? "");
          if (current !== last) {
            last = current;
            scheduleUpdate();
          }
        }, POLL_MS);
      }

      scheduleUpdate();
      return result;
    };

    // When a saved workflow loads, its text arrives after the node is created,
    // so refresh the preview then.
    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      this._ahpMarkdownUpdate?.();
      return result;
    };
  },
});
