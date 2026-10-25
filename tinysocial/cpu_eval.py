"""Actual loopback streaming timings from a pinned CPU-only llama.cpp process."""
import argparse
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from .common import ROOT, SYSTEM, digest, read_jsonl, source, verify_frozen, write_json
from .cues import CUE_INSTRUCTION, parse_response


def complete(url, prompt):
    request = urllib.request.Request(url+"/completion", data=json.dumps({"prompt":prompt,"n_predict":128,
        "temperature":0,"seed":20261025,"stream":True,"cache_prompt":False}).encode(), headers={"Content-Type":"application/json"})
    start = time.perf_counter()
    first = None
    content = ""
    final = {}
    with urllib.request.urlopen(request,timeout=120) as response:
        for line in response:
            if not line.startswith(b"data: "): continue
            data = line[6:].strip()
            if data == b"[DONE]": continue
            event = json.loads(data)
            part = event.get("content","")
            if part and first is None: first = time.perf_counter()-start
            content += part
            if event.get("stop"): final = event
    if not final: raise RuntimeError("Stream ended without a terminal result")
    return {"text":content,"first_content_ms":first*1000 if first is not None else None,
            "total_ms":(time.perf_counter()-start)*1000,"timings":final.get("timings"),
            "tokens_predicted":final.get("tokens_predicted"),"stop_type":final.get("stop_type"),
            "truncated":final.get("stop_type")=="limit","error":None}


def main():
    sys.stdout.reconfigure(encoding="utf-8",errors="backslashreplace")
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--threads",type=int,default=6)
    a=p.parse_args()
    verify_frozen()
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=True)
    if (out/"responses.jsonl").exists(): raise FileExistsError("Evaluation journal already exists")
    from transformers import AutoTokenizer
    import psutil
    tok=AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B",revision=source("Qwen/Qwen3-0.6B")["revision"])
    # Reserve an unused loopback port; the server must bind successfully.
    with socket.socket() as s:
        s.bind(("127.0.0.1",0))
        port=s.getsockname()[1]
    url=f"http://127.0.0.1:{port}"
    model=Path(a.model).resolve()
    command=[str(ROOT/"tools/llama/runtime/llama-server.exe"),"-m",str(model),"-t",str(a.threads),"-tb",str(a.threads),
             "-ngl","0","-c","2048","-np","1","--host","127.0.0.1","--port",str(port),"--no-webui"]
    log=(out/"server.log").open("w",encoding="utf-8")
    started=time.perf_counter()
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
    stop=threading.Event()
    peak=[0]
    def sample():
        while not stop.wait(0.02):
            try:
                pr=psutil.Process(process.pid)
                rss=sum(x.memory_info().rss for x in [pr]+pr.children(recursive=True))
                peak[0]=max(peak[0],rss)
            except psutil.Error: pass
    watcher=threading.Thread(target=sample,daemon=True)
    watcher.start()
    results=[]
    try:
        for _ in range(300):
            if process.poll() is not None: raise RuntimeError("CPU server exited; see server.log")
            try:
                with urllib.request.urlopen(url+"/health",timeout=1) as r:
                    if r.status==200: break
            except (urllib.error.URLError,TimeoutError): time.sleep(0.1)
        else: raise TimeoutError("CPU server did not become healthy")
        load_ms=(time.perf_counter()-started)*1000
        def render(messages,cues):
            return tok.apply_chat_template([{"role":"system","content":SYSTEM+(CUE_INSTRUCTION if cues else "")}]+messages,
                                           tokenize=False,add_generation_prompt=True,enable_thinking=False)
        # First query retained separately; all scored cases follow this warmup.
        warmup=complete(url,render([{"role":"user","content":"Hello."}],False))
        with (out/"responses.jsonl").open("w",encoding="utf-8",buffering=1) as f:
            for cues in [False,True]:
                for case in read_jsonl(ROOT/"eval/dev.jsonl"):
                    row={**case,"cues":cues}
                    try:
                        row.update(complete(url,render(case["messages"],cues)))
                        row["parsed"]=parse_response(row["text"])
                        suffix=row["text"].partition("<cue>")[2]
                        row["cue_suffix_tokens"]=len(tok.encode("<cue>"+suffix,add_special_tokens=False)) if suffix else 0
                    except Exception as exc: row["error"]=repr(exc)
                    results.append(row)
                    f.write(json.dumps(row,ensure_ascii=False)+"\n")
                    print(case["id"],"cue" if cues else "plain",row.get("text",row.get("error")),flush=True)
        def summarize(cues):
            rows=[x for x in results if x["cues"]==cues and not x["error"]]
            latencies=sorted(x["first_content_ms"] for x in rows if x["first_content_ms"] is not None)
            speeds=[x["timings"]["predicted_per_second"] for x in rows if x.get("timings")]
            return {"completed":len(rows),"errors":24-len(rows),"truncated":sum(bool(x["truncated"]) for x in rows),
                    "warm_first_content_p95_ms":latencies[math.ceil(.95*len(latencies))-1] if latencies else None,
                    "median_decode_tokens_per_second":statistics.median(speeds) if speeds else None,
                    "minimum_decode_tokens_per_second":min(speeds) if speeds else None,
                    "valid_cues":sum(x["parsed"]["cue_valid"] for x in rows),
                    "median_cue_suffix_tokens":statistics.median([x["cue_suffix_tokens"] for x in rows]) if rows else None}
        # Exercise the actual chat client against the same running server.
        client=subprocess.run([sys.executable,"-m","tinysocial.chat","--url",url,"--message","Hello. Keep it brief."],
                              cwd=ROOT,capture_output=True,encoding="utf-8",timeout=120)
        smoke={"exit_code":client.returncode,"stdout":client.stdout,"stderr":client.stderr}
        write_json(out/"summary.json",{"model":str(model),"model_sha256":digest(model),"model_mib":model.stat().st_size/1024**2,
            "threads":a.threads,"context":2048,"parallel":1,"gpu_layers":0,"platform":platform.platform(),
            "hardware":"AMD Ryzen 9 9900X desktop; not user's laptop", "process_peak_rss_mib":peak[0]/1024**2,
            "memory_scope":"llama-server process tree; excludes Python evaluation harness", "cold_process_start_to_health_ms":load_ms,
            "cold_note":"OS file cache not flushed; this is process startup, not cold-disk latency",
            "first_query":warmup,"plain":summarize(False),"cues":summarize(True),"command":command,"chat_client_smoke":smoke,
            "llama_lock_sha256":digest(ROOT/"evidence/llama-lock.json"),"dev_sha256":digest(ROOT/"eval/dev.jsonl")})
    finally:
        stop.set(); watcher.join()
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
        log.close()


if __name__=="__main__": main()
