import asyncio
import logging
import os
import random
import uuid
import io
import base64
import urllib.parse
import ipaddress
import socket
from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands
from src.logging_setup import setup
setup()
from src import config
from src.core import Service, PERSONALITIES, GIFTS, QUESTS, scope

log=logging.getLogger('echonest.bot')
intents=discord.Intents.default()
intents.message_content=True
intents.members=True
intents.dm_messages=True

class EchoNest(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!',intents=intents,help_command=None)
        self.service=Service()
    async def setup_hook(self):
        await self.service.start()
        self.service.client=self
        await self.tree.sync()
    async def close(self):
        await self.service.stop()
        await super().close()

bot=EchoNest()

def embed(title,body):
    return discord.Embed(title=title[:256],description=body[:4000],color=0x58738b)

async def send(interaction,text,private=True):
    if interaction.response.is_done():
        return await interaction.followup.send(embed=embed('EchoNest',text),ephemeral=private,allowed_mentions=discord.AllowedMentions.none())
    return await interaction.response.send_message(embed=embed('EchoNest',text),ephemeral=private,allowed_mentions=discord.AllowedMentions.none())

async def chosen(interaction):
    st,sid=scope(interaction)
    return await bot.service.selected(st,sid,str(interaction.user.id))

async def choose_char(interaction,character_name=None):
    st,sid=scope(interaction)
    if interaction.guild and interaction.guild_id is None:return None
    if character_name:
        return await bot.service.db.fetchrow('SELECT * FROM characters WHERE scope_type=$1 AND scope_id=$2 AND name=$3 AND status=$4 ORDER BY created_at DESC LIMIT 1',st,sid,character_name,'active')
    return await chosen(interaction)

class PersonalityModal(discord.ui.Modal,title='自訂角色性格'):
    name=discord.ui.TextInput(label='角色名稱',max_length=60)
    background=discord.ui.TextInput(label='角色背景',style=discord.TextStyle.paragraph,max_length=500)
    speech=discord.ui.TextInput(label='說話方式',style=discord.TextStyle.paragraph,max_length=500)
    traits=discord.ui.TextInput(label='個性與習慣',style=discord.TextStyle.paragraph,max_length=500)
    extra=discord.ui.TextInput(label='其他設定',style=discord.TextStyle.paragraph,max_length=500,required=False)
    async def on_submit(self,interaction):
        text='\n'.join(map(str,(self.background,self.speech,self.traits,self.extra)))
        if len(text.replace('\n','').strip())<100: return await send(interaction,'自訂性格描述至少需要 100 字。')
        st,sid=scope(interaction)
        await bot.service.db.execute('INSERT INTO characters(scope_type,scope_id,owner_id,name,personality,custom_personality) VALUES($1,$2,$3,$4,$5,$6)',st,sid,str(interaction.user.id),str(self.name),'自訂',text)
        await send(interaction,f'已建立角色「{self.name}」。'+ ('\n提醒：本伺服器成員會共用角色記憶，請勿分享敏感資訊。' if st=='guild' else ''))

@bot.tree.command(name='建立角色',description='建立 AI 角色')
@app_commands.describe(名稱='角色名稱',性格='選擇角色性格')
@app_commands.choices(性格=[app_commands.Choice(name=x,value=x) for x in PERSONALITIES])
async def create(interaction:discord.Interaction,名稱:str,性格:app_commands.Choice[str]):
    if len(名稱)>60: return await send(interaction,'角色名稱過長。')
    if 性格.value=='自訂':
        modal=PersonalityModal()
        modal.name.default=名稱
        return await interaction.response.send_modal(modal)
    st,sid=scope(interaction)
    await bot.service.db.execute('INSERT INTO characters(scope_type,scope_id,owner_id,name,personality) VALUES($1,$2,$3,$4,$5)',st,sid,str(interaction.user.id),名稱,性格.value)
    await send(interaction,f'已建立角色「{名稱}」，性格：{性格.value}。'+ ('\n提醒：本伺服器所有成員會共用這個角色的聊天記憶，請勿分享敏感資訊。' if st=='guild' else ''))

@bot.tree.command(name='角色列表',description='查看目前可使用的角色')
async def characters(interaction:discord.Interaction):
    st,sid=scope(interaction)
    rows=await bot.service.list_chars(st,sid)
    await send(interaction,'\n'.join(f'• {x["name"]}（{x["personality"]}）' for x in rows) if rows else '目前沒有角色。')

@bot.tree.command(name='切換角色',description='選擇目前互動的角色')
async def select(interaction:discord.Interaction,角色名稱:str):
    st,sid=scope(interaction)
    ch=await choose_char(interaction,角色名稱)
    if not ch:return await send(interaction,'找不到角色。')
    await bot.service.db.execute('INSERT INTO selected_characters(scope_type,scope_id,user_id,character_id) VALUES($1,$2,$3,$4) ON CONFLICT(scope_type,scope_id,user_id) DO UPDATE SET character_id=excluded.character_id',st,sid,str(interaction.user.id),ch['id'])
    await send(interaction,f'目前選用角色：{ch["name"]}。')

@bot.tree.command(name='角色設定',description='修改自己建立的角色')
async def settings(interaction:discord.Interaction,角色名稱:str,新名稱:str=None,新性格:str=None):
    ch=await choose_char(interaction,角色名稱)
    if not ch:return await send(interaction,'找不到角色。')
    if ch['owner_id']!=str(interaction.user.id):return await send(interaction,'只有建立者能修改角色。')
    if not 新名稱 and not 新性格:return await send(interaction,'請提供新名稱或新性格。')
    if 新性格 and 新性格 not in PERSONALITIES[:-1]:return await send(interaction,'性格不在預設清單中。')
    await bot.service.db.execute('UPDATE characters SET name=$1,personality=$2,custom_personality=CASE WHEN $3::text IS NULL THEN custom_personality ELSE NULL END WHERE id=$4',新名稱 or ch['name'],新性格 or ch['personality'],新性格,ch['id'])
    await send(interaction,'角色設定已更新。')

class DeleteView(discord.ui.View):
    def __init__(self,cid,st,sid,uid):
        super().__init__(timeout=60)
        self.cid,self.st,self.sid,self.uid=cid,st,sid,uid
    @discord.ui.button(label='確認永久刪除',style=discord.ButtonStyle.danger)
    async def confirm(self,interaction:discord.Interaction,button:discord.ui.Button):
        if str(interaction.user.id)!=self.uid:return await send(interaction,'這不是你的操作。')
        ok=await bot.service.delete_character(self.cid,self.st,self.sid,self.uid)
        await send(interaction,'角色已刪除。' if ok else '角色不存在或無權刪除。')
        self.stop()
    @discord.ui.button(label='取消',style=discord.ButtonStyle.secondary)
    async def cancel(self,interaction:discord.Interaction,button:discord.ui.Button):
        await send(interaction,'已取消。')
        self.stop()

@bot.tree.command(name='刪除角色',description='永久刪除自己建立的角色')
async def delete(interaction:discord.Interaction,角色名稱:str):
    ch=await choose_char(interaction,角色名稱)
    if not ch or ch['owner_id']!=str(interaction.user.id):return await send(interaction,'角色不存在或無權刪除。')
    st,sid=scope(interaction)
    await interaction.response.send_message(embed=embed('永久刪除',f'確定永久刪除「{ch["name"]}」？此操作無法復原。'),view=DeleteView(ch['id'],st,sid,str(interaction.user.id)),ephemeral=True)

@bot.tree.command(name='角色狀態',description='查看角色養成數值')
async def status(interaction:discord.Interaction,角色名稱:str=None):
    ch=await choose_char(interaction,角色名稱)
    if not ch:return await send(interaction,'請先使用 /切換角色。')
    affection=await bot.service.db.fetchval('SELECT points FROM affection WHERE character_id=$1 AND user_id=$2',ch['id'],str(interaction.user.id)) or 0
    description=f'角色：{ch["name"]}\n性格：{ch["personality"]}\n心情：{ch["mood"]}/100\n等級：{ch["level"]}\nEXP：{ch["exp"]}\n你的好感度：{affection}'
    await send(interaction,description)

async def do_chat(interaction,text,ch):
    if not ch:return await send(interaction,'請先建立或切換角色。')
    if not text.strip() or len(text)>1000:return await send(interaction,'聊天內容需為 1～1000 字元。')
    st,sid=scope(interaction)
    uid=str(interaction.user.id)
    key=(st,sid,uid)
    now=asyncio.get_running_loop().time()
    if now-bot.service.last_chat.get(key,-1e9)<config.CHAT_COOLDOWN_SECONDS:return await send(interaction,'聊天太頻繁，請稍後再試。')
    bot.service.last_chat[key]=now
    count=await bot.service.db.fetchval('SELECT count FROM daily_chat_counts WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND day=$4',st,sid,uid,bot.service.today()) or 0
    if count>=config.CHAT_DAILY_LIMIT:return await send(interaction,'今日聊天次數已達上限。')
    await interaction.response.defer(thinking=True)
    try:
        answer=await bot.service.enqueue(ch['id'],st,sid,uid,text)
        if not await bot.service.character(ch['id'],st,sid):return await send(interaction,'角色已刪除，聊天取消。')
        await interaction.followup.send(embed=embed(ch['name'],answer),allowed_mentions=discord.AllowedMentions.none())
        await bot.service.save_chat(ch['id'],uid,text,answer,st,sid)
        if st=='dm':
            await bot.service.db.execute('INSERT INTO chat_settings(user_id,last_chat_at,unanswered) VALUES($1,now(),0) ON CONFLICT(user_id) DO UPDATE SET last_chat_at=now(),unanswered=0',uid)
    except Exception:
        log.exception('Chat failed scope=%s character=%s user=%s',st,ch['id'],uid)
        await send(interaction,'聊天暫時失敗，請稍後再試。')

@bot.tree.command(name='聊天',description='與目前角色聊天')
async def chat(interaction:discord.Interaction,內容:str,角色名稱:str=None):
    ch=await choose_char(interaction,角色名稱)
    await do_chat(interaction,內容,ch)

@bot.tree.command(name='聊天設定',description='調整 DM 主動發言')
@app_commands.choices(頻率=[app_commands.Choice(name=x,value=y) for x,y in [('偶爾','rare'),('一般','normal'),('活躍','active')]])
async def chat_config(interaction:discord.Interaction,啟用:bool,頻率:app_commands.Choice[str]=None,安靜開始:int=23,安靜結束:int=8):
    if interaction.guild:return await send(interaction,'主動發言僅支援 DM。')
    uid=str(interaction.user.id)
    if not (0<=安靜開始<=23 and 0<=安靜結束<=23):return await send(interaction,'安靜時間請輸入 0～23。')
    freq=頻率.value if 頻率 else 'rare'
    await bot.service.db.execute('INSERT INTO chat_settings(user_id,enabled,frequency,quiet_start,quiet_end) VALUES($1,$2,$3,$4,$5) ON CONFLICT(user_id) DO UPDATE SET enabled=$2,frequency=$3,quiet_start=$4,quiet_end=$5',uid,啟用,freq,安靜開始,安靜結束)
    await send(interaction,f'主動發言已{"啟用" if 啟用 else "關閉"}；頻率：{freq}。')

@bot.tree.command(name='背包',description='查看持有物品')
async def bag(interaction:discord.Interaction):
    st,sid=scope(interaction)
    rows=await bot.service.db.fetch('SELECT item_id,quantity FROM inventories WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND quantity>0',st,sid,str(interaction.user.id))
    names={v[0]:k for k,v in GIFTS.items()}
    await send(interaction,'\n'.join(f'{names.get(r["item_id"],r["item_id"])} × {r["quantity"]}' for r in rows) if rows else '背包目前沒有物品。')

@bot.tree.command(name='簽到',description='領取每日簽到獎勵')
async def checkin(interaction:discord.Interaction):
    st,sid=scope(interaction)
    ok=await bot.service.checkin(st,sid,str(interaction.user.id))
    await send(interaction,'簽到成功，獲得花束 × 1。' if ok else '今天已經簽到過了。')

@bot.tree.command(name='送禮',description='贈送背包物品給角色')
async def gift(interaction:discord.Interaction,禮物:str,角色名稱:str=None):
    ch=await choose_char(interaction,角色名稱)
    if not ch:return await send(interaction,'請先選擇角色。')
    st,sid=scope(interaction)
    if 禮物 not in GIFTS:return await send(interaction,'請選擇有效的禮物名稱。')
    result=await bot.service.gift(st,sid,str(interaction.user.id),ch['id'],GIFTS[禮物][0])
    await send(interaction,result)

@gift.autocomplete('禮物')
async def gift_autocomplete(interaction:discord.Interaction,current:str):
    return [app_commands.Choice(name=name,value=name) for name in GIFTS if current.lower() in name.lower()][:25]

@bot.tree.command(name='探索',description='進行隨機探索')
async def explore(interaction:discord.Interaction,選擇:int=None):
    ch=await chosen(interaction)
    if not ch:return await send(interaction,'請先選擇角色。')
    uid=str(interaction.user.id)
    async with bot.service.db.acquire() as conn:
        async with conn.transaction():
            row=await conn.fetchrow('SELECT * FROM explorations WHERE character_id=$1 AND user_id=$2 AND status=$3 FOR UPDATE',ch['id'],uid,'active')
            if not row:
                if 選擇 is not None:return await send(interaction,'目前沒有進行中的探索。')
                await conn.execute('INSERT INTO explorations(character_id,user_id) VALUES($1,$2)',ch['id'],uid)
                return await send(interaction,'探索開始：你們來到一條陌生小路。使用 /探索 選擇:1（向左）或 2（向右）。')
            if 選擇 not in (1,2):return await send(interaction,'請輸入選擇 1 或 2。')
            step=row['step']+1
            if step>=3:
                await conn.execute('UPDATE explorations SET step=$1,status=$2 WHERE id=$3',step,'completed',row['id'])
                st,sid=scope(interaction)
                await conn.execute('INSERT INTO inventories(scope_type,scope_id,user_id,item_id,quantity) VALUES($1,$2,$3,$4,1) ON CONFLICT(scope_type,scope_id,user_id,item_id) DO UPDATE SET quantity=inventories.quantity+1',st,sid,uid,'chocolate')
                await conn.execute('INSERT INTO collections(scope_type,scope_id,user_id,collectible_id,character_id) VALUES($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING',st,sid,uid,'first_exploration',ch['id'])
                return await send(interaction,'探索完成！獲得巧克力 × 1，解鎖探索紀念。')
            await conn.execute('UPDATE explorations SET step=$1 WHERE id=$2',step,row['id'])
            await send(interaction,f'你選擇了路線 {選擇}。探索進度 {step}/3，繼續使用 /探索 選擇 1 或 2。')

@bot.tree.command(name='任務',description='查看任務與領取獎勵')
async def quests(interaction:discord.Interaction,領取:str=None):
    st,sid=scope(interaction)
    uid=str(interaction.user.id)
    if not 領取:
        return await send(interaction,'任務：\n'+ '\n'.join(f'{key}：{title}' for key,(title,_) in QUESTS.items())+'\n完成後使用 /任務 領取:<任務ID>。')
    if 領取 not in QUESTS:return await send(interaction,'找不到任務。')
    activity=QUESTS[領取][1]
    if activity=='chat':
        done=await bot.service.db.fetchval('SELECT EXISTS(SELECT 1 FROM chat_messages m JOIN characters c ON c.id=m.character_id WHERE c.scope_type=$1 AND c.scope_id=$2 AND m.user_id=$3 AND m.role=$4)',st,sid,uid,'user')
    elif activity=='gift':
        done=await bot.service.db.fetchval('SELECT EXISTS(SELECT 1 FROM gifts g JOIN characters c ON c.id=g.character_id WHERE c.scope_type=$1 AND c.scope_id=$2 AND g.user_id=$3)',st,sid,uid)
    else:
        done=await bot.service.db.fetchval('SELECT EXISTS(SELECT 1 FROM explorations e JOIN characters c ON c.id=e.character_id WHERE c.scope_type=$1 AND c.scope_id=$2 AND e.user_id=$3 AND e.status=$4)',st,sid,uid,'completed')
    if not done:return await send(interaction,'尚未完成任務。')
    async with bot.service.db.acquire() as conn:
        async with conn.transaction():
            row=await conn.fetchrow('INSERT INTO quest_claims(scope_type,scope_id,user_id,quest_id) VALUES($1,$2,$3,$4) ON CONFLICT DO NOTHING RETURNING quest_id',st,sid,uid,領取)
            if not row:return await send(interaction,'獎勵已領取。')
            await conn.execute('INSERT INTO inventories(scope_type,scope_id,user_id,item_id,quantity) VALUES($1,$2,$3,$4,1) ON CONFLICT(scope_type,scope_id,user_id,item_id) DO UPDATE SET quantity=inventories.quantity+1',st,sid,uid,'cake')
    await send(interaction,'任務獎勵領取成功：蛋糕 × 1。')

@bot.tree.command(name='收藏',description='查看收藏內容')
async def collection(interaction:discord.Interaction):
    st,sid=scope(interaction)
    rows=await bot.service.db.fetch('SELECT collectible_id FROM collections WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3',st,sid,str(interaction.user.id))
    await send(interaction,'已解鎖：\n'+'\n'.join(x['collectible_id'] for x in rows) if rows else '目前沒有收藏。')

class ImageConfirmView(discord.ui.View):
    def __init__(self,uid,cid,st,sid,data):
        super().__init__(timeout=240)
        self.uid,self.cid,self.st,self.sid,self.data=uid,cid,st,sid,data
    @discord.ui.button(label='確認使用圖片',style=discord.ButtonStyle.primary)
    async def confirm(self,interaction:discord.Interaction,button:discord.ui.Button):
        if str(interaction.user.id)!=self.uid:return await send(interaction,'只有建立者可以確認。')
        await interaction.response.defer(ephemeral=True)
        try:
            ch=await bot.service.character(self.cid,self.st,self.sid)
            if not ch or ch['owner_id']!=self.uid:raise ValueError('角色已刪除或沒有權限')
            await bot.service.upload_image(self.cid,self.st,self.sid,self.data)
            await interaction.followup.send('角色圖片已更新。',ephemeral=True)
        except Exception:
            log.exception('Image confirmation failed character=%s',self.cid)
            await interaction.followup.send('圖片更新失敗，請稍後再試。',ephemeral=True)
        self.stop()
    @discord.ui.button(label='取消',style=discord.ButtonStyle.secondary)
    async def cancel(self,interaction:discord.Interaction,button:discord.ui.Button):
        if str(interaction.user.id)!=self.uid:return await send(interaction,'這不是你的操作。')
        await send(interaction,'已取消圖片更新。')
        self.stop()

@bot.tree.command(name='生成角色圖片',description='為角色生成形象')
async def image_character(interaction:discord.Interaction,角色名稱:str=None):
    ch=await choose_char(interaction,角色名稱)
    if not ch:return await send(interaction,'請先選擇角色。')
    if ch['owner_id']!=str(interaction.user.id):return await send(interaction,'只有角色建立者可以修改角色圖片。')
    if not config.AGENS_API_URL or not config.AGENS_API_KEY or not config.SUPABASE_URL or not config.SUPABASE_SERVICE_ROLE_KEY:
        return await send(interaction,'圖片生成尚未設定。請聯絡管理者確認圖片服務與 Storage。')
    await interaction.response.defer(thinking=True,ephemeral=True)
    try:
        raw=await bot.service.generate_image(f'Anime character portrait, clean background, character name: {ch["name"]}. Personality: {ch["personality"]}. {ch["custom_personality"] or ""}')
        file=discord.File(io.BytesIO(raw),filename='preview.png')
        view=ImageConfirmView(str(interaction.user.id),ch['id'],*scope(interaction),raw)
        await interaction.followup.send('圖片預覽：確認後才會更新角色圖片。',file=file,view=view,ephemeral=True)
    except Exception:
        log.exception('Image generation failed character=%s',ch['id'])
        await send(interaction,'圖片生成失敗，請稍後再試。')

@bot.event
async def on_message(message:discord.Message):
    if message.author.bot or message.guild or not message.content.strip():return
    if message.content.startswith('/') or message.content.startswith('!'):return
    st,sid='dm',str(message.author.id)
    ch=await bot.service.selected(st,sid,str(message.author.id))
    if not ch:
        await message.channel.send('請先使用 /建立角色 與 /切換角色。')
        return
    # DM messages cannot be responded to via an Interaction.
    text=message.content
    if len(text)>1000:
        await message.channel.send('訊息請勿超過 1000 字元。')
        return
    key=(st,sid,str(message.author.id))
    now=asyncio.get_running_loop().time()
    if now-bot.service.last_chat.get(key,-1e9)<config.CHAT_COOLDOWN_SECONDS:return
    bot.service.last_chat[key]=now
    count=await bot.service.db.fetchval('SELECT count FROM daily_chat_counts WHERE scope_type=$1 AND scope_id=$2 AND user_id=$3 AND day=$4',st,sid,str(message.author.id),bot.service.today()) or 0
    if count>=config.CHAT_DAILY_LIMIT:
        await message.channel.send('今日聊天次數已達上限。')
        return
    try:
        async with message.channel.typing():
            answer=await bot.service.enqueue(ch['id'],st,sid,str(message.author.id),text)
        if not await bot.service.character(ch['id'],st,sid):return
        await message.channel.send(embed=embed(ch['name'],answer),allowed_mentions=discord.AllowedMentions.none())
        await bot.service.save_chat(ch['id'],str(message.author.id),text,answer,st,sid)
        await bot.service.db.execute('INSERT INTO chat_settings(user_id,last_chat_at,unanswered) VALUES($1,now(),0) ON CONFLICT(user_id) DO UPDATE SET last_chat_at=now(),unanswered=0',str(message.author.id))
    except Exception:
        log.exception('DM chat failed user=%s character=%s',message.author.id,ch['id'])
        await message.channel.send('聊天暫時失敗，請稍後再試。')

@bot.event
async def on_member_remove(member:discord.Member):
    try:
        rows=await bot.service.db.fetch('SELECT id FROM characters WHERE scope_type=$1 AND scope_id=$2 AND owner_id=$3','guild',str(member.guild.id),str(member.id))
        for row in rows:
            await bot.service.delete_character(row['id'],'guild',str(member.guild.id),str(member.id))
    except Exception:
        log.exception('Member departure cleanup failed guild=%s user=%s',member.guild.id,member.id)

@bot.tree.error
async def tree_error(interaction:discord.Interaction,error:app_commands.AppCommandError):
    log.error('Command failed command=%s user=%s type=%s',getattr(interaction.command,'name','unknown'),interaction.user.id,type(error).__name__,exc_info=(type(error),error,error.__traceback__))
    try: await send(interaction,'操作暫時失敗，請稍後再試。')
    except Exception: log.exception('Failed to report command error')

@bot.event
async def on_ready():
    log.info('Bot ready user=%s guilds=%s',bot.user,len(bot.guilds))

if __name__=='__main__':
    bot.run(config.DISCORD_TOKEN,log_handler=None)
