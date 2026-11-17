# 今彩539 官方來源證據擷取 v10

## 目的
在 GitHub-hosted Ubuntu runner 執行台彩網站目前使用的 `Daily539Result` 內部 API，避開本機 DNS 解析阻塞。此 API 是網站內部端點，並非台彩公開承諾穩定的API規格。

## 檔案
- `.github/workflows/539-official-capture.yml`：手動執行 workflow；預設只探測 2026-11。
- `fetch_official_daily539_api_v10.py`：月度擷取器，保存每月原始response bytes、HTTP headers、URL、UTC時間、SHA256、解析結果與906列候選比對。
- `candidates_906.csv`：906筆待核實清單；只作日期+五碼比對，不會覆寫主檔。

## 使用
將整個資料夾內容放進既有 GitHub repository 根目錄，確保 `candidates_906.csv`、Python 檔案及 `.github/workflows/` 路徑不變。到 Actions → `539 Official API Evidence Capture v10` → Run workflow，先選 `probe`。確認下載的 artifact 中有 `202611.response.bin`、metadata、summary，且 HTTP/schema 正常後，再選 `full`。

## 升級門檻
1. `probe` 成功不代表完整歷史月份成功。
2. `full` 必須35個月份全數有有效HTTP response及合法schema；若有失敗月份，僅部分成功，需補抓失敗月份。
3. `candidate_period_api_reconciliation.csv` 的 MATCH 只代表官方網站內部API response的日期+五碼吻合候選，需人工覆核期號欄位與raw evidence後，才能追加到獨立 append-only evidence overlay。
4. 禁止直接改寫主檔、歷史預測鎖、Registry v3或正式模型。
5. Workflow刻意沒有排程；完成手動測試與審核前不啟用定期抓取。

## 安全
Workflow僅需 `contents: read`，不需要PAT、Secrets或寫入repository權限。Artifact保留90天；請及時下載並另外長期封存及計算SHA256 manifest。
