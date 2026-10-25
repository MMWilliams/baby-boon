"""Copy the small, immutable pilot records into versioned evidence."""
import json
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tinysocial.common import digest, write_json


def main():
    items={
        "training":("checkpoints/pilot-v1",["config.json","result.json","resources.json","train.jsonl"]),
        "smol-float":("runs/baseline-smol-cpu",["config.json","responses.jsonl","resources.json"]),
        "qwen-float":("runs/baseline-qwen-cpu-v2",["config.json","responses.jsonl","resources.json"]),
        "pilot-float":("runs/pilot-float",["config.json","responses.jsonl","resources.json"]),
        "base-cpu":("runs/quantized-base-matched",["summary.json","responses.jsonl"]),
        "pilot-cpu":("runs/quantized-pilot",["summary.json","responses.jsonl"]),
        "base-export":("models/qwen-base-matched",["manifest.json"]),
        "pilot-export":("models/pilot-v1",["manifest.json"]),
        "teacher-probe":("runs/teacher-cpu-probe",["manifest.json","responses.jsonl"]),
    }
    records=[]
    for label,(directory,names) in items.items():
        dest=ROOT/"evidence/pilot"/label
        dest.mkdir(parents=True,exist_ok=True)
        for name in names:
            src=ROOT/directory/name
            target=dest/name
            shutil.copyfile(src,target)
            records.append({"path":target.relative_to(ROOT).as_posix(),"sha256":digest(target)})
    write_json(ROOT/"evidence/pilot/records.json",records)
    print("Archived",len(records),"experiment records")


if __name__=="__main__": main()
