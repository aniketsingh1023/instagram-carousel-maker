"""Main orchestrator: generate content → render slides → post to Instagram."""

import logging
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def load_config():
    from config import Config

    required = {
        "GEMINI_API_KEY":  "Get free key at https://aistudio.google.com/app/apikey",
        "IG_ACCESS_TOKEN": "Instagram Graph API token (see setup instructions)",
        "IG_USER_ID":      "Your numeric Instagram user ID (see setup instructions)",
        "INSTA_HANDLE":    "Your handle for watermark, e.g. @devvoxx",
    }
    missing = {k: v for k, v in required.items() if not os.getenv(k)}
    if missing:
        for var, hint in missing.items():
            log.error(f"Missing {var} — {hint}")
        sys.exit(1)

    return Config(
        gemini_key=os.environ["GEMINI_API_KEY"],
        ig_username="",
        ig_password="",
        ig_handle=os.environ["INSTA_HANDLE"],
        insta_session=None,
        dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
        topic_override=os.getenv("TOPIC_OVERRIDE", "").strip(),
    )


def main():
    cfg = load_config()
    log.info(f"Starting carousel maker | dry_run={cfg.dry_run}")

    # ── 1. Generate content ────────────────────────────────────────────────────
    from src.content_generator import ContentGenerator
    generator = ContentGenerator(api_key=cfg.gemini_key)
    topic = generator.pick_topic()
    log.info(f"Topic: {topic}")

    content = generator.generate_carousel(topic)
    log.info(f"Generated {len(content.slides)} slides")

    # ── 2. Fetch tool logo ─────────────────────────────────────────────────────
    from src.image_fetcher import fetch_logo
    logo = fetch_logo(topic)
    if logo:
        log.info("Tool logo fetched successfully")
    else:
        log.info("No logo found, using emoji fallback")

    # ── 3. Render carousel images ──────────────────────────────────────────────
    from src.carousel_designer import CarouselDesigner
    designer = CarouselDesigner(handle=cfg.ig_handle)
    slide_paths = designer.render_carousel(content, logo=logo)
    log.info(f"Rendered {len(slide_paths)} slides to disk")

    # ── 4. Post to Instagram ───────────────────────────────────────────────────
    from src.instagram_poster import InstagramPoster
    poster = InstagramPoster(
        username=cfg.ig_username,
        password=cfg.ig_password,
        session_b64=cfg.insta_session,
    )
    poster.login()
    post_id = poster.post_carousel(slide_paths, content.caption)
    log.info(f"Post ID: {post_id}")

    # ── 5. Cleanup ─────────────────────────────────────────────────────────────
    if not cfg.dry_run:
        generator.mark_topic_used(topic)
        for p in slide_paths:
            p.unlink(missing_ok=True)
        log.info("Slides cleaned up")
    else:
        log.info(f"[DRY RUN] Slides kept in data/slides/ for inspection")

    log.info("Done!")


if __name__ == "__main__":
    main()
