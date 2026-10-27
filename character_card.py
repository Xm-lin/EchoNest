import io
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT_PATHS = ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
              '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
              'C:/Windows/Fonts/msjh.ttc']

def font(size):
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path,size)
    return ImageFont.load_default()

def render_card(name, personality, owner, mood, affection, level, exp, portrait=None):
    image=Image.new('RGB',(1000,580),'#10151f')
    d=ImageDraw.Draw(image)
    d.rounded_rectangle((30,30,970,550),radius=32,fill='#1b2534',outline='#33445d',width=2)
    d.text((70,55),'ECHONEST  /  CHARACTER',font=font(20),fill='#93abc8')
    d.text((70,100),str(name)[:24],font=font(42),fill='#f1f5fc')
    d.text((70,170),f'性格  {personality}',font=font(24),fill='#b8c9dd')
    d.text((70,218),f'擁有者  {owner}',font=font(22),fill='#b8c9dd')
    d.text((70,290),f'等級  {level}',font=font(27),fill='#f1f5fc')
    d.text((70,338),f'好感度  {affection}',font=font(24),fill='#f1f5fc')
    def bar(y,title,value,max_value,color):
        d.text((70,y),f'{title}  {value}/{max_value}',font=font(19),fill='#b8c9dd')
        d.rounded_rectangle((70,y+34,575,y+51),radius=8,fill='#344255')
        w=int(505*max(0,min(value/max_value,1)))
        if w: d.rounded_rectangle((70,y+34,70+w,y+51),radius=8,fill=color)
    bar(393,'心情',int(mood),100,'#64c7b0')
    bar(463,'EXP',int(exp)%100,100,'#82a9ff')
    d.rounded_rectangle((635,108,920,443),radius=20,fill='#29364a')
    if portrait:
        try:
            with Image.open(io.BytesIO(portrait)) as p:
                p=ImageOps.fit(p.convert('RGB'),(285,335))
                image.paste(p,(635,108))
        except Exception:
            pass
    else:
        d.text((695,250),'NO IMAGE',font=font(23),fill='#91a4bd')
    out=io.BytesIO();image.save(out,format='PNG');out.seek(0)
    return out
