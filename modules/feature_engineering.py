import pandas as pd
import numpy as np
import math
import logging

logger = logging.getLogger(__name__)

# Từ điển tĩnh lưu tọa độ (Lat, Lon) và Độ cao (Altitude - tính bằng mét) của các sân WC 2026
# (Mày có thể bổ sung thêm danh sách đầy đủ 16 sân của Mỹ, Canada, Mexico vào đây)
WC2026_VENUES = {
    "Estadio Azteca": {"city": "Mexico City", "lat": 19.3029, "lon": -99.1505, "altitude": 2240},
    "Estadio Akron": {"city": "Guadalajara", "lat": 20.6817, "lon": -103.4628, "altitude": 1566},
    "Estadio BBVA": {"city": "Monterrey", "lat": 25.6697, "lon": -100.2444, "altitude": 540},
    "MetLife Stadium": {"city": "New Jersey", "lat": 40.8128, "lon": -74.0742, "altitude": 2},
    "BC Place": {"city": "Vancouver", "lat": 49.2768, "lon": -123.1120, "altitude": 5},
    "BMO Field": {"city": "Toronto", "lat": 43.6332, "lon": -79.4186, "altitude": 75},
    "AT&T Stadium": {"city": "Dallas", "lat": 32.7473, "lon": -97.0945, "altitude": 165},
    # Default fallback cho các sân chưa khai báo
    "Unknown": {"city": "Unknown", "lat": 0.0, "lon": 0.0, "altitude": 0}
}

class FeatureEngineer:
    """
    Module chế biến dữ liệu đầu vào (Feature Engineering).
    Chuyển đổi dữ liệu thô (xG, Lịch sử thi đấu, Sân bãi) thành các Feature Vectors 
    có trọng số để đưa vào mô hình Machine Learning (XGBoost/RandomForest).
    """
    
    def __init__(self):
        self.venues = WC2026_VENUES

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Tính khoảng cách di chuyển thực tế (đường chim bay) giữa 2 tọa độ bằng km.
        """
        R = 6371.0 # Bán kính trái đất (km)
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def calculate_travel_fatigue(self, prev_venue: str, current_venue: str, days_rest: int) -> float:
        """
        Tính chỉ số mệt mỏi do di chuyển (Travel Fatigue Index).
        Khoảng cách bay càng xa và số ngày nghỉ càng ít thì chỉ số này càng cao.
        """
        if prev_venue not in self.venues or current_venue not in self.venues:
            return 0.0
            
        v1 = self.venues[prev_venue]
        v2 = self.venues[current_venue]
        
        distance_km = self._haversine_distance(v1['lat'], v1['lon'], v2['lat'], v2['lon'])
        
        # Nếu nghỉ >= 6 ngày, coi như đã hồi phục hoàn toàn mệt mỏi do bay
        if days_rest >= 6:
            return 0.0
            
        # Công thức: (Khoảng cách / 1000) * Trọng số thiếu ngày nghỉ
        fatigue_score = (distance_km / 1000.0) * (6 - days_rest) * 0.5
        return round(fatigue_score, 3)

    def calculate_altitude_penalty(self, venue_name: str, team_region: str = "Europe") -> float:
        """
        Tính điểm phạt độ cao (Altitude Penalty).
        Các đội Nam Mỹ (như Bolivia, Ecuador, Colombia, Mexico) quen với không khí loãng.
        Các đội Châu Âu hoặc Châu Á sẽ bị giảm sút thể lực nặng ở hiệp 2 nếu đá ở sân > 1500m.
        """
        venue_info = self.venues.get(venue_name, self.venues["Unknown"])
        alt = venue_info["altitude"]
        
        # Sân dưới 1000m hầu như không ảnh hưởng
        if alt < 1000:
            return 0.0
            
        penalty = (alt - 1000) / 1000.0 # Bắt đầu phạt từ mốc 1000m
        
        # Giảm thiểu hình phạt cho các đội thuộc khu vực đã quen độ cao (Nam Mỹ / Trung Mỹ)
        if team_region in ["CONMEBOL", "CONCACAF"]:
            penalty = penalty * 0.3
            
        return round(penalty, 3)

    def build_match_features(self, match_data: dict) -> pd.DataFrame:
        """
        Hàm chính: Tổng hợp toàn bộ chỉ số để tạo ra 1 dòng (Row) feature cho Model dự đoán.
        match_data là một dict chứa thông tin trận đấu (lấy từ DB hoặc Data Crawler).
        """
        logger.info(f"Đang chế biến feature cho trận: {match_data['home_team']} vs {match_data['away_team']}")
        
        # 1. Xử lý khoảng cách và ngày nghỉ
        home_fatigue = self.calculate_travel_fatigue(
            match_data.get('home_prev_venue', 'Unknown'), 
            match_data['venue_name'], 
            match_data.get('home_days_rest', 5)
        )
        
        away_fatigue = self.calculate_travel_fatigue(
            match_data.get('away_prev_venue', 'Unknown'), 
            match_data['venue_name'], 
            match_data.get('away_days_rest', 5)
        )
        
        # 2. Xử lý sốc độ cao
        home_alt_penalty = self.calculate_altitude_penalty(match_data['venue_name'], match_data.get('home_region', 'Unknown'))
        away_alt_penalty = self.calculate_altitude_penalty(match_data['venue_name'], match_data.get('away_region', 'Unknown'))
        
        # 3. Kết hợp Form và xG (Trừ đi độ mệt mỏi)
        # Giả định xG cơ bản lấy từ API là trung bình 5 trận gần nhất
        base_home_xg = match_data.get('home_xg_avg', 1.0)
        base_away_xg = match_data.get('away_xg_avg', 1.0)
        
        # Thể lực yếu / sốc độ cao làm giảm kỳ vọng ghi bàn (xG) và tăng rủi ro thủng lưới
        adj_home_xg = base_home_xg - (home_fatigue * 0.05) - (home_alt_penalty * 0.1)
        adj_away_xg = base_away_xg - (away_fatigue * 0.05) - (away_alt_penalty * 0.1)

        # 4. Đóng gói thành Vector
        features = {
            "fixture_id": match_data['fixture_id'],
            "venue_alt": self.venues.get(match_data['venue_name'], self.venues["Unknown"])["altitude"],
            "home_fatigue_idx": home_fatigue,
            "away_fatigue_idx": away_fatigue,
            "home_alt_penalty": home_alt_penalty,
            "away_alt_penalty": away_alt_penalty,
            "home_form_score": match_data.get('home_form_score', 0.5), # Dữ liệu Form từ chuỗi W-D-L
            "away_form_score": match_data.get('away_form_score', 0.5),
            "adjusted_home_xg": max(0.1, round(adj_home_xg, 3)), # xG không thể âm
            "adjusted_away_xg": max(0.1, round(adj_away_xg, 3)),
            # Tính độ lệch sức mạnh tổng hợp (Chỉ số quan trọng nhất cho Model)
            "xg_diff": round(adj_home_xg - adj_away_xg, 3),
            "fatigue_diff": round(away_fatigue - home_fatigue, 3) 
        }
        
        # Trả về DataFrame 1 dòng chuẩn bị ném vào model.predict()
        return pd.DataFrame([features])

# ==========================================
# KHỐI TEST NHANH 
# ==========================================
if __name__ == "__main__":
    fe = FeatureEngineer()
    
    # Kịch bản giả định ngay thời điểm hiện tại:
    # Đội khách (Châu Âu) vừa đá ở Vancouver, được nghỉ 4 ngày, phải bay xuống Mexico City đá với Đội nhà (CONCACAF).
    sample_match = {
        "fixture_id": 999,
        "home_team": "Mexico",
        "away_team": "Germany",
        "venue_name": "Estadio Azteca",
        "home_region": "CONCACAF",
        "away_region": "UEFA",
        "home_prev_venue": "Estadio Akron",  # Mexico di chuyển gần
        "away_prev_venue": "BC Place",       # Đức bay từ Canada xuống
        "home_days_rest": 5,
        "away_days_rest": 4,
        "home_xg_avg": 1.5,
        "away_xg_avg": 2.2,                  # Ban đầu Đức nhỉnh hơn về xG
        "home_form_score": 0.7,
        "away_form_score": 0.8
    }
    
    print("--- DỮ LIỆU FEATURE ĐẦU RA ---")
    df_features = fe.build_match_features(sample_match)
    
    # Hiển thị kết quả dọc để dễ đọc
    for col in df_features.columns:
        print(f"{col.ljust(20)}: {df_features.iloc[0][col]}")