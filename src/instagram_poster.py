"""Posts carousel images to Instagram using Playwright (real browser automation)."""

import base64
import json
import logging
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from config import SESSION_FILE, DELAY_RANGE

log = logging.getLogger(__name__)

STORAGE_FILE = Path("data/ig_browser_state.json")


class InstagramPoster:
    def __init__(self, username: str, password: str, session_b64: str | None = None):
        self.username = username
        self.password = password
        self.session_b64 = session_b64

    def login(self) -> None:
        """Validate session exists. Actual browser is launched per-post."""
        if not self.session_b64:
            raise RuntimeError(
                "No INSTA_SESSION found.\n"
                "Run 'python create_session.py' locally to generate one,\n"
                "then add it as the INSTA_SESSION GitHub Secret."
            )
        # Decode and write storage state to disk
        try:
            STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            state_json = base64.b64decode(self.session_b64.strip()).decode()
            json.loads(state_json)  # validate it's proper JSON
            STORAGE_FILE.write_text(state_json)
            log.info("Browser session loaded from secret")
        except Exception as e:
            raise RuntimeError(
                f"Invalid INSTA_SESSION — run 'python create_session.py' again: {e}"
            ) from e

    def post_carousel(self, image_paths: list[Path], caption: str) -> str:
        dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        if dry_run:
            log.info("[DRY RUN] Skipping actual post")
            log.info(f"[DRY RUN] Caption: {caption[:120]}")
            log.info(f"[DRY RUN] Slides: {[p.name for p in image_paths]}")
            return "DRY_RUN"

        self._validate_images(image_paths)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                storage_state=str(STORAGE_FILE),
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1"
                ),
            )
            try:
                post_id = self._do_post(context, image_paths, caption)
                return post_id
            finally:
                context.close()
                browser.close()

    def _do_post(self, context, image_paths: list[Path], caption: str) -> str:
        page = context.new_page()
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        time.sleep(3)

        # Verify logged in
        if "login" in page.url or page.query_selector('input[name="username"]'):
            raise RuntimeError(
                "Session expired. Run 'python create_session.py' again and update INSTA_SESSION."
            )

        log.info("Logged in, navigating to create post...")

        # Click the Create / + button
        try:
            # Try SVG icon button (desktop layout)
            create_btn = page.locator('a[href="/create/select/"]').first
            if not create_btn.is_visible(timeout=3000):
                raise PWTimeout("not visible")
            create_btn.click()
        except Exception:
            # Fallback: click by aria label
            page.get_by_label("New post").first.click()

        time.sleep(2)

        # Click "Post" if a type-selection dialog appears
        try:
            page.get_by_role("button", name="Post").first.click(timeout=3000)
            time.sleep(1)
        except Exception:
            pass  # Already in file select mode

        # Upload images via hidden file input
        log.info(f"Uploading {len(image_paths)} slides...")
        file_input = page.locator('input[type="file"]').first
        file_input.set_files([str(p) for p in image_paths])
        time.sleep(3)

        # If Instagram asks to select multiple for carousel, click it
        try:
            page.get_by_role("button", name="Select multiple").click(timeout=3000)
            time.sleep(1)
        except Exception:
            pass

        # Click through crop step
        self._click_next(page, step="crop")

        # Click through filter step
        self._click_next(page, step="filters")

        # Caption step — add caption
        log.info("Adding caption...")
        try:
            caption_box = page.locator('[aria-label="Write a caption..."]').first
            caption_box.wait_for(timeout=8000)
            caption_box.click()
            caption_box.fill(caption[:2200])  # Instagram 2200 char limit
        except Exception as e:
            log.warning(f"Caption input error: {e}")

        time.sleep(1)

        # Share / Post
        log.info("Sharing post...")
        try:
            page.get_by_role("button", name="Share").click(timeout=5000)
        except Exception:
            page.get_by_role("button", name="Post").click(timeout=5000)

        # Wait for success confirmation
        try:
            page.wait_for_selector(
                'text=Your post has been shared, [aria-label="Like"], '
                '[data-testid="post-shared"]',
                timeout=30000,
            )
            log.info("Post shared successfully!")
        except Exception:
            # May have posted even without confirmation dialog
            log.warning("Could not confirm post success, but may have worked")

        time.sleep(2)
        return "posted"

    def _click_next(self, page, step: str = "") -> None:
        try:
            btn = page.get_by_role("button", name="Next").first
            btn.wait_for(timeout=8000)
            btn.click()
            time.sleep(2)
            log.info(f"Clicked Next ({step})")
        except Exception as e:
            log.warning(f"Next button ({step}): {e}")

    def _validate_images(self, paths: list[Path]) -> None:
        from PIL import Image
        if len(paths) < 2:
            raise ValueError(f"Need at least 2 images, got {len(paths)}")
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Missing slide: {path}")
            img = Image.open(path)
            w, h = img.size
            if w != 1080 or h != 1080:
                raise ValueError(f"{path.name} must be 1080x1080, got {w}x{h}")
