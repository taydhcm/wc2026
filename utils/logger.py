import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name="wc26_bot", log_file="logs/bot.log", level=logging.INFO):
    """
    Thiết lập logger với khả năng xoay vòng file (Rotating) để bảo vệ ổ cứng.
    """
    # Đảm bảo thư mục logs tồn tại
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Định dạng log: [Thời gian] [Level] [Tên Module] - [Nội dung]
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    # 1. Ghi log ra file (với xoay vòng: tối đa 5MB/file, giữ lại 3 file cũ)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # 2. Ghi log ra màn hình console (để theo dõi lúc đang chạy tay)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Thêm handlers vào logger
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Khởi tạo logger chung cho cả hệ thống
logger = setup_logger()