# 性格選擇更新

- `/建立角色` 的 `性格` 參數保留 8 種預設選項與「自訂」。選擇「自訂」時，直接開啟 Discord Modal，輸入性格名稱及描述。
- `/角色設定` → 「修改性格」開啟下拉選單；選擇「自訂」後開啟同樣的 Modal。
- 選擇預設性格時清空自訂性格描述，使用內建的性格 Prompt。
- 自訂性格名稱寫入 `characters.personality`；描述寫入 `characters.personality_description`，並提供給 Gemini。
- 更改性格不會重置角色的聊天、記憶或養成資料。

## 部署

現有資料庫：先備份，再於 Supabase SQL Editor 執行 `database/005_personality_description.sql`，然後部署新程式。
全新資料庫：`database/schema.sql` 已包含新增欄位；其他原有的初始化／遷移步驟仍須照專案說明執行。

## 驗證

Python 編譯與既有 pytest 測試已通過。尚未連接 Discord、Supabase、Gemini 做端到端驗證。
