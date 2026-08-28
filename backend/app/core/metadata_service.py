import os
import shutil
import time
import tempfile
import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Union, Any, Optional
from app.core.metadata import MetadataManager
from app.core.tov1050_contract import LINE_WORKBOOKS
from app.core.tov1050_metadata import TOV1050MetadataManager

# Configure logging
logger = logging.getLogger(__name__)

class MetadataService:
    def __init__(self, config_dir: Union[str, Path]):
        self.config_dir = Path(config_dir)
        logger.info(f"MetadataService initialized with config_dir: {self.config_dir.absolute()}")
        logger.info(f"Config directory exists: {self.config_dir.exists()}")
        
        if self.config_dir.exists():
            try:
                # Log available files for diagnostics
                xlsx_files = list(self.config_dir.glob("*.xlsx"))
                logger.info(f"Available .xlsx files in config_dir: {[f.name for f in xlsx_files]}")
            except Exception as e:
                logger.warning(f"Failed to list config directory: {e}")

    def create_backup(self, filename: str) -> str:
        """Creates a backup of the specified configuration file."""
        source = self.config_dir / filename
        logger.info(f"Creating backup for file: {source.absolute()}")
        
        if not source.exists():
            error_msg = f"Config file not found at: {source.absolute()}"
            logger.error(error_msg)
            logger.error(f"Config directory: {self.config_dir.absolute()}, exists: {self.config_dir.exists()}")
            
            # List available files for debugging
            if self.config_dir.exists():
                try:
                    available_files = list(self.config_dir.glob("*.xlsx"))
                    logger.error(f"Available .xlsx files: {[f.name for f in available_files]}")
                except Exception as e:
                    logger.error(f"Failed to list files: {e}")
            
            raise FileNotFoundError(error_msg)
        
        backups_dir = self.config_dir / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Backup directory: {backups_dir.absolute()}")
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        # Change extension to .xlsx (Plan Step 2)
        backup_name = f"{source.stem}_{timestamp}.xlsx"
        backup_path = backups_dir / backup_name
        
        shutil.copy2(source, backup_path)
        logger.info(f"Backup created successfully: {backup_path.absolute()}")
        return str(backup_path)

    def validate_row(self, row: Dict[str, Any]) -> bool:
        """
        Validates a single row of threshold configuration.
        Enforces L1 (Critical) > L2 (Warning) > L3 (Info) OR reverse based on logic.
        """
        exc_type = row.get("Exc Type", "")
        
        # Helper to safely get float or None
        def get_val(key):
            v = row.get(key)
            if pd.isna(v) or v == "":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        # Determine keys based on Exc Type
        if "Low Height" in exc_type:
            prefix = "Low Height"
            mode = "min" # L1 < L2 < L3
        elif "High Height" in exc_type:
            prefix = "High Height"
            mode = "max" # L1 > L2 > L3
        elif "Wire Wear" in exc_type:
            prefix = "Wire Wear"
            mode = "min" # L1 < L2 < L3
        elif "Stagger" in exc_type:
            prefix = "Stagger"
            mode = "max" # L1 > L2 > L3 (Abs deviation)
        else:
            return True # Unknown type, skip logic validation
            
        l1 = get_val(f"{prefix} L1")
        l2 = get_val(f"{prefix} L2")
        l3 = get_val(f"{prefix} L3")
        
        # Validation Logic:
        if mode == "min": # Lower is worse (L1 < L2 < L3)
            if l1 is not None and l2 is not None and l1 > l2: return False
            if l2 is not None and l3 is not None and l2 > l3: return False
            if l1 is not None and l3 is not None and l1 > l3: return False
        else: # Higher is worse (L1 > L2 > L3)
            if l1 is not None and l2 is not None and l1 < l2: return False
            if l2 is not None and l3 is not None and l2 < l3: return False
            if l1 is not None and l3 is not None and l1 < l3: return False
            
        return True

    def get_sheet_names(self, filename: str) -> List[str]:
        """Returns list of sheet names in the Excel file."""
        file_path = self.config_dir / filename
        logger.info(f"Getting sheet names for file: {file_path.absolute()}")
        
        if not file_path.exists():
            error_msg = f"Config file not found at: {file_path.absolute()}"
            logger.error(error_msg)
            logger.error(f"Config directory: {self.config_dir.absolute()}, exists: {self.config_dir.exists()}")
            
            # List available files for debugging
            if self.config_dir.exists():
                try:
                    available_files = list(self.config_dir.glob("*.xlsx"))
                    logger.error(f"Available .xlsx files: {[f.name for f in available_files]}")
                except Exception as e:
                    logger.error(f"Failed to list files: {e}")
            
            raise FileNotFoundError(error_msg)
        
        with pd.ExcelFile(file_path) as xl:
            sheet_names = xl.sheet_names
            logger.info(f"Sheet names retrieved: {sheet_names}")
            return sheet_names

    def get_metadata(self, filename: str, sheet_name: str = 'threshold') -> List[Dict[str, Any]]:
        """
        Loads metadata from Excel and returns as list of dicts.
        Supports fetching different sheets.
        """
        file_path = self.config_dir / filename
        logger.info(f"Loading metadata from: {file_path.absolute()}, sheet: {sheet_name}")
        
        if not file_path.exists():
            error_msg = f"Config file not found at: {file_path.absolute()}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            # The settings screen must use the same TOV1050 adapter as the
            # analyzer. The generic manager would drop Location Type while
            # normalizing the long-form threshold sheet.
            manager_type = TOV1050MetadataManager if filename in {
                *LINE_WORKBOOKS.values(),
                "TKS metadata.xlsx",
            } else MetadataManager
            mgr = manager_type(config_path=file_path)
            
            is_tov1050 = filename in {
                *LINE_WORKBOOKS.values(),
                "TKS metadata.xlsx",
            }
            if sheet_name == 'threshold' and not is_tov1050:
                df = mgr.get_all_thresholds()
            else:
                # Access internal method to load raw sheet
                df = mgr._load_sheet(sheet_name)
            
            records = df.replace({np.nan: None}).to_dict(orient="records")
            logger.info(f"Metadata loaded successfully. Rows: {len(records)}")
            return records
        except ValueError as e:
            # Attempt normalized sheet name match (case/space/underscore)
            def normalize_name(value: str) -> str:
                # Remove spaces, underscores, and convert to lower case
                return value.strip().lower().replace(" ", "").replace("_", "")

            try:
                with pd.ExcelFile(file_path) as xl:
                    sheet_names = xl.sheet_names
                
                target_norm = normalize_name(sheet_name)
                
                # Find matching sheet
                matched_sheet = None
                for name in sheet_names:
                    if normalize_name(name) == target_norm:
                        matched_sheet = name
                        break
                
                if matched_sheet:
                    logger.warning(f"Sheet name normalized: '{sheet_name}' -> '{matched_sheet}'")
                    # Use internal load method if available, or just recursive call with correct name (risky if infinite loop, but we broke loop by using matched_sheet)
                    # Better to use MetadataManager directly to avoid recursion logic issues
                    # Create new manager to be safe
                    mgr_retry = MetadataManager(config_path=file_path)
                    # Access internal _load_sheet logic via public method if possible, or protected
                    df = mgr_retry._load_sheet(matched_sheet)
                    
                    records = df.replace({np.nan: None}).to_dict(orient="records")
                    logger.info(f"Metadata loaded successfully (normalized). Rows: {len(records)}")
                    return records
                else:
                    logger.error(f"Sheet '{sheet_name}' not found. Available: {sheet_names}")
                    # Re-raise original error or new one
                    raise ValueError(f"Sheet '{sheet_name}' not found in {filename}. Available: {sheet_names}")
            
            except Exception as inner_error:
                logger.error(f"Failed to recover from sheet error: {inner_error}", exc_info=True)
                raise ValueError(f"Sheet '{sheet_name}' not found or invalid.")
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}", exc_info=True)
            raise

    def save_configuration(self, filename: str, data: List[Dict[str, Any]], sheet_name: str = 'threshold') -> Dict[str, Any]:
        """
        Saves configuration to Excel after validation and backup.
        Uses atomic file swap logic.
        """
        source_path = self.config_dir / filename
        logger.info(f"Saving configuration to: {source_path.absolute()}, sheet: {sheet_name}, rows: {len(data)}")
        
        # 1. Validation
        if sheet_name == 'threshold':
            logger.info("Validating threshold data...")
            for idx, row in enumerate(data):
                if not self.validate_row(row):
                    error_msg = f"Validation failed at row {idx + 1} for {row.get('Exc Type')}: Logic violation (L1/L2/L3)."
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            logger.info("Validation passed.")

        # 2. Backup
        backup_path = None
        try:
            backup_path = self.create_backup(filename)
        except Exception as e:
            error_msg = f"Backup failed: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

        # 3. Write to Excel (Atomic Swap)
        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx", dir=self.config_dir)
        os.close(fd)
        logger.info(f"Created temp file: {temp_path}")
        
        try:
            # Copy original to temp first to preserve other sheets
            if source_path.exists():
                shutil.copy2(source_path, temp_path)
                logger.info("Copied original file to temp location")
            
            df = pd.DataFrame(data)
            
            with pd.ExcelWriter(temp_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            logger.info(f"Wrote data to sheet '{sheet_name}' in temp file")
                
            # 4. Atomic Replace with Retry Logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    os.replace(temp_path, source_path)
                    logger.info(f"Successfully replaced original file (attempt {attempt + 1})")
                    break # Success
                except (PermissionError, OSError) as e:
                    logger.warning(f"Replace attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        # Final failure
                        if isinstance(e, PermissionError):
                            error_msg = "File is locked. Please close Excel and try again."
                            logger.error(error_msg)
                            raise RuntimeError(error_msg)
                        error_msg = f"OS Error during file save: {e}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
                    
                    # Wait before retry
                    sleep_time = 0.5 * (attempt + 1)
                    logger.info(f"Waiting {sleep_time}s before retry...")
                    time.sleep(sleep_time) # 0.5s, 1.0s, 1.5s
            
        except Exception as e:
            logger.error(f"Exception during file save: {e}", exc_info=True)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info("Cleaned up temp file")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_err}")
            
            # Re-raise nicely formatted error
            if "File is locked" in str(e):
                raise e
            raise RuntimeError(f"Failed to save Excel file: {e}")

        logger.info(f"Configuration saved successfully. Backup: {backup_path}")
        return {"status": "success", "backup": backup_path}
