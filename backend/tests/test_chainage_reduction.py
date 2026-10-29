import numpy as np
import pandas as pd
import pytest
from types import SimpleNamespace

from app.core.chainage_reduction import (
    ALGORITHM_VERSION, reduce_chainage, reduce_chainage_chunks,
)
from app.core.analyzers import ExceptionDetector


@pytest.mark.parametrize('size', [1, 4, 9, 10, 11, 20, 30])
def test_each_channel_selects_actual_central_value_and_earliest_source(size):
    rng = np.random.default_rng(size)
    frame = pd.DataFrame({'Chainage': [9999.8] * size,
                          'source_row_number': np.arange(101, 101 + size),
                          'SampleCount': np.arange(400, 400 + size),
                          'height1': rng.permutation(size).astype(float),
                          'wear2': rng.permutation(size).astype(float),
                          'stagger3': rng.integers(-3, 4, size).astype(float)})
    original = frame.copy(deep=True)
    result, metadata = reduce_chainage(frame)
    assert len(result) == 1
    for channel in ['height1', 'wear2', 'stagger3']:
        values = frame[channel].tolist()
        ordered = sorted(values)
        centers = {ordered[(size - 1) // 2], ordered[size // 2]}
        index = next(i for i, value in enumerate(values) if value in centers)
        assert result[channel].iloc[0] == values[index]
        assert result[f'{channel}_source_row'].iloc[0] == 101 + index
        assert result[f'{channel}_sample_counter'].iloc[0] == 400 + index
        assert result[f'{channel}_valid_count'].iloc[0] == size
    assert 'source_row_number' not in result and 'SampleCount' not in result
    assert result.source_row_first.iloc[0] == 101
    assert result.source_row_last.iloc[0] == 100 + size
    assert metadata['algorithm'] == ALGORITHM_VERSION
    assert metadata['noise_filter'] is None
    pd.testing.assert_frame_equal(frame, original)


def test_even_value_selection_uses_acquisition_order_not_always_lower_or_upper():
    frame = pd.DataFrame({'Chainage': [1] * 4 + [2] * 4,
                          'height1': [20, 10, 30, 0, 10, 20, 0, 30]})
    result, _ = reduce_chainage(frame)
    assert result.height1.tolist() == [20, 10]
    assert result.height1_source_row.tolist() == [1, 5]


def test_finite_values_only_and_all_missing_is_a_gap_not_zero():
    frame = pd.DataFrame({'Chainage': [1] * 5,
                          'height1': [np.nan, np.inf, -np.inf, 12., None],
                          'wear1': [np.nan, np.inf, -np.inf, None, np.nan]})
    result, _ = reduce_chainage(frame)
    assert result.height1.iloc[0] == 12
    assert result.height1_source_row.iloc[0] == 4
    assert result.height1_valid_count.iloc[0] == 1
    assert pd.isna(result.wear1.iloc[0])
    assert pd.isna(result.wear1_source_row.iloc[0])
    assert result.wear1_valid_count.iloc[0] == 0


def test_nonadjacent_revisit_decimal_precision_context_gap_and_reset_are_separate():
    frame = pd.DataFrame({'Chainage': [100.01, 100.01, 100.010001, 100.01, 100.01, 100.01, 100.01],
                          'height1': range(7), 'Class': ['A', 'A', 'A', 'A', 'B', 'B', 'B'],
                          'source_row_number': [2, 3, 4, 5, 6, 8, 9],
                          'SampleCount': [10, 11, 12, 13, 14, 15, 1]})
    result, _ = reduce_chainage(frame)
    assert result.sample_count.tolist() == [2, 1, 1, 1, 1, 1]
    assert result.source_row_first.tolist() == [2, 4, 5, 6, 8, 9]
    assert result.pass_id.tolist() == [0, 0, 0, 0, 0, 1]
    assert result.segment_id.tolist() == [0, 0, 0, 1, 2, 3]


@pytest.mark.parametrize('counter', ['SampleCount', 'SampleCount [n.]'])
def test_counter_alias_finite_reset_and_canonical_precedence(counter):
    frame = pd.DataFrame({'Chainage': [1.] * 6, 'height1': range(6),
                          counter: [10, np.inf, np.nan, 11, 1, 2]})
    if counter == 'SampleCount':
        frame['SampleCount [n.]'] = [6, 5, 4, 3, 2, 1]
    original = frame.copy(deep=True)
    result, metadata = reduce_chainage(frame)
    assert result.sample_count.tolist() == [4, 2]
    assert result.pass_id.tolist() == [0, 1]
    assert metadata['sample_counter_column'] == counter
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize('chunk_size', [1, 2, 3, 4, 7, 10, 11, 30])
@pytest.mark.parametrize('with_source', [False, True])
def test_chunk_boundaries_preserve_exact_frame_and_provenance(chunk_size, with_source):
    frame = pd.DataFrame({'Chainage': [1.] * 10 + [2.] * 4 + [1.] * 5 + [3.] * 11,
                          'height1': np.arange(30, dtype=float)[::-1],
                          'wear2': [np.nan] * 11 + list(np.arange(19, dtype=float)),
                          'Class': ['A'] * 15 + ['B'] * 15,
                          'SampleCount': list(range(16)) + list(range(14))})
    if with_source:
        frame['source_row_number'] = list(range(2, 18)) + list(range(20, 34))
    whole, whole_meta = reduce_chainage(frame)
    chunks = [frame.iloc[:0], *[frame.iloc[i:i + chunk_size] for i in range(0, len(frame), chunk_size)], frame.iloc[:0]]
    actual, metadata = reduce_chainage_chunks(chunks)
    pd.testing.assert_frame_equal(actual, whole)
    assert metadata == whole_meta


def test_empty_and_invalid_coordinate_rows_do_not_merge_and_singleton_passthrough():
    frame = pd.DataFrame({'Chainage': [np.nan, np.nan, 3., 4., 5.], 'height1': [1., 2., 3., 4., 5.]})
    result, _ = reduce_chainage(frame)
    assert result.height1.tolist() == [1., 2., 3., 4., 5.]
    assert result.segment_id.tolist() == [0, 1, 2, 2, 2]
    empty, metadata = reduce_chainage(frame.iloc[:0])
    assert empty.empty and metadata['raw_points'] == metadata['grouped_points'] == 0
    no_chunks, metadata = reduce_chainage_chunks([])
    assert no_chunks.empty and metadata['grouped_points'] == 0


def test_nullable_missing_identity_at_chunk_end_remains_an_isolated_segment():
    frame = pd.DataFrame({'Chainage': pd.Series([1., pd.NA, 2.], dtype='Float64'),
                          'source_row_number': pd.Series([1, pd.NA, 3], dtype='Int64'),
                          'height1': pd.Series([4., pd.NA, 6.], dtype='Float64')})
    whole, _ = reduce_chainage(frame)
    chunked, _ = reduce_chainage_chunks([frame.iloc[:2], frame.iloc[2:]])
    pd.testing.assert_frame_equal(whole, chunked)
    assert whole.segment_id.tolist() == [0, 1, 2]
    assert pd.isna(whole.height1_source_row.iloc[1])


def _peak_frame():
    return pd.DataFrame({'Chainage': [100., 100.2, 100.4, 100.6],
                         'Class': ['Tunnel'] * 4, 'Track Type': ['Tangent'] * 4,
                         'height_min': [4000., 3900., 3800., 3700.],
                         'height1': [4500., 3900., 4000., 4000.],
                         'height2': [4000., 4000., 3800., 3700.],
                         'height1_source_row': [2., 13., 22., 32.],
                         'height2_source_row': [5., 15., 28., 39.],
                         'height2_sample_counter': [4., 14., 27., 38.],
                         'group_id': [80, 81, 82, 83],
                         'segment_id': [0, 0, 1, 1]})


def test_detector_respects_segments_and_reports_the_peak_channels_actual_source():
    frame = _peak_frame()
    result = ExceptionDetector(None)._group_consecutive(pd.Series([True] * 4), frame, 'height_min', 'min', 'Mainline')
    assert result.FromM.tolist() == [100., 100.4]
    assert result.ToM.tolist() == [100.2, 100.6]
    assert result.peak_channel.tolist() == ['height1', 'height2']
    assert result.peak_source_row.tolist() == [13., 39.]
    assert result.peak_group_id.tolist() == [81, 83]
    assert result.peak_segment_id.tolist() == [0, 1]
    assert result.peak_sample_counter.iloc[1] == 38
    # Existing raw callers have no segment marker and keep existing continuity.
    legacy = frame.drop(columns=['segment_id'])
    old = ExceptionDetector(None)._group_consecutive(pd.Series([True] * 4), legacy, 'height_min', 'min', 'Mainline')
    assert len(old) == 1 and old.FromM.iloc[0] == 100 and old.ToM.iloc[0] == 100.6


def test_detector_does_not_bridge_a_missing_measurement_or_change_other_channel_peaks():
    frame = _peak_frame()
    frame.loc[1, ['height1', 'height2', 'height_min']] = np.nan
    result = ExceptionDetector(None)._group_consecutive(frame.height_min.le(4200), frame, 'height_min', 'min', 'Mainline')
    assert result.FromM.tolist() == [100., 100.4]
    assert result.ToM.tolist() == [100., 100.6]
    assert result.peak_channel.tolist() == ['height2', 'height2']


@pytest.mark.parametrize('kind,channel,target,level,threshold', [
    ('Low Height', 'height2', 4550., 'L2', 4600.),
    ('Low Height', 'height2', 4450., 'L1', 4500.),
    ('High Height', 'height2', 5850., 'L2', 5800.),
    ('High Height', 'height2', 5950., 'L1', 5900.),
    ('Wire Wear', 'wear2', 7., 'L2', 8.),
    ('Wire Wear', 'wear2', 5., 'L1', 6.),
    ('Stagger Left', 'stagger2', 325., 'L3', 300.),
    ('Stagger Left', 'stagger2', 375., 'L2', 350.),
    ('Stagger Left', 'stagger2', 425., 'L1', 400.),
    ('Stagger Right', 'stagger2', -325., 'L3', 300.),
    ('Stagger Right', 'stagger2', -375., 'L2', 350.),
    ('Stagger Right', 'stagger2', -425., 'L1', 400.),
])
def test_reduced_threshold_levels_and_peak_identity_use_representative_samples(
        kind, channel, target, level, threshold):
    thresholds = pd.DataFrame([
        {'Exc Type': 'Low Height', 'Class': 'both', 'Track Type': 'both',
         'Low Height L1': 4500., 'Low Height L2': 4600.},
        {'Exc Type': 'High Height', 'Class': 'both', 'Track Type': 'both',
         'High Height L1': 5900., 'High Height L2': 5800.},
        {'Exc Type': 'Wire Wear', 'Class': 'both', 'Track Type': 'both',
         'Wire Wear L1': 6., 'Wire Wear L2': 8.},
        *[{'Exc Type': f'Stagger {side}', 'Class': 'both', 'Track Type': 'Tangent',
           'Stagger L1': 400., 'Stagger L2': 350., 'Stagger L3': 300.}
          for side in ['Left', 'Right']],
    ])
    metadata = SimpleNamespace(get_all_thresholds=lambda: thresholds,
                               get_boundaries_for_plot=lambda *args: pd.DataFrame())
    detector = ExceptionDetector(metadata)
    # Context is already mapped before reduction, as in the new import path.
    detector._map_class_info = lambda frame, *args: frame
    detector._map_track_info = lambda frame, *args: frame
    defaults = {'height1': 5200., 'height2': 5200., 'wear1': 12., 'wear2': 12.,
                'stagger1': 0., 'stagger2': 0.}
    raw = pd.DataFrame({**{c: [value] * 10 for c, value in defaults.items()},
                        'Chainage': [1000.] * 10, 'Class': ['both'] * 10,
                        'Track Type': ['Tangent'] * 10,
                        'source_row_number': range(100, 110),
                        'SampleCount': range(200, 210)})
    # A raw extreme at the first source row must not become the reduced peak.
    raw[channel] = [target * 2, *([target] * 8), defaults[channel]]
    representative, _ = reduce_chainage(raw)
    results, _ = detector.analyze(representative, 'TWL', 'Mainline', 'UT', '20261026')
    exception = results[kind]
    assert len(exception) == 1
    row = exception.iloc[0]
    assert row.maxValue == target and row.level == level
    assert row['Threshold Value'] == threshold
    assert row.FromM == row.ToM == row.maxLocation == 1000.
    assert row.peak_channel == channel
    assert row.peak_source_row == 101 and row.peak_sample_counter == 201
    assert row.peak_group_id == 0 and row.peak_segment_id == 0


def test_analyze_metadata_mapped_skips_context_remapping():
    thresholds = pd.DataFrame([{
        'Exc Type': 'Low Height', 'Class': 'both', 'Track Type': 'both',
        'Low Height L1': 4500., 'Low Height L2': 4600.,
    }])
    class ExplodingMetadata:
        def get_all_thresholds(self):
            return thresholds
        def get_boundaries_for_plot(self, *args):
            return pd.DataFrame()
    detector = ExceptionDetector(ExplodingMetadata())
    detector._map_class_info = lambda *_: (_ for _ in ()).throw(AssertionError('unexpected remap'))
    detector._map_track_info = lambda *_: (_ for _ in ()).throw(AssertionError('unexpected remap'))
    frame = pd.DataFrame({
        'Chainage': [10.], 'Class': ['both'], 'Track Type': ['Tangent'],
        'height1': [5000.], 'height2': [5000.], 'height3': [5000.], 'height4': [5000.],
    })
    detector.analyze(frame, 'TWL', 'Mainline', 'UT', '20261026', metadata_mapped=True)
