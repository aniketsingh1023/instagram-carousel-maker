"""Posts carousel images to Instagram using instagrapi."""

import base64
import logging
import os
import time
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    TwoFactorRequired,
)
from PIL import Image

from config import SESSION_FILE, DELAY_RANGE

log = logging.getLogger(__name__)


class InstagramPoster:
    def __init__(self, username: str, password: str, session_b64: str | None = None):
        self.username = username
        self.password = password
        self.session_b64 = session_b64
        self.client = Client()
        self.client.delay_range = DELAY_RANGE
        # Simulate iPhone 13 — matches a real common device to avoid bot detection
        self.client.set_device({
            "app_version": "269.0.0.18.75",
            "android_version": 26,
            "android_release": "8.0.0",
            "dpi": "460dpi",
            "resolution": "1080x2340",
            "manufacturer": "Apple",
            "device": "iPhone13,2",
            "model": "iPhone 13",
            "cpu": "apple_a15_bionic",
            "version_code": "314665256",
        })

    def login(self) -> None:
        session_path = Path(SESSION_FILE)

        if self.session_b64:
            self._restore_session(self.session_b64, session_path)
            if self._ping_session():
                log.info("Session restored successfully - no re-login needed")
                return
            log.warning("Stored session invalid, performing fresh login...")

        self._fresh_login(session_path)

    def post_carousel(self, image_paths: list[Path], caption: str) -> str:
        self._validate_images(image_paths)

        dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        if dry_run:
            log.info("[DRY RUN] Would post carousel with caption:")
            log.info(caption[:200])
            log.info(f"[DRY RUN] Images: {[str(p) for p in image_paths]}")
            return "DRY_RUN_NO_POST_ID"

        log.info(f"Uploading {len(image_paths)}-slide carousel to Instagram...")
        try:
            media = self.client.album_upload(
                paths=[str(p) for p in image_paths],
                caption=caption,
            )
            post_id = str(media.pk)
            log.info(f"Posted successfully! Media ID: {post_id}")
            return post_id
        except ChallengeRequired as e:
            raise RuntimeError(
                "Instagram challenge required. Log in manually once via the app "
                "and update the INSTA_SESSION secret."
            ) from e
        except LoginRequired as e:
            raise RuntimeError(
                "Instagram session expired. Clear INSTA_SESSION secret and re-run."
            ) from e

    # ── Private ────────────────────────────────────────────────────────────────

    def _restore_session(self, b64: str, session_path: Path) -> None:
        try:
            session_path.parent.mkdir(parents=True, exist_ok=True)
            session_path.write_bytes(base64.b64decode(b64))
            self.client.load_settings(str(session_path))
            log.info("Session loaded from base64 secret")
        except Exception as e:
            log.warning(f"Failed to restore session: {e}")

    def _ping_session(self) -> bool:
        try:
            self.client.get_timeline_feed()
            return True
        except Exception:
            return False

    def _fresh_login(self, session_path: Path) -> None:
        log.info(f"Logging in as {self.username}...")
        try:
            self.client.login(self.username, self.password)
        except TwoFactorRequired:
            raise RuntimeError(
                "Two-factor authentication is required. "
                "Disable 2FA or use an app password for this account."
            )

        # Save session and print new base64 for GitHub Secret update
        session_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.dump_settings(str(session_path))
        new_b64 = base64.b64encode(session_path.read_bytes()).decode()
        # This is captured by the GitHub Actions post-step to update the secret
        print(f"NEW_SESSION_B64={new_b64}")
        log.info("Session saved. Update INSTA_SESSION secret with the NEW_SESSION_B64 above.")

    def _validate_images(self, paths: list[Path]) -> None:
        if len(paths) < 2:
            raise ValueError(f"Need at least 2 images for a carousel, got {len(paths)}")
        if len(paths) > 10:
            raise ValueError(f"Instagram allows max 10 images, got {len(paths)}")

        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Slide not found: {path}")
            try:
                img = Image.open(path)
                w, h = img.size
                if w != 1080 or h != 1080:
                    raise ValueError(f"{path.name} must be 1080x1080, got {w}x{h}")
            except Exception as e:
                raise ValueError(f"Invalid image {path.name}: {e}") from e
