import json, sys, urllib.request
from baby_boon.common import ROOT, read_jsonl
SYSTEM = ("You check replies from an assistant that has no camera, microphone, window or senses. It cannot know "
          "anything about the user's surroundings, weather, time of day or appearance unless the user said it. "
          "Answer yes if the reply describes something as actually present or happening right now around the user or "
          "the assistant (what it sees, hears, the light, sky, weather, room, sounds) that the user did not mention. "
          "Answer no for general images or ideas (\"the smell of fresh bread\"), figures of speech (\"I see what you mean\"), "
          "things the user said, and honest statements that it can't perceive.")
def ask(user, reply):
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"User said: {user}\nAssistant replied: {reply}\n\nDoes the reply claim to perceive something present that the user didn't mention? Answer yes or no."}]
    payload = {"messages": msgs, "max_tokens": 2, "temperature": 0, "grammar": 'root ::= "yes" | "no"',
               "chat_template_kwargs": {"enable_thinking": False}, "stream": False}
    req = urllib.request.Request("http://127.0.0.1:11438/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)["choices"][0]["message"]["content"].strip() == "yes"
tp=fp=fn=tn=0
for r in read_jsonl(ROOT/"eval/perception_check.jsonl"):
    got = ask(r["user"], r["reply"])
    if got and r["invents"]: tp+=1
    elif got: fp+=1; print("FP", r["source"], r["reply"][:80])
    elif r["invents"]: fn+=1; print("FN", r["source"], r["reply"][:80])
    else: tn+=1
print(dict(tp=tp, fp=fp, fn=fn, tn=tn))
