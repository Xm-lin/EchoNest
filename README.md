# EchoNest — Discord AI 多角色養成 Bot

支援繁體中文 Slash Commands、Gemini、Supabase PostgreSQL + Storage、Docker / Render。

## 指令（9 個）

| 指令 | 功能 |
|---|---|
| `/建立角色 [圖片]` | 上傳 PNG/JPG/WEBP（選填）後開啟表單，填寫名稱、個性、背景、說話風格；建立時生成獨立 System Message |
| `/角色列表` | 列出角色 ID、名稱、個性與目前角色；空列表也能使用 |
| `/角色狀態` | 查看目前角色、好感度、等級、EXP、圖片 |
| `/角色設定 [圖片]` | 透過表單修改目前角色，可更換圖片；重新生成該角色的 System Message |
| `/切換角色 角色id` | 根據角色列表中的 ID 切換角色 |
| `/聊天 內容` | Gemini 對話，按角色、使用者隔離對話記錄與摘要 |
| `/背包` | 查看使用者道具 |
| `/簽到` | 台灣時間每日一次，領取隨機道具 |
| `/送禮 道具` | 消耗道具，增加目前角色的好感度 |

**沒有任何角色時，只有 `/建立角色` 和 `/角色列表` 能使用。** 不會自動建立預設角色。每隻角色的 System Message 在建立時由欄位組合生成並儲存；修改角色時更新。背包和簽到按使用者及空間儲存，好感度、EXP、對話、記憶按使用者 + 角色儲存。

## 部署前準備

1. **Discord Developer Portal** → 建立 Application → Bot → Reset Token，取得 `DISCORD_TOKEN`。在 Installation 設定 Guild Install 和 User Install，Scopes 選 `bot`、`applications.commands`，Bot Permissions 至少 Send Messages / Embed Links。重新邀請 Bot 以確保授權生效。
2. **Supabase** 建立 Project → Connect → 選 **Session Pooler** 的 PostgreSQL URI 作為 `DATABASE_URL`，並將密碼正確 URL encode。若遇到連線問題，先確認 pooler 與 IPv4 可用。
3. **Supabase Storage** → 建立名稱 `characters` 的 **Public bucket**（這樣 Discord 才能讀取角色圖片）。角色圖片公開可讀，請勿上傳私密照片。圖片檔最大 5 MB。
4. Supabase Project Settings / API Keys 取得 Project URL `SUPABASE_URL` 與 **service_role / secret key** `SUPABASE_SERVICE_ROLE_KEY`。此金鑰可繞過 RLS，**只能放 Render Environment，絕對不要放前端或 GitHub**。
5. Gemini API Key 設為 `GEMINI_API_KEY`，模型名稱 `GEMINI_MODEL`（預設 `gemini-2.5-flash`）。

## Render

將此資料夾內容推上 GitHub（`.env` 不要上傳），Render → New Web Service → 連接 Repo → Runtime Docker → Free。設定以下 Environment：

```
DISCORD_TOKEN=...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=postgresql://...
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=characters
```

`PORT` 由 Render 提供（本機預設 10000）。啟動時自動建立 `bot_*` 資料表；不會覆蓋舊版資料表。`/health` 在 Bot 真正登入 Discord 後回應 HTTP 200。Render 免費方案可能休眠；UptimeRobot 定期檢查不保證免費方案永久在線，且需遵守平台政策。

## 本機執行

```bash
cp .env.example .env
# 編輯 .env，填入環境變數
python -m pip install -r requirements.txt
python bot.py
```

或 `docker compose up --build`。請使用 Python 3.12+。

## 重要限制

- **Guild Install 與 User Install 在同一伺服器內的空間隔離**：目前 `discord.py` 沒有公開 `authorizing_integration_owners` 屬性，因此採「伺服器內 → guild 空間；DM / 私人頻道 → user 空間」的保守規則。若同一伺服器內同時存在兩種安裝模式，**不能保證區分**，請勿將其視為完全隔離。未來需改用支援 interaction authorizing owners 的底層 payload 或函式庫。
- 建立與修改伺服器角色需要 Manage Server 權限；其他使用者可聊天、切換角色並各自養成。個人空間只允許本人使用。
- 圖片採 Supabase Storage Public bucket，僅公開圖片；其他資料留在 PostgreSQL。
- 目前不提供刪除角色功能；舊版單角色資料不自動轉移。
- 長期摘要每 40 筆新訊息整理一次，聊天內容僅送往設定的 Gemini API。
- Discord Global Slash Commands 更新可能需要一些時間才會顯示。

## 排錯

- `AttributeError: authorizing_integration_owners`：新版不再使用此屬性。
- 「應用程式沒有回應」：檢查 Render Logs；資料庫操作已移至執行緒，先回覆 defer。
- Storage 上傳失敗：確認 bucket 名稱、Public 設定、URL 和 service_role key。
- `/角色列表` 看不到舊角色：新版刻意使用獨立 `bot_characters` 資料表，不會繼承舊版預設角色。


## v2：個性列表與固定 Prompt

- `/建立角色`：先從 8 種個性下拉選單選擇，再填入角色名稱、背景、說話風格。圖片可在指令中上傳。
- `/角色設定`：可重新選擇個性、修改角色資訊或更換圖片。
- 核心 `SYSTEM_PROMPT` 寫在 `bot.py`，聊天時即時組合角色資料，不再依賴舊的資料庫 Prompt。
- 舊角色仍可使用；若個性欄位是舊版自由文字，仍可聊天，重新設定後會改用列表值。
- 其餘 9 個指令、資料表、Docker/Render 部署方式保留。
- Discord 的個性選單有效期限為 3 分鐘，過期後重新執行指令即可。


## v3：刪除角色

`/刪除角色`：選擇角色後按「確認刪除」。只有角色建立者或伺服器管理員能刪除；會同步清除角色資料、聊天記憶、養成進度與 Storage 圖片。使用者背包和簽到紀錄不受影響。每次最多顯示 25 個可刪除角色。
