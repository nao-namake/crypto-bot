"""
マクロ経済データフェッチャー
Yahoo Financeから米ドル指数(DXY)・金利データを取得し、101特徴量システムに統合
"""

import logging
import pandas as pd
import yfinance as yf
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MacroDataFetcher:
    """マクロ経済データ取得クラス"""
    
    def __init__(self):
        self.symbols = {
            'dxy': 'DX-Y.NYB',  # ドル指数
            'us10y': '^TNX',    # 米10年債利回り
            'us2y': '^IRX',     # 米2年債利回り
        }
        
    def get_macro_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        マクロ経済データ取得
        
        Args:
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）
            
        Returns:
            マクロデータの辞書
        """
        try:
            # デフォルト期間設定（過去1年間）
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                
            macro_data = {}
            
            for name, symbol in self.symbols.items():
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(start=start_date, end=end_date)
                    
                    if not data.empty:
                        data.columns = data.columns.str.lower()
                        macro_data[name] = data
                        logger.info(f"{name} data retrieved: {len(data)} records")
                    else:
                        logger.warning(f"No data retrieved for {name}")
                        
                except Exception as e:
                    logger.error(f"Failed to fetch {name} data: {e}")
                    
            return macro_data
            
        except Exception as e:
            logger.error(f"Failed to fetch macro data: {e}")
            return {}
    
    def calculate_macro_features(self, macro_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        マクロ経済特徴量計算（10特徴量）
        
        Args:
            macro_data: マクロデータ辞書
            
        Returns:
            マクロ特徴量辞書
        """
        try:
            features = {}
            
            # DXY（ドル指数）特徴量
            if 'dxy' in macro_data and not macro_data['dxy'].empty:
                dxy_data = macro_data['dxy']
                latest_dxy = dxy_data['close'].iloc[-1]
                
                features.update({
                    'dxy_level': latest_dxy,
                    'dxy_change_1d': dxy_data['close'].pct_change().iloc[-1],
                    'dxy_change_5d': dxy_data['close'].pct_change(5).iloc[-1],
                    'dxy_ma_ratio': latest_dxy / dxy_data['close'].rolling(20).mean().iloc[-1],
                })
            else:
                features.update(self._get_default_dxy_features())
                
            # 米10年債利回り特徴量
            if 'us10y' in macro_data and not macro_data['us10y'].empty:
                us10y_data = macro_data['us10y']
                latest_10y = us10y_data['close'].iloc[-1]
                
                features.update({
                    'us10y_yield': latest_10y,
                    'us10y_change_1d': us10y_data['close'].diff().iloc[-1],
                    'us10y_trend': 1 if us10y_data['close'].rolling(5).mean().iloc[-1] > us10y_data['close'].rolling(20).mean().iloc[-1] else 0,
                })
            else:
                features.update(self._get_default_10y_features())
                
            # 米2年債利回り特徴量とイールドカーブ
            if 'us2y' in macro_data and not macro_data['us2y'].empty:
                us2y_data = macro_data['us2y']
                latest_2y = us2y_data['close'].iloc[-1]
                
                features.update({
                    'us2y_yield': latest_2y,
                    'yield_curve_slope': features.get('us10y_yield', 4.0) - latest_2y,  # 10年-2年スプレッド
                    'yield_curve_inversion': 1 if features.get('us10y_yield', 4.0) < latest_2y else 0,
                })
            else:
                features.update(self._get_default_2y_features())
                
            # NaN値をデフォルト値で補完
            for key, value in features.items():
                if pd.isna(value):
                    features[key] = self._get_default_macro_features()[key]
                    
            logger.info(f"Macro features calculated: {len(features)} features")
            return features
            
        except Exception as e:
            logger.error(f"Failed to calculate macro features: {e}")
            return self._get_default_macro_features()
    
    def _get_default_dxy_features(self) -> Dict[str, Any]:
        """DXY特徴量デフォルト値"""
        return {
            'dxy_level': 103.0,  # 典型的なDXYレベル
            'dxy_change_1d': 0.0,
            'dxy_change_5d': 0.0,
            'dxy_ma_ratio': 1.0,
        }
    
    def _get_default_10y_features(self) -> Dict[str, Any]:
        """10年債特徴量デフォルト値"""
        return {
            'us10y_yield': 4.0,  # 典型的な10年債利回り
            'us10y_change_1d': 0.0,
            'us10y_trend': 0,
        }
        
    def _get_default_2y_features(self) -> Dict[str, Any]:
        """2年債特徴量デフォルト値"""
        return {
            'us2y_yield': 4.5,  # 典型的な2年債利回り
            'yield_curve_slope': -0.5,  # 逆イールド状態
            'yield_curve_inversion': 1,
        }
    
    def _get_default_macro_features(self) -> Dict[str, Any]:
        """マクロ特徴量デフォルト値（10特徴量）"""
        features = {}
        features.update(self._get_default_dxy_features())
        features.update(self._get_default_10y_features())
        features.update(self._get_default_2y_features())
        return features