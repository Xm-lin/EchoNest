"""EchoNest character-card renderer. Fixed artboard + live data; no image AI calls.

Replace assets/character_card_base.png with your own 900x1340 blank template.
Keep portrait/text/number areas empty: they are rendered dynamically.
"""
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
W, H = 900, 1340
WHITE = '#F7F3FA'
MUTED = '#B6ADBE'
LILAC = '#C2A3F5'
PINK = '#F2A1C5'
FONTS = ['/usr/share/fonts/opentype/noto', '/usr/share/fonts/truetype/noto']


def font(size, serif=False):
    file = 'NotoSerifCJK-Regular.ttc' if serif else 'NotoSansCJK-Regular.ttc'
    for directory in FONTS:
        try:
            return ImageFont.truetype(str(Path(directory) / file), size, index=3)
        except OSError:
            continue
    return ImageFont.truetype('DejaVuSans.ttf', size)


def put(draw, xy, value, size, color=WHITE, max_width=None, serif=False, anchor='lt'):
    value = str(value)
    f = font(size, serif)
    if max_width:
        while size > 18 and draw.textbbox((0, 0), value, font=f)[2] > max_width:
            size -= 2
            f = font(size, serif)
        while value and draw.textbbox((0, 0), value, font=f)[2] > max_width:
            value = value[:-1]
        if not value:
            value = '…'
    draw.text(xy, value, font=f, fill=color, anchor=anchor)


def progress(draw, x0, y0, x1, y1, value, tint):
    draw.rounded_rectangle((x0,y0,x1,y1), radius=9, fill='#494353')
    width = int((x1-x0)*max(0,min(1,value)))
    if width:
        draw.rounded_rectangle((x0,y0,x0+max(16,width),y1),radius=9,fill=tint)


def heart(draw, x, y, active):
    color = PINK if active else '#51485B'
    draw.ellipse((x-17,y-12,x+1,y+6),fill=color)
    draw.ellipse((x-1,y-12,x+17,y+6),fill=color)
    draw.polygon([(x-17,y-3),(x+17,y-3),(x,y+22)],fill=color)


def render_character_card(character, profile, portrait_bytes=None, relation='初識'):
    image = Image.open(ROOT/'assets'/'character_card_base.png').convert('RGB')
    if image.size != (W,H):
        raise ValueError('Template must be 900x1340')
    draw = ImageDraw.Draw(image)
    if portrait_bytes:
        try:
            with Image.open(BytesIO(portrait_bytes)) as source:
                source = ImageOps.exif_transpose(source)
                source.thumbnail((2600,2600))
                portrait = ImageOps.fit(source.convert('RGB'),(W,760),centering=(.5,.35))
            image.paste(portrait,(0,0))
        except (OSError, ValueError, Image.DecompressionBombError):
            portrait_bytes = None
    if not portrait_bytes:
        draw.rectangle((0,0,W,760),fill='#393344')
        put(draw,(W//2,350),'尚未上傳角色圖片',30,'#C5BBCD',anchor='mm')
    veil=Image.new('RGBA',(W,760),(0,0,0,0))
    vd=ImageDraw.Draw(veil)
    for y in range(760):
        alpha=int(248*max(0,(y-310)/450)**1.3)
        vd.line((0,y,W,y),fill=(20,19,30,alpha))
    image.paste(veil,(0,0),veil)
    draw=ImageDraw.Draw(image)
    # all UI uses fixed top-left anchors to avoid mixed-font baseline drift
    put(draw,(56,54),'EchoNest',30,'#FFFFFF')
    put(draw,(56,548),character.get('name','角色'),88,WHITE,max_width=780,serif=True)
    put(draw,(60,681),f"{character.get('personality','未知')}  ·  {relation}",28,'#E2D0EE',max_width=750)

    put(draw,(58,778),'關係階段',22,MUTED)
    put(draw,(58,819),relation,34)
    put(draw,(340,778),'目前心情',22,MUTED)
    put(draw,(340,819),character.get('mood','普通'),34,max_width=210)
    put(draw,(647,778),'角色個性',22,MUTED)
    put(draw,(647,819),character.get('personality','未知'),34,max_width=192)

    exp=max(0,int(profile.get('exp') or 0))
    affection=max(0,min(100,int(profile.get('affection') or 0)))
    put(draw,(58,905),'Lv.',27,MUTED,serif=True)
    put(draw,(58,948),f'{1+exp//100:02}',77,WHITE,serif=True)
    put(draw,(276,917),'經驗值',27,MUTED)
    put(draw,(841,919),f'{exp%100} / 100',25,'#D5C1EE',anchor='rt')
    progress(draw,276,977,841,995,(exp%100)/100,LILAC)

    put(draw,(58,1106),'好感度',27,MUTED)
    for i in range(5):
        heart(draw,310+i*75,1134,affection >= (i+1)*20)
    put(draw,(841,1106),f'{affection} / 100',25,'#F3ACCE',anchor='rt')
    progress(draw,58,1181,841,1199,affection/100,PINK)
    put(draw,(58,1262),'ECHONEST',19,'#8D859A')
    put(draw,(841,1262),f"#{character.get('id','—')}",19,'#8D859A',anchor='rt')
    result=BytesIO()
    image.save(result,format='PNG',optimize=True)
    result.seek(0)
    return result
