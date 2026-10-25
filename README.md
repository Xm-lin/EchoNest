# EchoNest v5 — Discord 角色養成遊戲

基於 v4 升級，保留既有 Discord / Gemini / Supabase 架構，新增故事探索、收藏、每週任務與大圖角色檔案。**不需重建資料庫、不需清空舊角色。**

## 遊戲玩法

1. `/建立角色 [圖片]`：選擇個性、填入背景、上傳角色圖（可選）。
2. `/角色狀態`：先顯示**大張角色圖片**，下一則私密訊息顯示名稱、關係階段、心情、好感度、等級、EXP 條。
3. `/聊天 內容`：Gemini 角色對話及好感度評分，對話記憶依角色及使用者隔離；60 秒內至多一次 EXP / 好感度結算。
4. `/探索`：六種故事事件，每次三個不同選擇；獲得 EXP、好感度與角色專屬紀念品。每個角色每天最多完成 3 次（台灣時間）；未完成事件可在 20 分鐘內再次 `/探索`。
5. `/任務`：每週三項目標（聊天結算 3 次、探索 2 次、送禮 1 次），達成時**自動**領取 EXP +35 與禮物盒 ×1；每週一重置，沒有連續登入懲罰。
6. `/收藏`：查看紀念品與最近五段故事回憶，收藏以使用者及角色分開保存。
7. `/簽到`、`/背包`、`/送禮`：保留 v4 道具系統。
8. `/角色列表`、`/切換角色`、`/角色設定`、`/刪除角色`：保留原功能。

總計 **13 個全域 Slash Commands**。角色關係階段依好感度分為初識、熟悉、信任、知己；角色互動不需要生成圖片 API，僅上傳使用者提供的圖片。故事事件使用預先編寫的文本，不額外消耗 Gemini API 額度。

## 部署到 Render

1. 先備份 Supabase 資料庫。把 ZIP **內的檔案**上傳至 GitHub Repo 根目錄（包括新增 `game.py`）。
2. Render → EchoNest → Environment，設定：

```dotenv
DISCORD_TOKEN=...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=postgresql://...
SUPABASE_URL=https://你的專案.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=characters
```

3. Supabase Storage 建立名稱為 `characters` 的 **Public** bucket。`SUPABASE_URL` 請填專案根網址，**不要附 `/rest/v1`**（程式也有防呆修正）。
4. Render → Manual Deploy → Deploy latest commit。Logs 應出現 `Synced 13 global slash commands`。
5. Discord 執行 `/建立角色`（可先不附圖測試），再測 `/角色狀態`、`/探索`、`/任務`、`/收藏`。

新資料表會由 `database.py` 的 `CREATE TABLE IF NOT EXISTS` 自動建立；舊有角色與聊天資料不會被刪除。新功能需要 Supabase DB 帳號具有建立資料表的權限。

## 測試

```bash
python tests/test_static.py
python tests/test_game.py
python -m compileall -q bot.py database.py game.py
```

這些是本地靜態與內容測試，**不等於已連線 Discord、Supabase、Gemini 完成端對端測試**。

## 注意事項

- 圖片會存到 Public Storage，請勿上傳私密圖片。角色圖片的 `set_image` 會受 Discord 顯示尺寸影響；Discord Embed 無法將圖片排在同一張資訊卡的標題上方，因此本版以**圖片訊息在前、資訊卡在後**實現順序。
- 不同安裝方式的 Guild/User Install 在 guild 內仍沿用原始 `scope_of` 實作，未實現完整的兩種安裝隔離。
- 探索故事是六組可重複的固定事件，並非 AI 即時生成的無限劇情；未來可在 `game.py` 增加事件庫。
