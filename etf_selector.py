import yfinance as yf
import pandas as pd
import numpy as np
from etf_crawler import fetch_and_filter_etf

def rank_by_blended_momentum(df_top_n):
    """
    第三層攻擊過濾 (終極防禦版)：計算多重時間框架綜合動能分數
    權重設定：50% 半年 + 30% 季 + 20% 月
    """
    print(f"\n⚡ 啟動進階大腦決策：正在計算前 {len(df_top_n)} 檔 ETF 的「三維綜合動能分數」...")
    
    momentum_data = []
    
    for index, row in df_top_n.iterrows():
        code = row['Code']
        ticker_symbol = f"{code}.TW"
        
        # 1. 預設值全數初始化為 0.0
        roc_20d, roc_60d, roc_120d, blended_score = 0.0, 0.0, 0.0, 0.0
        
        try:
            # 關閉 yfinance 煩人的錯誤訊息
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1y")
            
            # 🌟 核心防護 1：清掉沒有收盤價的「髒資料」
            if not hist.empty and 'Close' in hist.columns:
                hist = hist.dropna(subset=['Close'])
            
            if len(hist) > 0:
                latest_price = hist['Close'].iloc[-1]
                
                # 計算 20 天動能
                if len(hist) >= 20:
                    price_20d = hist['Close'].iloc[-20]
                    if price_20d > 0: # 避免除以 0
                        roc_20d = ((latest_price - price_20d) / price_20d) * 100
                        
                # 計算 60 天動能
                if len(hist) >= 60:
                    price_60d = hist['Close'].iloc[-60]
                    if price_60d > 0:
                        roc_60d = ((latest_price - price_60d) / price_60d) * 100
                        
                # 計算 120 天動能
                if len(hist) >= 120:
                    price_120d = hist['Close'].iloc[-120]
                    if price_120d > 0:
                        roc_120d = ((latest_price - price_120d) / price_120d) * 100
                
                # 計算綜合分數
                blended_score = (roc_120d * 0.5) + (roc_60d * 0.3) + (roc_20d * 0.2)
                
        except Exception as e:
            # 發生任何錯誤，就當作動能為 0
            pass 
            
        # 🌟 核心防護 2：強迫把所有 NaN 轉回 0.0 (避免 JSON 出現 null)
        roc_20d = 0.0 if pd.isna(roc_20d) else roc_20d
        roc_60d = 0.0 if pd.isna(roc_60d) else roc_60d
        roc_120d = 0.0 if pd.isna(roc_120d) else roc_120d
        blended_score = 0.0 if pd.isna(blended_score) else blended_score
            
        momentum_data.append({
            'Code': code,
            '近20日漲幅(%)': round(roc_20d, 2),
            '近60日漲幅(%)': round(roc_60d, 2),
            '近120日漲幅(%)': round(roc_120d, 2),
            '綜合動能分數': round(blended_score, 2)
        })
        
    # 將計算結果轉換為 DataFrame 並與原表合併
    df_momentum = pd.DataFrame(momentum_data)
    df_merged = pd.merge(df_top_n, df_momentum, on='Code', how='inner')
    
    # 執行最終排序：依據「綜合動能分數」由高到低排序
    df_final = df_merged.sort_values(by='綜合動能分數', ascending=False).reset_index(drop=True)
    
    print("✅ 大腦運算完畢！三維動能排序完成。")
    return df_final


# ==========================================
# 系統主程序
# ==========================================
if __name__ == "__main__":
    print("🚀 AccuVest 系統啟動：開始執行選股管線...\n")
    
    safe_etf_list = fetch_and_filter_etf(min_scale_ntd=50000000000, top_n=20)
    
    if safe_etf_list is not None and not safe_etf_list.empty:
        final_attack_list = rank_by_blended_momentum(safe_etf_list)
        
        # 🌟 將最強的前 5 名存入 JSON (供 LINE 推播讀取)
        final_attack_list.head(5).to_json('top_etfs.json', orient='records', force_ascii=False)
        print("\n📁 已經將最強標的存入 top_etfs.json")
        
        print(f"\n🎯 最終決策清單 (綜合動能最強 Top 5)：")
        display_cols = ['Code', 'ETF名稱', '近120日漲幅(%)', '近60日漲幅(%)', '近20日漲幅(%)', '綜合動能分數']
        # 🌟 確保存在欄位才印出，防止終端機當機
        existing_cols = [c for c in display_cols if c in final_attack_list.columns]
        print(final_attack_list[existing_cols].head(5).to_string())
    else:
        print("❌ 系統中斷：無法從資料獲取層取得有效名單。")
