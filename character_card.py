"""Render an EchoNest character card using Pillow; no image generation call."""
import io
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat

SIZE = (1600, 960)
FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
FONT_CJK = [os.path.join(FONT_DIR, 'NotoSansCJK-Regular.ttc'), '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', 'C:/Windows/Fonts/msjh.ttc']
FONT_SERIF = ['/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf', '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf']
FONT_NUMBER = ['/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf', '/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf']
FONT_SANS = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']

def font(size, kind='cjk'):
    paths = {'cjk': FONT_CJK, 'serif': FONT_SERIF, 'number': FONT_NUMBER, 'sans': FONT_SANS}[kind]
    for path in paths:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def mix(a, b, t):
    return tuple(round(a[i]*(1-t)+b[i]*t) for i in range(3))

def theme_color(portrait):
    if not portrait:
        return (177, 141, 197)
    try:
        with Image.open(io.BytesIO(portrait)) as im:
            im = im.convert('RGB').resize((96,96))
            colors = im.quantize(colors=16).convert('RGB').getcolors(96*96) or []
        candidates = []
        for count, color in colors:
            r,g,b = color
            spread = max(color)-min(color)
            light = (r+g+b)/3
            if 50 < light < 210 and spread > 15 and not (r>g*1.15 and g>b*1.1):
                candidates.append((count*min(spread,75), color))
        if candidates:
            raw = max(candidates)[1]
            return mix(raw, (187,164,211), .38)
    except Exception:
        pass
    return (177, 141, 197)

def fitted_font(draw, text, max_width, start, minimum=22, kind='cjk'):
    for size in range(start,minimum-1,-2):
        f = font(size,kind)
        if draw.textbbox((0,0),text,font=f)[2] <= max_width:
            return f
    return font(minimum,kind)

def render_card(name, personality, owner, mood, affection, level, exp, portrait=None):
    accent = theme_color(portrait)
    pale = mix(accent,(255,245,255),.62)
    muted = mix(accent,(91,82,106),.58)
    bg = (24,23,32)
    im = Image.new('RGB', SIZE, bg)
    d = ImageDraw.Draw(im)
    # Subtle horizontal background gradient, deliberately without glow.
    for y in range(960):
        shade = round(7*y/960)
        d.line((0,y,1599,y),fill=(bg[0]+shade,bg[1]+shade,bg[2]+shade))
    # Double frame and handcrafted corner strokes.
    d.rounded_rectangle((20,20,1580,940),radius=27,outline=pale,width=9)
    d.rounded_rectangle((33,33,1567,927),radius=19,outline=muted,width=2)
    for sx in (1,-1):
        for sy in (1,-1):
            x = 40 if sx==1 else 1560
            y = 40 if sy==1 else 920
            d.line([(x,y+sy*50),(x,y),(x+sx*75,y)],fill=pale,width=3)
            d.line([(x+sx*9,y+sy*60),(x+sx*9,y+sy*9),(x+sx*85,y+sy*9)],fill=muted,width=2)
    # Header.
    d.text((90,72),'E C H O N E S T   /   C H A R A C T E R',font=font(23,'sans'),fill=pale)
    d.line((550,81,743,81),fill=muted,width=2)
    # Character title; large serif English and a clear CJK fallback.
    name = str(name or 'Unnamed')
    english = all(ord(ch)<128 for ch in name)
    title_kind = 'serif' if english else 'cjk'
    title = fitted_font(d,name,660,180 if english else 115,36,title_kind)
    d.text((84,116),name,font=title,fill=(246,234,250),stroke_width=0)
    name_bottom = d.textbbox((84,116),name,font=title)[3]
    tag_y = max(292,min(335,name_bottom+12))
    tag_y = tag_y+15
    personality = str(personality or '未設定')
    tag_font = fitted_font(d,personality,260,32,20)
    tag_w = min(310,max(170,d.textbbox((0,0),personality,font=tag_font)[2]+56))
    d.rounded_rectangle((84,tag_y,84+tag_w,tag_y+57),radius=9,outline=pale,width=2)
    d.text((136,tag_y+4),personality,font=tag_font,fill=(245,235,249))
    # Section break.
    d.line((88,395,710,395),fill=muted,width=2)
    d.polygon([(84,395),(96,383),(108,395),(96,407)],fill=pale)
    d.text((80,425),'等級',font=font(39),fill=(235,224,240))
    d.text((200,400),str(level),font=font(94,'number'),fill=(245,231,249))
    def stat(y, label, value, maximum):
        d.text((100,y-5),label,font=font(31),fill=(245,237,248))
        maximum=max(1,int(maximum))
        d.text((205,y+5),f'{value} / {maximum}',font=font(27,'sans'),fill=pale)
        d.rounded_rectangle((100,y+50,700,y+70),radius=11,fill=(48,44,59),outline=muted,width=2)
        ratio=max(0,min(float(value)/maximum,1))
        if ratio>0:
            width=max(9,round(523*ratio))
            d.rounded_rectangle((103,y+54,173+width,y+67),radius=9,fill=pale)

    stat(510,'好感度',int(affection),100)
    stat(610,'心情',int(mood),100)
    stat(710,'EXP',int(exp)%100,100)
    # Portrait panel.
    frame=(730,140,1535,800)
    d.rounded_rectangle((frame[0]-3,frame[1]-3,frame[2]+3,frame[3]+3),radius=20,outline=pale,width=4)
    box=(frame[2]-frame[0],frame[3]-frame[1])
    if portrait:
        try:
            with Image.open(io.BytesIO(portrait)) as src:
                pic=ImageOps.fit(src.convert('RGB'),box,method=Image.Resampling.LANCZOS,centering=(.5,.42))
            mask=Image.new('L',box,0)
            ImageDraw.Draw(mask).rounded_rectangle((0,0,box[0]-1,box[1]-1),radius=17,fill=255)
            im.paste(pic,(frame[0],frame[1]),mask)
        except Exception:
            d.text((1025,435),'NO IMAGE',font=font(30,'sans'),fill=pale)
    else:
        d.text((1025,435),'NO IMAGE',font=font(30,'sans'),fill=pale)
    # Bottom owner strip.
    d.line((70,827,1530,827),fill=muted,width=2)
    owner = str(owner or '未知')
    label='主人：'+owner
    d.text((150,855),label,font=fitted_font(d,label,1100,31,18),fill=pale)
    for x in (1430,1467,1504):
        d.polygon([(x,861),(x+8,873),(x+20,879),(x+8,885),(x,897),(x-8,885),(x-20,879),(x-8,873)],fill=pale)
    out=io.BytesIO()
    im.save(out,'PNG')
    out.seek(0)
    return out


if __name__ == "__main__":
    # 測試資料，可以自行修改
    NAME = "Niko"
    PERSONALITY = "搞笑"
    OWNER = "小林"
    MOOD = 100
    AFFECTION = 100
    LEVEL = 1
    EXP = 35

    # 角色圖片，放在同一個資料夾
    IMAGE_PATH = "portrait.png"

    portrait = None
    if os.path.isfile(IMAGE_PATH):
        with open(IMAGE_PATH, "rb") as f:
            portrait = f.read()

    result = render_card(
        name=NAME,
        personality=PERSONALITY,
        owner=OWNER,
        mood=MOOD,
        affection=AFFECTION,
        level=LEVEL,
        exp=EXP,
        portrait=portrait,
    )

    with open("card_preview.png", "wb") as f:
        f.write(result.getvalue())

    print("已產生 card_preview.png")