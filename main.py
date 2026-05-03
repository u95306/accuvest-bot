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

client = genai.Client(api_key=GEMINI_API_KEY)
# ... 下面的程式碼完全保持不變 ...
# ==========================================
# 2. 核心功能模組區
# ==========================================

def get_gemini_briefing(macro_data, etf_data):
    """大腦：呼叫 Gemini 產生極簡晨間推播文案"""
    print("🧠 正在呼叫 Gemini 解讀數據...")
    prompt = f"""
    你現在是「準投資」平台的首席 AI 翻譯官。
    你的任務是將生硬的量化數據，轉化為每天早上 08:30 發送給使用者（允希）的極簡晨間推播。

    【嚴格寫作規範】
    1. 語氣：冷靜、客觀、俐落，帶有軟體工程師的精確感。不需要過度熱情或使用多餘的問候語。
    2. 美學：貫徹極簡主義，絕不廢話。使用條列式結構。
    3. 動作指令：必須在最後給出明確的【進出場狀態】（例如：建議進場、強制抱緊、警示減碼、全面清倉）。

    【今日後台數據輸入】
    - 國發會景氣燈號：{macro_data.get('ndc_light')} (分數：{macro_data.get('ndc_score')})
    - 製造業 PMI 指數：{macro_data.get('pmi_score')} (狀態：{macro_data.get('pmi_status')})
    - AI 防雷嚴選最高安全覆蓋率 ETF：{etf_data.get('top_etf_name')} ({etf_data.get('top_etf_coverage')})

    請根據以上數據，產出今日的晨間推播文案。
    """
    try:
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
# 3. 主流程控制器 (Main Execution)
# ==========================================
if __name__ == "__main__":
    print("🚀 啟動準投資晨間自動化流程...")
    
    # 模擬今日從資料庫和爬蟲取得的最新數據
    today_macro = {
        'ndc_light': '紅燈',
        'ndc_score': 39,
        'pmi_score': 55.4,
        'pmi_status': '擴張'
    }
    today_etf = {
        'top_etf_name': '00881 國泰台灣5G+',
        'top_etf_coverage': '48.5%'
    }
    
    # 步驟 1：請大腦產出文案
    briefing_content = get_gemini_briefing(today_macro, today_etf)
    
    if briefing_content:
        print("\n--- 預覽文案 ---")
        print(briefing_content)
        print("----------------\n")
        
        # 步驟 2：請嘴巴發送出去
        broadcast_to_line(briefing_content)
