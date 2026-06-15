import logging

logger = logging.getLogger(__name__)

class EdgeCalculator:
    """
    Module tính toán lợi thế thực tế (Net Edge) cho các kèo trên Polymarket.
    Tích hợp mô hình bù trừ Slippage và phí giao dịch.
    """
    
    def __init__(self, gas_fee_estimate: float = 0.01, min_edge_threshold: float = 0.05):
        """
        gas_fee_estimate: Phí ước tính (quy đổi ra đơn vị giá cổ phiếu 0-1).
        min_edge_threshold: Ngưỡng tối thiểu để bot quyết định xuống tiền (ví dụ 5%).
        """
        self.gas_fee = gas_fee_estimate
        self.min_edge = min_edge_threshold

    def calculate_slippage(self, order_size: float, liquidity_depth: float) -> float:
        """
        Tính toán Slippage dự kiến dựa trên độ sâu sổ lệnh.
        Công thức cơ bản: Trượt giá tỉ lệ nghịch với thanh khoản có sẵn.
        """
        if liquidity_depth <= 0:
            return 1.0 # Thanh khoản = 0, Slippage vô cực
            
        # Hệ số trượt giá (thường dao động 0.01 - 0.05 tùy sàn)
        slippage_factor = 0.02
        return (order_size / liquidity_depth) * slippage_factor

    def get_net_edge(self, model_prob: float, market_best_ask: float, 
                     market_best_bid: float, liquidity_volume: float, order_size: float) -> dict:
        """
        Tính toán lợi thế cuối cùng sau khi trừ mọi chi phí.
        
        Args:
            model_prob: Xác suất thắng dự đoán bởi Model.
            market_best_ask: Giá mua tốt nhất hiện tại trên sàn.
            market_best_bid: Giá bán tốt nhất hiện tại trên sàn.
            liquidity_volume: Tổng khối lượng khớp được ở giá tốt nhất.
            order_size: Khối lượng mày định đặt lệnh.
        """
        # 1. Tính Slippage thực tế cho khối lượng đặt lệnh
        slippage = self.calculate_slippage(order_size, liquidity_volume)
        
        # 2. Tính giá thực tế mày phải trả (Effective Price)
        # Nếu mua (Buy Yes), giá thực tế = Best Ask + Slippage
        effective_price = market_best_ask + slippage
        
        # 3. Net Edge = Xác suất thắng dự đoán - Chi phí thực tế
        net_edge = model_prob - effective_price - self.gas_fee
        
        is_profitable = net_edge >= self.min_edge
        
        return {
            "net_edge": round(net_edge, 4),
            "effective_price": round(effective_price, 4),
            "slippage": round(slippage, 4),
            "is_profitable": is_profitable,
            "decision": "BUY" if is_profitable else "WAIT"
        }

# ==========================================
# KHỐI TEST NHANH 
# ==========================================
if __name__ == "__main__":
    calc = EdgeCalculator(gas_fee_estimate=0.005) # Phí giả định trên Polygon thấp
    
    # Kịch bản: Model tin 65% thắng, sàn đang bán giá 0.55
    # Nhưng thanh khoản mỏng (cần mua 500 share mà sàn chỉ có 1000 share ở giá đó)
    result = calc.get_net_edge(
        model_prob=0.65,
        market_best_ask=0.55,
        market_best_bid=0.53,
        liquidity_volume=1000,
        order_size=500
    )
    
    print("--- KẾT QUẢ TÍNH TOÁN EDGE ---")
    for k, v in result.items():
        print(f"{k}: {v}")