"""
AHP Markdown Note

A text note with a rich Markdown renderer, for notes written in any language,
including right-to-left (RTL) languages such as Persian, Arabic and Hebrew.

Supported Markdown:
- CommonMark: headings, emphasis, links, images, lists, quotes, code blocks,
  horizontal rules, hard line breaks
- GitHub Flavored Markdown: tables and ~~strikethrough~~
- Task lists:           - [x] done / - [ ] to do
- Footnotes:            text[^1] ... [^1]: note
- Definition lists:     Term / : definition
- Math:                 $inline$ and $$display$$ (LaTeX, shown as MathML)

RTL handling: every block (paragraph, heading, list item, quote, table cell)
gets dir="auto", so the browser sets its direction from its first strong
character. Code and math always stay left-to-right.

Raw HTML in the note is escaped, not rendered, so notes cannot inject markup.

The node has two outputs: the note's raw Markdown, and the rendered HTML.
The live preview in the node uses the route below.

Licensed under the GNU General Public License v3.0. See LICENSE.
"""

from html import escape

from aiohttp import web

# The node must appear in the node list even if its libraries are missing.
# Rendering then fails with a clear message, instead of the node vanishing.
_MISSING_LIBRARY = None
try:
    from markdown_it import MarkdownIt
    from mdit_py_plugins.deflist import deflist_plugin
    from mdit_py_plugins.dollarmath import dollarmath_plugin
    from mdit_py_plugins.footnote import footnote_plugin
    from mdit_py_plugins.tasklists import tasklists_plugin
    from latex2mathml.converter import convert as latex_to_mathml
except ImportError as _error:
    _MISSING_LIBRARY = str(_error)

try:
    from server import PromptServer
except ImportError:  # Lets the module be imported outside ComfyUI, e.g. in tests
    PromptServer = None


ROUTE = "/ahp/markdown/render"
MAX_CHARS = 2_000_000  # Refuse absurdly large notes

# Block-level tokens that get dir="auto" so each block follows its own language.
AUTO_DIRECTION_TOKENS = {
    "paragraph_open",
    "heading_open",
    "list_item_open",
    "blockquote_open",
    "th_open",
    "td_open",
    "dt_open",
    "dd_open",
}


def _render_math_inline(self, tokens, idx, options, env):
    return _math(tokens[idx].content, display=False)


def _render_math_block(self, tokens, idx, options, env):
    return f'<div class="ahp-math-block" dir="ltr">{_math(tokens[idx].content, display=True)}</div>\n'


def _math(latex, display):
    """Convert LaTeX to MathML. If the LaTeX is invalid, show it as plain code."""
    try:
        mathml = latex_to_mathml(latex.strip())
    except Exception:
        return f'<code class="ahp-math-error" dir="ltr">{escape(latex)}</code>'
    if display:
        mathml = mathml.replace('display="inline"', 'display="block"', 1)
    return mathml


def _mark_auto_direction(state):
    for token in state.tokens:
        if token.type in AUTO_DIRECTION_TOKENS:
            token.attrSet("dir", "auto")


def _build_renderer():
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    md.enable(["table", "strikethrough"])
    md.use(footnote_plugin)
    md.use(tasklists_plugin, enabled=True)
    md.use(deflist_plugin)
    md.use(dollarmath_plugin, allow_space=True, double_inline=True)
    md.add_render_rule("math_inline", _render_math_inline)
    md.add_render_rule("math_block", _render_math_block)
    md.core.ruler.push("ahp_auto_direction", _mark_auto_direction)
    return md


INSTALL_HINT = (
    "The AHP Markdown Note needs three Python libraries that are not installed "
    f"in this ComfyUI environment ({_MISSING_LIBRARY}). Install them with: "
    "python -m pip install -r custom_nodes/comfyuiAHP_nodepack/requirements.txt "
    "then restart ComfyUI."
)

_RENDERER = _build_renderer() if _MISSING_LIBRARY is None else None


def render_markdown(text):
    """Return the note as an HTML fragment wrapped in a dir="auto" container."""
    if _RENDERER is None:
        raise RuntimeError(INSTALL_HINT)
    source = text or ""
    if len(source) > MAX_CHARS:
        raise ValueError(f"Note is too large ({len(source)} characters; the limit is {MAX_CHARS}).")
    return f'<div class="ahp-md" dir="auto">{_RENDERER.render(source)}</div>'


if PromptServer is not None:

    @PromptServer.instance.routes.post(ROUTE)
    async def ahp_render_markdown(request):
        """Live preview: takes {"text": ...} and returns {"html": ...}."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "Request body must be JSON."}, status=400)
        text = body.get("text", "") if isinstance(body, dict) else ""
        try:
            return web.json_response({"html": render_markdown(str(text))})
        except ValueError as error:
            return web.json_response({"error": str(error)}, status=413)
        except RuntimeError as error:
            return web.json_response({"error": str(error)}, status=500)


class AHPMarkdownNote:
    """Outputs the note as raw Markdown and as rendered HTML."""

    CATEGORY = "AHP/Text"
    FUNCTION = "make_note"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("markdown", "html")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "text": ("STRING", {"default": "", "multiline": True}),
            },
        }

    def make_note(self, text=""):
        source = text or ""
        return (source, render_markdown(source))


NODE_CLASS_MAPPINGS = {
    "AHP_MarkdownNote": AHPMarkdownNote,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AHP_MarkdownNote": "AHP Markdown Note",
}
