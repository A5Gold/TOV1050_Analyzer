import pandas as pd
import numpy as np
import logging
import math
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, List

# Configure logging
logger = logging.getLogger(__name__)


STAGGER_MAGNITUDE_RULE_VERSION = "symmetric-stagger-magnitude-2026-11-03-v1"
STAGGER_LEVELS = ("Stagger L1", "Stagger L2", "Stagger L3")
STAGGER_SIDES = ("Stagger Left", "Stagger Right")


def normalize_stagger_thresholds(frame: pd.DataFrame, *, source: str = "threshold") -> pd.DataFrame:
    """Expand legacy one-sided stagger rows into a shared magnitude per context.

    Only the returned in-memory frame changes. Conflicting source rows must be
    reviewed instead of resolved by row order.
    """
    if "Exc Type" not in frame or not any(column in frame for column in STAGGER_LEVELS):
        return frame.copy()

    records = frame.to_dict(orient="records")
    groups = {}
    stagger_positions = set()

    for position, row in enumerate(records):
        side = str(row.get("Exc Type", "")).strip()
        if side not in STAGGER_SIDES:
            continue
        stagger_positions.add(position)
        context = (str(row.get("Class", "")).strip(), str(row.get("Track Type", "")).strip())
        group = groups.setdefault(context, {"first": position, "rows": {}, "levels": {}})
        group["rows"].setdefault(side, row)
        for level in STAGGER_LEVELS:
            value = row.get(level)
            if value is None or value is pd.NA or (isinstance(value, str) and not value.strip()):
                continue
            if not isinstance(value, str) and pd.isna(value):
                continue
            try:
                number = float(str(value).replace(",", "").strip())
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{source}/threshold row {position + 2}: invalid {side} {level} "
                    f"for Class={context[0]}, Track Type={context[1]}: {value!r}"
                ) from exc
            if not math.isfinite(number):
                raise ValueError(
                    f"{source}/threshold row {position + 2}: non-finite {side} {level} "
                    f"for Class={context[0]}, Track Type={context[1]}: {value!r}"
                )
            magnitude = abs(number)
            prior = group["levels"].get(level)
            if prior is not None and not math.isclose(prior[0], magnitude, rel_tol=0, abs_tol=1e-9):
                raise ValueError(
                    f"{source}/threshold rows {prior[1] + 2} and {position + 2}: "
                    f"conflicting Stagger magnitude for Class={context[0]}, "
                    f"Track Type={context[1]}, {level}: {prior[0]} vs {magnitude}"
                )
            group["levels"][level] = (magnitude, position)

    if not groups:
        return frame.copy()

    insert_at = {group["first"]: group for group in groups.values()}
    output = []
    for position, row in enumerate(records):
        if position not in stagger_positions:
            output.append(row)
            continue
        group = insert_at.get(position)
        if group is None:
            continue
        if not group["levels"]:
            raise ValueError(f"{source}/threshold row {position + 2}: Stagger Left and Right have no configured levels")
        for side in STAGGER_SIDES:
            normalized = dict(group["rows"].get(side, row))
            normalized["Exc Type"] = side
            for level in STAGGER_LEVELS:
                normalized[level] = group["levels"].get(level, (np.nan,))[0]
            output.append(normalized)

    result = pd.DataFrame(output, columns=frame.columns)
    result.attrs["stagger_magnitude_rule_version"] = STAGGER_MAGNITUDE_RULE_VERSION
    return result

class MetadataManager:
    """
    負責載入與管理 Metadata (Excel)。
    v2.4 Refactor:
    - String Cleaning for Class and Track Type.
    - Numeric Enforcement for thresholds.
    """

    def __init__(self, config_path: Union[str, Path]):
        self.config_path = Path(config_path)
        self._cache: Dict[str, pd.DataFrame] = {}
        
        logger.info(f"Initializing MetadataManager with config_path: {self.config_path.absolute()}")
        
        if not self.config_path.exists():
            error_msg = f"Metadata file not found at: {self.config_path.absolute()}"
            logger.error(error_msg)
            
            # Log parent directory info for debugging
            parent_dir = self.config_path.parent
            logger.error(f"Parent directory: {parent_dir.absolute()}, exists: {parent_dir.exists()}")
            if parent_dir.exists():
                try:
                    available_files = list(parent_dir.glob("*.xlsx"))
                    logger.error(f"Available .xlsx files in parent dir: {[f.name for f in available_files]}")
                except Exception as e:
                    logger.error(f"Failed to list parent directory: {e}")
            
            raise FileNotFoundError(error_msg)
        
        logger.info(f"MetadataManager initialized successfully. File size: {self.config_path.stat().st_size} bytes")

    def _load_sheet(self, sheet_name: str) -> pd.DataFrame:
        if sheet_name not in self._cache:
            logger.info(f"Loading sheet '{sheet_name}' from {self.config_path.name}")
            try:
                with pd.ExcelFile(self.config_path) as xl:
                    real_sheet_names = xl.sheet_names
                    logger.debug(f"Available sheets: {real_sheet_names}")
                    
                    target_sheet = sheet_name
                    if sheet_name not in real_sheet_names:
                        # Optional: Add loose matching logic if needed
                        error_msg = f"Sheet '{sheet_name}' not found. Available: {real_sheet_names}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)

                    df = pd.read_excel(xl, sheet_name=target_sheet)
                    logger.info(f"Sheet '{sheet_name}' loaded. Shape: {df.shape}")
                
                # Column Name Cleaning
                df.columns = df.columns.astype(str).str.strip()
                
                # Value Cleaning: Class, Track Type
                if 'Class' in df.columns:
                    df['Class'] = df['Class'].astype(str).str.strip()
                    
                if 'Track Type' in df.columns:
                    df['Track Type'] = df['Track Type'].astype(str).str.strip()

                # Keep wide Stagger tokens until the common adapter validates
                # them; otherwise a malformed value silently becomes NaN.
                if sheet_name == 'threshold':
                     if 'Exc Type' in df and 'min' in df:
                         for position, row in df.iterrows():
                             level = str(row['Exc Type']).strip()
                             if level not in STAGGER_LEVELS:
                                 continue
                             value = row['min']
                             if pd.isna(value) or (isinstance(value, str) and not value.strip()):
                                 continue
                             try:
                                 number = float(str(value).replace(',', '').strip())
                             except (TypeError, ValueError) as exc:
                                 raise ValueError(
                                     f"{self.config_path}/threshold row {position + 2}: invalid {level} min "
                                     f"for Class={row.get('Class')}, Track Type={row.get('Track Type')}: {value!r}"
                                 ) from exc
                             if not math.isfinite(number):
                                 raise ValueError(
                                     f"{self.config_path}/threshold row {position + 2}: non-finite {level} min "
                                     f"for Class={row.get('Class')}, Track Type={row.get('Track Type')}: {value!r}"
                                 )
                     for col in df.columns:
                         if col in STAGGER_LEVELS:
                             continue
                         if 'min' in col.lower() or 'max' in col.lower() or 'L1' in col or 'L2' in col or 'L3' in col:
                             df[col] = pd.to_numeric(
                                 df[col].astype(str).str.replace(',', '', regex=False).str.strip(),
                                 errors='coerce',
                             )
                     df = normalize_stagger_thresholds(df, source=str(self.config_path))

                self._cache[sheet_name] = df
                logger.info(f"Sheet '{sheet_name}' cached successfully")
            except Exception as e:
                logger.error(f"Failed to load sheet '{sheet_name}': {e}", exc_info=True)
                try:
                    with pd.ExcelFile(self.config_path) as xl:
                        available = xl.sheet_names
                except:
                    available = "Unknown"
                error_msg = f"Failed to load sheet '{sheet_name}'. Available: {available}. Error: {e}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        return self._cache[sheet_name].copy()

    def _get_sheet_name(self, line: str, section: str, track: str) -> str:
        # RAC section reuses Mainline sheet logic (EAL UP/DN)
        if section == 'RAC':
            return f"{line} {track}"
        
        if section == 'LOW':
            return "LOW S1"
        if section == 'Mainline':
            return f"{line} {track}"
        return f"{section} {track}"

    def _extract_interval_data(self, sheet_name: str, start_col: str, end_col: str, value_cols: List[str]) -> pd.DataFrame:
        """
        Extract interval data from a sheet with robust numeric parsing.
        
        Phase 10.10 Post-Bug Issue 4: TML DN Stagger 異常未生成
        - 根因: Metadata Excel 數值欄位含有千分位逗號 (e.g., '81,410.9')
        - pd.to_numeric(errors='coerce') 無法解析含逗號的字串，導致 NaN
        - 修復: 在 pd.to_numeric 前先移除逗號和空白
        """
        try:
            df = self._load_sheet(sheet_name)
        except ValueError:
            return pd.DataFrame()
        
        required = [start_col, end_col] + value_cols
        missing = [c for c in required if c not in df.columns]
        if missing:
            print(f"Warning: Sheet '{sheet_name}' missing columns {missing}. Available: {df.columns.tolist()}")
            return pd.DataFrame()

        sub_df = df[[start_col, end_col] + value_cols].copy()
        sub_df = sub_df.dropna(subset=[start_col, end_col])
        
        # Phase 10.10 Issue 4 Fix: Clean numeric columns before conversion
        # Remove thousand separators (commas) and whitespace
        def clean_numeric(val):
            if pd.isna(val):
                return val
            if isinstance(val, (int, float)):
                return val
            # Convert to string, strip whitespace, remove commas
            s = str(val).strip().replace(',', '')
            return s if s else np.nan
        
        sub_df[start_col] = sub_df[start_col].apply(clean_numeric)
        sub_df[end_col] = sub_df[end_col].apply(clean_numeric)
        
        sub_df[start_col] = pd.to_numeric(sub_df[start_col], errors='coerce')
        sub_df[end_col] = pd.to_numeric(sub_df[end_col], errors='coerce')
        sub_df = sub_df.dropna(subset=[start_col, end_col])
        
        if sub_df.empty:
            return pd.DataFrame()

        try:
            starts = np.minimum(sub_df[start_col], sub_df[end_col])
            ends = np.maximum(sub_df[start_col], sub_df[end_col])
            sub_df.index = pd.IntervalIndex.from_arrays(starts, ends, closed='both')
        except Exception as e:
            print(f"Interval creation failed for {sheet_name}: {e}")
            return pd.DataFrame()
        
        return sub_df[value_cols]

    def _get_boundary_df(self, line: str, track: str, selected_section: str) -> Tuple[pd.DataFrame, str, str]:
        """Helper to get raw boundary dataframe and column names"""
        df = self._load_sheet('Exception Boundarys')
        
        prefix = "UP Track" if "UP" in track.upper() else "DN Track"
        start_col = f"{prefix} FromM"
        end_col = f"{prefix} ToM"
        
        df = df[df['Line'] == line].copy()
        
        if line == 'EAL':
            if selected_section == 'LMC':
                # LMC section: only use LMC class boundaries
                df = df[df['Class'] == 'LMC']
            elif selected_section in ['RAC', 'LOW', 'Mainline']:
                # RAC, LOW, and Mainline: use same logic
                # Exclude LMC to get Mainline/Default boundaries
                df = df[df['Class'] != 'LMC']
        
        # Ensure numeric
        df[start_col] = pd.to_numeric(df[start_col], errors='coerce')
        df[end_col] = pd.to_numeric(df[end_col], errors='coerce')
        df = df.dropna(subset=[start_col, end_col])
        
        return df, start_col, end_col

    def get_exception_boundaries(self, line: str, track: str, selected_section: str) -> pd.DataFrame:
        df, start_col, end_col = self._get_boundary_df(line, track, selected_section)
        
        if df.empty:
            return pd.DataFrame()

        try:
            starts = np.minimum(df[start_col], df[end_col])
            ends = np.maximum(df[start_col], df[end_col])
            df.index = pd.IntervalIndex.from_arrays(starts, ends, closed='both')
            return df[['Class']]
        except Exception as e:
            print(f"Error creating boundary intervals: {e}")
            return pd.DataFrame()

    def get_boundaries_for_plot(self, line: str, track: str, selected_section: str) -> pd.DataFrame:
        """Returns Class boundaries as a simple DataFrame [Class, FromM, ToM] for plotting"""
        try:
            df, start_col, end_col = self._get_boundary_df(line, track, selected_section)
            if df.empty:
                return pd.DataFrame(columns=['Class', 'FromM', 'ToM'])
            
            # Normalize to FromM < ToM just in case, or keep original? 
            # Usually strict From/To is better for plotting lines.
            result = df[['Class', start_col, end_col]].copy()
            result.columns = ['Class', 'FromM', 'ToM']
            return result
        except Exception:
            return pd.DataFrame(columns=['Class', 'FromM', 'ToM'])

    def get_track_type_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        sheet = self._get_sheet_name(line, section, track)
        return self._extract_interval_data(sheet, 'Track Type FromM', 'Track Type ToM', ['Track Type'])

    def get_overlap_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        sheet = self._get_sheet_name(line, section, track)
        return self._extract_interval_data(sheet, 'Overlap FromM', 'Overlap ToM', ['Overlap', 'Tension Length'])

    def get_landmark_intervals(self, line: str, section: str, track: str) -> pd.DataFrame:
        sheet = self._get_sheet_name(line, section, track)
        return self._extract_interval_data(sheet, 'Landmark FromM', 'Landmark ToM', ['Landmark'])

    def get_all_thresholds(self) -> pd.DataFrame:
        df = self._load_sheet('threshold')
        return self._normalize_thresholds(df)

    def _normalize_thresholds(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adapts legacy Long Format (Excel) to Wide Format (Detector).
        """
        # 1. Check if already wide (has 'Low Height L1' column)
        if 'Low Height L1' in df.columns or any(column in df for column in STAGGER_LEVELS):
            return normalize_stagger_thresholds(df, source=str(self.config_path))
            
        # 2. Pivot Long to Wide
        grouped = {}
        
        for idx, row in df.iterrows():
            cls = row.get('Class', 'both')
            tt = row.get('Track Type', 'both')
            raw_exc = str(row.get('Exc Type', '')).strip()
            
            # Skip empty or normal
            if not raw_exc or raw_exc.lower() == 'normal':
                continue
            
            # Determine Base Type and Level
            col_name = None
            val = None
            target_types = []
            
            # Stagger
            if 'Stagger' in raw_exc:
                level = raw_exc.replace('Stagger', '').strip() # L1, L2, L3
                col_name = f'Stagger {level}'
                val = row.get('min') # Stagger uses min (e.g. 480)
                target_types = ['Stagger Left', 'Stagger Right']
                    
            # Low Height
            elif 'Low Height' in raw_exc:
                level = raw_exc.replace('Low Height', '').strip()
                col_name = f'Low Height {level}'
                val = row.get('max') # Low Height uses max (e.g. 4475)
                target_types = ['Low Height']
                
            # High Height
            elif 'High Height' in raw_exc:
                level = raw_exc.replace('High Height', '').strip()
                col_name = f'High Height {level}'
                val = row.get('min') # High Height uses min
                target_types = ['High Height']

            # Wire Wear
            elif 'Wire Wear' in raw_exc:
                level = raw_exc.replace('Wire Wear', '').strip()
                col_name = f'Wire Wear {level}'
                val = row.get('max') # Wire Wear uses max (e.g. 7.24)
                target_types = ['Wire Wear']

            # Apply to targets
            for base_type in target_types:
                key = (cls, tt, base_type)
                if key not in grouped:
                    grouped[key] = {'Class': cls, 'Track Type': tt, 'Exc Type': base_type}
                
                # Only set if val is numeric
                if pd.notna(val):
                    if base_type in STAGGER_SIDES and col_name in grouped[key]:
                        previous = grouped[key][col_name]
                        if not math.isclose(abs(float(previous)), abs(float(val)), rel_tol=0, abs_tol=1e-9):
                            raise ValueError(
                                f"{self.config_path}/threshold row {idx + 2}: conflicting Stagger magnitude "
                                f"for Class={cls}, Track Type={tt}, {col_name}: {previous} vs {val}"
                            )
                    grouped[key][col_name] = val
                
        # Convert to DataFrame
        if not grouped:
            return df

        normalized_df = pd.DataFrame(list(grouped.values()))
        return normalize_stagger_thresholds(normalized_df, source=str(self.config_path))

    # ─── Calculation Module: Tension Length Lookup ─────────────────────────────

    def get_tension_length_lookup(self, line: str, track: str, section: str) -> pd.DataFrame:
        """
        Return a standardised tension-length lookup table for the calculation module.

        Converts the existing Overlap-based metadata into one row per tension length,
        so the wear calculator can map each chainage to a unique TL interval.

        Args:
            line:    'EAL' or 'TML'
            track:   'UP' or 'DN'
            section: 'Mainline', 'RAC', 'LOW S1', 'LMC'

        Returns:
            DataFrame with columns: from_m, to_m, tension_length, track_type, overlap
        """
        sheet_name = self._get_sheet_name_for_calc(line, track, section)
        try:
            df = self._load_sheet(sheet_name)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning(f"get_tension_length_lookup: cannot load sheet '{sheet_name}': {exc}")
            return pd.DataFrame(columns=['from_m', 'to_m', 'tension_length', 'track_type', 'overlap'])

        result = self._aggregate_tension_lengths(df)
        return self._sort_tension_lengths(result)

    def get_tension_length_source_rows(
        self, line: str, track: str, section: str
    ) -> pd.DataFrame:
        """Return unsplit source rows for section-aware wear-cycle resolution."""
        columns = ["from_m", "to_m", "tension_length"]
        sheet_name = self._get_sheet_name_for_calc(line, track, section)
        try:
            frame = self._load_sheet(sheet_name)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning(
                "get_tension_length_source_rows: cannot load sheet '%s': %s",
                sheet_name,
                exc,
            )
            return pd.DataFrame(columns=columns)

        source_columns = {
            "Overlap FromM": "from_m",
            "Overlap ToM": "to_m",
            "Tension Length": "tension_length",
        }
        if not set(source_columns).issubset(frame.columns):
            logger.warning(
                "get_tension_length_source_rows: missing columns %s",
                set(source_columns) - set(frame.columns),
            )
            return pd.DataFrame(columns=columns)

        result = frame.loc[:, list(source_columns)].rename(columns=source_columns).copy()
        populated = pd.DataFrame(
            {
                column: result[column].notna()
                & result[column].astype(str).str.strip().ne("")
                for column in columns
            }
        ).any(axis=1)
        return result.loc[populated, columns].reset_index(drop=True)

    def _get_sheet_name_for_calc(self, line: str, track: str, section: str) -> str:
        """Map (line, track, section) to the correct metadata sheet name."""
        _map = {
            ('EAL', 'UP', 'Mainline'): 'EAL UP',
            ('EAL', 'DN', 'Mainline'): 'EAL DN',
            ('EAL', 'UP', 'RAC'):      'RAC UP',
            ('EAL', 'DN', 'RAC'):      'RAC DN',
            ('EAL', 'UP', 'LOW S1'):   'LOW S1',
            ('EAL', 'DN', 'LOW S1'):   'LOW S1',
            ('EAL', 'UP', 'LMC'):      'LMC UP',
            ('EAL', 'DN', 'LMC'):      'LMC DN',
            ('TML', 'UP', 'Mainline'): 'TML UP',
            ('TML', 'DN', 'Mainline'): 'TML DN',
        }
        key = (line.upper(), track.upper(), section)
        return _map.get(key, f'{line.upper()} {track.upper()}')

    def _aggregate_tension_lengths(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert Overlap-based metadata rows into one row per tension length.

        When a row contains multiple TLs (comma-separated), the Overlap interval
        is split evenly among them.
        """
        required = {'Overlap FromM', 'Overlap ToM', 'Tension Length'}
        if not required.issubset(df.columns):
            logger.warning(f"_aggregate_tension_lengths: missing columns {required - set(df.columns)}")
            return pd.DataFrame(columns=['from_m', 'to_m', 'tension_length', 'track_type', 'overlap'])

        rows = []
        def _to_float(value):
            if pd.isna(value):
                return None
            if isinstance(value, (int, float)):
                return float(value)
            cleaned = str(value).strip().replace(',', '')
            if not cleaned:
                return None
            return float(cleaned)

        for _, row in df.iterrows():
            from_m = _to_float(row.get('Overlap FromM'))
            to_m   = _to_float(row.get('Overlap ToM'))
            tl_raw = row.get('Tension Length')

            if from_m is None or to_m is None:
                continue
            if pd.isna(tl_raw):
                continue

            tl_list = [t.strip() for t in str(tl_raw).split(',') if t.strip()]
            if not tl_list:
                continue

            track_type = row.get('Track Type', '') if not pd.isna(row.get('Track Type', np.nan)) else ''
            overlap    = row.get('Overlap', '')    if not pd.isna(row.get('Overlap', np.nan))    else ''

            if len(tl_list) == 1:
                rows.append({
                    'from_m':         from_m,
                    'to_m':           to_m,
                    'tension_length': tl_list[0],
                    'track_type':     str(track_type),
                    'overlap':        str(overlap),
                })
            else:
                segment = (to_m - from_m) / len(tl_list)
                for i, tl in enumerate(tl_list):
                    rows.append({
                        'from_m':         from_m + i * segment,
                        'to_m':           from_m + (i + 1) * segment,
                        'tension_length': tl,
                        'track_type':     str(track_type),
                        'overlap':        str(overlap),
                    })

        return pd.DataFrame(rows, columns=['from_m', 'to_m', 'tension_length', 'track_type', 'overlap'])

    def _sort_tension_lengths(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sort tension-length rows by TL label: H -> numeric -> X -> T -> D -> M -> L -> other."""
        if df.empty:
            return df

        def _sort_key(tl: str):
            tl = str(tl).strip()
            if not tl:
                return (9, 0, tl)
            prefix = tl[0].upper()
            suffix = tl[1:]
            num = int(suffix) if suffix.isdigit() else 0
            order = {'H': 0, 'X': 2, 'T': 3, 'D': 4, 'M': 5, 'L': 6}
            if prefix.isdigit():
                return (1, int(tl) if tl.isdigit() else 0, tl)
            return (order.get(prefix, 7), num, tl)

        df = df.copy()
        df['_sort_key'] = df['tension_length'].apply(_sort_key)
        df = df.sort_values('_sort_key').drop(columns=['_sort_key']).reset_index(drop=True)
        return df
