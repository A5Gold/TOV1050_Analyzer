import sys
import os
import pandas as pd
import io

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app.core.exporter import ExcelExporter

def test_reorder_columns():
    print("Testing _reorder_columns...")
    df = pd.DataFrame({
        'id': [1],
        'extra_col': ['ignore'],
        'FromM': [100]
    })
    
    expected_cols = ['id', 'FromM', 'ToM']
    result = ExcelExporter._reorder_columns(df, expected_cols)
    
    assert list(result.columns) == expected_cols
    assert 'extra_col' not in result.columns
    assert 'ToM' in result.columns
    print("PASS")

def test_export_report():
    print("Testing export_report...")
    data = {
        'Height': [
            {'id': 1, 'FromM': 10, 'ToM': 20, 'maxValue': 5.5, 'level': 'L1'}
        ]
    }
    
    output = ExcelExporter.export_report(data)
    assert isinstance(output, io.BytesIO)
    
    # Read back to verify
    df = pd.read_excel(output, sheet_name='Summary')
    # Phase 10.10-F: Columns are now renamed to display headers
    expected_cols = [ExcelExporter.REPORT_HEADERS.get(c, c) for c in ExcelExporter.REPORT_COLUMNS]
    assert list(df.columns) == expected_cols
    print("PASS")

def test_export_history_compare():
    print("Testing export_history_compare...")
    df = pd.DataFrame({
        'id': [1],
        'FromM': [100],
        'ToM': [200],
        'length': [100],
        'exception type': ['Height'],
        'maxValue': [5.1],
        'maxLocation': [150],
        'Landmark': ['Pole 1'],
        'Tension Length': ['TL1'],
        'Track Type': ['Main'],
        'level': ['L2']
    })
    
    output = ExcelExporter.export_history_compare(df)
    assert isinstance(output, io.BytesIO)
    
    # Read back - reading MultiIndex header in pandas is tricky with read_excel defaults
    # header=[0,1] tells pandas to read first two rows as header
    df_read = pd.read_excel(output, header=[0, 1])
    
    # Check top level columns
    top_level = df_read.columns.get_level_values(0).unique()
    print("Columns:", df_read.columns)
    print("Data:", df_read)
    assert 'EXCEPTION' in top_level
    assert 'INITIAL CHECK' in top_level
    
    # Check data mapping
    # Note: read_excel with MultiIndex headers often results in an empty first row or shifted data depending on engine
    # We check the last row which should have our data
    val = df_read[('EXCEPTION', 'ID')].iloc[-1]
    assert val == 1
    
    print("PASS")

# =============================================================================
# Phase 10.10 - Bug 2: Catenary Report Column Order (TDD)
# =============================================================================

def test_catenary_report_columns():
    """Catenary Report should include computed columns in correct order."""
    # Simulate a DataFrame as produced by analyze() with pre-computed columns
    df = pd.DataFrame({
        'Chainage': [100050.0, 100060.0],
        'height1': [5200.0, 5100.0],
        'height2': [5210.0, 5090.0],
        'height3': [5190.0, 5110.0],
        'height4': [5205.0, 5095.0],
        'stagger1': [10.0, 20.0],
        'stagger2': [11.0, 21.0],
        'stagger3': [12.0, 22.0],
        'stagger4': [13.0, 23.0],
        'wear1': [8.0, 7.0],
        'wear2': [9.0, 8.0],
        'wear3': [10.0, 9.0],
        'wear4': [11.0, 10.0],
        'Track Type': ['Tangent', 'Curve'],
        'Overlap': [None, 'Y'],
        'Tension Length': [None, 'TL1'],
        'Landmark': [None, 'Pole 1'],
        'Class': ['both', 'both'],
        # Pre-computed by analyze()
        'height_min': [5190.0, 5090.0],
        'height_max': [5210.0, 5110.0],
        'wear_min': [8.0, 7.0],
        'wear_max': [11.0, 10.0],
        'stg_max': [13.0, 23.0],
        'stg_min': [10.0, 20.0],
    })

    output = ExcelExporter.export_catenary_report(df)
    assert isinstance(output, io.BytesIO), "Should return BytesIO"

    # Read back to verify column order
    df_read = pd.read_csv(output)

    # Verify key columns exist
    assert 'Chainage' in df_read.columns
    assert 'height_min' in df_read.columns
    assert 'height_max' in df_read.columns
    assert 'wear_min' in df_read.columns
    assert 'wear_max' in df_read.columns
    assert 'stg_max' in df_read.columns
    assert 'stg_min' in df_read.columns

    # Verify column order: Chainage comes first in the raw data section,
    # then height, stagger, wear, metadata, computed
    columns = list(df_read.columns)
    assert columns.index('Chainage') < columns.index('height1')
    assert columns.index('height4') < columns.index('stagger1')
    assert columns.index('stagger4') < columns.index('wear1')
    assert columns.index('wear4') < columns.index('Track Type')
    assert columns.index('Class') < columns.index('height_min')
    assert columns.index('height_max') < columns.index('wear_min')
    assert columns.index('wear_max') < columns.index('stg_max')


if __name__ == "__main__":
    try:
        test_reorder_columns()
        test_export_report()
        test_export_history_compare()
        test_catenary_report_columns()
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

