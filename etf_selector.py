import yfinance as yf
import pandas as pd
from etf_crawler import fetch_and_filter_etf

def rank_by_blended_momentum(df_top_n):
    """
    第三層攻擊過濾 (終極大腦層)：計算多重時間框架綜合動能分數
    權重設定：50% 半年動能 + 30% 季動能 + 20% 月動能
    """
    print(f"\n⚡ 啟動進階大腦決策：正在計算前 {len(df_top_n)} 檔 ETF 的「三維綜合動能分數」...")
    
    momentum_data = []
    
    for index, row in df_top_n.iterrows():
        code = row['Code']
        ticker_symbol = f"{code}.TW"
        
        # 預設值初始化 (防呆機制)
        roc_20d, roc_60d, roc_120d, blended_score = 0.0, 0.0, 0.0, 0.0
        
        try:
            # 為了確保能拿到 120 個「交易日」，我們將請求期間拉長為一年 (1y)
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1y")
            
            if len(hist) > 0:
                latest_price = hist['Close'].iloc[-1]
                
                # 計算 20 天動能 (約一個月)
                if len(hist) >= 20:
                    price_20d = hist['Close'].iloc[-20]
                    roc_20d = ((latest_price - price_20d) / price_20d) * 100
                    
                # 計算 60 天動能 (約一季)
                if len(hist) >= 60:
                    price_60d = hist['Close'].iloc[-60]
                    roc_60d = ((latest_price - price_60d) / price_60d) * 100
                    
                # 計算 120 天動能 (約半年)
                if len(hist) >= 120:
                    price_120d = hist['Close'].iloc[-120]
                    roc_120d = ((latest_price - price_120d) / price_120d) * 100
                
                # 計算綜合分數
                # 備註：若 ETF 上市不滿半年，roc_120d 會是 0，導致總分較低。
                # 這完全符合我們「偏好經過市場長期檢驗的成熟標的」之投資哲學。
                blended_score = (roc_120d * 0.5) + (roc_60d * 0.3) + (roc_20d * 0.2)
                
        except Exception as e:
            # 若發生網路錯誤或該 ETF 無資料，則全部維持 0
            pass 
            
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
        # 呼叫最新版的動能計算函式
        final_attack_list = rank_by_blended_momentum(safe_etf_list)
        
        print(f"\n🎯 最終決策清單 (綜合動能最強 Top 5)：")
        
        # 調整輸出的欄位，讓你能一眼看穿它的三個時間維度
        display_cols = ['Code', 'ETF名稱', '近120日漲幅(%)', '近60日漲幅(%)', '近20日漲幅(%)', '綜合動能分數']
        # 將最強的前 5 名 ETF 匯出成 JSON 檔案，供推播層讀取
        final_attack_list.head(5).to_json('top_etfs.json', orient='records', force_ascii=False)
        print("📁 已經將最強標的存入 top_etfs.json")
    else:
        print("❌ 系統中斷：無法從資料獲取層取得有效名單。")