import logging

logger = logging.getLogger(__name__)

class KellyCriterion:
    """
    Module quản lý vốn bằng tiêu chí Kelly.
    Chỉ định tỷ lệ phần trăm (percentage) tài khoản được phép đặt cược cho mỗi trận đấu.
    """
    
    def __init__(self, fraction: float = 0.15):
        """
        fraction: Hệ số an toàn (Fractional Kelly). 
        Lời khuyên: Để 0.1 (10%) đến 0.2 (20%) để tránh biến động tài khoản quá mạnh.
        """
        self.fraction = fraction

    def calculate_bet_size(self, net_edge: float, market_prob: float, bankroll: float) -> float:
        """
        Tính toán khối lượng tiền (quy đổi ra số cổ phiếu) nên đặt.
        
        Công thức: f* = (Edge) / (Odds_decimal - 1)
        Với Binary Option: Odds_decimal = 1 / market_prob
        """
        if net_edge <= 0:
            return 0.0
            
        # market_prob là giá cổ phiếu hiện tại (ví dụ: 0.55)
        # Odds thập phân (b) = (1 / market_prob) - 1
        # Lưu ý: Nếu market_prob = 1.0 (trường hợp cực hiếm), tránh chia cho 0
        if market_prob >= 0.99: 
            return 0.0
            
        decimal_odds = 1.0 / market_prob
        b = decimal_odds - 1
        
        # Công thức Kelly cơ bản: f* = (bp - q) / b
        # p = xác suất thắng thực tế (market_prob + net_edge)
        # q = 1 - p
        p = market_prob + net_edge
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # Chỉ vào lệnh nếu Kelly dương (Edge thực sự tồn tại)
        if kelly_fraction <= 0:
            return 0.0
            
        # Áp dụng Fractional Kelly để giảm thiểu rủi ro (giảm độ biến động)
        safe_bet_fraction = kelly_fraction * self.fraction
        
        # Số tiền tuyệt đối nên vào lệnh
        bet_amount = bankroll * safe_bet_fraction
        
        return round(bet_amount, 2)

# ==========================================
# KHỐI TEST NHANH 
# ==========================================
if __name__ == "__main__":
    # Giả sử ví mày có 1000 USD trên Polymarket
    kelly = KellyCriterion(fraction=0.1) # Dùng 10% Kelly (cực kỳ an toàn)
    
    # Giả sử Edge là 10% (0.1) và giá hiện tại là 0.50
    bankroll = 1000
    net_edge = 0.10
    market_price = 0.50
    
    bet_size = kelly.calculate_bet_size(net_edge, market_price, bankroll)
    
    print("--- QUẢN LÝ VỐN KELLY ---")
    print(f"Số vốn hiện tại: {bankroll} USD")
    print(f"Edge dự kiến: {net_edge*100}%")
    print(f"Số tiền đề xuất vào lệnh: {bet_size} USD")
    print(f"-> Tương đương với {round(bet_size/market_price, 0)} cổ phiếu (shares)")