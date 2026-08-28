import pandas as pd
import numpy as np
from pathlib import Path

class DataLoader:
    """
    负责读取原始 .datac (CSV) 档案，执行数据清洗与栏位标准化。
    核心职责包括生成高精度的 'Chainage' 栏位。
    """

    def __init__(self):
        # 定义栏位映射 (Legacy -> Standard)
        # Note: Input columns will be stripped of whitespace
        self.column_mapping = {
            'STG1c': 'stagger1', 'STG2c': 'stagger2', 'STG3c': 'stagger3', 'STG4c': 'stagger4',
            'RWH1mm': 'wear1', 'RWH2mm': 'wear2', 'RWH3mm': 'wear3', 'RWH4mm': 'wear4',
            'WHGT1c': 'height1', 'WHGT2c': 'height2', 'WHGT3c': 'height3', 'WHGT4c': 'height4',
            'LINE': 'Line', 'TRACK': 'Track'
        }

    def load_data(self, file_path: str) -> pd.DataFrame:
        """
        读取并处理数据文件。
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        # 1. 读取原始数据
        try:
            # use sep=';' and handle variable whitespace if needed, 
            # but usually fixed width or purely ; delimited. 
            # The sample shows ; delimiter.
            df = pd.read_csv(path, sep=';', engine='python')
            
            # Clean string columns (strip whitespace)
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}")
        
        # 1.1. 數據修剪：移除前 20 行和後 20 行（設置/拆卸階段）
        # 這些行代表不穩定的機器設置和拆卸階段
        if len(df) > 40:
            # 移除數據的前 20 行和後 20 行（標題已在讀取時處理）
            df = df.iloc[20:-20].copy()
            # 重置索引以保持連續性
            df = df.reset_index(drop=True)
        # 如果數據少於或等於 40 行，保留所有數據（邊緣情況處理）

        # 2. 清洗栏位名称 (Remove spaces)
        # Example: 'WHGT1c  ' -> 'WHGT1c'
        df.columns = df.columns.str.strip()
        
        # 3. 移除无效行 (rows where KM is 'KM' - header repetition?)
        if 'KM' in df.columns:
            # Ensure KM is not the literal string 'KM' (if headers repeated)
            df = df[df['KM'].astype(str) != 'KM'].copy()

        # 4. 重命名栏位
        df = df.rename(columns=self.column_mapping)

        # 5. 确保数值型态
        numeric_cols = [
            'KM', 'LOCATION', 
            'height1', 'height2', 'height3', 'height4', 
            'wear1', 'wear2', 'wear3', 'wear4', 
            'stagger1', 'stagger2', 'stagger3', 'stagger4'
        ]
        
        # Convert empty strings or whitespace-only strings to NaN before numeric conversion
        # The .apply(strip) above helps, but empty strings '' need to be NaN
        df = df.replace(r'^\s*$', np.nan, regex=True)

        cols_to_convert = [c for c in numeric_cols if c in df.columns]
        for col in cols_to_convert:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 5.1. 錯誤信號處理：將 wear 列中的 6.56 替換為 NaN
        # 6.56 是已知的系統錯誤代碼（默認返回值），專門用於 Wire Wear 測量
        # 僅在 wear 列中替換，不影響 stagger 和 height 列
        wear_columns = ['wear1', 'wear2', 'wear3', 'wear4']
        for col in wear_columns:
            if col in df.columns:
                # 使用 .loc 確保正確的賦值，避免 SettingWithCopyWarning
                df.loc[df[col] == 6.56, col] = np.nan

        # 6. 生成 Chainage (核心逻辑)
        if 'KM' in df.columns and 'LOCATION' in df.columns:
            df = self._calculate_chainage(df)
        else:
            # Fallback if no KM/LOCATION (should fail validation if critical)
            pass

        # 7. 高度校正
        
        for i in range(1, 5):
            col = f'height{i}'
            if col in df.columns:
                # Fill NaN with NaN, but valid values + 5300
                df[col] = df[col] + 5300

        return df

    def _calculate_chainage(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成 'Chainage' 栏位。
        规则: 
        1. 字面拼接 KM 与 LOCATION (格式化为 000.00)。
        2. 保留高精度 (High Precision)。
        """
        # Drop rows where critical location data is missing
        df = df.dropna(subset=['KM', 'LOCATION'])
        
        # 1. KM -> String (Integer part)
        # Handle cases where KM might be float like 100.0
        km_str = df['KM'].fillna(0).astype(int).astype(str)
        
        # 2. LOCATION -> Formatted String ("000.00")
        # Ensure it's treated as float first
        loc_str = df['LOCATION'].apply(lambda x: "{:06.2f}".format(float(x)))
        
        # 3. Concatenate (e.g., "100" + "116.75" -> "100116.75")
        chainage_str = km_str + loc_str
        
        # 4. Convert to float
        df['Chainage'] = chainage_str.astype(float)
        
        return df
