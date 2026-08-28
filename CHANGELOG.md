# Changelog

All notable changes to the TOV1050 Analyzer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.3] - 2026-02-09

### 🐛 Bug Fixes

- **Issue 1: Missing Columns & Content (P0)**:
  - **Catenary Report**: Expanded `chart_data` to include metadata, computed fields, and Task Run Data.
  - **Exception Table**: Fixed missing `line` and `track` fields.
  - **ComparisonDataGrid**: Fixed metadata passing for `line` and `track`.
  - **Database**: Fixed `saved_at` and `last_updated` timezone display (UTC+8).
- **Issue 2: Duplicate Columns in New Excel Format (P0)**:
  - Fixed "column 'exception type' is not unique" error when importing new format Excel files by normalizing column names before check.

### 🧪 Testing

- Added `backend/tests/test_analysis_compare.py` for new vs old Excel format compatibility.
- Added `backend/tests/test_analysis_chart_data.py` for chart data field completeness.

## [2.0.2] - 2026-01-27

### 🐛 Bug Fixes

- **Portable App Config Path**: Fixed "File Not Found" error for configuration files in portable .exe
  - Updated `get_config_dir()` in analysis.py and metadata.py to locate config relative to executable
  - Config now correctly found at `resources/config/` in packaged apps (not in AppData)
  - Added triple-check logic: Portable → Bundle → Development paths
  - Resolves HTTPException 404 for metadata files in production deployments

### 🔧 Improvements

- **Data Quality Enhancement**: Improved data ingestion with automatic trimming and error signal handling
  - Automatically removes first and last 20 rows (machine setup/teardown phases) to improve analysis accuracy
  - Filters out erroneous 6.56 values in wear columns (known system error code)
  - Added safety check for datasets with less than 40 rows

### 📚 Documentation

- Added comprehensive user manual (DOCX and PPTX formats)
- Added detailed development plans and technical guides
- Enhanced documentation with code logic explanations and test guides
- Added fix-portable-config-path.md with detailed technical explanation

### 🏗️ Build & Deployment

- Configured packaging for Windows portable executable (.exe)
- Setup PyInstaller configuration for backend server bundling
- Integrated Electron builder for desktop application distribution
- Disabled APPDATA config copying for true portable app design

---

## [2.0.1] - 2026-01-26

### 🐛 Bug Fixes

- **DN Track Analysis Timeout**: Fixed "Network Error" when analyzing EAL DN Track Mainline configuration
  - Optimized interval mapping algorithm with vectorized numpy operations
  - Reduced analysis time from 14s to 0.28s for 20,000 rows (50x improvement)
  - Resolved issue caused by 56 overlapping intervals in EAL DN metadata
- **500 Error Handling**: Improved error messages for malformed `.datac` files
  - Now returns 400 status with helpful details when KM or LOCATION columns are missing
  - Added validation for empty DataFrames with clear error messages
  - Fixed HTTPException wrapping that converted 400/404 errors to generic 500 errors

### 🧪 Testing

- Added test coverage for UTF-8 BOM file handling
- Added test for missing KM column scenario
- Added test for empty DataFrame validation
- Added test for missing Chainage error handling
- All 34 tests passing

---

## [2.0.0] - 2026-01-16

### ✨ New Features

- **Exception Generator**: Complete analysis workflow for detecting Height, Stagger, and Wear exceptions from `.datac` files
- **History Compare**: Chain comparison algorithm to identify repeated exceptions across multiple inspection cycles
- **Metadata Editor**: Full-featured editor with undo/redo, validation, and auto-backup
- **Multi-Tab Sessions**: Analyze multiple datasets simultaneously with independent state management
- **Algorithm Tutorial**: Interactive documentation explaining exception detection logic
- **Comparison Charts**: Overlaid waveform visualization with auto-zoom and trace filtering

### 🔧 Improvements

- **File Naming Convention**: Standardized export filenames following `{Date}_{Line}_{Track}_{Section}_*` format
- **Chart X-Axis Anchoring**: Fixed X-axis positioning to always display at chart bottom
- **Export Buttons**: Raw/Report exports now correctly use session parameters
- **UI Enhancements**: Improved layout, colors, dropdowns in Metadata Editor
- **State Management**: Zustand store for persistent session data across view navigation

### 🐛 Bug Fixes

- Fixed file locking issues in metadata service
- Resolved chart overflow and tooltip errors
- Fixed graph zoom and interaction issues
- Corrected track type boundaries in analysis
- Fixed dynamic metadata sheets loading (400 errors)

### 📚 Documentation

- Added comprehensive README with Quick Start guide
- Created User Guide with detailed workflow instructions
- Updated Architecture documentation with Mermaid diagrams
- Added Packaging guide for .exe distribution

### 🏗️ Architecture

- Hybrid Desktop Architecture: Electron + React + FastAPI
- Python sidecar process for heavy data processing
- REST API communication over localhost
- Zustand for frontend state management

---

## [1.0.0] - 2025-10-01

### Initial Release

- Basic exception detection functionality
- Single file analysis
- Excel report export

---

## Legend

- ✨ New Features
- 🔧 Improvements
- 🐛 Bug Fixes
- 📚 Documentation
- 🏗️ Architecture
- ⚠️ Breaking Changes
- 🔒 Security
