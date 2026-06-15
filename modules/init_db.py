import os
from sqlalchemy import create_engine, text

# Lấy đường dẫn thư mục gốc của project (nằm ngoài modules)
# File này đang ở trong modules/, nên cần quay lại 1 cấp
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(base_dir, "data", "wc2026_data.db")

engine = create_engine(f"sqlite:///{db_path}")

create_table_sql = """
CREATE TABLE IF NOT EXISTS wc26_fixtures (
    fixture_id INTEGER PRIMARY KEY,
    date TEXT,
    timestamp INTEGER,
    venue_name TEXT,
    status TEXT,
    home_team_name TEXT,
    away_team_name TEXT
);
"""

try:
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
        print(f"Đã tạo bảng thành công tại: {db_path}")
except Exception as e:
    print(f"Lỗi: {e}")