import requests
import zipfile
import io
import pandas as pd
import json
import os
from fredapi import Fred
import time
import sys  # 💡 新增：用來發送中斷信號 (Hard Fail)
# 💡 新增：直接從推播層借用「嘴巴」
from notification_layer import broadcast_to_line

# ==========================================
# 模組 1: 資料獲取層 (國發會景氣燈號)
# ==========================================
def fetch_and_save_taiwan_light(zip_url):
    """
    從國發會 ZIP 檔抓取最新景氣燈號，並存成 JSON 給大腦讀取
    """
    print("📡 [資料層] 開始從國發會抓取最新景氣燈號...")
    try:
        response = requests.get(zip_url)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as the_zip:
            target_filename = None
            
            # 策略 A：嘗試修復檔名編碼
            for zinfo in the_zip.infolist():
                try:
                    # 關鍵：將誤判為 CP437 的檔名轉回 CP950 (Big5)
                    real_name = zinfo.filename.encode('cp437').decode('cp950')
                except:
                    real_name = zinfo.filename
                
                # 💡 新增防呆：看到 schema 就直接跳過，不論大小寫
                if 'schema' in real_name.lower():
                    continue
                    
                if '景氣指標與燈號.csv' in real_name:
                    target_filename = zinfo.filename
                    print(f"🎯 成功透過檔名修復定位檔案: {real_name}")
                    break
            
            # 策略 B：如果策略 A 失敗，改用「內容特徵」掃描所有 CSV
            if not target_filename:
                print("⚠️ 檔名匹配失敗，啟動內容特徵掃描...")
                for name in the_zip.namelist():
                    if name.lower().endswith('.csv'):
                        with the_zip.open(name) as f:
                            # 只讀取標題列進行檢查，不耗費記憶體
                            try:
                                header_df = pd.read_csv(f, encoding='utf-8-sig', nrows=0)
                                if '景氣對策信號' in header_df.columns:
                                    target_filename = name
                                    print(f"🎯 透過欄位特徵成功鎖定檔案: {name}")
                                    break
                            except:
                                continue

            if not target_filename:
                print("❌ 窮盡所有方法仍找不到包含景氣燈號的 CSV 檔案。")
                return False

            # 讀取最終確定的檔案
            with the_zip.open(target_filename) as csv_file:
                df = pd.read_csv(csv_file, encoding='utf-8-sig')


        # 排序並取得最新一筆
        df = df.sort_values(by='Date').reset_index(drop=True)
        recent_df = df.tail(6) # 取最近半年資料

        # 轉換為標準 Python 字典 (注意型別轉換，避免 JSON 報錯)
        cleaned_data = {
            "indicator": "Taiwan_Business_Indicator",
            "dates": recent_df['Date'].astype(str).tolist(),
            "scores": recent_df['景氣對策信號綜合分數'].astype(int).tolist(),
            "color_names": recent_df['景氣對策信號'].astype(str).tolist()
        }

        # 存成獨立的 JSON 檔案
        with open('taiwan_light.json', 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

        print(f"✅ [資料層] 獲取成功！最新月份 {cleaned_data['dates']} 已儲存至 taiwan_light.json")
        return True

    except Exception as e:
        print(f"❌ [資料層] 抓取或處理失敗: {e}")
        return False



# ==========================================
# 核心引擎：FRED 安全抓取與防護網 (寫一次就好)
# ==========================================
def fetch_fred_with_retry(fetch_logic_func, module_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 讓外面的函數自己決定要抓什麼、算什麼
            return fetch_logic_func()
        except Exception as e:
            print(f"⚠️ [{module_name}] 第 {attempt + 1} 次失敗: {e}")
            if attempt < max_retries - 1:
                print("等待 10 秒後進行重試...")
                time.sleep(8) # 💡 失敗的話，睡 8 秒再重新執行下一次迴圈 
            else:
                print(f"❌ [{module_name}] 重試達上限。")
                error_msg = f"【系統緊急通知】🚨\nAccuVest {module_name} 發生異常...\n將交接至 12:37 降級重試。"
                broadcast_to_line(error_msg)
                sys.exit(1)


# ⚠️ FRED API Key
FRED_API_KEY = os.environ.get("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

# ==========================================
# 模組 2: 資料獲取層 (美國-進出口年增率 (YoY))
# ==========================================
           
def logic_macro_data():
    data = fred.get_series('AMTMNO')
    time.sleep(2)
    if data.empty:
        return False

    df = pd.DataFrame(data, columns=['new_orders'])
    df['yoy_growth'] = df['new_orders'].pct_change(periods=12, fill_method=None) * 100

    # 大腦其實只需要最近 6 個月的數據來判斷趨勢，我們過濾掉多餘雜訊
    df = df.dropna().tail(6)

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

def fetch_and_save_macro_data():
    # 只要呼叫引擎，把邏輯塞進去，防呆機制自動啟動！
    fetch_fred_with_retry(logic_macro_data, "進出口年增率")


# ==========================================
# 模組 3: 資料獲取層 (美國長短天期殖利率倒掛 (10Y-2Y))
# ==========================================

def logic_yield_curve():
    # 💡 決定：中期（半年~一年）避險追蹤，T10Y2Y 的轉折訊號比 T10Y3M 更具備領先性與操作空間
    data = fred.get_series('T10Y2Y')
    time.sleep(2)
    if data.empty:
        return False

    df = pd.DataFrame(data, columns=['spread'])
    # 🚨 重要修改：不能唯獨取 120 天。必須取至少 252 個交易日（約 1 年）
    # 這樣才能在「現在解除倒掛」時，依然能在陣列中找到「過去幾個月前倒掛」的痕跡
    df = df.dropna().tail(252)

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

# 執行抓取
def fetch_and_save_yield_curve():
    fetch_fred_with_retry(logic_yield_curve, "美國長短天期殖利率倒掛")

# ==========================================
# 模組 4: 資料獲取層 (新增 CPI 與 利率)
# ==========================================

def logic_indicators():
    # 1. 抓取通膨 CPI
    cpi_raw = fred.get_series('CPIAUCSL')
    cpi_df = pd.DataFrame(cpi_raw, columns=['cpi'])
    cpi_df['cpi_yoy'] = cpi_df['cpi'].pct_change(12, fill_method=None) * 100
    time.sleep(2)

    # 2. 抓取失業率 (UNRATE) 取代充滿雜訊的 NFP
    unrate_raw = fred.get_series('UNRATE')
    time.sleep(2)
    # 3. 整合最近一年 (12個月) 的數據，因為 Sahm Rule 需要過去 12 個月的最低點
    combined = pd.DataFrame({
        'cpi_yoy': cpi_df['cpi_yoy'],
        'unrate': unrate_raw # 💡 併入失業率數據
    }).dropna().tail(12)

    cleaned_data = {
        "indicator": "Safety_Monitor",
        "dates": combined.index.strftime('%Y-%m-%d').tolist(),
        "cpi_yoy": combined['cpi_yoy'].tolist(),
        "unrate": combined['unrate'].tolist() # 💡 輸出失業率供大腦計算 Sahm Rule
    }

    with open('safety_data.json', 'w') as f:
        json.dump(cleaned_data, f, indent=4)

    print("✅ [資料層] 通膨與失業率監控數據已儲存至 safety_data.json。")
    return True

def fetch_safety_indicators():
    fetch_fred_with_retry(logic_indicators, "通膨與失業率")



# ==========================================
# 主流程控制器 (Main Execution)
# ==========================================
if __name__ == "__main__":
    print("🚀 啟動 AccuVest 資料獲取引擎...")
    
    # 國發會景氣燈號 (ZIP_URL 變數也可以移下來這裡集中管理)
    ZIP_URL = "https://ws.ndc.gov.tw/Download.ashx?u=LzAwMS9hZG1pbmlzdHJhdG9yLzEwL3JlbGZpbGUvNTc4MS82MzkyL2VhMjM1YmQ5LWQwNTItNGE2OS1hYmZjLWQ1Yzc4NWQzZDBlMi56aXA%3d&n=5pmv5rCj5oyH5qiZ5Y%2bK54eI6JmfLnppcA%3d%3d&icon=.zip"
    fetch_and_save_taiwan_light(ZIP_URL)
    
    # FRED 總經指標群
    fetch_and_save_macro_data()
    fetch_and_save_yield_curve()
    fetch_safety_indicators()
    
    print("🏁 所有資料獲取完畢")
