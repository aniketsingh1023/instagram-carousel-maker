"""All constants and configuration for the carousel maker."""

from dataclasses import dataclass

# ── Canvas ─────────────────────────────────────────────────────────────────────
SLIDE_W, SLIDE_H = 1080, 1080

# ── Colors (R, G, B) ───────────────────────────────────────────────────────────
BG_DARK   = (8,   8,  16)
BG_LIGHT  = (13,  13,  26)
CYAN      = (0,  212, 255)
PURPLE    = (124,  58, 237)
WHITE     = (255, 255, 255)
GRAY      = (160, 160, 190)
PINK      = (255,  72, 176)

# ── Typography sizes (px) ──────────────────────────────────────────────────────
FONT_HOOK_TITLE  = 72
FONT_HOOK_SUB    = 32
FONT_SLIDE_NUM   = 22
FONT_CONTENT_H   = 52
FONT_CONTENT_B   = 30
FONT_CTA_TITLE   = 68
FONT_CTA_SUB     = 30
FONT_WATERMARK   = 22
FONT_BG_NUM      = 120

# ── Layout ─────────────────────────────────────────────────────────────────────
MARGIN = 72

# ── Topic rotation pool ────────────────────────────────────────────────────────
TECH_TOPICS = [
    "Python tricks every developer must know",
    "JavaScript ES2024 hidden features",
    "AI prompting secrets for developers",
    "Docker and Kubernetes survival guide",
    "Git commands that save hours every week",
    "FastAPI vs Django: which to choose in 2025",
    "Linux terminal commands for power users",
    "SQL performance tricks no one teaches",
    "React 19: what changed and why it matters",
    "DevOps automation with GitHub Actions",
    "Machine learning without a GPU",
    "TypeScript patterns senior devs use daily",
    "REST API design best practices",
    "Redis use cases beyond simple caching",
    "Cloud costs: free tier survival guide",
    "Python data structures you underuse",
    "CSS tricks that will blow your mind",
    "VS Code shortcuts to 10x your productivity",
    "Async Python: async/await explained simply",
    "System design concepts every dev must know",
    "Clean code principles with Python examples",
    "Web security vulnerabilities and how to fix them",
    "Next.js 15 features that change everything",
    "Database indexing strategies explained simply",
    "Python decorators: a complete visual guide",
    "Kubernetes patterns for production apps",
    "GraphQL vs REST: the real difference",
    "Python list comprehensions: advanced tricks",
    "CI/CD pipeline best practices in 2025",
    "Open source AI models you can run locally",
]

# ── Scheduling (UTC cron) ─────────────────────────────────────────────────────
# Adjust to your timezone. Below = 8 AM and 7 PM IST
CRON_MORNING = "30 2 * * *"   # 08:00 IST = 02:30 UTC
CRON_EVENING = "30 13 * * *"  # 19:00 IST = 13:30 UTC

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_MODEL  = "gemini-2.0-flash"
MAX_RETRIES   = 4
BASE_DELAY    = 5  # seconds

# ── Instagram ─────────────────────────────────────────────────────────────────
SESSION_FILE  = "data/ig_session.json"
OUTPUT_DIR    = "data/slides"
DELAY_RANGE   = [3, 7]

# ── App config dataclass ──────────────────────────────────────────────────────
@dataclass
class Config:
    gemini_key:     str
    ig_username:    str
    ig_password:    str
    ig_handle:      str = "@devvoxx"
    insta_session:  str | None = None
    dry_run:        bool = False
    topic_override: str = ""
