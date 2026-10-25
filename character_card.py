"""Render a Discord-ready character profile PNG with Pillow; no AI calls."""
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 900, 1250
BG = (14, 17, 30)
WHITE = (243, 241, 255)
MUTED = (162, 168, 194)
PURPLE = (170, 141, 255)
PINK = (248, 150, 192)
FONT_PATHS = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]


def font(size):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_text(draw, text, max_width, initial_size, min_size=22):
    text = str(text)
    for size in range(initial_size, min_size - 1, -2):
        f = font(size)
        if draw.textbbox((0, 0), text, font=f)[2] <= max_width:
            return text, f
    f = font(min_size)
    while text and draw.textbbox((0, 0), text + '…', font=f)[2] > max_width:
        text = text[:-1]
    return text + '…', f


def bar(draw, x, y, width, fraction, accent):
    fraction = max(0.0, min(1.0, fraction))
    draw.rounded_rectangle((x, y, x + width, y + 14), radius=7, fill=(50, 53, 74))
    fill_width = round(width * fraction)
    if fill_width:
        draw.rounded_rectangle((x, y, x + max(14, fill_width), y + 14), radius=7, fill=accent)


def render_character_card(character, profile, portrait_bytes=None, relation='初識'):
    image = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(image)
    # Portrait takes up the top half, with a soft gradient into the stats panel.
    hero_h = 735
    if portrait_bytes:
        try:
            with Image.open(BytesIO(portrait_bytes)) as raw:
                portrait = ImageOps.fit(raw.convert('RGB'), (W, hero_h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.30))
            image.paste(portrait, (0, 0))
        except (OSError, ValueError):
            portrait_bytes = None
    if not portrait_bytes:
        for y in range(hero_h):
            t = y / hero_h
            draw.line((0, y, W, y), fill=(int(41 - 20*t), int(36 - 16*t), int(83 - 45*t)))
        draw.ellipse((230, 150, 670, 590), outline=(104, 89, 164), width=4)
        draw.text((W//2, 355), 'E', font=font(180), anchor='mm', fill=(146, 123, 214))
    overlay = Image.new('RGBA', (W, hero_h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(hero_h):
        a = int(245 * max(0, (y - 400) / (hero_h - 400)) ** 1.45)
        od.line((0, y, W, y), fill=(*BG, a))
    image.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((40, 38, 270, 86), radius=24, fill=(31, 30, 56))
    draw.text((61, 48), 'E C H O N E S T', font=font(22), fill=(216, 202, 255))
    draw.text((56, 695), 'CHARACTER PROFILE', font=font(21), fill=PURPLE)
    name, nf = fit_text(draw, character['name'], 780, 76)
    draw.text((52, 730), name, font=nf, fill=WHITE)
    draw.text((56, 826), f"{relation}   /   {character['personality']}", font=font(29), fill=(195, 181, 244))
    draw.line((54, 885, 846, 885), fill=(70, 67, 94), width=2)
    exp = max(0, int(profile['exp']))
    affection = max(0, min(100, int(profile['affection'])))
    mood = str(character.get('mood', '普通'))
    draw.text((56, 915), 'MOOD  /  心情', font=font(23), fill=MUTED)
    mood_text, mf = fit_text(draw, mood, 340, 30)
    draw.text((56, 950), mood_text, font=mf, fill=WHITE)
    draw.text((485, 915), 'LEVEL  /  等級', font=font(23), fill=MUTED)
    draw.text((485, 949), f'LV. {1 + exp // 100:02d}', font=font(36), fill=WHITE)
    draw.text((56, 1021), 'AFFECTION  /  好感度', font=font(23), fill=MUTED)
    draw.text((844, 1015), f'{affection} / 100', font=font(26), fill=PINK, anchor='ra')
    bar(draw, 56, 1062, 788, affection / 100, PINK)
    draw.text((56, 1101), 'EXPERIENCE  /  經驗值', font=font(23), fill=MUTED)
    draw.text((844, 1097), f'{exp % 100} / 100', font=font(26), fill=PURPLE, anchor='ra')
    bar(draw, 56, 1141, 788, (exp % 100) / 100, PURPLE)
    draw.line((56, 1196, 844, 1196), fill=(58, 58, 82), width=2)
    draw.text((56, 1210), 'YOUR STORY CONTINUES', font=font(20), fill=(132, 134, 163))
    draw.text((844, 1210), f"#{character['id']}", font=font(20), fill=(132, 134, 163), anchor='ra')
    output = BytesIO()
    image.save(output, format='PNG', optimize=True)
    output.seek(0)
    return output
