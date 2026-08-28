import pytest
import pandas as pd
import numpy as np
from app.core.analyzers import ExceptionDetector
from unittest.mock import MagicMock
from app.core.metadata import MetadataManager

class TestExceptionDetection:
    """Tests for Story 1.4: Exception Detection Engine"""

    @pytest.fixture
    def mock_thresholds(self):
        return pd.DataFrame([
            # Low Height (Min Mode): L1 < L2. Gatekeeper max(L1, L2).
            # L1=4500 (Severe), L2=4600 (Warning).
            {'Exc Type': 'Low Height', 'Class': 'Mainline', 'Track Type': 'both', 'min': 4000, 'max': 5000, 'Low Height L1': 4500, 'Low Height L2': 4600},
            
            # High Height (Max Mode): L1 > L2. Gatekeeper min(L1, L2).
            # L1=5500 (Severe), L2=5400 (Warning).
            {'Exc Type': 'High Height', 'Class': 'Mainline', 'Track Type': 'both', 'min': 5000, 'max': 6000, 'High Height L1': 5500, 'High Height L2': 5400},
            
            # Stagger Left (Abs Mode, Tangent): L1 > L2 > L3
            {'Exc Type': 'Stagger Left', 'Class': 'Mainline', 'Track Type': 'Tangent', 'min': 300, 'max': 600, 'Stagger L1': 500, 'Stagger L2': 400, 'Stagger L3': 350},
            # Stagger Left (Abs Mode, Curve): L1 > L2 > L3 (Different values)
            {'Exc Type': 'Stagger Left', 'Class': 'Mainline', 'Track Type': 'Curve', 'min': 350, 'max': 650, 'Stagger L1': 550, 'Stagger L2': 450, 'Stagger L3': 400},
             # Stagger Right (Same structure)
            {'Exc Type': 'Stagger Right', 'Class': 'Mainline', 'Track Type': 'Tangent', 'min': 300, 'max': 600, 'Stagger L1': 500, 'Stagger L2': 400, 'Stagger L3': 350},
        ])

    @pytest.fixture
    def detector(self, mock_thresholds):
        mm = MagicMock(spec=MetadataManager)
        mm.get_all_thresholds.return_value = mock_thresholds
        
        # Mock boundaries for plotting (not used in detection logic but called)
        mm.get_boundaries_for_plot.return_value = pd.DataFrame()
        mm.get_exception_boundaries.return_value = pd.DataFrame() 
        mm.get_track_type_intervals.return_value = pd.DataFrame()
        mm.get_overlap_intervals.return_value = pd.DataFrame()
        mm.get_landmark_intervals.return_value = pd.DataFrame()
        
        return ExceptionDetector(mm)

    def test_low_height_detection(self, detector):
        """Test AC1 & AC2 for Low Height (Min Mode)"""
        # Thresholds: L1=4500, L2=4600.
        # Values < 4600 are exceptions.
        # Priority: <= 4500 is L1, <= 4600 is L2.
        
        df = pd.DataFrame({
            'Chainage': [100, 200, 300, 400],
            'height1': [4400, 4550, 4700, 4400],
            'height2': [4400, 4550, 4700, 4400], # min of row
            'Class': ['Mainline'] * 4,
            'Track Type': ['Tangent'] * 4
        })
        
        # Mock map methods
        detector._map_class_info = MagicMock(return_value=df)
        detector._map_track_info = MagicMock(return_value=df)
        
        results, _ = detector.analyze(df, 'EAL', 'Mainline', 'UP', '20250101')
        
        lh_res = results['Low Height']
        
        # 4400 (L1), 4550 (L2), 4700 (OK), 4400 (L1).
        # Group 1: 100-200. Min 4400. L1.
        # Group 2: 400. Min 4400. L1.
        
        assert len(lh_res) == 2
        
        exc1 = lh_res.iloc[0]
        assert exc1['maxValue'] == 4400
        assert exc1['level'] == 'L1'
        
    def test_high_height_detection(self, detector):
        """Test AC1 & AC2 for High Height (Max Mode)"""
        # Thresholds: L1=5500, L2=5400.
        # > 5400 is exception.
        # >= 5500 is L1.
        
        df = pd.DataFrame({
            'Chainage': [100, 200],
            'height1': [5600, 5450],
            'height2': [5600, 5450],
            'Class': ['Mainline'] * 2,
            'Track Type': ['Tangent'] * 2
        })
        
        detector._map_class_info = MagicMock(return_value=df)
        detector._map_track_info = MagicMock(return_value=df)
        
        results, _ = detector.analyze(df, 'EAL', 'Mainline', 'UP', '20250101')
        hh = results['High Height']
        
        # Group 1: 100-200. Max 5600. L1.
        assert len(hh) == 1
        assert hh.iloc[0]['level'] == 'L1'
        assert hh.iloc[0]['maxValue'] == 5600

    def test_wire_wear_l1_only_uses_l1_gatekeeper(self):
        """Wire Wear with only L1 active should detect only values at/below L1."""
        detector = ExceptionDetector(None)
        thresholds = pd.DataFrame([
            {'Exc Type': 'Wire Wear', 'Class': 'Mainline', 'Track Type': 'both',
             'Wire Wear L1': 9.1, 'Wire Wear L2': ''},
        ])
        df = pd.DataFrame({
            'Chainage': [100, 200, 300],
            'wear1': [9.0, 9.1, 9.2],
            'wear2': [9.0, 9.1, 9.2],
            'wear3': [9.0, 9.1, 9.2],
            'wear4': [9.0, 9.1, 9.2],
            'wear_min': [9.0, 9.1, 9.2],
            'Class': ['Mainline'] * 3,
            'Track Type': ['Tangent'] * 3,
        })

        result = detector._detect_scalar(
            df, 'wear', 'Wire Wear', thresholds, 'min',
            '20250101', 'UP', 'EAL', 'Mainline'
        )

        assert len(result) == 1
        assert result.iloc[0]['FromM'] == 100
        assert result.iloc[0]['ToM'] == 200
        assert result.iloc[0]['level'] == 'L1'
        assert result.iloc[0]['Threshold Value'] == 9.1

    def test_wire_wear_l1_only_without_l2_column_uses_l1_gatekeeper(self):
        """Wire Wear with no L2 column should still detect only L1 exceptions."""
        detector = ExceptionDetector(None)
        thresholds = pd.DataFrame([
            {'Exc Type': 'Wire Wear', 'Class': 'Mainline', 'Track Type': 'both',
             'Wire Wear L1': 9.1},
        ])
        df = pd.DataFrame({
            'Chainage': [100, 200, 300],
            'wear1': [9.0, 9.1, 9.2],
            'wear2': [9.0, 9.1, 9.2],
            'wear3': [9.0, 9.1, 9.2],
            'wear4': [9.0, 9.1, 9.2],
            'wear_min': [9.0, 9.1, 9.2],
            'Class': ['Mainline'] * 3,
            'Track Type': ['Tangent'] * 3,
        })

        result = detector._detect_scalar(
            df, 'wear', 'Wire Wear', thresholds, 'min',
            '20250101', 'UP', 'EAL', 'Mainline'
        )

        assert len(result) == 1
        assert result.iloc[0]['FromM'] == 100
        assert result.iloc[0]['ToM'] == 200
        assert result.iloc[0]['level'] == 'L1'
        assert result.iloc[0]['Threshold Value'] == 9.1

    def test_wire_wear_l1_l2_still_classifies_between_l1_and_l2_as_l2(self):
        """Wire Wear with L1/L2 active should preserve existing L2 behavior."""
        detector = ExceptionDetector(None)
        thresholds = pd.DataFrame([
            {'Exc Type': 'Wire Wear', 'Class': 'Mainline', 'Track Type': 'both',
             'Wire Wear L1': 9.1, 'Wire Wear L2': 10.2},
        ])
        df = pd.DataFrame({
            'Chainage': [100],
            'wear1': [9.6],
            'wear2': [9.6],
            'wear3': [9.6],
            'wear4': [9.6],
            'wear_min': [9.6],
            'Class': ['Mainline'],
            'Track Type': ['Tangent'],
        })

        result = detector._detect_scalar(
            df, 'wear', 'Wire Wear', thresholds, 'min',
            '20250101', 'UP', 'EAL', 'Mainline'
        )

        assert len(result) == 1
        assert result.iloc[0]['level'] == 'L2'
        assert result.iloc[0]['Threshold Value'] == 10.2

    def test_stagger_detection_levels(self, detector):
        """Test AC1: Stagger L1/L2/L3 Priority"""
        # Tangent: L3=350, L2=400, L1=500.
        df = pd.DataFrame({
            'Chainage': [100, 300, 500], # Spaced out
            'stagger1': [360, 410, 510], # L3, L2, L1
            'stagger2': [0,0,0], 'stagger3':[0,0,0], 'stagger4':[0,0,0],
            'Class': ['Mainline'] * 3,
            'Track Type': ['Tangent'] * 3
        })
        # Safe rows to break groups
        df_safe = pd.DataFrame({
            'Chainage': [200, 400],
            'stagger1': [100, 100],
            'stagger2': [0,0], 'stagger3':[0,0], 'stagger4':[0,0],
            'Class': ['Mainline']*2, 'Track Type': ['Tangent']*2
        })
        df_final = pd.concat([df, df_safe]).sort_values('Chainage').reset_index(drop=True)
        
        detector._map_class_info = MagicMock(return_value=df_final)
        detector._map_track_info = MagicMock(return_value=df_final)
        
        results, _ = detector.analyze(df_final, 'EAL', 'Mainline', 'UP', '20250101')
        sl = results['Stagger Left']
        
        assert len(sl) == 3
        sl = sl.sort_values('FromM')
        
        # 360 -> L3
        assert sl.iloc[0]['level'] == 'L3'
        # 410 -> L2
        assert sl.iloc[1]['level'] == 'L2'
        # 510 -> L1
        assert sl.iloc[2]['level'] == 'L1'

    def test_stagger_detection_curve_vs_tangent(self, detector):
        """Test AC1: Curve thresholds vs Tangent thresholds"""
        # Tangent: L1=500.
        # Curve: L1=550.
        
        # Value 520.
        # Tangent -> L1 (520 > 500)
        # Curve -> Not L1 (520 < 550) (Assume L2 is 450, so L2)
        
        df = pd.DataFrame({
            'Chainage': [100, 300],
            'stagger1': [520, 520],
            'stagger2': [0,0], 'stagger3':[0,0], 'stagger4':[0,0],
            'Class': ['Mainline'] * 2,
            'Track Type': ['Tangent', 'Curve']
        })
        
        detector._map_class_info = MagicMock(return_value=df)
        detector._map_track_info = MagicMock(return_value=df)
        
        results, _ = detector.analyze(df, 'EAL', 'Mainline', 'UP', '20250101')
        sl = results['Stagger Left']
        
        # Assuming they are treated as separate groups due to non-consecutive chainage (100, 300)
        # But analyze logic doesn't care about chainage gap size, only index continuity.
        # Indices are 0 and 1. They are consecutive in DataFrame.
        # However, check_stagger uses mask changes.
        # 100: Tangent, 520. Mask=True.
        # 300: Curve, 520. Mask=True.
        # They are consecutive Trues. 
        # _group_consecutive will group them together.
        # Group: 100-300. Max=520.
        # Track Type: mode(). If tie, might pick Tangent or Curve.
        
        # To strictly test threshold application logic without grouping artifacts, 
        # I should test them separately or ensure they don't group.
        # I will test them in separate calls or separate groups.
        
        # Run 1: Tangent
        df_tan = df.iloc[[0]].copy()
        detector._map_class_info = MagicMock(return_value=df_tan)
        detector._map_track_info = MagicMock(return_value=df_tan)
        res_tan, _ = detector.analyze(df_tan, 'EAL', 'Mainline', 'UP', '20250101')
        assert res_tan['Stagger Left'].iloc[0]['level'] == 'L1'
        
        # Run 2: Curve
        df_cur = df.iloc[[1]].copy()
        detector._map_class_info = MagicMock(return_value=df_cur)
        detector._map_track_info = MagicMock(return_value=df_cur)
        res_cur, _ = detector.analyze(df_cur, 'EAL', 'Mainline', 'UP', '20250101')
        assert res_cur['Stagger Left'].iloc[0]['level'] == 'L2'






