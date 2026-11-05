"""Extract latest TOV1050 sources into auditable wide-candidate layouts."""
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import math
import sys

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/metadata-review-2026-11-03/other-lines-wide-v1'
sys.path.insert(0, str(ROOT/'backend'))
from app.core.tov1050_metadata import TOV1050MetadataManager
from app.core.tov1050_capabilities import TensionLengthInterval, sweep_approved_intervals
from app.core.tov1050_boundary_review import termination_evidence

ITEMS = [('ISL','ISL','Mainline'), ('KTL','KTL','Mainline'),
         ('LAR_AEL','AEL','Mainline'), ('LAR_TCL','TCL','Mainline'),
         ('TKL','TKL','Mainline'), ('TKS','TKL','TKS'), ('TWL','TWL','Mainline')]
HEADERS = ['Landmark FromM','Landmark ToM','Landmark','Overlap FromM','Overlap ToM',
           'Overlap','Tension Length','Track Type','Track Type FromM','Track Type ToM','Interval Closed']

def ranges(values):
    result=[]
    for value in sorted(set(values)):
        if result and value==result[-1][1]+1:
            result[-1][1]=value
        else:
            result.append([value,value])
    return ', '.join(str(a) if a==b else f'{a}-{b}' for a,b in result)

def clean(value):
    if isinstance(value,float) and math.isnan(value):
        return None
    return value.item() if hasattr(value,'item') else value

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    layouts=[]
    for identity,line,session in ITEMS:
        path=ROOT/'config'/f'{identity} metadata.xlsx'
        source_sha=hashlib.sha256(path.read_bytes()).hexdigest()
        book=load_workbook(path,data_only=False)
        manager=TOV1050MetadataManager(path)
        layout={'identity':identity,'line':line,'session':session,'source':str(path),
                'source_sha256':source_sha,'filename':f'{identity} metadata.xlsx',
                'source_sheets':book.sheetnames,'changes':[], 'added':[], 'routes':[], 'source_warnings':[]}
        with ZipFile(path) as package:
            layout['native_features']=[name for name in package.namelist()
                if name.startswith(('xl/charts/','xl/pivotTables/','xl/externalLinks/','xl/tables/')) and name.endswith('.xml')]
        tl_table=[['Sheet','Tension Length','FromM','ToM','Point Count','Basis','Status','Source Rows']]
        landmark_table=[['Sheet','Landmark FromM','Landmark ToM','Landmark','Kind','Source Row']]
        for direction in ['UT','DT']:
            name=f'{identity} {direction}'
            sheet=book[name]
            assert [c.value for c in sheet[1]][:7]==['Track Type','Track Type FromM','Track Type ToM',None,'Bracket FromM','Tension Length','Bracket']
            tracks=[]
            for r in range(2,sheet.max_row+1):
                values=[sheet.cell(r,c).value for c in range(1,4)]
                if any(v is not None for v in values):
                    assert values[0] and all(isinstance(v,(int,float)) and math.isfinite(v) for v in values[1:])
                    assert values[1]<=values[2]
                    tracks.append(values)
            points=manager._point_frame(line,session,direction).to_dict('records')
            assert not any(p['classification']=='unclassified' for p in points), name
            bracket_matrix=[['Bracket FromM','Tension Length','Bracket','classification','wire_role',
                'source_sheet','source_excel_row','original_workbook','original_sheet',
                'original_excel_row','source_bracket','component_index']]
            groups=defaultdict(list)
            excluded=[]
            landmarks=[]
            domain_columns=(4,5) if direction=='UT' else (6,7)
            domain_values=[book['Exception Boundarys'].cell(r,c).value
                for r in range(2,book['Exception Boundarys'].max_row+1) for c in domain_columns
                if isinstance(book['Exception Boundarys'].cell(r,c).value,(int,float))]
            domain=(min(domain_values),max(domain_values))
            for point in points:
                r=point['excel_row']
                evidence=termination_evidence(point['bracket']) if point['classification']=='termination' else None
                role=evidence['wire_role'] if evidence else None
                original=[sheet.cell(r,c).value for c in (5,6,7)]
                bracket_matrix.append(original+[point['classification'],role,name,r,
                    point['source_workbook'],point['source_sheet'],clean(point['source_excel_row']),
                    point['source_bracket'],clean(point['component_index'])])
                if point['classification'] in {'normal','termination'} and not domain[0]<=point['chainage_m']<=domain[1]:
                    layout['source_warnings'].append({'sheet':name,'cell':f'E{r}',
                        'bracket':point['bracket'],'value_m':point['chainage_m'],
                        'tension_length':point['tension_length'],'domain_m':domain,
                        'candidate_cell':f'{name} Brackets!A{len(bracket_matrix)}',
                        'original_mapping_sheet':point['source_sheet'],
                        'original_mapping_row':clean(point['source_excel_row'])})
                if point['classification']=='landmark':
                    landmarks.append([point['chainage_m'],point['chainage_m'],point['bracket']])
                    landmark_table.append([name,point['chainage_m'],point['chainage_m'],point['bracket'],'point-only',r])
                elif point['classification'] in {'normal','termination'} and point['tension_length']:
                    if role in {'messenger','ambiguous'}:
                        excluded.append({'row':r,'bracket':point['bracket'],'role':role})
                    else:
                        groups[point['tension_length']].append((point['chainage_m'],r))
            tl_intervals=[]
            for tl,values in sorted(groups.items()):
                lower,upper=min(v for v,r in values),max(v for v,r in values)
                status='review_required: single_point' if lower==upper else 'review_candidate; not runtime approval'
                if lower<domain[0] or upper>domain[1]:
                    status='review_required: source outside Class domain'
                tl_table.append([name,tl,lower,upper,len(values),'physical bracket min/max; excludes explicit Messenger',status,ranges(r for v,r in values)])
                tl_intervals.append(TensionLengthInterval(lower,upper,tl,'review-candidate-request-2026-11-03',name))
            atoms=sweep_approved_intervals(tl_intervals)
            matrix=[HEADERS]
            for i in range(max(len(atoms),len(tracks),len(landmarks))):
                row=[None]*11
                if i<len(landmarks):
                    row[:3]=landmarks[i]
                if i<len(atoms):
                    atom=atoms[i]
                    row[3:7]=[atom.from_m,atom.to_m,
                        'Y' if len(atom.active_tension_lengths)>1 else 'N' if atom.active_tension_lengths else None,
                        ','.join(atom.active_tension_lengths) or None]
                    row[10]=atom.closed
                if i<len(tracks):
                    row[7:10]=tracks[i]
                matrix.append(row)
            layout['changes'].append({'name':name,'matrix':matrix,'source_max_row':sheet.max_row})
            layout['added'].append({'name':name+' Brackets','matrix':bracket_matrix})
            layout['routes'].append({'name':name,'track_count':len(tracks),'point_count':len(points),
                'landmark_count':len(landmarks),'tl_count':len(tl_intervals),'atom_count':len(atoms),
                'messenger_excluded':excluded,'single_point_tls':[t.tension_length for t in tl_intervals if t.from_m==t.to_m]})
        guide=[['項目','規則／使用方式'],
            ['本批狀態','標準化候選，供手動核對；沒有替換config或啟用runtime provider。'],
            ['A:K欄組','與DRL wide候選一致；A:C、D:G、H:J是獨立清單，不按同列互相對應。'],
            ['TL','同方向／TL支架min/max候選；Landmark及明確Messenger不作Contact邊界依據。'],
            ['Overlap','同方向TL候選active集合；Y=多TL，N只限目前所列TL集合，域外／無TL未知。'],
            ['Interval Closed','K欄只屬D:E區間：both含兩端；neither不含兩端；單點atoms另列。'],
            ['Landmark','A:C來源是單點，FromM=ToM；同名不同位置不合併，也不擴張猜範圍。'],
            ['支架與來源','完整點表在各Brackets頁；__provenance__等舊audit頁保留，代表轉換前來源歷史。'],
            ['數值','threshold、Class、Track Type沿現行config原值；canonical m，不再乘1000。'],
            ['正式程式','須接入精確closure／TL候選及Landmark點語義後才可正式啟用。']]
        layout['added'].extend([{'name':'TL Boundaries','matrix':tl_table},
            {'name':'Landmark Points','matrix':landmark_table},
            {'name':'Wide Candidate Guide','matrix':guide},
            {'name':'Wide Candidate Source','matrix':[['Source workbook','SHA256','Rules','Status'],
                [str(path),source_sha,'other-lines-wide-2026-11-03-v1','review-only; not activated']]}])
        if layout['source_warnings']:
            guide.append(['來源需核對','Data Review列出超出Class整體範圍的支架；受影響TL及Overlap僅供查錯，不能直接啟用。'])
            review=[['Source Sheet','Source Cell','Bracket','Value (m)','Class Domain (m)',
                     'Tension Length','Candidate Cell','Action']]
            for warning in layout['source_warnings']:
                review.append([warning['sheet'],warning['cell'],warning['bracket'],warning['value_m'],
                    f'{domain[0]}–{domain[1]}' if len(layout['routes'])==1 else
                    f'{warning["domain_m"][0]}–{warning["domain_m"][1]}',
                    warning['tension_length'],warning['candidate_cell'],
                    '核對正確里程；保留來源值，受影響區間尚不能啟用'])
            layout['added'].append({'name':'Data Review','matrix':review})
        layouts.append(layout)
    (OUT/'workbook-layouts.json').write_text(json.dumps(layouts,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'workbooks':len(layouts),'routes':sum(len(l['routes']) for l in layouts),
        'points':sum(r['point_count'] for l in layouts for r in l['routes']),
        'landmarks':sum(r['landmark_count'] for l in layouts for r in l['routes']),
        'tension_lengths':sum(r['tl_count'] for l in layouts for r in l['routes'])}))

if __name__=='__main__':
    prepare()
