"""Read-only verification of the newly downloaded dev reports."""
from pathlib import Path
from collections import Counter
import json
import sys
import hashlib
import urllib.request
import urllib.parse
import openpyxl

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.report_context import metadata_values

evidence = json.loads((OUT / 'validation.json').read_text(encoding='utf-8'))
assert evidence['status'] == 'passed', evidence.get('error')
results = []
for record, expected_chart, expected_summary in zip(evidence['reports'], (83963, 83244), (289, 330)):
    file = Path(record['report'])
    book = openpyxl.load_workbook(file, read_only=True, data_only=True)
    try:
        metadata = metadata_values(book)
        rows = iter(book['Summary'].values)
        headers = list(next(rows))
        data = [row for row in rows if any(x is not None for x in row)]
        assert len(data) == expected_summary, (file.name, len(data))
        enrichment = {}
        for field in ('Overlap', 'Tension Length', 'Landmark'):
            assert field in headers, (file.name, field)
            index = headers.index(field)
            enrichment[field] = dict(Counter(str(row[index]) for row in data))
        chart_rows = sum(1 for row in book['ChartData'].values) - 1
        assert chart_rows == expected_chart, (file.name, chart_rows)
        assert metadata['export_data_mode'] == 'chainage_median'
        assert metadata['detection_data_mode'] == 'cleaned_raw'
        assert int(metadata['chart_row_count']) == chart_rows
        assert int(metadata['raw_row_count']) > chart_rows
        item = {'file': str(file), 'chart_rows': chart_rows, 'summary_rows': len(data),
                'metadata': metadata, 'enrichment': enrichment,
                'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
        results.append(item)
        print(file.name, chart_rows, len(data), enrichment, flush=True)
    finally:
        book.close()
comparison = Path(evidence['history']['report'])
job = evidence['history']['job']
url = 'http://127.0.0.1:8000/api/jobs/' + job['job_id'] + '/result?' + urllib.parse.urlencode({'client_session_id': job['client_session_id']})
with urllib.request.urlopen(url, timeout=30) as response:
    comparison_result = json.load(response)
expected_ids = {str(row['id']) for group in comparison_result['repeated'].values() for row in group}
book = openpyxl.load_workbook(comparison, read_only=True, data_only=True)
try:
    sheets = {}
    cells = set()
    for sheet in book:
        rows = list(sheet.values)
        sheets[sheet.title] = {'rows': len(rows), 'headers': rows[0] if rows else []}
        cells.update(str(cell) for row in rows for cell in row if cell is not None)
    assert evidence['history']['stats']['total'] == 15, evidence['history']['stats']
    assert len(expected_ids) == 15 and expected_ids <= cells, (expected_ids - cells)
    assert comparison.stat().st_size > 0
finally:
    book.close()
summary = {'status': 'passed', 'exception_reports': results,
           'comparison_report': str(comparison), 'comparison_sheets': sheets,
           'history_stats': evidence['history']['stats'],
           'comparison_ids_verified': len(expected_ids),
           'sources_and_config_unchanged': evidence['sources_and_config_unchanged'],
           'renderer_errors': [item for item in evidence['errors'] if not item.startswith('Screenshot:')],
           'screenshot_warnings': [item for item in evidence['errors'] if item.startswith('Screenshot:')],
           'failed_api_requests': evidence['requests_failed']}
(OUT / 'readback.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print(json.dumps({'status': summary['status'], 'history_stats': summary['history_stats'], 'comparison_sheets': sheets}, ensure_ascii=False))
