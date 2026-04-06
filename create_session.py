"""
Run this ONCE locally to create your Instagram session.
It handles any email/SMS challenge interactively.

Usage:
    python create_session.py

Then copy the printed INSTA_SESSION value into GitHub Secrets.
"""

import base64
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired, TwoFactorRequired

load_dotenv()

SESSION_FILE = Path("data/ig_session.json")
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

username = os.getenv("INSTA_USERNAME") or input("Instagram username: ").strip()
password = os.getenv("INSTA_PASSWORD") or input("Instagram password: ").strip()

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

print(f"\nLogging in as {username}...")

try:
    cl.login(username, password)
    print("Login successful!")

except ChallengeRequired:
    print("\nInstagram sent a challenge (email/SMS code).")
    cl.challenge_resolve(cl.last_json)
    code = input("Enter the 6-digit verification code: ").strip()
    cl.challenge_send_security_code(code)
    print("Challenge passed!")

except TwoFactorRequired:
    print("\n2FA required.")
    code = input("Enter your 2FA code: ").strip()
    two_factor_identifier = cl.last_json.get("two_factor_info", {}).get("two_factor_identifier")
    cl.two_factor_login(
        username, code,
        two_factor_identifier=two_factor_identifier,
        verification_method="1"
    )
    print("2FA passed!")

# Save session
cl.dump_settings(str(SESSION_FILE))
session_b64 = base64.b64encode(SESSION_FILE.read_bytes()).decode()

print("\n" + "="*60)
print("SUCCESS! Add this as GitHub Secret named INSTA_SESSION:")
print("="*60)
print(session_b64)
print("="*60)
print("\nGo to: https://github.com/aniketsingh1023/instagram-carousel-maker/settings/secrets/actions")
print("Click 'New repository secret', name it INSTA_SESSION, paste the value above.")
