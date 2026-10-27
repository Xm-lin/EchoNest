import asyncio
import io
import logging
import random
from datetime import datetime, timedelta, timezone

import aiohttp
import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

import config
from ai import generate
from character_card import render_card
from health import start
from images import create_image, upload_image, delete_image, ImageProviderError

logging.basicConfig(level=config.env('LOG_LEVEL','INFO'),format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
log=logging.getLogger('echonest')
TZ=timezone(timedelta(hours=8))
PERSONALITIES=['傲嬌','毒舌','活潑','冷淡','溫柔','天然呆','腹黑','成熟','自訂']
GIFTS={'花束':3,'巧克力':4,'茶':2,'書':5,'玩偶':6,'餅乾':2,'明信片':3,'音樂盒':8,
       '羽毛筆':3,'星星吊飾':5,'香氛蠟燭':5,'手作卡片':4,'玻璃珠':2,'木製書籤':3,
       '毛線帽':5,'小盆栽':5,'鑰匙圈':3,'摺紙':2,'幸運石':3,'絲帶':2,
       '香水':6,'手帳':4,'相框':5,'水晶球':7,'風鈴':4,'手環':5,'毛毯':6,'圍巾':5,
       '紙鶴':2,'玻璃杯':3,'保溫瓶':5,'雨傘':4,'筆記本':3,'小夜燈':6,'咖啡豆':3,
       '奶茶':3,'熱可可':3,'果汁':2,'布丁':3,'馬卡龍':4,'蛋糕':5,'冰淇淋':3,
       '鬱金香':4,'向日葵':4,'滿天星':3,'乾燥花':4,'蝴蝶結':2,'手工皂':3,'香包':3,
       '陶瓷杯':4,'拼圖':5,'桌遊':6,'畫冊':5,'小說':4,'唱片':6,'耳機套':4,
       '徽章':3,'貼紙':2,'星空瓶':7,'迷你模型':6,'手作飾品':5,'紀念幣':4} 

def day(): return datetime.now(TZ).date()
def area(interaction): return ('guild',interaction.guild_id) if interaction.guild_id else ('dm',interaction.user.id)

def make_embed(text): return discord.Embed(description=text[:3900],color=0x678bc3)

class EchoNest(commands.Bot):
    def __init__(self):
        intents=discord.Intents.default();intents.members=True
        super().__init__(command_prefix='!',intents=intents,allowed_mentions=discord.AllowedMentions.none())
        self.pool=None;self.ai_lock=asyncio.Lock();self.proactive_task=None

    async def setup_hook(self):
        self.pool=await asyncpg.create_pool(config.DATABASE_URL,min_size=1,max_size=5,command_timeout=25)
        required={'characters':{'id','image_url','mood','exp','level','owner_id'},
                  'chat_settings':{'unanswered','last_chat_at'},'explorations':{'count'},
                  'important_memories':{'content'}}
        async with self.pool.acquire() as conn:
            for table,columns in required.items():
                rows=await conn.fetch('SELECT column_name FROM information_schema.columns WHERE table_schema=$1 AND table_name=$2','public',table)
                missing=columns-{r['column_name'] for r in rows}
                if missing: raise RuntimeError(f'Database schema mismatch: {table} missing {sorted(missing)}. See build.txt.')
        await self.tree.sync()
        self.proactive_task=asyncio.create_task(self.proactive_loop())
        log.info('Database verified and Discord commands synchronized')

    async def close(self):
        if self.proactive_task:self.proactive_task.cancel()
        if self.pool:await self.pool.close()
        await super().close()

    async def proactive_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                now=datetime.now(TZ)
                if 8<=now.hour<23:
                    rows=await self.pool.fetch('''SELECT user_id,frequency,last_chat_at,last_proactive_at,unanswered
                      FROM chat_settings WHERE proactive_enabled=true LIMIT 100''')
                    for r in rows:
                        last=r['last_chat_at']
                        if not last or (datetime.now(timezone.utc)-last)>timedelta(days=7):continue
                        if r['unanswered']>=5:continue
                        hours={'occasional':12,'normal':6,'active':3}.get(r['frequency'],12)
                        if r['last_proactive_at'] and (datetime.now(timezone.utc)-r['last_proactive_at'])<timedelta(hours=hours):continue
                        c=await self.pool.fetchrow('''SELECT c.* FROM selections s JOIN characters c ON c.id=s.character_id
                           WHERE s.scope_type='dm' AND s.scope_id=$1 AND s.user_id=$1 AND c.status='active' ''',r['user_id'])
                        if not c:continue
                        # Claim before sending, avoiding duplicates across worker iterations.
                        updated=await self.pool.fetchval('''UPDATE chat_settings SET last_proactive_at=now(),unanswered=unanswered+1
                          WHERE user_id=$1 AND proactive_enabled=true RETURNING user_id''',r['user_id'])
                        if not updated:continue
                        try:
                            async with self.ai_lock:
                                msg=await generate(config.GEMINI_API_KEY,config.GEMINI_MODEL,
                                  c['personality']+' '+c['description'],[{'role':'user','content':'請自然地發一句簡短的問候，不要假裝有真實身體。'}])
                            user=await self.fetch_user(r['user_id'])
                            await user.send(embed=make_embed(f'**{c["name"]}**\n{msg}'))
                        except (discord.Forbidden,discord.HTTPException):
                            await self.pool.execute('UPDATE chat_settings SET proactive_enabled=false WHERE user_id=$1',r['user_id'])
                            log.info('Cannot send proactive DM; disabled user=%s',r['user_id'])
                        except Exception:log.exception('Proactive message failed')
            except asyncio.CancelledError:break
            except Exception:log.exception('Proactive loop failed')
            await asyncio.sleep(900)

bot=EchoNest()

async def say(i,text,private=True):
    if i.response.is_done():await i.followup.send(text[:1900],ephemeral=private)
    else:await i.response.send_message(text[:1900],ephemeral=private)

async def selected(i):
    kind,sid=area(i)
    return await bot.pool.fetchrow('''SELECT c.* FROM selections s JOIN characters c ON c.id=s.character_id
       WHERE s.scope_type=$1 AND s.scope_id=$2 AND s.user_id=$3 AND c.status='active'
       AND c.scope_type=$1 AND c.scope_id=$2''',kind,sid,i.user.id)

async def add_item(conn,kind,sid,user,item,count=1):
    await conn.execute('''INSERT INTO inventories(scope_type,scope_id,user_id,item,quantity)
      VALUES($1,$2,$3,$4,$5) ON CONFLICT(scope_type,scope_id,user_id,item)
      DO UPDATE SET quantity=inventories.quantity+$5''',kind,sid,user,item,count)

@bot.tree.command(name='建立角色',description='建立新的 AI 角色')
@app_commands.choices(性格=[app_commands.Choice(name=p,value=p) for p in PERSONALITIES])
async def create(i:discord.Interaction,名稱:str,性格:app_commands.Choice[str],設定:str=''):
    if not 1<=len(名稱)<=40:return await say(i,'名稱長度須為 1～40 字。')
    if 性格.value=='自訂' and len(設定)<100:return await say(i,'自訂性格描述至少 100 字。')
    kind,sid=area(i)
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            cid=await conn.fetchval('''INSERT INTO characters(scope_type,scope_id,owner_id,name,personality,description)
              VALUES($1,$2,$3,$4,$5,$6) RETURNING id''',kind,sid,i.user.id,名稱,性格.value,設定[:2000])
            await conn.execute('''INSERT INTO selections(scope_type,scope_id,user_id,character_id)
              VALUES($1,$2,$3,$4) ON CONFLICT(scope_type,scope_id,user_id)
              DO UPDATE SET character_id=$4''',kind,sid,i.user.id,cid)
    await say(i,f'已建立「{名稱}」（#{cid}），並設為目前角色。')

@bot.tree.command(name='角色列表',description='列出目前區域的角色')
async def list_chars(i:discord.Interaction):
    kind,sid=area(i)
    rows=await bot.pool.fetch('''SELECT id,name,personality FROM characters
      WHERE scope_type=$1 AND scope_id=$2 AND status='active' ORDER BY id DESC LIMIT 50''',kind,sid)
    await say(i,'\n'.join(f'#{r["id"]} {r["name"]}（{r["personality"]}）' for r in rows) or '尚無角色。')

@bot.tree.command(name='切換角色',description='切換目前對話角色')
async def switch(i:discord.Interaction,角色編號:int):
    kind,sid=area(i)
    name=await bot.pool.fetchval('''SELECT name FROM characters WHERE id=$1 AND scope_type=$2
       AND scope_id=$3 AND status='active' ''',角色編號,kind,sid)
    if not name:return await say(i,'找不到角色。')
    await bot.pool.execute('''INSERT INTO selections(scope_type,scope_id,user_id,character_id)
      VALUES($1,$2,$3,$4) ON CONFLICT(scope_type,scope_id,user_id) DO UPDATE SET character_id=$4''',kind,sid,i.user.id,角色編號)
    await say(i,f'已切換至「{name}」。')

class SettingsView(discord.ui.View):
    def __init__(self,cid,owner):
        super().__init__(timeout=180);self.cid=cid;self.owner=owner
    async def interaction_check(self,i):
        if i.user.id!=self.owner:
            await say(i,'只有建立者可以修改。');return False
        return True
    @discord.ui.button(label='修改名稱',style=discord.ButtonStyle.secondary)
    async def rename(self,i,button):await i.response.send_modal(EditModal(self.cid,'name','修改名稱'))
    @discord.ui.button(label='修改性格',style=discord.ButtonStyle.secondary)
    async def personality(self,i,button):await i.response.send_modal(EditModal(self.cid,'personality','修改性格'))
    @discord.ui.button(label='修改圖片',style=discord.ButtonStyle.secondary)
    async def image(self,i,button):await say(i,'使用 /生成角色圖片 產生新圖片，或使用 /上傳角色圖片 上傳圖片。')

class EditModal(discord.ui.Modal):
    def __init__(self,cid,field,title):
        super().__init__(title=title);self.cid=cid;self.field=field
        self.value=discord.ui.TextInput(label=title,max_length=2000 if field=='personality' else 40)
        self.add_item(self.value)
    async def on_submit(self,i):
        value=str(self.value.value).strip()
        if not value:return await say(i,'內容不能為空。')
        kind,sid=area(i)
        sql=f'UPDATE characters SET {self.field}=$1 WHERE id=$2 AND owner_id=$3 AND scope_type=$4 AND scope_id=$5'
        result=await bot.pool.execute(sql,value,self.cid,i.user.id,kind,sid)
        await say(i,'已更新。' if result=='UPDATE 1' else '無權修改。')

@bot.tree.command(name='角色設定',description='透過按鈕編輯角色')
async def settings(i:discord.Interaction,角色編號:int):
    kind,sid=area(i)
    c=await bot.pool.fetchrow('SELECT id,name FROM characters WHERE id=$1 AND owner_id=$2 AND scope_type=$3 AND scope_id=$4',角色編號,i.user.id,kind,sid)
    if not c:return await say(i,'找不到你建立的角色。')
    await i.response.send_message(f'編輯「{c["name"]}」',view=SettingsView(c['id'],i.user.id),ephemeral=True)

@bot.tree.command(name='刪除角色',description='永久刪除自己建立的角色')
async def delete(i:discord.Interaction,角色編號:int,確認:str):
    if 確認!='永久刪除':return await say(i,'請輸入「永久刪除」確認。')
    kind,sid=area(i)
    result=await bot.pool.execute('DELETE FROM characters WHERE id=$1 AND owner_id=$2 AND scope_type=$3 AND scope_id=$4',角色編號,i.user.id,kind,sid)
    if result=='DELETE 1':
        try:await delete_image(角色編號)
        except Exception:log.exception('Storage cleanup failed')
    await say(i,'角色及關聯資料已刪除。' if result=='DELETE 1' else '無權刪除或角色不存在。')

async def fetch_portrait(url):
    if not url or not config.SUPABASE_URL or not url.startswith(config.SUPABASE_URL+'/storage/v1/object/public/'):
        return None
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as session:
        async with session.get(url) as r:
            if r.status==200:
                data=await r.read()
                return data if len(data)<=12*1024*1024 else None

@bot.tree.command(name='角色狀態',description='查看角色狀態圖片卡片')
async def status(i:discord.Interaction):
    await i.response.defer(thinking=True,ephemeral=True)
    c=await selected(i)
    if not c:return await say(i,'請先建立或切換角色。')
    aff=await bot.pool.fetchval('SELECT points FROM affection WHERE character_id=$1 AND user_id=$2',c['id'],i.user.id) or 0
    portrait=await fetch_portrait(c['image_url'])
    card=await asyncio.to_thread(render_card,c['name'],c['personality'],str(c['owner_id']),c['mood'],aff,c['level'],c['exp'],portrait)
    await i.followup.send(file=discord.File(card,filename='character.png'),ephemeral=True)

async def respond(i,message):
    if not 1<=len(message.strip())<=1000:return await say(i,'訊息長度需為 1～1000 字。')
    await i.response.defer(thinking=True)
    c=await selected(i)
    if not c:return await say(i,'請先建立或切換角色。')
    async with bot.ai_lock:
        history=await bot.pool.fetch('''SELECT role,content,user_id FROM chat_messages
          WHERE character_id=$1 ORDER BY id DESC LIMIT 20''',c['id'])
        turns=[{'role':r['role'],'content':(f'玩家 {r["user_id"]}: ' if r['role']=='user' else '')+r['content']} for r in reversed(history)]
        turns.append({'role':'user','content':f'玩家 {i.user.id}: {message}'})
        summary=await bot.pool.fetchval('SELECT summary FROM memories WHERE character_id=$1',c['id']) or ''
        query=message.lower()
        tags=await bot.pool.fetch('SELECT tag,content FROM important_memories WHERE character_id=$1 ORDER BY id DESC LIMIT 50',c['id'])
        matched=[r['content'] for r in tags if r['tag'].lower() in query][:3]
        try:reply=await generate(config.GEMINI_API_KEY,config.GEMINI_MODEL,c['personality']+' '+c['description'],turns,summary+'\n'+'\n'.join(matched))
        except Exception:
            log.exception('Chat failed character=%s',c['id']);return await say(i,'AI 暫時無法回覆。')
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute('INSERT INTO chat_messages(character_id,user_id,role,content) VALUES($1,$2,$3,$4)',c['id'],i.user.id,'user',message)
                await conn.execute('INSERT INTO chat_messages(character_id,user_id,role,content) VALUES($1,NULL,$2,$3)',c['id'],'assistant',reply)
                await conn.execute('''INSERT INTO affection(character_id,user_id,points,last_reward_at,reward_day,reward_count)
                  VALUES($1,$2,1,now(),$3,1) ON CONFLICT(character_id,user_id)
                  DO UPDATE SET points=affection.points+CASE WHEN affection.reward_day=$3 AND affection.reward_count>=20 THEN 0
                  WHEN affection.last_reward_at>now()-interval '60 seconds' THEN 0 ELSE 1 END,
                  reward_count=CASE WHEN affection.reward_day=$3 THEN affection.reward_count+1 ELSE 1 END,
                  reward_day=$3,last_reward_at=now()''',c['id'],i.user.id,day())
                await conn.execute('UPDATE characters SET exp=exp+1,level=1+((exp+1)/100) WHERE id=$1',c['id'])
                if not i.guild_id:
                    await conn.execute('''INSERT INTO chat_settings(user_id,last_chat_at,unanswered) VALUES($1,now(),0)
                      ON CONFLICT(user_id) DO UPDATE SET last_chat_at=now(),unanswered=0''',i.user.id)
                count=await conn.fetchval('SELECT count(*) FROM chat_messages WHERE character_id=$1',c['id'])
                if count>80:
                    old=await conn.fetch('''SELECT id,role,content FROM chat_messages WHERE character_id=$1
                      ORDER BY id ASC LIMIT 20''',c['id'])
                    compact=' '.join(f'{r["role"]}: {r["content"][:100]}' for r in old)
                    await conn.execute('''INSERT INTO memories(character_id,summary) VALUES($1,$2)
                      ON CONFLICT(character_id) DO UPDATE SET summary=right(memories.summary || ' ' || $2,1800),updated_at=now()''',c['id'],compact[:1200])
                    await conn.execute('DELETE FROM chat_messages WHERE id=ANY($1::bigint[])',[r['id'] for r in old])
    for offset in range(0,len(reply),1900):
        await i.followup.send(embed=make_embed(reply[offset:offset+1900]))

@bot.tree.command(name='聊天',description='與目前角色對話')
async def chat(i:discord.Interaction,訊息:str):await respond(i,訊息)

@bot.tree.command(name='聊天設定',description='設定私人訊息主動發言')
@app_commands.choices(頻率=[app_commands.Choice(name=n,value=v) for n,v in [('偶爾','occasional'),('一般','normal'),('活躍','active')]])
async def chat_settings(i:discord.Interaction,主動發言:bool,頻率:app_commands.Choice[str]):
    if i.guild_id:return await say(i,'請在 Bot 私人訊息中設定。')
    await bot.pool.execute('''INSERT INTO chat_settings(user_id,proactive_enabled,frequency,last_chat_at)
      VALUES($1,$2,$3,now()) ON CONFLICT(user_id) DO UPDATE SET proactive_enabled=$2,frequency=$3''',i.user.id,主動發言,頻率.value)
    await say(i,'設定已儲存。主動發言只會在 08:00～23:00（台灣時間）嘗試傳送。')

@bot.tree.command(name='記住', description='為自己的角色加入一則重要記憶')
async def remember(i:discord.Interaction, 標籤:str, 內容:str):
    c = await selected(i)
    if not c:return await say(i,'請先建立或切換角色。')
    if c['owner_id'] != i.user.id:return await say(i,'只有建立者可以編輯角色記憶。')
    if not (1<=len(標籤)<=30 and 1<=len(內容)<=200):
        return await say(i,'標籤 1～30 字、內容 1～200 字。')
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute('INSERT INTO important_memories(character_id,tag,content) VALUES($1,$2,$3)',c['id'],標籤,內容)
            await conn.execute('''DELETE FROM important_memories WHERE character_id=$1 AND id NOT IN
                (SELECT id FROM important_memories WHERE character_id=$1 ORDER BY id DESC LIMIT 50)''',c['id'])
    await say(i,'重要記憶已保存。')

@bot.tree.command(name='記憶列表', description='查看角色的重要記憶')
async def memory_list(i:discord.Interaction):
    c=await selected(i)
    if not c:return await say(i,'請先建立或切換角色。')
    if c['owner_id']!=i.user.id:return await say(i,'只有建立者可以查看完整記憶。')
    rows=await bot.pool.fetch('SELECT id,tag,content FROM important_memories WHERE character_id=$1 ORDER BY id DESC LIMIT 15',c['id'])
    await say(i,'\n'.join(f'#{r["id"]} [{r["tag"]}] {r["content"]}' for r in rows) or '沒有重要記憶。')

@bot.tree.command(name='刪除記憶', description='刪除自己角色的一則重要記憶')
async def forget_memory(i:discord.Interaction, 記憶編號:int):
    c=await selected(i)
    if not c:return await say(i,'請先建立或切換角色。')
    if c['owner_id']!=i.user.id:return await say(i,'只有建立者可以刪除記憶。')
    result=await bot.pool.execute('DELETE FROM important_memories WHERE id=$1 AND character_id=$2',記憶編號,c['id'])
    await say(i,'記憶已刪除。' if result=='DELETE 1' else '找不到這則記憶。')

@bot.tree.command(name='背包',description='查看持有物品')
async def inventory(i:discord.Interaction):
    kind,sid=area(i)
    rows=await bot.pool.fetch('SELECT item,quantity FROM inventories WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND quantity>0 ORDER BY item',kind,sid,i.user.id)
    await say(i,'\n'.join(f'{r["item"]} × {r["quantity"]}' for r in rows) or '背包是空的。')

@bot.tree.command(name='簽到',description='領取每日禮物')
async def checkin(i:discord.Interaction):
    kind,sid=area(i)
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            row=await conn.fetchval('''INSERT INTO checkins(scope_type,scope_id,user_id,day) VALUES($1,$2,$3,$4)
              ON CONFLICT DO NOTHING RETURNING day''',kind,sid,i.user.id,day())
            if row:await add_item(conn,kind,sid,i.user.id,'花束')
    await say(i,'簽到成功，獲得花束 × 1。' if row else '今天已經簽到過。')

@bot.tree.command(name='送禮',description='送禮給目前角色')
async def gift(i:discord.Interaction,禮物:str):
    c=await selected(i)
    if not c:return await say(i,'請先建立或切換角色。')
    if 禮物 not in GIFTS:return await say(i,'未知禮物，請先使用 /背包 查看名稱。')
    kind,sid=area(i)
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            used=await conn.fetchval('''UPDATE inventories SET quantity=quantity-1
              WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND item=$4 AND quantity>0 RETURNING quantity''',kind,sid,i.user.id,禮物)
            if used is not None:
                await conn.execute('''INSERT INTO affection(character_id,user_id,points) VALUES($1,$2,$3)
                  ON CONFLICT(character_id,user_id) DO UPDATE SET points=affection.points+$3''',c['id'],i.user.id,GIFTS[禮物])
                await conn.execute('UPDATE characters SET mood=LEAST(100,mood+2) WHERE id=$1',c['id'])
    await say(i,f'已送出 {禮物}，好感度 +{GIFTS[禮物]}。' if used is not None else '背包沒有這件物品。')

@bot.tree.command(name='探索',description='探索並獲得隨機物品，每日最多五次')
async def explore(i:discord.Interaction):
    kind,sid=area(i)
    item=random.choice(list(GIFTS))
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            count=await conn.fetchval('''INSERT INTO explorations(scope_type,scope_id,user_id,day,count)
              VALUES($1,$2,$3,$4,1) ON CONFLICT(scope_type,scope_id,user_id,day)
              DO UPDATE SET count=explorations.count+1 WHERE explorations.count<5 RETURNING count''',kind,sid,i.user.id,day())
            if count:
                await add_item(conn,kind,sid,i.user.id,item)
                await conn.execute('''INSERT INTO collections(scope_type,scope_id,user_id,key) VALUES($1,$2,$3,$4)
                  ON CONFLICT DO NOTHING''',kind,sid,i.user.id,'初次探索')
    await say(i,f'探索獲得「{item}」。今日 {count}/5 次。' if count else '今天已探索五次，明天再來。')

@bot.tree.command(name='任務',description='領取每日探索任務獎勵')
async def quests(i:discord.Interaction):
    kind,sid=area(i)
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            done=await conn.fetchval('SELECT count FROM explorations WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND day=$4',kind,sid,i.user.id,day())
            if not done:return await say(i,'今日任務：至少探索一次。')
            row=await conn.fetchval('''INSERT INTO quests(scope_type,scope_id,user_id,day,claimed)
              VALUES($1,$2,$3,$4,true) ON CONFLICT DO NOTHING RETURNING day''',kind,sid,i.user.id,day())
            if row:await add_item(conn,kind,sid,i.user.id,'巧克力')
    await say(i,'任務完成，獲得巧克力 × 1。' if row else '今日獎勵已領取。')

@bot.tree.command(name='收藏',description='查看收藏')
async def collection(i:discord.Interaction):
    kind,sid=area(i)
    rows=await bot.pool.fetch('SELECT key FROM collections WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3',kind,sid,i.user.id)
    await say(i,'\n'.join(r['key'] for r in rows) or '尚無收藏。')

IMAGE_STYLES = {
    'anime': 'Japanese anime character portrait, clean line art, expressive eyes, detailed cel shading',
    'realistic': 'Photorealistic cinematic character portrait, natural lighting, detailed skin and hair',
    'illustration': 'High-quality digital character illustration, painterly lighting, rich colors',
    'watercolor': 'Soft watercolor character portrait on textured paper, delicate brushwork',
    'pixel': 'Detailed pixel art character portrait, crisp pixels, retro game aesthetic',
    'chibi': 'Cute chibi character illustration, stylized proportions, colorful and friendly',
    'fantasy': 'Fantasy RPG character concept art, intricate costume and magical atmosphere',
    'comic': 'Modern comic book character art, strong ink lines, dynamic shading',
}

def portrait_prompt(character, appearance, style):
    visual = IMAGE_STYLES.get(style, IMAGE_STYLES['illustration'])
    return (f'Original fictional character, {visual}. '
            f'Single character portrait, no text, no watermark, suitable for all ages. '
            f'Character name: {character["name"][:40]}. '
            f'Personality: {character["personality"][:100]}. '
            f'Appearance: {appearance.strip()[:700]}')

class ImageConfirmView(discord.ui.View):
    def __init__(self, character_id, owner_id, image_bytes, prompt):
        super().__init__(timeout=180)
        self.character_id = character_id
        self.owner_id = owner_id
        self.image_bytes = image_bytes
        self.prompt = prompt

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await say(interaction, '只有建立者可以操作這張圖片。')
            return False
        return True

    @discord.ui.button(label='使用這張圖片', style=discord.ButtonStyle.success)
    async def confirm(self, interaction, button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        kind, sid = area(interaction)
        current = await bot.pool.fetchval('''SELECT id FROM characters WHERE id=$1 AND owner_id=$2
            AND scope_type=$3 AND scope_id=$4 AND status='active' ''',
            self.character_id, interaction.user.id, kind, sid)
        if not current:
            return await say(interaction, '角色不存在或已無權修改。')
        try:
            url = await upload_image(self.character_id, self.image_bytes)
            await bot.pool.execute('UPDATE characters SET image_url=$1 WHERE id=$2 AND owner_id=$3',
                                   url, self.character_id, interaction.user.id)
        except Exception:
            log.exception('Unable to save generated portrait character=%s', self.character_id)
            return await say(interaction, '儲存失敗，請檢查 Storage 設定。')
        self.disable_all_items()
        await interaction.edit_original_response(content='角色圖片已更新。', view=None)
        self.stop()

    @discord.ui.button(label='重新生成', style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction, button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        kind, sid = area(interaction)
        exists = await bot.pool.fetchval('''SELECT id FROM characters WHERE id=$1 AND owner_id=$2
            AND scope_type=$3 AND scope_id=$4 AND status='active' ''',
            self.character_id, interaction.user.id, kind, sid)
        if not exists:
            return await say(interaction, '角色不存在或已無權修改。')
        try:
            async with bot.ai_lock:
                new_image = await create_image(self.prompt)
            new_view = ImageConfirmView(self.character_id, self.owner_id, new_image, self.prompt)
            await interaction.followup.send('已依照相同風格重新生成，確認後才會替換角色圖片。',
                file=discord.File(io.BytesIO(new_image), filename='preview.png'),
                view=new_view, ephemeral=True)
            self.disable_all_items()
            self.stop()
        except ImageProviderError as exc:
            await say(interaction, f'重新生成失敗：{exc}')
        except Exception:
            log.exception('Regenerate image failed')
            await say(interaction, '重新生成失敗，請查看 Render Logs。')

    @discord.ui.button(label='取消', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        self.stop()
        await interaction.response.edit_message(content='已取消，原角色圖片不變。', attachments=[], view=None)

@bot.tree.command(name='生成角色圖片', description='選擇風格，使用 Agnes AI 生成角色圖片')
@app_commands.describe(外觀描述='描述角色的外觀、服裝、髮色等', 風格='選擇圖片風格')
@app_commands.choices(風格=[
    app_commands.Choice(name='日系動漫', value='anime'),
    app_commands.Choice(name='寫實人像', value='realistic'),
    app_commands.Choice(name='精緻插畫', value='illustration'),
    app_commands.Choice(name='水彩手繪', value='watercolor'),
    app_commands.Choice(name='像素藝術', value='pixel'),
    app_commands.Choice(name='Q版可愛', value='chibi'),
    app_commands.Choice(name='奇幻角色', value='fantasy'),
    app_commands.Choice(name='漫畫風格', value='comic'),
])
async def character_image(i:discord.Interaction, 外觀描述:str, 風格:app_commands.Choice[str]):
    if not 1 <= len(外觀描述.strip()) <= 700:
        return await say(i, '外觀描述需為 1～700 字。')
    await i.response.defer(thinking=True, ephemeral=True)
    c = await selected(i)
    if not c:
        return await say(i, '請先建立或切換角色。')
    if c['owner_id'] != i.user.id:
        return await say(i, '只有角色建立者可以生成角色圖片。')
    try:
        prompt = portrait_prompt(c, 外觀描述, 風格.value)
        async with bot.ai_lock:
            data = await create_image(prompt)
        view = ImageConfirmView(c['id'], i.user.id, data, prompt)
        await i.followup.send(f'圖片已生成（{風格.name}）。確認後才會取代原角色圖片。',
                              file=discord.File(io.BytesIO(data), filename='preview.png'),
                              view=view, ephemeral=True)
    except ImageProviderError as exc:
        log.warning('Agnes image generation failed: %s', exc)
        await say(i, f'圖片產生失敗：{exc}')
    except Exception:
        log.exception('Image generation failed character=%s', c['id'])
        await say(i, '圖片產生失敗，請查看 Render Logs。')

@bot.tree.command(name='上傳角色圖片',description='上傳自己的角色圖片')
async def upload_portrait(i:discord.Interaction,圖片:discord.Attachment):
    await i.response.defer(thinking=True,ephemeral=True)
    c=await selected(i)
    if not c:return await say(i,'請先建立或切換角色。')
    if c['owner_id']!=i.user.id:return await say(i,'只有角色建立者可以修改圖片。')
    if not 圖片.content_type or not 圖片.content_type.startswith('image/') or 圖片.size>10*1024*1024:
        return await say(i,'請上傳小於 10MB 的圖片。')
    try:
        from images import validate_image
        data=validate_image(await 圖片.read())
        url=await upload_image(c['id'],data)
        await bot.pool.execute('UPDATE characters SET image_url=$1 WHERE id=$2 AND owner_id=$3',url,c['id'],i.user.id)
        await say(i,'角色圖片已更新。')
    except Exception:
        log.exception('Portrait upload failed');await say(i,'上傳失敗，請檢查 Storage 設定。')

@bot.event
async def on_member_remove(member):
    try:
        rows=await bot.pool.fetch('DELETE FROM characters WHERE scope_type=$1 AND scope_id=$2 AND owner_id=$3 RETURNING id','guild',member.guild.id,member.id)
        for row in rows:
            try:await delete_image(row['id'])
            except Exception:log.exception('Image cleanup failed')
    except Exception:log.exception('Owner cleanup failed')

@bot.tree.error
async def on_error(i,error):
    log.error('Command error: %s',type(error).__name__,exc_info=(type(error),error,error.__traceback__))
    try:await say(i,'操作失敗，請稍後重試。')
    except Exception:log.exception('Cannot report command error')

if __name__=='__main__':
    start();log.info('HTTP health server started')
    if not all((config.DISCORD_TOKEN,config.DATABASE_URL,config.GEMINI_API_KEY)):
        raise RuntimeError('Missing DISCORD_TOKEN, DATABASE_URL or GEMINI_API_KEY')
    bot.run(config.DISCORD_TOKEN,log_handler=None)
