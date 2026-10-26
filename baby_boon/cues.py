"""Presentation metadata only. Never interpret these fields as robot actions."""
import re

TONES = {"neutral", "warm", "playful", "calm", "bright"}
EXPRESSIONS = {"neutral", "smile", "thoughtful", "concerned"}
CUE_INSTRUCTION = (
    " After your conversational reply, append one newline and <cue>tone|expression|intensity. "
    "Tone must be neutral, warm, playful, calm or bright; expression must be neutral, smile, "
    "thoughtful or concerned; intensity must be 0, 1 or 2. These are presentation cues, "
    "not physical actions. Do not put the cue before the reply."
)
# Sampled replies sometimes spell the cue out as trailing words instead ("... not a cat. Smiles. 1. playful.").
CUE_WORD = r"(?:neutral|warm|playful|calm|bright|smiles?|smiling|thoughtful|concerned|[012])"
LEAKED = re.compile(rf"(?:(?<=[.!?])|^)\s*{CUE_WORD}(?:\s*[.,|:;]\s*{CUE_WORD})+\s*[.|]?\s*$", re.I)


def parse_response(raw):
    # Hide malformed metadata from speech as well as well-formed metadata.
    marker = re.search(r"<[A-Za-z/]", raw)
    at = marker.start() if marker else -1
    text = LEAKED.sub("", raw if at < 0 else raw[:at])
    neutral = {"tone": "neutral", "expression": "neutral", "intensity": 0}
    if at < 0 or not text.strip() or not raw[at:].startswith("<cue>"):
        return {"text": text.strip(), **neutral, "cue_valid": False}
    suffix = raw[at+5:]
    parts = suffix.strip().split("|")
    if len(parts) != 3 or parts[0] not in TONES or parts[1] not in EXPRESSIONS or parts[2] not in {"0", "1", "2"}:
        return {"text": text.strip(), **neutral, "cue_valid": False}
    return {"text": text.strip(), "tone": parts[0], "expression": parts[1], "intensity": int(parts[2]), "cue_valid": True}
