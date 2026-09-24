# VisionEdge 2.2.1

本版以 VisionEdge 2.2.0 為基線，不改既有檢測判定、SN lock、履歷保存或相機流程，新增產線多國語 UI。

## 多國語

支援四種語言：

- 繁體中文（zh-Hant）
- 简体中文（zh-Hans）
- English（en）
- Español（es，採墨西哥產線常用中性用語）

即時檢測整合頁與 Flow Studio 頂部均有單一 🌐 語言選單。選擇會保存在瀏覽器，下次開啟沿用；首次使用依瀏覽器語言判斷，無法識別時使用繁體中文。

翻譯涵蓋靜態 UI、動態狀態、單張拍照判定、History、常見錯誤、Toast、confirm/alert 與新增的動態 DOM。產品名稱、SN、樣板名稱、Step 名稱與檔名標記為使用者資料，不翻譯，避免改變現場資料語意。

## 邏輯檢查

- `backend-login` 與寫死帳密仍不存在；根路徑直接進 VisionEdge。
- 2.2.0 的 snapshot / history / SN lock / UNKNOWN / NG / revision guard 設計未修改。
- 語言切換只作用在瀏覽器顯示層，不進入 API 或資料庫。
- Flow Studio 仍可由 operator 頂部導覽直接進入；這符合目前 2.2.0 行為，但若量產希望更單純，後續建議改成「Operator UI 預設隱藏工程入口」，不需要重新加入帳密登入。

## 驗證限制

本交付環境缺少 Flask/OpenCV 等 Python runtime 套件且無外網，因此無法在此環境重跑完整 integration suite。已完成前端 JavaScript syntax check、四語靜態覆蓋檢查、登入殘留搜尋與檔案結構檢查。部署到既有 VisionEdge runtime 後仍應執行原有 regression tests 與 QTI 真機驗收。
