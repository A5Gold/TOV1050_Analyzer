"""Isolated read-only parameter exploration, not application code."""
import sys, json, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.tov1050_data_ingestion import TOV1050DataLoader

def run_starts(df):
    x = df.Chainage.to_numpy()
    counter = df['SampleCount [n.]'].astype(float).to_numpy()
    source = df.source_row_number.to_numpy()
    boundary = np.r_[True, (x[1:] != x[:-1]) | (np.diff(counter) < 0) | (np.diff(source) != 1)]
    return np.flatnonzero(boundary)

if __name__ == '__main__':
    out = {}
    for size in ['partial', 'full']:
        start = time.perf_counter()
        df = TOV1050DataLoader().load_data(ROOT / f'00 Reference Document/Raw data/TWL/test file {size}.csv')
        starts = run_starts(df)
        ends = np.r_[starts[1:], len(df)]
        lengths = ends - starts
        result = {'rows': len(df), 'runs': len(starts), 'run_sizes': dict(zip(*[a.tolist() for a in np.unique(lengths, return_counts=True)])), 'channels': {}}
        for c in ['height1','height2','stagger1','stagger2','wear1','wear2']:
            values = df[c].to_numpy(dtype=float)
            spans5, spans6 = [], []
            for lo, hi in zip(starts, ends):
                a = np.sort(values[lo:hi][np.isfinite(values[lo:hi])])
                if len(a) >= 5: spans5.append(float(np.min(a[4:] - a[:-4])))
                if len(a) >= 6: spans6.append(float(np.min(a[5:] - a[:-5])))
            q = [.1,.25,.5,.75,.9,.95,.99]
            result['channels'][c] = {'quantiles': q, 'min5_span': np.quantile(spans5,q).tolist(), 'min6_span':np.quantile(spans6,q).tolist(), 'finite':int(np.isfinite(values).sum())}
        result['seconds'] = time.perf_counter() - start
        out[size] = result
        print(json.dumps({size:result}), flush=True)
    (Path(__file__).parent/'profile.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
