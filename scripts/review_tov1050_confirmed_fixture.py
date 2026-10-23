"""Read-only source-row review and evidence-aware fixture coverage merge."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.core.tov1050_data_ingestion import TOV1050DataLoader
from app.core.tov1050_metadata import TOV1050MetadataManager
from app.core.tov1050_contract import metadata_workbook_for


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fixture',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--previous',type=Path,required=True)
    parser.add_argument('--metadata-dir',type=Path,default=ROOT/'config')
    args=parser.parse_args()
    config=json.loads((ROOT/'config/tov1050-regression-fixture-contexts.json').read_text(encoding='utf-8'))
    context=config[args.fixture]
    source=ROOT/args.fixture
    assert sha(source)==context['source_sha256'],'Confirmed source changed'
    frame=TOV1050DataLoader().load_data(source)
    line,session,track=(context[k] for k in ('line','session','track'))
    workbook=metadata_workbook_for(line,session,args.metadata_dir.resolve())
    manager=TOV1050MetadataManager(workbook)
    review=pd.DataFrame({'source_csv':args.fixture,'source_row_number':frame.source_row_number,
                         'Chainage_m':frame.Chainage,'line':line,'session':session,'direction':track})
    intervals=(('class',manager.get_exception_boundaries(line,track,session)),
               ('track',manager.get_track_type_intervals(line,session,track)))
    for label,data in intervals:
        _,missing=data.index.get_indexer_non_unique(frame.Chainage)
        review[f'{label}_covered']=True
        review.iloc[missing,review.columns.get_loc(f'{label}_covered')]=False
    review.to_csv(args.output/'retained-chainage-review.csv',index=False,encoding='utf-8-sig')
    sheets=[]
    wide=manager._uses_wide_intervals()
    track_sheet=' '.join(manager._wide_context(line,session,track)) if wide else manager._get_direction_sheet(session,track)
    for sheet in (('Exception Boundarys',track_sheet) if wide else ('location type',track_sheet)):
        data=pd.read_excel(workbook,sheet_name=sheet)
        data.insert(0,'excel_row',data.index+2)
        data.insert(0,'sheet',sheet)
        data.insert(0,'workbook',str(workbook))
        if wide:
            prefix='UP' if track=='UT' else 'DN'
            start,end=(f'{prefix} Track FromM',f'{prefix} Track ToM') if sheet=='Exception Boundarys' else ('Track Type FromM','Track Type ToM')
            data=data.loc[data[start].notna() | data[end].notna()].copy()
            data['FromM']=pd.to_numeric(data[start])
            data['ToM']=pd.to_numeric(data[end])
        else:
            data['FromM']=pd.to_numeric(data.startKM)*1000
            data['ToM']=pd.to_numeric(data.endKM)*1000
        sheets.append(data)
    pd.concat(sheets,ignore_index=True).to_csv(args.output/'metadata-interval-review.csv',index=False,encoding='utf-8-sig')
    previous=json.loads((args.previous/'real-results.json').read_text(encoding='utf-8'))
    for run in previous['real_runs']:
        assert sha(run['path'])==run['sha256'],'Previous fixture source changed'
        capabilities=run['metadata_capabilities']
        assert sha(capabilities['workbook'])==capabilities['workbook_sha256'],'Previous metadata changed'
    matrix=pd.read_csv(args.previous/'real-fixture-coverage.csv',keep_default_na=False)
    matrix['evidence_batch']=args.previous.name
    matrix['validation_scope']='previous_full_export_snapshot; source and metadata digests rechecked'
    current=pd.read_csv(args.output/'real-fixture-coverage.csv',keep_default_na=False)
    for row in current.to_dict('records'):
        match=matrix.line.eq(row['line']) & matrix.session.eq(row['session']) & matrix.direction.eq(row['direction'])
        assert int(match.sum())==1
        for key,value in row.items():
            matrix.loc[match,key]=value
        matrix.loc[match,'evidence_batch']=args.output.name
        matrix.loc[match,'validation_scope']='isolated_reference_only; complete exports verified; runtime remains blocked' if row['status']=='pass_isolated_reference_only' else 'current_analysis_preflight; exports not run when blocked'
    matrix.to_csv(args.output/'combined-fixture-coverage.csv',index=False,encoding='utf-8-sig')
    print(json.dumps(dict(contexts=len(matrix),statuses=matrix.status.value_counts().to_dict(),
                         retained_rows=len(frame),coverage=manager.get_measurement_coverage(frame.Chainage,line,session,track))))


if __name__=='__main__':
    main()
