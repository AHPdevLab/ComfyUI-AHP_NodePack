// comfyuiAHP_nodepack - AHP Markdown Note frontend.
// The node has two tabs:
// - Plain text: the editor, where the note is written.
// - Markdown:   the rendered note. The server renders it (POST /ahp/markdown/render),
//               so the Python renderer is the only place the Markdown rules live.
// Licensed under the GNU General Public License v3.0. See LICENSE.

import { app } from "../../scripts/app.js";

const NODE_CLASS = "AHP_MarkdownNote";
const TEXT_WIDGET = "text";
const ROUTE = "/ahp/markdown/render";
const DEBOUNCE_MS = 300;
const STYLE_ID = "ahp-markdown-note-style";

const CSS = `
.ahp-md-note { display: flex; flex-direction: column; gap: 6px; width: 100%; height: 100%; min-height: 0; box-sizing: border-box; }
.ahp-md-tabs { display: flex; gap: 4px; }
.ahp-md-tab {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid #444;
  border-radius: 6px;
  background: #2a2a2a;
  color: #aaa;
  cursor: pointer;
  font-size: 12px;
}
.ahp-md-tab.active { background: #3b3b3b; color: #fff; border-color: #6a6a6a; }
.ahp-md-editor {
  box-sizing: border-box;
  width: 100%;
  flex: 1 1 auto;
  min-height: 120px;
  resize: none;
  padding: 12px 16px;
  border-radius: 6px;
  border: 1px solid #333;
  background: #1e1e1e;
  color: #e6e6e6;
  font-family: Vazirmatn, Tahoma, "Segoe UI", "Noto Naskh Arabic", "Noto Sans", sans-serif;
  font-size: 14px;
  line-height: 1.7;
  text-align: start;
}
.ahp-md-preview {
  box-sizing: border-box;
  width: 100%;
  flex: 1 1 auto;
  min-height: 120px;
  overflow: auto;
  padding: 12px 16px;
  border-radius: 6px;
  background: #1e1e1e;
  color: #e6e6e6;
  font-family: Vazirmatn, Tahoma, "Segoe UI", "Noto Naskh Arabic", "Noto Sans", sans-serif;
  font-size: 14px;
  line-height: 1.7;
  text-align: start;
}
.ahp-md-preview:empty::before { content: "Nothing to show yet."; opacity: 0.5; }
.ahp-md-preview .ahp-md-error { color: #ff8a8a; direction: ltr; text-align: left; }
.ahp-md h1, .ahp-md h2, .ahp-md h3, .ahp-md h4, .ahp-md h5, .ahp-md h6 { margin: 0.8em 0 0.4em; line-height: 1.3; }
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
.ahp-md pre.ahp-frontmatter { color: #aaa; }
.ahp-md blockquote { margin: 0.6em 0; padding: 0.2em 1em; border-inline-start: 3px solid #666; color: #bbb; }
.ahp-md table { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse; margin: 0.6em 0; }
.ahp-md th, .ahp-md td { border: 1px solid #555; padding: 4px 8px; }
.ahp-md th { background: #2a2a2a; }
.ahp-md hr { border: none; border-top: 1px solid #444; margin: 1em 0; }
.ahp-md ul, .ahp-md ol { padding-inline-start: 2em; margin: 0.4em 10px; }
.ahp-md li.task-list-item { list-style: none; }
.ahp-md li.task-list-item input { margin-inline-end: 0.4em; pointer-events: none; }
.ahp-md dt { font-weight: 600; margin-top: 0.4em; }
.ahp-md dd { margin-inline-start: 1.5em; }
.ahp-md dl.field-list dt { color: #9ad; }
.ahp-md .footnotes { font-size: 0.9em; color: #bbb; }
.ahp-md mark { background: #6b5a00; color: #fff; padding: 0 2px; border-radius: 3px; }
.ahp-md .ahp-wikilink { color: #8fc7ff; border-bottom: 1px dotted #8fc7ff; cursor: default; }
.ahp-md .ahp-math-block { margin: 0.5em 0; overflow-x: auto; text-align: center; }
.ahp-md .ahp-math-error { color: #ff8a8a; }
.ahp-md .admonition, .ahp-md .ahp-callout {
  border-inline-start: 4px solid #4a8fd8;
  background: #232a33;
  padding: 6px 12px;
  margin: 0.6em 0;
  border-radius: 4px;
}
.ahp-md .admonition-title { font-weight: 600; margin: 0.2em 0; }
.ahp-md .ahp-callout-warning, .ahp-md .ahp-callout-caution { border-color: #d89a2a; background: #332a1c; }
.ahp-md .ahp-callout-tip, .ahp-md .ahp-callout-success { border-color: #3aaa6a; background: #1c3026; }
.ahp-md .ahp-callout-danger, .ahp-md .ahp-callout-error, .ahp-md .ahp-callout-bug { border-color: #d84a4a; background: #361e1e; }
.ahp-md sub, .ahp-md sup { font-size: 0.75em; }
`;

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = CSS;
  document.head.appendChild(style);
}

function makeTab(label) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ahp-md-tab";
  button.textContent = label;
  return button;
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

      // Replace the plain multi-line widget with the tabbed editor. The new
      // widget keeps the same name ("text"), so saved workflows still load.
      const nativeText = this.widgets?.find((w) => w.name === TEXT_WIDGET);
      const initial = nativeText ? String(nativeText.value ?? "") : "";
      if (nativeText) {
        this.widgets.splice(this.widgets.indexOf(nativeText), 1);
        // Remove the original textarea from the page too, or it stays visible.
        nativeText.inputEl?.remove();
        nativeText.element?.remove();
        nativeText.onRemove?.();
      }

      const container = document.createElement("div");
      container.className = "ahp-md-note";

      const tabBar = document.createElement("div");
      tabBar.className = "ahp-md-tabs";
      const plainTab = makeTab("Plain text");
      const markdownTab = makeTab("Markdown");
      tabBar.append(plainTab, markdownTab);

      const editor = document.createElement("textarea");
      editor.className = "ahp-md-editor";
      editor.dir = "auto";
      editor.spellcheck = false;
      editor.value = initial;

      const preview = document.createElement("div");
      preview.className = "ahp-md-preview ahp-md";
      preview.dir = "auto";

      container.append(tabBar, editor, preview);

      let mode = "plain";
      let latest = 0;
      let timer = null;

      // Renders the note on the server. Only the newest reply is shown.
      const render = async () => {
        if (mode !== "markdown") return;
        const id = ++latest;
        try {
          const response = await fetch(ROUTE, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: editor.value }),
          });
          const data = await response.json();
          if (id !== latest) return;
          if (!response.ok || data.error) {
            preview.replaceChildren();
            const err = document.createElement("div");
            err.className = "ahp-md-error";
            err.textContent = data.error || "Preview could not be rendered.";
            preview.appendChild(err);
          } else {
            // The server escapes raw HTML, so its output is safe to insert.
            preview.innerHTML = data.html;
          }
        } catch (error) {
          if (id !== latest) return;
          preview.textContent = `Preview error: ${error}`;
        }
      };

      const scheduleRender = () => {
        clearTimeout(timer);
        timer = setTimeout(render, DEBOUNCE_MS);
      };

      const setMode = (next) => {
        mode = next;
        plainTab.classList.toggle("active", next === "plain");
        markdownTab.classList.toggle("active", next === "markdown");
        editor.style.display = next === "plain" ? "" : "none";
        preview.style.display = next === "markdown" ? "" : "none";
        if (next === "markdown") render();
      };

      plainTab.addEventListener("click", () => setMode("plain"));
      markdownTab.addEventListener("click", () => setMode("markdown"));
      editor.addEventListener("input", () => {
        if (mode === "markdown") scheduleRender();
      });

      this.addDOMWidget(TEXT_WIDGET, "ahp_markdown_text", container, {
        getValue: () => editor.value,
        setValue: (value) => {
          editor.value = value ?? "";
          if (mode === "markdown") scheduleRender();
        },
        serialize: true,
        hideOnZoom: false,
        getMinHeight: () => 280,
      });

      setMode("plain");
      this._ahpMarkdownRefresh = () => {
        if (mode === "markdown") scheduleRender();
      };
      return result;
    };

    nodeType.prototype.onConfigure = function () {
      const result = onConfigure?.apply(this, arguments);
      this._ahpMarkdownRefresh?.();
      return result;
    };
  },
});