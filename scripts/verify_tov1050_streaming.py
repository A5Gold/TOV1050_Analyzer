"""Compare the new writer against saved, pinned TOV640 subprocess evidence."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys

from verify_tov1050_contracts import ROOT, PIN, compare


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--baseline",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    results=[]
    for name in ("canonical-asc-default","canonical-desc-custom","canonical-isolated-levels","legacy-EAL"):
        output=args.output/f"{name}-tov1050.json.gz"
        subprocess.run([sys.executable,str(ROOT/"scripts/tov1050_contract_worker.py"),"--repo",str(ROOT),
                        "--input",str(args.baseline/f"{name}-input.json"),"--output",str(output),"--streaming"],check=True,
                       stdout=subprocess.DEVNULL)
        compare(json.loads(gzip.decompress((args.baseline/f"{name}-tov640.json.gz").read_bytes())),
                json.loads(gzip.decompress(output.read_bytes())))
        results.append(dict(case=name,status="pass",reference_commit=PIN,
                            writer="TOV1050 streaming; exception/enrichment semantics unchanged"))
        print(f"{name}: pass",flush=True)
    (args.output/"results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
