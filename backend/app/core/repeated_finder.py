import pandas as pd
import numpy as np
from typing import List, Optional

class RepeatedExceptionFinder:
    def __init__(self):
        pass

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Maps legacy and new format column names to current standard.
        
        Legacy Format: startM, endM, track type
        New Format (Phase 10.10): ID, Exception Type, MaxValue, MaxLocation, Length
        Current Standard: FromM, ToM, Track Type, id, exception type, maxValue, maxLocation, length
        
        Phase 10.10 Post-Bug Issue 2: History Compare 新/舊 Excel 格式不相容
        - 新格式使用 PascalCase: ID, Exception Type, MaxValue, MaxLocation, Length
        - 舊格式使用小寫/camelCase: id, exception type, maxValue, maxLocation, length
        - 需要統一映射到舊格式以確保比對演算法正常運作
        """
        mapping = {
            # Legacy format mappings
            'startM': 'FromM',
            'endM': 'ToM',
            'track type': 'Track Type',
            
            # New format mappings (Phase 10.10 Issue 2)
            'ID': 'id',
            'Exception Type': 'exception type',
            'MaxValue': 'maxValue',
            'MaxLocation': 'maxLocation',
            'Length': 'length',
        }
        # Rename only if columns exist
        return df.rename(columns=mapping)

    def find_repeated(self, df_chain: pd.DataFrame, df_new: pd.DataFrame, new_id_label: str = 'previous') -> pd.DataFrame:
        """
        Executes the "Strict Intersection & Peak Verification" algorithm in a chain.
        
        Args:
            df_chain (DataFrame): The accumulator DataFrame (Latest).
            df_new (DataFrame): The next report in the time sequence (Older).
            new_id_label (str): Column name for the matching ID from df_new (e.g. "Previous 1").
            
        Returns:
            DataFrame: Results containing values from df_chain, with added new_id_label column.
        """
        # 1. Standardize Columns
        old = self._standardize_columns(df_chain.copy()) # This is actually "Current/Latest"
        new = self._standardize_columns(df_new.copy())   # This is actually "Previous/Older"
        
        # Ensure required columns exist
        req_cols = ['FromM', 'ToM', 'maxLocation', 'maxValue', 'exception type', 'id']
        for c in req_cols:
            if c not in old.columns or c not in new.columns:
                # print(f"Warning: Missing columns. Old: {old.columns.tolist()}, New: {new.columns.tolist()}")
                return pd.DataFrame()
        
        # 2. Filter by Exception Type (Join on 'exception type')
        # We rename columns to avoid collision. 
        # df_chain (old) is the "Master/Latest". df_new (new) is the "Target/Previous".
        
        # Safety: Ensure df_new doesn't have conflicting 'Previous' columns that might confuse us
        # (Though we strictly use id_target later, it's good practice)
        cols_to_use_new = [c for c in new.columns if not c.startswith('Previous ')]
        new = new[cols_to_use_new]
        
        old_suff = old.add_suffix('_master')
        new_suff = new.add_suffix('_target')
        
        # Restore join key
        old_suff = old_suff.rename(columns={'exception type_master': 'exception type'})
        new_suff = new_suff.rename(columns={'exception type_target': 'exception type'})
        
        merged = pd.merge(old_suff, new_suff, on='exception type', how='inner')
        
        if merged.empty:
            return pd.DataFrame()

        # 3. Vectorized Geometric Logic
        # A. Intersection Interval
        i_start = np.maximum(merged['FromM_master'], merged['FromM_target'])
        i_end = np.minimum(merged['ToM_master'], merged['ToM_target'])
        
        # B. Check Existence (Valid Interval)
        valid_interval = i_start <= i_end
        
        # C. Check Peaks (Both peaks must be in the intersection)
        peak_master_in = (merged['maxLocation_master'] >= i_start) & (merged['maxLocation_master'] <= i_end)
        peak_target_in = (merged['maxLocation_target'] >= i_start) & (merged['maxLocation_target'] <= i_end)
        
        # Combined Condition
        is_repeated = valid_interval & peak_master_in & peak_target_in
        
        # Filter Results
        repeated_matches = merged[is_repeated].copy()
        
        if repeated_matches.empty:
            return pd.DataFrame()
            
        # 4. Deduplicate
        # We want to map ONE Latest exception to ONE Previous exception.
        # Priority: Keep first match? Or best match? Legacy kept first.
        repeated_matches = repeated_matches.drop_duplicates(subset=['id_master'], keep='first')
        
        # 5. Column Management
        # We keep the MASTER (Latest) values.
        # We add the TARGET (Previous) ID as the new column.
        
        # Rename id_target to new_id_label
        repeated_matches[new_id_label] = repeated_matches['id_target']
        
        # Preserve Target Metadata for Chart Visualization (Issue 6)
        # Store as "{new_id_label}_FromM", etc.
        repeated_matches[f"{new_id_label}_FromM"] = repeated_matches['FromM_target']
        repeated_matches[f"{new_id_label}_ToM"] = repeated_matches['ToM_target']
        repeated_matches[f"{new_id_label}_maxLocation"] = repeated_matches['maxLocation_target']
        repeated_matches[f"{new_id_label}_maxValue"] = repeated_matches['maxValue_target']

        # Restore Master columns to original names
        col_map = {c: c.replace('_master', '') for c in repeated_matches.columns if c.endswith('_master')}
        result = repeated_matches.rename(columns=col_map)
        
        # Select final columns
        # We must keep all "Previous X" columns that might have been in df_chain
        # Identify columns to keep:
        # - Standard report columns
        # - "Previous" columns
        # - The new_id_label
        
        final_cols = ['id', 'exception type', 'FromM', 'ToM', 'length', 'maxValue', 'maxLocation', new_id_label]
        
        # Add new metadata columns
        final_cols.extend([f"{new_id_label}_FromM", f"{new_id_label}_ToM", f"{new_id_label}_maxLocation", f"{new_id_label}_maxValue"])

        # Add existing "Previous" columns from df_chain (which are now in result)
        # They were preserved because add_suffix('_master') renamed them to 'Previous 1_master', 
        # and then we renamed them back to 'Previous 1'.
        
        # Find all 'Previous' columns in result
        # We need to catch 'Previous 1', 'Previous 1_FromM', 'Previous 2', etc.
        existing_prevs = [c for c in result.columns if c.startswith('Previous') and c not in final_cols]
        final_cols.extend(existing_prevs)

        # Add optional columns if they exist
        optional_cols = [
            'level', 'Track Type', 'Section', 'Class', 'Threshold Value',
            'Overlap', 'Tension Length', 'Landmark',
            # Phase 11 Issue 1 (12.4/12.5): Preserve Task Run Data columns
            'task_run_date', 'line', 'track', 'task_no',
            'station_start', 'station_end',
        ]
        for c in optional_cols:
            if c in result.columns:
                final_cols.append(c)
                
        return result[final_cols]


