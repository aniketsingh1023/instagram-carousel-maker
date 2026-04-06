"""Fetches tech tool/language logos from SimpleIcons CDN and converts SVG→PIL."""

import io
import logging
import re

import cairosvg
import requests
from PIL import Image

log = logging.getLogger(__name__)

# Maps common topic keywords → SimpleIcons slug
# Full list at https://simpleicons.org/
ICON_MAP = {
    "python":     "python",
    "javascript": "javascript",
    "js":         "javascript",
    "typescript": "typescript",
    "ts":         "typescript",
    "react":      "react",
    "nextjs":     "nextdotjs",
    "next.js":    "nextdotjs",
    "node":       "nodedotjs",
    "nodejs":     "nodedotjs",
    "docker":     "docker",
    "kubernetes": "kubernetes",
    "k8s":        "kubernetes",
    "git":        "git",
    "github":     "github",
    "linux":      "linux",
    "rust":       "rust",
    "go":         "go",
    "golang":     "go",
    "java":       "openjdk",
    "fastapi":    "fastapi",
    "django":     "django",
    "flask":      "flask",
    "redis":      "redis",
    "sql":        "postgresql",
    "postgres":   "postgresql",
    "mysql":      "mysql",
    "mongodb":    "mongodb",
    "aws":        "amazonaws",
    "devops":     "githubactions",
    "ci/cd":      "githubactions",
    "ai":         "openai",
    "machine learning": "tensorflow",
    "ml":         "tensorflow",
    "css":        "css3",
    "html":       "html5",
    "graphql":    "graphql",
    "terraform":  "terraform",
    "ansible":    "ansible",
    "vim":        "vim",
    "vscode":     "visualstudiocode",
    "bash":       "gnubash",
    "shell":      "gnubash",
    "r":          "r",
    "swift":      "swift",
    "kotlin":     "kotlin",
    "flutter":    "flutter",
    "dart":       "dart",
}


def _detect_icon_slug(topic: str) -> str | None:
    """Fuzzy-match topic string to a SimpleIcons slug."""
    topic_lower = topic.lower()
    for keyword, slug in ICON_MAP.items():
        if keyword in topic_lower:
            return slug
    return None


def fetch_logo(topic: str, size: int = 220, color: str = "00d4ff") -> Image.Image | None:
    """
    Fetch the SimpleIcons logo for the given topic as a PIL RGBA Image.
    Downloads raw SVG from the simpleicons GitHub repo (no CDN auth issues).
    Returns None if no matching icon is found or download fails.
    """
    slug = _detect_icon_slug(topic)
    if not slug:
        log.info(f"No icon found for topic: {topic!r}")
        return None

    # Use raw GitHub (simpleicons repo) — no rate limiting or auth issues
    url = (
        f"https://raw.githubusercontent.com/simple-icons/simple-icons"
        f"/develop/icons/{slug}.svg"
    )
    headers = {"User-Agent": "carousel-maker/1.0"}
    try:
        resp = requests.get(url, timeout=10, headers=headers)
        if resp.status_code == 404:
            log.info(f"No icon in simple-icons for slug={slug!r}")
            return None
        resp.raise_for_status()

        svg_bytes = resp.content
        if not svg_bytes.strip().startswith(b"<"):
            log.warning(f"Got non-SVG response for slug={slug!r}")
            return None

        # Colorize: replace fill with our cyan color
        svg_colored = svg_bytes.decode().replace(
            'fill="currentColor"', f'fill="#{color}"'
        ).replace(
            "currentColor", f"#{color}"
        ).encode()

        png_bytes = cairosvg.svg2png(
            bytestring=svg_colored,
            output_width=size,
            output_height=size,
        )
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        log.info(f"Fetched logo for {topic!r} → simpleicons:{slug}")
        return img

    except Exception as e:
        log.warning(f"Failed to fetch logo for {topic!r}: {e}")
        return None


def make_logo_glow(logo: Image.Image, glow_color=(0, 212, 255)) -> Image.Image:
    """
    Composite a soft glow layer behind the logo for the cyberpunk effect.
    Returns a new RGBA image (logo size + padding for glow bleed).
    """
    from PIL import ImageFilter

    pad = 60
    w, h = logo.size
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))

    # Glow layer — colorize the alpha channel of logo
    glow_base = Image.new("RGBA", logo.size, (*glow_color, 0))
    r, g, b, a = logo.split()
    glow_base.putalpha(a)
    glow_canvas = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_canvas.paste(glow_base, (pad, pad))
    glow_blurred = glow_canvas.filter(ImageFilter.GaussianBlur(radius=24))

    canvas = Image.alpha_composite(canvas, glow_blurred)
    canvas.paste(logo, (pad, pad), logo)
    return canvas
