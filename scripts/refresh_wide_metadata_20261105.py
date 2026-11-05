"""Read revised candidates; prepare new derived layouts without writing XLSX."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import sys
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/metadata-review-2026-11-05/wide-v3'
sys.path.insert(0, str(ROOT / 'backend'))
from app.core.tov1050_capabilities import TensionLengthInterval, sweep_approved_intervals

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def matrix(sheet):
    rows = [list(r) for r in sheet.values]
    while rows and not any(v is not None for v in rows[-1]):
        rows.pop()
    return rows

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = ROOT / '00 Reference Document/TOV1050 TL-BK No.xlsx'
    sources = sorted((ROOT / 'outputs/metadata-review-2026-11-03/other-lines-wide-v1/candidates').glob('*.xlsx'))
    sources.append(ROOT / 'outputs/metadata-review-2026-11-03/drl-wide-v2/DRL metadata (wide UT-PL candidate).xlsx')
    layouts = []
    for source in sources:
        book = load_workbook(source, data_only=False)
        changes = []
        tls = [['Sheet', 'Tension Length', 'FromM', 'ToM', 'Point Count', 'Basis', 'Status', 'Source Rows']]
        route_counts = []
        for bracket_sheet in [s for s in book.sheetnames if s.endswith(' Brackets')]:
            name = bracket_sheet.removesuffix(' Brackets')
            raw = matrix(book[bracket_sheet]); headers = raw[0]
            h = {v: i for i,v in enumerate(headers)}
            groups = defaultdict(list)
            # Preserve explicit classification/role from each candidate's Brackets.
            for rownum, row in enumerate(raw[1:], 2):
                position, tl, label = row[:3]
                if position is None or tl is None:
                    continue
                kind = row[h['classification']] if 'classification' in h else 'normal'
                role = row[h['wire_role']] if 'wire_role' in h else None
                if kind not in {'normal', 'termination'} or role in {'messenger', 'ambiguous'}:
                    continue
                tl = str(int(tl)) if isinstance(tl,float) and tl.is_integer() else str(tl)
                groups[tl].append((float(position), rownum))
            intervals = []
            for tl, points in sorted(groups.items()):
                lower, upper = min(x for x,r in points), max(x for x,r in points)
                intervals.append(TensionLengthInterval(lower,upper,tl,'user-rule-2026-11-05',bracket_sheet))
                tls.append([name,tl,lower,upper,len(points),'physical brackets + Contact termination min/max',
                            'single_point' if lower==upper else 'user-confirmed rule 2026-11-05',
                            ','.join(str(r) for p,r in points)])
            old = matrix(book[name]); main = old[0]
            landmarks = []
            tracks = []
            for row in old[1:]:
                row += [None] * (11-len(row))
                if row[2] is not None:
                    a,b = row[:2]
                    if a is None or b is None or a>b:
                        raise ValueError(f'{source.name}/{name}: invalid Landmark interval')
                    landmarks.append([a-100,b+100,row[2]] if a==b else row[:3])
                if row[7] is not None:
                    tracks.append(row[7:10])
            atoms = sweep_approved_intervals(intervals)
            new = [main]
            for i in range(max(len(atoms),len(landmarks),len(tracks))):
                row = [None]*11
                if i<len(landmarks): row[:3]=landmarks[i]
                if i<len(tracks): row[7:10]=tracks[i]
                if i<len(atoms):
                    atom=atoms[i]
                    row[3:7]=[atom.from_m,atom.to_m,'Y' if len(atom.active_tension_lengths)>1 else 'N' if atom.active_tension_lengths else None,','.join(atom.active_tension_lengths) or None]
                    row[10]=atom.closed
                new.append(row)
            changes.append({'name':name,'matrix':new,'old_rows':book[name].max_row,'new':False})
            route_counts.append({'sheet':name,'tl_count':len(groups),'landmarks':len(landmarks),'atoms':len(atoms)})
        changes.append({'name':'TL Boundaries','matrix':tls,'old_rows':book['TL Boundaries'].max_row,'new':False})
        if 'Data Review' in book:
            review=matrix(book['Data Review'])
            for row in review[1:]:
                refs={'ISL UT':112948,'TKL UT':60316,'TKL DT':62208}
                if row[0] in refs:
                    row[3]=refs[row[0]]
                    row[7]='已由使用者修正；新TL／Overlap已重算（2026-11-05）'
            changes.append({'name':'Data Review','matrix':review,'old_rows':book['Data Review'].max_row,'new':False})
        guide_name='Wide Candidate Guide' if 'Wide Candidate Guide' in book else 'Review Guide'
        guide=matrix(book[guide_name])
        guide=[guide[0],['規則日期','2026-11-05；使用者確認全部實體支架及Contact termination取min/max'],
               ['Overlap','單TL=N；多TL=Y；無TL未知；K欄只控制D:E端點'],
               ['Landmark','原有範圍保留；原始單點X擴為[X-100,X+100]m；不重複擴張'],
               ['欄組','A:C、D:G、H:J是獨立清單，同列不代表互相對應'],
               ['來源保存','Brackets及原始Landmark Points保留；舊audit／provenance為轉換歷史'],
               ['狀態','新版本候選；未替換正式config；需以更新loader驗證'],
               ['資料缺口','沒有Landmark來源的方向維持空白；單點TL不擴張']]
        changes.append({'name':guide_name,'matrix':guide,'old_rows':book[guide_name].max_row,'new':False})
        provenance=[['Item','Path / rule','SHA256'],['input_candidate',str(source),digest(source)],
                    ['mapping_source',str(mapping),digest(mapping)],['rule','wide-enrichment-2026-11-05-v1',None],
                    ['landmark_rule','existing interval unchanged; point +/-100m once',None],
                    ['activation','isolated candidate only',None]]
        changes.append({'name':'Rules 2026-11-05','matrix':provenance,'old_rows':0,'new':True})
        filename='DRL metadata.xlsx' if source.name.startswith('DRL') else source.name
        layouts.append({'source':str(source),'source_sha256':digest(source),'filename':filename,
                        'changes':changes,'routes':route_counts})
        book.close()
    (OUT/'layouts.json').write_text(json.dumps(layouts,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'workbooks':len(layouts),'routes':sum(len(x['routes']) for x in layouts)}))

if __name__=='__main__': prepare()
