# EchoNest v8 — Discord AI 角色機器人

沿用 v7 的角色、資料庫與 Pillow 角色卡，新增三項功能：

1. **`/送禮` 背包選單**：顯示持有的禮物及數量，選擇後確認才扣除道具；送出後顯示剩餘數量。
2. **`/聊天` Webhook 角色頭像**：在具備 `Manage Webhooks` 權限的伺服器文字頻道，以角色名稱與 Supabase 角色圖片作為訊息左側的圓形頭像。無權限、私訊、無圖片時回退 Embed。Webhook 重複使用，不會每次建立。
3. **`/生成角色圖片 描述`**：呼叫外部生圖 API，私密預覽，按「使用這張角色圖片」才上傳 Supabase 並替換；可取消。限制 5MB、僅角色建立者或管理員可修改。

共有 **14 個 Slash Commands**。保留建立角色、角色列表、切換角色、角色設定、刪除角色、角色狀態、聊天、背包、簽到、送禮、探索、任務、收藏等既有功能。

## Render 環境變數

保留 v7 原本的 `DISCORD_TOKEN`、`GEMINI_API_KEY`、`GEMINI_MODEL`、`DATABASE_URL`、`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、`SUPABASE_STORAGE_BUCKET`。

選用圖片生成服務時，額外設定：

```dotenv
IMAGE_API_KEY=你的圖片服務金鑰
IMAGE_API_URL=https://你的圖片服務提供的完整圖片生成端點
IMAGE_MODEL=供應商提供的模型ID
```

也支援 `AGNES_API_KEY` 作為金鑰變數名稱。**注意：Agnes 是否支援此 OpenAI 相容端點及模型名稱，必須依實際供應商文件確認。** 本專案未內建或假設任何未驗證的 Agnes API URL。API 預期接受 JSON `{model,prompt,n}`，回傳 `data[0].b64_json` 或 `data[0].url` 等常見格式；不相容時需調整 `generate_character_image()`。未設定 API 時，其他 13 個指令仍可正常使用。

## Discord 權限

Webhook 需要機器人在目標文字頻道擁有 **Manage Webhooks**。請確保 Supabase `characters` bucket 是 Public，且角色已有上傳圖片。私訊和無權限頻道會退回原本的 Embed，並不會修改 Bot 帳號本身的頭像。

## 部署與測試

把 ZIP 內檔案放到 GitHub 專案根目錄，Render 部署最新 commit。保留現有 Supabase 資料庫，程式會沿用既有資料表。

```bash
python tests/test_static.py
python tests/test_game.py
python -m compileall -q bot.py character_card.py database.py game.py
```

這些是本機靜態／遊戲測試，**未在你的 Discord、Render、Supabase 或 Agnes 帳號實際進行端對端測試**。

---

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

- 圖片會存到 Public Storage，請勿上傳私密圖片。`/角色狀態` 會以 Pillow 即時合成一張 1000×1440 PNG：上方角色大圖，下方名稱、關係階段、心情、等級、好感度及經驗值進度條。無圖片時顯示預設背景，不需要任何圖片生成 API。Docker 會安裝 Noto CJK 字型以正確顯示繁體中文。
- 不同安裝方式的 Guild/User Install 在 guild 內仍沿用原始 `scope_of` 實作，未實現完整的兩種安裝隔離。
- 探索故事是六組可重複的固定事件，並非 AI 即時生成的無限劇情；未來可在 `game.py` 增加事件庫。

## 角色狀態圖片卡

`character_card.py` 使用 Pillow 將 Supabase Storage 的角色圖片與 PostgreSQL 數值合成 PNG，直接傳到 Discord，不需 Gemini 圖片 API，也不需新增資料表。圖片下載失敗時改用預設背景。若修改 Dockerfile，需重新部署以安裝中文字型。


## v5 角色卡視覺改版（新版）

`/角色狀態` 會使用 `character_card.py` 的 Pillow 模板產生 1000×1440 PNG：上方為玩家實際上傳的角色圖片，下方為深紫色玻璃質感資訊區、關係階段、心情、個性、等級、經驗值與五顆好感度愛心。沒有上傳圖片時顯示抽象預設圖案，不會冒用其他角色立繪。

- 不需要 Gemini 生圖 API、額外 API Key、或新增資料表。
- Render Docker 已安裝 `fonts-noto-cjk`，可以顯示繁體中文。
- 角色圖由 Supabase Storage 讀取；其他數值由 PostgreSQL 讀取，每次呼叫即時渲染。
- 模板本身不包含示範用角色圖片；請在 Discord 上傳你自己的圖片。

### 簡約角色卡（無 AI 生成）
`/角色狀態` 使用 `character_card.py` 的 Pillow 模板，直接合成使用者上傳的角色圖片、角色名稱、關係階段、心情、個性、等級、EXP 和好感度。沒有邊框、裝飾性英文或 AI 圖片生成；無角色圖片時使用簡單的中性色佔位背景。Render Dockerfile 已安裝 Noto CJK 字型。


## 角色卡固定模板（v7）

- `/角色狀態` 使用 Pillow 產生 900 × 1340 PNG；不使用 AI 生成角色卡。
- `assets/character_card_base.png` 是可自行替換的**空白底板**，不可預先放入角色名稱、圖片、數值。
- `character_card.py` 將 Supabase 角色圖片、名稱、關係、心情、個性、等級、EXP、好感度填到固定位置。
- 可以用外部繪圖工具或 AI 製作**空白底板**，但需維持 900 × 1340 並保留角色圖與文字區域；正式生成不依賴 AI API。
- `assets/character_card_base.png` 可自行替換。角色圖片仍從玩家上傳的 Supabase Storage 取得。
