import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING

from .metadata import MetadataManager

if TYPE_CHECKING:
    from .database import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)

class ExceptionDetector:
    """
    異常檢測核心引擎。
    v2.6 Refactor:
    - Fix: Handle overlapping intervals in _apply_mapping using get_indexer_non_unique logic.
    - Fix: Strict type casting for severity comparison (str vs float).
    - Fix: Enforce L1 > L2 > L3 hierarchy.
    """

    # Configuration for detection depth and mode
    CONFIG = {
        'Low Height': {'depth': 2, 'mode': 'min'},
        'High Height': {'depth': 2, 'mode': 'max'},
        'Wire Wear': {'depth': 2, 'mode': 'min'},
        'Stagger Left': {'depth': 3, 'mode': 'abs'},
        'Stagger Right': {'depth': 3, 'mode': 'abs'}
    }

    def __init__(self, metadata_manager: MetadataManager):
        self.meta_mgr = metadata_manager
        self.last_session_id: Optional[str] = None

    @staticmethod
    def _build_exception_id(
        date_str: str,
        line: str,
        track: str,
        section: str,
        task_no: Optional[str],
        station_start: Optional[str],
        station_end: Optional[str],
        code: str,
        counter: int,
    ) -> str:
        """Build exception_id using Condition A or B.

        Condition B (Custom): all of task_no, station_start, station_end provided.
          Format: {date_str}_{line}_{task_no}_{station_start.upper()}-{station_end.upper()}_{code}{counter}
          Example: 20260206_TML_D2_HUH-TAW_LH0

        Condition A (Default): any of task_no/station_start/station_end is empty/None.
          Format: {date_str}_{line}_{track}_{section}_{code}{counter}
          Example: 20260206_TML_DN_Mainline_LH0
        """
        if task_no and station_start and station_end:
            return (
                f"{date_str}_{line}_{task_no}_"
                f"{station_start.upper()}-{station_end.upper()}_{code}{counter}"
            )
        return f"{date_str}_{line}_{track}_{section}_{code}{counter}"

    def analyze(
        self, 
        df: pd.DataFrame, 
        line: str, 
        section: str, 
        track: str, 
        date_str: str,
        auto_save: bool = False,
        db_manager: Optional['DatabaseManager'] = None,
        raw_data_file_path: Optional[str] = None,
        raw_data_file_name: Optional[str] = None,
        raw_data_file_size: Optional[int] = None,
        task_no: Optional[str] = None,
        station_start: Optional[str] = None,
        station_end: Optional[str] = None
    ) -> Tuple[Dict[str, Any], pd.DataFrame]:
        """
        執行完整的異常分析流程。
        Returns: (results_dict, boundary_df_for_plot)
        """
        # 1. Map Class (Dynamic Section)
        df = self._map_class_info(df, line, track, section)
        
        # 2. Map Track Type, Overlap, Landmark
        df = self._map_track_info(df, line, section, track)
        
        # 3. Get Boundaries for Plotting
        boundary_df = self.meta_mgr.get_boundaries_for_plot(line, track, section)
        
        # 4. Prepare Thresholds
        thresholds_df = self.meta_mgr.get_all_thresholds()
        
        results = {}
        
        # 4.5 Pre-compute aggregate columns (Phase 10.10: row_val split)
        # These persist on df and are NOT overwritten by _detect_scalar
        height_cols = [c for c in ['height1', 'height2', 'height3', 'height4'] if c in df.columns]
        wear_cols = [c for c in ['wear1', 'wear2', 'wear3', 'wear4'] if c in df.columns]

        if height_cols:
            df['height_min'] = df[height_cols].min(axis=1)
            df['height_max'] = df[height_cols].max(axis=1)
        if wear_cols:
            df['wear_min'] = df[wear_cols].min(axis=1)
            df['wear_max'] = df[wear_cols].max(axis=1)
        
        # 5. Detect Scalar (Height, Wear) - Depth 2
        results['Low Height'] = self._detect_scalar(
            df, 'height', 'Low Height', thresholds_df, mode='min',
            date_str=date_str, track=track, line=line, section_name=section,
            task_no=task_no, station_start=station_start, station_end=station_end
        )

        results['High Height'] = self._detect_scalar(
            df, 'height', 'High Height', thresholds_df, mode='max',
            date_str=date_str, track=track, line=line, section_name=section,
            task_no=task_no, station_start=station_start, station_end=station_end
        )

        results['Wire Wear'] = self._detect_scalar(
            df, 'wear', 'Wire Wear', thresholds_df, mode='min',
            date_str=date_str, track=track, line=line, section_name=section,
            task_no=task_no, station_start=station_start, station_end=station_end
        )
        
        # 6. Detect Stagger - Depth 3
        stagger_l, stagger_r = self._detect_stagger(
            df, thresholds_df, date_str, track, line, section_name=section,
            task_no=task_no, station_start=station_start, station_end=station_end
        )
        results['Stagger Left'] = stagger_l
        results['Stagger Right'] = stagger_r
        
        # 6.5 Inject Task Run Data into all exception DataFrames (Phase 10.10 Issue 1)
        # This ensures exported Excel contains complete Task Run Data columns
        task_run_data = {
            'task_run_date': date_str,
            'line': line,
            'track': track,
            'task_no': task_no,
            'station_start': station_start,
            'station_end': station_end,
        }
        for exc_type, exc_df in results.items():
            if isinstance(exc_df, pd.DataFrame) and not exc_df.empty:
                for field, value in task_run_data.items():
                    if field not in exc_df.columns:
                        exc_df[field] = value
        
        # 7. Auto-Save to Database (Stateful Transformation)
        if auto_save and db_manager is not None:
            session_id = self._save_to_database(
                db_manager=db_manager,
                results=results,
                line=line,
                section=section,
                track=track,
                date_str=date_str,
                raw_data_file_path=raw_data_file_path,
                raw_data_file_name=raw_data_file_name,
                raw_data_file_size=raw_data_file_size,
                task_no=task_no,
                station_start=station_start,
                station_end=station_end
            )
            results['session_id'] = session_id
            self.last_session_id = session_id
            logger.info(f"Auto-saved analysis session: {session_id}")
        
        return results, boundary_df

    def _map_class_info(self, df: pd.DataFrame, line: str, track: str, selected_section: str) -> pd.DataFrame:
        try:
            boundary_df = self.meta_mgr.get_exception_boundaries(line, track, selected_section)
            # Use robust mapping for Class
            self._apply_mapping(df, boundary_df, ['Class'])
            if 'Class' not in df.columns:
                df['Class'] = 'both'
            else:
                df['Class'] = df['Class'].fillna('both')
        except Exception as e:
            print(f"Warning: Class mapping failed: {e}")
            df['Class'] = 'both'
        return df

    def _map_track_info(self, df: pd.DataFrame, line: str, section: str, track: str) -> pd.DataFrame:
        try:
            tt_df = self.meta_mgr.get_track_type_intervals(line, section, track)
            self._apply_mapping(df, tt_df, ['Track Type']) 
        except Exception:
            if 'Track Type' not in df.columns: df['Track Type'] = np.nan

        try:
            ov_df = self.meta_mgr.get_overlap_intervals(line, section, track)
            self._apply_mapping(df, ov_df, ['Overlap', 'Tension Length'])
        except Exception:
            if 'Overlap' not in df.columns: df['Overlap'] = np.nan
            if 'Tension Length' not in df.columns: df['Tension Length'] = np.nan

        try:
            lm_df = self.meta_mgr.get_landmark_intervals(line, section, track)
            self._apply_mapping(df, lm_df, ['Landmark'])
        except Exception:
            if 'Landmark' not in df.columns: df['Landmark'] = np.nan
        return df

    def _apply_mapping(self, df: pd.DataFrame, info_df: pd.DataFrame, cols: List[str]):
        """
        Maps values from info_df (IntervalIndex) to df (Chainage).
        Handles overlapping intervals by prioritizing the shortest interval (most specific).
        
        Performance optimized for large datasets with overlapping intervals.
        """
        for col in cols:
            if col not in df.columns:
                df[col] = np.nan
                df[col] = df[col].astype(object)
        
        if info_df.empty: return

        try:
            # 1. Fast Path: Standard get_indexer (Works if no overlaps)
            indexer = info_df.index.get_indexer(df['Chainage'])
            found_mask = (indexer != -1)
            valid_indices = indexer[found_mask]
            
            for col in cols:
                if col in info_df.columns:
                    mapped_vals = info_df[col].iloc[valid_indices].values
                    df.loc[found_mask, col] = mapped_vals
                    
        except Exception: 
            # 2. Optimized Path: Vectorized Interval Lookup (Handles Overlaps Efficiently)
            # Uses numpy broadcasting for O(N*M) but with vectorized operations
            try:
                chainages = df['Chainage'].values
                n_points = len(chainages)
                
                # Extract interval bounds as numpy arrays
                lefts = np.array([idx.left for idx in info_df.index])
                rights = np.array([idx.right for idx in info_df.index])
                lengths = rights - lefts
                
                # Create result arrays for each column
                results = {col: np.full(n_points, np.nan, dtype=object) for col in cols}
                best_lengths = np.full(n_points, np.inf)
                
                # Process in chunks for memory efficiency
                chunk_size = 10000
                for chunk_start in range(0, n_points, chunk_size):
                    chunk_end = min(chunk_start + chunk_size, n_points)
                    chunk_chainages = chainages[chunk_start:chunk_end]
                    chunk_best_lengths = best_lengths[chunk_start:chunk_end].copy()
                    
                    # Check each interval
                    for i, (left, right, length) in enumerate(zip(lefts, rights, lengths)):
                        # Find points within this interval
                        mask = (chunk_chainages >= left) & (chunk_chainages <= right)
                        
                        if not mask.any():
                            continue
                        
                        # Update only if this interval is shorter (more specific)
                        better_mask = mask & (length < chunk_best_lengths)
                        
                        if better_mask.any():
                            chunk_best_lengths[better_mask] = length
                            
                            for col in cols:
                                if col in info_df.columns:
                                    results[col][chunk_start:chunk_end][better_mask] = info_df.iloc[i][col]
                    
                    best_lengths[chunk_start:chunk_end] = chunk_best_lengths
                
                # Apply results to dataframe
                for col in cols:
                    df[col] = results[col]
                    
            except Exception as e:
                # 3. Fallback: IntervalTree (if numpy approach fails)
                try:
                    from intervaltree import IntervalTree
                    
                    tree = IntervalTree()
                    for idx in info_df.index:
                        tree[idx.left:idx.right] = idx
                    
                    def get_vals(x):
                        matches = tree.at(x)
                        if not matches:
                            return [np.nan] * len(cols)
                        sorted_matches = sorted(matches, key=lambda m: (m.end - m.begin))
                        best_match = sorted_matches[0]
                        return info_df.loc[best_match.data, cols].values.tolist()

                    mapped_series = df['Chainage'].apply(get_vals)
                    mapped_df = pd.DataFrame(mapped_series.tolist(), index=df.index, columns=cols)
                    
                    for col in cols:
                        df[col] = mapped_df[col]
                        
                except Exception as e2:
                    print(f"Error in optimized mapping: {e}, {e2}. Falling back to slow loop.")
                    self._fallback_slow_mapping(df, info_df, cols)

    def _fallback_slow_mapping(self, df: pd.DataFrame, info_df: pd.DataFrame, cols: List[str]):
        """Legacy slow path for overlapping intervals (O(N*M))"""
        print(f"Notice: Using fallback slow mapping for {cols}.")
        
        def find_val(x, col_name):
            try:
                matches = info_df.index.contains(x)
                if matches.any():
                    return info_df.loc[matches, col_name].iloc[0]
            except:
                pass
            return np.nan

        for col in cols:
            if col in info_df.columns:
                df[col] = df['Chainage'].apply(lambda x: find_val(x, col))

    def _get_vectorized_threshold(self, df: pd.DataFrame, thresholds_df: pd.DataFrame, 
                                exc_type: str, bound: str, track_type: str = None) -> pd.Series:
        """
        Retrieves threshold values as a pandas Series aligned with df.
        Returns np.nan for missing lookups to support vector operations.
        
        Fallback Behavior (v2.7):
        - If Class is NOT defined in threshold sheet for this Exc Type, fallback to 'both'
        - If Class IS defined but value is NaN, preserve NaN (no fallback)
        - This ensures LMC section automatically uses Mainline ('both') thresholds 
          when LMC-specific thresholds don't exist
        
        Examples:
        1. LMC class undefined → uses 'both' threshold (Mainline standard)
        2. LMC class defined with value → uses LMC-specific threshold
        3. LMC class defined with NaN → preserves NaN (no detection)
        """
        t_subset = thresholds_df[thresholds_df['Exc Type'] == exc_type].copy()
        if t_subset.empty: return pd.Series(np.nan, index=df.index)

        if track_type:
            t_subset = t_subset[
                (t_subset['Track Type'] == track_type) | 
                (t_subset['Track Type'].isna()) | 
                (t_subset['Track Type'] == 'both')
            ]
        
        if 'Class' not in t_subset.columns: return pd.Series(np.nan, index=df.index)
        if bound not in t_subset.columns: return pd.Series(np.nan, index=df.index)
            
        class_val_map = t_subset.set_index('Class')[bound].to_dict()
        threshold_series = df['Class'].map(class_val_map)
        
        # Fallback Logic
        if 'both' in class_val_map:
            both_val = class_val_map['both']
            # Identify classes that correspond to a defined row in thresholds (even if value is NaN)
            defined_classes = set(t_subset['Class'].unique())
            
            # If a row's class is NOT in defined_classes, use 'both'
            # If a row's class IS in defined_classes (e.g. SCL), keep original mapped value (even if NaN)
            undefined_mask = ~df['Class'].isin(defined_classes)
            
            # Apply fallback only to undefined classes
            # Note: We must handle the case where threshold_series is already NaN for undefined classes
            # We overwrite those NaNs with both_val
            threshold_series.loc[undefined_mask] = both_val
            
        # Enforce numeric type and use np.nan for missing
        return pd.to_numeric(threshold_series, errors='coerce').fillna(np.nan)

    def _group_consecutive(self, mask_series: pd.Series, df: pd.DataFrame, value_col: str, agg_func: str, section_name: str) -> pd.DataFrame:
        if not mask_series.any():
            return pd.DataFrame()

        changes = (mask_series != mask_series.shift()).cumsum()
        exc_df = df[mask_series].copy()
        exc_df['group_id'] = changes[mask_series]
        
        results = []
        grouped = exc_df.groupby('group_id')
        
        for gid, group in grouped:
            if agg_func == 'min':
                worst_idx = group[value_col].idxmin()
            else:
                # max or abs (stagger handles its own sign, passing raw values here usually)
                worst_idx = group[value_col].idxmax()
            
            worst_val = group.loc[worst_idx, value_col]
            worst_loc = group.loc[worst_idx, 'Chainage']
            worst_class = group.loc[worst_idx, 'Class']
            
            if 'Track Type' in group.columns:
                t_type = group['Track Type'].mode()[0] if not group['Track Type'].mode().empty else 'Unknown'
            else:
                t_type = 'Unknown'
            
            overlap = group['Overlap'].dropna().iloc[0] if 'Overlap' in group and not group['Overlap'].dropna().empty else None
            landmark = group['Landmark'].dropna().iloc[0] if 'Landmark' in group and not group['Landmark'].dropna().empty else None
            tl = group['Tension Length'].dropna().iloc[0] if 'Tension Length' in group and not group['Tension Length'].dropna().empty else None

            results.append({
                'FromM': group['Chainage'].min(),
                'ToM': group['Chainage'].max(),
                'length': group['Chainage'].max() - group['Chainage'].min(),
                'maxValue': worst_val,
                'maxLocation': worst_loc,
                'Track Type': t_type,
                'Overlap': overlap,
                'Tension Length': tl,
                'Landmark': landmark,
                'Class': worst_class,
                'Section': section_name
            })
            
        return pd.DataFrame(results)

    def _detect_scalar(self, df: pd.DataFrame, col_prefix: str, exc_type: str, thresholds: pd.DataFrame,
                      mode: str, date_str: str, track: str, line: str, section_name: str,
                      task_no: Optional[str] = None, station_start: Optional[str] = None,
                      station_end: Optional[str] = None) -> pd.DataFrame:
        """
        Handles Height and Wire Wear (Depth=2: L1, L2).
        Min Mode: L1 < L2. Lower is worse. Gatekeeper = max(L1, L2).
        Max Mode: L1 > L2. Higher is worse. Gatekeeper = min(L1, L2).
        """
        cols = [f'{col_prefix}{i}' for i in range(1, 5)]
        valid_cols = [c for c in cols if c in df.columns]
        if not valid_cols: return pd.DataFrame()

        # Phase 10.10: Use pre-computed columns instead of overwriting row_val
        # Map col_prefix + mode to the pre-computed column name
        _agg_col_map = {
            ('height', 'min'): 'height_min',
            ('height', 'max'): 'height_max',
            ('wear', 'min'): 'wear_min',
            ('wear', 'max'): 'wear_max',
        }
        agg_col = _agg_col_map.get((col_prefix, mode))

        if agg_col and agg_col in df.columns:
            # Use pre-computed column (does not overwrite)
            pass
        else:
            # Fallback: compute on the fly (should not happen in normal flow)
            agg_col = f'_tmp_{col_prefix}_{mode}'
            if mode == 'min':
                df[agg_col] = df[valid_cols].min(axis=1)
            else:
                df[agg_col] = df[valid_cols].max(axis=1)

        # 1. Fetch Thresholds (Depth 2 Only)
        l1_series = self._get_vectorized_threshold(df, thresholds, exc_type, f"{exc_type} L1")
        l2_series = self._get_vectorized_threshold(df, thresholds, exc_type, f"{exc_type} L2")

        active_thresholds = pd.concat([l1_series, l2_series], axis=1)

        # 2. Determine Gatekeeper
        if mode == 'min':
            gatekeeper = active_thresholds.max(axis=1, skipna=True)
            mask = df[agg_col] <= gatekeeper
        else:
            gatekeeper = active_thresholds.min(axis=1, skipna=True)
            mask = df[agg_col] >= gatekeeper

        # Ensure gatekeeper is not NaN
        mask = mask & gatekeeper.notna()

        # 3. Grouping
        result_df = self._group_consecutive(mask, df, agg_col, mode, section_name)
        if result_df.empty: return result_df
            
        # 4. Classification Loop (Priority: L1 > L2)
        result_df['level'] = 'TBD'
        result_df['Threshold Value'] = np.nan
        
        for idx, row in result_df.iterrows():
            val = float(row['maxValue'])
            cls = row['Class']
            
            # Fetch raw threshold values
            # Fix: manual lookup also had wrong args
            l1_raw = self._manual_threshold_lookup(thresholds, exc_type, f"{exc_type} L1", cls)
            l2_raw = self._manual_threshold_lookup(thresholds, exc_type, f"{exc_type} L2", cls)
            
            # Robust Type Casting (Handle strings in Excel)
            l1_val = pd.to_numeric(l1_raw, errors='coerce') if l1_raw is not None else np.nan
            l2_val = pd.to_numeric(l2_raw, errors='coerce') if l2_raw is not None else np.nan
            
            final_level = 'Unknown'
            final_thresh = np.nan
            
            if mode == 'min':
                # Check L1 first (Most Severe)
                # Ensure values are strictly less than or equal to threshold
                # AND ensure threshold is not None/NaN
                if not np.isnan(l1_val) and val <= l1_val:
                    final_level = 'L1'
                    final_thresh = l1_val
                elif not np.isnan(l2_val) and val <= l2_val:
                    final_level = 'L2'
                    final_thresh = l2_val
            else: # max
                if not np.isnan(l1_val) and val >= l1_val:
                    final_level = 'L1'
                    final_thresh = l1_val
                elif not np.isnan(l2_val) and val >= l2_val:
                    final_level = 'L2'
                    final_thresh = l2_val
            
            result_df.at[idx, 'level'] = final_level
            result_df.at[idx, 'Threshold Value'] = final_thresh

        # ID Generation
        result_df['exception type'] = exc_type
        short_code_map = {'Low Height': 'LH', 'High Height': 'HH', 'Wire Wear': 'W'}
        code = short_code_map.get(exc_type, 'XX')
        result_df['id'] = [
            self._build_exception_id(date_str, line, track, section_name, task_no, station_start, station_end, code, i)
            for i in range(len(result_df))
        ]
        
        return result_df

    def _manual_threshold_lookup(self, thresholds_df, exc_type, bound, cls):
        subset = thresholds_df[thresholds_df['Exc Type'] == exc_type]
        # Strict match first
        res = subset[subset['Class'] == cls]
        if not res.empty: 
            return res.iloc[0].get(bound) # Use .get() to avoid KeyError if column missing
        
        # Fallback to 'both'
        res = subset[subset['Class'] == 'both']
        if not res.empty: 
            return res.iloc[0].get(bound)
            
        return None

    def _detect_stagger(self, df: pd.DataFrame, thresholds: pd.DataFrame, date_str: str, track: str, line: str, section_name: str,
                       task_no: Optional[str] = None, station_start: Optional[str] = None,
                       station_end: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Handles Stagger (Depth=3: L1, L2, L3).
        Abs Mode: Higher Absolute Value is worse.
        Gatekeeper: min(L1, L2, L3) (Absolute).
        """
        stagger_cols = ['stagger1', 'stagger2', 'stagger3', 'stagger4']
        valid_cols = [c for c in stagger_cols if c in df.columns]
        if not valid_cols: return pd.DataFrame(), pd.DataFrame()
            
        df['stg_max'] = df[valid_cols].max(axis=1) # Positive (Left)
        df['stg_min'] = df[valid_cols].min(axis=1) # Negative (Right)
        
        thresh_col = 'min' # Fix: Stagger thresholds (start of exception range) are in 'min' column

        def check_stagger(val_col, direction):
            masks = []
            
            # Loop Track Types because thresholds depend on Tangent/Curve
            for t_type in ['Tangent', 'Curve']:
                # 1. Fetch Thresholds (Depth 3)
                # Correct usage: exc_type is generic 'Stagger L1' in the method call, wait.
                # In _detect_stagger call: 
                # l1_s = self._get_vectorized_threshold(df, thresholds, 'Stagger L1', thresh_col, track_type=t_type)
                # Here 'Stagger L1' is passed as exc_type.
                # But in mock/excel, Exc Type is 'Stagger Left' or 'Stagger Right'.
                # AND the column is 'Stagger L1'.
                
                # Fix: We need to look up thresholds for "Stagger Left" or "Stagger Right" (based on direction)
                # And the column "Stagger L1"
                
                target_exc_type = f'Stagger {"Left" if direction == "L" else "Right"}'
                
                l1_s = self._get_vectorized_threshold(df, thresholds, target_exc_type, 'Stagger L1', track_type=t_type)
                l2_s = self._get_vectorized_threshold(df, thresholds, target_exc_type, 'Stagger L2', track_type=t_type)
                l3_s = self._get_vectorized_threshold(df, thresholds, target_exc_type, 'Stagger L3', track_type=t_type)
                
                # 2. Determine Gatekeeper
                # E.g. L1=450, L2=400, L3=350.
                # Warning if Abs(Val) > 350.
                # Gatekeeper is min(L1, L2, L3).
                gate_s = np.fmin(np.fmin(l1_s, l2_s), l3_s)
                
                # Create Track Type Mask
                if 'Track Type' in df.columns:
                    t_mask = (df['Track Type'] == t_type)
                else:
                    t_mask = pd.Series(False, index=df.index)
                
                # Create Value Mask
                if direction == 'L':
                    # Positive values > gate
                    v_mask = (df[val_col] >= gate_s)
                else:
                    # Negative values < -gate
                    v_mask = (df[val_col] <= -gate_s) 
                
                masks.append(t_mask & v_mask & gate_s.notna())
            
            if not masks: return pd.DataFrame()
            
            # Combine masks from Tangent/Curve logic
            final_mask = pd.concat(masks, axis=1).any(axis=1)
            
            # 3. Grouping (Use 'max' for abs mode because we want peak deviation)
            # For Left (Positive), max is peak.
            # For Right (Negative), min is peak.
            agg_mode = 'max' if direction == 'L' else 'min'
            res = self._group_consecutive(final_mask, df, val_col, agg_mode, section_name)
            
            if res.empty: return res
                
            # NEW: Explicit naming for Left/Right differentiation
            res['exception type'] = f'Stagger {"Left" if direction == "L" else "Right"}'
            res['level'] = 'TBD'
            res['Threshold Value'] = np.nan
            
            # 4. Classification Loop (L1 > L2 > L3)
            for idx, row in res.iterrows():
                val_abs = abs(float(row['maxValue'])) # Cast float
                cls = row['Class']
                tt = row['Track Type'] 
                
                # Fetch raw
                target_exc_type = f'Stagger {"Left" if direction == "L" else "Right"}'
                l1_raw = self._manual_threshold_lookup_stagger(thresholds, target_exc_type, 'Stagger L1', cls, tt)
                l2_raw = self._manual_threshold_lookup_stagger(thresholds, target_exc_type, 'Stagger L2', cls, tt)
                l3_raw = self._manual_threshold_lookup_stagger(thresholds, target_exc_type, 'Stagger L3', cls, tt)
                
                # Cast float
                l1 = float(l1_raw) if l1_raw is not None else None
                l2 = float(l2_raw) if l2_raw is not None else None
                l3 = float(l3_raw) if l3_raw is not None else None
                
                final_level = 'Unknown'
                final_thresh = np.nan
                
                if l1 is not None and val_abs >= l1:
                    final_level = 'L1'
                    final_thresh = l1
                elif l2 is not None and val_abs >= l2:
                    final_level = 'L2'
                    final_thresh = l2
                elif l3 is not None and val_abs >= l3:
                    final_level = 'L3'
                    final_thresh = l3
                    
                res.at[idx, 'level'] = final_level
                res.at[idx, 'Threshold Value'] = final_thresh

            code = 'SL' if direction == 'L' else 'SR'
            res['id'] = [
                self._build_exception_id(date_str, line, track, section_name, task_no, station_start, station_end, code, i)
                for i in range(len(res))
            ]
            return res

        left_res = check_stagger('stg_max', 'L')
        right_res = check_stagger('stg_min', 'R')
        
        return left_res, right_res

    def _manual_threshold_lookup_stagger(self, thresholds_df, exc_type, bound, cls, track_type):
        subset = thresholds_df[
            (thresholds_df['Exc Type'] == exc_type) & 
            ((thresholds_df['Track Type'] == track_type) | (thresholds_df['Track Type'].isna()) | (thresholds_df['Track Type'] == 'both'))
        ]
        res = subset[subset['Class'] == cls]
        if not res.empty: return res.iloc[0][bound]
        res = subset[subset['Class'] == 'both']
        if not res.empty: return res.iloc[0][bound]
        return None

    def _save_to_database(
        self,
        db_manager: 'DatabaseManager',
        results: Dict[str, Any],
        line: str,
        section: str,
        track: str,
        date_str: str,
        raw_data_file_path: Optional[str] = None,
        raw_data_file_name: Optional[str] = None,
        raw_data_file_size: Optional[int] = None,
        task_no: Optional[str] = None,
        station_start: Optional[str] = None,
        station_end: Optional[str] = None
    ) -> str:
        """
        Save analysis results to database (Stateful Transformation).
        
        Saves:
        - Session metadata to analysis_sessions table
        - All detected exceptions to exceptions table
        
        Args:
            db_manager: DatabaseManager instance
            results: Analysis results dictionary
            line: Line code (e.g., 'EAL', 'TML')
            section: Section name
            track: Track code (e.g., 'UP', 'DOWN')
            date_str: Analysis date (YYYYMMDD)
            raw_data_file_path: Optional source file path
            raw_data_file_name: Optional source file name
            raw_data_file_size: Optional source file size
            task_no: Optional task number
            station_start: Optional start station
            station_end: Optional end station
        
        Returns:
            Session ID (UUID string)
        """
        from .database import save_analysis_session, save_exceptions_from_analysis
        
        # Prepare session data
        session_data = {
            'line': line,
            'section': section,
            'track': track,
            'date_str': date_str,
            'raw_data_file_path': raw_data_file_path,
            'raw_data_file_name': raw_data_file_name,
            'raw_data_file_size': raw_data_file_size,
            'task_no': task_no,
            'station_start': station_start,
            'station_end': station_end
        }
        
        # Prepare exceptions dictionary for save function
        exceptions_dict: Dict[str, List[Dict[str, Any]]] = {}
        for exc_type, exc_data in results.items():
            if exc_type == 'session_id':
                continue
            if isinstance(exc_data, pd.DataFrame) and not exc_data.empty:
                exceptions_dict[exc_type] = exc_data.to_dict(orient='records')
        
        # Save to database
        with db_manager.get_connection() as conn:
            session_id = save_analysis_session(conn, session_data)
            
            if exceptions_dict:
                saved_count = save_exceptions_from_analysis(conn, session_id, exceptions_dict)
                logger.info(f"Saved {saved_count} exceptions for session {session_id}")
        
        return session_id
