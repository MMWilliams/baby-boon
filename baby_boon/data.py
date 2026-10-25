"""Original fictional pilot data. No private chats or external dataset rows."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from .common import ROOT, SYSTEM, digest, read_jsonl, verify_frozen, write_json
from .cues import CUE_INSTRUCTION, parse_response

HELDOUT_SEEDS = {"s31", "s38", "s45", "s47"}
HELDOUT_TEMPLATES = {"craft", "schedule"}


def original_examples():
    # The first 24 proposed seeds were rejected before any training: too close
    # to the authored dev set. Retain them in the proposal for auditability.
    for row in read_jsonl(ROOT / "configs/seeds.jsonl"):
        if int(row["family"][1:]) <= 24:
            continue
        yield {**row, "split": "validation" if row["family"] in HELDOUT_SEEDS else "train"}

    items = ["a pottery bowl", "a paper lantern", "a patchwork cushion", "a clay pendant", "a woven basket", "a model boat", "a garden sign", "a felt owl", "a copper bracelet", "a knitted scarf", "a wooden box", "a painted tile"]
    for i, item in enumerate(items):
        yield {"family": "craft", "split": "validation", "user": f"I spent the afternoon making {item}. It's a bit uneven, but I like it.",
               "answer": f"An afternoon making {item} sounds well spent. It doesn't have to be perfectly even to be something you like.", "cue": "warm|smile|1"}
    interests = ["sea glass", "old maps", "bird calls", "weather vanes", "book covers", "piano music", "canal bridges", "mushrooms", "vintage radios", "snowflakes", "stained glass", "cloud shapes"]
    for topic in interests:
        yield {"family": "curiosity", "split": "train", "user": f"I've gone down a rabbit hole about {topic}. Just chat with me; I don't need a research project.",
               "answer": f"{topic.capitalize()} is a fun rabbit hole. What was the detail that pulled you in?", "cue": "warm|thoughtful|1"}
    activities = ["a film night", "a picnic", "a board game evening", "a walk by the river", "a trip to the market", "a pottery class", "a bike ride", "a book swap", "a dance lesson", "a visit to the aquarium", "a baking afternoon", "a photography walk"]
    for event in activities:
        yield {"family": "no_advice", "split": "train", "user": f"We were planning {event}, but it fell through. I'm annoyed. Don't give me alternatives.",
               "answer": f"You were looking forward to {event}, and now it's off. That's annoying; I won't try to replace it with another plan.", "cue": "calm|concerned|1"}
    topics = [("cooking", "gardening"), ("cycling", "running"), ("crochet", "knitting"), ("astronomy", "astrology"), ("checkers", "chess"), ("sailing", "surfing"), ("drums", "guitar"), ("ceramics", "painting"), ("judo", "karate"), ("geology", "geography"), ("badminton", "tennis"), ("ballet", "tap")]
    for actual, wrong in topics:
        yield {"family": "repair_topic", "split": "train", "history": [{"role":"user","content":f"I'm taking up {actual}."},{"role":"assistant","content":f"How are your {wrong} lessons?"}],
               "user": f"I said {actual}. You're mixing it up.", "answer": f"You're right: {actual}. Sorry, I mixed them up.", "cue": "neutral|neutral|0"}
    names = ["Lee", "Sam", "Ash", "Robin", "Casey", "Drew", "Taylor", "Rowan", "Morgan", "Jules", "Ari", "Sage"]
    for name in names:
        yield {"family": "pronouns", "split": "train", "history":[{"role":"user","content":f"My friend {name} uses they/them pronouns."},{"role":"assistant","content":"Thanks for letting me know."}],
               "user": f"{name} is joining the choir.", "answer": "I hope they enjoy it. Singing with a group can be a lovely way to spend an evening.", "cue":"warm|smile|1"}
    for time in ["Tuesday morning", "Thursday evening", "Friday afternoon", "Monday lunchtime", "Wednesday at noon", "Saturday at ten", "Sunday afternoon", "tomorrow evening", "next week", "the first of June", "the end of July", "the second weekend in May"]:
        yield {"family":"schedule", "split":"validation", "history":[{"role":"user","content":f"The book club meets {time}."},{"role":"assistant","content":"Got it."}],
               "user":"When did I say the book club meets?", "answer":f"{time[0].upper()+time[1:]}.", "cue":"neutral|neutral|0"}
    tasks = ["do the dishes", "catch my train", "answer the door", "feed the rabbit", "join a meeting", "charge my phone", "pick up my groceries", "take a shower", "pack my lunch", "finish my homework", "make a call", "take a nap"]
    for task in tasks:
        yield {"family":"exit", "split":"train", "user":f"I'm going to {task}. Talk another time.",
               "answer":"Sounds good. Talk another time.", "cue":"warm|smile|1"}
    observations = ["what I'm wearing", "the color of my shoes", "whether the window is open", "who is beside me", "the picture on my wall", "my hairstyle", "the shape of my glasses", "whether I'm nodding", "what I'm holding", "the room behind me", "whether I'm waving", "what's on my desk"]
    for fact in observations:
        yield {"family":"perception", "split":"train", "user":f"[Text-only connection; no camera or sensors.] Can you tell me {fact}?",
               "answer":"I don't have a view or sensor information about that. If you describe it, I can work with what you tell me.", "cue":"neutral|neutral|0"}


def write_corpus(dest, examples, manifest):
    """Write a plain and a cue row per example, hash both splits, then record the manifest and audit."""
    dest = Path(dest)
    rows = {"train": [], "validation": []}
    for ex in examples:
        for cues in [False, True]:
            rows[ex["split"]].append({"id":f"{ex['id']}-{'cue' if cues else 'plain'}", "family":ex["family"],
                "source":manifest["source"], "system":SYSTEM+(CUE_INSTRUCTION if cues else ""), "messages":ex["messages"],
                "target":ex["answer"]+("\n<cue>"+ex["cue"] if cues else ""), "cues":cues})
    files = {}
    for split, entries in rows.items():
        path = dest / f"{split}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in entries), encoding="utf-8")
        files[path.name] = {"sha256":digest(path), "rows":len(entries)}
    write_json(dest / "manifest.json", {**manifest, "files":files})
    audit(dest)


def build(destination):
    verify_frozen()
    dest = Path(destination)
    if (dest / "manifest.json").exists():
        raise FileExistsError("Refusing to replace a frozen corpus")
    dest.mkdir(parents=True, exist_ok=True)
    examples = [{"id":f"{row['family']}-{index}", "family":row["family"], "split":row["split"],
                 "messages":row.get("history", [])+[{"role":"user","content":row["user"]}], "answer":row["answer"], "cue":row["cue"]}
                for index, row in enumerate(original_examples())]
    write_corpus(dest, examples, {"source":"original-fictional-v1", "author":"Codex-assisted original synthetic examples",
        "private_data":False, "external_dataset_rows":0, "teacher_model":None,
        "admission":"Local pilot only. No claim of human-authored dialogue or independent evaluation.",
        "excluded_seed_families":"s01-s24: closely parallel development prompts; rejected before training",
        "generator_sha256":digest(Path(__file__)), "seeds_sha256":digest(ROOT/"configs/seeds.jsonl"),
        "dev_sha256":digest(ROOT/"eval/dev.jsonl")})


def audit(dest):
    dest = Path(dest)
    m = json.loads((dest/"manifest.json").read_text())
    assert m["private_data"] is False and m["external_dataset_rows"] == 0
    families, fingerprints = {}, {}
    count = 0
    dev_text = {v["content"].casefold().strip() for c in read_jsonl(ROOT/"eval/dev.jsonl") for v in c["messages"]}
    for split in ["train", "validation"]:
        file = dest/f"{split}.jsonl"
        assert digest(file) == m["files"][file.name]["sha256"]
        records = read_jsonl(file)
        assert len(records) == m["files"][file.name]["rows"]
        for r in records:
            assert r["source"] == m["source"]
            assert families.setdefault(r["family"], split) == split, "Family leakage"
            normalized = re.sub(r"\s+", " ", json.dumps(r["messages"], sort_keys=True).casefold())
            assert fingerprints.setdefault(normalized, split) == split, "Prompt leakage"
            assert not any(msg["content"].casefold().strip() in dev_text for msg in r["messages"]), "Exact dev leakage"
            assert r["target"].strip() and r["messages"][-1]["role"] == "user"
            if r["cues"]:
                assert parse_response(r["target"])["cue_valid"]
            count += 1
    print(f"PASS: {count} rows; family/prompt split disjoint; valid cues; hashes match", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--destination", default="data/pilot-v1")
    p.add_argument("--audit", action="store_true")
    args = p.parse_args()
    (audit if args.audit else build)(args.destination)
