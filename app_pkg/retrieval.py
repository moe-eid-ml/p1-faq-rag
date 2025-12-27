

"""
Shared retrieval helpers.

Why this file exists:
- Keep small, stable utilities (path normalization, file keys, link building) in ONE place.
- Avoid duplicating link logic across app.py / cli.py / tests.
- Keep this module dependency-light (no imports from app.py) to avoid cycles.
"""

from __future__ import annotations

from os.path import basename
from urllib.parse import quote


def normalize_relpath(path: str) -> str:
    """
    Normalize a repo-relative path so it is safe to embed in URLs across OSes.

    Examples:
      r"docs\\wohngeld\\a.txt" -> "docs/wohngeld/a.txt"
      "./docs/x.txt" -> "docs/x.txt"
    """
    rel = str(path).replace("\\", "/").lstrip("./")
    return rel


def file_key(path: str) -> str:
    """Stable file identifier for 'file-level' grouping (basename, lowercased)."""
    return basename(path).lower()


def source_url(path: str, *, link_mode: str, github_blob_base: str) -> str:
    """
    Build a clickable URL for a source path.

    link_mode:
      - "github": points to the GitHub blob URL (shareable)
      - "local": uses Gradio’s /file= route (clickable in browser; works on HF too)
    """
    rel = normalize_relpath(path)
    if link_mode == "local":
        # Browsers often block file:// from http pages; Gradio serves files via /file=
        return f"/file={quote(rel, safe='/')}"
    # default: github
    return github_blob_base + quote(rel, safe="/")