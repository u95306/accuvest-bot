# ==========================================
# 模組 1: 資料獲取層 (國發會景氣燈號)
# ==========================================
import requests
import zipfile
import io
import pandas as pd
import json

def fetch_and_save_taiwan_light(zip_url):
    """
    從國發會 ZIP 檔抓取最新景氣燈號，並存成 JSON 給大腦讀取
    """
    print("📡 [資料層] 開始從國發會抓取最新景氣燈號...")
    try:
        response = requests.get(zip_url)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as the_zip:
            csv_filename = "景氣指標與燈號.csv"
            with the_zip.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')

        # 排序並取得最新一筆
        df = df.sort_values(by='Date').reset_index(drop=True)
        latest_data = df.iloc[-1]

        # 轉換為標準 Python 字典 (注意型別轉換，避免 JSON 報錯)
        cleaned_data = {
            "indicator": "Taiwan_Business_Indicator",
            "date": str(latest_data['Date']),
            "score": int(latest_data['景氣對策信號綜合分數']),
            "color_name": str(latest_data['景氣對策信號'])
        }

        # 存成獨立的 JSON 檔案
        with open('taiwan_light.json', 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

        print(f"✅ [資料層] 獲取成功！最新月份 {cleaned_data['date']} 已儲存至 taiwan_light.json")
        return True

    except Exception as e:
        print(f"❌ [資料層] 抓取或處理失敗: {e}")
        return False

# --- 執行資料抓取 ---
if __name__ == "__main__":
    ZIP_URL = "https://ws.ndc.gov.tw/Download.ashx?u=LzAwMS9hZG1pbmlzdHJhdG9yLzEwL3JlbGZpbGUvNTc4MS82MzkyL2VhMjM1YmQ5LWQwNTItNGE2OS1hYmZjLWQ1Yzc4NWQzZDBlMi56aXA%3d&n=5pmv5rCj5oyH5qiZ5Y%2bK54eI6JmfLnppcA%3d%3d&icon=.zip"
    fetch_and_save_taiwan_light(ZIP_URL)

# ==========================================
# 模組 1: 資料獲取層 (data_ingestion)
# ==========================================
from fredapi import Fred
import pandas as pd
import json

# ⚠️ 請換上妳重新生成的新 API Key
FRED_API_KEY = '359f40b1c0ecb081e1d8f14d0f3287fd'
fred = Fred(api_key=FRED_API_KEY)

def fetch_and_save_macro_data():
    """
    只負責抓取 AMTMNO 數據，計算 YoY，並存成 JSON 給大腦讀取
    """
    print("📡 [資料層] 開始從 FRED 抓取美國製造業新訂單數據...")
    try:
        data = fred.get_series('AMTMNO')
        if data.empty:
            return False

        df = pd.DataFrame(data, columns=['new_orders'])
        df['yoy_growth'] = df['new_orders'].pct_change(periods=12) * 100

        # 大腦其實只需要最近 3 個月的數據來判斷趨勢，我們過濾掉多餘雜訊
        df = df.dropna().tail(3)

        # 將 DataFrame 轉換為乾淨的 Python 字典
        cleaned_data = {
            "indicator": "AMTMNO_YoY",
            "dates": df.index.strftime('%Y-%m-%d').tolist(),
            "values": df['yoy_growth'].tolist()
        }

        # 將乾淨的數據存成 JSON 檔案 (這就是解耦的關鍵媒介)
        with open('macro_data.json', 'w') as f:
            json.dump(cleaned_data, f, indent=4)

        print("✅ [資料層] 數據清洗完成，已儲存至 macro_data.json")
        return True

    except Exception as e:
        print(f"❌ [資料層] 抓取失敗: {e}")
        return False

# 執行資料抓取
fetch_and_save_macro_data()

# ==========================================
# 模組 1: 資料獲取層 (新增殖利率利差)
# ==========================================
from fredapi import Fred
import pandas as pd
import json

# 請確認使用最新的 API Key
FRED_API_KEY = '359f40b1c0ecb081e1d8f14d0f3287fd'
fred = Fred(api_key=FRED_API_KEY)

def fetch_and_save_yield_curve():
    """
    抓取 10Y-2Y 殖利率利差，並存成 JSON 給大腦讀取
    """
    print("📡 [資料層] 開始從 FRED 抓取 10Y-2Y 殖利率利差...")
    try:
        # T10Y2Y 是 FRED 官方計算好的 10年減2年 利差數據
        data = fred.get_series('T10Y2Y')
        if data.empty:
            return False

        df = pd.DataFrame(data, columns=['spread'])
        # 利差數據天天更新，我們取最近 120 個交易日 (約半年) 來觀察趨勢
        df = df.dropna().tail(120)

        cleaned_data = {
            "indicator": "Yield_Curve_10Y2Y",
            "dates": df.index.strftime('%Y-%m-%d').tolist(),
            "values": df['spread'].tolist()
        }

        # 存成獨立的 JSON 檔案
        with open('yield_curve.json', 'w') as f:
            json.dump(cleaned_data, f, indent=4)

        print("✅ [資料層] 殖利率利差獲取成功，已儲存至 yield_curve.json")
        return True

    except Exception as e:
        print(f"❌ [資料層] 抓取失敗: {e}")
        return False

# 執行抓取
fetch_and_save_yield_curve()

# ==========================================
# 模組 1: 資料獲取層 (新增 CPI 與 利率)
# ==========================================
from fredapi import Fred
import pandas as pd
import json

FRED_API_KEY = '359f40b1c0ecb081e1d8f14d0f3287fd'
fred = Fred(api_key=FRED_API_KEY)

def fetch_safety_indicators():
    """
    抓取 CPI 與 基準利率，計算年增率與趨勢
    """
    print("📡 [資料層] 正在抓取通膨與利率數據...")
    try:
        # 1. 抓取 CPI 並計算 YoY
        cpi_raw = fred.get_series('CPIAUCSL')
        cpi_df = pd.DataFrame(cpi_raw, columns=['cpi'])
        cpi_df['cpi_yoy'] = cpi_df['cpi'].pct_change(12) * 100

        # 2. 抓取基準利率 (FEDFUNDS)
        fed_rate = fred.get_series('FEDFUNDS')

        # 3. 整合最近半年的數據
        combined = pd.DataFrame({
            'cpi_yoy': cpi_df['cpi_yoy'],
            'fed_rate': fed_rate
        }).dropna().tail(6)

        cleaned_data = {
            "indicator": "Safety_Monitor",
            "dates": combined.index.strftime('%Y-%m-%d').tolist(),
            "cpi_yoy": combined['cpi_yoy'].tolist(),
            "fed_rate": combined['fed_rate'].tolist()
        }

        with open('safety_data.json', 'w') as f:
            json.dump(cleaned_data, f, indent=4)

        print("✅ [資料層] 安全監控數據已儲存。")
        return True
    except Exception as e:
        print(f"❌ [資料層] 抓取失敗: {e}")
        return False

fetch_safety_indicators()
