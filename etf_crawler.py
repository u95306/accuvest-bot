import time
import requests
import pandas as pd
from requests.exceptions import RequestException, Timeout, ConnectionError
import numpy as np

def safe_fetch_json(url, max_retries=3):
    """
    安全獲取 JSON 資料的通用函式，包含超時、異常捕獲與重試機制
    """
    headers = {'Connection': 'close'}
    
    for attempt in range(1, max_retries + 1):
        try:
            # 這裡使用 (3, 10) 代表 3 秒連線超時，10 秒讀取超時
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            
            # 如果 HTTP 狀態碼不是 200，會在這裡主動觸發 HTTPError 異常
            response.raise_for_status() 
            
            # 成功獲取並解析 JSON
            return response.json()
            
        except Timeout as e:
            print(f"⚠️ 請求超時 (嘗試 {attempt}/{max_retries}): {url} -> {e}")
        except ConnectionError as e:
            print(f"⚠️ 連線錯誤 (嘗試 {attempt}/{max_retries}): {url} -> {e}")
        except RequestException as e:
            print(f"⚠️ 其他請求異常 (嘗試 {attempt}/{max_retries}): {url} -> {e}")
        except ValueError:
            print(f"❌ 解析失敗：該 URL 回傳的不是合法的 JSON 格式: {url}")
            return None
            
        # 如果不是最後一次嘗試，就等待 5 秒再重試，避免頻率過高被封鎖
        if attempt < max_retries:
            time.sleep(5)
            
    print(f"❌ 達到最大重試次數，無法獲取資料: {url}")
    return None

def fetch_and_filter_etf(min_scale_ntd=50000000000, top_n=20):
    """
    雙層過濾系統：
    第一層 (防禦)：依據 AUM (資產規模) 篩選出大於門檻的 ETF。
    第二層 (攻擊)：在第一層的安全名單中，依據「月均成交金額」排序，取出前 N 名。
    """
    print("啟動資料獲取層：正在向證交所請求 ETF 規模與流動性數據...\n")
    # ---------------------------------------------------------
    # 步驟 1: 獲取所需的三份資料表
    # ---------------------------------------------------------
    url_avg_price = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_AVG_ALL"
    url_units = "https://openapi.twse.com.tw/v1/opendata/t187ap47_L"
    url_monthly_volume = "https://openapi.twse.com.tw/v1/exchangeReport/FMSRFK_ALL"

    print("🔄 開始依序獲取台灣證交所 API 資料...")
    
    # 呼叫 safe_fetch_json 安全獲取三份資料
    res_price = safe_fetch_json(url_avg_price)
    res_units = safe_fetch_json(url_units)
    res_volume = safe_fetch_json(url_monthly_volume)

    # 檢查是否所有資料都成功拿到 (只要有一個是 None 就終止)
    if not all([res_price, res_units, res_volume]):
        print("❌ 核心資料下載不完整，終止後續處理。")
        return None

    print("✅ 所有資料表獲取成功，開始進行資料處理...")

    # 轉為 DataFrame
    df_price = pd.DataFrame(res_price)
    df_units = pd.DataFrame(res_units)
    df_volume = pd.DataFrame(res_volume)

    # 統一 Mapping 鍵值為 'Code'
    if 'Code' not in df_price.columns and '證券代號' in df_price.columns:
        df_price = df_price.rename(columns={'證券代號': 'Code'})
        
    code_col_units = '基金代號' if '基金代號' in df_units.columns else '證券代號'
    df_units = df_units.rename(columns={code_col_units: 'Code'})
    
    # 注意：FMSRFK_ALL API 官方文件通常定義 'Code' 或 '證券代號'
    if 'Code' not in df_volume.columns and '證券代號' in df_volume.columns:
        df_volume = df_volume.rename(columns={'證券代號': 'Code'})

    # ---------------------------------------------------------
    # 步驟 2: 第一層過濾 (規模 AUM 防護)
    # ---------------------------------------------------------
    # 合併價格與單位數
    df_merged = pd.merge(df_units, df_price, on='Code', how='inner')
    
    # 清洗：收盤價
    df_merged['收盤價'] = df_merged['ClosingPrice'].astype(str).str.replace(',', '', regex=False)
    df_merged['收盤價'] = pd.to_numeric(df_merged['收盤價'], errors='coerce').fillna(0)
    
    # 清洗：發行單位
    unit_col = '發行單位數/轉換數' if '發行單位數/轉換數' in df_merged.columns else '發行單位數'
    df_merged['發行單位'] = df_merged[unit_col].astype(str).str.replace(',', '', regex=False)
    df_merged['發行單位'] = pd.to_numeric(df_merged['發行單位'], errors='coerce').fillna(0)
    
    # 計算 AUM 並過濾
    df_merged['AUM'] = df_merged['發行單位'] * df_merged['收盤價']
    df_safe_pool = df_merged[df_merged['AUM'] >= min_scale_ntd].copy()
    
    print(f"🛡️ 第一層防護完畢：共有 {len(df_safe_pool)} 檔 ETF 規模超過 {min_scale_ntd/100000000} 億。")

    # ---------------------------------------------------------
    # 步驟 3: 第二層排序 (月均成交金額流動性)
    # ---------------------------------------------------------
    # 將第一層過濾後的安全名單，與成交量表進行 JOIN
    df_final = pd.merge(df_safe_pool, df_volume, on='Code', how='inner')
    
    # 清洗：當月總成交金額與成交日數
    df_final['TradeValueA'] = df_final['TradeValueA'].astype(str).str.replace(',', '', regex=False)
    df_final['TradeValueA'] = pd.to_numeric(df_final['TradeValueA'], errors='coerce').fillna(0)
    
    df_final['TradeVolumeB'] = df_final['TradeVolumeB'].astype(str).str.replace(',', '', regex=False)
    df_final['TradeVolumeB'] = pd.to_numeric(df_final['TradeVolumeB'], errors='coerce').fillna(1) # 避免除以 0
    
    # 這裡我們用一個更精確的算法：如果你只想看日均，我們應該找「成交天數」。
    # 但證交所 API 欄位名稱變動頻繁。如果沒有天數，我們用「成交筆數」或「總金額」來直接排序也是絕對有效的流動性指標。
    # 為了簡化與穩定，我們直接使用當月「總成交金額」作為流動性排序標準 (金額越大，流動性絕對越好)。
    df_final['當月總成交金額'] = df_final['TradeValueA']

    # 排序：依據流動性 (總成交金額) 降冪排序
    df_final = df_final.sort_values(by='當月總成交金額', ascending=False)
    
    # 取前 N 名 (預設前 20)
    df_top_n = df_final.head(top_n).copy()

    # ---------------------------------------------------------
    # 步驟 4: 整理最終輸出格式
    # ---------------------------------------------------------
    df_top_n['AUM(億)'] = (df_top_n['AUM'] / 100000000).round(2)
    # 將成交金額轉換為「億」方便閱讀
    df_top_n['月成交金額(億)'] = (df_top_n['當月總成交金額'] / 100000000).round(2)
    
    # 【工程師防護網升級】：自動掃描存在的名稱欄位 (解決 pd.merge 產生的 _x, _y 問題)
    possible_name_cols = ['基金簡稱', 'Name_x', 'Name', '證券名稱', '基金中文名稱']
    name_col = next((col for col in possible_name_cols if col in df_top_n.columns), 'Code')
    
    # 挑選最終要呈現的欄位
    final_output = df_top_n[['Code', name_col, '收盤價', 'AUM(億)', '月成交金額(億)']].reset_index(drop=True)
    
    # 將找到的名稱欄位 (例如 Name_x 或 基金簡稱) 統一重新命名為乾淨的 'ETF名稱'
    final_output = final_output.rename(columns={name_col: 'ETF名稱'})
    
    print(f"🚀 第二層排序完畢：已篩選出流動性最佳的前 {top_n} 檔 ETF。")
    return final_output

# --- 測試執行區塊 ---
if __name__ == "__main__":
    # 設定門檻：規模大於 500 億，並取流動性前 20 名
    best_etf_list = fetch_and_filter_etf(min_scale_ntd=50000000000, top_n=20)
    
    if best_etf_list is not None:
        print("\n🏆 AccuVest 雙層嚴選 ETF 名單 (規模達標 + 流動性 Top 20)：")
        print(best_etf_list)