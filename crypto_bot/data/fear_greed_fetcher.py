"""
Fear&Greed指数データフェッチャー
Alternative.me APIからCrypto Fear & Greed Indexを取得し、101特徴量システムに統合
"""

import logging
import requests
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FearGreedDataFetcher:
    """Fear&Greed指数データ取得クラス"""
    
    def __init__(self):
        self.api_url = "https://api.alternative.me/fng/"
        
    def get_fear_greed_data(self, limit: int = 30) -> Optional[pd.DataFrame]:
        """
        Fear&Greedデータ取得
        
        Args:
            limit: 取得するデータ数
            
        Returns:
            Fear&GreedデータのDataFrame
        """
        try:
            # Alternative.me APIからデータ取得
            params = {"limit": limit}
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'data' not in data:
                logger.warning("No Fear&Greed data in response")
                return None
                
            # DataFrameに変換
            fg_data = pd.DataFrame(data['data'])
            fg_data['timestamp'] = pd.to_datetime(fg_data['timestamp'], unit='s')
            fg_data['value'] = pd.to_numeric(fg_data['value'])
            fg_data = fg_data.sort_values('timestamp').set_index('timestamp')
            
            logger.info(f"Fear&Greed data retrieved: {len(fg_data)} records")
            return fg_data
            
        except Exception as e:
            logger.error(f"Failed to fetch Fear&Greed data: {e}")
            return None
    
    def calculate_fear_greed_features(self, fg_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Fear&Greed特徴量計算（13特徴量）
        
        Args:
            fg_data: Fear&Greedデータ
            
        Returns:
            Fear&Greed特徴量辞書
        """
        try:
            if fg_data is None or fg_data.empty:
                return self._get_default_fear_greed_features()
                
            latest_value = fg_data['value'].iloc[-1]
            
            # Fear&Greed特徴量計算
            features = {
                # 基本指標
                'fg_index': latest_value,
                'fg_change_1d': fg_data['value'].pct_change().iloc[-1],
                'fg_change_7d': fg_data['value'].pct_change(7).iloc[-1] if len(fg_data) >= 7 else 0.0,
                'fg_ma_7': fg_data['value'].rolling(7).mean().iloc[-1] if len(fg_data) >= 7 else latest_value,
                'fg_ma_30': fg_data['value'].rolling(30).mean().iloc[-1] if len(fg_data) >= 30 else latest_value,
                
                # 感情状態分類
                'fg_extreme_fear': 1 if latest_value < 25 else 0,
                'fg_fear': 1 if 25 <= latest_value < 45 else 0,
                'fg_neutral': 1 if 45 <= latest_value < 55 else 0,
                'fg_greed': 1 if 55 <= latest_value < 75 else 0,
                'fg_extreme_greed': 1 if latest_value >= 75 else 0,
                
                # 統計指標
                'fg_volatility': fg_data['value'].rolling(7).std().iloc[-1] if len(fg_data) >= 7 else 10.0,
                'fg_momentum': (latest_value - fg_data['value'].rolling(7).mean().iloc[-1]) if len(fg_data) >= 7 else 0.0,
                'fg_reversal_signal': 1 if (latest_value < 25 or latest_value > 75) else 0,  # 反転シグナル
            }
            
            # NaN値をデフォルト値で補完
            for key, value in features.items():
                if pd.isna(value):
                    features[key] = self._get_default_fear_greed_features()[key]
                    
            logger.info(f"Fear&Greed features calculated: {features}")
            return features
            
        except Exception as e:
            logger.error(f"Failed to calculate Fear&Greed features: {e}")
            return self._get_default_fear_greed_features()
    
    def _get_default_fear_greed_features(self) -> Dict[str, Any]:
        """Fear&Greed特徴量デフォルト値"""
        return {
            'fg_index': 50.0,  # 中立
            'fg_change_1d': 0.0,
            'fg_change_7d': 0.0,
            'fg_ma_7': 50.0,
            'fg_ma_30': 50.0,
            'fg_extreme_fear': 0,
            'fg_fear': 0,
            'fg_neutral': 1,
            'fg_greed': 0,
            'fg_extreme_greed': 0,
            'fg_volatility': 10.0,
            'fg_momentum': 0.0,
            'fg_reversal_signal': 0,
        }