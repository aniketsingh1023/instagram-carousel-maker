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
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
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
        time.sleep(4)

        # Verify logged in
        if "login" in page.url or page.query_selector('input[name="username"]'):
            raise RuntimeError(
                "Session expired. Run 'python create_session.py' again and update INSTA_SESSION."
            )

        log.info(f"Logged in at {page.url}. Opening create modal...")

        # Click the sidebar "New post" / "+" button — it opens a modal (no URL change)
        create_clicked = False
        for selector in [
            '[aria-label="New post"]',
            'svg[aria-label="New post"]',
            '[aria-label="Create"]',
            'a[href="/create/style/select/"]',
        ]:
            try:
                el = page.locator(selector).first
                el.wait_for(state="visible", timeout=4000)
                el.click()
                create_clicked = True
                log.info(f"Clicked create button via: {selector}")
                time.sleep(3)
                break
            except Exception:
                continue

        if not create_clicked:
            # JS fallback — find any element with aria-label containing "new post" or "create"
            found = page.evaluate("""
                () => {
                    const labels = ['New post', 'Create', 'new post'];
                    for (const label of labels) {
                        const el = document.querySelector(`[aria-label="${label}"]`);
                        if (el) {
                            const btn = el.closest('a, button, [role="button"]') || el;
                            btn.click();
                            return label;
                        }
                    }
                    return null;
                }
            """)
            if found:
                log.info(f"Clicked create button via JS eval: {found}")
                time.sleep(3)
                create_clicked = True
            else:
                log.warning("Could not find create button — modal may not open")

        # Screenshot after clicking create
        try:
            page.screenshot(path="data/debug_01_after_create_click.png", full_page=False)
            log.info(f"Screenshot saved. URL: {page.url}")
        except Exception:
            pass

        # Click "Post" from the submenu that appeared (Post / Live video / Ad / AI)
        post_clicked = False
        for sel in [
            'a[href="/create/style/"]',
            'a:has-text("Post")',
            '[role="menuitem"]:has-text("Post")',
            'span:has-text("Post")',
            'div:has-text("Post")',
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.click()
                    post_clicked = True
                    log.info(f"Clicked Post submenu via: {sel}")
                    time.sleep(3)
                    break
            except Exception:
                continue

        if not post_clicked:
            log.warning("Could not click Post submenu item")

        # Screenshot after clicking Post — should show the file upload modal
        try:
            page.screenshot(path="data/debug_01b_after_post_click.png", full_page=False)
        except Exception:
            pass

        # ── Upload all slides via the modal's "Select from computer" button ──
        log.info(f"Uploading {len(image_paths)} slides...")
        try:
            with page.expect_file_chooser(timeout=12000) as fc_info:
                page.get_by_role("button", name="Select from computer").first.click(timeout=10000)
            fc_info.value.set_files([str(p) for p in image_paths])
            log.info("All slides uploaded via 'Select from computer' file chooser")
        except Exception as e:
            log.warning(f"File chooser failed ({e}), trying JS fallback...")
            page.evaluate(
                "document.querySelectorAll('input[type=\"file\"]')"
                ".forEach(el => { el.multiple = true; })"
            )
            time.sleep(0.3)
            page.locator('input[type="file"]').first.set_input_files(
                [str(p) for p in image_paths]
            )
            log.info("All slides uploaded via JS multiple=true fallback")

        # Screenshot after upload
        try:
            page.screenshot(path="data/debug_02_after_upload.png", full_page=False)
        except Exception:
            pass

        time.sleep(4)

        # OK button on any aspect-ratio / crop dialog
        try:
            page.get_by_role("button", name="OK").click(timeout=3000)
            time.sleep(1)
        except Exception:
            pass

        # Click through crop step
        self._click_next(page, step="crop")

        # Click through filter/edit step
        self._click_next(page, step="filters")

        # Caption step — add caption
        log.info("Adding caption...")
        try:
            caption_box = page.locator(
                '[aria-label="Write a caption..."], [aria-label="Caption"], textarea'
            ).first
            caption_box.wait_for(timeout=10000)
            caption_box.click()
            caption_box.fill(caption[:2200])  # Instagram 2200 char limit
        except Exception as e:
            log.warning(f"Caption input error: {e}")

        time.sleep(1)

        # Share / Post
        log.info("Sharing post...")
        shared = False
        for btn_name in ("Share", "Post"):
            try:
                page.get_by_role("button", name=btn_name).first.click(timeout=6000)
                shared = True
                break
            except Exception:
                continue
        if not shared:
            raise RuntimeError("Could not find Share/Post button")

        # Wait for success confirmation
        try:
            page.wait_for_selector(
                ':text("Your post has been shared"), '
                ':text("Post shared"), '
                '[data-testid="post-shared"]',
                timeout=40000,
            )
            log.info("Post shared successfully!")
        except Exception:
            log.warning("Could not confirm post success dialog, but may have posted")

        time.sleep(3)
        return "posted"

    def _upload_one_file(self, page, img_path: Path) -> None:
        """Upload a single image file to whatever file input is on the current page."""
        # Try file chooser via "Select from computer" button
        try:
            with page.expect_file_chooser(timeout=6000) as fc_info:
                page.get_by_role("button", name="Select from computer").first.click(timeout=4000)
            fc_info.value.set_files([str(img_path)])
            return
        except Exception:
            pass
        # Fallback: JS force multiple=true then set_input_files (single file, always valid)
        page.evaluate(
            "document.querySelectorAll('input[type=\"file\"]')"
            ".forEach(el => { el.multiple = true; })"
        )
        time.sleep(0.3)
        page.locator('input[type="file"]').first.set_input_files([str(img_path)])

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
