"""Deterministic syntax highlighting for exported Org source blocks.

Org exports src blocks as ``<pre class="src src-<lang>">`` without
fontification (emacs-nox has no htmlize). This module re-lexes those
blocks with Pygments so pages get syntax highlighting without any
client-side JavaScript.
"""

from __future__ import annotations

import html as html_module
import re

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

_LANG_ALIASES = {
    "sh": "bash",
    "shell": "bash",
    "console": "bash",
    "terminal": "bash",
    "emacs-lisp": "emacs-lisp",
    "elisp": "emacs-lisp",
    "common-lisp": "common-lisp",
    "cl": "common-lisp",
    "js": "javascript",
    "ts": "typescript",
    "yml": "yaml",
    "md": "markdown",
    "org": "org-mode",
    "nix": "nix",
    "rest": "http",
}

_PRE_RE = re.compile(
    r'<pre class="src src-([A-Za-z0-9_-]+)">(.*?)</pre>', re.DOTALL
)
_UNESCAPES = [
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&quot;", '"'),
    ("&#39;", "'"),
    ("&amp;", "&"),
]

_formatter = HtmlFormatter(nowrap=True, classprefix="")


def _unescape(text: str) -> str:
    for entity, char in _UNESCAPES:
        text = text.replace(entity, char)
    return text


_CODE_WRAPPER_RE = re.compile(r"^\s*<code[^>]*>(.*)</code>\s*$", re.DOTALL)


def _highlight(code: str, lang: str) -> str | None:
    lang = _LANG_ALIASES.get(lang, lang)
    try:
        lexer = get_lexer_by_name(lang, stripnl=False, ensurenl=False)
    except ClassNotFound:
        return None
    return highlight(code, lexer, _formatter).rstrip("\n")


def highlight_fragment(fragment: str) -> str:
    """Re-highlight every recognized src block in an exported fragment."""

    def replace(match: re.Match) -> str:
        lang = match.group(1)
        code = _unescape(match.group(2))
        # ox-html wraps src contents in <code> inside <pre>; the wrapper is
        # markup, not content, and must never reach the lexer.
        wrapper = _CODE_WRAPPER_RE.match(code)
        if wrapper:
            code = wrapper.group(1)
        marked = _highlight(code, lang)
        if marked is None:
            inner = html_module.escape(code)
            return f'<pre class="src src-{lang}">{inner}</pre>'
        return f'<pre class="src src-{lang}"><span class="highlight">{marked}</span></pre>'

    return _PRE_RE.sub(replace, fragment)
