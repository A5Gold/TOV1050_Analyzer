"""
Unit tests for conditional file naming logic.

Tests the generate_filename() function in analysis.py to ensure correct
behavior for both default (Track + Section) and custom (Task Number + Station Range)
naming modes.
"""

import pytest
from app.api.endpoints.analysis import generate_filename


class TestConditionalNaming:
    """Test suite for conditional file naming logic."""
    
    # ============================================================================
    # Default Mode Tests (Condition A: Any optional field is missing)
    # ============================================================================
    
    def test_default_mode_raw_data(self):
        """Test default mode for raw data export."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="raw"
        )
        assert result == "20260127_EAL_UP_Mainline_Catenary_Report.csv"
    
    def test_default_mode_exception_report(self):
        """Test default mode for exception report export."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report"
        )
        assert result == "20260127_EAL_UP_Mainline_Exception_Report.xlsx"
    
    def test_default_mode_repeated_report(self):
        """Test default mode for repeated exception report."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="repeated",
            file_count=3
        )
        assert result == "20260127_EAL_UP_Mainline_Exception_Report_3_Repeated.xlsx"
    
    def test_default_mode_tml_line(self):
        """Test default mode with TML line."""
        result = generate_filename(
            date_str="20260128",
            line="TML",
            track="DN",
            section="Mainline",
            file_type="report"
        )
        assert result == "20260128_TML_DN_Mainline_Exception_Report.xlsx"
    
    def test_default_mode_lmc_section(self):
        """Test default mode with LMC section."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="LMC",
            file_type="raw"
        )
        assert result == "20260127_EAL_UP_LMC_Catenary_Report.csv"
    
    # ============================================================================
    # Custom Mode Tests (Condition B: All optional fields provided)
    # ============================================================================
    
    def test_custom_mode_all_fields_provided(self):
        """Test custom mode when all optional fields are provided."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report",
            task_no="U1",
            station_start="HUH",
            station_end="RAC"
        )
        assert result == "20260127_EAL_U1_HUH-RAC_Exception_Report.xlsx"
    
    def test_custom_mode_raw_data(self):
        """Test custom mode for raw data export."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="raw",
            task_no="D3",
            station_start="LOW",
            station_end="NAC"
        )
        assert result == "20260127_EAL_D3_LOW-NAC_Catenary_Report.csv"
    
    def test_custom_mode_repeated_report(self):
        """Test custom mode for repeated exception report."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="repeated",
            file_count=5,
            task_no="S1",
            station_start="SHA",
            station_end="HUH"
        )
        assert result == "20260127_EAL_S1_SHA-HUH_Exception_Report_5_Repeated.xlsx"
    
    def test_custom_mode_uppercase_enforcement(self):
        """Test that station codes are automatically converted to uppercase."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report",
            task_no="d3",
            station_start="low",
            station_end="nac"
        )
        # Station codes should be uppercase
        assert result == "20260127_EAL_d3_LOW-NAC_Exception_Report.xlsx"
    
    def test_custom_mode_various_task_numbers(self):
        """Test custom mode with various task number formats."""
        test_cases = [
            ("U1", "U1"),
            ("D3A", "D3A"),
            ("S1", "S1"),
            ("U1A", "U1A"),
        ]
        
        for task_no, expected_task in test_cases:
            result = generate_filename(
                date_str="20260127",
                line="EAL",
                track="UP",
                section="Mainline",
                file_type="report",
                task_no=task_no,
                station_start="HUH",
                station_end="RAC"
            )
            assert expected_task in result
            assert "HUH-RAC" in result
    
    # ============================================================================
    # Fallback Tests (Partial optional fields - should use default mode)
    # ============================================================================
    
    def test_fallback_missing_task_no(self):
        """Test fallback to default mode when task_no is missing."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report",
            task_no=None,
            station_start="HUH",
            station_end="RAC"
        )
        # Should use default mode (Track + Section)
        assert result == "20260127_EAL_UP_Mainline_Exception_Report.xlsx"
    
    def test_fallback_missing_station_start(self):
        """Test fallback to default mode when station_start is missing."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report",
            task_no="U1",
            station_start=None,
            station_end="RAC"
        )
        # Should use default mode
        assert result == "20260127_EAL_UP_Mainline_Exception_Report.xlsx"
    
    def test_fallback_missing_station_end(self):
        """Test fallback to default mode when station_end is missing."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report",
            task_no="U1",
            station_start="HUH",
            station_end=None
        )
        # Should use default mode
        assert result == "20260127_EAL_UP_Mainline_Exception_Report.xlsx"
    
    def test_fallback_all_optional_fields_none(self):
        """Test fallback when all optional fields are explicitly None."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report",
            task_no=None,
            station_start=None,
            station_end=None
        )
        # Should use default mode
        assert result == "20260127_EAL_UP_Mainline_Exception_Report.xlsx"
    
    def test_fallback_empty_string_task_no(self):
        """Test fallback when task_no is empty string (should be treated as None)."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report",
            task_no="",
            station_start="HUH",
            station_end="RAC"
        )
        # Empty string is falsy, should use default mode
        assert result == "20260127_EAL_UP_Mainline_Exception_Report.xlsx"
    
    # ============================================================================
    # Edge Cases and Error Handling
    # ============================================================================
    
    def test_repeated_report_without_file_count_raises_error(self):
        """Test that repeated report type requires file_count parameter."""
        with pytest.raises(ValueError, match="file_count is required"):
            generate_filename(
                date_str="20260127",
                line="EAL",
                track="UP",
                section="Mainline",
                file_type="repeated"
                # Missing file_count
            )
    
    def test_invalid_file_type_raises_error(self):
        """Test that invalid file type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown file_type"):
            generate_filename(
                date_str="20260127",
                line="EAL",
                track="UP",
                section="Mainline",
                file_type="invalid_type"
            )
    
    def test_special_characters_in_station_codes(self):
        """Test handling of special characters in station codes."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report",
            task_no="U1",
            station_start="HUH-01",
            station_end="RAC-02"
        )
        assert "HUH-01-RAC-02" in result
    
    def test_date_format_consistency(self):
        """Test that various date formats are handled consistently."""
        test_dates = ["20260127", "20251231", "20300101"]
        
        for date in test_dates:
            result = generate_filename(
                date_str=date,
                line="EAL",
                track="UP",
                section="Mainline",
                file_type="report"
            )
            assert result.startswith(date)
    
    def test_line_variations(self):
        """Test that different line codes are handled correctly."""
        lines = ["EAL", "TML", "ISL", "TCL"]
        
        for line in lines:
            result = generate_filename(
                date_str="20260127",
                line=line,
                track="UP",
                section="Mainline",
                file_type="report"
            )
            assert f"_{line}_" in result
    
    # ============================================================================
    # Integration-like Tests (Real-world scenarios)
    # ============================================================================
    
    def test_scenario_typical_analysis_export(self):
        """Test a typical analysis export scenario."""
        # User performs analysis and exports report
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="report"
        )
        assert result == "20260127_EAL_UP_Mainline_Exception_Report.xlsx"
    
    def test_scenario_custom_task_export(self):
        """Test export with custom task and station range."""
        # User specifies custom task and station range
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",  # Will be ignored
            section="Mainline",  # Will be ignored
            file_type="report",
            task_no="U1A",
            station_start="HUH",
            station_end="SHA"
        )
        # Should use custom mode
        assert "U1A" in result
        assert "HUH-SHA" in result
        assert "UP" not in result  # Track not used
        assert "Mainline" not in result  # Section not used (except in "Mainline" could be substring)
    
    def test_scenario_repeated_comparison_export(self):
        """Test repeated exception comparison export."""
        result = generate_filename(
            date_str="20260127",
            line="EAL",
            track="UP",
            section="Mainline",
            file_type="repeated",
            file_count=3
        )
        assert "Exception_Report_3_Repeated.xlsx" in result
    
    def test_scenario_raw_data_custom_mode(self):
        """Test raw data export with custom naming."""
        result = generate_filename(
            date_str="20260128",
            line="TML",
            track="DN",
            section="Mainline",
            file_type="raw",
            task_no="D1",
            station_start="TUM",
            station_end="SUN"
        )
        assert result == "20260128_TML_D1_TUM-SUN_Catenary_Report.csv"
