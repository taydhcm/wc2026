import requests
import pandas as pd
import time
from datetime import datetime

# Giả định mày có module logger tự viết trong utils/logger.py
# Nếu chưa có, dùng tạm print hoặc thư viện logging của Python
import logging
logger = logging.getLogger(__name__)

class FootballDataCrawler:
    """
    Module cào dữ liệu bóng đá từ API-Football.
    Tối ưu cho việc lấy Fixtures, Lineups, xG và Team Stats phục vụ WC 2026.
    """
    
    def __init__(self, api_key: str, season: int = 2025): # Thêm tham số season
        self.api_key = api_key
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-apisports-key": self.api_key,
            "Accept": "application/json"
        }
        self.wc_league_id = 1 
        self.season = season # Sử dụng season được truyền vào

    def _make_request(self, endpoint: str, params: dict = None, retries: int = 3) -> list:
        """
        Hàm gọi API chung có cơ chế Retry để chống rớt mạng hoặc Rate Limit.
        """
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                # Kiểm tra lỗi từ phía API (ví dụ: hết request trong ngày)
                if data.get("errors"):
                    logger.error(f"API Error at {endpoint}: {data.get('errors')}")
                    return []
                    
                return data.get("response", [])
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Lỗi kết nối {endpoint} (Lần {attempt + 1}/{retries}): {e}")
                time.sleep(2) # Nghỉ 2s trước khi thử lại
                
        logger.error(f"Thất bại hoàn toàn khi lấy dữ liệu từ {endpoint}")
        return []

    def get_upcoming_fixtures(self, date_str: str = None) -> pd.DataFrame:
        """
        Lấy lịch thi đấu, tỷ lệ kèo cơ bản và trạng thái trận đấu.
        date_str: Định dạng 'YYYY-MM-DD'
        """
        params = {
            "league": self.wc_league_id,
            "season": self.season
        }
        if date_str:
            params["date"] = date_str
            
        logger.info(f"Đang cào lịch thi đấu WC {self.season}...")
        raw_data = self._make_request("fixtures", params=params)
        
        if not raw_data:
            return pd.DataFrame()

        # Tiền xử lý (Parse JSON -> Phẳng hóa cấu trúc cho dễ insert DB)
        fixtures_list = []
        for item in raw_data:
            fixture = item['fixture']
            teams = item['teams']
            
            fixtures_list.append({
                "fixture_id": fixture['id'],
                "date": fixture['date'],
                "timestamp": fixture['timestamp'],
                "venue_name": fixture['venue']['name'],
                "venue_city": fixture['venue']['city'],
                "status": fixture['status']['short'],
                "home_team_id": teams['home']['id'],
                "home_team_name": teams['home']['name'],
                "away_team_id": teams['away']['id'],
                "away_team_name": teams['away']['name']
            })
            
        df = pd.DataFrame(fixtures_list)
        return df

    def get_team_advanced_stats(self, team_id: int) -> dict:
        """
        Lấy Form, sức mạnh tấn công/phòng thủ để tính Elo/xG.
        """
        params = {
            "league": self.wc_league_id,
            "season": self.season,
            "team": team_id
        }
        logger.info(f"Lấy dữ liệu thống kê nâng cao cho Team ID: {team_id}")
        raw_data = self._make_request("teams/statistics", params=params)
        
        if not raw_data:
            return {}
            
        stats = raw_data
        # Rút trích các features quan trọng phục vụ Machine Learning
        extracted_features = {
            "team_id": team_id,
            "form": stats['form'],
            "goals_for_avg": stats['goals']['for']['average']['total'],
            "goals_against_avg": stats['goals']['against']['average']['total'],
            "clean_sheets": stats['clean_sheet']['total']
        }
        return extracted_features

    def get_match_lineups(self, fixture_id: int) -> pd.DataFrame:
        """
        Cào đội hình ra sân (Rất quan trọng trên Polymarket vì khi có sao chấn thương, Edge sẽ lệch mạnh).
        """
        params = {"fixture": fixture_id}
        logger.info(f"Đang cào đội hình xuất phát cho Fixture ID: {fixture_id}")
        raw_data = self._make_request("fixtures/lineups", params=params)
        
        if not raw_data:
            return pd.DataFrame()

        lineup_data = []
        for team_data in raw_data:
            team_id = team_data['team']['id']
            formation = team_data['formation']
            
            for player in team_data['startXI']:
                p_info = player['player']
                lineup_data.append({
                    "fixture_id": fixture_id,
                    "team_id": team_id,
                    "formation": formation,
                    "player_id": p_info['id'],
                    "player_name": p_info['name'],
                    "position": p_info['pos'],
                    "grid": p_info['grid']
                })
                
        return pd.DataFrame(lineup_data)

# ==========================================
# KHỐI TEST NHANH KHI CHẠY TRỰC TIẾP FILE NÀY
# ==========================================
if __name__ == "__main__":
    from config.api_keys import FOOTBALL_API_KEY
    
    # Khởi tạo Crawler
    crawler = FootballDataCrawler(api_key=FOOTBALL_API_KEY)
    
    # Test 1: Lấy danh sách trận đấu
    print("--- FETCHING FIXTURES ---")
    df_fixtures = crawler.get_upcoming_fixtures()
    if not df_fixtures.empty:
        print(df_fixtures.head())
        # Demo cách lấy đội hình cho trận đầu tiên tìm thấy
        first_match_id = df_fixtures.iloc[0]['fixture_id']
        
        print(f"\n--- FETCHING LINEUPS FOR MATCH {first_match_id} ---")
        df_lineups = crawler.get_match_lineups(fixture_id=first_match_id)
        print(df_lineups.head())