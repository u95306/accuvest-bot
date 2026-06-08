import json

class AccuVestBrain:
    def __init__(self):
        # 定義四個資料來源的檔案路徑
        self.data_files = {
            'orders': 'macro_data.json',
            'yield': 'yield_curve.json',
            'safety': 'safety_data.json',
            'taiwan': 'taiwan_light.json'
        }

    def _load_json(self, key):
        """共用的 JSON 讀取函式"""
        try:
            with open(self.data_files[key], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            # 實務上可以加入 logging
            return None

    def make_final_decision(self):
        """
        大腦核心：執行多指標權重裁決 (Priority Logic)
        優先級：通膨防呆 > Sahm衰退崩盤 > 10Y3M解倒掛 > 台灣過熱防護 > 美國訂單攻擊
        """
        # 1. 載入所有感應器數據
        orders = self._load_json('orders')
        yield_data = self._load_json('yield')
        safety = self._load_json('safety')
        taiwan = self._load_json('taiwan')

        # 初始化預設決策 (最保守狀態)
        decision = {
            "status": "WAIT_AND_SEE",
            "action": "保持觀望",
            "asset_allocation": {"股票型基金": 0, "美國債券": 0, "現金": 100},
            "reason": "指標數據不完整或訊號不明確，等待市場方向。"
        }

        # 預先提取利率與就業資料 (多個優先級會用到)
        cpi_list = safety.get('cpi_yoy', []) if safety else []
        unrate_list = safety.get("unrate", []) if safety else []  # 用於薩姆規則
        # ==========================================
        # 優先級 1：通膨斷路器 2.0 (Exception) - 極簡 CPI 防呆
        # ==========================================

        if len(cpi_list) > 0:
            current_cpi = cpi_list[-1]
            if current_cpi >= 4.0:
                decision.update({
                    "status": "STAGFLATION_CRASH",
                    "action": "【全面清倉】",
                    "asset_allocation": {"股票型基金": 0, "美國債券": 0, "現金": 100},
                    "reason": f"偵測到惡性通膨 (CPI: {current_cpi:.1f}%)，強制啟動股債雙殺斷路器，全數轉為現金避險。"
                })
                return decision
        
        # ==========================================
        # 優先級 2：Sahm Rule (薩姆規則衰退確認)
        # ==========================================
        # Sahm Rule 公式：近3個月失業率平均 - 過去12個月最低失業率 >= 0.5%
        if len(unrate_list) >= 12:
            current_3m_avg = sum(unrate_list[-3:]) / 3
            past_12m_min = min(unrate_list[-12:])
            sahm_value = current_3m_avg - past_12m_min

            if sahm_value >= 0.5:
                decision.update({
                    "status": "SAHM_RECESSION_CRASH",
                    "action": "【衰退崩盤：緊急清倉】",
                    "asset_allocation": {"股票型基金": 0, "美國債券": 80, "現金": 20},
                    "reason": f"觸發 Sahm Rule 衰退警報 (指標值: {sahm_value:.2f}%)，實體經濟實質步入衰退主跌段，資金緊急轉入美債避險。"
                })
                return decision    

        # ==========================================
        # 優先級 3：終極逃命信號 (解倒掛)
        # ==========================================
        if yield_data:
            values = yield_data.get('values', [])
            # 確保資料量足夠（過去一年的交易日）
            if len(values) >= 250:
                current_spread = values[-1]

                # 🔒 硬門檻 1：歷史數據雜訊過濾
                # 過去一年的數據中，必須實質倒掛（< 0）累積超過 60 天，確立其經濟週期意義
                past_year_spreads = values[-250:-20]  # 排除最近一個月的波動
                inversion_days = sum(1 for val in past_year_spreads if val < 0)
                was_substantial_inverted = inversion_days >= 60

                # 🔒 硬門檻 2：前瞻性景氣引爆線（完全不看 Fed 是否降息，避免落後）
                # 當前利差突破 0.5%，代表美債市場已正式定價「急速陡峭化」的衰退主跌段
                is_recession_triggered = current_spread > 0.5

                # 剛倒掛時不走；解除倒掛且搭配緊急降息，才是真正的衰退崩盤
                # 兩道硬門檻同時滿足 ➔ 觸發斷路器，直接 return 跳出
                if was_substantial_inverted and is_recession_triggered:
                    decision.update(
                        {
                            "status": "RECESSION_STEEPENING_CRASH",
                            "action": "【中期防禦型減碼】",
                            # 股票移至美債擴大收益，並且保留 30% 現金作為半年後台股跌深的抄底子彈
                            "asset_allocation": {"股票型基金": 0, "美國債券": 70, "現金": 30},
                            "reason": f"確認觸發衰退斷路器。T10Y2Y 歷史實質倒掛達 {inversion_days} 天。當前利差強勢突破 0.5% 門檻（現為 {current_spread:.2f}%），債市確認進入衰退陡峭化階段。強制執行中期防禦配置，鎖定美債利潤並保留現金子彈。",
                        }
                    )
                    return decision  # 絕對否決權，乾淨俐落

        
        # 預先提取與計算台灣燈號與美國訂單數據
        tw_scores = taiwan.get('scores', []) if taiwan else []
        tw_colors = taiwan.get('color_names', []) if taiwan else []
        tw_score = tw_scores[-1] if tw_scores else 0
        tw_color = tw_colors[-1] if tw_colors else '未知'
        
        is_order_3mma_up = False
        if orders:
            order_3mma_values = orders.get('values', [])
            # 💡 既然 values 已經是 3MMA 的數值，要判斷趨勢是否向上：
            # 只要最新一個月（[-1]）大於上個月（[-2]）即可！
            if len(order_3mma_values) >= 2:
                is_order_3mma_up = order_3mma_values[-1] > order_3mma_values[-2]
        
        # ==========================================
        # 優先級 4：台灣景氣過熱防護 (連續三紅燈才收割)
        # ==========================================
        # 判斷是否連續三個月紅燈 (分數 >= 38)
        is_three_red_lights = len(tw_scores) >= 3 and all(s >= 38 for s in tw_scores[-3:])
        if is_three_red_lights:
            decision.update({
                "status": "OVERHEATED_DEFENSE",
                "action": "【過熱防禦：分批獲利了結】",
                "asset_allocation": {"股票型基金": 50, "美國債券": 20, "現金": 30},
                "reason": f"台灣景氣燈號已「連續 3 個月」亮出紅燈 (最新 {tw_score} 分)，確認市場處於極度狂熱末端，強制啟動防護，分批調節股票落袋為安。"
            })
            return decision
        

        # ==========================================
        # 優先級 5：基本面攻擊引擎 (藍燈買股票)
        # ==========================================
        # 只要美國訂單向上，不管台灣燈號是不是藍燈，果斷判定為牛市    
        if is_order_3mma_up:
            # 💡 關鍵判斷：如果前一個月還在過熱防禦狀態（例如 tw_scores[-2] 是紅燈 >=38），代表剛脫離紅燈
            is_just_exited_red = len(tw_scores) >= 2 and tw_scores[-2] >= 38
            
            if is_just_exited_red:
                decision.update({
                    "status": "BULL_MARKET_RECOVERY",
                    "action": "【牛市初試：部分資金回補】",
                    # 從原先防禦的股票 50% 提高到 75%（即買回 25% 的股票）
                    "asset_allocation": {"股票型基金": 75, "美國債券": 10, "現金": 15},
                    "reason": "台灣燈號已脫離連續紅燈(過熱解除)，且美國製造業訂單 3MMA 趨勢強勢向上。策略啟動「第一階段分批買回 25%」，保留部分現金防禦高檔震盪。"
                })
            else:
                # 如果已經脫離紅燈很久了，美國訂單依舊強勁，直接全軍突擊
                decision.update({
                    "status": "BULL_MARKET",
                    "action": "【全軍突擊/抱緊】",
                    "asset_allocation": {"股票型基金": 100, "美國債券": 0, "現金": 0},
                    "reason": "美國製造業訂單 3MMA 趨勢強勢向上，且台灣無過熱疑慮，確認為多頭擴張期，100% 佈局強勢 ETF。"
                })
            return decision
        
        # ==========================================
        # 優先級 6：常規修正期
        # ==========================================
        # 美國訂單向下，且沒有觸發任何崩盤或過熱指標
        if not is_order_3mma_up:
            decision.update({
                "status": "MARKET_CORRECTION",
                "action": "【常規修正：出清觀望】",
                #常規修正不該清倉。保留 40% 股票參與市場，30% 美債防禦，30% 現金隨時加碼。
                "asset_allocation": {"股票型基金": 40, "美國債券": 30, "現金": 30},
                "reason": f"美國訂單 3MMA 動能疲軟轉向，且台灣燈號({tw_color})尚未過熱，基本面轉入常規修正期，建議轉入避險資產等待落底。"
            })
            return decision

        # 若以上皆未觸發，維持預設的 WAIT_AND_SEE
        return decision
        

# ==========================================
# 執行與測試區塊
# ==========================================
if __name__ == "__main__":
    brain = AccuVestBrain()
    final_result = brain.make_final_decision()

    print("========================================")
    print("🎯 AccuVest 系統大腦最終決策報告")
    print("========================================")
    print(json.dumps(final_result, ensure_ascii=False, indent=4))
    print("========================================")
        
    # 【新增】將大腦的決策輸出為 JSON 檔案，供 LLM 層讀取
    with open('final_decision.json', 'w', encoding='utf-8') as f:
        json.dump(final_result, f, ensure_ascii=False, indent=4)
        
    print("✅ 大腦運算完畢！決策已儲存至 final_decision.json")
