"""Brand logo storage in GitHub.

Logos are committed to the repo under brand-assets/<brand-slug>/<brand-slug>_logo
and read back through the GitHub contents API, so the same store serves the web
UI (via a proxy) and the export renderer. Requires a fine-grained PAT with
contents:write on the repo (settings.github_token). All calls are best effort:
a missing token or failed call returns None so a logo is simply absent, never an
error that breaks brand management or an export.
"""

from __future__ import annotations

import base64
import re

import httpx

from .config import settings

_API = "https://api.github.com"


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "brand"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def logo_path(brand_name: str, ext: str) -> str:
    slug = _slug(brand_name)
    ext = (ext or "png").lstrip(".").lower()
    return f"brand-assets/{slug}/{slug}_logo.{ext}"


def commit_logo(brand_name: str, content: bytes, ext: str) -> str | None:
    """Commit (or update) a brand logo. Returns the repo path, or None if it
    could not be stored (no token, network error)."""
    if not settings.github_token:
        return None
    path = logo_path(brand_name, ext)
    url = f"{_API}/repos/{settings.github_repo}/contents/{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            existing = client.get(
                url, headers=_headers(), params={"ref": settings.github_branch}
            )
            sha = existing.json().get("sha") if existing.status_code == 200 else None
            body = {
                "message": f"Add brand logo for {brand_name}",
                "content": base64.b64encode(content).decode(),
                "branch": settings.github_branch,
            }
            if sha:
                body["sha"] = sha
            resp = client.put(url, headers=_headers(), json=body)
            resp.raise_for_status()
        return path
    except Exception:  # pragma: no cover - network path, best effort
        return None


def fetch_logo(path: str) -> bytes | None:
    """Read a logo's bytes back from the repo, or None if unavailable."""
    if not settings.github_token or not path:
        return None
    url = f"{_API}/repos/{settings.github_repo}/contents/{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                url, headers=_headers(), params={"ref": settings.github_branch}
            )
            resp.raise_for_status()
            return base64.b64decode(resp.json()["content"])
    except Exception:  # pragma: no cover - network path, best effort
        return None
