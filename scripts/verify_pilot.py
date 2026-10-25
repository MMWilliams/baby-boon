"""Verify the actual artifacts; report known quality failure without hiding it."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tinysocial.common import digest, read_jsonl, verify_frozen
from tinysocial.data import audit


def main():
    verify_frozen()
    audit(ROOT/"data/pilot-v1")
    for record in json.loads((ROOT/"evidence/pilot/records.json").read_text()):
        assert digest(ROOT/record["path"])==record["sha256"],record["path"]
    for path in ["runs/baseline-smol-cpu","runs/baseline-qwen-cpu-v2","runs/pilot-float"]:
        rows=read_jsonl(ROOT/path/"responses.jsonl")
        assert len(rows)==24 and len({r["id"] for r in rows})==24
        assert all(r["error"] is None for r in rows)
    for path in ["models/qwen-base-matched","models/pilot-v1"]:
        manifest=json.loads((ROOT/path/"manifest.json").read_text())
        for name,record in manifest["files"].items():
            assert digest(ROOT/path/name)==record["sha256"]
    result=json.loads((ROOT/"checkpoints/pilot-v1/result.json").read_text())
    resources=json.loads((ROOT/"checkpoints/pilot-v1/resources.json").read_text())
    assert result["steps"]==46 and result["lora_b_norm_from_zero_init"]>0
    assert resources["visible_gpu"]=="-1" and resources["peak_gpu_allocated_mib"]==0
    assert resources["peak_rss_mib"]<=20000 and result["elapsed_seconds"]<=1800
    for path in ["runs/quantized-base-matched","runs/quantized-pilot"]:
        summary=json.loads((ROOT/path/"summary.json").read_text())
        rows=read_jsonl(ROOT/path/"responses.jsonl")
        assert len(rows)==48 and len({(r["id"],r["cues"]) for r in rows})==48
        assert all(r["error"] is None for r in rows)
        assert summary["chat_client_smoke"]["exit_code"]==0
        assert summary["gpu_layers"]==0
    pilot=json.loads((ROOT/"runs/quantized-pilot/summary.json").read_text())
    assert pilot["model_mib"]<=512 and pilot["process_peak_rss_mib"]<=2048
    for mode in ["plain","cues"]:
        assert pilot[mode]["warm_first_content_p95_ms"]<=500
        assert pilot[mode]["minimum_decode_tokens_per_second"]>=20
    print("PASS: artifact hashes, complete journals, actual optimization, resource caps, desktop CPU targets")
    print("FAILED ACCEPTANCE: social-quality regressions remain; see PILOT_REPORT.md. Human/laptop validation pending.")
    return 2


if __name__=="__main__": sys.exit(main())
