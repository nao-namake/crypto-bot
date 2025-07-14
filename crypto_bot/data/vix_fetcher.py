"""
VIX恐怖指数データフェッチャー
Yahoo Financeから米国VIX指数データを取得し、101特徴量システムに統合
"""

import logging
import pandas as pd
import yfinance as yf
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class VIXDataFetcher:
    """VIX恐怖指数データ取得クラス"""
    
    def __init__(self):
        self.symbol = "^VIX"  # Yahoo Finance VIXシンボル
        
    def get_vix_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        VIXデータ取得
        
        Args:
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）
            
        Returns:
            VIXデータのDataFrame
        """
        try:
            # デフォルト期間設定（過去1年間）
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                
            # Yahoo Financeからデータ取得
            vix_ticker = yf.Ticker(self.symbol)
            vix_data = vix_ticker.history(start=start_date, end=end_date)
            
            if vix_data.empty:
                logger.warning("No VIX data retrieved")
                return None
                
            # カラム名を統一
            vix_data.columns = vix_data.columns.str.lower()
            vix_data = vix_data.rename(columns={'close': 'vix_close'})
            
            logger.info(f"VIX data retrieved: {len(vix_data)} records")
            return vix_data
            
        except Exception as e:
            logger.error(f"Failed to fetch VIX data: {e}")
            return None
    
    def calculate_vix_features(self, vix_data: pd.DataFrame) -> Dict[str, Any]:
        """
        VIX特徴量計算（6特徴量）
        
        Args:
            vix_data: VIXデータ
            
        Returns:
            VIX特徴量辞書
        """
        try:
            if vix_data is None or vix_data.empty:
                return self._get_default_vix_features()
                
            latest_vix = vix_data['vix_close'].iloc[-1]
            
            # VIX特徴量計算
            features = {
                'vix_level': latest_vix,
                'vix_change_1d': vix_data['vix_close'].pct_change().iloc[-1],
                'vix_change_5d': vix_data['vix_close'].pct_change(5).iloc[-1], 
                'vix_ma_ratio': latest_vix / vix_data['vix_close'].rolling(20).mean().iloc[-1],
                'vix_volatility': vix_data['vix_close'].rolling(10).std().iloc[-1],
                'vix_fear_regime': 1 if latest_vix > 25 else 0,  # 恐怖指標
            }
            
            # NaN値をデフォルト値で補完
            for key, value in features.items():
                if pd.isna(value):
                    features[key] = self._get_default_vix_features()[key]
                    
            logger.info(f"VIX features calculated: {features}")
            return features
            
        except Exception as e:
            logger.error(f"Failed to calculate VIX features: {e}")
            return self._get_default_vix_features()
    
    def _get_default_vix_features(self) -> Dict[str, Any]:
        """VIX特徴量デフォルト値"""
        return {
            'vix_level': 20.0,  # 通常レベル
            'vix_change_1d': 0.0,
            'vix_change_5d': 0.0,
            'vix_ma_ratio': 1.0,
            'vix_volatility': 5.0,
            'vix_fear_regime': 0,  # 平常状態
        }