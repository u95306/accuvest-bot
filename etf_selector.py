import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo 
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

def apply_score_smoothing(df_today, history_file='historical_scores.json'):
    """
    引入歷史平滑機制 (今日 40% + 昨日 60%)，降低短期雜訊。
    """
    print("🌊 啟動分數平滑機制...")
    yesterday_scores = {}
    
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            yesterday_scores = json.load(f)
            
    final_scores = []
    for index, row in df_today.iterrows():
        code = row['Code']
        today_score = row['綜合動能分數']
        
        yesterday_score = yesterday_scores.get(code, today_score)
        smoothed_score = (today_score * 0.4) + (yesterday_score * 0.6)
        final_scores.append(round(smoothed_score, 2))
        
    df_today['綜合動能分數'] = final_scores
    df_final = df_today.sort_values(by='綜合動能分數', ascending=False).reset_index(drop=True)
    
    # 存下最新的平滑分數供下次使用
    current_scores_dict = dict(zip(df_final['Code'], df_final['綜合動能分數']))
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(current_scores_dict, f, ensure_ascii=False, indent=4)
        
    return df_final

# ==========================================
# 系統主程序
# ==========================================
if __name__ == "__main__":
    print("🚀 AccuVest 系統啟動：開始執行選股管線...\n")
    
    taipei_tz = ZoneInfo("Asia/Taipei")
    now_in_taipei = datetime.now(taipei_tz)

    # 如果是星期一 (weekday() == 0) 才執行繁重的重新運算
    if now_in_taipei.weekday() == 0:
        print("📅 今日為週一，啟動核心動能計算與平滑機制...\n")
        safe_etf_list = fetch_and_filter_etf(min_scale_ntd=40000000000, top_n=30)
    
        if safe_etf_list is not None and not safe_etf_list.empty:
            
            # 1. 取得今日最新分數
            df_today = rank_by_blended_momentum(safe_etf_list)
            
            # 2. 套用平滑公式 (封裝後的乾淨呼叫)
            df_final = apply_score_smoothing(df_today)
            
            # 3. 輸出結果與儲存
            df_final.head(5).to_json('top_etfs.json', orient='records', force_ascii=False)
            print("\n📁 已經將平滑後的強勢標的存入 top_etfs.json")
            
            # --- 測試執行區塊 ---
            print(f"\n🎯 最終決策清單 (綜合動能最強 Top 5)：")
            display_cols = ['Code', 'ETF名稱', '近120日漲幅(%)', '近60日漲幅(%)', '近20日漲幅(%)', '綜合動能分數']
            existing_cols = [c for c in display_cols if c in df_final.columns]
            
            print(f"\n📊 目前排序依據：【近120日漲幅(%)】")
            # 💡 建立一個專供顯示用的 DataFrame，並依照 120 日漲幅降冪 (由大到小) 排序
            df_display = df_final.sort_values(by='近120日漲幅(%)', ascending=False)
            print(df_display[existing_cols].head(20).to_string())
            
        else:
            print("❌ 系統中斷：無法從資料獲取層取得有效名單。")
            
    else:
        # 非星期一，只需確認歷史檔案存在即可，不用重跑
        print(f"📅 今日為星期 {now_in_taipei.weekday() + 1}，非更新日。")
        if os.path.exists('top_etfs.json'):
            print(f"📦 偵測到歷史紀錄，直接沿用上週一的 ETF 排行榜資料。")
        else:
             print("⚠️ 警告：找不到上週的 top_etfs.json，可能會影響後續推播層運作。")
