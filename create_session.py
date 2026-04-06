"""
Run this ONCE locally to log into Instagram in a real browser and save the session.
Opens a visible Chrome window so you can log in normally (including any 2FA/challenge).

Usage:
    python create_session.py

After login, copy the printed INSTA_SESSION value to your GitHub Secret.
"""

import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

STORAGE_FILE = Path("data/ig_browser_state.json")
STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Opening Instagram in Chrome — log in normally.")
print("Close the browser OR press Enter here when done.")
print("=" * 60)
print()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=50)
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()
    page.goto("https://www.instagram.com/accounts/login/")

    print("Waiting for you to log in... (press Enter in this terminal when done)")
    input()

    # Check if logged in
    page.goto("https://www.instagram.com/")
    page.wait_for_load_state("networkidle")

    if "login" in page.url:
        print("Not logged in yet! Please log in first, then press Enter.")
        input()

    # Save browser state (cookies + localStorage)
    context.storage_state(path=str(STORAGE_FILE))
    browser.close()

# Encode as base64
state_b64 = base64.b64encode(STORAGE_FILE.read_bytes()).decode()

print()
print("=" * 60)
print("SUCCESS! Add this as GitHub Secret named INSTA_SESSION:")
print("=" * 60)
print(state_b64)
print("=" * 60)
print()
print("→ https://github.com/aniketsingh1023/instagram-carousel-maker/settings/secrets/actions")
print("→ Find INSTA_SESSION → Edit → paste the value above → Save")
