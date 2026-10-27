# EchoNest

Discord AI 角色聊天與養成機器人。使用 Gemini 聊天、Agnes AI 生圖、Pillow 角色卡、Supabase 儲存資料與圖片。

## 目錄

- [開始使用](#開始使用)
- [角色指令](#角色指令)
- [聊天與記憶](#聊天與記憶)
- [養成與收藏](#養成與收藏)
- [圖片生成](#圖片生成)
- [使用須知](#使用須知)

## 開始使用

將機器人加入 Discord 伺服器，或開啟私人訊息。使用 `/建立角色` 建立角色，再使用 `/聊天` 開始對話。私人訊息與伺服器的角色和背包分開儲存。

## 角色指令

| 指令 | 功能 |
| --- | --- |
| `/建立角色` | 建立角色，選擇預設或自訂性格 |
| `/角色列表` | 查看角色 |
| `/切換角色` | 切換對話角色 |
| `/角色設定` | 透過按鈕編輯名稱、性格與圖片 |
| `/刪除角色` | 具管理權限者永久刪除角色 |
| `/角色狀態` | 顯示心情、好感度、等級、EXP 與角色圖片卡片 |
| `/上傳角色圖片` | 上傳角色圖片 |

## 聊天與記憶

| 指令 | 功能 |
| --- | --- |
| `/聊天` | 與選取角色聊天 |
| `/聊天設定` | 設定 DM 主動發言頻率 |
| `/記住` | 建立者新增角色重要記憶 |
| `/記憶列表` | 建立者查看重要記憶 |
| `/刪除記憶` | 建立者刪除重要記憶 |

角色可參考近期聊天紀錄、簡要歷史與最多三則相關重要記憶。伺服器角色共享聊天紀錄，請勿在聊天中透露個人敏感資料。

## 養成與收藏

| 指令 | 功能 |
| --- | --- |
| `/背包` | 查看持有的物品 |
| `/簽到` | 每日領取花束 |
| `/送禮` | 輸入背包內的禮物名稱送給角色 |
| `/探索` | 每日最多五次，隨機取得物品 |
| `/任務` | 領取每日探索任務獎勵 |
| `/收藏` | 查看收藏紀錄 |

禮物池有 62 種物品。好感度依使用者分開計算，角色心情與等級共用。

## 圖片生成

`/生成角色圖片` 可選擇日系動漫、寫實人像、精緻插畫、水彩手繪、像素藝術、Q版可愛、奇幻角色、漫畫風格等 8 種風格，再依角色設定及外觀描述呼叫 Agnes AI，先顯示預覽。可按「重新生成」沿用相同風格。只有具管理權限者按下「使用這張圖片」，才會將圖片儲存到 Supabase Storage 並更新角色狀態卡；取消不會覆蓋原圖。生成請求可能使用服務額度。

## 使用須知

- Bot 必須持續在線才能回覆或發送主動訊息；免費 Web Service 可能休眠。
- 圖片生成需要服務可用且設定 API 金鑰，沒有完成真實帳號端到端測試。
- 伺服器角色的舊對話使用 AI 產生摘要；私人角色對話依使用者隔離，暫不做共享摘要。
- 主動發言適用單實例運作；多實例部署需要額外排程鎖。
- 管理員部署說明請參閱 `build.txt`。


## 生成角色圖片（人物形容／風格／動作）

使用 `/生成角色圖片`，填寫三個必填欄位：

- **人物形容**：例如「銀白色短髮、紫色眼睛、黑色蝴蝶結、貓耳」。
- **風格**：從 8 種風格下拉選單選擇。
- **動作**：例如「微微歪頭，帶著疲倦表情看向鏡頭」。

程式將三項資訊與統一的高品質頭像構圖提示詞結合，優先生成**脖子以上、臉部為畫面主體**的角色圖。生圖後可預覽、使用、重新生成或取消；重新生成會沿用原本三項設定。實際結果取決於 Agnes AI 模型。


### 所有圖片風格統一近距離構圖
八種風格皆使用相同的臉部特寫構圖：脖子以上、臉部為主、柔和光影與細膩質感；風格只影響繪製媒材，人物形容與動作仍由使用者自由輸入。

## Permissions update

Before deploying this version, back up your Supabase database and run `database/003_permissions.sql` in the SQL editor. Keep **Guild Install** and **User Install** enabled in the Discord Developer Portal to preserve DM slash commands. Commands in guilds where EchoNest is not installed are blocked at execution time, although Discord may still display user-installed commands there.

New commands: `/回覆可見性`, `/角色權限`, `/角色授權`, `/邀請角色`, `/接受邀請`, `/轉移所有權`, `/批次刪除角色`. Guild transfer requires Manage Server permission; after transfer, the role is restricted to administrators. Existing roles default to everyone.

Run `python -m compileall -q .` for a basic syntax check. For live tests, stop the Render bot instance before running `python bot.py` locally. Discord and Supabase integration has not been tested automatically.

完整更新與尚待驗證事項見 `CHANGELOG_REVIEW.md`。
