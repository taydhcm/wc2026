import time
import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.constants import POLYGON

logger = logging.getLogger(__name__)

class PolymarketClient:
    """
    Module tương tác với Orderbook của Polymarket.
    Chuyên xử lý lấy giá, tính xác suất thực tế và đặt lệnh Limit chống trượt giá.
    """
    
    def __init__(self, private_key: str, funder_address: str):
        # Khởi tạo client kết nối trực tiếp với mạng Polygon Mainnet
        self.host = "https://clob.polymarket.com"
        self.chain_id = POLYGON
        self.client = ClobClient(
            host=self.host,
            key=private_key,
            chain_id=self.chain_id,
            funder=funder_address
        )
        
        # Khởi tạo và thiết lập API credentials (Bắt buộc để đặt lệnh)
        try:
            self.client.set_api_creds(self.client.create_or_derive_api_creds())
            logger.info("Đã kết nối và xác thực thành công với Polymarket CLOB.")
        except Exception as e:
            logger.error(f"Lỗi xác thực ví Polymarket: {e}")

    def get_market_depth(self, token_id: str) -> dict:
        """
        Quét sổ lệnh (Orderbook) để lấy giá Bid/Ask tốt nhất và khối lượng thanh khoản.
        token_id: ID của tùy chọn (Ví dụ: ID của cổ phiếu "Yes" cho việc Brazil thắng).
        """
        try:
            # Lấy Orderbook Level 2
            orderbook = self.client.get_order_book(token_id)
            
            if not orderbook.bids or not orderbook.asks:
                logger.warning(f"Thanh khoản quá mỏng hoặc token_id {token_id} không hợp lệ.")
                return None
                
            best_bid = float(orderbook.bids[0].price)
            best_bid_size = float(orderbook.bids[0].size)
            best_ask = float(orderbook.asks[0].price)
            best_ask_size = float(orderbook.asks[0].size)
            
            # Tính Implied Probability (Xác suất thị trường ngầm định) bằng Mid-price
            implied_prob = (best_bid + best_ask) / 2
            
            # Spread (Độ chênh lệch) - Spread càng rộng, thanh khoản càng rủi ro
            spread = best_ask - best_bid
            
            return {
                "token_id": token_id,
                "best_bid": best_bid,
                "best_bid_size": best_bid_size,
                "best_ask": best_ask,
                "best_ask_size": best_ask_size,
                "implied_prob": implied_prob,
                "spread": spread
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi quét Orderbook cho token {token_id}: {e}")
            return None

    def execute_limit_buy(self, token_id: str, size: float, max_price: float) -> dict:
        """
        Thực hiện lệnh MUA giới hạn (Limit Buy).
        max_price: Giá TỐI ĐA mày chấp nhận mua để tránh bị Slippage.
        """
        logger.info(f"Chuẩn bị đặt lệnh BUY token {token_id} | Size: {size} | Max Price: {max_price}")
        
        # Kiểm tra Orderbook thực tế trước khi đặt lệnh
        market = self.get_market_depth(token_id)
        if not market:
            return {"status": "error", "message": "Không đọc được Orderbook"}
            
        if market["best_ask"] > max_price:
            logger.warning(f"Hủy lệnh: Giá Ask hiện tại ({market['best_ask']}) cao hơn Max Price ({max_price}).")
            return {"status": "canceled", "message": "Vượt quá ngưỡng Slippage cho phép"}

        # Nếu giá tốt, tiến hành tạo và gửi lệnh
        try:
            order_args = OrderArgs(
                price=max_price,          # Đặt ở mức giá max mày chịu được
                size=size,                # Số lượng share (cổ phiếu) muốn mua
                side="BUY",               # Hành động: Mua
                token_id=token_id         # Mã token của cửa cược
            )
            
            # Sử dụng GTC (Good Till Canceled) hoặc FOK (Fill Or Kill)
            # Ở Polymarket, nên dùng FOK nếu muốn khớp ngay lập tức hoặc hủy toàn bộ
            signed_order = self.client.create_order(
                order_args, 
                order_type=ApiOrderType.FOK 
            )
            
            response = self.client.post_order(signed_order)
            logger.info(f"Đặt lệnh thành công! Chi tiết: {response}")
            return {"status": "success", "data": response}
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi lệnh giao dịch: {e}")
            return {"status": "error", "message": str(e)}

# ==========================================
# KHỐI TEST NHANH 
# ==========================================
if __name__ == "__main__":
    import json
    
    # Load config từ file an toàn
    # Giả định mày lưu Private Key vào file config/poly_wallet.json
    # { "private_key": "0x...", "funder_address": "0x..." }
    try:
        with open("../config/poly_wallet.json", "r") as f:
            wallet = json.load(f)
            
        poly_client = PolymarketClient(
            private_key=wallet["private_key"],
            funder_address=wallet["funder_address"]
        )
        
        # Test 1: Đọc thử một Token ID (Mã này lấy từ URL của Polymarket hoặc API)
        # Ví dụ một mã Token ID giả định
        test_token = "0x25a6eb81427517c2f0f5b9d3184ebf79116c4f74d4df0ee8e61cb05f6d895b60" 
        
        print("--- FETCHING MARKET DEPTH ---")
        depth = poly_client.get_market_depth(test_token)
        if depth:
            print(f"Giá Bid tốt nhất: {depth['best_bid']} (Vol: {depth['best_bid_size']})")
            print(f"Giá Ask tốt nhất: {depth['best_ask']} (Vol: {depth['best_ask_size']})")
            print(f"Xác suất thị trường (Implied Prob): {depth['implied_prob']*100:.2f}%")
            print(f"Độ giãn spread: {depth['spread']:.4f}")
            
    except FileNotFoundError:
        print("Chưa có file poly_wallet.json. Hãy tạo file chứa private_key để test.")