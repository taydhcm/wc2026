# wc2026-poly-hunter

Khung dự án Python cho "World Cup 2026 Edge Hunter" theo hướng Polygon/Polymarket.

## Cấu trúc
- `main_bot.py`: chạy pipeline 2 chiều (crawl -> model -> edge -> kelly -> Telegram)
- `modules/`: các lớp logic (data_crawler, polymarket_client, db_manager, ...)
- `config/`: api keys & `poly_wallet.json` (private key đã mã hóa - placeholder)
- `data/`: dữ liệu chạy/ghi log/snapshot

## Chạy

### 1) Cài deps
```bash
pip install -r requirements.txt
```

### 2) Dry-run
```bash
python main_bot.py --dry-run
```

## Lưu ý bảo mật
- Không commit private key thật.
- `config/poly_wallet.json` chỉ là placeholder.

