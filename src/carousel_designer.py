"""Renders 1080x1080 Instagram carousel slides — dark cyberpunk tech aesthetic."""

import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import (
    BG_DARK, BG_LIGHT, CYAN, PURPLE, WHITE, GRAY,
    SLIDE_W, SLIDE_H, MARGIN, OUTPUT_DIR,
    FONT_HOOK_TITLE, FONT_HOOK_SUB, FONT_CONTENT_H, FONT_CONTENT_B,
    FONT_CTA_TITLE, FONT_WATERMARK, FONT_BG_NUM, FONT_SLIDE_NUM,
)
from src.content_generator import CarouselContent, SlideContent

log = logging.getLogger(__name__)
FONT_DIR = Path("assets/fonts")

# Extra design tokens
ACCENT2   = (189,  52, 254)   # hot purple #bd34fe
GOLD      = (255, 196,  57)   # #ffc439
DARK_CARD = (255, 255, 255, 14)


class CarouselDesigner:
    def __init__(self, handle: str = "@devvoxx"):
        self.handle = handle
        self.out_dir = Path(OUTPUT_DIR)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.fonts = self._load_fonts()

    # ── Public ─────────────────────────────────────────────────────────────────

    def render_carousel(self, content: CarouselContent,
                         logo: Image.Image | None = None) -> list[Path]:
        paths = []
        total = len(content.slides)
        # Extract short topic tag (e.g. "PYTHON") from topic string
        tag = _topic_tag(content.topic)
        for slide in content.slides:
            img = self.render_slide(slide, total, tag, logo)
            path = self.out_dir / f"slide_{slide.slide_num:02d}.jpg"
            img.convert("RGB").save(path, "JPEG", quality=96)
            log.info(f"Saved {path.name}")
            paths.append(path)
        return paths

    def render_slide(self, slide: SlideContent, total: int = 7,
                      tag: str = "", logo: Image.Image | None = None) -> Image.Image:
        base = self._make_base()

        if slide.slide_type == "hook":
            base = self._render_hook(base, slide, logo)
        elif slide.slide_type == "cta":
            base = self._render_cta(base, slide)
        else:
            base = self._render_content(base, slide)

        base = self._add_topic_tag(base, tag)
        base = self._add_progress_bar(base, slide.slide_num, total)
        base = self._add_slide_badge(base, slide.slide_num, total)
        base = self._add_watermark(base)
        return base

    # ── Base layers ────────────────────────────────────────────────────────────

    def _make_base(self) -> Image.Image:
        w, h = SLIDE_W, SLIDE_H
        # Diagonal dark gradient
        xs = np.linspace(0, 1, w)
        ys = np.linspace(0, 1, h)
        xg, yg = np.meshgrid(xs, ys)
        t = (xg * 0.4 + yg * 0.6)
        r = (BG_DARK[0] + t * (BG_LIGHT[0] - BG_DARK[0])).astype(np.uint8)
        g = (BG_DARK[1] + t * (BG_LIGHT[1] - BG_DARK[1])).astype(np.uint8)
        b = (BG_DARK[2] + t * (BG_LIGHT[2] - BG_DARK[2])).astype(np.uint8)
        base = Image.fromarray(np.stack([r, g, b], axis=2), "RGB").convert("RGBA")

        # Dot grid
        dots = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dots)
        for x in range(0, w, 44):
            for y in range(0, h, 44):
                dd.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(255, 255, 255, 16))
        base = Image.alpha_composite(base, dots)

        # Diagonal lines
        lines = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lines)
        for off in range(-h, w + h, 100):
            ld.line([(off, 0), (off + h, h)], fill=(*PURPLE, 14), width=1)
        base = Image.alpha_composite(base, lines)

        # Glow orbs
        orbs = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(orbs)
        od.ellipse([-160, -160, 560, 560], fill=(*CYAN, 20))
        od.ellipse([660, 620, 1340, 1300], fill=(*ACCENT2, 16))
        base = Image.alpha_composite(base, orbs.filter(ImageFilter.GaussianBlur(120)))

        return base

    # ── Slide renderers ────────────────────────────────────────────────────────

    def _render_hook(self, base: Image.Image, slide: SlideContent,
                      logo: Image.Image | None) -> Image.Image:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        # Left accent bar (full height, gradient)
        for y in range(SLIDE_H):
            alpha = int(220 * (1 - abs(y - SLIDE_H / 2) / (SLIDE_H / 2)) ** 0.5)
            draw.point((0, y), fill=(*CYAN, alpha))
            draw.point((1, y), fill=(*CYAN, alpha // 3))

        # Top cyan border
        draw.rectangle([0, 0, SLIDE_W, 5], fill=(*CYAN, 200))

        # Logo or emoji — top center
        logo_bottom = 260
        if logo:
            from src.image_fetcher import make_logo_glow
            logo_w = 180
            logo_h = int(logo.size[1] * logo_w / logo.size[0])
            resized = logo.resize((logo_w, logo_h), Image.LANCZOS)
            glowing = make_logo_glow(resized, CYAN)
            paste_x = (SLIDE_W - glowing.width) // 2
            paste_y = 80
            layer.paste(glowing, (paste_x, paste_y), glowing)
            logo_bottom = paste_y + glowing.height + 10
        elif slide.emoji_icon:
            draw.text((SLIDE_W // 2, 110), slide.emoji_icon,
                       font=self.fonts["emoji_xl"], fill=WHITE, anchor="mt")
            logo_bottom = 230

        # Cyan rule
        rule_y = logo_bottom + 10
        _draw_glowing_line(layer, MARGIN + 60, rule_y, SLIDE_W - MARGIN - 60,
                            rule_y, CYAN, width=3, blur=6)

        # Headline
        hl_y = rule_y + 28
        hl_y = self._highlighted_text_center(
            layer, slide.headline, slide.accent_word,
            hl_y, self.fonts["heading_xl"], WHITE, CYAN, line_spacing=14,
        )

        # Body / teaser
        draw = ImageDraw.Draw(layer)
        self._text_center_wrap(draw, slide.body, hl_y + 22,
                                self.fonts["body_lg"], GRAY,
                                SLIDE_W - MARGIN * 3, line_spacing=12)

        # "Swipe →" pill at bottom
        pill_y = 950
        pill_w, pill_h = 200, 44
        pill_x = (SLIDE_W - pill_w) // 2
        draw.rounded_rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                                radius=22, fill=(*CYAN, 28), outline=(*CYAN, 120), width=2)
        draw.text((SLIDE_W // 2, pill_y + pill_h // 2), "swipe →",
                   font=self.fonts["badge"], fill=(*CYAN, 220), anchor="mm")

        return Image.alpha_composite(base, layer)

    def _render_content(self, base: Image.Image, slide: SlideContent) -> Image.Image:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        content_x = MARGIN + 40
        content_w = SLIDE_W - content_x - MARGIN

        # Faint big slide number watermark (top-left bg)
        num_str = f"0{slide.slide_num - 1}"
        bg_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(bg_layer)
        bd.text((MARGIN - 20, 100), num_str,
                 font=self.fonts["bg_num"], fill=(*CYAN, 15))
        layer = Image.alpha_composite(layer, bg_layer)
        draw = ImageDraw.Draw(layer)

        # Vertical cyan glow line (left edge accent)
        _draw_glowing_line(layer, MARGIN, 170, MARGIN, 880,
                            CYAN, width=3, blur=6, vertical=True)

        # Headline with accent
        hl_y = 185
        hl_y = self._highlighted_text_left(
            layer, slide.headline, slide.accent_word,
            (content_x, hl_y), self.fonts["heading_lg"],
            WHITE, CYAN, max_width=content_w, line_spacing=10,
        )

        # Divider
        draw = ImageDraw.Draw(layer)
        div_y = hl_y + 18
        draw.rectangle([content_x, div_y, content_x + 400, div_y + 2],
                        fill=(*CYAN, 160))

        # Emoji
        emoji_y = div_y + 48
        if slide.emoji_icon:
            draw.text((content_x, emoji_y), slide.emoji_icon,
                       font=self.fonts["emoji_md"], fill=WHITE)
            body_y = emoji_y + 80
        else:
            body_y = div_y + 50

        # Body card (subtle background)
        body_lines = self._wrap(slide.body, self.fonts["body"], content_w)
        lh = self.fonts["body"].getbbox("Ag")[3] + 18
        card_h = len(body_lines) * lh + 30
        draw.rounded_rectangle(
            [content_x - 12, body_y - 14,
             SLIDE_W - MARGIN + 12, body_y + card_h],
            radius=14, fill=(255, 255, 255, 10),
        )

        # Body text
        self._text_left_wrap(draw, slide.body, (content_x, body_y),
                              self.fonts["body"], GRAY, content_w, line_spacing=18)

        return Image.alpha_composite(base, layer)

    def _render_cta(self, base: Image.Image, slide: SlideContent) -> Image.Image:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)

        # Top + bottom neon borders
        for thick, color in [(6, CYAN), (3, ACCENT2)]:
            draw.rectangle([0, 0, SLIDE_W, thick], fill=(*color, 230))
            draw.rectangle([0, SLIDE_H - thick, SLIDE_W, SLIDE_H], fill=(*color, 230))

        # Glow orb center
        orb = Image.new("RGBA", base.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(orb)
        od.ellipse([240, 280, 840, 800], fill=(*CYAN, 18))
        layer = Image.alpha_composite(layer, orb.filter(ImageFilter.GaussianBlur(90)))
        draw = ImageDraw.Draw(layer)

        # Card
        draw.rounded_rectangle([70, 220, SLIDE_W - 70, 870],
                                radius=28, fill=DARK_CARD,
                                outline=(*CYAN, 55), width=1)

        # Emoji
        if slide.emoji_icon:
            draw.text((SLIDE_W // 2, 260), slide.emoji_icon,
                       font=self.fonts["emoji_xl"], fill=WHITE, anchor="mt")

        # CTA headline — shrink font to fit within card width
        cta_y = 380
        cta_font = self.fonts["cta_title"]
        max_cta_w = SLIDE_W - 180
        # Try smaller sizes until it fits
        for size in [68, 56, 48, 40, 34]:
            p = FONT_DIR / "Montserrat-ExtraBold.ttf"
            f = ImageFont.truetype(str(p), size) if p.exists() else self.fonts["cta_title"]
            lines = self._wrap(slide.headline, f, max_cta_w)
            if len(lines) <= 2:
                cta_font = f
                break
        # Draw each wrapped line
        for line in self._wrap(slide.headline, cta_font, max_cta_w):
            cta_y = self._glowing_text_center(
                layer, line, cta_y, cta_font, WHITE, CYAN, blur=14,
            )
            cta_y -= 8  # tighten line gap

        draw = ImageDraw.Draw(layer)

        # Cyan divider
        draw.rectangle([SLIDE_W // 2 - 220, cta_y + 14,
                         SLIDE_W // 2 + 220, cta_y + 16],
                        fill=(*CYAN, 160))

        # Body text
        self._text_center_wrap(draw, slide.body, cta_y + 38,
                                self.fonts["body_lg"], GRAY,
                                SLIDE_W - 220, line_spacing=14)

        # Handle pill
        handle_y = 750
        hw = int(self.fonts["heading_md"].getlength(self.handle)) + 48
        hh = 56
        hx = (SLIDE_W - hw) // 2
        draw.rounded_rectangle([hx, handle_y, hx + hw, handle_y + hh],
                                radius=28, fill=(*CYAN, 30),
                                outline=(*CYAN, 200), width=2)
        draw.text((SLIDE_W // 2, handle_y + hh // 2),
                   self.handle, font=self.fonts["heading_md"],
                   fill=CYAN, anchor="mm")

        return Image.alpha_composite(base, layer)

    # ── Chrome overlays ────────────────────────────────────────────────────────

    def _add_topic_tag(self, base: Image.Image, tag: str) -> Image.Image:
        if not tag:
            return base
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        font = self.fonts["tag"]
        tw = int(font.getlength(tag))
        pad_x, pad_y = 16, 8
        tx, ty = MARGIN, SLIDE_H - 52
        draw.rounded_rectangle(
            [tx, ty, tx + tw + pad_x * 2, ty + 34 + pad_y],
            radius=8, fill=(*PURPLE, 40), outline=(*PURPLE, 160), width=1,
        )
        draw.text((tx + pad_x, ty + pad_y // 2 + 2), tag,
                   font=font, fill=(*PURPLE, 240))
        return Image.alpha_composite(base, layer)

    def _add_progress_bar(self, base: Image.Image, num: int, total: int) -> Image.Image:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        bar_y = SLIDE_H - 8
        bar_h = 4
        # Track
        draw.rectangle([0, bar_y, SLIDE_W, bar_y + bar_h],
                        fill=(*WHITE, 15))
        # Fill
        filled = int(SLIDE_W * num / total)
        for x in range(filled):
            t = x / SLIDE_W
            r = int(CYAN[0] * (1 - t) + ACCENT2[0] * t)
            g = int(CYAN[1] * (1 - t) + ACCENT2[1] * t)
            b = int(CYAN[2] * (1 - t) + ACCENT2[2] * t)
            draw.line([(x, bar_y), (x, bar_y + bar_h)], fill=(r, g, b, 220))
        return Image.alpha_composite(base, layer)

    def _add_slide_badge(self, base: Image.Image, num: int, total: int) -> Image.Image:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        bx1, by1, bx2, by2 = SLIDE_W - 148, 34, SLIDE_W - 34, 78
        draw.rounded_rectangle([bx1, by1, bx2, by2],
                                radius=22, fill=(*CYAN, 25),
                                outline=(*CYAN, 190), width=2)
        draw.text(((bx1 + bx2) // 2, (by1 + by2) // 2),
                   f"{num}/{total}", font=self.fonts["badge"],
                   fill=WHITE, anchor="mm")
        return Image.alpha_composite(base, layer)

    def _add_watermark(self, base: Image.Image) -> Image.Image:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        draw.text((SLIDE_W - MARGIN, SLIDE_H - 52),
                   self.handle, font=self.fonts["watermark"],
                   fill=(*GRAY, 120), anchor="rm")
        return Image.alpha_composite(base, layer)

    # ── Text helpers ───────────────────────────────────────────────────────────

    def _highlighted_text_center(self, base, text, accent, y, font,
                                  main_color, accent_color,
                                  line_spacing=10) -> int:
        lines = self._wrap(text, font, SLIDE_W - MARGIN * 3)
        accent_words = set(accent.lower().split())
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        cur_y = y
        for line in lines:
            lw = int(font.getlength(line))
            cx = (SLIDE_W - lw) // 2
            for word in line.split():
                clean = word.strip(".,!?:;").lower()
                is_accent = clean in accent_words or any(aw in clean for aw in accent_words)
                color = accent_color if is_accent else main_color
                ww = int(font.getlength(word + " "))
                if is_accent:
                    gl = Image.new("RGBA", base.size, (0, 0, 0, 0))
                    gd = ImageDraw.Draw(gl)
                    gd.text((cx, cur_y), word, font=font, fill=(*accent_color, 110))
                    gl = gl.filter(ImageFilter.GaussianBlur(9))
                    layer = Image.alpha_composite(layer, gl)
                    draw = ImageDraw.Draw(layer)
                draw.text((cx, cur_y), word, font=font, fill=color)
                cx += ww
            lh = font.getbbox(line)[3] + line_spacing
            cur_y += lh
        base_result = Image.alpha_composite(base, layer)
        base.paste(base_result)
        return cur_y

    def _highlighted_text_left(self, base, text, accent, pos, font,
                                main_color, accent_color,
                                max_width, line_spacing=10) -> int:
        lines = self._wrap(text, font, max_width)
        accent_words = set(accent.lower().split())
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        x0, cur_y = pos
        for line in lines:
            cx = x0
            for word in line.split():
                clean = word.strip(".,!?:;").lower()
                is_accent = clean in accent_words or any(aw in clean for aw in accent_words)
                color = accent_color if is_accent else main_color
                ww = int(font.getlength(word + " "))
                if is_accent:
                    gl = Image.new("RGBA", base.size, (0, 0, 0, 0))
                    gd = ImageDraw.Draw(gl)
                    gd.text((cx, cur_y), word, font=font, fill=(*accent_color, 100))
                    gl = gl.filter(ImageFilter.GaussianBlur(7))
                    layer = Image.alpha_composite(layer, gl)
                    draw = ImageDraw.Draw(layer)
                draw.text((cx, cur_y), word, font=font, fill=color)
                cx += ww
            cur_y += font.getbbox(line)[3] + line_spacing
        base_result = Image.alpha_composite(base, layer)
        base.paste(base_result)
        return cur_y

    def _glowing_text_center(self, base, text, y, font,
                              color, glow_color, blur=12) -> int:
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        # Glow pass
        gl = Image.new("RGBA", base.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)
        gd.text((SLIDE_W // 2, y), text, font=font,
                 fill=(*glow_color, 140), anchor="mt")
        gl = gl.filter(ImageFilter.GaussianBlur(blur))
        layer = Image.alpha_composite(layer, gl)
        draw = ImageDraw.Draw(layer)
        draw.text((SLIDE_W // 2, y), text, font=font, fill=color, anchor="mt")
        base_result = Image.alpha_composite(base, layer)
        base.paste(base_result)
        return y + font.getbbox(text)[3] + 16

    def _text_center_wrap(self, draw, text, y, font, color, max_w, line_spacing=10) -> int:
        for line in self._wrap(text, font, max_w):
            draw.text((SLIDE_W // 2, y), line, font=font, fill=color, anchor="mt")
            y += font.getbbox(line)[3] + line_spacing
        return y

    def _text_left_wrap(self, draw, text, pos, font, color, max_w, line_spacing=10) -> int:
        x, y = pos
        for line in self._wrap(text, font, max_w):
            draw.text((x, y), line, font=font, fill=color)
            y += font.getbbox(line)[3] + line_spacing
        return y

    def _wrap(self, text: str, font, max_px: int) -> list[str]:
        words = text.split()
        lines, cur = [], []
        for word in words:
            test = " ".join(cur + [word])
            if font.getlength(test) <= max_px:
                cur.append(word)
            else:
                if cur:
                    lines.append(" ".join(cur))
                cur = [word]
        if cur:
            lines.append(" ".join(cur))
        return lines or [text]

    # ── Font loading ───────────────────────────────────────────────────────────

    def _load_fonts(self) -> dict:
        def load(name: str, size: int):
            p = FONT_DIR / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
            log.warning(f"Font missing: {name}")
            return ImageFont.load_default()

        return {
            "heading_xl":  load("Montserrat-ExtraBold.ttf", FONT_HOOK_TITLE),
            "heading_lg":  load("Montserrat-Bold.ttf",      FONT_CONTENT_H),
            "heading_md":  load("Montserrat-Bold.ttf",      38),
            "cta_title":   load("Montserrat-ExtraBold.ttf", FONT_CTA_TITLE),
            "body":        load("Inter-Regular.ttf",         FONT_CONTENT_B),
            "body_lg":     load("Inter-Regular.ttf",         FONT_HOOK_SUB),
            "badge":       load("Inter-Regular.ttf",         FONT_SLIDE_NUM),
            "watermark":   load("Inter-Regular.ttf",         FONT_WATERMARK),
            "bg_num":      load("Montserrat-ExtraBold.ttf", FONT_BG_NUM),
            "tag":         load("Montserrat-Bold.ttf",       20),
            "emoji_xl":    load("NotoEmoji-Regular.ttf",     80),
            "emoji_md":    load("NotoEmoji-Regular.ttf",     52),
        }


# ── Module-level helpers ────────────────────────────────────────────────────────

def _topic_tag(topic: str) -> str:
    """Extract a short uppercased tag from the topic, e.g. 'PYTHON'."""
    stop = {"and", "or", "the", "a", "an", "for", "to", "in", "of",
            "with", "vs", "that", "you", "your", "why", "how", "what",
            "every", "must", "know", "no", "one", "teaches", "guide",
            "best", "practices", "tips", "tricks", "secrets"}
    words = [w for w in topic.split() if w.lower() not in stop and len(w) > 2]
    return words[0].upper() if words else ""


def _draw_glowing_line(canvas: Image.Image,
                        x1: int, y1: int, x2: int, y2: int,
                        color, width: int = 2, blur: int = 6,
                        vertical: bool = False) -> None:
    """Draw a line with a soft glow on the canvas (in-place alpha composite)."""
    gl = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(gl)
    gd.line([(x1, y1), (x2, y2)], fill=(*color, 80), width=width + 4)
    gl = gl.filter(ImageFilter.GaussianBlur(blur))
    # Sharp line on top
    sharp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sharp)
    sd.line([(x1, y1), (x2, y2)], fill=(*color, 220), width=width)
    combined = Image.alpha_composite(gl, sharp)
    result = Image.alpha_composite(canvas, combined)
    canvas.paste(result)
