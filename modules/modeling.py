import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
import logging
from sklearn.model_selection import train_test_split
from sklearn.metrics import brier_score_loss, log_loss, accuracy_score, roc_auc_score

logger = logging.getLogger(__name__)

class WorldCupModel:
    """
    Module Machine Learning sử dụng XGBoost để dự đoán xác suất trận đấu.
    Tối ưu hóa Brier Score để đảm bảo độ chuẩn xác của Implied Probability cho Polymarket.
    """
    
    def __init__(self, model_path: str = "data/wc_xgb_model.joblib"):
        self.model_path = model_path
        # Các siêu tham số (Hyperparameters) chống Overfitting cho bóng đá
        self.params = {
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'max_depth': 4,              # Không để quá sâu, bóng đá có tính ngẫu nhiên cao
            'learning_rate': 0.05,
            'n_estimators': 150,
            'subsample': 0.8,            # Lấy ngẫu nhiên 80% data mỗi cây để giảm nhiễu
            'colsample_bytree': 0.8,
            'random_state': 42,
            'use_label_encoder': False
        }
        self.model = xgb.XGBClassifier(**self.params)
        self.is_trained = False
        
        # Nếu đã có model lưu sẵn thì load lên luôn
        if os.path.exists(self.model_path):
            self.load_model()

    def train(self, df: pd.DataFrame, target_col: str = 'home_win', test_size: float = 0.2):
        """
        Huấn luyện model với dữ liệu lịch sử.
        Mục tiêu: Tính xác suất Đội Nhà Thắng (1) hoặc Không Thắng (0).
        """
        logger.info(f"Bắt đầu huấn luyện mô hình XGBoost với {len(df)} trận đấu...")
        
        # Tách features (X) và target (y)
        # Bỏ các cột ID hoặc tên không mang ý nghĩa toán học
        drop_cols = [target_col, 'fixture_id', 'venue_name', 'home_team', 'away_team']
        X = df.drop(columns=[col for col in drop_cols if col in df.columns])
        y = df[target_col]
        
        # Chia tập Train/Test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
        
        # Đưa vào huấn luyện
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        self.is_trained = True
        
        # Đánh giá hiệu suất thực tế trên tập Test
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred_bin = self.model.predict(X_test)
        
        # Các chỉ số sinh tử của dân cá cược
        brier = brier_score_loss(y_test, y_pred_proba)
        loss = log_loss(y_test, y_pred_proba)
        acc = accuracy_score(y_test, y_pred_bin)
        auc = roc_auc_score(y_test, y_pred_proba)
        
        logger.info(f"--- KẾT QUẢ HUẤN LUYỆN ---")
        logger.info(f"Accuracy (Độ chính xác): {acc:.4f}")
        logger.info(f"ROC-AUC (Khả năng phân loại): {auc:.4f}")
        logger.info(f"Brier Score (Độ lệch xác suất - Càng gần 0 càng tốt): {brier:.4f}")
        logger.info(f"Log Loss: {loss:.4f}")
        
        # Nếu Brier Score > 0.25, model của mày đang phán bừa, cần xem lại Feature Engineering
        if brier > 0.25:
            logger.warning("Brier Score quá cao! Không nên dùng model này để trade thật.")
            
        self.save_model()
        return {"brier_score": brier, "accuracy": acc, "roc_auc": auc}

    def predict_match_probability(self, features_df: pd.DataFrame) -> float:
        """
        Dự đoán xác suất thắng cho một trận đấu cụ thể (Live/Upcoming).
        features_df: DataFrame 1 dòng chứa các feature đã được chế biến từ feature_engineering.py
        Trả về Float: Xác suất từ 0.0 đến 1.0
        """
        if not self.is_trained:
            logger.error("Model chưa được huấn luyện hoặc chưa load file joblib.")
            return 0.0
            
        # Lọc bỏ các cột định danh không cần thiết giống như lúc Train
        drop_cols = ['fixture_id', 'venue_name', 'home_team', 'away_team']
        X_pred = features_df.drop(columns=[col for col in drop_cols if col in features_df.columns])
        
        # Lấy xác suất của class 1 (Home Win)
        probability = self.model.predict_proba(X_pred)[0][1]
        return round(probability, 4)

    def save_model(self):
        """Lưu model ra file để dùng cho các lần chạy bot sau."""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        logger.info(f"Đã lưu mô hình tại: {self.model_path}")

    def load_model(self):
        """Tải model từ file."""
        self.model = joblib.load(self.model_path)
        self.is_trained = True
        logger.info(f"Đã tải mô hình thành công từ: {self.model_path}")

# ==========================================
# KHỐI TEST NHANH 
# ==========================================
if __name__ == "__main__":
    # 1. Tạo dữ liệu giả lập (Mock Data) để Test quá trình Train
    np.random.seed(42)
    sample_size = 500
    
    # Giả lập dữ liệu đã qua tiền xử lý
    mock_df = pd.DataFrame({
        'fixture_id': range(sample_size),
        'venue_alt': np.random.randint(0, 2500, sample_size),
        'home_fatigue_idx': np.random.uniform(0, 3, sample_size),
        'away_fatigue_idx': np.random.uniform(0, 3, sample_size),
        'xg_diff': np.random.uniform(-2.5, 2.5, sample_size),     # Rất quan trọng
        'fatigue_diff': np.random.uniform(-2, 2, sample_size),
        'home_win': np.where(np.random.uniform(-2.5, 2.5, sample_size) + np.random.normal(0, 1, sample_size) > 0, 1, 0)
    })
    # Chỉnh lại home_win cho tương quan với xg_diff để model có cái học
    mock_df['home_win'] = (mock_df['xg_diff'] + np.random.normal(0, 1.5, sample_size) > 0).astype(int)

    # Khởi tạo và Train model
    print("--- BẮT ĐẦU TRAINING MÔ HÌNH ---")
    model = WorldCupModel(model_path="../data/test_xgb.joblib")
    metrics = model.train(mock_df, target_col='home_win')
    
    # 2. Test dự đoán 1 trận đấu mới
    print("\n--- BẮT ĐẦU DỰ ĐOÁN TRẬN MỚI ---")
    new_match = pd.DataFrame([{
        'fixture_id': 999,
        'venue_alt': 2240,       # Sân Azteca
        'home_fatigue_idx': 0.5, # Chủ nhà khỏe
        'away_fatigue_idx': 2.1, # Khách mệt mỏi
        'xg_diff': 1.2,          # Chủ nhà áp đảo xG
        'fatigue_diff': 1.6
    }])
    
    prob = model.predict_match_probability(new_match)
    print(f"Dữ liệu trận đấu:\n{new_match.T}")
    print(f"-> MÔ HÌNH DỰ ĐOÁN XÁC SUẤT ĐỘI NHÀ THẮNG: {prob * 100:.2f}%")