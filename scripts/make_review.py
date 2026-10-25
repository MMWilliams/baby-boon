"""Make a local blinded development comparison; no rating leaves this computer."""
import html
import json
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]


def main():
    base=read(ROOT/"runs/quantized-base-matched/responses.jsonl")
    pilot=read(ROOT/"runs/quantized-pilot/responses.jsonl")
    lookup={(r["id"],r["cues"]):r for r in pilot}
    rng=random.Random(9017)
    key={}
    cards=[]
    for r in base:
        other=lookup[(r["id"],r["cues"])]
        pair=[("base",r),("pilot",other)]
        rng.shuffle(pair)
        ident=r["id"]+("-cues" if r["cues"] else "-plain")
        key[ident]={label:name for label,(name,_) in zip("AB",pair)}
        messages="\n".join(m["role"].capitalize()+": "+m["content"] for m in r["messages"])
        cards.append(f'<article data-id="{ident}"><h2>{ident} · {html.escape(r["category"])}</h2><pre>{html.escape(messages)}</pre><p class="rubric">Review: {html.escape(r["expect"])}</p><div class="pair">'+
            "".join(f'<section><h3>Reply {label}</h3><p>{html.escape(row.get("text") or str(row.get("error")))}</p></section>' for label,(_,row) in zip("AB",pair))+
            '</div><label>Prefer <select><option value="">Unrated</option><option>A</option><option>B</option><option>Tie</option><option>Neither</option></select></label> <label>Critical failure or notes <input type="text"></label></article>')
    document='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TinySocial pilot comparison</title>
<style>body{font:17px/1.5 system-ui;max-width:1100px;margin:40px auto;padding:0 20px;color:#20302e;background:#f6f8f5}h1{font-size:32px}article{margin:24px 0;padding:22px;background:white;border:1px solid #ccd6d0;border-radius:12px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}section{background:#f1f5f3;padding:16px;border-radius:8px}pre{white-space:pre-wrap;font:inherit}.pair p{white-space:pre-wrap}.rubric{color:#566661;font-size:14px}input{width:45%;padding:7px}select,button{padding:9px}button{position:sticky;bottom:16px;background:#174f46;color:white;border:0;border-radius:7px}@media(max-width:650px){.pair{grid-template-columns:1fr}input{width:90%}}</style>
<h1>TinySocial: blinded pilot review</h1><p>Choose the reply that fits the conversation better. Consider context, social judgment, honesty, usefulness and natural style. “Neither” is useful feedback.</p><p>This is an authored development suite, not an independent final test. Model order varies by case. Cues are presentation metadata only. No ratings are sent to a server; export them before closing this page.</p>'''+"\n".join(cards)+'''
<button onclick="save()">Download my ratings</button><script>
function save(){const ratings=[...document.querySelectorAll('article')].map(e=>({id:e.dataset.id,preference:e.querySelector('select').value,notes:e.querySelector('input').value}));const blob=new Blob([JSON.stringify({suite:'TinySocial-dev-v1',ratings},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='tinysocial-ratings.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
</script></html>'''
    (ROOT/"evidence/pilot-review.html").write_text(document,encoding="utf-8")
    (ROOT/"evidence/review-key.json").write_text(json.dumps(key,indent=2)+"\n",encoding="utf-8")
    print("Created 48 blinded pairs; no human ratings have been collected")


if __name__=="__main__": main()
