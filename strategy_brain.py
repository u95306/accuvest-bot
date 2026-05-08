# ==========================================
# 模組 2: 核心大腦層 (strategy_brain.py) - 終極重構版
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
        優先級：CPI 斷路器 > 殖利率避險 > 基本面攻擊(訂單+燈號)
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

        # ==========================================
        # 優先級 1：通膨斷路器 (Exception) - 防止股債雙殺
        # ==========================================
        if safety:
            cpi_list = safety.get('cpi_yoy', [])
            rate_list = safety.get('fed_rate', [])

            if len(cpi_list) > 0 and len(rate_list) > 1:
                current_cpi = cpi_list[-1]
                is_rate_hiking = rate_list[-1] > rate_list[-2]

                # 若 CPI >= 4% 且處於升息循環
                if current_cpi >= 4.0 and is_rate_hiking:
                    decision.update({
                        "status": "STAGFLATION_CRASH",
                        "action": "【全面清倉】",
                        "asset_allocation": {"00881": 0, "00679B": 0, "CASH": 100},
                        "reason": f"偵測到高通膨 ({current_cpi:.1f}%) 且聯準會持續升息，啟動 2022 斷路器避開股債雙殺。"
                    })
                    return decision # 觸發最高警報，直接返回，不看其他指標

        # ==========================================
        # 優先級 2：殖利率避險 (Defense) - 預警經濟衰退
        # ==========================================
        if yield_data:
            values = yield_data.get('values', [])
            if len(values) >= 30:
                current_spread = values[-1]
                past_spreads = values[:-1]
                # 檢查過去是否倒掛
                was_inverted = any(val < 0 for val in past_spreads)

                # 解除倒掛並陡峭化：最危險的時刻
                if was_inverted and current_spread > 0:
                    decision.update({
                        "status": "RECESSION_HEDGE",
                        "action": "【警示減碼/轉向避險】",
                        "asset_allocation": {"00881": 0, "00679B": 100, "CASH": 0},
                        "reason": "10Y-2Y 殖利率曲線解除倒掛並急速陡峭化，衰退警報確認，資金轉入美債防禦。"
                    })
                    return decision

        # ==========================================
        # 優先級 3：基本面攻擊 (Growth) - 訂單與台灣燈號雙重確認
        # ==========================================
        if orders and taiwan:
            order_values = orders.get('values', [])
            if len(order_values) >= 3:
                m2, m1, m0 = order_values[-3], order_values[-2], order_values[-1]

                # 訂單邏輯：正在正成長，或從負值止跌回升
                is_order_positive = m0 > 0
                is_order_rebounding = (m1 < 0) and (m0 > m1) and (m1 <= m2)

                tw_score = taiwan.get('score', 0)
                tw_color = taiwan.get('color_name', '未知')

                # 攻擊條件：訂單指標轉好，且台灣景氣非藍燈 (>=17分，即黃藍燈以上)
                if (is_order_positive or is_order_rebounding) and tw_score >= 17:
                    decision.update({
                        "status": "BULL_MARKET",
                        "action": "【建議進場/抱緊】",
                        "asset_allocation": {"00881": 100, "00679B": 0, "CASH": 0},
                        "reason": f"美國製造業訂單動能轉強，且台灣景氣燈號({tw_color})確認脫離低迷區，基本面擴張中。"
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
