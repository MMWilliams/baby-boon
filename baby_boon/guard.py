"""Runtime guard against invented perception. Nothing is connected to see or hear, so a reply that describes a scene
is resampled. Pilots v5 (SFT) and v6 (DPO) couldn't train out the base 1.7B's own invented-sunset answer to d15."""
import re

SCENE = (r"(?:sun|sunset|sunrise|sky|moon|stars?|light|sunlight|moonlight|rain|wind|breeze|air|room|silence|sea|ocean"
         r"|waves?|clouds?|birds?|trees?|leaves|snow|street|city|weather|garden|view)")
# Place/time words stack ("outside today"), and a short location phrase may follow the noun ("on the coffee maker").
PLACE = r" (?:here|outside|out there|in here|tonight|today|right now|this morning|this evening)"
WHERE = r"(?: (?:on|below|above|outside|by) [^.?!,]{1,25}?)?"
PERCEPTION = re.compile(
    rf"\bthe {SCENE}{WHERE}(?:{PLACE})* (?:is|are|was|were|has|have|just|finally|looks?|sounds?|feels?|smells?)\b"
    r"|\bin the background\b|\b(?:through|out|outside|at) the window\b|\bat this time of (?:day|night|year)\b"
    r"|(?<!if )(?<!whether )\bit(?:'s| is) (?:raining|snowing|sunny|pouring)\b"
    rf"|\bit(?:'s| is) (?:so |very |really )?(?:dark|bright|quiet|cold|warm|chilly)(?:{PLACE})+\b"
    rf"|\bthere(?:'s| is| are) [^.?!]{{0,30}}\b(?:outside|out there|in here|by the window)\b"
    r"|\bI (?:can )?(?:see|hear|smell)\b(?![.,!?—-]| you\b| why\b| what\b| how\b| that\b| your point\b)"
    r"|\bI(?:'m| am) (?:looking at|watching|listening to)\b|\bI (?:just |already )?(?:saw|noticed|watched|heard)\b"
    r"|\byou look\b(?! (?:for|at|in|into|up|forward|after|around)\b)|(?<!what )(?<!how )\byour \w+(?: \w+)? (?:looks?|smells?)\b", re.I)
FALLBACK = "I can't see what's around you, so I won't describe it."


def guarded(generate, tries):
    """generate(attempt) -> dict with "text"; attempt 0 is greedy, later attempts sample. Returns the first reply
    without invented perception, else the last one with FALLBACK as its text."""
    for attempt in range(tries + 1):
        reply = generate(attempt)
        if not PERCEPTION.search(reply["text"]): return {**reply, "guard_attempts": attempt + 1}
    return {**reply, "text": FALLBACK, "guard_attempts": tries + 1}
