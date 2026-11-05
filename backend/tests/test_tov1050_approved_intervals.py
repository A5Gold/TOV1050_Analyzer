import hashlib
import io
import json

import pandas as pd
import pytest
from openpyxl import load_workbook

from app.core.tov1050_approved_intervals import ApprovedIntervalProvider, VERSION
from app.core.tov1050_capabilities import MetadataCapabilityError


def release(tmp_path, *, complete=False):
    workbook = tmp_path / 'test.xlsx'
    workbook.write_bytes(b'metadata-source')
    lineage = dict(closed='both', approval_id='test-only-approval', source_ids=['workbook'])
    context = dict(line='TKL', session='Mainline', direction='UT',
                   tension_lengths=[dict(from_m=0, to_m=2, tension_length='A', wire_role='contact', **lineage),
                                    dict(from_m=2, to_m=4, tension_length='B', wire_role='contact', **lineage)],
                   coverage=[dict(from_m=0, to_m=5, complete_tl_set=complete, **lineage)],
                   landmarks=[dict(from_m=1, to_m=1, landmark='Test location', **lineage)])
    document = dict(schema_version=VERSION, chainage_unit='m',
                    sources={'workbook': dict(path=workbook.name, sha256=hashlib.sha256(workbook.read_bytes()).hexdigest())},
                    approvals={'test-only-approval': dict(approved_by='test fixture', approved_at='2026-10-29', scope='fixture only')},
                    contexts=[context])
    sidecar = workbook.with_suffix('.approved-intervals.json')
    sidecar.write_text(json.dumps(document), encoding='utf-8')
    return workbook, sidecar, document


def test_endpoint_contact_and_partial_completeness(tmp_path):
    workbook, _, _ = release(tmp_path)
    provider = ApprovedIntervalProvider(workbook)
    at = lambda x: provider.lookup(x, 'TKL', 'Mainline', 'UT')
    assert at(2)['Overlap'] == 'Y'
    assert at(2)['Tension Length'] == 'A / B'
    for x in [0, 1.999999, 2.000001, 4]:
        assert at(x)['Overlap'] is None  # Unknown TLs may overlap the known TL.
    assert at(4.5)['tl_status'] == 'unresolved_pairing'
    assert at(6)['tl_status'] == 'outside_coverage'
    assert at(1)['Landmark'] == 'Test location'
    assert at(1.00001)['Landmark'] is None
    assert provider.lookup(2, 'TKL', 'TKS', 'UT')['Tension Length'] is None
    assert provider.lookup(2, 'TKL', 'Mainline', 'DT')['Tension Length'] is None
    frame = pd.DataFrame({'Chainage': [2, 1, 2.00001, 2, -1]})
    provider.map_frame(frame, 'TKL', 'Mainline', 'UT')
    assert frame['Tension Length'].tolist() == ['A / B', 'A', 'B', 'A / B', None]


def test_complete_coverage_permits_negative_only_with_known_tl(tmp_path):
    workbook, _, _ = release(tmp_path, complete=True)
    provider = ApprovedIntervalProvider(workbook)
    assert provider.lookup(1, 'TKL', 'Mainline', 'UT')['Overlap'] == 'N'
    assert provider.lookup(2, 'TKL', 'Mainline', 'UT')['Overlap'] == 'Y'
    assert provider.lookup(4.5, 'TKL', 'Mainline', 'UT')['Overlap'] is None


@pytest.mark.parametrize('mutation', ['messenger', 'approval', 'source', 'unit', 'closure', 'duplicate'])
def test_invalid_release_never_silently_maps(tmp_path, mutation):
    workbook, sidecar, document = release(tmp_path)
    interval = document['contexts'][0]['tension_lengths'][0]
    if mutation == 'messenger': interval['wire_role'] = 'messenger'
    if mutation == 'approval': interval['approval_id'] = 'missing'
    if mutation == 'source': document['sources']['workbook']['sha256'] = 'stale'
    if mutation == 'unit': document['chainage_unit'] = 'km'
    if mutation == 'closure': interval['closed'] = 'neither'
    if mutation == 'duplicate': document['contexts'].append(document['contexts'][0])
    sidecar.write_text(json.dumps(document), encoding='utf-8')
    with pytest.raises(MetadataCapabilityError): ApprovedIntervalProvider(workbook)


def test_source_or_approval_drift_during_analysis(tmp_path):
    workbook, sidecar, _ = release(tmp_path)
    provider = ApprovedIntervalProvider(workbook)
    provider.verify_sources()
    workbook.write_bytes(b'changed')
    with pytest.raises(MetadataCapabilityError, match='source changed'): provider.verify_sources()
    sidecar.write_text('{}')
    with pytest.raises(MetadataCapabilityError, match='release changed'): provider.verify_sources()


def test_missing_release_and_nan_are_unknown(tmp_path):
    workbook = tmp_path / 'missing.xlsx'
    provider = ApprovedIntervalProvider(workbook)
    frame = pd.DataFrame({'Chainage': [float('nan'), 12]})
    provider.map_frame(frame, 'ISL', 'Mainline', 'UT')
    assert frame['Overlap'].isna().all()
    assert frame['Tension Length'].isna().all()


def test_invalid_document_or_deleted_source_has_actionable_error(tmp_path):
    workbook, sidecar, _ = release(tmp_path)
    provider = ApprovedIntervalProvider(workbook)
    workbook.unlink()
    with pytest.raises(MetadataCapabilityError, match='unavailable.*import again'):
        provider.verify_sources()
    sidecar.write_text('[]')
    with pytest.raises(MetadataCapabilityError, match='document must be an object'):
        ApprovedIntervalProvider(workbook)


def test_approved_mapping_does_not_change_detection_or_median_samples(tmp_path):
    from app.core.analyzers import ExceptionDetector
    from app.core.tov1050_metadata import TOV1050MetadataManager
    from app.core.chainage_reduction import reduce_chainage
    from pathlib import Path
    config = Path(__file__).resolve().parents[2] / 'config/ISL metadata.xlsx'
    manager = TOV1050MetadataManager(config)
    workbook, _, _ = release(tmp_path, complete=True)
    provider = ApprovedIntervalProvider(workbook)
    frame = pd.DataFrame({'Chainage': [0, 0, 1, 1, 2, 3], 'height1': [4, 2, 8, 6, 9, 10],
                          'Class': ['Tunnel'] * 6, 'Track Type': ['Straight'] * 6})
    baseline, _ = reduce_chainage(frame)
    # Production API deliberately maps optional values after reduction.
    enriched, _ = reduce_chainage(frame.copy())
    enriched = provider.map_frame(enriched, 'TKL', 'Mainline', 'UT')
    pd.testing.assert_frame_equal(baseline, enriched[baseline.columns])
    # Exact adapter bypasses the legacy mixed-closure fallback.
    manager._approved_provider = provider
    manager.get_track_type_intervals = lambda *a: pd.DataFrame()
    detector = ExceptionDetector(manager)
    adapter = detector._map_track_info(frame.copy(), 'TKL', 'Mainline', 'UT')
    assert adapter.loc[adapter.Chainage == 2, 'Overlap'].eq('Y').all()
    assert adapter.loc[adapter.Chainage == 3, 'Overlap'].eq('N').all()
    before = detector._group_consecutive(pd.Series(True, index=baseline.index), baseline, 'height1', 'min', 'Mainline')
    after = detector._group_consecutive(pd.Series(True, index=enriched.index), enriched, 'height1', 'min', 'Mainline')
    stable = [c for c in before if c not in {'Tension Length', 'Overlap', 'Landmark'}]
    pd.testing.assert_frame_equal(before[stable], after[stable])
    assert after['Tension Length'].tolist() == ['A']  # Existing first-nonempty policy.
    manager.get_boundaries_for_plot = lambda *a: pd.DataFrame()
    manager.get_all_thresholds = lambda: pd.DataFrame([{
        'Class': 'Tunnel', 'Exc Type': 'Low Height', 'Track Type': 'Straight',
        'Low Height L1': 5, 'Low Height L2': 9,
    }])
    args = dict(line='TKL', section='Mainline', track='UT', date_str='20261029', metadata_mapped=True)
    old, _ = detector.analyze(baseline.copy(), **args)
    new, _ = detector.analyze(enriched.copy(), **args)
    assert not old['Low Height'].empty
    for kind in old:
        stable_columns = [c for c in old[kind] if c not in {'Tension Length', 'Overlap', 'Landmark'}]
        pd.testing.assert_frame_equal(old[kind][stable_columns], new[kind][stable_columns])


def test_export_keeps_position_evidence_out_of_summary_layout():
    from app.core.exporter import ExcelExporter
    record = dict(id='test', FromM=1, ToM=3, maxLocation=2,
                  metadata_enrichment=json.dumps({'overlap_status': 'unresolved_pairing'}))
    workbook = load_workbook(ExcelExporter.export_report({'Stagger': pd.DataFrame([record])}), read_only=True)
    assert 'MetadataEvidence' in workbook.sheetnames
    assert 'metadata_enrichment' not in next(workbook['Summary'].values)
    assert 'unresolved_pairing' in list(workbook['MetadataEvidence'].values)[1][-1]
    workbook.close()


@pytest.mark.parametrize('stream', [False, True])
def test_large_review_roundtrips_without_excel_cell_truncation(stream):
    from pathlib import Path
    from app.core.exporter import ExcelExporter
    from app.core.tov1050_metadata import TOV1050MetadataManager
    from app.core.tov1050_report_export import export_tov1050_report
    manager = TOV1050MetadataManager(Path(__file__).resolve().parents[2] / 'config/ISL metadata.xlsx')
    capabilities = manager.get_capabilities('ISL', 'Mainline', 'UT')
    assert len(json.dumps(capabilities)) > 32767  # Regression: an Excel cell would silently truncate this.
    metadata = {'metadata_capabilities': json.dumps(capabilities)}
    export = export_tov1050_report if stream else ExcelExporter.export_report
    output = export({}, metadata=metadata)
    workbook = load_workbook(output, read_only=True)
    saved = dict(list(workbook['_Metadata'].values)[1:])
    parsed = json.loads(saved['metadata_capabilities'])
    assert parsed['workbook_sha256'] == capabilities['workbook_sha256']
    assert 'boundary_review' not in parsed
    evidence = list(workbook['MetadataBoundaryReview'].values)
    count = sum(len(r['source_rows']) + len(r['known_boundaries']) for r in capabilities['boundary_review'])
    assert len(evidence) == count + 1
    assert 'Line' in evidence[0] and 'Track' in evidence[0]
    assert 'boundary_review' in capabilities  # Immutable API/snapshot evidence stays available.
    workbook.close()
