# ==========================================
# 模組 2: 核心大腦層 (strategy_brain.py) - 終極重構版 V4
# ==========================================
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
        優先級：連續升息斷路器 > 解倒掛+降息逃命 > 3MMA基本面攻擊
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
            "asset_allocation": {"00881": 0, "00679B": 0, "CASH": 100},
            "reason": "指標數據不完整或訊號不明確，等待市場方向。"
        }

        # 預先提取利率與就業資料 (多個優先級會用到)
        rate_list = safety.get('fed_rate', []) if safety else []
        nfp_list = safety.get('nfp_additions', []) if safety else []
        cpi_list = safety.get('cpi_yoy', []) if safety else []
        # ==========================================
        # 優先級 1：通膨斷路器 2.0 (Exception) - 結合 NFP 就業防呆
        # ==========================================

        if len(rate_list) >= 4 and len(cpi_list) > 0:
            current_cpi = cpi_list[-1]

            # 判斷是否「暴力升息」：最新利率大於三個月前 (容許中間有未開會的平緩期)
            is_aggressive_hiking = (rate_list[-1] > rate_list[-4])
            
            # 判斷就業市場是否已經崩潰 (最近兩個月 NFP 是否為負)
            is_labor_crashing = len(nfp_list) >= 2 and (nfp_list[-1] < 0 and nfp_list[-2] < 0)

            # 當 Fed 為了抑制惡性通膨 (CPI>=4) 而連續升息時，資金派對結束
            if current_cpi >= 4.0 and is_aggressive_hiking:
                # 💡 加入 NFP 雙重確認：如果就業已經崩潰，聯準會將轉向，取消清倉指令
                if is_labor_crashing:
                    print("🧠 [大腦推演] 偵測到高通膨，但 NFP 連續負成長，預期聯準會即將降息救市，解除清倉斷路器。")
                    # 不 return decision，讓程式繼續往下走到「優先級 2」去買美債避險
                else:
                    decision.update({
                        "status": "STAGFLATION_CRASH",
                        "action": "【全面清倉】",
                        "asset_allocation": {"00881": 0, "00679B": 0, "CASH": 100},
                        "reason": f"偵測到高通膨 ({current_cpi:.1f}%) 且升息，且就業尚未衰退，啟動斷路器避開股債雙殺。"
                    })
                    return decision # 觸發最高警報，直接返回，不看其他指標

        # ==========================================
        # 優先級 2：終極逃命信號 (解倒掛 + 聯準會緊急降息)
        # ==========================================
        if yield_data and len(rate_list) >= 2:
            values = yield_data.get('values', [])
            if len(values) >= 30:
                current_spread = values[-1]
                past_spreads = values[:-1]
                
                # 檢查過去是否倒掛
                was_inverted = any(val < 0 for val in past_spreads)
                # 檢查 Fed 是否開始降息 (利率拐點向下)
                is_cutting_rates = rate_list[-1] < rate_list[-2]

                # 剛倒掛時不走；解除倒掛且搭配緊急降息，才是真正的衰退崩盤
                if was_inverted and current_spread > 0 and is_cutting_rates:
                    decision.update({
                        "status": "RECESSION_CRASH",
                        "action": "【緊急避險】",
                        "asset_allocation": {"00881": 0, "00679B": 100, "CASH": 0},
                        "reason": "殖利率解除倒掛，且 Fed 開始預防性降息，實體經濟確認步入衰退，資金轉入美債避險。"
                    })
                    return decision

        # ==========================================
        # 優先級 3：基本面攻擊 (導入 3MMA 移動平均濾除雜訊)
        # ==========================================
        if orders and taiwan:
            order_values = orders.get('values', [])
            # 確保有足夠的月份數據來計算 3MMA (至少需要 4 個月來比較本月與上月的 3MMA)
            if len(order_values) >= 4:
                # 計算最近三個月的平均 (Current 3MMA)
                current_3mma = sum(order_values[-3:]) / 3
                # 計算上個月看回去的三個月平均 (Previous 3MMA)
                prev_3mma = sum(order_values[-4:-1]) / 3
                
               # 3MMA 進場點：轉為正成長，或是擺脫谷底連續向上
                is_order_3mma_up = (current_3mma > 0) or (current_3mma > prev_3mma)
            else:
                # 若數據不足，退回單月判斷防呆
                is_order_3mma_up = order_values[-1] > 0 if order_values else False


            tw_score = taiwan.get('score', 0)
            tw_color = taiwan.get('color_name', '未知')

            # 攻擊條件：訂單指標轉好，且台灣景氣非藍燈 (>=17分，即黃藍燈以上)
            if is_order_3mma_up and tw_score >= 17:
                # 判斷資金面：Fed 是否已經停止升息或開始降息 (資金回流訊號)
                is_fed_friendly = len(rate_list) >= 2 and (rate_list[-1] <= rate_list[-2])
                
                reason_msg = f"美國製造業訂單 3MMA 趨勢向上，且台灣燈號({tw_color})脫離低迷。"
                if is_fed_friendly:
                    reason_msg += " 疊加 Fed 停止升息/降息，資金回流新興市場，強烈建議進場。"

                decision.update({
                    "status": "BULL_MARKET",
                    "action": "【建議進場/抱緊】",
                    "asset_allocation": {"00881": 100, "00679B": 0, "CASH": 0},
                    "reason": reason_msg
                })
                return decision
            else:
                # 💡 數據轉弱，給出明確的空頭防守指令，而不是預設的「等待市場方向」
                decision.update({
                    "status": "BEAR_MARKET",
                    "action": "【空頭衰退：出清觀望】",
                    "asset_allocation": {"00881": 0, "00679B": 0, "CASH": 100},
                    "reason": f"美國訂單 3MMA 動能疲軟或台灣燈號({tw_color})落入收縮區，基本面轉弱，建議保留現金。"
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
