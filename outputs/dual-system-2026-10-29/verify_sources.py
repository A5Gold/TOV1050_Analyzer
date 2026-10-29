"""Capture/verify read-only fixture hashes for this implementation."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).with_name('source-baseline.json')
FILES = [
    '00 Reference Document/Raw data/TML/TML_D1_260410.datac',
    '00 Reference Document/Raw data/TWL/20260907_TWL_UT.csv',
    '00 Reference Document/Raw data/TWL/20260630_TWL_UT.csv',
    '02 Output Document/TWL/20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report_MedianSample.xlsx',
    '02 Output Document/TWL/20260630_TWL_UT_MAINLINE_CEN_TSW_Exception_Report_MedianSample.xlsx',
    '02 Output Document/AEL/20260603_AEL_UT_MAINLINE_SHR_AWE_Exception_Report_MedianSample.xlsx',
]
FILES += [path.relative_to(ROOT).as_posix() for path in sorted((ROOT / 'config').glob('*.xlsx'))]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


actual = {name: {'sha256': digest(ROOT / name), 'bytes': (ROOT / name).stat().st_size} for name in FILES}
if '--verify' in sys.argv:
    expected = json.loads(DEST.read_text(encoding='utf-8'))['files']
    changed = [name for name, value in expected.items() if actual.get(name) != value]
    print(json.dumps({'source_files': len(expected), 'unchanged': not changed, 'changed': changed}))
    sys.exit(bool(changed))
if DEST.exists():
    raise SystemExit('Baseline already exists; use --verify')
DEST.write_text(json.dumps({
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'git_status': subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True),
    'files': actual,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'source_files': len(actual), 'baseline': str(DEST)}))
