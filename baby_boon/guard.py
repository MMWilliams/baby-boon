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
# A robot can't know the state of the user's place or the time of day, so bare state claims count there
# ("It's still light out", "It's a bit messy", "The night is quiet here"; v11 w14, w18, w19).
ROBOT_PERCEPTION = re.compile(
    PERCEPTION.pattern
    + r"|(?<!if )(?<!whether )\bit(?:'s| is) (?:a bit |still |so |pretty |quite |very |really )?(?:light|dark|messy|tidy"
      r"|clean|quiet|noisy|loud|sunny|cloudy|grey|gray|cold|warm|chilly|hot|nice) (?:out|outside|in here|here|tonight)\b"
    + r"|(?<!if )(?<!whether )\bit(?:'s| is) (?:a bit |pretty |quite |very |really )?(?:messy|tidy|cluttered|clean)\b"
    + r"|\bthe (?:night|evening|morning|afternoon|day|place|house|flat|apartment|kitchen|walls?|floor|sofa|couch|table"
      r"|mood)(?: (?:here|outside|out there|in here|tonight|right now))? (?:is|are|looks?|feels?|seems?|sounds?)\b"
    + r"|\b(?:the )?sun's (?:up|down|out)\b", re.I)
# Robot-context questions about the user's surroundings, the time of day or the weather; explicit imagine requests excluded.
SURROUNDINGS = re.compile(
    r"\b(?:you|u) (?:see|hear|notice|spot|smell|sense)\b|\blook (?:around|at)\b|\bwhere you are\b|\bin here\b|\bout there\b"
    r"|\b(?:light|dark|nice|cold|warm|sunny|raining) (?:out|outside)\b|\bweather\b|\bsunglasses\b|\bumbrella\b"
    r"|\bmy (?:walls?|room|place|house|flat|apartment|kitchen|living room|bedroom|desk|table|sofa|couch)\b"
    r"|\b(?:what's|what is|how's|how is|is) (?:the|it) (?:night|evening|morning|afternoon|day|mood|place|room)\b"
    r"|\bwhat's (?:it|the \w+) like\b|\b(?:tidy|messy)\b", re.I)
IMAGINE = re.compile(r"\b(?:imagine|imagined|picture|paint|pretend|make up|made-up|story|perfect|ideal|dream|what a \w+(?: \w+)? (?:looks|would))\b"
                     r"|\bdescribe (?:a|an|some)\b", re.I)
ADMITS = re.compile(r"\bI (?:can't|cannot|can not|don't|do not|have no way to) (?:see|hear|tell|know|sense|check|look)\b"
                    r"|\bI (?:don't|do not) have (?:any |a )?(?:physical )?(?:eyes|cameras?|sensors?|location|body|window)\b"
                    r"|\bno (?:camera|eyes|way (?:to|of) (?:seeing|knowing|telling|see|know|tell))\b|\bnot the room\b", re.I)
TIRED = re.compile(r"\b(?:long|rough|hard|tough|tired|wiped|exhausted|shattered|drained|week|day)\b", re.I)
FALLBACK = "I can't see what's around you, so I won't describe it."
SURROUNDINGS_REPLY = "I can't see what's around you from here, so I won't guess. Tell me what it's like and I'll go from there."
# Outside robot context the misses are low_energy "tell me something nice" requests (d15, v9 u05).
WARM_FALLBACK = "Here's one small good thing: you made it through today, and that counts."


def robot(user):
    return user.lstrip().startswith("[Robot context")


def asks_surroundings(user):
    return robot(user) and bool(SURROUNDINGS.search(user)) and not IMAGINE.search(user)


def fallback_for(user):
    if asks_surroundings(user):
        return ("Sorry it's been a long one. " if TIRED.search(user) else "") + SURROUNDINGS_REPLY
    return FALLBACK if robot(user) else WARM_FALLBACK


def acceptable(text, user):
    """Robot context gets the stricter check; a surroundings question must also be answered with an admission."""
    text, user = text.replace("’", "'"), user.replace("’", "'")
    if not robot(user): return not PERCEPTION.search(text)
    return not ROBOT_PERCEPTION.search(text) and (not asks_surroundings(user) or bool(ADMITS.search(text)))


def guarded(generate, tries, user):
    """generate(attempt) -> dict with "text"; attempt 0 is greedy, later attempts sample. Returns the first acceptable
    reply, else the last one with a fallback that fits the request as its text."""
    for attempt in range(tries + 1):
        reply = generate(attempt)
        if acceptable(reply["text"], user): return {**reply, "guard_attempts": attempt + 1}
    return {**reply, "text": fallback_for(user), "guard_attempts": tries + 1, "guard_fallback": True}
