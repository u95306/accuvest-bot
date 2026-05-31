# AccuVest
> 反資訊爆炸的極簡總經量化投資系統 (Macro-Driven Algorithmic Trading System)

## 系統架構 (System Architecture)
採用嚴謹的「三層式解耦架構 (Decoupled 3-Tier Architecture)」，確保模組獨立性與高容錯率：

### 1. 📡 眼睛與耳朵：資料獲取層 (`data_ingestion.py`)
- 負責串接 FRED API 與國發會 OpenAPI，抓取美國製造業新訂單 (AMTMNO)、殖利率利差、CPI 與就業數據。
- 將清洗後的指標轉換為乾淨的 JSON 檔案，供大腦層讀取。
- **容錯機制**：內建「指數退避 (Exponential Backoff)」重試邏輯，有效應對 API `504 Gateway Timeout`。若達重試上限，將觸發 `sys.exit(1)` 主動報錯，並透過 LINE 提早發送緊急信號彈。

### 2. 🧠 核心大腦：邏輯決策層 (`strategy_brain.py`)
- 拋棄主觀預測，以 Python 實作嚴格的優先級決策樹 (Priority Logic)。
- **優先級 1 - 通膨斷路器**：偵測惡性通膨 (CPI >= 4.0) 疊加暴力升息，在就業尚未完全衰退前，強制啟動 100% 現金避險。
- **優先級 2 - 衰退逃命信號**：偵測殖利率「解除倒掛」且 Fed 啟動降息，確認實體經濟步入衰退，資金全面輪動至美債 ETF (00679B)。
- **優先級 3 - 基本面攻擊**：利用美國新訂單 3MMA (三個月移動平均) 濾除單月雜訊，搭配台灣景氣燈號脫離藍燈 (>=17分)，啟動高勝率多頭重壓 (00881)。

### 3. 🗣️ 首席轉譯官：智能推播層 (`notification_layer.py`)
- 串接 Google Gemini API，嚴格要求 LLM 扮演「不帶情緒、極簡客觀」的轉譯官，將大腦輸出的 JSON 決策轉化為晨間早報。
- 透過 LINE Messaging API 執行單向廣播推播。
- **降級機制 (Fallback)**：預設主力模型為 `gemini-2.5-flash`，若遇伺服器 `503 Service Unavailable` 異常，系統將自動降級切換至 `gemini-1.5-flash`，確保每日晨報不中斷。

---

## 基礎建設與排程 (CI/CD & Cron)
- 依賴 **GitHub Actions** (`schedule.yml`) 進行無人值守自動化。
- **時間偏移 (Jitter)**：刻意避開全球 API 請求壅塞的整點，設定於台灣時間 `08:37` 執行。
- **交接聯絡簿機制**：結合 `actions/cache` 設計狀態快取。若早盤因外部環境引發 Hard Fail，系統將會利用狀態標記，於中午 `12:37` 自動執行降級備用排程補發。

## 環境變數與機密配置 (Environment Variables)
部署前請確保於本地 `.env` 或 GitHub Repository Secrets 中配置以下金鑰：

```env
FRED_API_KEY=your_fred_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
LINE_CHANNEL_TOKEN=your_line_bot_token_here
```
## 執行與測試 (Local Testing)
在本地環境測試時，請嚴格按照以下順序執行，以確保 JSON 資料流傳遞正確：
### 0. 安裝環境依賴 (Install Dependencies)
請確保已啟動虛擬環境，並安裝所有必要套件（包含 pandas, fredapi, google-genai, python-dotenv, pyarrow 等）：
```Bash
pip install -r requirements.txt
```
### 1. 獲取數據並產生 macro_data.json 等資料
`python data_ingestion.py`

### 2. 核心大腦運算並產生 final_decision.json
`python strategy_brain.py`

### 3. 轉譯文案並推播至 LINE
`python notification_layer.py`
