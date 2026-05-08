import os
import requests
import time

# 讀取環境變數中的金鑰
FRED_API_KEY = os.getenv("FRED_API_KEY")

def test_fred_raw(series_id, name):
    """使用最底層的 requests 測試 FRED API，揪出真實錯誤"""
    print(f"\n====================================")
    print(f"🔍 測試項目: {name} (代號: {series_id})")
    print(f"====================================")
    
    if not FRED_API_KEY:
        print("❌ 錯誤：找不到 FRED_API_KEY 環境變數！")
        return

    # FRED 官方的 API 網址 (指定回傳 JSON 格式)
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json"
    
    try:
        # 設定 10 秒 Timeout，避免程式卡死
        response = requests.get(url, timeout=10)
        
        print(f"HTTP 狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            obs_count = len(data.get('observations', []))
            print(f"✅ 測試成功！成功抓取 {obs_count} 筆歷史數據。")
        else:
            print(f"❌ 測試失敗！FRED 伺服器回應：")
            # 印出伺服器真實的抱怨內容
            print(response.text[:500]) 
            
    except Exception as e:
        print(f"⚠️ 網路連線發生嚴重例外: {e}")

def test_taiwan_ndc():
    """測試國發會 ZIP 下載與解析"""
    print(f"\n====================================")
    print(f"🔍 測試項目: 台灣國發會景氣燈號 (ZIP 下載)")
    print(f"====================================")
    
    zip_url = "https://ws.ndc.gov.tw/Download.ashx?u=LzAwMS9hZG1pbmlzdHJhdG9yLzEwL3JlbGZpbGUvNTc4MS82MzkyL2VhMjM1YmQ5LWQwNTItNGE2OS1hYmZjLWQ1Yzc4NWQzZDBlMi56aXA%3d&n=5pmv5rCj5oyH5qiZ5Y%2bK54eI6JmfLnppcA%3d%3d&icon=.zip"
    
    try:
        response = requests.get(zip_url, timeout=15)
        print(f"HTTP 狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ 下載成功！檔案大小: {len(response.content)} bytes")
        else:
            print(f"❌ 下載失敗！狀態碼: {response.status_code}")
            
    except Exception as e:
         print(f"⚠️ 網路連線發生嚴重例外: {e}")

# --- 開始執行全面體檢 ---
if __name__ == "__main__":
    print("🚀 啟動 AccuVest 外部 API 全面診斷...\n")
    
    # 測試 1：台灣燈號
    test_taiwan_ndc()
    time.sleep(2)
    
    # 測試 2：美國製造業訂單 (攻擊指標)
    test_fred_raw('AMTMNO', '美國製造業新訂單')
    time.sleep(3) # 強制延遲，避免被當成駭客攻擊
    
    # 測試 3：殖利率利差 (防禦指標)
    test_fred_raw('T10Y2Y', '10Y-2Y 殖利率利差')
    time.sleep(3)
    
    # 測試 4：CPI 通膨 (斷路器指標)
    test_fred_raw('CPIAUCSL', '美國 CPI 通膨率')
