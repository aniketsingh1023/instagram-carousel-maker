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
            value = self.session_b64.strip()

            # Detect if it's a raw sessionid cookie (not base64 JSON)
            # Raw sessionids look like: 61986645064%3Axxx or 61986645064:xxx
            if self._looks_like_sessionid(value):
                import urllib.parse
                sessionid = urllib.parse.unquote(value)
                log.info("Detected raw sessionid — logging in via sessionid...")
                try:
                    self.client.login_by_sessionid(sessionid)
                    log.info("Login by sessionid successful!")
                    return
                except Exception as e:
                    raise RuntimeError(f"sessionid login failed: {e}") from e

            # Otherwise treat as base64-encoded JSON settings file
            self._restore_session(value, session_path)
            if self._ping_session():
                log.info("Session restored successfully")
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

    def _looks_like_sessionid(self, value: str) -> bool:
        """Raw sessionids start with digits (user ID) followed by : or %3A."""
        import re
        return bool(re.match(r'^\d{5,20}(%3A|:)', value))

    def _ping_session(self) -> bool:
        try:
            self.client.get_timeline_feed()
            return True
        except Exception:
            return False

    def _fresh_login(self, session_path: Path) -> None:
        raise RuntimeError(
            "No valid INSTA_SESSION found. "
            "Run 'python create_session.py' locally to generate a session, "
            "then add it as the INSTA_SESSION GitHub Secret."
        )

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
