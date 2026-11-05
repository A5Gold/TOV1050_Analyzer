"""Read supplied real inputs; write development evidence only under outputs/."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / 'outputs'):
        raise ValueError('Validation artifacts must stay inside outputs/')
    output.mkdir(parents=True, exist_ok=False)
    os.environ['DB_PATH'] = str(output / 'isolated-validation.db')
    sys.path.insert(0, str(ROOT / 'backend'))
    from fastapi import HTTPException
    from openpyxl import load_workbook
    from app.api.endpoints import analysis as api
    from app.core.tov1050_report_export import export_tov1050_report

    cases = [
        ('TWL/20260907_TWL_UT.csv', 'TWL', 'UT', '20260907', 'CEN', 'TSW'),
        ('TWL/20260630_TWL_UT.csv', 'TWL', 'UT', '20260630', 'CEN', 'TSW'),
        ('TML/TML_D1_260410.datac', 'TML', 'DN', '20260410', '', ''),
    ]
    results = []
    for index, (name, line, track, date, start, end) in enumerate(cases):
        path = ROOT / '00 Reference Document/Raw data' / name
        record = dict(file=str(path), entry='direct _analyze_sync (not Electron/HTTP)', source_sha256=sha(path))
        started = time.perf_counter()
        print(f'START {name}', flush=True)
        try:
            request = api.AnalyzeRequest(file_path=str(path), line=line, section='Mainline', track=track,
                date_str=date, task_no='', station_start=start, station_end=end, client_session_id=f'followup-real-{index}')
            response = api._analyze_sync(request)
            state = api.ANALYSIS_SESSIONS[request.client_session_id]
            record.update(status='success', exception_counts={k: len(v) for k, v in response['exceptions'].items()},
                          aggregation=response['aggregation_metadata'], chart_resolution=response['chart_resolution'])
            record['canonical_detection_sha256'] = hashlib.sha256(json.dumps({
                kind: [{k: v for k, v in row.items() if k not in {'metadata_enrichment', 'Tension Length', 'Overlap', 'Landmark'}}
                       for row in rows] for kind, rows in response['exceptions'].items()
            }, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
            if line == 'TWL':
                report = output / f'{date}_TWL_UT_DevelopmentValidation.xlsx'
                export_tov1050_report(state['results'], state['analysis_df'],
                    metadata=dict(analysis_revision=state['analysis_revision'],
                                  metadata_capabilities=json.dumps(response['metadata_capabilities'], ensure_ascii=False),
                                  enrichment_version='tov640-first-nonempty-v1',
                                  **state['aggregation_metadata']), output_path=report)
                workbook = load_workbook(report, read_only=True)
                meta = dict(list(workbook['_Metadata'].values)[1:])
                saved_capabilities = json.loads(meta['metadata_capabilities'])
                assert saved_capabilities['workbook_sha256'] == response['metadata_capabilities']['workbook_sha256']
                summary = iter(workbook['Summary'].values)
                headers = next(summary)
                assert all(column in headers for column in ['Overlap', 'Tension Length', 'Landmark'])
                record['report'] = str(report)
                record['report_summary_rows'] = sum(1 for _ in summary)
                record['report_sheets'] = workbook.sheetnames
                workbook.close()
                record['report_sha256'] = sha(report)
            del response, state
        except HTTPException as exc:
            record.update(status='blocked', status_code=exc.status_code, detail=exc.detail)
        finally:
            for state in api.ANALYSIS_SESSIONS.values():
                api._release_chart_cache(state)
            api.ANALYSIS_SESSIONS.clear()
            api.LAST_ANALYSIS_RESULTS = {}
            api.LAST_ANALYSIS_SNAPSHOT = None
            api.LAST_RAW_DF = None
            gc.collect()
        record['elapsed_seconds'] = time.perf_counter() - started
        record['source_unchanged'] = sha(path) == record['source_sha256']
        assert record['source_unchanged']
        results.append(record)
        (output / 'validation.json').write_text(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        print(f"END {name}: {record['status']} ({record['elapsed_seconds']:.1f}s)", flush=True)


if __name__ == '__main__':
    main()
