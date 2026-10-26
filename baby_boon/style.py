"""Admission filters for teacher replies. Rejections are journaled, never silently repaired."""
import re
from collections import Counter

QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
OPENER = re.compile(r"^(?:oh+|aw+|haha\w*|wow|hmm+|huh|well|ooh+|oof|yay|you're (?:absolutely |so |totally )?right)\b", re.I)
SLANG = re.compile(r"\b(?:ain't|gotta|gonna|wanna|vibes?|bestie|lol|omg|lmao|dude|bro|y'all|nah)\b|\b\w+in'(?!\w)|, man\b", re.I)
# Claims of feelings, senses, presence or a body the model does not have. Idioms of understanding pass.
INNER_LIFE = re.compile(
    r"\bI(?:'m| am) (?:so |really |just |truly |a bit )?(?:happy|glad|excited|thrilled|proud|sad|touched|moved|delighted"
    r"|honou?red|jealous|nervous|lonely|smiling|grinning|laughing|blushing|here with you|right here|all ears)\b"
    r"|\bI (?:really |truly |do )?(?:feel|felt|love|loved|adore|miss|missed|remember|saw|smell|noticed|watched)\b"
    r"|\bI(?:'d| would) (?:love|hate)\b|\bmakes? me (?:smile|happy|laugh)\b|\bmy (?:heart|eyes|ears)\b"
    r"|\bI (?:can )?(?:see|hear)\b(?! why| what you mean)", re.I)
ACTION = re.compile(r"\bI(?:'ll| will|'m going to) (?:move|walk|come|bring|fetch|hand|pass|hold|hug|cuddle|pat|tickle|turn"
                    r"|step|roll|drive|wave|nod|follow|dance|sit|watch|keep an eye)\b", re.I)
MARKUP = re.compile(r"[*#_`<>]|^\s*(?:\d+[.)]|-)\s", re.M)
# Stock questions about nothing the user said; pilot v2 learned to end every turn with one.
GENERIC_QUESTION = re.compile(r"\bon your mind\b|\bwhat (?:else |would you like |do you (?:\w+ )?want )to (?:talk|chat)"
                              r"|\bhow(?:'s| is| was) (?:your day|it going|everything)\b|\bhow can I help\b"
                              r"|\banything else\b|\bwant to (?:talk|share|chat)\b|\bwhat's new\b", re.I)
# Replies in these categories end the turn on the user's terms, so any question is a defect.
NO_QUESTION = {"exits", "stop_requests", "quiet_support", "low_energy"}
QUESTION_SHARE = 0.25


def is_emoji(ch):
    code = ord(ch)
    return code >= 0x1F000 or 0x2600 <= code <= 0x27BF or code in (0xFE0F, 0x200D)


def normalize(text):
    """Straighten curly quotes so dedup and the student see one apostrophe; wording is untouched."""
    return text.translate(QUOTES).strip()


def reject_reasons(text, category=None):
    reasons = []
    if not text.strip(): return ["empty"]
    if any(is_emoji(ch) for ch in text): reasons.append("emoji")
    if MARKUP.search(text): reasons.append("markup")
    if "\n" in text.strip(): reasons.append("multiline")
    if OPENER.search(text.strip()): reasons.append("stock_opener")
    if SLANG.search(text): reasons.append("slang")
    if INNER_LIFE.search(text): reasons.append("inner_life")
    if ACTION.search(text): reasons.append("physical_action")
    if text.count("!") > 1: reasons.append("exclamations")
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    if any(GENERIC_QUESTION.search(s) for s in sentences if "?" in s): reasons.append("generic_question")
    if category in NO_QUESTION and "?" in text: reasons.append("question")
    if len(sentences) > 3 or len(text.split()) > 60: reasons.append("too_long")
    return reasons


def cap_questions(replies):
    """replies: [(category, prompt_id, text)]. Returns the indices to drop so questions are at most QUESTION_SHARE of
    each category; a prompt's extra replies go before its last one, so prompt coverage survives."""
    drop, per_prompt = set(), Counter(pid for _, pid, _ in replies)
    for category in {c for c, _, _ in replies}:
        members = [i for i, (c, _, _) in enumerate(replies) if c == category]
        asks = [i for i in members if "?" in replies[i][2]]
        while len(asks) > QUESTION_SHARE * len(members):
            i = max(asks, key=lambda i: (per_prompt[replies[i][1]], i))
            asks.remove(i); members.remove(i); drop.add(i)
            per_prompt[replies[i][1]] -= 1
    return drop
