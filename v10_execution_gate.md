# v10執行閘門驗收紀錄｜2026-11-17

## 已完成
- Python編譯與解析器自測通過。
- 35個月份（2024-01至2026-11）範圍計算通過。
- 906筆待核實清單讀取成功，906筆均缺少官方期號欄位。
- Workflow輸入檔路徑已統一為ASCII檔名 `candidates_906.csv`，避免ZIP檔名編碼造成Runner找不到檔案。
- Workflow只允許手動 `workflow_dispatch`，預設 `probe`，沒有自動排程。
- `GITHUB_TOKEN`權限限制為`contents: read`，不授予Repository寫入權限。
- 封存包不包含Python `.pyc`快取檔。

## 尚未完成／不可宣稱完成
- 尚未連接使用者GitHub Repository，未能在GitHub-hosted Runner實際執行。
- 尚無台彩API原始HTTP回應、response bytes或雲端SHA256證據。
- 官方期號核實新增仍為0筆；906筆仍待官方來源核實。

## 執行順序
1. 將本資料夾內容放入既有Repository根目錄（保留`.github/workflows/`路徑）。
2. 在Actions手動執行`539 Official API Evidence Capture v10`，選`probe`。
3. 檢查artifact包含`202611.response.bin`、metadata及`summary.json`，且HTTP狀態與schema有效。
4. probe驗收通過後，再手動選`full`。
5. 35個月份完整有效後，人工核對日期、五碼、期號與raw bytes，再追加獨立append-only overlay；不得改寫主檔、Registry或預測鎖。
