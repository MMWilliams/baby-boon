"""Bounded CPU-only feasibility probe; does not generate or admit training data."""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from baby_boon.common import SYSTEM, digest, read_jsonl, source, write_json
from baby_boon.cpu_eval import complete


def main():
    from transformers import AutoTokenizer
    manifest_path=Path.home()/".ollama/models/manifests/registry.ollama.ai/library/qwen3/4b"
    manifest=json.loads(manifest_path.read_text())
    layer=next(x for x in manifest["layers"] if x["mediaType"]=="application/vnd.ollama.image.model")
    model=Path.home()/".ollama/models/blobs"/layer["digest"].replace(":","-")
    if digest(model)!=layer["digest"].split(":")[1]: raise ValueError("Local teacher blob changed")
    dest=ROOT/"runs/teacher-cpu-probe"
    dest.mkdir(parents=True,exist_ok=True)
    if (dest/"responses.jsonl").exists(): raise FileExistsError("Probe already exists")
    tok=AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B",revision=source("Qwen/Qwen3-0.6B")["revision"],local_files_only=True)
    with socket.socket() as s:
        s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    url=f"http://127.0.0.1:{port}"
    command=[str(ROOT/"tools/llama/runtime/llama-server.exe"),"-m",str(model),"-ngl","0","-t","6","-tb","6","-c","2048","-np","1","--host","127.0.0.1","--port",str(port),"--no-webui"]
    with (dest/"server.log").open("w") as log:
        server=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        try:
            for _ in range(300):
                if server.poll() is not None: raise RuntimeError("Teacher server exited")
                try:
                    with urllib.request.urlopen(url+"/health",timeout=1) as r:
                        if r.status==200: break
                except (urllib.error.URLError,TimeoutError): time.sleep(.1)
            else: raise TimeoutError("Teacher load timed out")
            records=[]
            for row in read_jsonl(ROOT/"eval/dev.jsonl"):
                if row["id"] not in {"d03","d09","d11","d17","d23"}: continue
                prompt=tok.apply_chat_template([{"role":"system","content":SYSTEM}]+row["messages"],tokenize=False,add_generation_prompt=True,enable_thinking=False)
                records.append({**row,**complete(url,prompt)})
            (dest/"responses.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records),encoding="utf-8")
            write_json(dest/"manifest.json",{"model":"installed ollama qwen3:4b","model_blob_sha256":layer["digest"],"ollama_manifest_sha256":digest(manifest_path),
                       "purpose":"Five-case CPU feasibility probe, no training admission or quality certification","command":command,
                       "prompt_template":"Qwen3 non-thinking rendered as text; runtime tokenizes using teacher's GGUF vocabulary"})
            print("Teacher CPU probe complete; 5 development responses retained",flush=True)
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill();server.wait()


if __name__=="__main__": main()
