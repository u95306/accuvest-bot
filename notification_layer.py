import os
import requests
import json
from google import genai
import traceback

# 從環境變數安全地讀取鑰匙 (不要把真實字串寫在這裡了！)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_TOKEN")

# 如果讀不到鑰匙，程式提早報錯退出
if not GEMINI_API_KEY or not LINE_CHANNEL_TOKEN:
    raise ValueError("⚠️ 找不到環境變數中的 API 鑰匙，請檢查設定！")

# 初始化 Gemini 客戶端
client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. 輔助模組：讀取 JSON 檔案
# ==========================================
def load_json_data(filepath):
    """安全地讀取本地端的 JSON 檔案"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"⚠️ 讀取 {filepath} 發生錯誤: {e}")
        return None

# ==========================================
# 3. 核心功能模組區
# ==========================================
def get_gemini_briefing():
    """讀取大腦決策與原始數據，並交由 Gemini 翻譯"""
    
    # --- 步驟 A：讀取所有 JSON 檔案 ---
    decision = load_json_data('final_decision.json')
    if not decision:
        print("❌ 找不到 final_decision.json，請確認大腦層是否已成功執行。")
        return None
        
    orders = load_json_data('macro_data.json')
    yield_data = load_json_data('yield_curve.json')
    safety = load_json_data('safety_data.json')
    taiwan = load_json_data('taiwan_light.json')
    etf_data = load_json_data('top_etfs.json')


    # --- 步驟 B：動態提取最新盤面數據 (加入防呆機制) ---
    try:
        orders_yoy = f"{orders.get('values', [0])[-1]:.2f}" if orders else "未知"
        yield_spread = f"{yield_data.get('values', [0])[-1]:.2f}" if yield_data else "未知"
        cpi = f"{safety.get('cpi_yoy', [0])[-1]:.1f}" if safety else "未知"
        # 💡 關鍵修正：對應最新版連續燈號的 'color_names' 陣列
        tw_light = taiwan.get('color_names', ['未知'])[-1] if taiwan else "未知"
    except Exception as e:
        print(f"⚠️ 提取數據發生錯誤: {e}")
        orders_yoy, yield_spread, cpi, tw_light = "讀取異常", "讀取異常", "讀取異常", "讀取異常"

    etf_recommendation = "無（維持現金或觀望）"
    if etf_data and len(etf_data) > 0:
        etf_lines = []
        for i, etf in enumerate(etf_data, 1): # enumerate(, 1) 讓編號從 1 開始
            code = etf.get('Code', '未知')
            name = etf.get('ETF名稱', '未知')
            score = etf.get('綜合動能分數', 0.0)

            # 💡 提取大腦算出的黃金坑標記
            signal = etf.get('訊號標記', '')
            signal_display = f" {signal}" if signal else ""

            etf_lines.append(f"  {i}. {code} {name} (動能: {score}){signal_display}")
        
        # 將陣列組合成換行的字串
        etf_recommendation = "\n" + "\n".join(etf_lines)

    # --- 步驟 C：提取大腦的核心決策 ---
    final_action = decision.get("action", "【無明確指令】")
    reasoning = decision.get("reason", "無")
    allocation = decision.get("asset_allocation", "等待市場訊號")


    # 組裝盤面數據字串
    raw_data_string = f"""
    - 美國訂單 YoY: {orders_yoy}%
    - 10Y-2Y 利差: {yield_spread}%
    - 美國 CPI: {cpi}%
    - 台灣燈號: {tw_light}
    - 資產配置: {allocation}
    - 今日強勢嚴選 Top 5: {etf_recommendation}
    """

    # --- 組合寫給 Gemini 的 Prompt ---
    prompt = f"""
    你現在是 AccuVest 極簡投資平台的「首席文案轉譯官」。
    你的任務是撰寫今天的晨間推播。

    【最高指導原則】
    你不允許自行判斷市場走勢。你必須「絕對服從」系統給定的核心決策。

    【系統輸入】
    1. 核心決策：{final_action}
    2. 決策主因：{reasoning}
    3. 當前盤面與精選標的：\n{raw_data_string}

    【輸出要求】
    請以冷靜、客觀、極簡的工程師風格撰寫推播文案。
    結構必須是：
    1. 第一行直接印出核心決策。
    2. 第二段用當前盤面數據簡單解釋這個決策，並列出資產配置。
    3. 🌟 如果決策是「建議進場」或「強制觀望」，請在最後一段【完整條列出這 5 檔】強勢嚴選標的與分數。
    4. 🚨 關鍵任務：如果標的後方帶有「🚨 超跌黃金坑」標記，請在文案中用一句話冷靜點出「部分標的出現負乖離，具備潛在右側佈局價值」。
    5. 語氣要堅定，排版要乾淨俐落，方便在手機上閱讀。
    """
    

    # --- 步驟 D：組合寫給 Gemini 的 Prompt ---
    # (前面組裝 prompt 的程式碼維持不變...)

    try:
        print("🧠 嘗試使用 gemini-3.5-flash 進行轉譯...")
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
        )
        return response.text
        
    except Exception as e:
        print("🚨 [系統底層錯誤報告] 🚨")
        traceback.print_exc() 
        print("------------------------")
        
        error_message = str(e)
        print(f"⚠️ gemini-3.5-flash 呼叫失敗: {error_message}")
        
        # 判斷是否為 503 錯誤 (或者其他伺服器端錯誤)
        if "503" in error_message or "Service Unavailable" in error_message:
            print("🔄 偵測到 503 錯誤，啟動降級機制，切換至 gemini-2.5-flash...")
            try:
                # 備用方案：使用 gemini-2.5-flash (注意：Google 目前沒有 2.5-flash，備用通常選前一代或 lite)
                fallback_response = client.models.generate_content(
                    model='gemini-2.5-flash', 
                    contents=prompt,
                )
                print("✅ 備用模型轉譯成功！")
                return fallback_response.text
            except Exception as fallback_error:
                print(f"❌ 備用模型也失敗了: {fallback_error}")
                # 如果連備用都失敗，回傳一個系統預設的安全字串，確保 LINE 還是會響
                return f"【系統通知】\n決策：{final_action}\n(備註：AI 轉譯伺服器暫時無回應，請直接查看大腦原始決策)"
        else:
            # 如果不是 503 錯誤 (例如 API Key 錯誤)，就直接報錯，不盲目重試
            print("❌ 發生非 503 的嚴重錯誤，請檢查系統。")
            return f"【系統通知】\n決策：{final_action}\n(備註：AI 轉譯發生異常)"


def broadcast_to_line(message_text):
    #嘴巴：呼叫 LINE 廣播 API 發送訊息
    if not message_text:
        print("⚠️ 沒有文案可發送。")
        return

    print("📢 正在透過 LINE 廣播推播...")
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}"
    }
    data = {
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }

    res = requests.post(url, headers=headers, data=json.dumps(data))

    if res.status_code in (200, 204):
        print("✅ 推播發送成功！請檢查手機。")
    else:
        print(f"❌ 推播發送失敗: {res.status_code} - {res.text}")


# ==========================================
# 4. 主流程控制器 (Main Execution)
# ==========================================
if __name__ == "__main__":
    print("🚀 啟動 AccuVest 晨間自動化推播流程...")

    # 步驟 1：讀取本地 JSON 並請大腦產出文案
    print("🧠 讀取大腦決策並聯繫首席轉譯官...")
    briefing_content = get_gemini_briefing()

    if briefing_content:
        print("\n--- 預覽文案 ---")
        print(briefing_content)
        print("----------------\n")

        # 步驟 2：請嘴巴發送出去
        broadcast_to_line(briefing_content)

