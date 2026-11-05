"""Read-only source extraction for DRL wide candidate; never writes source XLSX."""
from pathlib import Path
import hashlib
import json
import sys
from collections import defaultdict
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/metadata-review-2026-11-03/drl-wide-v2'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.tov1050_capabilities import TensionLengthInterval, sweep_approved_intervals

paths = [ROOT / 'config/DRL metadata.xlsx',
         ROOT / 'outputs/metadata-review-2026-11-03/batch-01/candidates/DRL metadata (review candidate).xlsx',
         ROOT / '00 Reference Document/config/DRL metadata.xlsx']
sources = [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
raw, old, reference = [load_workbook(p, data_only=True) for p in paths]
sheets = []
def add(name, matrix):
    sheets.append({'name': name, 'matrix': matrix})

def row_ranges(values):
    ranges = []
    for value in sorted(set(values)):
        if ranges and value == ranges[-1][1]+1:
            ranges[-1][1] = value
        else:
            ranges.append([value,value])
    return ', '.join(str(a) if a==b else f'{a}-{b}' for a,b in ranges)

add('Review Guide', [['項目', '本版規則'],
    ['來源', '採用目前正式 DRL 的 threshold、location、track；支架沿用前輪標準化點表。'],
    ['路線', '只有 UT 與獨立 PL；沒有 DT；PL 不歸類 UT 或 DT。'],
    ['Wire Wear', 'OCS L1=9.1；ORCR 保留原來 7.44，其他門檻按來源轉 wide。'],
    ['TL 邊界', '依使用者 2026-11-03 確認，各路線每個 TL 的支架最小／最大里程。'],
    ['Overlap', '由同路線 TL 區間的 active set 產生；N 僅表示所列 TL 集合無重疊，域外留空。'],
    ['端點', '來源 TL 含兩端；DRL UT／PL 的 K 欄 both=含端點，neither=不含兩端；單點獨立保留。'],
    ['Landmark', '沒有核實區間，A:C 留空；不從普通支架猜測。'],
    ['啟用狀態', '新候選供手修；尚未替換 config。正式 loader 尚須接 UT／PL 獨立路線與 closure。'],
    ['Class 邊界', '保留來源 43599–43600、44300–44301 m 的 1m 間隔，沒有靜默延伸。']])

header = [c.value for c in reference['threshold'][1]][:15]
groups = {}
trace = [['Target', 'Source', 'Rule']]
for r in range(2, raw['threshold'].max_row + 1):
    cls, track, exc, low, high, remark = [raw['threshold'].cell(r,c).value for c in range(1,7)]
    if not exc or exc == 'normal':
        continue
    base, level = exc.rsplit(' ', 1)
    groups.setdefault((cls,track), {})[exc] = (low if base in {'Stagger','High Height'} else high, r)
wide = [header]
checks = []
for (cls,track), entries in groups.items():
    for exc in ['Stagger Left','Stagger Right','Wire Wear','Low Height','High Height']:
        base = 'Stagger' if exc.startswith('Stagger') else exc
        if not any(k.startswith(base+' ') for k in entries):
            continue
        row = [cls,track,exc] + [None]*12
        for c,label in enumerate(header[3:], 3):
            if label.startswith(base+' ') and label in entries:
                value, source_row = entries[label]
                row[c] = value
                target = f'threshold!{chr(65+c)}{len(wide)+1}'
                trace.append([target, f'config/DRL metadata.xlsx!threshold row {source_row}',
                              'min for Stagger/High Height; max for Wire Wear/Low Height'])
                checks.append({'row': len(wide)+1, 'column': c+1, 'value': value, 'source_row': source_row})
        wide.append(row)
add('threshold', wide)
locations = [[str(raw['location type'].cell(r,1).value),
              round(raw['location type'].cell(r,2).value*1000,4),
              round(raw['location type'].cell(r,3).value*1000,4)]
             for r in range(2,raw['location type'].max_row+1) if raw['location type'].cell(r,1).value]
add('Exception Boundarys', [['Line','Class','C/R','UT Track FromM','UT Track ToM','PL Track FromM','PL Track ToM']] +
    [['DRL',cls,'OCS',a,b,a,b] for cls,a,b in locations])
tl_matrix = [['Route','Tension Length','FromM','ToM','Point Count','Basis','Approval','Bracket Rows']]
bracket_sheets = []
atom_counts = {}
for route in ['UT','PL']:
    old_sheet = old[f'DRL {route} Brackets']
    points = [[c.value for c in row] for row in old_sheet.iter_rows()]
    points[0][4] = 'route'
    groups_tl = defaultdict(list)
    for r,point in enumerate(points[1:],2):
        point[4] = route
        if point[0] is not None and point[1] is not None and point[3] != 'landmark':
            groups_tl[str(point[1])].append((point[0], r))
    intervals = []
    for tl, values in groups_tl.items():
        lower,upper = min(p for p,r in values),max(p for p,r in values)
        tl_matrix.append([route,tl,lower,upper,len(values),'bracket min/max',
                          'user-confirmed 2026-11-03', row_ranges(r for p,r in values)])
        intervals.append(TensionLengthInterval(lower,upper,tl,'user-confirmed 2026-11-03',f'DRL {route} Brackets'))
    atoms = sweep_approved_intervals(intervals)
    atom_counts[route] = len(atoms)
    track = [[raw[f'{route} track type'].cell(r,1).value,
              round(raw[f'{route} track type'].cell(r,2).value*1000,4),
              round(raw[f'{route} track type'].cell(r,3).value*1000,4)]
             for r in range(2,raw[f'{route} track type'].max_row+1) if raw[f'{route} track type'].cell(r,1).value]
    matrix = [['Landmark FromM','Landmark ToM','Landmark','Overlap FromM','Overlap ToM','Overlap',
               'Tension Length','Track Type','Track Type FromM','Track Type ToM','Interval Closed']]
    for i in range(max(len(atoms),len(track))):
        row = [None]*11
        if i < len(atoms):
            atom = atoms[i]
            row[3:7] = [atom.from_m,atom.to_m,
                        'Y' if len(atom.active_tension_lengths)>1 else 'N' if atom.active_tension_lengths else None,
                        ','.join(atom.active_tension_lengths) or None]
            row[10] = atom.closed
        if i < len(track):
            row[7:10] = track[i]
        matrix.append(row)
    add(f'DRL {route}', matrix)
    bracket_sheets.append((f'DRL {route} Brackets', points))
for name,points in bracket_sheets:
    add(name,points)
add('TL Boundaries',tl_matrix)
add('Source provenance', [['Path','SHA256']] + [[s['path'],s['sha256']] for s in sources])
add('Conversion audit',trace)
layout = [{'filename':'DRL metadata (wide UT-PL candidate).xlsx','sheets':sheets}]
(OUT/'workbook-layouts.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'source-and-checks.json').write_text(json.dumps({'sources':sources,'threshold_checks':checks,
    'locations':locations,'atom_counts':atom_counts,'tl_rows':tl_matrix[1:]},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'output':str(OUT),'threshold_rows':len(wide)-1,'tl_count':len(tl_matrix)-1,'atoms':atom_counts}))
