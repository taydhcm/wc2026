import pandas as pd
import logging
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Module quản lý kết nối và đẩy dữ liệu vào SQLite Database.
    SQLite gọn nhẹ, không cần driver phức tạp.
    """
    
    def __init__(self, db_config: dict):
        """
        Khởi tạo Engine kết nối SQLite.
        db_config chứa 'db_path' như đã cấu hình trong api_keys.py
        """
        # Trích xuất đường dẫn từ dictionary
        db_path = db_config.get("db_path", "data/wc2026_data.db")
        
        # Chuỗi kết nối cho SQLite
        self.connection_string = f"sqlite:///{db_path}"
        
        try:
            self.engine = create_engine(self.connection_string, echo=False)
            logger.info(f"Đã khởi tạo kết nối Database tại: {db_path}")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo Database Engine: {e}")
            raise

    def insert_dataframe(self, df: pd.DataFrame, table_name: str, if_exists: str = 'append'):
        """
        Đẩy dữ liệu vào SQLite.
        """
        if df.empty:
            return False

        try:
            df.to_sql(name=table_name, con=self.engine, if_exists=if_exists, index=False)
            logger.info(f"Đã insert thành công {len(df)} dòng vào bảng [{table_name}].")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Lỗi khi insert dữ liệu: {e}")
            return False

    def upsert_fixtures(self, df: pd.DataFrame, table_name: str = 'wc26_fixtures'):
        """
        Upsert cho SQLite sử dụng cơ chế đè dữ liệu (REPLACE).
        Lưu ý: Bảng cần có Primary Key là fixture_id để REPLACE hoạt động đúng.
        """
        try:
            # SQLite xử lý tốt nhất bằng cách tạo bảng tạm hoặc dùng REPLACE INTO
            # Cách đơn giản nhất cho SQLite là append vào một bảng tạm rồi xử lý bằng SQL
            with self.engine.begin() as conn:
                df.to_sql('temp_table', con=conn, if_exists='replace', index=False)
                
                # SQLite hỗ trợ INSERT OR REPLACE (nếu trùng Primary Key thì ghi đè)
                sql = f"""
                INSERT OR REPLACE INTO {table_name} (fixture_id, date, timestamp, venue_name, status, home_team_name, away_team_name)
                SELECT fixture_id, date, timestamp, venue_name, status, home_team_name, away_team_name FROM temp_table
                """
                conn.execute(text(sql))
                conn.execute(text("DROP TABLE temp_table"))
            
            logger.info(f"Đã Upsert thành công vào bảng [{table_name}].")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Lỗi Upsert SQLite: {e}")
            return False

    def execute_raw_query(self, sql_query: str, params: dict = None) -> list:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query), params or {})
                if result.returns_rows:
                    return [dict(row._mapping) for row in result]
                conn.commit()
                return []
        except SQLAlchemyError as e:
            logger.error(f"Lỗi truy vấn: {e}")
            return []