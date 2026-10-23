"""Record full-data detection goldens and mapping coverage without exports."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.api.endpoints import analysis
from app.core.tov1050_contract import metadata_workbook_for
from app.core.tov1050_metadata import TOV1050MetadataManager


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    app=FastAPI()
    app.include_router(analysis.router)
    client=TestClient(app)
    evidence=[]
    fixtures=[("AEL","UT","20260822_AEL_UT_SHO_AWE.csv"),("KTL","UT","20260825_KTL_UT.csv"),("TKL","DT","20260708_TKL_DT.csv")]
    for line,track,name in fixtures:
        path=ROOT/"00 Reference Document/Raw data"/line/name
        params=dict(file_path=str(path),line=line,track=track,section="Mainline",session="Mainline",date_str=name[:8],station_start="SHO" if line=="AEL" else "NOT_PROVIDED",station_end="AWE" if line=="AEL" else "NOT_PROVIDED",client_session_id="fixture-audit")
        response=client.post("/analyze",json=params)
        assert response.status_code==200,response.text
        payload=response.json()
        frame=analysis.ANALYSIS_SESSIONS["fixture-audit"]["raw_df"]
        manager=TOV1050MetadataManager(metadata_workbook_for(line,"Mainline",ROOT/"config"))
        missing={}
        for label,intervals in (("class",manager.get_exception_boundaries(line,track,"Mainline")),("track",manager.get_track_type_intervals(line,"Mainline",track))):
            _,positions=intervals.index.get_indexer_non_unique(frame.Chainage)
            missing[label]=dict(uncovered_rows=len(positions),first_uncovered_chainages_m=frame.iloc[positions[:20]].Chainage.tolist())
        item=dict(source=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),context=params,
                  cleaning=payload["cleaning_summary"],class_counts=frame.Class.fillna("<missing>").value_counts().to_dict(),
                  track_type_counts=frame["Track Type"].fillna("<missing>").value_counts().to_dict(),mapping_coverage=missing,
                  exceptions=payload["exceptions"],metadata_capabilities=payload["metadata_capabilities"],
                  chart_resolution=payload["chart_resolution"],
                  limitation="Station labels NOT_PROVIDED are explicit test export context, not authoritative station bounds" if line!="AEL" else "Sample without exceptions")
        (args.output/f"{line}-{track}-golden.json").write_text(json.dumps(item,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        evidence.append(dict(line=line,track=track,rows=len(frame),exceptions={k:len(v) for k,v in payload["exceptions"].items()},mapping_coverage=missing))
        print(json.dumps(evidence[-1]),flush=True)
        analysis.ANALYSIS_SESSIONS.clear()
        analysis.LAST_RAW_DF=pd.DataFrame()
        del frame,payload,response
    (args.output/"summary.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
