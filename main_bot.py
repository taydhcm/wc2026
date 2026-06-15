import time
import asyncio
from modules.data_crawler import FootballDataCrawler
from modules.db_manager import DatabaseManager
from modules.feature_engineering import FeatureEngineer
from modules.modeling import WorldCupModel
from modules.polymarket_client import PolymarketClient
from modules.edge_calculator import EdgeCalculator
from modules.kelly_criterion import KellyCriterion
from modules.telegram_ops import TelegramBot
from config.api_keys import FOOTBALL_API_KEY, DB_CONFIG, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.logger import logger
import json

class MainBot:
    def __init__(self):
        # Khởi tạo các module
        #self.crawler = FootballDataCrawler(api_key=FOOTBALL_API_KEY)
        self.crawler = FootballDataCrawler(api_key=FOOTBALL_API_KEY, season=2025)
        self.db = DatabaseManager(db_config=DB_CONFIG)
        self.fe = FeatureEngineer()
        self.model = WorldCupModel()
        
        # Load ví (giả định đã tạo file json)
        with open("config/poly_wallet.json", "r") as f:
            wallet = json.load(f)
        self.poly = PolymarketClient(wallet["private_key"], wallet["funder_address"])
        
        self.edge_calc = EdgeCalculator()
        self.kelly = KellyCriterion(fraction=0.1) # Dùng 10% Kelly
        self.tg = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

    async def run_cycle(self):
        """Vòng lặp thực thi chiến lược cho mỗi trận đấu."""
        logger.info("Bắt đầu chu kỳ quét kèo mới...")
        
        # 1. Lấy dữ liệu trận đấu sắp diễn ra
        fixtures = self.crawler.get_upcoming_fixtures()
        if fixtures.empty:
            return

        for _, match in fixtures.iterrows():
            # 2. Xử lý Feature & Dự đoán xác suất
            features = self.fe.build_match_features(match.to_dict())
            win_prob = self.model.predict_match_probability(features)
            
            # 3. Lấy dữ liệu từ Polymarket để tính Edge
            # Giả định token_id được map từ fixture_id
            token_id = f"token_{match['fixture_id']}" 
            market = self.poly.get_market_depth(token_id)
            
            if market:
                # 4. Tính toán Net Edge
                edge_data = self.edge_calc.get_net_edge(
                    model_prob=win_prob,
                    market_best_ask=market['best_ask'],
                    market_best_bid=market['best_bid'],
                    liquidity_volume=market['best_ask_size'],
                    order_size=100 # Giả định kích thước lệnh thử nghiệm
                )
                
                # 5. Quyết định đặt lệnh
                if edge_data['is_profitable']:
                    bet_size = self.kelly.calculate_bet_size(
                        edge_data['net_edge'], market['best_ask'], bankroll=1000
                    )
                    
                    msg = self.tg.format_trade_alert(match.to_dict(), edge_data['net_edge'], market['best_ask'])
                    await self.tg.send_message(msg)
                    logger.info(f"Cảnh báo kèo thơm: {match['home_team_name']} vs {match['away_team_name']}")

    async def start(self):
        """Chạy vòng lặp vô hạn."""
        while True:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp chính: {e}")
            
            # Nghỉ 1 tiếng trước khi quét lại (Tránh Rate Limit của API)
            await asyncio.sleep(3600)

if __name__ == "__main__":
    bot = MainBot()
    asyncio.run(bot.start())
