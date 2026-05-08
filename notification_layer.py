import os
import requests
import json
from google import genai

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

    # --- 步驟 B：動態提取最新盤面數據 (加入防呆機制) ---
    try:
        orders_yoy = f"{orders['values'][-1]:.2f}" if orders else "未知"
        yield_spread = f"{yield_data['values'][-1]:.2f}" if yield_data else "未知"
        cpi = f"{safety['cpi_yoy'][-1]:.1f}" if safety else "未知"
        tw_light = taiwan['color_name'] if taiwan else "未知"
    except (KeyError, IndexError):
        orders_yoy, yield_spread, cpi, tw_light = "讀取異常", "讀取異常", "讀取異常", "讀取異常"

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
    """

    # --- 步驟 D：組合寫給 Gemini 的 Prompt ---
    prompt = f"""
    你現在是 AccuVest 極簡投資平台的「首席文案轉譯官」。
    你的任務是撰寫今天的晨間推播。

    【最高指導原則】
    你不允許自行判斷市場走勢。你必須「絕對服從」系統給定的核心決策。

    【系統輸入】
    1. 核心決策：{final_action}
    2. 決策主因：{reasoning}
    3. 當前盤面數據：\n{raw_data_string}

    【輸出要求】
    請以冷靜、客觀、極簡的工程師風格，寫一段 80 字以內的推播文案。
    結構必須是：
    1. 第一行直接印出核心決策。
    2. 第二段用當前盤面數據簡單解釋這個決策，並明確列出資產配置建議。
    3. 語氣要堅定，不要使用「或許」、「可能」等模稜兩可的詞彙。
    """

    try:
        # 呼叫 Gemini (使用較為穩定的 gemini-2.5-flash 模型)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"❌ Gemini API 錯誤: {e}")
        return None


def broadcast_to_line(message_text):
    """嘴巴：呼叫 LINE 廣播 API 發送訊息"""
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
