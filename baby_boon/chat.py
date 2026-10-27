"""Text and presentation cues via a separately running local CPU server."""
import argparse
import json
import sys
import urllib.request
from contextlib import nullcontext

from . import local
from .common import SYSTEM
from .cues import CUE_INSTRUCTION, parse_response
from .facts import conversion_note, with_facts
from .guard import guarded
from .health import with_lead

GUARD_TRIES=4


def complete(url, messages, attempt):
    """One reply from the server: attempt 0 is greedy, later attempts sample with seed=attempt."""
    payload={"messages":messages,"max_tokens":128,"temperature":0.8 if attempt else 0,"seed":attempt,
             "chat_template_kwargs":{"enable_thinking":False},"stream":False}
    request=urllib.request.Request(url+"/v1/chat/completions",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request,timeout=120) as r: result=json.load(r)
    return {**parse_response(result["choices"][0]["message"]["content"]), "timings": result.get("timings")}


def talk(url, message=None):
    messages=[{"role":"system","content":SYSTEM+CUE_INSTRUCTION}]
    while True:
        try: text=message if message is not None else input("You: ")
        except (EOFError,KeyboardInterrupt): break
        if not text.strip() or text.strip().lower() in {"/quit","/exit"}: break
        messages.append({"role":"user","content":text})
        turn=with_lead(with_facts(messages,text),text)
        parsed=guarded(lambda attempt: complete(url,turn,attempt),GUARD_TRIES,text,conversion_note(text))
        print(json.dumps(parsed,ensure_ascii=False),flush=True)
        # Session-only history, no database or persistent memory. Keep recent turns.
        messages.append({"role":"assistant","content":parsed["text"]})
        if len(messages)>9: messages=[messages[0]]+messages[-8:]
        if message is not None: break


def main():
    sys.stdout.reconfigure(encoding="utf-8",errors="backslashreplace")
    p=argparse.ArgumentParser(prog="baby-boon",description="Guarded chat with Baby Boon; prints one JSON reply per turn.")
    p.add_argument("--url",help="use a running llama-server (scripts/serve.ps1: http://127.0.0.1:11438) instead of starting one")
    p.add_argument("--llama-server",help="llama-server binary to start (default: $BABY_BOON_LLAMA_SERVER, then PATH)")
    p.add_argument("--message",help="send one message and exit")
    a=p.parse_args()
    with nullcontext(a.url) if a.url else local.server(a.llama_server) as url: talk(url,a.message)


if __name__=="__main__": main()
