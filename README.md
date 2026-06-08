# AccuVest
> 反資訊爆炸的極簡總經量化投資系統 (Macro-Driven Algorithmic Trading System)

## 系統架構 (System Architecture)
採用嚴謹的「三層式解耦架構 (Decoupled 3-Tier Architecture)」，確保模組獨立性與高容錯率：

### 1. 📡 資料獲取層 (`data_ingestion.py`)
- **指標精準化**：串接 FRED API 與國發會 OpenAPI，抓取美國製造業新訂單 (AMTMNO)、美國 10Y-2Y 殖利率利差、美國消費者物價指數 (CPI) 以及美國失業率 (UNRATE，取代高雜訊的 NFP)。
- **歷史視野擴展**：自動回溯清洗並保留最近 12 個月的完整數據鏈，專門用以支援大腦層執行「薩姆規則 (Sahm Rule)」的精確矩陣運算。
- **容錯機制**：內建「指數退避 (Exponential Backoff)」重試邏輯，有效應對 API `504 Gateway Timeout`。若達重試上限，將觸發 `sys.exit(1)` 主動報錯，並透過 LINE 提早發送緊急信號彈。

### 2. 🎯 量化選股引擎：三維動能與黃金坑 (`etf_selector.py`)
- **前端提早過濾 (Early Filtering)**：在爬蟲階段 (`etf_crawler.py`) 即透過字串特徵自動剔除代號包含 `A` 的主動型 ETF，避免主觀操作黑盒子破壞系統純粹性，並防止其佔用高流動性候選名單。
- **純粹動能排序**：徹底拔除具有遲滯效應的歷史分數平滑機制（EMA），在每週一對前 20 大高流 AUM ETF 執行最赤裸、即時的綜合動能運算：`(120日漲幅 * 0.5) + (60日漲幅 * 0.3) + (20日漲幅 * 0.2)`。
- **🚨 黃金坑偵測器**：實作「月線負乖離濾網」。當大腦判定處於安全多頭，但優質原型 ETF 因短線非理性恐慌導致月線乖離率 `bias_20 <= -4.0%` 時，系統會自動在終端機與推播文案中點亮 `🚨 超跌黃金坑` 的高賠率奇襲標記。

### 3. 🧠 邏輯決策層 (`strategy_brain.py`)
拋棄主觀預測，以 Python 實作嚴格的優先級決策樹 (Priority Logic)。
- **優先級 1 - 通膨斷路器**：當美國 CPI YoY >= 4.0% 時，判定為高通膨惡性緊縮環境，強行中斷常規避險邏輯，配置改為 **【100% 現金】**，絕對防禦股債雙殺。
- **優先級 2 - 薩姆衰退確認 (Sahm Rule)**：當「近 3 個月失業率平均」減去「過去 12 個月最低失業率」>= 0.5% 時，確認實體經濟步入衰退主跌段，啟動 **【美債 80% + 現金 20%】** 的傳統通縮衰退大避險。
- **優先級 3 - 10Y-3M 解倒掛預警**：當 10Y-3M 經歷顯著倒掛後重新回升突破 0.1% 臨界點，暗示債市已定價聯聯會的被動降息，啟動中期減碼配置 **【股票 30% + 美債 50% + 現金 20%】**。
- **優先級 4 - 台灣景氣過熱防護 (紅燈數鈔票)**：當台灣景氣燈號分數 >= 38 分（紅燈區）時，市場進入非理性過熱，強制啟動獲利了結，配置收縮至 **【股票 40% + 美債 30% + 現金 30%】**。
- **優先級 5 - 基本面攻擊引擎 (藍燈買股票)**：完全解耦台灣藍燈的進場枷鎖。只要美國製造業新訂單 3MMA 趨勢強勢向上，即便台灣燈號仍處於低迷藍燈，大腦亦判定為「牛市初升段」，執行 **【100% 股票型 ETF 全軍突擊】**。
- **優先級 6 - 常規修正期**：美國新訂單 3MMA 動能轉弱，且未觸發任何極端斷路器，執行常規防守 **【美債 50% + 現金 50%】**。

### 4. 🗣️ 智能推播層 (`notification_layer.py`)
- **訊號標記感知**：自動識別 JSON 資料流中的黃金坑標記（`🚨 超跌黃金坑`），並將訊號動態揉入 Prompt 之中。
- **文案風格約束**：嚴格限定 Google Gemini API 扮演冷靜、精確、去情緒化的工程師風格，產出方便手機閱讀的極簡推播晨報，並透過 LINE 廣播 API 發送。
- **生產級升級與降級 (Fallback)**：全面對齊 Google 最新生產線模型。預設主力模型為 `gemini-3.5-flash`，若遇伺服器 `503` 異常，系統將零延遲自動降級切換至 `gemini-2.5-flash`。

---
## 基礎建設與排程 (CI/CD & Cron)
- **去壅塞排程指揮**：不依賴 GitHub 內建易壅塞的 cron 觸發，排程轉交由 **cron-job.org** 的外部 Webhook 精準喚醒 GitHub Actions（透過 `workflow_dispatch`）。
- **時間偏移 (Jitter)**：設定於台灣時間每日 `08:37` 執行，避開全球整點請求高峰。
- **狀態快取補發機制**：結合 `actions/cache` 設計成功打卡單（`success.flag`）。若早盤因不可抗力引發 Hard Fail，中午 `12:37` 的備用排程會自動檢查打卡單，並執行降級補發。
- **記憶同步精簡化**：每週一核心大腦計算完成後，GitHub Actions 僅會將最新生成的決策名單 `top_etfs.json` 推送回 GitHub 倉庫保存，不留任何多餘的歷史快取檔案，保持程式庫極簡。

## 環境變數與機密配置 (Environment Variables)
部署前請確保於本地 `.env` 或 GitHub Repository Secrets 中配置以下金鑰：

```env
FRED_API_KEY=your_fred_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
LINE_CHANNEL_TOKEN=your_line_bot_token_here
```
## 執行與測試 (Local Testing)
在本地環境手動測試時，請嚴格按照與 GitHub Actions (CI/CD) 完全相同的順序執行，以確保 JSON 資料流傳遞正確：
### 0. 安裝環境依賴 (Install Dependencies)
請確保已啟動虛擬環境，並安裝所有必要套件：
```Bash
pip install -r requirements.txt
```
### 1. 獲取數據並產生 macro_data.json 等資料
抓取最新總經、燈號與市場數據，並清洗儲存為基礎 JSON 檔案。
```Bash
python data_ingestion.py
```
### 2. 核心大腦運算並產生 final_decision.json
讀取數據執行優先級決策樹，判定目前處於多頭攻擊或防守避險狀態。
```Bash
python strategy_brain.py
```
### 3. ETF 嚴選層 (規模/流動性/動能決策)
根據大腦決策，掃描大盤並選出季線之上、動能最強的前 3 大 ETF 標的。
```Bash
python etf_selector.py
```
### 4. 轉譯文案並推播至 LINE
由 Gemini 擔任轉譯官，將前三步產出的最終數據與標的轉化為晨間早報，並推播至 LINE。
```Bash
python notification_layer.py
```
