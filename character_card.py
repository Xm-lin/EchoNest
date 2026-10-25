"""EchoNest illustrated character card. Pillow-only, no image generation/API calls.

All displayed player values come from the database; the hero image comes from
Supabase Storage. The art direction is a reusable game UI, not a fixed screenshot.
"""
from io import BytesIO
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

W, H = 1000, 1440
BG = (15, 12, 30)
WHITE = (247, 239, 255)
MUTED = (177, 164, 207)
LILAC = (183, 146, 255)
PINK = (255, 164, 213)
FONT_SANS = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]
FONT_SERIF = [
    '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc',
] + FONT_SANS


def font(size, serif=False):
    for path in (FONT_SERIF if serif else FONT_SANS):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fitted(draw, text, max_width, size, minimum=20, serif=False):
    text = str(text)
    while size > minimum and draw.textbbox((0, 0), text, font=font(size, serif))[2] > max_width:
        size -= 2
    f = font(size, serif)
    if draw.textbbox((0, 0), text, font=f)[2] <= max_width:
        return text, f
    while text and draw.textbbox((0, 0), text + '…', font=f)[2] > max_width:
        text = text[:-1]
    return text + '…', f


def aligned_text(draw, xy, text, *, font, fill, anchor=None, **kwargs):
    """Align text to its visible top edge, independent of font ascender."""
    if anchor:
        return draw.text(xy, text, font=font, fill=fill, anchor=anchor, **kwargs)
    left, top, _, _ = draw.textbbox((0, 0), str(text), font=font, stroke_width=kwargs.get("stroke_width", 0))
    return draw.text((xy[0] - left, xy[1] - top), text, font=font, fill=fill, **kwargs)


def glow_layer(base, x, y, radius, color, strength=110):
    layer = Image.new('RGBA', base.size)
    d = ImageDraw.Draw(layer)
    d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(*color, strength))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius // 2)))


def rounded_panel(draw, rect, fill=(29, 23, 49, 235), outline=(115, 92, 160, 145), radius=28):
    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=outline, width=2)


def spark(draw, x, y, size=10, color=(202, 170, 255, 170)):
    draw.line((x-size, y, x+size, y), fill=color, width=2)
    draw.line((x, y-size, x, y+size), fill=color, width=2)
    draw.ellipse((x-2, y-2, x+2, y+2), fill=(255, 242, 255, 210))


def progress(draw, rect, value, color):
    x0, y0, x1, y1 = rect
    draw.rounded_rectangle(rect, radius=(y1-y0)//2, fill=(64, 53, 91, 230))
    value = max(0, min(100, value))
    width = int((x1-x0)*value/100)
    if width:
        width = max(width, y1-y0)
        draw.rounded_rectangle((x0, y0, min(x1, x0+width), y1), radius=(y1-y0)//2, fill=(*color, 255))
        draw.ellipse((min(x1, x0+width)-14, y0-3, min(x1, x0+width)+3, y1+3), fill=(255, 236, 255, 215))


def heart(draw, cx, cy, size, fill):
    # Filled vector heart: no emoji fonts needed on Render.
    r = size / 4
    draw.ellipse((cx-2*r, cy-2*r, cx, cy), fill=fill)
    draw.ellipse((cx, cy-2*r, cx+2*r, cy), fill=fill)
    draw.polygon([(cx-2*r, cy-r), (cx+2*r, cy-r), (cx, cy+2.1*r)], fill=fill)


def cover_portrait(raw, width, height):
    with Image.open(BytesIO(raw)) as source:
        source = ImageOps.exif_transpose(source)
        source.thumbnail((2800, 2800))
        return ImageOps.fit(source.convert('RGB'), (width, height), method=Image.Resampling.LANCZOS,
                            centering=(0.5, 0.28)).convert('RGBA')


def render_character_card(character, profile, portrait_bytes=None, relation='初識'):
    card = Image.new('RGBA', (W, H), (*BG, 255))
    d = ImageDraw.Draw(card, 'RGBA')
    # Subtle wallpaper, illuminated behind the actual portrait.
    for y in range(H):
        t = y/H
        d.line((0, y, W, y), fill=(int(27-12*t), int(18-6*t), int(48-15*t), 255))
    glow_layer(card, 130, 450, 390, (124, 74, 196), 135)
    glow_layer(card, 940, 100, 320, (217, 111, 163), 95)
    glow_layer(card, 760, 1160, 360, (91, 73, 186), 85)

    hero_h = 745
    portrait_ok = False
    if portrait_bytes:
        try:
            portrait = cover_portrait(portrait_bytes, W, hero_h)
            card.alpha_composite(portrait, (0, 0))
            portrait_ok = True
        except (OSError, ValueError, Image.DecompressionBombError):
            pass
    if not portrait_ok:
        # Deliberately abstract placeholder; never substitutes a made-up character.
        placeholder = Image.new('RGBA', (W, hero_h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(placeholder, 'RGBA')
        pd.ellipse((190, 70, 830, 720), outline=(190, 151, 255, 100), width=5)
        pd.ellipse((280, 160, 730, 610), fill=(100, 76, 153, 75), outline=(201, 165, 255, 115), width=3)
        paligned_text(d, (500, 365), '✦', font=font(155), anchor='mm', fill=(231, 203, 255, 220))
        card.alpha_composite(placeholder)

    # Portrait legibility: cinematic dark vignette and soft bottom fade.
    shade = Image.new('RGBA', (W, hero_h))
    sd = ImageDraw.Draw(shade)
    for y in range(hero_h):
        lower = max(0, (y-390)/(hero_h-390))
        a = int(235 * lower**1.2)
        sd.line((0, y, W, y), fill=(16, 12, 30, a))
    card.alpha_composite(shade)
    d = ImageDraw.Draw(card, 'RGBA')
    d.rounded_rectangle((36, 34, 964, 1404), radius=34, outline=(187, 149, 245, 105), width=2)
    d.rounded_rectangle((56, 54, 286, 108), radius=26, fill=(22, 16, 42, 210), outline=(201, 169, 255, 130), width=2)
    aligned_text(d, (78, 69), 'E C H O N E S T', font=font(22), fill=(239, 215, 255, 255))
    aligned_text(d, (62, 562), 'CHARACTER  /  PROFILE', font=font(23), fill=(219, 182, 255, 255))
    name, name_font = fitted(d, character['name'], 850, 92, 40, serif=True)
    aligned_text(d, (56, 603), name, font=name_font, fill=WHITE, stroke_width=1, stroke_fill=(20, 12, 37))
    personality = str(character.get('personality') or '未知')
    tag, tag_font = fitted(d, f'{personality}  ·  {relation}', 820, 28)
    aligned_text(d, (62, 711), tag, font=tag_font, fill=(225, 192, 255))
    d.line((62, 768, 938, 768), fill=(169, 126, 232, 135), width=2)

    # Status ribbon.
    rounded_panel(d, (54, 791, 946, 898), fill=(30, 23, 53, 235))
    aligned_text(d, (85, 809), '關係階段', font=font(22), fill=MUTED)
    aligned_text(d, (85, 845), str(relation), font=font(31), fill=WHITE)
    d.line((370, 814, 370, 877), fill=(119, 97, 160, 165), width=2)
    aligned_text(d, (412, 809), '目前心情', font=font(22), fill=MUTED)
    mood, mood_font = fitted(d, character.get('mood', '普通'), 225, 31)
    aligned_text(d, (412, 845), mood, font=mood_font, fill=WHITE)
    d.line((699, 814, 699, 877), fill=(119, 97, 160, 165), width=2)
    aligned_text(d, (743, 809), '角色個性', font=font(22), fill=MUTED)
    trait, trait_font = fitted(d, personality, 165, 29)
    aligned_text(d, (743, 845), trait, font=trait_font, fill=WHITE)

    exp = max(0, int(profile.get('exp') or 0))
    affection = max(0, min(100, int(profile.get('affection') or 0)))
    lvl = 1 + exp // 100
    rounded_panel(d, (54, 919, 946, 1113), fill=(29, 22, 52, 240))
    aligned_text(d, (87, 952), 'Lv.', font=font(29, serif=True), fill=MUTED)
    aligned_text(d, (87, 989), f'{lvl:02d}', font=font(70, serif=True), fill=WHITE)
    d.line((307, 944, 307, 1086), fill=(122, 94, 168, 175), width=2)
    aligned_text(d, (352, 953), '經驗值   EXPERIENCE', font=font(23), fill=(212, 193, 242))
    aligned_text(d, (904, 954), f'{exp%100} / 100', font=font(24), anchor='ra', fill=(216, 186, 255))
    progress(d, (354, 1017, 903, 1040), exp%100, LILAC)
    aligned_text(d, (354, 1060), '每一次互動，都是成長的紀錄', font=font(19), fill=(148, 137, 180))
    spark(d, 927, 936, 9)

    rounded_panel(d, (54, 1131, 946, 1304), fill=(29, 22, 52, 240))
    aligned_text(d, (86, 1162), '好感度   AFFECTION', font=font(24), fill=(231, 204, 248))
    aligned_text(d, (905, 1161), f'{affection} / 100', font=font(24), anchor='ra', fill=PINK)
    for i in range(5):
        heart(d, 410+i*86, 1192, 32, (255, 168, 211, 255) if affection >= (i+1)*20 else (99, 85, 122, 255))
    progress(d, (89, 1250, 907, 1272), affection, PINK)

    aligned_text(d, (75, 1342), 'YOUR STORY CONTINUES', font=font(21), fill=(183, 166, 214))
    aligned_text(d, (921, 1342), f'#{character.get("id", "—")}', font=font(21), anchor='ra', fill=(183, 166, 214))
    # Stable, tasteful decorative stars; no randomness in character identity.
    for x, y, r in [(919, 132, 13), (70, 370, 8), (932, 545, 12), (921, 740, 7), (74, 1377, 5)]:
        spark(d, x, y, r)
    output = BytesIO()
    card.convert('RGB').save(output, format='PNG', optimize=True)
    output.seek(0)
    return output
