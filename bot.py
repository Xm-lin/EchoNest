import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

import config
from ai import generate

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')
log = logging.getLogger('echonest')
TZ = timezone(timedelta(hours=8))
PERSONALITIES = ['傲嬌', '毒舌', '活潑', '冷淡', '溫柔', '天然呆', '腹黑', '成熟', '自訂']
GIFTS = {'花束': 3, '巧克力': 4, '茶': 2, '書': 5, '玩偶': 6, '餅乾': 2, '明信片': 3, '音樂盒': 8}

def scope(interaction):
    if interaction.guild_id:
        return 'guild', interaction.guild_id
    return 'dm', interaction.user.id

def today():
    return datetime.now(TZ).date()

class EchoNest(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.pool = None
        self.ai_lock = asyncio.Lock()

    async def setup_hook(self):
        self.pool = await asyncpg.create_pool(config.DATABASE_URL, min_size=1, max_size=5, command_timeout=20)
        required = {'characters': {'id','scope_type','scope_id','owner_id','status','created_at'},
                    'chat_settings': {'user_id','proactive_enabled'}, 'selections': {'character_id'}}
        async with self.pool.acquire() as conn:
            for table, cols in required.items():
                actual = {r['column_name'] for r in await conn.fetch('SELECT column_name FROM information_schema.columns WHERE table_schema=$1 AND table_name=$2', 'public', table)}
                if not cols.issubset(actual):
                    raise RuntimeError(f'Database schema mismatch: {table}: missing {sorted(cols-actual)}. Run database/schema.sql on a NEW database.')
        await self.tree.sync()
        log.info('Database verified and Discord commands synchronized')

    async def close(self):
        if self.pool:
            await self.pool.close()
        await super().close()

bot = EchoNest()

async def selected(interaction):
    kind, sid = scope(interaction)
    return await bot.pool.fetchrow('''SELECT c.* FROM selections s JOIN characters c ON c.id=s.character_id
        WHERE s.scope_type=$1 AND s.scope_id=$2 AND s.user_id=$3 AND c.scope_type=$1
        AND c.scope_id=$2 AND c.status='active' ''', kind, sid, interaction.user.id)

async def say(interaction, content, ephemeral=True):
    if interaction.response.is_done():
        await interaction.followup.send(content[:1900], ephemeral=ephemeral, allowed_mentions=discord.AllowedMentions.none())
    else:
        await interaction.response.send_message(content[:1900], ephemeral=ephemeral, allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name='建立角色', description='建立 AI 角色')
@app_commands.describe(名稱='角色名稱', 性格='預設性格或自訂', 設定='角色背景與說話方式')
@app_commands.choices(性格=[app_commands.Choice(name=p, value=p) for p in PERSONALITIES])
async def create(interaction: discord.Interaction, 名稱: str, 性格: app_commands.Choice[str], 設定: str = ''):
    kind, sid = scope(interaction)
    if not 1 <= len(名稱) <= 40:
        return await say(interaction, '角色名稱需為 1～40 字。')
    if 性格.value == '自訂' and len(設定) < 100:
        return await say(interaction, '自訂性格描述至少需要 100 字。')
    row = await bot.pool.fetchrow('''INSERT INTO characters(scope_type,scope_id,owner_id,name,personality,description)
        VALUES($1,$2,$3,$4,$5,$6) RETURNING id''', kind,sid,interaction.user.id,名稱,性格.value,設定[:2000])
    await bot.pool.execute('''INSERT INTO selections(scope_type,scope_id,user_id,character_id)
        VALUES($1,$2,$3,$4) ON CONFLICT(scope_type,scope_id,user_id) DO UPDATE SET character_id=EXCLUDED.character_id''', kind,sid,interaction.user.id,row['id'])
    await say(interaction, f'已建立角色「{名稱}」，編號 {row["id"]}，並設為目前角色。')

@bot.tree.command(name='角色列表', description='查看目前範圍的角色')
async def list_characters(interaction: discord.Interaction):
    kind,sid = scope(interaction)
    rows = await bot.pool.fetch('SELECT id,name,personality FROM characters WHERE scope_type=$1 AND scope_id=$2 AND status=$3 ORDER BY id DESC LIMIT 50',kind,sid,'active')
    await say(interaction, '\n'.join(f'#{r["id"]} {r["name"]}（{r["personality"]}）' for r in rows) or '目前沒有角色。')

@bot.tree.command(name='切換角色', description='切換目前角色')
async def switch(interaction: discord.Interaction, 角色編號: int):
    kind,sid = scope(interaction)
    row = await bot.pool.fetchrow('SELECT name FROM characters WHERE id=$1 AND scope_type=$2 AND scope_id=$3 AND status=$4',角色編號,kind,sid,'active')
    if not row: return await say(interaction, '找不到這個範圍內的角色。')
    await bot.pool.execute('''INSERT INTO selections(scope_type,scope_id,user_id,character_id)
      VALUES($1,$2,$3,$4) ON CONFLICT(scope_type,scope_id,user_id) DO UPDATE SET character_id=EXCLUDED.character_id''',kind,sid,interaction.user.id,角色編號)
    await say(interaction, f'已切換到「{row["name"]}」。')

@bot.tree.command(name='角色設定', description='修改自己建立的角色')
async def settings(interaction: discord.Interaction, 角色編號: int, 新名稱: str, 新設定: str = ''):
    kind,sid = scope(interaction)
    if not 1 <= len(新名稱) <= 40: return await say(interaction, '名稱需為 1～40 字。')
    result = await bot.pool.execute('''UPDATE characters SET name=$1,description=$2 WHERE id=$3 AND scope_type=$4 AND scope_id=$5 AND owner_id=$6 AND status='active' ''',新名稱,新設定[:2000],角色編號,kind,sid,interaction.user.id)
    await say(interaction, '角色已更新。' if result == 'UPDATE 1' else '角色不存在，或你不是建立者。')

@bot.tree.command(name='刪除角色', description='永久刪除自己建立的角色')
async def delete(interaction: discord.Interaction, 角色編號: int, 確認: str):
    if 確認 != '永久刪除': return await say(interaction, '請在確認欄輸入「永久刪除」。')
    kind,sid = scope(interaction)
    result = await bot.pool.execute('DELETE FROM characters WHERE id=$1 AND scope_type=$2 AND scope_id=$3 AND owner_id=$4',角色編號,kind,sid,interaction.user.id)
    await say(interaction, '角色與關聯資料已刪除。' if result == 'DELETE 1' else '角色不存在，或你不是建立者。')

@bot.tree.command(name='角色狀態', description='查看角色心情、等級及好感度')
async def status(interaction: discord.Interaction):
    c = await selected(interaction)
    if not c: return await say(interaction,'請先建立或切換角色。')
    aff = await bot.pool.fetchval('SELECT points FROM affection WHERE character_id=$1 AND user_id=$2',c['id'],interaction.user.id) or 0
    await say(interaction,f'{c["name"]}\n性格：{c["personality"]}\n心情：{c["mood"]}/100\n等級：{c["level"]}\nEXP：{c["exp"]}\n你的好感度：{aff}')

async def chat_reply(interaction, message):
    if not message.strip() or len(message)>1000:
        return await say(interaction,'訊息需為 1～1000 字。')
    await interaction.response.defer(thinking=True)
    c = await selected(interaction)
    if not c: return await say(interaction,'請先建立或切換角色。')
    async with bot.ai_lock:
        history = await bot.pool.fetch('SELECT role,content,user_id FROM chat_messages WHERE character_id=$1 ORDER BY id DESC LIMIT 19',c['id'])
        turns = [{'role':r['role'],'content': (f'玩家 {r["user_id"]}: ' if r['role']=='user' else '')+r['content']} for r in reversed(history)]
        turns.append({'role':'user','content':f'玩家 {interaction.user.id}: {message}'})
        summary = await bot.pool.fetchval('SELECT summary FROM memories WHERE character_id=$1',c['id']) or ''
        try:
            reply = await generate(config.GEMINI_API_KEY,config.GEMINI_MODEL,c['personality']+' '+c['description'],turns,summary)
        except Exception:
            log.exception('Gemini chat failed character=%s',c['id'])
            return await say(interaction,'AI 暫時無法回覆，請稍後再試。')
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute('INSERT INTO chat_messages(character_id,user_id,role,content) VALUES($1,$2,$3,$4)',c['id'],interaction.user.id,'user',message)
                await conn.execute('INSERT INTO chat_messages(character_id,user_id,role,content) VALUES($1,$2,$3,$4)',c['id'],None,'assistant',reply)
                await conn.execute('''INSERT INTO affection(character_id,user_id,points) VALUES($1,$2,1)
                    ON CONFLICT(character_id,user_id) DO UPDATE SET points=affection.points+1''',c['id'],interaction.user.id)
                await conn.execute('UPDATE characters SET exp=exp+1,level=1+(exp+1)/100 WHERE id=$1',c['id'])
                if not interaction.guild_id:
                    await conn.execute('''INSERT INTO chat_settings(user_id,last_chat_at) VALUES($1,now())
                    ON CONFLICT(user_id) DO UPDATE SET last_chat_at=now()''',interaction.user.id)
    for i in range(0,len(reply),1900):
        await interaction.followup.send(embed=discord.Embed(description=reply[i:i+1900]),allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name='聊天', description='與目前角色聊天')
async def chat(interaction: discord.Interaction, 訊息: str):
    await chat_reply(interaction,訊息)

@bot.tree.command(name='聊天設定', description='設定 DM 主動發言')
@app_commands.choices(頻率=[app_commands.Choice(name=n,value=v) for n,v in [('偶爾','occasional'),('一般','normal'),('活躍','active')]])
async def chat_settings(interaction: discord.Interaction, 主動發言: bool, 頻率: app_commands.Choice[str]):
    if interaction.guild_id: return await say(interaction,'請在私人訊息中設定主動發言。')
    await bot.pool.execute('''INSERT INTO chat_settings(user_id,proactive_enabled,frequency) VALUES($1,$2,$3)
        ON CONFLICT(user_id) DO UPDATE SET proactive_enabled=$2,frequency=$3''',interaction.user.id,主動發言,頻率.value)
    await say(interaction,'設定已儲存。注意：主動訊息排程尚未啟用。')

@bot.tree.command(name='背包', description='查看物品')
async def inventory(interaction: discord.Interaction):
    kind,sid=scope(interaction)
    rows=await bot.pool.fetch('SELECT item,quantity FROM inventories WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND quantity>0 ORDER BY item',kind,sid,interaction.user.id)
    await say(interaction,'\n'.join(f'{r["item"]} × {r["quantity"]}' for r in rows) or '背包目前是空的。')

@bot.tree.command(name='簽到', description='領取每日禮物')
async def checkin(interaction: discord.Interaction):
    kind,sid=scope(interaction)
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            row=await conn.fetchrow('''INSERT INTO checkins(scope_type,scope_id,user_id,day) VALUES($1,$2,$3,$4)
                ON CONFLICT DO NOTHING RETURNING day''',kind,sid,interaction.user.id,today())
            if row:
                await conn.execute('''INSERT INTO inventories(scope_type,scope_id,user_id,item,quantity) VALUES($1,$2,$3,$4,1)
                    ON CONFLICT(scope_type,scope_id,user_id,item) DO UPDATE SET quantity=inventories.quantity+1''',kind,sid,interaction.user.id,'花束')
    await say(interaction,'簽到成功！獲得花束 × 1。' if row else '今天已經簽到過了。')

@bot.tree.command(name='送禮', description='送禮給目前角色')
@app_commands.choices(禮物=[app_commands.Choice(name=x,value=x) for x in GIFTS])
async def gift(interaction: discord.Interaction, 禮物: app_commands.Choice[str]):
    c=await selected(interaction)
    if not c:return await say(interaction,'請先建立或切換角色。')
    kind,sid=scope(interaction)
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            used=await conn.fetchrow('''UPDATE inventories SET quantity=quantity-1
                WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND item=$4 AND quantity>0 RETURNING quantity''',kind,sid,interaction.user.id,禮物.value)
            if used:
                await conn.execute('''INSERT INTO affection(character_id,user_id,points) VALUES($1,$2,$3)
                    ON CONFLICT(character_id,user_id) DO UPDATE SET points=affection.points+$3''',c['id'],interaction.user.id,GIFTS[禮物.value])
                await conn.execute('UPDATE characters SET mood=LEAST(100,mood+2) WHERE id=$1',c['id'])
    await say(interaction,f'已送出{禮物.value}，好感度 +{GIFTS[禮物.value]}。' if used else '背包沒有這項禮物。')

@bot.tree.command(name='探索', description='進行一次隨機探索')
async def explore(interaction: discord.Interaction):
    kind,sid=scope(interaction)
    item=random.choice(list(GIFTS))
    await bot.pool.execute('''INSERT INTO inventories(scope_type,scope_id,user_id,item,quantity) VALUES($1,$2,$3,$4,1)
        ON CONFLICT(scope_type,scope_id,user_id,item) DO UPDATE SET quantity=inventories.quantity+1''',kind,sid,interaction.user.id,item)
    await bot.pool.execute('''INSERT INTO collections(scope_type,scope_id,user_id,key) VALUES($1,$2,$3,$4)
        ON CONFLICT DO NOTHING''',kind,sid,interaction.user.id,'初次探索')
    await say(interaction,f'你在探索途中找到「{item}」！已放入背包。')

@bot.tree.command(name='任務', description='領取每日探索任務獎勵')
async def quests(interaction: discord.Interaction):
    kind,sid=scope(interaction)
    async with bot.pool.acquire() as conn:
        async with conn.transaction():
            explored=await conn.fetchval('SELECT 1 FROM collections WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND key=$4',kind,sid,interaction.user.id,'初次探索')
            if not explored:return await say(interaction,'任務：完成一次探索。')
            row=await conn.fetchrow('''INSERT INTO quests(scope_type,scope_id,user_id,day,claimed)
                VALUES($1,$2,$3,$4,true) ON CONFLICT DO NOTHING RETURNING day''',kind,sid,interaction.user.id,today())
            if row:
                await conn.execute('''INSERT INTO inventories(scope_type,scope_id,user_id,item,quantity) VALUES($1,$2,$3,$4,1)
                    ON CONFLICT(scope_type,scope_id,user_id,item) DO UPDATE SET quantity=inventories.quantity+1''',kind,sid,interaction.user.id,'巧克力')
    await say(interaction,'任務完成，獲得巧克力 × 1。' if row else '今天的任務獎勵已領取。')

@bot.tree.command(name='收藏', description='查看收藏紀錄')
async def collections(interaction: discord.Interaction):
    kind,sid=scope(interaction)
    rows=await bot.pool.fetch('SELECT key FROM collections WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3',kind,sid,interaction.user.id)
    await say(interaction,'\n'.join(r['key'] for r in rows) or '尚無收藏。')

@bot.tree.command(name='生成角色圖片', description='生成角色圖片')
async def character_image(interaction: discord.Interaction):
    await say(interaction,'圖片生成服務尚未接入；不會扣除任何資源。')

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild or not message.content.strip(): return
    # DM messages can directly talk to the selected character.
    class DMInteraction:
        def __init__(self,m):
            self.user=m.author;self.guild_id=None;self.response=None
    # Discord Interaction responses cannot be reused for raw DM events.
    kind,sid='dm',message.author.id
    c=await bot.pool.fetchrow('''SELECT c.* FROM selections s JOIN characters c ON c.id=s.character_id
        WHERE s.scope_type='dm' AND s.scope_id=$1 AND s.user_id=$1 AND c.status='active' ''',sid)
    if not c:
        await message.channel.send('請先使用 /建立角色 或 /切換角色。');return
    if len(message.content)>1000:
        await message.channel.send('訊息最多 1000 字。');return
    async with bot.ai_lock:
        history=await bot.pool.fetch('SELECT role,content,user_id FROM chat_messages WHERE character_id=$1 ORDER BY id DESC LIMIT 19',c['id'])
        turns=[{'role':r['role'],'content':r['content']} for r in reversed(history)]
        turns.append({'role':'user','content':message.content})
        try:
            reply=await generate(config.GEMINI_API_KEY,config.GEMINI_MODEL,c['personality']+' '+c['description'],turns)
        except Exception:
            log.exception('DM generation failed character=%s',c['id']);await message.channel.send('AI 暫時無法回覆。');return
        async with bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute('INSERT INTO chat_messages(character_id,user_id,role,content) VALUES($1,$2,$3,$4)',c['id'],sid,'user',message.content)
                await conn.execute('INSERT INTO chat_messages(character_id,user_id,role,content) VALUES($1,$2,$3,$4)',c['id'],None,'assistant',reply)
                await conn.execute('''INSERT INTO affection(character_id,user_id,points) VALUES($1,$2,1)
                    ON CONFLICT(character_id,user_id) DO UPDATE SET points=affection.points+1''',c['id'],sid)
                await conn.execute('UPDATE characters SET exp=exp+1 WHERE id=$1',c['id'])
                await conn.execute('''INSERT INTO chat_settings(user_id,last_chat_at) VALUES($1,now())
                    ON CONFLICT(user_id) DO UPDATE SET last_chat_at=now()''',sid)
    for i in range(0,len(reply),1900):
        await message.channel.send(embed=discord.Embed(description=reply[i:i+1900]))

@bot.event
async def on_member_remove(member: discord.Member):
    try:
        await bot.pool.execute('DELETE FROM characters WHERE scope_type=$1 AND scope_id=$2 AND owner_id=$3','guild',member.guild.id,member.id)
    except Exception:
        log.exception('Guild owner cleanup failed guild=%s',member.guild.id)

@bot.tree.error
async def on_app_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    log.error('Slash command failed: %s',error,exc_info=(type(error),error,error.__traceback__))
    try: await say(interaction,'操作失敗，請稍後再試。')
    except Exception: log.exception('Unable to report interaction failure')

if __name__=='__main__':
    bot.run(config.DISCORD_TOKEN,log_handler=None)
