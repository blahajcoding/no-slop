#!/usr/bin/env python3
"""Static slop scanner for the no-slop skill.

Deterministic checks against built HTML/CSS/JS. Emits findings mapped to the
no-slop rules, a verdict, and an exit code.

    python3 scan_slop.py <dir> [--per-file] [--text] [--quiet]

exit 0 = clean, 1 = review, 2 = slop.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------- config

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "vendor", "bower_components",
    ".next", "out", "coverage", ".cache", ".vercel", ".turbo", ".parcel-cache",
    "__pycache__", ".venv", "venv", ".svelte-kit", "storybook-static",
    ".yarn", ".pnpm-store", ".nuxt", ".output", "public/build", "static/vendor",
}
SCAN_EXT = {".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".jsx", ".tsx",
            ".ts", ".vue", ".svelte", ".astro"}

# no-slop Rule 1 pool. Inter is handled separately (leniency clause).
FONT_POOL = ["space grotesk", "geist", "instrument serif", "dm serif display",
             "playfair display", "poppins", "montserrat", "roboto", "archivo",
             "spline sans mono", "ibm plex", "karla", "besley", "young serif"]

PURPLE_HEX = re.compile(
    r"#(7c3aed|8b5cf6|a855f7|9333ea|6d28d9|7c5cff|8b7cf6|a78bfa|c084fc"
    r"|6366f1|818cf8|6f5cf6|7b61ff|9d7bff|5b21b6|4c1d95|7e22ce|a78bfa"
    r"|8b5cf6|4f46e5|4338ca)", re.I)
PURPLE_TW = re.compile(
    r"\b(?:bg|text|from|to|via|border|ring|fill|stroke)-"
    r"(?:purple|violet|indigo|fuchsia)-(?:300|400|500|600|700)\b")
GRADIENT = re.compile(r"\b(?:linear|radial|conic)-gradient\s*\(", re.I)
GRADIENT_TW = re.compile(r"\bbg-gradient-to-[a-z]{2}\b")
GLASS = re.compile(r"backdrop-filter\s*:\s*(?:blur|saturate)", re.I)
EMOJI = re.compile("[\U0001F000-\U0001F2FF\U0001F300-\U0001FAFF]")
CAPS_LABEL = re.compile(r"text-transform\s*:\s*uppercase", re.I)
LEFT_BORDER = re.compile(r"border-left(?:-color)?\s*:\s*[^;}]*#[0-9a-f]{3,8}", re.I)
TOP_ACCENT = re.compile(r"border-top\s*:\s*[234]px\s+solid\s+#[0-9a-f]{3,8}", re.I)
HOVER_LIFT = re.compile(
    r":hover[^{}]*\{[^{}]*(?:translateY\(|translate3d\(|scale\(1\.[0-9]|rotate\()",
    re.I)
TAGLINES = ["transform your", "launch faster", "build your dreams",
            "create without limits", "where ideas become", "the future of",
            "unlock your potential", "supercharge", "take it to the next level",
            "revolutionize", "game-changer", "blazing fast", "empower"]
SHADCN_TOKENS = re.compile(
    r"--(?:background|foreground|primary|muted|card|popover|border|ring)\s*:", re.I)
STAT_ROW = re.compile(r"(?:\b\d{1,3}k\+|\b99\.\d%|\b24/7\b|1M\+)", re.I)

FONT_DECL = re.compile(r"font-family\s*:\s*([^;}]+)", re.I)
FONT_VAR = re.compile(r"--font-[a-z0-9-]+\s*:\s*([^;}]+)", re.I)
GOOGLE_FONT = re.compile(r"fonts\.googleapis\.com/css2?\?[^\"')\s]*?family=([^\"'&:)]+)", re.I)
TW_ARBITRARY_FONT = re.compile(r"font-\[['\"]?([A-Za-z0-9][A-Za-z0-9 _-]*)['\"]?\]")

RADIUS_DECL = re.compile(r"border-radius\s*:\s*([^;}]+)", re.I)
RADIUS_TOKEN = re.compile(r"^([\d.]+)(px|rem|em|%)$", re.I)
TW_ROUNDED = re.compile(r"\brounded(?:-[a-z0-9]+)?\b|\brounded-\[[^\]]+\]")

H1_BLOCK = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.I | re.S)
HERO_EMPHASIS = re.compile(r"<(?:em|i|b|strong)\b|font-style\s*:\s*italic|"
                           r"class=\"[^\"]*\bitalic\b", re.I)
OL_BLOCK = re.compile(r"<ol\b([^>]*)>(.*?)</ol>", re.I | re.S)
OL_EXEMPT = re.compile(r"breadcrumb|pagination|pager|toc|table-of-contents|nav\b", re.I)
STEP_PROSE = re.compile(r"\bstep (?:one|two|three|1|2|3)\b", re.I)

COPYRIGHT = re.compile(r"(?:©|&copy;|copyright\b)[^\n<]{0,60}", re.I)
YEAR = re.compile(r"\b(19|20)\d{2}\b")

SHADOW_DECL = re.compile(r"(box-shadow|filter)\s*:\s*([^;}]+)", re.I)
COLOR_FUNC = re.compile(r"(rgba?|hsla?|oklch|oklab|color-mix)\s*\(([^()]*(?:\([^()]*\))?[^()]*)\)", re.I)
HEX_COLOR = re.compile(r"#[0-9a-f]{3,8}\b", re.I)

OPACITY_ZERO = re.compile(r"opacity\s*:\s*0(?:\.0+)?\s*[;}]", re.I)
JS_REVEAL = re.compile(r"IntersectionObserver|classList\.(?:add|toggle)|"
                       r"requestAnimationFrame|\.observe\(", re.I)
ANIMATION = re.compile(r"(?:^|[;{\s])(animation|transition)(?:-[\w-]+)?\s*:", re.I)
REDUCED_MOTION = re.compile(r"prefers-reduced-motion", re.I)
OUTLINE_KILL = re.compile(r"outline\s*:\s*(?:none|0(?:px)?)\s*[;}]", re.I)
FOCUS_STYLE = re.compile(r":focus(?:-visible|-within)?", re.I)

FAVICON = re.compile(r"<link\b[^>]*rel=[\"'][^\"']*\bicon\b", re.I)
OG_IMAGE = re.compile(r"property=[\"']og:image[\"']", re.I)
OG_TITLE = re.compile(r"property=[\"']og:title[\"']", re.I)
META_DESC = re.compile(r"<meta\b[^>]*name=[\"']description[\"']", re.I)
TITLE_TAG = re.compile(r"<title[^>]*>([^<]*)</title>", re.I)
TITLE_GENERIC = re.compile(r"^\s*(home|untitled|index|page|new page|document)\s*$", re.I)

SPACING_DECL = re.compile(
    r"\b(?:margin|padding|gap|row-gap|column-gap)(?:-(?:top|right|bottom|left|inline|block))?"
    r"\s*:\s*([^;}]+)", re.I)
SPACING_TOKEN = re.compile(r"^([\d.]+)px$")

# name -> (doc rule, severity). "tell" counts toward the verdict, "review" does not.
CHECKS = {
    "default_fonts":            ("Rule 1", "tell"),
    "inter_sole_identity":      ("Rule 1", "review"),
    "hero_emphasis":            ("Rule 1", "tell"),
    "mono_body":                ("Rule 1", "tell"),
    "vibecode_purple":          ("Rule 2", "tell"),
    "purple_tint":              ("Rule 2", "review"),
    "gradient_count":           ("Rule 2/4", "review"),
    "colored_glows":            ("Rule 2", "tell"),
    "glassmorphism":            ("Rule 4", "review"),
    "contrast_failures":        ("Rule 2", "tell"),
    "uppercase_labels":         ("Rule 3", "tell"),
    "left_border_cards":        ("Rule 2", "tell"),
    "top_accent_borders":       ("Rule 2", "review"),
    "nested_cards":             ("Rule 3", "tell"),
    "numbered_steps":           ("Rule 3", "tell"),
    "stat_banner_hits":         ("Rule 3", "review"),
    "distinct_radius_values":   ("Rule 4", "tell"),
    "off_scale_spacing":        ("Rule 4", "review"),
    "hidden_without_js":        ("Rule 5", "tell"),
    "hover_lift_effects":       ("Rule 5", "tell"),
    "missing_reduced_motion":   ("Rule 5", "tell"),
    "outline_removed":          ("Rule 7", "tell"),
    "emoji_count":              ("Rule 6", "review"),
    "generic_taglines":         ("Rule 6", "tell"),
    "stale_copyright":          ("Rule 6", "tell"),
    "missing_og":               ("Rule 7", "tell"),
    "missing_favicon":          ("Rule 7", "tell"),
    "missing_meta_desc":        ("Rule 7", "review"),
    "generic_title":            ("Rule 7", "tell"),
}
TELL_THRESHOLD = 4  # no-slop: 4+ triggered patterns reads as machine-made


# ---------------------------------------------------------------- helpers

def hex_to_rgb(h: str):
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    if len(h) < 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _nums(s: str):
    return [float(x) for x in re.findall(r"[-+]?[\d.]+", s)[:3]]


def color_to_rgb(spec: str):
    """Best-effort parse of a CSS color. Returns (r,g,b) 0..255 or None."""
    spec = spec.strip().lower()
    if spec.startswith("#"):
        return hex_to_rgb(spec)
    m = re.match(r"rgba?\(([^)]+)\)", spec)
    if m:
        n = _nums(m.group(1))
        if len(n) >= 3:
            return tuple(int(max(0, min(255, v))) for v in n[:3])
        return None
    m = re.match(r"hsla?\(([^)]+)\)", spec)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        try:
            h = float(parts[0].rstrip("deg")) % 360
            s = float(parts[1].rstrip("%")) / 100
            l = float(parts[2].rstrip("%")) / 100
        except (ValueError, IndexError):
            return None
        return hsl_to_rgb(h, s, l)
    m = re.match(r"oklch\(([^)]+)\)", spec)
    if m:
        parts = re.split(r"[,\s/]+", m.group(1).strip())
        try:
            l = float(parts[0].rstrip("%"))
            if l > 1:
                l /= 100
            c = float(parts[1])
            h = float(parts[2].rstrip("deg")) if len(parts) > 2 else 0.0
        except (ValueError, IndexError):
            return None
        return oklch_to_rgb(l, c, h)
    if spec in ("white", "#fff"):
        return (255, 255, 255)
    if spec == "black":
        return (0, 0, 0)
    return None


def hsl_to_rgb(h, s, l):
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c),
               (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return tuple(int(round(v * 255)) for v in (r + m, g + m, b + m))


def oklch_to_rgb(l, c, h):
    import math
    a = c * math.cos(math.radians(h))
    b = c * math.sin(math.radians(h))
    l_ = l + 0.3963377774 * a + 0.2158037573 * b
    m_ = l - 0.1055613458 * a - 0.0638541728 * b
    s_ = l - 0.0894841775 * a - 1.2914855480 * b
    l3, m3, s3 = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3
    g = -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3
    bl = -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3
    def enc(v):
        v = max(0.0, min(1.0, v))
        v = 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055
        return int(round(v * 255))
    return (enc(r), enc(g), enc(bl))


def luminance(rgb):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def rgb_to_hue(rgb):
    import colorsys
    r, g, b = (v / 255 for v in rgb)
    h, _, _ = colorsys.rgb_to_hsv(r, g, b)
    return h * 360


def is_purpleish(spec: str) -> bool:
    rgb = color_to_rgb(spec)
    if not rgb:
        return False
    import colorsys
    r, g, b = (v / 255 for v in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    deg = h * 360
    return 255 <= deg <= 300 and s >= 0.20 and 0.10 <= v <= 0.98


def is_colored_glow(value: str) -> bool:
    for m in COLOR_FUNC.finditer(value):
        fn = m.group(1).lower()
        if fn.startswith("color-mix"):
            continue
        rgb = color_to_rgb(m.group(0))
        if not rgb:
            continue
        r, g, b = rgb
        spread = max(rgb) - min(rgb)
        if spread >= 40 and max(rgb) >= 120:
            return True
    return False


def norm_font(name: str):
    name = name.strip().strip("'\"").split(",")[0].strip().strip("'\"")
    return re.sub(r"\s+", " ", name).lower()


def walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and
                       not d.startswith(".git")]
        for f in filenames:
            if os.path.splitext(f)[1].lower() in SCAN_EXT:
                yield os.path.join(dirpath, f)


def read(path):
    try:
        return open(path, "r", encoding="utf-8", errors="ignore").read()
    except OSError:
        return ""


# ---------------------------------------------------------------- checks

def check_fonts(html, css, stack):
    hits = set()
    inter = False
    for blob in (html, css, stack):
        for m in FONT_DECL.finditer(blob):
            n = norm_font(m.group(1))
            if n in FONT_POOL:
                hits.add(n)
            if n == "inter":
                inter = True
        for m in FONT_VAR.finditer(blob):
            n = norm_font(m.group(1))
            if n in FONT_POOL:
                hits.add(n)
            if n == "inter":
                inter = True
        for m in GOOGLE_FONT.finditer(blob):
            n = norm_font(m.group(1).replace("+", " "))
            if n in FONT_POOL:
                hits.add(n)
            if n == "inter":
                inter = True
        for m in TW_ARBITRARY_FONT.finditer(blob):
            n = norm_font(m.group(1))
            if n in FONT_POOL:
                hits.add(n)
            if n == "inter":
                inter = True
    return sorted(hits), inter


def check_hero_emphasis(html):
    out = []
    for m in H1_BLOCK.finditer(html):
        if HERO_EMPHASIS.search(m.group(1)):
            out.append(re.sub(r"\s+", " ", m.group(1))[:60])
    return out


def check_mono_body(css):
    """Mono is only a tell as *body* copy. Code blocks and pre keep their mono."""
    hits = set()
    body_sel = re.compile(r"(?:^|[\s,>+~])(?:body|html|:root|main)\b", re.I)
    for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", css):
        selector, body = m.group(1).strip(), m.group(2)
        if not body_sel.search(selector):
            continue
        for fd in FONT_DECL.finditer(body):
            for fam in fd.group(1).split(","):
                n = norm_font(fam)
                if "mono" in n or "courier" in n or "consolas" in n:
                    hits.add(n)
    return sorted(hits)


def check_radius(html, css, stack):
    values = set()
    for blob in (css, stack):
        for m in RADIUS_DECL.finditer(blob):
            raw = m.group(1)
            raw = raw.split("/")[0]
            for tok in raw.split():
                t = tok.strip()
                if t in ("0", "0px", "0rem"):
                    continue
                mm = RADIUS_TOKEN.match(t)
                if mm:
                    val, unit = float(mm.group(1)), mm.group(2).lower()
                    if unit == "rem":
                        val *= 16
                    elif unit == "em":
                        val *= 16
                    values.add(f"{val:g}px" if unit != "%" else "50%")
                elif re.match(r"^[\d.]+%$", t):
                    values.add("50%")
    for blob in (html, stack):
        for m in TW_ROUNDED.finditer(blob):
            cls = m.group(0)
            if cls in ("rounded-none", "rounded-0"):
                continue
            values.add("tw:" + cls)
    return sorted(values)


VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
             "meta", "param", "source", "track", "wbr", "path", "circle", "rect",
             "line", "polyline", "polygon", "use", "stop", "ellipse"}
TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9-]*)\b([^>]*?)(/?)\s*>", re.S)
CARD_CLASS = re.compile(r"class\s*=\s*[\"'][^\"']*\bcard\b", re.I)


def check_nested_cards(html):
    """Depth-aware: only counts a card opened while another card is still open."""
    stack = []
    nested = 0
    for m in TAG.finditer(html):
        closing, tag, attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if tag in VOID_TAGS or selfclose:
            continue
        if closing:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == tag:
                    del stack[i:]
                    break
            continue
        is_card = bool(CARD_CLASS.search(attrs))
        if is_card and any(c for _, c in stack):
            nested += 1
        stack.append((tag, is_card))
    return nested


def check_numbered_steps(html):
    hits = 0
    for m in OL_BLOCK.finditer(html):
        attrs, body = m.group(1), m.group(2)
        if OL_EXEMPT.search(attrs):
            continue
        items = len(re.findall(r"<li\b", body, re.I))
        if items >= 3 and not OL_EXEMPT.search(body[:200]):
            hits += 1
    return hits


def purple_loudness(css):
    """Doc targets purple *gradients* and saturated fills. A 0.1-alpha tint is a review item."""
    loud, tint = [], []
    for m in re.finditer(r"([a-z-]+)\s*:\s*([^;}]+)", css, re.I):
        prop, value = m.group(1).lower(), m.group(2)
        colors = [c.group(0) for c in
                  re.finditer(r"#[0-9a-f]{3,8}|rgba?\([^)]*\)|hsla?\([^)]*\)|oklch\([^)]*\)",
                              value, re.I)]
        for spec in colors:
            if not is_purpleish(spec):
                continue
            alpha = 1.0
            am = re.search(r"[\d.]+\s*\)\s*$", spec)
            parts = re.split(r"[,\s/]+", spec.strip(")").split("(", 1)[-1])
            if len(parts) == 4:
                try:
                    alpha = float(parts[3].rstrip("%"))
                    if alpha > 1:
                        alpha /= 100
                except ValueError:
                    alpha = 1.0
            in_gradient = "gradient" in value
            if in_gradient or (prop.startswith("background") and alpha >= 0.5):
                loud.append(spec)
            else:
                tint.append(spec)
    return sorted(set(loud)), sorted(set(tint))


def check_shadows(css):
    graded = 0
    colored = 0
    for m in SHADOW_DECL.finditer(css):
        value = m.group(2)
        if not (COLOR_FUNC.search(value) or HEX_COLOR.search(value)):
            continue
        graded += 1
        if is_colored_glow(value):
            colored += 1
    return graded, colored


def check_contrast(css):
    """Same-rule color/background pairs that fail WCAG AA for body text."""
    fails = []
    for m in re.finditer(r"([^{}]*)\{([^{}]*)\}", css):
        body = m.group(2)
        fg = re.search(r"(?:^|[;{\s])color\s*:\s*([^;}]+)", body)
        bg = re.search(r"(?:^|[;{\s])background(?:-color)?\s*:\s*([^;}]+)", body)
        if not fg or not bg:
            continue
        f, b = fg.group(1).strip(), bg.group(1).strip()
        if "var(" in f or "var(" in b or "gradient" in b:
            continue
        rfg, rbg = color_to_rgb(f), color_to_rgb(b)
        if not rfg or not rbg:
            continue
        ratio = contrast_ratio(rfg, rbg)
        if ratio < 4.5:
            fails.append({"selector": m.group(1).strip()[:60],
                          "fg": f, "bg": b, "ratio": round(ratio, 2)})
    return fails[:10]


def check_spacing(css):
    off = 0
    total = 0
    for m in SPACING_DECL.finditer(css):
        for tok in m.group(1).split():
            mm = SPACING_TOKEN.match(tok.strip())
            if not mm:
                continue
            v = float(mm.group(1))
            total += 1
            if v % 4 != 0:
                off += 1
    return total, off


def check_motion(css, stack):
    hidden = bool(OPACITY_ZERO.search(css))
    reveal = bool(JS_REVEAL.search(stack))
    animated = bool(ANIMATION.search(css))
    reduced = bool(REDUCED_MOTION.search(css))
    return {
        "opacity_zero": hidden,
        "js_reveal_present": reveal,
        "hidden_without_js": hidden and not reveal,
        "animated": animated,
        "missing_reduced_motion": animated and not reduced,
    }


def check_focus(css):
    return bool(OUTLINE_KILL.search(css)) and not bool(FOCUS_STYLE.search(css))


def check_copyright(html):
    now = datetime.now(timezone.utc).year
    for m in COPYRIGHT.finditer(html):
        for ym in YEAR.finditer(m.group(0)):
            y = int(ym.group(0))
            if y < now:
                return y
    return None


# ---------------------------------------------------------------- scan

def build_report(root: str, blobs: dict):
    html = blobs["html"]
    css = blobs["css"]
    stack = blobs["stack"]
    low = stack.lower()
    out = {}
    findings = []
    files = blobs["files"]

    fonts, inter = check_fonts(html, css, stack)
    out["default_fonts"] = fonts
    out["inter_present"] = inter
    loud_purple, tint_purple = purple_loudness(css + "\n" + html)
    purples = sorted(set(m.group(0) for m in PURPLE_HEX.finditer(stack)))
    purples += sorted(set(m.group(0) for m in PURPLE_TW.finditer(stack)))
    purples += loud_purple
    tints = [t for t in tint_purple if t not in purples]
    out["vibecode_purple"] = sorted(set(purples))
    out["purple_tint"] = tints
    out["gradient_count"] = len(GRADIENT.findall(stack)) + len(GRADIENT_TW.findall(stack))
    graded, colored = check_shadows(css)
    out["gradient_shadows"] = graded
    out["colored_glows"] = colored
    out["glassmorphism"] = len(GLASS.findall(stack))
    out["emoji_count"] = len(EMOJI.findall(html + css))
    out["uppercase_labels"] = len(CAPS_LABEL.findall(css))
    out["left_border_cards"] = len(LEFT_BORDER.findall(css))
    out["top_accent_borders"] = len(TOP_ACCENT.findall(css))
    out["hover_lift_effects"] = len(HOVER_LIFT.findall(css))
    radii = check_radius(html, css, stack)
    out["distinct_radius_values"] = len(radii)
    out["radius_tokens"] = radii
    out["nested_cards"] = check_nested_cards(html)
    out["numbered_steps"] = check_numbered_steps(html)
    out["step_prose"] = len(STEP_PROSE.findall(html))
    out["shadcn_tokens"] = bool(SHADCN_TOKENS.search(css))
    out["generic_taglines"] = [t for t in TAGLINES if t in low]
    out["stale_copyright"] = check_copyright(html)
    out["hero_emphasis"] = check_hero_emphasis(html)
    out["mono_body"] = check_mono_body(css)
    out["stat_banner_hits"] = sorted(set(STAT_ROW.findall(html)))[:6]
    out["contrast_failures"] = check_contrast(css)
    sp_total, sp_off = check_spacing(css)
    out["spacing_tokens"] = sp_total
    out["off_scale_spacing"] = sp_off
    motion = check_motion(css, stack)
    out.update(motion)
    out["outline_removed"] = check_focus(css)
    out["has_og_title"] = bool(OG_TITLE.search(html))
    out["has_og_image"] = bool(OG_IMAGE.search(html))
    out["has_favicon"] = bool(FAVICON.search(html))
    out["has_meta_desc"] = bool(META_DESC.search(html))
    title = TITLE_TAG.search(html)
    out["title"] = title.group(1).strip() if title else None
    out["generic_title"] = bool(title and TITLE_GENERIC.match(title.group(1)))

    # ---- findings + verdict
    def add(key, detail, count=1):
        rule, sev = CHECKS.get(key, ("?", "review"))
        findings.append({"check": key, "rule": rule, "severity": sev,
                         "detail": detail, "count": count})

    if fonts:
        add("default_fonts", fonts)
    if inter and not fonts:
        add("inter_sole_identity", "inter used as the only identity face; name why")
    if out["hero_emphasis"]:
        add("hero_emphasis", out["hero_emphasis"])
    if out["mono_body"]:
        add("mono_body", out["mono_body"])
    if out["vibecode_purple"]:
        add("vibecode_purple", out["vibecode_purple"], len(out["vibecode_purple"]))
    if out["purple_tint"]:
        add("purple_tint", out["purple_tint"], len(out["purple_tint"]))
    if out["gradient_count"] > 4:
        add("gradient_count", out["gradient_count"], out["gradient_count"])
    if out["colored_glows"]:
        add("colored_glows", out["colored_glows"], out["colored_glows"])
    if out["glassmorphism"]:
        add("glassmorphism", out["glassmorphism"], out["glassmorphism"])
    if out["contrast_failures"]:
        add("contrast_failures", out["contrast_failures"], len(out["contrast_failures"]))
    if out["uppercase_labels"] > 3:
        add("uppercase_labels", out["uppercase_labels"], out["uppercase_labels"])
    if out["left_border_cards"]:
        add("left_border_cards", out["left_border_cards"], out["left_border_cards"])
    if out["top_accent_borders"]:
        add("top_accent_borders", out["top_accent_borders"], out["top_accent_borders"])
    if out["nested_cards"]:
        add("nested_cards", out["nested_cards"], out["nested_cards"])
    if out["numbered_steps"]:
        add("numbered_steps", out["numbered_steps"], out["numbered_steps"])
    if out["stat_banner_hits"]:
        add("stat_banner_hits", out["stat_banner_hits"])
    if out["distinct_radius_values"] > 3:
        add("distinct_radius_values", radii, out["distinct_radius_values"])
    if sp_total and sp_off > max(1, sp_total * 0.2):
        add("off_scale_spacing", f"{sp_off}/{sp_total} off a 4px grid")
    if out["hidden_without_js"]:
        add("hidden_without_js", "opacity:0 with no reveal logic found")
    if out["hover_lift_effects"]:
        add("hover_lift_effects", out["hover_lift_effects"], out["hover_lift_effects"])
    if out["missing_reduced_motion"]:
        add("missing_reduced_motion", "animation/transition without prefers-reduced-motion")
    if out["outline_removed"]:
        add("outline_removed", "outline:none with no :focus style")
    if out["emoji_count"] > 3:
        add("emoji_count", out["emoji_count"], out["emoji_count"])
    if out["generic_taglines"]:
        add("generic_taglines", out["generic_taglines"], len(out["generic_taglines"]))
    if out["stale_copyright"]:
        add("stale_copyright", out["stale_copyright"])
    if not (out["has_og_title"] and out["has_og_image"]):
        add("missing_og", {"og:title": out["has_og_title"], "og:image": out["has_og_image"]})
    if not out["has_favicon"]:
        add("missing_favicon", True)
    if not out["has_meta_desc"]:
        add("missing_meta_desc", True)
    if out["generic_title"]:
        add("generic_title", out["title"])

    tells = [f for f in findings if f["severity"] == "tell"]
    n_tells = sum(f["count"] for f in tells)
    verdict = "slop" if n_tells >= TELL_THRESHOLD else ("review" if findings else "clean")
    out["findings"] = findings
    out["tell_count"] = n_tells
    out["verdict"] = verdict
    out["exit"] = {"clean": 0, "review": 1, "slop": 2}[verdict]
    out["files_scanned"] = files
    return out


STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.I | re.S)


def split_page(text: str):
    """Inline <style> blocks are CSS and must not be invisible to the CSS checks."""
    return "\n".join(STYLE_BLOCK.findall(text))


def collect(root: str):
    html_parts, css_parts, other_parts, files = [], [], [], []
    for p in sorted(walk(root)):
        text = read(p)
        files.append(os.path.relpath(p, root))
        ext = os.path.splitext(p)[1].lower()
        if ext in (".html", ".htm", ".vue", ".svelte", ".astro"):
            html_parts.append(text)
            inline = split_page(text)
            if inline:
                css_parts.append(inline)
        elif ext == ".css":
            css_parts.append(text)
        else:
            other_parts.append(text)
    return {
        "html": "\n".join(html_parts),
        "css": "\n".join(css_parts),
        "stack": "\n".join(html_parts + css_parts + other_parts),
        "files": files,
    }


def render_text(rep):
    lines = [f"verdict: {rep['verdict'].upper()}  (tells={rep['tell_count']}, "
             f"exit={rep['exit']}, files={len(rep['files_scanned'])})"]
    if not rep["findings"]:
        lines.append("  no findings")
    for f in rep["findings"]:
        mark = "!" if f["severity"] == "tell" else "?"
        lines.append(f"  [{mark}] {f['check']} ({f['rule']}): {f['detail']}")
    return "\n".join(lines)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if not args:
        print(__doc__)
        return 64
    root = args[0]
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 64
    reports = []
    if "--per-file" in flags:
        for p in sorted(walk(root)):
            if os.path.splitext(p)[1].lower() not in (".html", ".htm"):
                continue
            text = read(p)
            rep = build_report(p, {"html": text, "css": split_page(text),
                                   "stack": text, "files": [p]})
            rep["path"] = os.path.relpath(p, root)
            reports.append(rep)
    else:
        rep = build_report(root, collect(root))
        rep["path"] = root
        reports.append(rep)

    worst = max(r["exit"] for r in reports) if reports else 0
    if "--json" in flags or not ("--text" in flags):
        payload = reports if (len(reports) > 1 or "--per-file" in flags) else reports[0]
        print(json.dumps(payload, indent=2))
    else:
        print("\n".join(render_text(r) for r in reports))
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv))
