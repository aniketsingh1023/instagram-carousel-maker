"""Generates viral tech carousel content using Google Gemini API (free tier)."""

import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import google.generativeai as genai

from config import TECH_TOPICS, GEMINI_MODEL, MAX_RETRIES, BASE_DELAY

log = logging.getLogger(__name__)

TOPICS_FILE = Path("data/posted_topics.json")


@dataclass
class SlideContent:
    slide_num: int
    slide_type: str          # "hook" | "content" | "cta"
    headline: str
    body: str
    accent_word: str         # 1-3 words to highlight in cyan
    emoji_icon: str


@dataclass
class CarouselContent:
    topic: str
    caption: str
    hashtags: list[str]
    slides: list[SlideContent] = field(default_factory=list)


class ContentGenerator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def pick_topic(self) -> str:
        override = os.getenv("TOPIC_OVERRIDE", "").strip()
        if override:
            log.info(f"Using topic override: {override}")
            return override

        recently_used = self._load_recent_topics()
        available = [t for t in TECH_TOPICS if t not in recently_used]
        if not available:
            # Cycle complete - reset
            available = TECH_TOPICS
            self._save_recent_topics([])

        topic = random.choice(available)
        log.info(f"Selected topic: {topic}")
        return topic

    def generate_carousel(self, topic: str) -> CarouselContent:
        prompt = self._build_prompt(topic)
        raw = self._call_gemini(prompt)
        content = self._parse_response(raw, topic)
        log.info(f"Generated {len(content.slides)} slides for: {topic}")
        return content

    def mark_topic_used(self, topic: str) -> None:
        recent = self._load_recent_topics()
        recent.append(topic)
        # Keep last 14 to avoid repeats for ~1 week (2 posts/day)
        self._save_recent_topics(recent[-14:])

    # ── Private ────────────────────────────────────────────────────────────────

    def _build_prompt(self, topic: str) -> str:
        return f"""You are a viral tech content creator for Instagram with 500K followers.
Generate a 7-slide carousel about: "{topic}"

TARGET AUDIENCE: Developers and CS students who scroll fast. Stop them cold with the hook.

SLIDE STRUCTURE:
- Slide 1 (hook): A shocking, bold statement + 1-line teaser. Make them NEED to swipe.
- Slides 2-6 (content): Each = 1 specific actionable tip or insight. Real examples, no fluff.
- Slide 7 (cta): Tell them to comment a KEYWORD to receive all slides in DM. The keyword = the main topic in ALL CAPS (e.g. comment "PYTHON"). Also ask them to follow. Make the headline use the word "Comment" and the keyword.

RULES:
- headline: MAX 8 words, punch hard, make it urgent or surprising
- body: MAX 40 words, use real code concepts, variable names, commands, numbers
- accent_word: 1-3 words FROM the headline that should glow in neon cyan
- emoji_icon: one relevant emoji per slide
- caption: engaging 2-3 line post caption + 5 relevant hashtags at the end

Respond ONLY with valid JSON (no markdown fences, no explanation):
{{
  "topic": "{topic}",
  "caption": "your 2-3 line engaging caption here\\n\\n#HashTag1 #HashTag2 #HashTag3 #HashTag4 #HashTag5",
  "hashtags": ["#HashTag1", "#HashTag2", "#HashTag3", "#HashTag4", "#HashTag5"],
  "slides": [
    {{
      "slide_num": 1,
      "slide_type": "hook",
      "headline": "Bold hook headline here",
      "body": "The teaser that makes them swipe right now",
      "accent_word": "hook headline",
      "emoji_icon": "🔥"
    }},
    {{
      "slide_num": 2,
      "slide_type": "content",
      "headline": "Tip number one title",
      "body": "Concrete explanation with real example. No vague advice.",
      "accent_word": "one title",
      "emoji_icon": "⚡"
    }},
    ... continue for slides 3, 4, 5, 6 ...
    {{
      "slide_num": 7,
      "slide_type": "cta",
      "headline": "Comment PYTHON to get this in DM",
      "body": "I will send you all 7 slides in your DM for free. Follow for daily dev secrets.",
      "accent_word": "PYTHON",
      "emoji_icon": "🚀"
    }}
  ]
}}"""

    def _call_gemini(self, prompt: str) -> str:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                log.info(f"Calling Gemini (attempt {attempt}/{MAX_RETRIES})...")
                response = self.model.generate_content(prompt)
                text = response.text.strip()
                if not text:
                    raise ValueError("Empty response from Gemini")
                return text
            except Exception as e:
                if attempt == MAX_RETRIES:
                    raise
                delay = BASE_DELAY * (2 ** (attempt - 1))
                log.warning(f"Gemini attempt {attempt} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)

    def _parse_response(self, raw: str, topic: str) -> CarouselContent:
        # Strip markdown fences if present
        text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Try extracting JSON via regex
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ValueError(f"No valid JSON in Gemini response: {text[:300]}")
            data = json.loads(match.group())

        slides_raw = data.get("slides", [])
        if len(slides_raw) < 7:
            raise ValueError(f"Expected 7 slides, got {len(slides_raw)}")

        slides = [
            SlideContent(
                slide_num=s["slide_num"],
                slide_type=s.get("slide_type", "content"),
                headline=s.get("headline", ""),
                body=s.get("body", ""),
                accent_word=s.get("accent_word", ""),
                emoji_icon=s.get("emoji_icon", ""),
            )
            for s in slides_raw[:7]
        ]

        return CarouselContent(
            topic=data.get("topic", topic),
            caption=data.get("caption", topic),
            hashtags=data.get("hashtags", []),
            slides=slides,
        )

    def _load_recent_topics(self) -> list[str]:
        if not TOPICS_FILE.exists():
            return []
        try:
            return json.loads(TOPICS_FILE.read_text())
        except Exception:
            return []

    def _save_recent_topics(self, topics: list[str]) -> None:
        TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOPICS_FILE.write_text(json.dumps(topics, indent=2))
