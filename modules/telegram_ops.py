import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

class TelegramBot:
    """
    Module Telegram Bot: Thông báo kèo và nhận lệnh điều khiển từ xa.
    """
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.bot = Bot(token=token)

    async def send_message(self, text: str):
        """Gửi thông báo nhanh về máy điện thoại của mày."""
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Lỗi gửi Telegram: {e}")

    def format_trade_alert(self, match_info: dict, edge: float, price: float) -> str:
        """Định dạng message cảnh báo kèo thơm."""
        return (
            f"🚨 *CÓ KÈO THƠM WC2026*\n\n"
            f"⚽ *Trận:* {match_info['home_team']} vs {match_info['away_team']}\n"
            f"📈 *Edge:* `{edge*100:.2f}%`\n"
            f"💰 *Giá dự kiến:* `{price:.3f}`\n"
            f"--------------------------\n"
            f"Nhập `/buy_{match_info['fixture_id']}` để khớp lệnh."
        )

# ==========================================
# CẤU HÌNH HANDLER (Dùng cho main_bot.py)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Polymarket đã sẵn sàng! Chờ lệnh...")

async def handle_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi mày bấm lệnh /buy_xxxx từ Telegram."""
    command = update.message.text
    fixture_id = command.split('_')[1]
    
    # Logic tại đây: Gọi hàm thực thi mua từ polymarket_client.py
    await update.message.reply_text(f"Đang thực hiện mua trận {fixture_id}...")

def run_telegram_server(token: str):
    """Khởi chạy Bot Telegram (chạy vòng lặp lắng nghe lệnh)."""
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", handle_buy))
    
    logger.info("Telegram Bot đang lắng nghe...")
    app.run_polling()

# ==========================================
# KHỐI TEST NHANH 
# ==========================================
if __name__ == "__main__":
    # Test thử gửi 1 tin nhắn cảnh báo
    # Cần thay TOKEN của mày vào
    MY_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    MY_CHAT_ID = "YOUR_CHAT_ID"
    
    import asyncio
    
    async def main():
        bot = TelegramBot(MY_TOKEN, MY_CHAT_ID)
        test_match = {"home_team": "Brazil", "away_team": "England", "fixture_id": 12345}
        msg = bot.format_trade_alert(test_match, 0.08, 0.45)
        await bot.send_message(msg)
        print("Đã gửi tin nhắn test!")

    asyncio.run(main())