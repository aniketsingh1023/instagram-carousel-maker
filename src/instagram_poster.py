"""Posts carousel images to Instagram using the official Graph API."""

import logging
import os
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)

_API = "https://graph.facebook.com/v21.0"


class InstagramPoster:
    def __init__(self, username: str = "", password: str = "", session_b64: str | None = None):
        self.access_token = os.getenv("IG_ACCESS_TOKEN", "")
        self.user_id = os.getenv("IG_USER_ID", "")

    def login(self) -> None:
        if not self.access_token or not self.user_id:
            raise RuntimeError(
                "IG_ACCESS_TOKEN and IG_USER_ID secrets are required.\n"
                "See setup instructions: run 'python get_ig_token.py'"
            )
        r = requests.get(
            f"{_API}/me",
            params={"fields": "id,name", "access_token": self.access_token},
            timeout=15,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Invalid IG_ACCESS_TOKEN: {r.text}")
        log.info(f"Graph API authenticated as: {r.json().get('name')}")

    def post_carousel(self, image_paths: list[Path], caption: str) -> str:
        dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        if dry_run:
            log.info("[DRY RUN] Skipping post")
            log.info(f"[DRY RUN] Caption: {caption[:120]}")
            log.info(f"[DRY RUN] Slides: {[p.name for p in image_paths]}")
            return "DRY_RUN"

        self._validate_images(image_paths)

        # 1. Host each image publicly (Instagram pulls from URL)
        log.info(f"Hosting {len(image_paths)} images...")
        image_urls = []
        for i, path in enumerate(image_paths):
            url = self._upload_image(path)
            image_urls.append(url)
            log.info(f"  Slide {i+1} → {url}")

        # 2. Create a media container for each image
        log.info("Creating per-image containers...")
        child_ids = []
        for url in image_urls:
            cid = self._create_image_container(url)
            child_ids.append(cid)
            time.sleep(1)
        log.info(f"Created {len(child_ids)} containers")

        # 3. Create the carousel container
        log.info("Creating carousel container...")
        carousel_id = self._create_carousel_container(child_ids, caption)

        # 4. Wait for Instagram to process media
        log.info("Waiting for media processing...")
        self._wait_until_finished(carousel_id)

        # 5. Publish
        log.info("Publishing...")
        post_id = self._publish(carousel_id)
        log.info(f"Published! Post ID: {post_id}")
        return post_id

    # ── Private helpers ──────────────────────────────────────────────────────

    def _upload_image(self, path: Path) -> str:
        """Upload image to catbox.moe for free public hosting (no account needed)."""
        for attempt in range(3):
            try:
                with open(path, "rb") as f:
                    r = requests.post(
                        "https://catbox.moe/user/api.php",
                        data={"reqtype": "fileupload"},
                        files={"fileToUpload": (path.name, f, "image/jpeg")},
                        timeout=60,
                    )
                r.raise_for_status()
                url = r.text.strip()
                if url.startswith("https://"):
                    return url
                raise ValueError(f"Unexpected response: {url}")
            except Exception as e:
                log.warning(f"Upload attempt {attempt+1} failed: {e}")
                time.sleep(3)
        raise RuntimeError(f"Failed to upload {path.name} after 3 attempts")

    def _create_image_container(self, image_url: str) -> str:
        r = requests.post(
            f"{_API}/{self.user_id}/media",
            data={
                "image_url": image_url,
                "is_carousel_item": "true",
                "access_token": self.access_token,
            },
            timeout=30,
        )
        self._check(r, "create image container")
        return r.json()["id"]

    def _create_carousel_container(self, children: list[str], caption: str) -> str:
        r = requests.post(
            f"{_API}/{self.user_id}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "caption": caption[:2200],
                "access_token": self.access_token,
            },
            timeout=30,
        )
        self._check(r, "create carousel container")
        return r.json()["id"]

    def _wait_until_finished(self, container_id: str, timeout: int = 120) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = requests.get(
                f"{_API}/{container_id}",
                params={"fields": "status_code,status", "access_token": self.access_token},
                timeout=15,
            )
            data = r.json()
            status = data.get("status_code", "")
            log.info(f"  Container status: {status}")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"Media processing error: {data}")
            time.sleep(5)
        raise RuntimeError("Timed out waiting for media processing")

    def _publish(self, carousel_id: str) -> str:
        r = requests.post(
            f"{_API}/{self.user_id}/media_publish",
            data={"creation_id": carousel_id, "access_token": self.access_token},
            timeout=30,
        )
        self._check(r, "publish")
        return r.json()["id"]

    def _check(self, r: requests.Response, step: str) -> None:
        if r.status_code != 200:
            raise RuntimeError(f"Graph API error at '{step}': {r.status_code} {r.text}")

    def _validate_images(self, paths: list[Path]) -> None:
        from PIL import Image
        if len(paths) < 2:
            raise ValueError(f"Need ≥2 images for carousel, got {len(paths)}")
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Missing: {path}")
            img = Image.open(path)
            w, h = img.size
            if w != 1080 or h != 1080:
                raise ValueError(f"{path.name} must be 1080×1080, got {w}×{h}")
