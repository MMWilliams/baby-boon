"""Text and presentation cues via a separately running local CPU server."""
import argparse
import json
import sys
import urllib.request

from .common import SYSTEM
from .cues import CUE_INSTRUCTION, parse_response


def main():
    sys.stdout.reconfigure(encoding="utf-8",errors="backslashreplace")
    p=argparse.ArgumentParser()
    p.add_argument("--url",default="http://127.0.0.1:11438")
    p.add_argument("--message")
    a=p.parse_args()
    messages=[{"role":"system","content":SYSTEM+CUE_INSTRUCTION}]
    while True:
        try: text=a.message if a.message is not None else input("You: ")
        except (EOFError,KeyboardInterrupt): break
        if not text.strip() or text.strip().lower() in {"/quit","/exit"}: break
        messages.append({"role":"user","content":text})
        payload={"messages":messages,"max_tokens":128,"temperature":0,
                 "chat_template_kwargs":{"enable_thinking":False},"stream":False}
        request=urllib.request.Request(a.url+"/v1/chat/completions",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(request,timeout=120) as r: result=json.load(r)
        raw=result["choices"][0]["message"]["content"]
        parsed=parse_response(raw)
        print(json.dumps(parsed,ensure_ascii=False))
        # Session-only history, no database or persistent memory. Keep recent turns.
        messages.append({"role":"assistant","content":parsed["text"]})
        if len(messages)>9: messages=[messages[0]]+messages[-8:]
        if a.message is not None: break


if __name__=="__main__": main()
