"""
Run this ONCE locally to create your Instagram session using your browser session ID.
This avoids the API login (which gets IP-blocked) entirely.

HOW TO GET YOUR SESSION ID:
1. Open instagram.com in Chrome/Safari and log in normally
2. Open DevTools (F12 or right-click → Inspect)
3. Go to Application tab → Cookies → https://www.instagram.com
4. Find the cookie named 'sessionid' and copy its value
5. Paste it when prompted below

Usage:
    python create_session.py
"""

import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from instagrapi import Client

load_dotenv()

SESSION_FILE = Path("data/ig_session.json")
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Instagram Session Creator")
print("=" * 60)
print()
print("To get your session ID:")
print("  1. Open instagram.com in Chrome/Safari, log in")
print("  2. Press F12 → Application tab → Cookies → instagram.com")
print("  3. Find 'sessionid' cookie and copy its value")
print()

session_id = input("Paste your sessionid cookie value here: ").strip()
if not session_id:
    print("Error: sessionid cannot be empty")
    exit(1)

print("\nCreating session from browser cookie...")

cl = Client()
cl.delay_range = [3, 7]
cl.set_device({
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

try:
    cl.login_by_sessionid(session_id)
    user = cl.account_info()
    print(f"Logged in as: @{user.username} ✓")
except Exception as e:
    print(f"Error: {e}")
    print("\nMake sure you copied the full sessionid value from the cookie.")
    exit(1)

# Save session
cl.dump_settings(str(SESSION_FILE))
session_b64 = base64.b64encode(SESSION_FILE.read_bytes()).decode()

print()
print("=" * 60)
print("SUCCESS! Add this as GitHub Secret named INSTA_SESSION:")
print("=" * 60)
print(session_b64)
print("=" * 60)
print()
print("→ Go to: https://github.com/aniketsingh1023/instagram-carousel-maker/settings/secrets/actions")
print("→ Click 'New repository secret'")
print("→ Name: INSTA_SESSION")
print("→ Value: paste the long string above")
