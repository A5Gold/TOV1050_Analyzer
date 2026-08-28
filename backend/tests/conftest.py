import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from pathlib import Path
from io import StringIO
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.metadata import MetadataManager

@pytest.fixture
def mock_datac_content():
    """Sample .datac CSV content with semi-colon delimiter"""
    return """KM;LOCATION;LINE;TRACK;STG1c;STG2c;STG3c;STG4c;RWH1mm;RWH2mm;RWH3mm;RWH4mm;WHGT1c;WHGT2c;WHGT3c;WHGT4c
100;100.50;EAL;UP;10;11;12;13;5;6;7;8;5300;5305;5310;5315
100;100.55;EAL;UP;15;16;17;18;6;7;8;9;5301;5306;5311;5316
100;101.00;EAL;UP;20;21;22;23;7;8;9;10;5302;5307;5312;5317
"""

@pytest.fixture
def mock_metadata_manager():
    """Mock MetadataManager with preset DataFrames"""
    mm = MagicMock(spec=MetadataManager)
    
    # Mock boundaries
    boundaries = pd.DataFrame({
        'Class': ['Mainline', 'Siding'],
        'UP Track FromM': [100000.0, 100200.0],
        'UP Track ToM': [100200.0, 100400.0],
        'DN Track FromM': [100000.0, 100200.0],
        'DN Track ToM': [100200.0, 100400.0],
        'Line': ['EAL', 'EAL']
    })
    mm.get_exception_boundaries.return_value = pd.DataFrame({
        'Class': ['Mainline']
    }, index=pd.IntervalIndex.from_arrays([100000.0], [100200.0]))

    # Mock Track Types
    track_types = pd.DataFrame({
        'Track Type': ['Tangent', 'Curve'],
        'Track Type FromM': [100000.0, 100100.0],
        'Track Type ToM': [100100.0, 100200.0]
    })
    mm.get_track_type_intervals.return_value = track_types[['Track Type']].set_index(
        pd.IntervalIndex.from_arrays(track_types['Track Type FromM'], track_types['Track Type ToM'])
    )

    # Mock Thresholds
    thresholds = pd.DataFrame([
        {'Exc Type': 'Low Height', 'Class': 'Mainline', 'Track Type': 'both', 'max': 4600, 'min': 0, 'Exc Type L1': 4500, 'Exc Type L2': 4550},
        {'Exc Type': 'High Height', 'Class': 'Mainline', 'Track Type': 'both', 'max': 6000, 'min': 5800, 'Exc Type L1': 5900, 'Exc Type L2': 5850},
    ])
    mm.get_all_thresholds.return_value = thresholds
    
    mm.get_boundaries_for_plot.return_value = pd.DataFrame()
    mm.get_overlap_intervals.return_value = pd.DataFrame()
    mm.get_landmark_intervals.return_value = pd.DataFrame()

    return mm
