"""Tests for calculation API routes - Task 6 TDD"""
import pytest
import io
import pandas as pd
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app

client = TestClient(app)


def _make_excel_bytes():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        pd.DataFrame({
            'Run Date': ['2026-01-01', '2026-02-01'],
            'ID': ['W001', 'W002'],
            'Tension Length': ['H02', 'H02'],
            'FromM': [1000.0, 1000.0],
            'ToM': [1100.0, 1100.0],
            'MaxValue': [10.5, 10.3],
            'Level': ['L2', 'L2'],
            'ACTION': [None, None],
        }).to_excel(writer, sheet_name='Wire Wear', index=False)
        pd.DataFrame({
            'task_run_date': ['2026-01-01', '2026-01-01', '2026-02-01', '2026-02-01'],
            'Tension Length': ['H02', 'H02', 'H02', 'H02'],
            'Chainage': [1000.0, 1050.0, 1000.0, 1050.0],
            'wear_min': [10.5, 10.3, 10.1, 9.9],
            'Track Type': ['Tangent', 'Tangent', 'Tangent', 'Tangent'],
            'Overlap': [None, None, None, None],
        }).to_excel(writer, sheet_name='ChartData', index=False)
    return buf.getvalue()


# --- Health -------------------------------------------------------------------

def test_health_endpoint():
    resp = client.get('/api/calculation/health')
    assert resp.status_code == 200
    assert resp.json() == {'status': 'ok'}


# --- Upload -------------------------------------------------------------------

def test_upload_valid_file_returns_200():
    data = _make_excel_bytes()
    resp = client.post(
        '/api/calculation/upload',
        files=[('files', ('test.xlsx', data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))],
    )
    assert resp.status_code == 200

def test_upload_response_has_wear_results():
    data = _make_excel_bytes()
    resp = client.post(
        '/api/calculation/upload',
        files=[('files', ('test.xlsx', data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))],
    )
    body = resp.json()
    assert 'wear_results' in body
    assert isinstance(body['wear_results'], list)
    assert len(body['wear_results']) > 0

def test_upload_response_has_trend_results():
    data = _make_excel_bytes()
    resp = client.post(
        '/api/calculation/upload',
        files=[('files', ('test.xlsx', data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))],
    )
    body = resp.json()
    assert 'trend_results' in body
    assert isinstance(body['trend_results'], list)

def test_upload_wear_result_fields():
    data = _make_excel_bytes()
    resp = client.post(
        '/api/calculation/upload',
        files=[('files', ('test.xlsx', data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))],
    )
    wr = resp.json()['wear_results'][0]
    for field in ('tension_length', 'from_m', 'to_m', 'avg_wear_min', 'sd', 'wear_percentage', 'dates', 'record_points'):
        assert field in wr, f"Missing field: {field}"

def test_upload_trend_result_fields():
    data = _make_excel_bytes()
    resp = client.post(
        '/api/calculation/upload',
        files=[('files', ('test.xlsx', data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))],
    )
    body = resp.json()
    if body['trend_results']:
        tr = body['trend_results'][0]
        for field in ('tension_length', 'from_m', 'to_m', 'dates', 'record_points', 'trend_points', 'trend_next', 'logic_1', 'logic_2', 'recommendation'):
            assert field in tr, f"Missing field: {field}"

def test_upload_multiple_files():
    data = _make_excel_bytes()
    resp = client.post(
        '/api/calculation/upload',
        files=[
            ('files', ('test1.xlsx', data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
            ('files', ('test2.xlsx', data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
        ],
    )
    assert resp.status_code == 200

def test_upload_no_files_returns_422():
    resp = client.post('/api/calculation/upload')
    assert resp.status_code == 422
