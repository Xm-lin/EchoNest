"""Deterministic, low-API-cost EchoNest progression and story events."""
import random
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
EVENTS = [
    {'title':'雨天的邀請','story':'突然下起雨，{name}站在屋簷下，似乎在等你說些什麼。','choices':[('陪對方等雨停',3,12,'雨天車票','你們聊起雨聲，這段小小的回憶被保存下來。'),('找一把傘',2,15,'紙傘吊飾','你找到了一把傘，對方默默記住了這份細心。'),('聊聊今天的事',1,10,'雨滴書籤','一段平凡的對話，意外變成值得記住的時刻。')]},
    {'title':'神祕紙條','story':'{name}撿到一張沒有署名的紙條，上面只有一句「你會怎麼選？」','choices':[('一起解開謎題',3,14,'神祕紙條','你們合作找出了紙條背後的小祕密。'),('猜猜寫信的人',1,12,'鉛筆速寫','你們的猜測讓整件事變得有趣。'),('把紙條收好',2,10,'折角便條','有些謎題不急著解開。')]},
    {'title':'意外的小禮物','story':'{name}拿出一個包裝不太整齊的小盒子，問你覺得裡面是什麼。','choices':[('認真猜一猜',2,13,'緞帶','猜測的過程比答案更令人開心。'),('先謝謝對方',3,11,'小禮盒','一份心意被好好接住了。'),('反過來出題',1,15,'問號徽章','你們開始了一場即興猜謎遊戲。')]},
    {'title':'午後的岔路','story':'走到岔路口時，{name}提議今天走一條沒走過的路。','choices':[('走安靜的小路',2,12,'落葉標本','你們發現一處安靜的風景。'),('去熱鬧的街道',1,15,'街角票根','沿途的聲音和風景成了新故事。'),('交給對方決定',3,10,'路線地圖','這次換對方帶路，你看見不同的世界。')]},
    {'title':'突然的挑戰','story':'{name}提出一個小挑戰：用一句話形容今天的心情。','choices':[('說一件開心的事',2,13,'笑臉貼紙','你們交換了今天值得開心的片刻。'),('說一件新發現',3,14,'發現筆記','對方很喜歡你注意到的細節。'),('說今天很普通',1,11,'日常紀錄','原來平凡的一天也有值得收藏的部分。')]},
    {'title':'書架上的故事','story':'{name}從書架抽出一本舊書，夾頁裡藏著一張照片。','choices':[('聽對方說故事',3,13,'舊照片','照片背後的故事成了共同的回憶。'),('分享自己的故事',2,15,'故事卡片','兩個不同的故事有了意外的連結。'),('一起找下一頁',1,12,'書頁碎片','你們在書中找到了新的線索。')]},
]
QUESTS = {'chat':('聊聊近況',3),'explore':('探索新故事',2),'gift':('送出一份心意',1)}


def today():
    return datetime.now(TZ).date().isoformat()


def week():
    d = datetime.now(TZ).date()
    return (d - timedelta(days=d.weekday())).isoformat()


def relationship(affection):
    if affection >= 80: return '知己'
    if affection >= 55: return '信任'
    if affection >= 25: return '熟悉'
    return '初識'


def progress(conn, scope, uid, cid, action):
    """Call within an existing transaction. Auto-award each weekly quest once."""
    if action not in QUESTS:
        return []
    w = week()
    row = conn.execute('''INSERT INTO bot_quest_progress(scope,user_id,character_id,week,action,count)
        VALUES(%s,%s,%s,%s,%s,1)
        ON CONFLICT(scope,user_id,character_id,week,action)
        DO UPDATE SET count=bot_quest_progress.count+1 RETURNING count''',
        (scope,uid,cid,w,action)).fetchone()
    label, target = QUESTS[action]
    if row['count'] != target:
        return []
    inserted = conn.execute('''INSERT INTO bot_quest_rewards(scope,user_id,character_id,week,action)
        VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING action''',
        (scope,uid,cid,w,action)).fetchone()
    if not inserted:
        return []
    conn.execute('UPDATE bot_profiles SET exp=exp+35 WHERE scope=%s AND user_id=%s AND character_id=%s', (scope,uid,cid))
    conn.execute('''INSERT INTO bot_inventory(scope,user_id,item,quantity) VALUES(%s,%s,'禮物盒',1)
        ON CONFLICT(scope,user_id,item) DO UPDATE SET quantity=bot_inventory.quantity+1''',(scope,uid))
    return [f'🏅 完成每週任務「{label}」：EXP +35、禮物盒 ×1']


def start_event(db, scope, uid, cid, name):
    """Pending event lasts 20 min; only completed events count against daily limit."""
    with db.transaction() as conn:
        conn.execute('SELECT id FROM bot_characters WHERE id=%s AND scope=%s FOR SHARE',(cid,scope))
        pending = conn.execute('''SELECT id,event_index FROM bot_story_pending WHERE scope=%s AND user_id=%s
            AND character_id=%s AND expires_at>NOW() FOR UPDATE''',(scope,uid,cid)).fetchone()
        if pending:
            index = pending['event_index']
            return {'id':pending['id'],'event':EVENTS[index], 'remaining':None, 'existing':True}
        count = conn.execute('''SELECT COUNT(*) AS n FROM bot_story_history
            WHERE scope=%s AND user_id=%s AND character_id=%s AND day=%s''',(scope,uid,cid,today())).fetchone()['n']
        if count >= 3:
            return None
        index = random.randrange(len(EVENTS))
        row = conn.execute('''INSERT INTO bot_story_pending(scope,user_id,character_id,event_index,expires_at)
            VALUES(%s,%s,%s,%s,NOW()+INTERVAL '20 minutes')
            ON CONFLICT(scope,user_id,character_id) DO UPDATE
            SET event_index=EXCLUDED.event_index,expires_at=EXCLUDED.expires_at
            RETURNING id''',(scope,uid,cid,index)).fetchone()
        return {'id':row['id'],'event':EVENTS[index], 'remaining':2-count,'existing':False}


def finish_event(db, scope, uid, cid, event_id, choice):
    with db.transaction() as conn:
        pending = conn.execute('''SELECT id,event_index FROM bot_story_pending
            WHERE scope=%s AND user_id=%s AND character_id=%s AND id=%s AND expires_at>NOW() FOR UPDATE''',
            (scope,uid,cid,event_id)).fetchone()
        if not pending:
            return None
        if choice not in (0,1,2):
            return None
        used = conn.execute('''SELECT COUNT(*) AS n FROM bot_story_history
            WHERE scope=%s AND user_id=%s AND character_id=%s AND day=%s''',(scope,uid,cid,today())).fetchone()['n']
        if used >= 3:
            return None
        event = EVENTS[pending['event_index']]
        label, delta, xp, souvenir, ending = event['choices'][choice]
        conn.execute('''INSERT INTO bot_profiles(scope,user_id,character_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING''',(scope,uid,cid))
        conn.execute('''UPDATE bot_profiles SET affection=LEAST(100,affection+%s),exp=exp+%s
            WHERE scope=%s AND user_id=%s AND character_id=%s''',(delta,xp,scope,uid,cid))
        conn.execute('''INSERT INTO bot_collectibles(scope,user_id,character_id,item,obtained_at)
            VALUES(%s,%s,%s,%s,NOW()) ON CONFLICT DO NOTHING''',(scope,uid,cid,souvenir))
        conn.execute('''INSERT INTO bot_story_history(scope,user_id,character_id,day,event_title,choice,ending)
            VALUES(%s,%s,%s,%s,%s,%s,%s)''',(scope,uid,cid,today(),event['title'],label,ending))
        conn.execute('DELETE FROM bot_story_pending WHERE id=%s',(event_id,))
        rewards = progress(conn,scope,uid,cid,'explore')
        return {'ending':ending,'delta':delta,'xp':xp,'souvenir':souvenir,'rewards':rewards}
